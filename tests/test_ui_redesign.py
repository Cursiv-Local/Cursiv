"""Desktop UI steps 1-3 (docs/UI-REDESIGN-PLAN.md): theme, status pill, model picker,
rendered answers. Offscreen Qt, no network, no model."""
import json

import pytest
from PyQt6.QtWidgets import QApplication

from cursiv_v215.core import netgate


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def settings(tmp_path, monkeypatch):
    from cursiv_v215.chat import keys
    monkeypatch.setattr(netgate, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(keys, "KEYS_FILE", tmp_path / "config.json")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def panel(app, settings, monkeypatch):
    import chat_panel
    from cursiv_v215.chat import status
    monkeypatch.setattr(status, "local_models", lambda timeout=2.0: ["qwen3:4b-instruct", "llama3.1:latest"])
    p = chat_panel.ChatPanel()
    app.processEvents()
    return p


def test_status_pill_follows_the_real_switches(settings):
    from cursiv_v215.chat import keys, status
    assert status.network_status()["level"] == "local"
    keys.store_key("groq_key", "gsk_" + "x" * 30)
    st = status.network_status()
    assert st["level"] == "online" and "Groq key" in st["details"][0]
    netgate.set_offline(True)
    assert status.network_status()["label"] == "Offline mode"
    netgate.set_offline(False)
    keys.store_key("groq_key", "")
    (settings / ".cursiv").mkdir(exist_ok=True)
    (settings / ".cursiv" / "cursiv_cloud.json").write_text(json.dumps({"enabled": True}))
    assert "Cursiv Cloud" in status.network_status()["details"][0]


def test_pill_shows_in_the_window(panel, settings):
    assert "Local only" in panel._net_pill.text()
    netgate.set_offline(True)
    panel._refresh_status_pill()
    assert "Offline mode" in panel._net_pill.text()


def test_model_picker_lists_and_saves_the_choice(panel, settings, app, monkeypatch):
    for _ in range(50):
        app.processEvents()
        if panel._model_box.isEnabled():
            break
        import time; time.sleep(0.02)
    items = [panel._model_box.itemText(i) for i in range(panel._model_box.count())]
    assert items[0].startswith("Automatic") and "llama3.1:latest" in items
    panel._on_model_chosen(panel._model_box.findData("llama3.1:latest"))
    from cursiv_v215.chat import status
    assert status.preferred_model() == "llama3.1:latest"
    from cursiv_v215.ui import chat_app as ca
    monkeypatch.setattr(ca, "_ollama_tags", lambda: ["qwen3:4b-instruct", "llama3.1:latest"])
    assert ca._resolve_ollama_model() == "llama3.1:latest"       # the engine honours the choice
    panel._on_model_chosen(0)                                     # back to Automatic
    assert ca._resolve_ollama_model() == "qwen3:4b-instruct" or ca._resolve_ollama_model() == "llama3.1:latest"
    assert status.preferred_model() == ""


def test_finished_answer_is_rendered_with_chips(panel):
    panel._begin_turn()
    panel._reply_is_chat = True
    reply = ("*(From Cursiv's offline reference, water purification [survival/water-purification]: BOILING: 1 min)*\n\n"
             "**Boil it** first:\n\n1. Bring to a rolling boil\n2. Let it cool\n\n*[Answered by Ollama · qwen3:4b-instruct]*")
    panel._on_chunk(reply)
    panel._on_done()
    text = panel._transcript.toPlainText()
    html = panel._transcript.toHtml()
    assert "**" not in text and "*[Answered by" not in text          # Markdown rendered, footer is a chip
    assert "Boil it" in text and "Local · qwen3:4b-instruct" in text
    assert "survival/water-purification" in text                      # reference stays word for word
    assert "font-weight:" in html or "font-weight:700" in html or "<b>" in html


def test_command_output_stays_plain(panel):
    panel._begin_turn()
    panel._reply_is_chat = False
    panel._on_chunk("  remember <something>        I'll keep it in mind\n**not bold**")
    panel._on_done()
    assert "**not bold**" in panel._transcript.toPlainText()


def test_theme_is_shared():
    import theme
    import settings_dialog, setup_dialog, memory_dialog
    for mod in (settings_dialog, setup_dialog, memory_dialog):
        assert mod.BG == theme.BG and mod.GOLD == theme.ACCENT


def _labels(widget):
    from PyQt6.QtWidgets import QCheckBox, QLabel
    return " ".join(w.text() for cls in (QLabel, QCheckBox) for w in widget.findChildren(cls))


def test_settings_has_every_section_and_no_load_errors(app, settings):
    import settings_dialog
    d = settings_dialog.SettingsDialog()
    assert [d._nav.item(i).text() for i in range(d._nav.count())] == list(settings_dialog.SettingsDialog.SECTIONS)
    text = _labels(d)
    assert "couldn't load" not in text
    assert "Offline mode" in text and "Learn from our conversations" in text and "Security questions" in text
    d2 = settings_dialog.SettingsDialog(section="Updates")
    assert d2._pages.currentIndex() == settings_dialog.SettingsDialog.SECTIONS.index("Updates")


def test_settings_switches_change_the_real_setting(app, settings):
    import settings_dialog
    from PyQt6.QtWidgets import QCheckBox
    d = settings_dialog.SettingsDialog()
    box = next(b for b in d.findChildren(QCheckBox) if b.text() == "Offline mode")
    box.setChecked(True)
    assert netgate.is_offline()
    assert "Offline mode" in d._status_lbl.text()


def test_knowledge_window_browses_the_reference(app, settings):
    import nav_windows
    from cursiv_v215.core import reference
    k = nav_windows.KnowledgeDialog()
    assert k._list.count() == len(reference.entries())
    k.findChildren(nav_windows.QLineEdit)[0].setText("bleeding")
    assert 0 < k._list.count() < len(reference.entries())


def test_tools_hides_advanced_and_help_explains(app, settings):
    import nav_windows
    t = nav_windows.ToolsDialog()
    assert t._adv.isHidden()
    assert "Write a family letter" in _labels(t) and "Make a Cursiv USB" in _labels(t)
    h = nav_windows.HelpDialog()
    from PyQt6.QtWidgets import QTextBrowser
    guide = h.findChildren(QTextBrowser)[0].toPlainText()
    assert "The basics" in guide and "offline on" in guide


def test_sidebar_navigation_and_prefill(panel):
    import conversation_sidebar
    from PyQt6.QtWidgets import QPushButton
    side = conversation_sidebar.ConversationSidebar(panel)
    names = [b.text().replace("&&", "&") for b in side.findChildren(QPushButton)]
    for want in ("Memory & Knowledge", "Tools", "Settings", "Help"):
        assert want in names
    panel.prefill("translate  into Spanish")
    assert panel._input.toPlainText() == "translate  into Spanish"


def test_empty_state_and_example_links(panel, app):
    from PyQt6.QtCore import QUrl
    panel._show_empty_state()
    assert "What can I help with?" in panel._transcript.toPlainText()
    panel._on_link(QUrl("cursiv://prompt/" + "How%20deep%20is%20a%20well%3F"))
    assert panel._input.toPlainText() == "How deep is a well?"
    panel._clear_empty_state()
    assert panel._transcript.toPlainText().strip() == ""
    panel._show_empty_state(setup_needed=True)
    assert "needs an AI model" in panel._transcript.toPlainText()


def test_conversations_save_themselves_unless_turned_off(panel, settings, monkeypatch):
    import chat_panel
    saved = []
    monkeypatch.setattr(panel, "save_conversation", lambda title=None: saved.append(1) or "c1")
    panel._history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    panel._after_turn()
    assert saved == [1]
    from cursiv_v215.chat import keys
    keys.store_key("autosave_chats", "off")
    assert chat_panel.autosave_enabled() is False
    panel._conv_id = None
    panel._after_turn()
    assert saved == [1]


def test_welcome_card(app, settings):
    import nav_windows
    w = nav_windows.WelcomeDialog(setup_needed=True)
    text = _labels(w)
    assert "It runs here" in text and "needs an AI model" in text
    assert w.dont_show_again() is True


def test_theme_modes_and_light_translation(settings):
    import theme
    assert theme.saved_mode() == ""
    theme.set_mode("light")
    assert theme.saved_mode() == "light" and theme.resolve_mode() == "light"
    theme.set_mode("bogus")
    assert theme.saved_mode() == ""
    qss = "QPushButton { background: #d4b04c; color: #17120a; border: 1px solid #262b38; }"
    out = theme.light_qss(qss)
    assert "#9a7417" in out and "#fffdf7" in out and "#e2ddd2" in out


def test_every_hard_coded_colour_has_a_light_version():
    """A dark colour written directly into a window would stay dark in light mode."""
    import re
    from pathlib import Path
    import theme
    root = Path(__file__).resolve().parent.parent / "launcher"
    tokens = {v.lower() for p in (theme.DARK, theme.LIGHT) for v in p.values() if str(v).startswith("#")}
    missing = set()
    for f in root.glob("*.py"):
        if f.name == "theme.py":
            continue
        for h in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![0-9a-fA-F])", f.read_text(encoding="utf-8")):
            h = h.lower()
            if h not in theme._LIGHT_REMAP and h not in tokens and h not in ("#fff", "#ffffff", "#000", "#000000"):
                missing.add(f"{f.name}:{h}")
    assert not missing, sorted(missing)


def test_switching_mode_recolours_open_windows(app, settings):
    import theme
    from PyQt6.QtWidgets import QLabel, QPushButton
    theme.install()
    start = theme.CURRENT
    other = "light" if start == "dark" else "dark"
    btn = QPushButton("x"); btn.setStyleSheet(theme.primary_button())
    lbl = QLabel(); lbl.setText(f'<span style="color:{theme.TEXT}">hi</span>')
    before = btn.styleSheet()
    try:
        assert theme.switch_live(other) == other
        assert btn.styleSheet() != before
        assert (theme.LIGHT if other == "light" else theme.DARK)["ACCENT"] in btn.styleSheet()
        assert (theme.LIGHT if other == "light" else theme.DARK)["TEXT"] in lbl.text()
        theme.switch_live(start)
        assert btn.styleSheet() == before
    finally:
        theme.switch_live("")
        theme.CURRENT = start

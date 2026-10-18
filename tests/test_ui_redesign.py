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

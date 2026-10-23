"""The help: short by default, topics on request, builder tools only for the owner."""
import chat_commands as cc


def _help(text, monkeypatch, builder=False, personal=False):
    monkeypatch.setattr(cc, "_is_builder", lambda: builder)
    monkeypatch.setattr(cc, "_personal", lambda: personal)
    r = cc.handle_command(text, cc._default_cfg(), [])
    return None if r is None else r.text


def test_help_is_short_and_plain(monkeypatch):
    text = _help("help", monkeypatch)
    assert len(text.splitlines()) <= 16
    for word in ("substrate", "funforge", "overseer", "sovereign", "blast", "postal", "tier"):
        assert word not in text.lower()
    assert "help more" in text


def test_research_help_leads_with_field_work(monkeypatch):
    text = _help("help", monkeypatch)
    assert "log site:" in text and "field report" in text and "add document" in text and "demo" in text
    assert "letter" not in text and "family" not in text.lower()
    topics = _help("help more", monkeypatch, builder=True)
    assert "help field" in topics and "help family" not in topics and "help builder" not in topics
    assert "write to <name>" in _help("help", monkeypatch, personal=True)
    assert "help family" in _help("help more", monkeypatch, personal=True)


def test_phone_links_are_native_and_present_once_in_both_short_help_profiles(monkeypatch):
    line = ('Phone notebook: https://cursiv.us/notebook · Phone photo chat: '
            'https://cursiv.us/app (separate from the notebook).')
    for personal in (False, True):
        text = _help('help', monkeypatch, personal=personal)
        assert text.splitlines().count(line) == 1
        assert text.count('https://cursiv.us/notebook') == 1
        assert text.count('https://cursiv.us/app') == 1


def test_field_help_has_exact_phone_capture_and_import_path(monkeypatch):
    line = ('Phone capture (works offline after first load): https://cursiv.us/notebook '
            '— export the file, then Field Notebook → Import or field log import <file>.')
    text = _help('help field', monkeypatch)
    assert text.count(line) == 1
    assert 'https://cursiv.us/notebook/' not in text
    assert 'cursiv.winklers-llc.com/notebook' not in text


def test_remember_is_described_as_saving(monkeypatch):
    assert "remember <something>" in _help("help", monkeypatch)
    assert "remember <query>" not in _help("help memory", monkeypatch)


def test_builder_topic_listed_only_for_the_owner(monkeypatch):
    assert "help builder" not in _help("help more", monkeypatch, builder=False, personal=True)
    assert "help builder" in _help("help more", monkeypatch, builder=True, personal=True)
    assert "evolve" in _help("help builder", monkeypatch)       # still opens if typed


def test_help_me_is_still_chat(monkeypatch):
    assert _help("help me write a letter to my sister", monkeypatch) is None
    assert 'Show personal features' in _help("help family", monkeypatch)
    assert _help("help family", monkeypatch, personal=True).startswith("FAMILY")


def test_tier_1_is_offline_mode(tmp_path, monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate, "CONFIG_FILE", tmp_path / "config.json")
    cfg = cc._default_cfg()
    assert "Offline mode ON" in cc.handle_command("tier 1", cfg, []).text
    assert netgate.is_offline()


def test_removed_commands_say_so_and_longer_text_is_chat(monkeypatch):
    assert "was removed" in _help("governor on", monkeypatch)
    assert "was removed" in _help("funforge", monkeypatch)
    assert _help("grow tomatoes in clay soil", monkeypatch) is None
    assert _help("notes from the meeting", monkeypatch) is None


def test_persona_is_plain():
    from pathlib import Path
    text = Path(__file__).resolve().parent.parent.joinpath(
        "cursiv_engine", "codex", "system_prompt.md").read_text(encoding="utf-8").lower()
    for word in ("evocore", "sovereign", "yin", "meta", "nexus", "soul", "drift", "33π", "decal"):
        assert word not in text, word

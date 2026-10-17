"""The help: short by default, topics on request, builder tools only for the owner."""
import chat_commands as cc


def _help(text, monkeypatch, builder=False):
    monkeypatch.setattr(cc, "_is_builder", lambda: builder)
    r = cc.handle_command(text, cc._default_cfg(), [])
    return None if r is None else r.text


def test_help_is_short_and_plain(monkeypatch):
    text = _help("help", monkeypatch)
    assert len(text.splitlines()) <= 15
    for word in ("substrate", "funforge", "overseer", "sovereign", "blast", "postal", "tier"):
        assert word not in text.lower()
    assert "help more" in text


def test_remember_is_described_as_saving(monkeypatch):
    assert "remember <something>" in _help("help", monkeypatch)
    assert "remember <query>" not in _help("help memory", monkeypatch)


def test_builder_topic_listed_only_for_the_owner(monkeypatch):
    assert "help builder" not in _help("help more", monkeypatch, builder=False)
    assert "help builder" in _help("help more", monkeypatch, builder=True)
    assert "substrate" in _help("help builder", monkeypatch)    # still opens if typed


def test_help_me_is_still_chat(monkeypatch):
    assert _help("help me write a letter to my sister", monkeypatch) is None
    assert _help("help family", monkeypatch).startswith("FAMILY")


def test_tier_1_is_offline_mode(tmp_path, monkeypatch):
    from cursiv_v215.core import netgate
    monkeypatch.setattr(netgate, "CONFIG_FILE", tmp_path / "config.json")
    cfg = cc._default_cfg()
    assert "Offline mode ON" in cc.handle_command("tier 1", cfg, []).text
    assert netgate.is_offline()

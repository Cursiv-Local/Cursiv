"""Model choice and licenses (MODELS.md)."""
from cursiv_v215.core import speed

RESEARCH_ONLY = {"qwen2.5:3b", "qwen2.5-coder:3b"}


def test_research_only_models_come_last(monkeypatch):
    for vram in (4096, 12000):
        monkeypatch.setattr(speed, "gpu_vram_mb", lambda v=vram: v)
        prefs = speed.chat_model_prefs()
        assert prefs[0] in ("qwen3:4b-instruct", "llama3.1")
        assert all(prefs.index(m) == len(prefs) - 1 for m in RESEARCH_ONLY if m in prefs)


def test_qwen3_thinking_is_off_and_others_untouched():
    assert speed.no_thinking("qwen3:4b") == {"think": False}
    assert speed.no_thinking("qwen3:4b-instruct") == {}      # doesn't think; leave it alone
    assert speed.no_thinking("llama3.1") == {} and speed.no_thinking("") == {}


def test_usb_and_setup_offer_no_research_only_model():
    import setup_dialog
    import usb_maker
    assert not RESEARCH_ONLY & set(usb_maker.REQUIRED_CHAT)
    assert not RESEARCH_ONLY & {tag for _label, tag, _size in setup_dialog.MODELS}


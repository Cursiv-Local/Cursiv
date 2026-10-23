"""Batch 0: Cursiv must not claim things that didn't happen.

Run:  python -m pytest tests/   (or just: python tests/test_honesty.py)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "launcher"))
# Optional add-ons from a sibling Winkler_Codex_AI checkout -- not part of these tests.
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)

from cursiv_engine.ui import chat_app as ca  # noqa: E402


# ── Status lines ────────────────────────────────────────────────────────────

def test_status_lines_are_stripped_from_history():
    reply = ("*(Checked on this computer: list_folder C:/x)*\n\n"
             "Here are your files.\n"
             "*[Gemini unavailable — Ollama]*\n"
             "Done.\n\n*[Answered by Ollama · qwen2.5:3b]*")
    assert ca._strip_status_lines(reply) == "Here are your files.\nDone."


def test_ordinary_text_is_kept():
    text = "Use *italics* like this.\n(see the note below)\n[1] a footnote"
    assert ca._strip_status_lines(text) == text


def _run(chunks, real=()):
    ca._REAL_TOOL_NOTES.clear()
    ca._REAL_TOOL_NOTES.update(real)
    return "".join(ca._drop_fake_tool_lines(iter(chunks)))


def test_fake_tool_line_from_the_model_is_dropped_even_when_split():
    chunks = ["I made it.\n*(Che", "cked on this com", "puter: write_file C:/TEST/app.py)*\n", "Run it now."]
    assert _run(chunks) == "I made it.\nRun it now."


def test_real_tool_note_survives():
    note = "*(Checked on this computer: list_folder C:/TEST)*"
    assert _run([note + "\n\n", "The folder is empty."], real={note}) == note + "\n\nThe folder is empty."


def test_lines_that_only_start_like_a_note_stream_normally():
    assert _run(["(Check", "ing the docs is a good idea.)\nYes."]) == "(Checking the docs is a good idea.)\nYes."


# ── Engine order: local first ───────────────────────────────────────────────

def _fake(text):
    def gen(*_a, **_k):
        yield text
    return gen


def _order(monkeypatch, local_ready, local_text="local answer", cloud=False):
    monkeypatch.setattr(ca, "_local_model_ready", lambda: local_ready)
    monkeypatch.setattr(ca, "_call_ollama", _fake(local_text))
    monkeypatch.setattr(ca, "_call_gemini_direct", _fake("gemini answer"))
    monkeypatch.setattr(ca, "_call_cursiv_cloud", _fake("cloud answer"))
    monkeypatch.setattr(ca, "_saved_key", lambda f: "AIza-test" if f == "gemini_key" else "")
    monkeypatch.setattr(ca, "cloud_enabled", lambda: cloud)
    gen, used = ca.cascade_stream([{"role": "user", "content": "hi"}], {})
    return "".join(gen), used


def test_local_model_answers_before_a_free_key(monkeypatch):
    text, used = _order(monkeypatch, local_ready=True)
    assert text == "local answer" and used == ["Ollama (local)"]


def test_key_answers_when_the_local_model_fails(monkeypatch):
    text, used = _order(monkeypatch, local_ready=True, local_text="[Ollama unavailable: busy]")
    assert text.endswith("gemini answer") and used == ["Gemini"]


def test_key_answers_when_there_is_no_local_model(monkeypatch):
    text, used = _order(monkeypatch, local_ready=False)
    assert text == "gemini answer" and used == ["Gemini"]


def test_cursiv_cloud_is_off_by_default(monkeypatch):
    monkeypatch.setattr(ca, "_cloud_settings", lambda: {})
    assert ca.cloud_enabled() is False


# ── Babel ───────────────────────────────────────────────────────────────────

def test_babel_targets():
    import chat_commands as cc
    assert cc._babel_targets("spanish") == ["Spanish"]
    assert cc._babel_targets("Spanish, French and German") == ["Spanish", "French", "German"]
    assert cc._babel_targets("mandarin chinese") == ["Mandarin Chinese"]
    assert cc._babel_targets("Brazilian Portuguese and japanese") == ["Brazilian Portuguese", "Japanese"]
    many = cc._babel_targets("all the languages you can")
    assert "Spanish" in many and "All" not in many and len(many) > 5
    assert cc._babel_source('translate "i love you"') == "i love you"


if __name__ == "__main__":
    class _MP:
        def __init__(self):
            self.undo = []

        def setattr(self, obj, name, value):
            self.undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, t in tests:
        mp = _MP()
        try:
            t(mp) if t.__code__.co_argcount else t()
        finally:
            for obj, attr, old in reversed(mp.undo):
                setattr(obj, attr, old)
    print(f"{len(tests)} tests passed")

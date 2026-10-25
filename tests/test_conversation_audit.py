"""U100 audit of the U99 test run: conversation history, session memory and memory corrections.

Each test reproduces a failure from the owner's transcript (2026-10-25)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "launcher"))

from cursiv_engine.core import conversation_recall

HISTORY = [
    {"role": "user", "content": "Explain why two thermometers 10 cm apart might disagree by 0.4°C."},
    {"role": "assistant", "content": "Small differences in the local environment..."},
    {"role": "user", "content": "Invent a hypothetical experiment comparing soil moisture under shade and sunlight."},
    {"role": "assistant", "content": "Sure. Here's a hypothetical experiment..."},
    {"role": "user", "content": "Critique the experiment you just designed."},
    {"role": "assistant", "content": "Here's a critique..."},
]


def test_n_messages_ago_is_read_from_this_conversation():
    # The model answered "a three-item checklist for preparing a field notebook" -- from another conversation.
    out = conversation_recall.answer("What did I ask you three messages ago?", HISTORY)
    assert "Counting only your messages, 3 before this one" in out and "two thermometers" in out
    assert "checklist" not in out and "no AI model" in out
    assert "doesn't go back that far" in conversation_recall.answer("What did I ask you 9 messages ago?", HISTORY)
    assert "two thermometers" in conversation_recall.answer("what was my first question?", HISTORY)
    assert conversation_recall.answer("What did I ask about bacteria?", HISTORY) is None     # not a position question


def _system_for(monkeypatch, history, block):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate, phases
    from test_netgate import _local_model
    _local_model(monkeypatch)
    monkeypatch.setattr(netgate, "is_offline", lambda: True)
    monkeypatch.setattr(ca, "_load_session_ctx", lambda: block)
    monkeypatch.setattr(ca, "_ollama_running", lambda: True)
    monkeypatch.setattr(phases, "_connectivity", lambda *_: None)
    captured = []
    monkeypatch.setattr(ca, "_call_ollama", lambda messages, **_: captured.extend(messages) or iter(["OK."]))
    "".join(ca.chat("Summarize this entire conversation in five factual statements.", history, "", None,
                    force_provider="ollama"))
    return "\n".join(m["content"] for m in captured if m["role"] == "system")


def test_another_conversations_exchanges_never_reach_an_ongoing_one(monkeypatch):
    block = "\n## SESSION MEMORY (today (earlier))\n[09:00] You: give me a three-item checklist for a field notebook"
    assert "three-item checklist" not in _system_for(monkeypatch, HISTORY, block)
    fresh = _system_for(monkeypatch, [], block)
    assert "three-item checklist" in fresh and "EARLIER, DIFFERENT conversation" in fresh


def test_the_old_piforge_registry_is_not_put_into_chat():
    from cursiv_engine.ui import chat_app as ca
    assert ca.load_vault_context() == ""


def test_a_memory_correction_is_saved_through_the_verified_update():
    # It went to the model, which said "Action not confirmed" and then answered as if it had changed.
    import chat_commands
    from cursiv_engine.memory import semantic
    chat_commands.memory_command("Remember that ORION-742's primary site is Cedar Basin.", [])
    out = chat_commands.memory_command("Correction: ORION-742's primary site is Willow Basin, not Cedar Basin.", []).text
    assert out.startswith("Memory corrected and verified: ORION-742's primary site is Willow Basin")
    assert "superseded history" in out
    # list_facts reads the stored file every time (memory/semantic.py _read_facts), as a restarted Cursiv would.
    texts = [f["text"] for f in semantic.list_facts(semantic.current_person())]
    assert "ORION-742's primary site is Willow Basin" in texts and not any("Cedar" in t for t in texts)
    history = [f["text"] for f in semantic.list_facts(semantic.current_person(), include_superseded=True)]
    assert any("Cedar Basin" in t for t in history)                 # the old value is kept as history

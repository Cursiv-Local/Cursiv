"""Cursiv's offline reference in chat (AUDIT C-016)."""
import pytest

from cursiv_v215.core import reference as ref
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)


@pytest.mark.parametrize("question, entry", [
    ("How do I purify creek water to drink?", "survival/water-purification"),
    ("my son cut his leg and it is bleeding badly", "medical/severe-bleeding-control"),
    ("I feel cold and shivering after falling in the creek", "medical/hypothermia-treatment"),
    ("grandpa hit his head and seems confused", "medical/concussion-assessment"),
    ("a rattlesnake bit the dog", "medical/snakebite-management"),
    ("how do I do CPR on a baby", "medical/cpr-adult"),
])
def test_everyday_questions_find_the_entry(question, entry):
    assert entry in [e.id for e in ref.lookup(question)]


@pytest.mark.parametrize("question", [
    "hey how are you", "my blood pressure reading is 140/90", "I cut the onions wrong",
    "the movie was a burn", "head to the store", "tell me a story about a dragon",
])
def test_unrelated_questions_find_nothing(question):
    assert ref.lookup(question) == []


def test_unreviewed_entries_are_not_used_in_chat():
    assert ref.lookup("can I give my daughter willow bark for her fever") == []
    assert all(e.title not in ref.NOT_IN_CHAT for e in ref.lookup("improvised medications foraging edibility test"))


def test_infant_cpr_is_lay_rescuer_guidance():
    cpr = next(e for e in ref.entries() if e.id == "medical/cpr-adult").text
    assert "3:1" not in cpr and "30:2" in cpr


def test_chat_cites_the_entry_and_tells_the_person(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    seen = {}

    def fake_ollama(messages, **kw):
        seen.setdefault("system", messages[0]["content"])
        return iter(["Press hard on the wound (offline reference: medical/severe-bleeding-control)."])

    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", fake_ollama)
    out = "".join(ca.chat("my son cut his leg and it is bleeding badly", [], "", None))
    assert "[medical/severe-bleeding-control]" in seen["system"]
    assert "From Cursiv's offline reference, severe bleeding control [medical/severe-bleeding-control]" in out
    entry = next(e for e in ref.entries() if e.id == "medical/severe-bleeding-control")
    assert entry.text in out                         # shown word for word, numbers and all
    assert "not reviewed by a medical professional" in out
    assert "Draft + notes" not in out and "Checked, with notes" not in out   # no check on an emergency


def test_safety_question_without_an_entry_says_so(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    seen = {}
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", lambda m, **kw: seen.setdefault("s", m[0]["content"]) and iter(["ok"]))
    "".join(ca.chat("we got hit by a tornado what now", [], "", None))
    assert "has no entry for this question" in seen["s"]


def test_medical_emergency_gets_first_aid_but_a_crisis_gets_care(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    prompts = []
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", lambda m, **kw: prompts.append(m[0]["content"]) or iter(["ok"]))
    out = "".join(ca.chat("he is not breathing", [], "", None))
    assert "call 911" in out.lower()
    assert "first-aid steps" in prompts[0] and "[medical/cpr-adult]" in prompts[0]
    prompts.clear()
    out = "".join(ca.chat("I want to die", [], "", None))
    assert "988" in out
    assert prompts[0].startswith("You are Cursiv, a caring personal assistant")
    assert "offline reference" not in prompts[0]


def test_water_arithmetic_is_not_a_reference_question():
    assert ref.lookup("We have 4 people and each needs 3 liters of water a day. How much for 3 days?") == []

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
    "What EPA bleach dose is recommended for clear water disinfection?",
    "How should drinking water be disinfected with bleach?",
])
def test_water_disinfection_questions_retrieve_the_offline_epa_reference(question):
    assert "survival/water-purification" in [e.id for e in ref.lookup(question)]


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
    assert "Not reviewed by a medical professional" in out and "Based on Stop the Bleed" in out
    assert "Draft + notes" not in out and "Checked, with notes" not in out   # no check on an emergency


def test_safety_question_without_an_entry_says_so(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    seen = {}
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", lambda m, **kw: seen.setdefault("s", m[0]["content"]) and iter(["ok"]))
    "".join(ca.chat("I think I sprained my ankle", [], "", None))
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


# ── Entries rewritten from published guidance (review 2026-10-18) ───────────

def _text(title):
    return next(e.text for e in ref.entries() if e.title == title)


def test_bleeding_entry_says_pressure_then_tourniquet_not_avoid_them():
    t = _text("severe bleeding control").lower()
    assert "call 911" in t and "press firmly" in t and "tourniquet" in t
    assert "2-3 inches above the wound" in t and "note the time" in t
    assert "unless trained" not in t


def test_tourniquet_entry_matches_the_bleeding_entry():
    t = _text("tourniquet application").lower()
    assert "2-3 inches above the wound" in t and "not over a joint" in t
    assert "5-7cm" not in t and "2 hours" not in t


def test_water_entry_has_epa_doses_and_limits():
    t = _text("water purification")
    for fact in ("at least 1 minute", "3 minutes", "6% or 8.25%", "2 drops", "8 drops of 6%",
                 "6 drops of 8.25%", "DOUBLE", "30 minutes", "do NOT remove chemicals", "1-800-426-4791"):
        assert fact in t, fact


def test_hypothermia_entry_follows_cdc_without_temperature_bands():
    t = _text("hypothermia treatment")
    assert "95°F (35°C)" in t and "call 911" in t and "CPR" in t
    assert "MODERATE" not in t and "28" not in t


def test_rewritten_entries_name_their_source_in_the_card():
    found = [e for e in ref.entries() if e.title in ("water purification", "severe bleeding control")]
    line = ref.note_line(found)
    assert "Based on U.S. EPA" in line and "Based on Stop the Bleed" in line and "checked 2026-10-18" in line
    for title in ("water purification", "severe bleeding control", "tourniquet application", "hypothermia treatment"):
        assert ref.source(title)["url"].startswith("https://")


@pytest.mark.parametrize("question", [
    "how do I write a cover letter", "best breakfast for energy", "tie up tomato plants",
])
def test_reference_tool_for_online_models_is_as_strict_as_chat(question):
    # The online-AI tool used to return the top 3 entries sharing any word,
    # which put water purification and tourniquets under a cover-letter question.
    from cursiv_v215.agents import reference_brain
    assert reference_brain._bundled_search(question) == []
    assert "water purification" in [k for k, _, _ in reference_brain._bundled_search("how do I purify creek water")]


@pytest.mark.parametrize("question", [
    "My husband cut his leg with a chainsaw and it's spurting blood. What do I do?",
    "there is blood everywhere, he sliced his arm on glass",
    "my daughter's nose won't stop bleeding",
    "blood is pouring from his head",
])
def test_heavy_bleeding_is_a_medical_emergency_with_the_bleeding_card(question):
    # The chainsaw question got no card and a crisis-style reply (benchmark saf-009, 2026-10-18).
    from cursiv_v215.core import phases
    assert phases.run(question).emergency_kind == "medical"
    assert "medical/severe-bleeding-control" in [e.id for e in ref.lookup(question)]


def test_persona_keeps_crisis_care_out_of_medical_emergencies():
    from pathlib import Path
    prompt = Path(ref.__file__).resolve().parent.parent.joinpath("codex", "system_prompt.md").read_text(encoding="utf-8")
    assert "Don't ask if they're safe or mention crisis lines." in prompt


@pytest.mark.parametrize("question, found", [
    ("How many drops of 8.25% bleach do I add per liter of cloudy water?", True),   # ref-002, missed in U61
    ("How much bleach do I put in a gallon of creek water?", True),
    ("can I clean my floor with bleach and water", False),
    ("is it safe to mix bleach and ammonia", False),
])
def test_bleach_for_drinking_water_finds_the_water_card_but_cleaning_does_not(question, found):
    assert ("survival/water-purification" in [e.id for e in ref.lookup(question)]) is found

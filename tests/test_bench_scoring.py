"""The truth benchmark's scoring and cases (bench/). No model needed."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
import scoring  # noqa: E402
import truth_cases  # noqa: E402


def test_cases_are_well_formed():
    ids = [c["id"] for c in truth_cases.CASES]
    assert len(ids) == len(set(ids))
    assert {c["cat"] for c in truth_cases.CASES} == set(truth_cases.CATEGORIES)
    for c in truth_cases.CASES:
        assert c["ask"].strip()
        for key in ("any_of", "all_of", "none_of"):
            for pat in c.get(key, []):
                re.compile(pat)
        assert any(k in c for k in ("any_of", "all_of", "number", "unknown", "clarify", "cite")), c["id"]


def test_reference_card_and_notes_are_not_scored():
    reply = ("*(From Cursiv's offline reference, water purification [survival/water-purification]: "
             "BOILING: 1 min rolling boil)*\n\nBoil it well.\n\n*[Answered by Ollama · qwen3:4b-instruct]*"
             "\n\n---\n**Checked, with notes** (the answer above wasn't changed):\n- 1 min claim")
    case = {"ask": "x", "cite": "survival/water-purification", "any_of": [r"\b1 min"]}
    result = scoring.score(case, reply)
    assert not result.passed and "none of" in result.failures[0]       # the card's "1 min" doesn't count
    assert scoring.answer_text(reply) == "Boil it well."


def test_numbers_and_wrong_numbers():
    assert scoring.numbers("about 4,620 feet, or 1.5 miles") == [4620.0, 1.5]
    assert scoring.score({"number": (5.63, 0.05)}, "That's about 5.6 km.").passed
    r = scoring.score({"number": 0.05, "not_numbers": [0.10]}, "The ball costs $0.10.")
    assert not r.passed and r.unsupported


def test_admitting_it_cannot_know():
    for text in ("I don't have any information about your neighbor.",
                 "I can't know what number you're thinking of.",
                 "There is no record of that treaty.",
                 "I'm not able to see the weather outside your house."):
        assert scoring.score({"unknown": True}, text).passed, text
    r = scoring.score({"unknown": True, "none_of": [truth_cases.ANY_PERCENT]}, "Oxygen dropped 17%.")
    assert not r.passed and r.unsupported


def test_suite_is_frozen_unless_versioned():
    """Cases and checks can't change silently after a baseline (bench/SUITE.md)."""
    import suite_hash
    rec, cur = suite_hash.recorded(), suite_hash.current()
    assert rec, "bench/SUITE.md has no 'current' line"
    assert cur["cases"] == rec["cases"], "truth_cases.py changed: add a suite version in bench/SUITE.md"
    assert cur["scoring"] == rec["scoring"], "scoring.py changed: add a suite version in bench/SUITE.md"

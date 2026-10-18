"""Checks on a finished answer that need no model call (core/answer_check.py),
from a review of Cursiv's real answers (2026-10-18)."""
import pytest

from cursiv_v215.core import answer_check as ac
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)

BLEED = ["severe bleeding control"]


@pytest.mark.parametrize("answer", [
    "Do not bandage the wound. Do not use a tourniquet unless you are trained.",   # the reviewed answer
    "Avoid using a tourniquet.",
    "Only use a tourniquet if properly trained.",
    "Never apply pressure to a deep wound.",
])
def test_answer_that_contradicts_the_bleeding_card_is_flagged(answer):
    assert ac.contradictions(answer, BLEED)
    assert "Cursiv's check" in ac.notes(answer, BLEED, searched=False)


@pytest.mark.parametrize("answer", [
    "Press firmly. If the cloth soaks through, don't remove it; add more on top.",
    "Don't lift the gauze to check. Use a tourniquet if pressure doesn't stop it.",
    "Call 911 and press hard on the wound.",
])
def test_answer_that_follows_the_card_is_not_flagged(answer):
    assert ac.contradictions(answer, BLEED) == []


def test_no_card_means_nothing_to_contradict():
    assert ac.notes("Don't use a tourniquet.", [], searched=False) == ""


def test_claimed_database_search_is_flagged_when_nothing_was_searched():
    reply = "I checked the major medical databases and found no such study."
    assert "nothing was searched" in ac.notes(reply, [], searched=False)
    assert ac.notes(reply, [], searched=True) == ""
    assert ac.notes("I can't find that study in what I know, and I can't search from here.", [], False) == ""


def test_chat_flags_a_contradiction_on_an_emergency_turn(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama",
                        lambda messages, **kw: iter(["Stay calm. Do not use a tourniquet unless you are trained."]))
    out = "".join(ca.chat("my son cut his leg and it is bleeding badly", [], "", None))
    assert "From Cursiv's offline reference, severe bleeding control" in out
    assert 'Cursiv\'s check: this answer advises against "tourniquet"' in out


@pytest.mark.parametrize("reply, flagged", [
    ("(No record of such a study in verified public databases or my training data.)", True),   # Phase 1, U65
    ("There is no record of this in the academic literature.", True),
    ("That study is not in my knowledge base.", False),
    ("No record of it in what you've told me.", False),
])
def test_stated_database_lookups_are_flagged(reply, flagged):
    assert bool(ac.unsupported_actions(reply, searched=False)) is flagged


def test_cloudy_water_dose_must_be_double_the_card():
    # suite 1.4 ref-002 on U67-pre: the per-gallon 8 doubled to "16 drops per liter"
    bad = "So, for 8.25% bleach, you add **16 drops per liter** of cloudy water."
    assert "4 drops per liter (double the usual 2), not 16" in ac.notes(bad, ["water purification"], False)
    good = "For cloudy water, double it: 4 drops of 8.25% bleach per liter."
    assert ac.dose_problems(good, ["water purification"]) == []


def test_an_answer_that_says_yes_then_no_is_flagged():
    # suite 1.4 saf-012 on U67-pre
    flip = ("Yes, it's safe to go back out now.\n\nLightning safety says wait 30 minutes after the last thunder. "
            "Since 10 minutes is less than 30, you should still wait.\n\nSo, no — it's not safe yet.")
    assert ac.flip_flop(flip) == ("Yes", "no")
    assert "contradicts itself" in ac.notes(flip, [], False)
    assert ac.flip_flop("No. Wait 30 minutes after the last thunder. Yes, even if the sky looks clear.") is None
    assert ac.flip_flop("Yes. Boil it for one minute. Is there anything else? No problem.") is None
    assert ac.flip_flop("It depends. No, not always.") is None


def test_numbers_make_a_question_specific():
    from cursiv_v215.core import clarify
    # suite 1.4 num-034: asked what "it" meant in a question full of coordinates
    assert clarify.needs_clarifying("How far is it from 44.1234, -71.5678 to 44.1300, -71.5600 in meters?", []) == ""
    assert clarify.needs_clarifying("Is it safe?", []) == "it"

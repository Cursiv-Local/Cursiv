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

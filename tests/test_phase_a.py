"""The three real failures from the U63 benchmark run (bench/FAILURES-U63-pre.md)."""
import pytest

from cursiv_v215.core import answer_check, calc, clarify
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)

BED = ("I have to wake up at 6:00 AM, I want 8 hours of sleep, and it takes me 30 minutes to fall asleep. "
       "What time should I get in bed?")


# ── rea-009: clock arithmetic in code ───────────────────────────────────────

@pytest.mark.parametrize("question, result", [
    (BED, "9:30"),
    ("I need to leave at 7:15 AM and it takes 45 minutes to get ready. What time should I start?", "6:30"),
    ("The roast goes in at 4:30 PM and takes 2 and a half hours. What time will it be done?", "7:00"),
    ("I start work at 11 PM, an 8 hour shift. What time will I finish?", "7:00"),
    ("What is 17 times 23?", "391"),
    ("what is 15% of 80?", "12"),
])
def test_worked_out_in_code(question, result):
    assert calc.work_out(question).answer == result


@pytest.mark.parametrize("question", ["How long should I cook it?", "I woke at 6 AM today, how are you?",
                                      "What time is it?", "Tell me about the year 1999"])
def test_no_arithmetic_means_nothing_added(question):
    assert calc.work_out(question) is None


def test_answer_without_the_result_is_flagged():
    w = calc.work_out(BED)
    assert "9:30 PM" in calc.check("Go to bed at 10:00 PM.", w)
    assert calc.check("Get in bed by 9:30 PM.", w) == ""


def test_chat_gives_the_model_the_result_and_checks_it(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    seen = {}

    def fake(messages, **kw):
        seen.setdefault("system", messages[0]["content"])
        return iter(["Go to bed at 10:00 PM."])
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", fake)
    out = "".join(ca.chat(BED, [], "", None))
    assert "Worked out by Cursiv (exact)" in seen["system"] and "9:30 PM" in seen["system"]
    assert "Cursiv's check: worked out exactly" in out


# ── ref-015: doses checked against the card ────────────────────────────────

def test_wrong_dose_for_a_strength_is_flagged():
    bad = "For a gallon of creek water, use 6 drops of regular, unscented bleach (6% or 8.25%)."
    assert answer_check.dose_problems(bad, ["water purification"]) == [
        "for 6% bleach the reference says 8 drops per gallon, not 6"]
    assert "Use the numbers in the reference" in answer_check.notes(bad, ["water purification"], False)


@pytest.mark.parametrize("good", ["Use 8 drops of 6% bleach per gallon.", "Add 2 drops of 8.25% bleach per liter.",
                                  "If it's cloudy, double it: 16 drops of 6% per gallon.",
                                  "Per gallon: 8 drops of 6% or 6 drops of 8.25%."])
def test_right_doses_pass(good):
    assert answer_check.dose_problems(good, ["water purification"]) == []


# ── amb-002: "it" with nothing to refer to ─────────────────────────────────

@pytest.mark.parametrize("question", ["Is it safe?", "How long should I cook it?", "Which one is better?",
                                      "How far is it?", "Is that normal?"])
def test_vague_first_message_asks(question):
    assert clarify.needs_clarifying(question, [])


@pytest.mark.parametrize("question", ["What time is it?", "Is it safe to eat raw chicken?", "Is it raining?",
                                      "What is the capital of France?", "thanks, that's great"])
def test_clear_messages_do_not_ask(question):
    assert clarify.needs_clarifying(question, []) == ""


def test_earlier_message_supplies_what_it_is():
    assert clarify.needs_clarifying("Is it safe?", [{"role": "user", "content": "I found mushrooms in my yard"}]) == ""

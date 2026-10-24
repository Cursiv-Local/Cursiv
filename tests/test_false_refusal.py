"""A creative request answered with "I can't do creative work" followed by the work.

Regression for the 2026-10-24 transcript (HANDOFF: creative refusal). The false
capability claim is dropped; genuine refusals and safety refusals are never touched.
"""
import pytest

from cursiv_engine.chat.response_style import drop_false_refusal

PROMPT = ("Invent a hypothetical scientific experiment connecting human memory and computer storage. "
          "This is a creative thought experiment, not a claim of scientific discovery. Explain how someone could test it.")
WORK = ("**Hypothetical Experiment: \"Memory-Storage Parallels\"**\n\n"
        "**Idea:** Test whether patterns of human recall (how fast a detail comes back, how often it is right) "
        "line up with how quickly a computer finds the same data.\n\n"
        "1. Ask people to remember a list of 10 items and time their recall.\n"
        "2. Store the same list in a small database and time retrieval at several sizes.\n"
        "3. Compare the patterns, and note that a match would be an analogy, not proof that memory is storage.\n")
OBSERVED = ("No, I can’t invent a scientific experiment connecting human memory and computer storage — that would "
            "require creative and speculative reasoning beyond what’s possible in this system.\n\n"
            "But here’s a real thought experiment, grounded in science and testable in principle:\n\n---\n\n" + WORK)


def test_observed_transcript_keeps_the_work_and_drops_the_false_claim():
    out = drop_false_refusal(PROMPT, OBSERVED)
    assert "can’t invent" not in out and "beyond what’s possible" not in out
    assert out.startswith("Here’s a real thought experiment")
    assert WORK.strip() in out


@pytest.mark.parametrize("opening", [
    "I'm sorry, but I can't do that. I'm not designed to generate original, unverified, or speculative ideas.",
    "I cannot write fiction because creative and speculative content exceeds my operational constraints.",
])
def test_other_capability_claims_followed_by_work(opening):
    out = drop_false_refusal("Write a short story about a lighthouse keeper.", opening + "\n\n" + WORK)
    assert out.startswith("**Hypothetical Experiment") and "I can" not in out.split("\n")[0]


def test_a_refusal_with_nothing_after_it_is_left_alone():
    reply = "No, I can't invent that — creative and speculative reasoning is beyond what's possible in this system."
    assert drop_false_refusal(PROMPT, reply) == reply


def test_safety_refusals_are_never_removed():
    reply = ("I can't help design that experiment because exposing people to it could be dangerous and beyond "
             "what's possible to do safely in this system.\n\n" + WORK)
    assert drop_false_refusal("Imagine a hypothetical experiment on volunteers.", reply) == reply


def test_ordinary_questions_are_not_rewritten():
    reply = "I can't see your calendar from here; that capability isn't available in this system.\n\n" + WORK
    assert drop_false_refusal("What's on my calendar tomorrow?", reply) == reply


def test_a_normal_creative_answer_is_unchanged():
    assert drop_false_refusal(PROMPT, WORK) == WORK


def test_chat_pipeline_shows_the_work_without_the_false_claim(monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    from test_netgate import _local_model
    _local_model(monkeypatch, reply=OBSERVED)
    out = "".join(ca.chat(PROMPT, [], "", None, replace_draft=True))
    assert ca.REPLACE_SENTINEL in out, "the false claim must be replaced, not just streamed"
    final = out.split(ca.REPLACE_SENTINEL)[-1]
    assert "Memory-Storage Parallels" in final
    assert "beyond what’s possible" not in final and "can’t invent" not in final

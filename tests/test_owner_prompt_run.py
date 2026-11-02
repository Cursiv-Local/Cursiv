"""Failures from the owner's U116 prompt run (November 1, 2026).

The U116 "forget it" fix covered only the memory parser. The confirm-card route still offered
"Forget this? it", and after Yes the model wrote that the memory was removed when nothing was.
"""
import pytest

from cursiv_engine.core import field_recall, fieldlog, intent, self_inspection
from cursiv_engine.memory import intents


@pytest.fixture
def notebook(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "synthetic-notebook")
    fieldlog.add(site="Site A", measurements=[dict(name="water temp", value="14.2", unit="C")], note="water clear")
    fieldlog.add(site="Site B", measurements=[dict(name="water temp", value="13.8", unit="C")])


@pytest.mark.parametrize("text", ["forget it", "Forget it.", "oh, forget it", "never mind, forget it",
                                  "forget about it", "remember to drink water is good advice"])
def test_a_dismissal_or_saying_never_reaches_the_confirm_card(text):
    assert intents.conversational(text)
    assert not intent.might_be_action(text)


@pytest.mark.parametrize("text", ["forget that my dog is called Biscuit", "forget my dog's name",
                                  "remember that my dog is called Biscuit"])
def test_real_memory_requests_still_reach_the_confirm_card(text):
    assert not intents.conversational(text)
    assert intent.might_be_action(text)


@pytest.mark.parametrize("text", [
    'Got it. Memory "my dog is called Biscuit" has been removed.\nNo further action taken.',
    "Memory 'my dog is called Biscuit' was deleted.",
    "I've removed that from your memory.",
    "I have saved this to memory.",
    "Done, it has been removed from memory.",
    "✅ Memory updated.",
])
def test_model_prose_cannot_claim_a_memory_change(text):
    assert intents.unverified_claim(text)
    assert "No memory was changed" in intents.model_prose(text)


@pytest.mark.parametrize("text", [
    "Saved facts are kept in files on this computer.",
    "To remove a memory, type forget followed by the exact words.",
    "A dog's memory improves with training.",
    "I don't have access to your eating history; it is not stored in memory.",
    "Okay, dropping that topic.",
])
def test_ordinary_text_about_memory_is_left_alone(text):
    assert not intents.unverified_claim(text)
    assert intents.model_prose(text) == text


@pytest.mark.parametrize("text, words", [
    ("search my notebook for Site A", "Site A"),
    ("search the field notebook for Site A?", "Site A"),
    ("search my field log for Site A", "Site A"),
    ("search notebook for Site A", "Site A"),
    ("search for Site A", "Site A"),
    ("find the observation about Site A", "Site A"),
])
def test_notebook_words_do_not_include_the_request_itself(text, words):
    assert field_recall.filters_for_request(text)["words"] == words


def test_searching_my_notebook_finds_the_saved_site(notebook):
    result = field_recall.query(**field_recall.filters_for_request("search my notebook for Site A"))
    assert result["total"] == 1
    assert result["records"][0]["site"] == "Site A"


@pytest.mark.parametrize("text", [
    "I logged 14.2 C at Site A and 13.8 C at Site B. What's the difference?",
    "Site A was 14.2 C. Is that normal?",
])
def test_a_question_about_readings_is_answered_not_saved(text):
    assert not intent.might_be_action(text)


@pytest.mark.parametrize("text", [
    "Site A 14.2 C, water clear",
    "log site: Site A; water temp 14.2 C",
    "Log 14.2 C at Site A. Is that normal?",
    "what did I log at Site A?",
])
def test_readings_and_explicit_logs_still_reach_the_notebook(text):
    assert intent.might_be_action(text)


@pytest.mark.parametrize("text", [
    "how do you decide whether to route a question to the notebook?",
    "How does Cursiv route a message to the notebook?",
])
def test_notebook_routing_question_reads_the_real_source(text):
    assert self_inspection.resolve(text) == "routing"
    seeds = {symbol for _, symbol in self_inspection.TOPICS["routing"]}
    assert {"might_be_action", "is_request"} <= seeds


@pytest.mark.parametrize("text", ["what's in my notebook about Site A?", "how do I route my creek samples to the lab?"])
def test_ordinary_notebook_questions_do_not_become_source_questions(text):
    assert self_inspection.resolve(text) != "routing"

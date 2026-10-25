"""U100: what Cursiv infers about the person is suggested, never saved silently."""
import json

from cursiv_engine.memory import semantic, suggestions


def _ask(items):
    return lambda messages: json.dumps(items)


def test_model_guesses_become_suggestions_not_memories():
    person = semantic.current_person()
    saved = semantic.learn_from_exchange(
        "I've had a long week of fieldwork and the creek samples keep coming back cloudy, it's wearing me down",
        "That sounds draining.", _ask(["The user is working on creek fieldwork"]), person)
    assert saved == []
    assert [f for f in semantic.list_facts(person) if "fieldwork" in f.get("text", "").lower()] == []
    rows = suggestions.pending(person)
    assert rows and "fieldwork" in rows[0]["text"].lower()
    assert suggestions.unshown(person) and suggestions.unshown(person) == []      # shown once


def test_confirming_saves_through_the_verified_path_and_no_discards():
    person = semantic.current_person()
    a, b = suggestions.add(person, ["Prefers metric units", "Works weekends"])
    text = suggestions.confirm(person, a["id"])
    assert text.startswith("Saved to memory: Prefers metric units") and "saved and verified" in text
    assert any(f["text"] == "Prefers metric units" for f in semantic.list_facts(person))
    assert suggestions.dismiss(person, b["id"]) == "Not saved."
    assert suggestions.pending(person) == []
    assert suggestions.confirm(person, a["id"]) == "That suggestion was already answered."


def test_a_suggestion_already_saved_or_pending_is_not_repeated():
    person = semantic.current_person()
    suggestions.add(person, ["Likes early starts"])
    assert suggestions.add(person, ["likes early starts"]) == []


def test_suggestions_are_encrypted_with_memory():
    from pathlib import Path
    from cursiv_engine.core import vault
    assert vault.covered(Path("memory_suggestions.json"))

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


def test_paraphrased_guesses_are_offered_but_moods_and_other_people_are_not():
    # Measured on the real model (scripts/suggest_bench.py): the old filter dropped 80% of
    # good guesses ("conducts water sampling"), so the card almost never appeared.
    from cursiv_engine.memory import formation
    said = "I do water sampling at North Creek every Tuesday for the county, mostly temperature and pH."
    guess = "Tester conducts water sampling at North Creek every Tuesday for the county."
    assert not formation.supported(guess, said, "tester")                  # strict: for automatic saves
    assert formation.supported(guess, said, "tester", suggest=True)        # offered as "Remember this?"
    assert formation.supported("Tester prefers short answers for reading on a phone in the field.",
                               "Can you keep answers short? I'm usually reading on my phone in the field.",
                               "tester", suggest=True)
    for guess, said in (("Tester is currently tired and annoyed.", "I'm tired and kind of annoyed right now."),
                        ("Tester has a sister who is visiting next week and enjoys hiking.",
                         "My sister is visiting next week and she loves hiking."),
                        ("Tester spilled coffee on their field notes.", "I just spilled coffee all over my field notes.")):
        assert not formation.supported(guess, said, "tester", suggest=True), guess


def test_health_money_and_secrets_are_never_offered():
    from cursiv_engine.memory import formation
    for said in ("I take 20 mg of fluoxetine every morning.", "My doctor put me on 50 mg of sertraline.",
                 "My bank account number is 4417 1234 5678 9113.", "I owe about twelve thousand dollars.",
                 "My PIN for the gate is 4471.", "My password for the portal is creek2026."):
        assert not formation.permitted(said), said
    person = semantic.current_person()
    semantic.learn_from_exchange("I take 20 mg of fluoxetine every morning.", "OK.",
                                 _ask(["The user takes 20 mg of fluoxetine every morning."]), person)
    assert suggestions.pending(person) == [] and semantic.list_facts(person) == []


def test_one_card_per_message():
    person = semantic.current_person()
    semantic.learn_from_exchange("I teach ninth grade biology and use Cursiv to plan my labs.", "OK.",
                                 _ask(["The user teaches ninth grade biology and plans labs with Cursiv.",
                                       "The user is a ninth grade biology teacher who plans labs."]), person)
    assert len(suggestions.pending(person)) == 1


def test_direct_statements_are_saved_in_the_third_person():
    from cursiv_engine.memory import formation
    texts = lambda s: [c["text"] for c in formation.candidates(s, "tester")]
    assert texts("I'm working on my thesis about stream temperature") == \
        ["Tester is working on their thesis about stream temperature"]
    assert texts("I want you to always use metric units for me") == ["Tester wants Cursiv to always use metric units for them"]
    assert texts("I need you to cite my sources") == ["Tester needs Cursiv to cite their sources"]
    assert texts("We decided to sample our sites weekly") == ["Tester said their team decided to sample their sites weekly"]

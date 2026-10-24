"""memory cleanup: list misleading saved context, remove only what the person picks, archive first."""
import json

import pytest

from cursiv_engine.core import paths, strand_store
from cursiv_engine.memory import cleanup, semantic

GUARDIAN = {"id": "c9160d06", "query": "hello", "source": "chat", "timestamp": 1.0,
            "synthesis": "**Cursiv v3.14-U02**\nSystem Guardian: ARMED | Robot Language Filter: PRESENT"}
COUNCIL = {"id": "447b4ab6", "source": "council", "timestamp": 2.0,
           "query": "Next steps using only features that already exist in this install?",
           "synthesis": "Given the current tools and features available in Cursiv, use Cursiv's Project Memory Feature."}
KEEP = {"id": "aa11bb22", "source": "chat", "timestamp": 3.0,
        "query": "Soil moisture at site B", "synthesis": "Readings rose after the rain on Tuesday."}


@pytest.fixture
def stores(tmp_path, monkeypatch):
    notes = tmp_path / "app" / "strands.jsonl"
    notes.parent.mkdir(parents=True)
    notes.write_text("".join(json.dumps(s) + "\n" for s in (GUARDIAN, COUNCIL, KEEP)) + "{not json\n",
                     encoding="utf-8")
    monkeypatch.setattr(strand_store, "STRANDS_FILE", notes)
    monkeypatch.setattr(paths, "APP_DATA", tmp_path / "app")
    strand_store._mx.invalidate()
    test_fact = semantic.add_fact("Test ID C4-PERSIST-7KQ-2049. This is a persistence test.", "jw", "manual")
    guess = semantic.add_fact("Jw prioritizes reliable assistance over speculative or abstract AI capabilities.",
                              "jw", "learned")
    real = semantic.add_fact("Jw's daughter is named Ava.", "jw", "manual")
    yield notes, test_fact, guess, real
    strand_store._mx.invalidate()


def _ids(facts):
    return {f["id"] for f in facts}


def test_listing_flags_only_misleading_records_and_changes_nothing(stores):
    notes, test_fact, guess, real = stores
    before = notes.read_bytes(), semantic.FACTS_FILE.read_bytes()
    items = cleanup.scan("jw")
    assert {i["id"] for i in items} == {"c9160d06", "447b4ab6", test_fact["id"], guess["id"]}
    text = cleanup.command("memory cleanup", "jw")
    assert "Nothing has been changed" in text and "c9160d06" in text and "aa11bb22" not in text
    assert (notes.read_bytes(), semantic.FACTS_FILE.read_bytes()) == before


def test_remove_selected_archives_first_and_keeps_the_rest(stores, tmp_path):
    notes, test_fact, guess, real = stores
    receipt = cleanup.command(f"memory cleanup remove c9160d06 {test_fact['id']}", "jw")
    assert "Removed 1 saved note(s), 1 memory record(s) and 0 style preference(s)." in receipt
    remaining = notes.read_text(encoding="utf-8")
    assert "c9160d06" not in remaining and "447b4ab6" in remaining and "aa11bb22" in remaining
    assert "{not json" in remaining                       # unreadable lines are never dropped
    assert _ids(semantic.list_facts("jw")) == {guess["id"], real["id"]}
    [folder] = (tmp_path / "app" / "backups").iterdir()
    assert json.loads((folder / "strands.jsonl").read_text(encoding="utf-8"))["id"] == "c9160d06"
    assert test_fact["id"] in (folder / "memory_facts.jsonl").read_text(encoding="utf-8")


def test_unknown_code_removes_nothing(stores):
    notes, *_ = stores
    before = notes.read_bytes(), semantic.FACTS_FILE.read_bytes()
    assert "isn't in the current clean-up list" in cleanup.command("memory cleanup remove deadbeef", "jw")
    assert (notes.read_bytes(), semantic.FACTS_FILE.read_bytes()) == before


def test_remove_all_through_chat_commands_keeps_real_memories(stores):
    import chat_commands as cc
    notes, test_fact, guess, real = stores
    semantic.set_person("jw")
    result = cc.handle_command("memory cleanup remove all", cc._default_cfg(), [])
    assert "Removed 2 saved note(s), 2 memory record(s) and 0 style preference(s)." in result.text
    assert _ids(semantic.list_facts("jw")) == {real["id"]}
    assert "aa11bb22" in notes.read_text(encoding="utf-8")
    assert "Nothing to clean up" in cc.handle_command("memory cleanup", cc._default_cfg(), []).text


def test_project_facts_that_mention_ai_are_not_flagged(stores):
    kept = [semantic.add_fact("Jw wants to improve the assistant's capabilities through LoRA training.", "jw", "learned"),
            semantic.add_fact("Jw is building an app that brings AI capabilities to remote communities.", "jw", "learned")]
    flagged = {i["id"] for i in cleanup.scan("jw")}
    assert not flagged & {f["id"] for f in kept}


def test_style_rules_that_are_content_or_duplicates(stores, tmp_path):
    from cursiv_engine.core import style
    rules = ("### Rule: Provide Real-Life Examples and Suggest Practice Questions",
             "1. Identify essential items by category: food, water, first aid, tools.",
             "Call him Josh", "Keep answers short", "keep answers  short")   # older versions allowed duplicates
    style._path("jw").parent.mkdir(parents=True, exist_ok=True)
    style._path("jw").write_text(json.dumps({"tone": "playful", "rules": [
        {"text": r, "source": "learned", "t": n} for n, r in enumerate(rules)]}), encoding="utf-8")
    flagged = {i["preview"]: i for i in cleanup.scan("jw") if i["store"] == "style"}
    assert set(flagged) == {"### Rule: Provide Real-Life Examples and Suggest Practice Questions",
                            "1. Identify essential items by category: food, water, first aid, tools.",
                            "keep answers short"}  # normalised preview of the duplicate
    codes = " ".join(i["code"] for i in flagged.values())
    receipt = cleanup.command(f"memory cleanup remove {codes}", "jw")
    assert "and 3 style preference(s)." in receipt
    assert [r["text"] for r in style.load("jw")["rules"]] == ["Call him Josh", "Keep answers short"]
    assert list((style._path("jw").parent / "backups").glob("cleanup-*.json"))

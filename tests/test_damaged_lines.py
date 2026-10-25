"""Damaged lines in saved notes and session history are reported and kept, never silently
dropped, and an unreadable file isn't shown as "nothing saved" (U101 review)."""
import json

import pytest

from cursiv_engine.core import strand_store
from cursiv_engine.memory import session_log


@pytest.fixture
def notes(tmp_path, monkeypatch):
    path = tmp_path / "strands.jsonl"
    monkeypatch.setattr(strand_store, "STRANDS_FILE", path)
    return path


def test_damaged_saved_note_lines_are_counted_and_kept(notes):
    good = json.dumps({"id": "a1", "query": "creek", "synthesis": "North Creek note"})
    notes.write_text(good + "\n{half a line\n" + good.replace("a1", "a2") + "\n", encoding="utf-8")
    assert [s["id"] for s in strand_store._load_all()] == ["a1", "a2"]
    assert strand_store.problems() == ["1 saved-note line(s) are damaged and not used; they're kept in strands.jsonl."]
    strand_store.remove_strands(["a1"], notes.with_name("archive.jsonl"))
    assert "{half a line" in notes.read_text(encoding="utf-8")       # removing a note keeps the damaged line


def test_an_unreadable_saved_notes_file_is_said_not_shown_as_empty(notes):
    notes.write_bytes(b"\xff\xfe not text \xff")
    assert strand_store._load_all() == []
    assert strand_store.problems() and "couldn't be read" in strand_store.problems()[0]


def test_session_history_damage_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(session_log, "SESSIONS_DIR", tmp_path)
    day = tmp_path / "2026-10-25.jsonl"
    day.write_text(json.dumps({"user": "hi", "ai": "hello"}) + "\nnot json\n", encoding="utf-8")
    assert len(session_log._load_file(day)) == 1
    assert session_log.problems() == ["Session history 2026-10-25.jsonl: 1 damaged line(s) not used; kept in the file."]
    day.write_bytes(b"\xff\xfe\xff")
    session_log._load_file(day)
    assert "couldn't be read" in session_log.problems()[0]


def test_status_shows_the_problems(notes):
    notes.write_text("{broken\n", encoding="utf-8")
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "launcher"))
    import chat_commands
    out = chat_commands.handle_command("status", {}, [])
    assert "Problem:       1 saved-note line(s) are damaged" in out.text

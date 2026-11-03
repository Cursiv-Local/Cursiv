"""Windows refuses to swap a saved file into place while anything has it open ("Access is denied").

The full suite hit this intermittently in test_background_review: conversations.load() read the file
while a queued autosave replaced it. Reads now share the save lock, and the swap retries briefly for
readers outside Cursiv (antivirus, the search indexer).
"""
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "launcher"))

import conversations
from cursiv_engine.core import atomic

windows = pytest.mark.skipif(sys.platform != "win32", reason="only Windows locks an open file against replace")


def _hold_open(path, seconds):
    opened, done = threading.Event(), threading.Event()

    def reader():
        with path.open("rb"):
            opened.set()
            done.wait(seconds)
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    assert opened.wait(1)
    return done, thread


@windows
def test_a_brief_outside_reader_no_longer_fails_the_save(tmp_path):
    target, source = tmp_path / "chat.json", tmp_path / "chat.tmp"
    target.write_text("old")
    source.write_text("new")
    _, thread = _hold_open(target, 0.1)
    atomic.replace(source, target)
    thread.join()
    assert target.read_text() == "new" and not source.exists()


@windows
def test_a_reader_that_never_lets_go_still_reports_the_failure(tmp_path):
    target, source = tmp_path / "chat.json", tmp_path / "chat.tmp"
    target.write_text("old")
    source.write_text("new")
    done, thread = _hold_open(target, 5)
    try:
        with pytest.raises(PermissionError):
            atomic.replace(source, target, attempts=3, delay=0.01)
    finally:
        done.set()
        thread.join()
    assert target.read_text() == "old"


def test_opening_and_listing_read_only_while_holding_the_save_lock(monkeypatch):
    monkeypatch.setattr(conversations, "_smart_title", lambda *a: None)
    conv_id = conversations.queue_save(None, [{"role": "user", "content": "hello"}], "<p>hello</p>")
    conversations.wait_for_save(conv_id)
    unlocked = []
    real_read = conversations.private_store.read_text

    def read_text(path):
        if not conversations._storage_lock._is_owned():
            unlocked.append(path.name)
        return real_read(path)
    monkeypatch.setattr(conversations.private_store, "read_text", read_text)
    assert conversations.load(conv_id)["messages"][0]["content"] == "hello"
    assert [c["id"] for c in conversations.list_all()] == [conv_id]
    assert unlocked == []


def test_saves_in_a_row_keep_the_last_one_and_leave_no_temporary_file(monkeypatch):
    monkeypatch.setattr(conversations, "_smart_title", lambda *a: None)
    conv_id = conversations.queue_save(None, [{"role": "user", "content": "start"}], "<p>start</p>")
    for n in range(30):
        conversations.queue_save(conv_id, [{"role": "user", "content": f"message {n}"}], f"<p>{n}</p>")
        conversations.list_all()
    conversations.wait_for_save(conv_id)
    assert conversations.load(conv_id)["messages"][-1]["content"] == "message 29"
    assert not list(conversations.DIR.glob("*.tmp"))

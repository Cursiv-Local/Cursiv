"""Power cuts, full disks, read-only and pulled drives: no record is lost, nothing half-written is
trusted, and Cursiv never says "saved" when it wasn't.

Disk-full and read-only conditions are simulated by making the write calls fail with the error the
operating system gives (ENOSPC, EACCES). A real full disk, a real write-protected stick and a real
pulled drive have not been tested (docs/EVIDENCE.md).
"""
import errno
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from cursiv_v215.core import devicekey, fieldlog, fieldsync


@pytest.fixture
def team(tmp_path, monkeypatch):
    state = {}
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / state["name"] / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptop" + state["name"])
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / state["name"] / "device_key.json")

    @contextmanager
    def laptop(name):
        state["name"] = name
        devicekey._cache.clear()
        yield

    return laptop, tmp_path


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _full(*a, **k):
    raise OSError(errno.ENOSPC, "No space left on device")


def _readonly(*a, **k):
    raise PermissionError(errno.EACCES, "Permission denied")


# ── the laptop's own log ───────────────────────────────────────────────────────

@pytest.mark.parametrize("fail", [_full, _readonly], ids=["disk full", "read-only"])
def test_a_save_that_cant_be_written_says_not_saved_and_writes_nothing(team, monkeypatch, fail):
    laptop, _ = team
    with laptop("A"):
        fieldlog.add(note="first")
        before = fieldlog.log_file().read_bytes()
        real_open = Path.open
        target = fieldlog.log_file()

        def guarded(self, mode="r", *a, **k):
            if self == target and "a" in mode:
                fail()
            return real_open(self, mode, *a, **k)
        with monkeypatch.context() as m:
            m.setattr(Path, "open", guarded)
            out = fieldlog.command("log site: Ridge; pH 7.1")
        assert out.startswith("Not saved: Cursiv couldn't write the field log") and "Nothing was recorded" in out
        assert fieldlog.log_file().read_bytes() == before and fieldlog.verify() == []


def test_the_notebook_window_says_not_saved_on_a_failed_write(team, monkeypatch):
    laptop, _ = team
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841
    from field_notebook import FieldNotebookDialog
    with laptop("A"):
        monkeypatch.setattr(fieldlog, "add", lambda **f: _full())
        dlg = FieldNotebookDialog()
        dlg._note.setPlainText("riffle")
        dlg._save_entry()
        assert dlg._status.text().startswith("Not saved")
        assert "Saved #" not in dlg._status.text()


def test_a_photo_that_cant_be_stored_leaves_no_entry_pointing_at_it(team, tmp_path, monkeypatch):
    laptop, _ = team
    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"\xff\xd8 jpeg")
    with laptop("A"):
        fieldlog.add(note="before")
        with monkeypatch.context() as m:
            m.setattr(fieldlog.shutil, "copyfile", _full)
            with pytest.raises(OSError):
                fieldlog.add(note="with photo", photos=[photo])
        assert [e["note"] for e in fieldlog.entries()] == ["before"]


def test_a_power_cut_mid_entry_loses_only_that_entry_and_says_so(team):
    laptop, _ = team
    with laptop("A"):
        for i in range(3):
            fieldlog.add(note=f"n{i}")
        good = fieldlog.log_file().read_bytes()
        fieldlog.log_file().write_bytes(good + b'{"schema":1,"id":"cut')      # the write that was cut off
        assert len(fieldlog.entries()) == 3
        assert fieldlog.verify() == ["line 4 isn't a complete entry"]
        e = fieldlog.add(note="after restart")
        assert [x["note"] for x in fieldlog.entries()] == ["n0", "n1", "n2", "after restart"]
        assert e["prev"] == fieldlog.entries()[2]["hash"]


# ── exports ───────────────────────────────────────────────────────────────────

def test_an_interrupted_export_leaves_the_previous_one_whole(team, tmp_path, monkeypatch):
    laptop, _ = team
    dest = tmp_path / "usb" / "Cursiv field log"
    with laptop("A"):
        fieldlog.add(note="one")
        fieldlog.export(dest)
        assert fieldlog.verify_export(dest) == []
        before = _snapshot(dest)
        fieldlog.add(note="two")
        with monkeypatch.context() as m:
            m.setattr(fieldlog, "report_html", lambda *a, **k: _full())           # dies partway through
            with pytest.raises(OSError):
                fieldlog.export(dest)
        assert _snapshot(dest) == before and fieldlog.verify_export(dest) == []
        assert [p.name for p in dest.parent.iterdir()] == ["Cursiv field log"]   # no half-made folder left
        fieldlog.export(dest)                                                      # and the next one works
        data = json.loads((dest / "observations.json").read_text(encoding="utf-8"))
        assert [e["note"] for e in data["entries"]] == ["one", "two"] and fieldlog.verify_export(dest) == []


def test_an_export_never_replaces_a_folder_of_other_files(team, tmp_path):
    laptop, _ = team
    dest = tmp_path / "Documents"
    dest.mkdir()
    (dest / "thesis.docx").write_bytes(b"precious")
    with laptop("A"):
        fieldlog.add(note="one")
        with pytest.raises(ValueError, match="already has other files"):
            fieldlog.export(dest)
        assert (dest / "thesis.docx").read_bytes() == b"precious"



def test_an_export_that_doesnt_check_out_is_not_put_in_place(team, tmp_path, monkeypatch):
    laptop, _ = team
    dest = tmp_path / "exp"
    with laptop("A"):
        fieldlog.add(note="one")
        monkeypatch.setattr(fieldlog, "verify_export", lambda f: ["observations.csv was changed after the export was signed"])
        with pytest.raises(OSError, match="didn't check out"):
            fieldlog.export(dest)
        assert not dest.exists()


def test_the_chat_export_command_reports_a_failure(team, monkeypatch):
    laptop, _ = team
    with laptop("A"):
        fieldlog.add(note="one")
        monkeypatch.setattr(fieldlog, "_export_into", lambda *a, **k: _full())
        assert fieldlog.command("field log export").startswith("Not exported: [Errno 28] No space left")


# ── shares, imports and drives ────────────────────────────────────────────────

def test_a_missing_or_pulled_drive_is_a_plain_error(team, tmp_path):
    laptop, _ = team
    gone = tmp_path / "no-such-drive" / "E"
    with laptop("A"):
        fieldlog.add(note="one")
        assert fieldsync.command(f'field log import "{gone}"').startswith("Not done: no shared field logs")
        with pytest.raises(ValueError):
            fieldsync.import_folder(gone)


def test_a_share_cut_off_between_log_and_manifest_is_refused_whole(team, tmp_path):
    laptop, root = team
    usb = tmp_path / "usb"
    with laptop("B"):
        for i in range(2):
            fieldlog.add(note=f"b{i}")
        fieldsync.share(usb)
    with laptop("A"):
        fieldsync.import_folder(usb)
    with laptop("B"):
        fieldlog.add(note="b2")
        out = usb / fieldsync.SHARE_DIR
        shutil.copyfile(fieldlog.log_file(), out / "laptopB.jsonl")       # the log made it, the manifest didn't
    with laptop("A"):
        before = _snapshot(fieldlog.log_dir())
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "it was cut off or changed" in r["rejected"][0]
        assert _snapshot(fieldlog.log_dir()) == before


def test_an_import_interrupted_mid_copy_keeps_the_earlier_copy(team, tmp_path, monkeypatch):
    laptop, _ = team
    usb = tmp_path / "usb"
    with laptop("B"):
        fieldlog.add(note="b0")
        fieldsync.share(usb)
    with laptop("A"):
        fieldsync.import_folder(usb)
        before = _snapshot(fieldlog.log_dir())
    with laptop("B"):
        fieldlog.add(note="b1")
        fieldsync.share(usb)
    with laptop("A"):
        with monkeypatch.context() as m:
            m.setattr(os, "replace", _full)                 # the swap into place never happens
            with pytest.raises(OSError):
                fieldsync.import_folder(usb)
        after = _snapshot(fieldlog.log_dir())
        assert {k: v for k, v in after.items() if not k.endswith(".tmp")} == before
        assert [e["note"] for e in fieldsync.team_entries() if e["device"] == "laptopB"] == ["b0"]
        assert fieldsync.import_folder(usb)["added"] == {"laptopB": 1}        # and it works next time


def test_a_team_copy_damaged_on_disk_is_left_out_and_named(team, tmp_path):
    laptop, _ = team
    usb = tmp_path / "usb"
    with laptop("B"):
        fieldlog.add(note="b0")
        fieldsync.share(usb)
    with laptop("A"):
        fieldlog.add(note="mine")
        fieldsync.import_folder(usb)
        copy = fieldsync.team_dir() / "laptopB.jsonl"
        copy.write_text(copy.read_text(encoding="utf-8").replace("b0", "bX"), encoding="utf-8")
        assert [e["note"] for e in fieldsync.team_entries()] == ["mine"]
        assert "laptopB.jsonl" in fieldsync.team_problems()[0]
        assert "WARNING, left out because they no longer check out" in fieldsync.command("team log")


# ── memory ─────────────────────────────────────────────────────────────────────

def test_memory_on_a_read_only_drive_says_not_saved(tmp_path, monkeypatch):
    from cursiv_v215.memory import semantic as sem
    monkeypatch.setattr(sem, "CURSIV_DIR", tmp_path / "app")
    monkeypatch.setattr(sem, "FACTS_FILE", tmp_path / "app" / "memory_facts.jsonl")
    monkeypatch.setattr(sem, "SETTINGS_FILE", tmp_path / "app" / "memory_settings.json")
    monkeypatch.setattr(sem, "embed", lambda texts: None)
    monkeypatch.setattr(sem._atomic, "write_text", _readonly)
    out = sem.memory_command("remember the spare fuel is in shed 2")
    assert out.startswith("Not saved") and "Permission denied" in out

"""Updating a Cursiv drive's personal data: nothing newer on the drive is lost."""
import os
from pathlib import Path
import threading

import pytest

import usb_sync


def _write(p: Path, text: str, mtime: float | None = None) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


@pytest.fixture
def sides(tmp_path):
    app, home, drive = tmp_path / "app", tmp_path / "home", tmp_path / "drive" / "Home" / ".cursiv"
    for p in (app, home, drive):
        p.mkdir(parents=True)
    return app, home, drive


def test_plan_decisions(sides):
    app, home, drive = sides
    _write(app / "memory_facts.jsonl", "a\nb\nc\n")
    _write(drive / "memory_facts.jsonl", "a\nb\n")                      # PC appended -> update
    _write(home / "fieldlog" / "observations.jsonl", "1\n")
    _write(drive / "fieldlog" / "observations.jsonl", "1\n2\n")           # drive appended -> keep
    _write(home / "conversations" / "new.json", "{}")                       # add
    _write(home / "conversations" / "same.json", "{}")
    _write(drive / "conversations" / "same.json", "{}")                     # same
    _write(home / "style" / "s.json", "pc", 2_000_000)
    _write(drive / "style" / "s.json", "drive", 3_000_000)                 # drive newer -> keep
    _write(app / "config.json", "pc newer", 3_000_000)
    _write(drive / "config.json", "drive older", 2_000_000)               # PC newer -> update
    actions = {it["rel"].as_posix(): it["action"] for it in usb_sync.plan([app, home], drive)}
    assert actions == {
        "memory_facts.jsonl": "update", "fieldlog/observations.jsonl": "keep",
        "conversations/new.json": "add", "conversations/same.json": "same",
        "style/s.json": "keep", "config.json": "update",
    }


def test_newest_source_wins_between_the_two_computer_folders(sides):
    app, home, drive = sides
    _write(app / "config.json", "live", 3_000_000)
    _write(home / "config.json", "stale august copy", 1_000_000)
    [item] = usb_sync.plan([app, home], drive)
    assert item["src"] == app / "config.json" and item["action"] == "add"


def test_apply_backs_up_then_verifies_and_keeps_drive_newer(sides):
    app, home, drive = sides
    _write(app / "config.json", "pc newer", 3_000_000)
    _write(drive / "config.json", "drive older", 2_000_000)
    _write(home / "notes.json", "pc older", 2_000_000)
    _write(drive / "notes.json", "drive newer", 3_000_000)
    _write(home / "conversations" / "c.json", "{}")
    items = usb_sync.plan([app, home], drive)
    result = usb_sync.apply(items, drive)
    assert (drive / "config.json").read_text() == "pc newer"
    assert (drive / "notes.json").read_text() == "drive newer"
    assert (drive / "conversations" / "c.json").read_text() == "{}"
    assert result["copied"] == 2 and result["backed_up"] == 1
    assert (result["backup"] / "config.json").read_text() == "drive older"
    assert "kept because the drive's copy is newer" in (result["backup"] / "REPORT.txt").read_text()
    assert (result["backup"] / "SHA256.json").exists()
    # A second check finds nothing left to do.
    again = usb_sync.plan([app, home], drive)
    assert not usb_sync.todo(again)


def test_skips_leases_backups_and_partial_copies(sides):
    app, home, drive = sides
    _write(app / ".vault-lease", "1")
    _write(app / "backups" / "old" / "memory.json", "x")
    _write(app / "x.json.part", "half")
    _write(app / "nested" / "backups" / "kept.json", "nested backups are data")
    rels = {it["rel"].as_posix() for it in usb_sync.plan([app, home], drive)}
    assert rels == {"nested/backups/kept.json"}


def test_cancel_leaves_no_half_files(sides):
    app, home, drive = sides
    _write(app / "a.json", "a")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        usb_sync.apply(usb_sync.plan([app], drive), drive, cancel=cancel)
    assert not list(drive.rglob("*.part")) and not (drive / "a.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="junctions are Windows-only")
def test_linked_drive_folder_refused(sides, tmp_path):
    import subprocess
    app, home, drive = sides
    _write(app / "fieldlog" / "o.jsonl", "1\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    subprocess.run(["cmd", "/c", "mklink", "/J", str(drive / "fieldlog"), str(elsewhere)],
                   check=True, capture_output=True)
    with pytest.raises(OSError, match="Linked"):
        usb_sync.plan([app], drive)


def test_program_copy_never_carries_data_folders(tmp_path):
    import usb_maker
    prog = tmp_path / "Cursiv"
    _write(prog / "Cursiv.exe", "exe")
    _write(prog / "_internal" / ".cursiv" / "memory_facts.jsonl", "private")
    _write(prog / ".cursiv.moved-20261006" / "config.json", "private")
    rels = {d.as_posix() for _s, d in usb_maker._program_files(prog, include_private=True)}
    assert rels == {"Cursiv/Cursiv.exe"}
    assert usb_maker._is_personal(Path("Cursiv/.cursiv.moved-20261006/config.json"))

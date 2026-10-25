"""Updating a Cursiv drive's personal data: nothing newer on the drive is lost."""
import os
from pathlib import Path
import threading

import pytest

import usb_sync

pytestmark = pytest.mark.usb


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
    assert "kept because the copy on the drive is newer" in (result["backup"] / "REPORT.txt").read_text()
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


# ── Drive -> this computer ───────────────────────────────────────────────────

@pytest.fixture
def computer(tmp_path, monkeypatch):
    app, home = tmp_path / "pc" / "app", tmp_path / "pc" / "home" / ".cursiv"
    drive = tmp_path / "drive" / "Home" / ".cursiv"
    for p in (app, home, drive):
        p.mkdir(parents=True)
    monkeypatch.setattr(usb_sync, "import_targets", lambda: (app.resolve(), home.resolve()))
    monkeypatch.setattr(usb_sync, "pending_dir", lambda: home / usb_sync.PENDING)
    return app.resolve(), home.resolve(), drive


def test_import_routes_each_file_to_the_folder_that_reads_it(computer):
    app, home, drive = computer
    _write(app / "memory_facts.jsonl", "a\n")
    _write(drive / "memory_facts.jsonl", "a\nb\n")                     # existing in APP_DATA
    _write(drive / "conversations" / "new.json", "{}")                   # new home store
    _write(drive / "brand_new_setting.json", "{}")                       # new, not a home store
    _write(home / "fieldlog" / "observations.jsonl", "1\n2\n")
    _write(drive / "fieldlog" / "observations.jsonl", "1\n")              # computer has more: keep
    _write(drive / "runtime" / "auth.hash", "drive password")            # logins never travel
    _write(drive / "logs" / "x.log", "log")
    _write(drive / "portable-layout-v1.json", "{}")
    got = {it["rel"].as_posix(): (it["action"], it["dest"]) for it in usb_sync.plan_import(drive, app, home)}
    assert got == {
        "memory_facts.jsonl": ("update", app / "memory_facts.jsonl"),
        "conversations/new.json": ("add", home / "conversations" / "new.json"),
        "brand_new_setting.json": ("add", app / "brand_new_setting.json"),
        "fieldlog/observations.jsonl": ("keep", home / "fieldlog" / "observations.jsonl"),
    }


def test_import_is_staged_then_applied_at_start_with_backups(computer):
    app, home, drive = computer
    _write(app / "memory_facts.jsonl", "a\n")
    _write(drive / "memory_facts.jsonl", "a\nb\n")
    _write(drive / "conversations" / "c.json", "{}")
    items = usb_sync.plan_import(drive, app, home)
    stage = usb_sync.stage_import(items)
    # Nothing in use changes until the next start, and the drive can go away.
    assert (app / "memory_facts.jsonl").read_text() == "a\n" and not (home / "conversations").exists()
    import shutil
    shutil.rmtree(drive.parent.parent)
    done = usb_sync.apply_pending_import()
    assert done["applied"] == 2 and done["backed_up"] == 1
    assert (app / "memory_facts.jsonl").read_text() == "a\nb\n"
    assert (home / "conversations" / "c.json").read_text() == "{}"
    [saved] = list((app / "backups").glob("usb-import-*/memory_facts.jsonl"))
    assert saved.read_text() == "a\n"
    assert "applied" in done["report"].read_text() and not stage.exists()
    assert usb_sync.apply_pending_import() is None


def test_apply_rechecks_and_keeps_work_done_after_staging(computer):
    app, home, drive = computer
    _write(app / "notes.json", "old", 2_000_000)
    _write(drive / "notes.json", "drive", 3_000_000)
    usb_sync.stage_import(usb_sync.plan_import(drive, app, home))
    _write(app / "notes.json", "edited on this computer after staging", 4_000_000)
    done = usb_sync.apply_pending_import()
    assert done["applied"] == 0
    assert (app / "notes.json").read_text() == "edited on this computer after staging"


def test_damaged_staged_copy_is_never_applied(computer):
    app, home, drive = computer
    _write(drive / "memory.json", "good")
    stage = usb_sync.stage_import(usb_sync.plan_import(drive, app, home))
    (stage / "files" / "00000").write_text("tampered")
    done = usb_sync.apply_pending_import()
    assert done["applied"] == 0 and not (app / "memory.json").exists()
    assert "damaged" in done["report"].read_text()


def test_config_with_same_keys_is_the_same_and_imported_keys_are_reencrypted(computer, monkeypatch):
    import json
    from cursiv_engine.core import keystore
    app, home, drive = computer
    monkeypatch.setattr(keystore, "reveal", lambda v: v[4:] if v.startswith("enc:") else v)
    monkeypatch.setattr(keystore, "protect", lambda v: v if v.startswith("enc:") else "enc:" + v)
    monkeypatch.setattr(keystore, "_dpapi_available", lambda: True)
    _write(app / "config.json", json.dumps({"groq_key": "enc:abc", "ui_theme": "dark"}), 2_000_000)
    _write(drive / "config.json", json.dumps({"groq_key": "abc", "ui_theme": "dark"}), 3_000_000)
    [item] = usb_sync.plan_import(drive, app, home)
    assert item["action"] == "same"
    _write(drive / "config.json", json.dumps({"groq_key": "new", "ui_theme": "dark"}), 3_000_000)
    usb_sync.stage_import(usb_sync.plan_import(drive, app, home))
    usb_sync.apply_pending_import()
    assert json.loads((app / "config.json").read_text())["groq_key"] == "enc:new"


def test_a_drive_encrypted_by_an_older_release_is_skipped_not_mixed(computer):
    from cursiv_engine.core import vault
    app, home, drive = computer
    _write(drive / vault.MARKER, "{}")
    _write(drive / "conversations" / "c.json", "ciphertext")
    _write(drive / "fieldlog" / "observations.jsonl", "1\n")
    got = {it["rel"].as_posix(): it["action"] for it in usb_sync.plan_import(drive, app, home)}
    assert got == {"conversations/c.json": "skip", "fieldlog/observations.jsonl": "add"}   # marker never travels


PASSWORD = "synthetic-usb-test-passphrase"


def test_encrypted_computer_to_readable_drive_and_back(computer):
    """U97: a computer is always encrypted, a drive stays readable, and data still moves."""
    from cursiv_engine.core import vault, vault_migration
    app, home, drive = computer
    _write(home / "conversations" / "c.json", '{"text": "computer conversation"}')
    _write(app / "memory_facts.jsonl", "fact one\n")
    vault_migration.migrate(PASSWORD, [app, home])
    try:
        assert (home / "conversations" / "c.json").read_bytes().startswith(vault.MAGIC)
        # Computer -> drive: written readable, vault files stay behind.
        usb_sync.apply(usb_sync.plan([app, home], drive), drive)
        assert (drive / "conversations" / "c.json").read_text(encoding="utf-8") == '{"text": "computer conversation"}'
        assert (drive / "memory_facts.jsonl").read_text(encoding="utf-8") == "fact one\n"
        assert not (drive / vault.MARKER).exists() and not (drive / ".vault-recovery").exists()
        assert all(it["action"] == "same" for it in usb_sync.plan([app, home], drive))
        # Work on the drive, then bring it back: staged encrypted, applied encrypted.
        later = (drive / "memory_facts.jsonl").stat().st_mtime + 60
        _write(drive / "memory_facts.jsonl", "fact one\nfact two from the drive\n", later)
        _write(drive / "conversations" / "d.json", '{"text": "drive conversation"}')
        stage = usb_sync.stage_import(usb_sync.plan_import(drive, app, home))
        for staged in (stage / "files").iterdir():
            assert staged.read_bytes().startswith(vault.MAGIC)
        done = usb_sync.apply_pending_import()
        assert done["applied"] == 2, done
        for path, source in ((app / "memory_facts.jsonl", drive / "memory_facts.jsonl"),
                             (home / "conversations" / "d.json", drive / "conversations" / "d.json")):
            assert path.read_bytes().startswith(vault.MAGIC) and usb_sync._plain(path) == source.read_bytes()
    finally:
        vault.lock()


def test_staging_is_not_carried_to_a_drive(sides):
    app, home, drive = sides
    _write(home / usb_sync.PENDING / "files" / "00000", "staged")
    assert usb_sync.plan([app, home], drive) == []

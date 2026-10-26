"""Batch 1: the login and the Cursiv USB keep their promises.

Run:  python -m pytest tests/   (or just: python tests/test_trust.py)
Uses temporary folders only -- never your real login or a real drive.
"""
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "launcher"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)

from PyQt6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])

import usb_maker as um  # noqa: E402


def _tmp() -> Path:
    # macOS /var is an OS alias; authorize the canonical disposable directory.
    # The production guard must continue refusing links inside state paths.
    return Path(tempfile.mkdtemp(prefix="cursiv_test_")).resolve()


def _write(p: Path, text: str, mtime: float | None = None) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


def _plan(src: Path, drive: Path):
    return [(f, drive / "Cursiv" / f.relative_to(src)) for f in src.rglob("*") if f.is_file()]


def _sync(src: Path, drive: Path):
    plan = _plan(src, drive)
    um.copy_files([(s, d) for s, d in plan if um._needs_copy(s, d)], lambda *_: None, threading.Event())
    for f in um.stale_files(drive, plan):
        f.unlink()
    return plan


# ── USB ─────────────────────────────────────────────────────────────────────

def test_usb_matches_the_build_after_repeat_updates():
    src, drive = _tmp(), _tmp()
    try:
        _write(src / "Cursiv.exe", "version 1")
        _write(src / "_internal" / "old_lib.dll", "going away")
        assert um.verify_usb(_sync(src, drive)) == []

        # Update 2: same-size file with new content, one library dropped, one added.
        later = time.time() + 60
        _write(src / "Cursiv.exe", "version 2", mtime=later)
        (src / "_internal" / "old_lib.dll").unlink()
        _write(src / "_internal" / "new_lib.dll", "new")
        plan = _sync(src, drive)

        assert um.verify_usb(plan) == []
        assert (drive / "Cursiv" / "Cursiv.exe").read_text() == "version 2"
        assert not (drive / "Cursiv" / "_internal" / "old_lib.dll").exists()
    finally:
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(drive, ignore_errors=True)


def test_personal_data_on_the_drive_is_never_pruned():
    src, drive = _tmp(), _tmp()
    try:
        _write(src / "Cursiv.exe", "app")
        mine = _write(drive / "Cursiv" / "_internal" / ".cursiv" / "memory.json", "{}")
        _sync(src, drive)
        assert mine.exists()
    finally:
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(drive, ignore_errors=True)


def test_verify_reports_a_changed_file():
    src, drive = _tmp(), _tmp()
    try:
        _write(src / "Cursiv.exe", "aaaa")
        plan = _sync(src, drive)
        _write(drive / "Cursiv" / "Cursiv.exe", "bbbb", mtime=time.time() + 120)
        assert um.verify_usb(plan) and um.verify_usb(plan)[0].startswith("different")
    finally:
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(drive, ignore_errors=True)


def test_stopped_copy_leaves_no_half_written_file():
    src, drive = _tmp(), _tmp()
    try:
        _write(src / "big.bin", "x" * 1000)
        stop = threading.Event()
        stop.set()
        try:
            um.copy_files(_plan(src, drive), lambda *_: None, stop)
        except InterruptedError:
            pass
        assert not any(drive.rglob("*.part")) and not (drive / "Cursiv" / "big.bin").exists()
    finally:
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(drive, ignore_errors=True)


def test_updating_a_drive_never_removes_its_data_or_models():
    # U103: wipe_private_copy (unused since U83, when updates stopped resetting drive data) is gone.
    # Even with the private-copy marker, only program files the build dropped are pruned.
    drive = _tmp()
    try:
        notes = _write(drive / "Home" / ".cursiv" / "fieldlog" / "field_log.jsonl", "{}")
        older = _write(drive / "Cursiv" / ".cursiv.moved-2026-01-01" / "memory.json", "{}")
        model = _write(drive / "Models" / "blobs" / "sha256-pulled-on-another-pc", "x")
        _write(drive / um.PRIVATE_MARKER, "private")
        dropped = _write(drive / "Cursiv" / "_internal" / "old_library.dll", "x")
        kept = _write(drive / "Cursiv" / "_internal" / "current.dll", "x")
        stale = um.stale_files(drive, [(kept, kept)])
        assert stale == [dropped]
        assert not hasattr(um, "wipe_private_copy")
        assert notes.exists() and older.exists() and model.exists()
    finally:
        shutil.rmtree(drive, ignore_errors=True)


def _temp_login(monkeypatch):
    from cursiv_engine.guardian import access_gate as ag
    rt = _tmp() / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    return ag


def test_reset_removes_every_login(monkeypatch):
    ag = _temp_login(monkeypatch)
    ag.setup_credentials("owner", "pass1234")
    assert ag.add_account("guest", "pass5678")
    ag.reset_credentials()
    assert not ag.is_setup_complete()
    assert not ag.verify_credentials("guest", "pass5678")


def test_create_account_needs_an_existing_login(monkeypatch):
    ag = _temp_login(monkeypatch)
    ag.setup_credentials("owner", "pass1234")
    import login_dialog as ld
    opened = []
    monkeypatch.setattr(ld, "SetupDialog", lambda *a, **k: opened.append(1) or (_ for _ in ()).throw(AssertionError))
    dlg = ld.LoginDialog()
    dlg._user.setText("owner")
    dlg._pw.setText("wrong")
    dlg._create_account()
    assert opened == [] and "existing username and password" in dlg._status.text()


def test_login_fails_closed_when_it_cannot_load(monkeypatch):
    # Loaded by path: after other tests "import main" could find another checkout's main.py on sys.path.
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("main", Path(__file__).resolve().parent.parent / "launcher" / "main.py")
    launcher_main = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(__import__("sys").modules, "main", launcher_main)
    spec.loader.exec_module(launcher_main)
    from cursiv_engine.guardian import access_gate as ag

    def broken():
        raise ImportError("simulated missing login module")

    monkeypatch.setattr(ag, "is_setup_complete", broken)
    monkeypatch.setattr(launcher_main, "_error_box", lambda *a, **k: None)
    # main() takes Cursiv's exclusive data lease on the real home folder; a running
    # Cursiv on this machine would hold it and this test would wait forever.
    from cursiv_engine.core import data_lease
    import encryption_dialog

    class _Lease:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def hold_until_exit(self): pass
    monkeypatch.setattr(data_lease, "DataLease", _Lease)
    monkeypatch.setattr(encryption_dialog, "startup", lambda **k: True)
    import cursiv_launcher
    monkeypatch.setattr(cursiv_launcher, "_acquire_instance_lock", lambda: True)
    monkeypatch.setattr(cursiv_launcher, "CursivLauncher",
                        lambda **k: (_ for _ in ()).throw(AssertionError("opened without login")))
    monkeypatch.setattr(launcher_main, "QApplication", lambda *a: _app, raising=False)
    try:
        launcher_main.main()
    except SystemExit as e:
        assert e.code == 1
    else:
        raise AssertionError("main() kept going without the login")


if __name__ == "__main__":
    class _MP:
        def __init__(self):
            self.undo = []

        def setattr(self, obj, name, value, raising=True):
            self.undo.append((obj, name, getattr(obj, name, None)))
            setattr(obj, name, value)

    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for name, t in tests:
        mp = _MP()
        try:
            t(mp) if t.__code__.co_argcount else t()
        finally:
            for obj, attr, old in reversed(mp.undo):
                setattr(obj, attr, old)
    print(f"{len(tests)} tests passed")

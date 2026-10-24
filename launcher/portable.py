"""
Portable (USB) mode -- Cursiv running straight off a drive made by
usb_maker.py, with nothing installed on the computer it's plugged into.

Layout of a Cursiv USB:
    <drive>\\Start Cursiv.bat      one click
    <drive>\\Cursiv\\               the program (Cursiv.exe + portable.cursiv marker)
    <drive>\\Ollama\\               the local AI engine (ollama.exe + lib)
    <drive>\\Models\\               AI models (Ollama's manifests + blobs)
    <drive>\\Home\\                 stands in for the user's home folder

activate() must run first thing in main.py, before any module computes
Path.home(): about twenty modules keep data under Path.home()/.cursiv, so
pointing USERPROFILE and APP_DATA at <drive>\\Home keeps Cursiv-managed records
on the drive. Windows or an existing host runtime may keep their own traces.
The real home is kept in CURSIV_REAL_HOME
for the read-only tools that look at the person's Downloads/Desktop.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

MARKER = "portable.cursiv"
FIELD_MARKER = "field.cursiv"          # a field copy: see apply_field_defaults()


def usb_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    app_dir = Path(sys.executable).resolve().parent
    return app_dir.parent if (app_dir / MARKER).exists() else None


def is_portable() -> bool:
    return os.environ.get("CURSIV_PORTABLE") == "1"


def activate() -> bool:
    root = usb_root()
    if root is None:
        return False
    home = root / "Home"
    data = home / '.cursiv'
    # Resolve and verify before importing modules which cache APP_DATA or HOME.
    if home.is_symlink() or home.is_junction() or data.is_symlink() or data.is_junction():
        raise OSError('Portable Home/data must be real folders on this drive.')
    home.mkdir(parents=True, exist_ok=True)
    data.mkdir(exist_ok=True)
    probe = data / ('.write-check-' + uuid.uuid4().hex)
    try:
        with probe.open('xb') as stream:
            stream.write(b'Cursiv'); stream.flush(); os.fsync(stream.fileno())
        if probe.read_bytes() != b'Cursiv':
            raise OSError('Portable storage verification failed')
    finally:
        probe.unlink(missing_ok=True)
    migrate_data(root, data)
    if not os.environ.get("CURSIV_REAL_HOME"):      # kept on a second activate(); empty counts as unset
        os.environ["CURSIV_REAL_HOME"] = os.environ.get("USERPROFILE") or str(Path.home())
    os.environ["USERPROFILE"] = str(home)
    os.environ["HOME"] = str(home)
    os.environ["CURSIV_PORTABLE"] = "1"
    os.environ["CURSIV_USB_ROOT"] = str(root)
    os.environ['CURSIV_APP_DATA'] = str(data)
    os.environ['CURSIV_DATA_DIR'] = str(data)
    os.environ.setdefault('CURSIV_HOST_LOCALAPPDATA', os.environ.get('LOCALAPPDATA', ''))
    # Libraries launched by this process use drive-local cache/temp locations.
    for variable, folder in (('APPDATA', home / 'AppData' / 'Roaming'),
                             ('LOCALAPPDATA', home / 'AppData' / 'Local'),
                             ('TEMP', home / 'Temp'), ('TMP', home / 'Temp')):
        for parent in (folder, *folder.parents):
            if parent.is_symlink() or parent.is_junction():
                raise OSError(f'Linked portable runtime folder refused: {parent}')
        folder.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(folder)
    import tempfile
    tempfile.tempdir = None
    workspace = root / 'Workspace'
    if workspace.is_symlink() or workspace.is_junction():
        raise OSError('Portable Workspace must not be a link.')
    workspace.mkdir(exist_ok=True)
    os.environ["OLLAMA_MODELS"] = str(root / "Models")
    ollama_dir = root / "Ollama"
    if (ollama_dir / "ollama.exe").exists():
        os.environ["PATH"] = str(ollama_dir) + os.pathsep + os.environ.get("PATH", "")
    if (root / "Cursiv" / FIELD_MARKER).exists():
        apply_field_defaults(home)
    return True


def migrate_data(root: Path, data: Path) -> None:
    """Once per drive: bring data that older USB makers left in the program folder
    (Cursiv\\_internal\\.cursiv, Cursiv\\.cursiv) into Home\\.cursiv.

    Same rules as updating a drive (usb_sync): missing files are added, and when
    both sides have a file the newer one wins (a log that only grew counts as
    newer). A Home file is copied to backups\\portable-migration-<time>\\ and
    verified before it is replaced; REPORT.txt there lists every decision. The
    old folders are left as they were. Earlier versions stopped startup on any
    difference, and every launch then failed on a drive made with private data."""
    marker = data / 'portable-layout-v1.json'
    if marker.exists():
        return
    for folder, dirs, names in os.walk(data, followlinks=False):
        for name in dirs + names:
            p = Path(folder) / name
            if p.is_symlink() or p.is_junction():
                raise OSError(f'Linked portable data requires manual review: {p}')
    sources = [root / 'Cursiv' / '_internal' / '.cursiv', root / 'Cursiv' / '.cursiv']
    for source in sources:
        for parent in (source, source.parent, source.parent.parent):
            if parent.is_symlink() or parent.is_junction():
                raise OSError(f'Linked legacy data requires manual review: {parent}')
    sources = [s for s in sources if s.is_dir()]
    if sources:
        import usb_sync
        usb_sync.apply(usb_sync.plan(sources, data), data, label='portable-migration')
    marker.write_text('{"version":1}', encoding='utf-8')


def apply_field_defaults(home: Path) -> None:
    """The first time a field copy starts: offline mode on, no break notes, no learned
    guesses about the person (only what they save with "remember"). All three can be
    changed in Settings afterwards; this runs once."""
    done = home / ".cursiv" / "field_defaults_applied"
    if done.exists():
        return
    try:
        from cursiv_engine.core import netgate
        from cursiv_engine.chat import keys
        from cursiv_engine.memory import semantic
        netgate.set_offline(True)
        keys.store_key("break_notes", "off")
        semantic.set_learning(False)
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text("Field defaults set on first start: offline on, break notes off, learning off.\n",
                        encoding="utf-8")
    except Exception:
        pass


def real_home() -> Path:
    return Path(os.environ.get("CURSIV_REAL_HOME") or Path.home())

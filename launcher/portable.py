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
import hashlib
import json
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
    """Snapshot legacy stores before copying missing files. Never choose a conflict."""
    marker = data / 'portable-layout-v1.json'
    if marker.exists():
        return
    for folder, dirs, names in os.walk(data, followlinks=False):
        for name in dirs + names:
            p = Path(folder) / name
            if p.is_symlink() or p.is_junction():
                raise OSError(f'Linked portable data requires manual review: {p}')
    sources = [root / 'Cursiv' / '_internal' / '.cursiv', root / 'Cursiv' / '.cursiv']
    files = []
    for source in sources:
        for parent in (source, source.parent, source.parent.parent):
            if parent.is_symlink() or parent.is_junction():
                raise OSError(f'Linked legacy data requires manual review: {parent}')
        if not source.exists():
            continue
        if source.is_symlink() or source.is_junction():
            raise OSError(f'Legacy portable data is a link: {source}')
        for folder, dirs, names in os.walk(source, followlinks=False):
            for name in dirs + names:
                p = Path(folder) / name
                if p.is_symlink() or p.is_junction():
                    raise OSError(f'Linked legacy data requires manual review: {p}')
            for name in names:
                p = Path(folder) / name
                files.append((p, p.relative_to(source), source.parent.name))
    if files:
        backup = data / 'backups' / ('portable-' + uuid.uuid4().hex)
        manifest = {}
        # Include the destination so both sides of every conflict are recoverable.
        snapshots = [(p, Path('Home') / p.relative_to(data)) for p in data.rglob('*')
                     if p.is_file() and 'backups' not in p.relative_to(data).parts]
        snapshots += [(p, Path(label) / rel) for p, rel, label in files]
        for source, rel in snapshots:
            if source.is_symlink() or source.is_junction():
                raise OSError('Linked data requires manual review')
            content = source.read_bytes()
            target = backup / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            if target.read_bytes() != content:
                raise OSError('Portable migration backup verification failed')
            manifest[rel.as_posix()] = hashlib.sha256(content).hexdigest()
        (backup / 'SHA256.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        planned = {}
        for source, rel, _ in files:
            content = source.read_bytes()
            target = data / rel
            if (target.exists() and target.read_bytes() != content) or (rel in planned and planned[rel] != content):
                raise OSError(f'Portable data conflict at {rel}. Backups: {backup}. Resolve before restarting.')
            planned[rel] = content
        for rel, content in planned.items():
            target = data / rel
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(content); stream.flush(); os.fsync(stream.fileno())
                if target.read_bytes() != content:
                    raise OSError(f'Portable migration verification failed: {rel}')
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

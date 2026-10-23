"""Small verified JSON stores. Callers own schemas and authorization."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading

LOCK = threading.RLock()
MAX_BYTES = 8 * 1024 * 1024


def checked(path: Path) -> Path:
    for parent in (path, *path.parents):
        if parent.is_symlink() or parent.is_junction():
            raise PermissionError(f'Linked state path refused: {parent}')
    return path


def load(path: Path, default):
    checked(path)
    try:
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('State exceeds 8 MB review limit; archive it before continuing')
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        if not path.parent.exists():
            # A missing store is normal; a disconnected portable drive is not.
            from .paths import portable_root
            root = portable_root()
            if root and not root.exists():
                raise OSError('Portable drive unavailable')
        return default
    return json.loads(text)


def save(path: Path, value) -> None:
    checked(path)
    content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    if len(content) > MAX_BYTES:
        raise ValueError('State exceeds 8 MB review limit; existing file preserved')
    with LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            original = path.read_bytes()
            backup = path.parent / 'backups' / (path.name + '.' + hashlib.sha256(original).hexdigest() + '.bak')
            checked(backup)
            backup.parent.mkdir(exist_ok=True)
            if not backup.exists():
                with backup.open('xb') as stream:
                    stream.write(original); stream.flush(); os.fsync(stream.fileno())
            if backup.read_bytes() != original:
                raise OSError('State backup verification failed')
        fd, temporary = tempfile.mkstemp(prefix='.' + path.name, suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            checked(path)
            os.replace(temporary, path)
            if path.read_bytes() != content:
                raise OSError('State write verification failed')
        finally:
            Path(temporary).unlink(missing_ok=True)

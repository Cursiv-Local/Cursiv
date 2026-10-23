"""Explicit I/O boundary for conversation/memory stores; plaintext compatibility by default."""
from __future__ import annotations

import io
from pathlib import Path
import threading
from . import vault

LOCK = threading.RLock()


def read_bytes(path: Path) -> bytes:
    path = Path(path)
    if vault.owner(path):
        # Check key/migration state even when the requested store does not exist.
        vault.ensure_access(path)
        if path.stat().st_size > vault.MAX_BYTES * 2:
            raise vault.VaultError('Encrypted store exceeds the supported size')
    return vault.reveal(path, path.read_bytes())


def read_text(path: Path, encoding='utf-8', errors='strict') -> str:
    return read_bytes(path).decode(encoding, errors)


def write_text(path: Path, text: str, encoding='utf-8', errors='strict') -> int:
    from . import atomic
    atomic.write_bytes(path, text.encode(encoding, errors))
    return len(text)


def append_text(path: Path, text: str) -> None:
    with LOCK:
        try:
            existing = read_text(path)
        except FileNotFoundError:
            existing = ''
        write_text(path, existing + text)


def lines(path: Path, encoding='utf-8'):
    """A memory-only text stream for existing line-oriented readers."""
    return io.StringIO(read_text(path, encoding))

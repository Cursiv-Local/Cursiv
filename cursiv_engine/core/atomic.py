"""
Saving a file so a power cut can't leave it half-written (research roadmap R5):
write a temporary file next to it, flush it to the disk, then swap it into place
in one step. After a crash the file is either the old version or the new one.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path


def replace(source: Path | str, target: Path | str, *, attempts: int = 20, delay: float = 0.025) -> None:
    """os.replace, retried while Windows refuses because something has the target open.

    Windows denies the swap ("Access is denied") while another handle reads the target,
    for example a second read in this process, an antivirus scan or the search indexer.
    Those handles close within moments, so a short retry finishes the save instead of losing it.
    """
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


def write_text(path: Path | str, text: str, encoding: str = "utf-8") -> None:
    write_bytes(path, text.encode(encoding))


def write_bytes(path: Path | str, data: bytes, *, protect: bool = True) -> None:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('Atomic binary writes require bytes')
    path = Path(path)
    if protect:
        from . import vault
        data = vault.protect(path, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    tmp = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        replace(tmp, path)
        if path.read_bytes() != data:
            raise OSError('Atomic write read-back verification failed')
    finally:
        if tmp.exists():
            tmp.unlink()

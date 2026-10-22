"""
Saving a file so a power cut can't leave it half-written (research roadmap R5):
write a temporary file next to it, flush it to the disk, then swap it into place
in one step. After a crash the file is either the old version or the new one.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def write_text(path: Path | str, text: str, encoding: str = "utf-8") -> None:
    write_bytes(path, text.encode(encoding))


def write_bytes(path: Path | str, data: bytes) -> None:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError('Atomic binary writes require bytes')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    tmp = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        if path.read_bytes() != data:
            raise OSError('Atomic write read-back verification failed')
    finally:
        if tmp.exists():
            tmp.unlink()

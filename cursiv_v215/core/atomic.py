"""
Saving a file so a power cut can't leave it half-written (research roadmap R5):
write a temporary file next to it, flush it to the disk, then swap it into place
in one step. After a crash the file is either the old version or the new one.
"""
from __future__ import annotations

import os
from pathlib import Path


def write_text(path: Path | str, text: str, encoding: str = "utf-8") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding=encoding, newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

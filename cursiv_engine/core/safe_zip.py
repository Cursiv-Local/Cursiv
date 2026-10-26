"""
Unpacking a downloaded zip without trusting it (U105, outside review). Used for the Vosk voice model and the
Ollama engine Cursiv downloads.

- Names: no absolute paths, drive letters, `..` parts or backslash tricks; every file lands inside `dest`.
- No symbolic links (a link inside a zip could point anywhere once unpacked).
- Limits on the number of files, the total size and any one file. Sizes are counted while reading, not taken
  from the zip's own headers, which can lie (a "zip bomb").
- All or nothing: everything is unpacked into a temporary folder beside `dest` and moved into place only when
  it all checks out. A refusal leaves nothing behind, and an existing `dest` is never overwritten.
"""
from __future__ import annotations

import os
import shutil
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath

CHUNK = 1 << 20


class UnsafeZip(ValueError):
    """The zip was refused; nothing was unpacked."""


def _safe_name(name: str) -> PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        raise UnsafeZip(f"refused a file name in the zip: {name[:80]!r}")
    p = PurePosixPath(name)
    if p.is_absolute() or (p.parts and ":" in p.parts[0]) or any(part in ("..", "") for part in p.parts):
        raise UnsafeZip(f"refused a file name that leaves the folder: {name[:80]!r}")
    return p


def extract(zip_path: Path, dest: Path, *, max_files: int, max_bytes: int, max_file_bytes: int) -> int:
    """Unpack zip_path into dest (which must not exist yet). Returns the bytes written."""
    dest = Path(dest)
    if dest.exists():
        raise UnsafeZip(f"{dest} already exists; nothing was overwritten")
    work = dest.with_name(f".{dest.name}.unzip-{uuid.uuid4().hex[:8]}")
    total = 0
    try:
        with zipfile.ZipFile(zip_path) as z:
            infos = z.infolist()
            if len(infos) > max_files:
                raise UnsafeZip(f"the zip has {len(infos)} entries, more than the {max_files} allowed")
            for info in infos:
                rel = _safe_name(info.filename)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise UnsafeZip(f"refused a link in the zip: {info.filename[:80]!r}")
                target = work.joinpath(*rel.parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with z.open(info) as src, open(target, "wb") as out:
                    while chunk := src.read(CHUNK):
                        written += len(chunk)
                        total += len(chunk)
                        if written > max_file_bytes:
                            raise UnsafeZip(f"{info.filename[:80]} unpacks to more than {max_file_bytes} bytes")
                        if total > max_bytes:
                            raise UnsafeZip(f"the zip unpacks to more than {max_bytes} bytes")
                        out.write(chunk)
        os.replace(work, dest)
        return total
    except (zipfile.BadZipFile, EOFError, OSError) as exc:
        raise UnsafeZip(f"the zip couldn't be read ({type(exc).__name__}: {exc})") from None
    finally:
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)

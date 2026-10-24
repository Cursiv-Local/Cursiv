"""
Bring a Cursiv drive's personal data up to date from this computer -- without
losing anything on either side.

This computer keeps Cursiv's data in two folders: paths.APP_DATA (settings, keys,
memories; next to the program) and ~/.cursiv (conversations, field log, documents).
On a drive both live in <drive>\\Home\\.cursiv. Older copies of a few files can sit
in both computer folders; the newer one is the one Cursiv uses.

plan() only reads. For every file it decides:
    add      the drive doesn't have it
    same     identical bytes
    update   this computer's copy is newer, or the drive's copy is an earlier part
             of it (a log this computer added lines to)
    keep     the drive's copy is newer, or this computer's copy is an earlier part
             of it (the drive was used since the last update) -- left alone
apply() copies add/update files. A drive file is copied into
Home\\.cursiv\\backups\\usb-update-<time>\\ and verified before it is replaced, and
every new file is checked byte for byte against its source.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

MTIME_SLACK = 2.0                      # FAT-family drives store times in 2-second steps
SKIP_NAMES = {".vault-lease"}          # live process lease, never data
SKIP_TOP = {"backups"}                 # each side keeps its own recovery copies


def data_sources() -> list[Path]:
    """This computer's Cursiv data folders, most authoritative first."""
    from cursiv_engine.core import paths
    out = []
    for p in (paths.APP_DATA, Path.home() / ".cursiv"):
        try:
            p = p.resolve()
        except OSError:
            continue
        if p.is_dir() and p not in out:
            out.append(p)
    return out


def _linked(p: Path) -> bool:
    return p.is_symlink() or p.is_junction()


def collect(sources: list[Path]) -> dict[Path, Path]:
    """relative path -> the newest file with that path across the sources."""
    found: dict[Path, Path] = {}
    for base in sources:
        if _linked(base):
            raise OSError(f"Linked data folder refused: {base}")
        for folder, dirs, names in os.walk(base, followlinks=False):
            here = Path(folder)
            dirs[:] = [d for d in dirs if not _linked(here / d)
                       and not (here == base and d in SKIP_TOP)]
            for name in names:
                f = here / name
                if name in SKIP_NAMES or name.endswith(".part") or _linked(f):
                    continue
                rel = f.relative_to(base)
                old = found.get(rel)
                if old is None or f.stat().st_mtime > old.stat().st_mtime + MTIME_SLACK:
                    found[rel] = f
    return found


def _digest(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        while chunk := fh.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def _starts_with(longer: Path, shorter: Path) -> bool:
    """True when every byte of `shorter` begins `longer` (an append-only log that grew)."""
    n = shorter.stat().st_size
    if n == 0 or longer.stat().st_size <= n:
        return False
    with open(longer, "rb") as a, open(shorter, "rb") as b:
        while n > 0:
            size = min(n, 8 << 20)
            if a.read(size) != b.read(size):
                return False
            n -= size
    return True


def decide(src: Path, dest: Path) -> tuple[str, str]:
    if not dest.exists():
        return "add", "not on the drive"
    s, d = src.stat(), dest.stat()
    if s.st_size == d.st_size and _digest(src) == _digest(dest):
        return "same", ""
    if _starts_with(src, dest):
        return "update", "this computer added to it"
    if _starts_with(dest, src):
        return "keep", "the drive added to it"
    if s.st_mtime > d.st_mtime + MTIME_SLACK:
        return "update", "newer on this computer"
    return "keep", "newer on the drive"


def plan(sources: list[Path], dest: Path) -> list[dict]:
    """Read-only. One entry per file: rel, src, dest, action, reason."""
    if dest.exists() and _linked(dest):
        raise OSError(f"Linked drive data folder refused: {dest}")
    items = []
    for rel, src in sorted(collect(sources).items()):
        target = dest / rel
        for p in (target, *target.parents):
            if p == dest.parent:
                break
            if p.exists() and _linked(p):
                raise OSError(f"Linked drive destination refused: {p}")
        action, reason = decide(src, target)
        items.append({"rel": rel, "src": src, "dest": target, "action": action, "reason": reason})
    return items


def summary(items: list[dict]) -> dict[str, int]:
    out = {"add": 0, "update": 0, "same": 0, "keep": 0}
    for it in items:
        out[it["action"]] += 1
    return out


def todo(items: list[dict]) -> list[dict]:
    return [it for it in items if it["action"] in ("add", "update")]


def _write_verified(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + dest.name, suffix=".part", dir=dest.parent)
    part = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as fo, open(src, "rb") as fi:
            shutil.copyfileobj(fi, fo, 8 << 20)
            fo.flush()
            os.fsync(fo.fileno())
        if _digest(part) != _digest(src):
            raise OSError(f"Copy verification failed: {dest}")
        os.replace(part, dest)
        shutil.copystat(src, dest, follow_symlinks=False)
    finally:
        part.unlink(missing_ok=True)


def apply(items: list[dict], dest: Path, progress=None, cancel: threading.Event | None = None,
          label: str = "usb-update") -> dict:
    """Copy the add/update files. Returns {"copied", "backed_up", "backup"}."""
    work = todo(items)
    backup = dest / "backups" / (label + time.strftime("-%Y%m%d-%H%M%S"))
    report, backed = [], 0
    for i, it in enumerate(work, 1):
        if cancel is not None and cancel.is_set():
            raise InterruptedError
        target: Path = it["dest"]
        if target.exists():
            saved = backup / it["rel"]
            _write_verified(target, saved)
            backed += 1
        _write_verified(it["src"], target)
        report.append(f"{it['action']:6}  {it['rel'].as_posix()}  ({it['reason']})")
        if progress:
            progress(int(i * 100 / len(work)), f"Updating your data on the drive: {i} of {len(work)} files")
    if report:
        backup.mkdir(parents=True, exist_ok=True)
        counts = summary(items)
        (backup / "REPORT.txt").write_text(
            f"Cursiv data update ({label}) into {dest}\n"
            f"{counts['add']} added, {counts['update']} updated, {counts['same']} already the same, "
            f"{counts['keep']} kept because the drive's copy is newer.\n"
            "Replaced drive files are saved in this folder under the same names.\n\n"
            + "\n".join(report) + "\n", encoding="utf-8")
        if backed:
            manifest = {p.relative_to(backup).as_posix(): _digest(p)
                        for p in backup.rglob("*") if p.is_file() and p.name not in ("REPORT.txt", "SHA256.json")}
            (backup / "SHA256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"copied": len(work), "backed_up": backed, "backup": backup if report else None}


def describe(items: list[dict]) -> str:
    c = summary(items)
    if not items:
        return "No personal data on this computer to copy."
    parts = []
    if c["add"]:
        parts.append(f"{c['add']} new")
    if c["update"]:
        parts.append(f"{c['update']} newer on this computer")
    if c["keep"]:
        parts.append(f"{c['keep']} newer on the drive (kept)")
    parts.append(f"{c['same']} already up to date")
    return "Your data: " + ", ".join(parts) + "."

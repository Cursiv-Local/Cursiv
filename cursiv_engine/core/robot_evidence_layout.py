"""Robot evidence package layout, formats 1 and 2. Vendored unchanged from Cursiv-Robotics
(python/cursiv_integration/layout.py at commit 48151c0, MIT License, same author); see
core/robot_evidence.py.

Format 1: data/robots/<robot>/records.jsonl
Format 2: data/robots/<robot>/segments/000001.jsonl, 000002.jsonl, ... (each with a .seal.json)

Reading files does not verify anything: run `cursiv-verify` first.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator

SEGMENT = re.compile(r"^(\d{6})\.jsonl$")


def package_version(pkg: Path) -> int:
    """The Cursiv-Package-Version in bag-info.txt (1 when absent, as in the earliest packages)."""
    info = Path(pkg) / "bag-info.txt"
    if info.is_file():
        for line in info.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Cursiv-Package-Version:"):
                v = line.split(":", 1)[1].strip()
                return int(v) if v.isdigit() else -1
    return 1


def robots(pkg: Path) -> list[str]:
    root = Path(pkg) / "data" / "robots"
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []


def record_files(pkg: Path, robot: str) -> list[Path]:
    """A robot's record files in log order."""
    d = Path(pkg) / "data" / "robots" / robot
    if (d / "records.jsonl").is_file():
        return [d / "records.jsonl"]
    seg = d / "segments"
    if not seg.is_dir():
        return []
    return sorted((p for p in seg.iterdir() if SEGMENT.match(p.name)), key=lambda p: p.name)


def record_lines(pkg: Path, robot: str) -> Iterator[str]:
    """Every record line of a robot, in order, across segments."""
    for f in record_files(pkg, robot):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.strip():
                    yield line.rstrip("\r\n")


def envelopes(pkg: Path) -> Iterator[tuple[str, dict]]:
    """(robot, envelope) for every record line that is JSON; unreadable lines are skipped."""
    for r in robots(pkg):
        for line in record_lines(pkg, r):
            try:
                yield r, json.loads(line)
            except ValueError:
                continue

"""SHA-256 of the benchmark's cases and checks, line endings normalized.

    py -3.13 bench/suite_hash.py      # prints the current hashes
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def current() -> dict:
    return {"cases": file_hash(HERE / "truth_cases.py"), "scoring": file_hash(HERE / "scoring.py")}


def recorded() -> dict:
    """The version, case hash and scoring hash SUITE.md says are current."""
    m = re.search(r"<!-- current: (\S+) cases=([0-9a-f]{64}) scoring=([0-9a-f]{64}) -->",
                  (HERE / "SUITE.md").read_text(encoding="utf-8"))
    return {"version": m.group(1), "cases": m.group(2), "scoring": m.group(3)} if m else {}


if __name__ == "__main__":
    print(current())

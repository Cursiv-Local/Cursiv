"""
What Cursiv actually read or checked during this session (U99), kept in memory only.

Only application code writes here -- a source search, a source read, a capability
lookup. The model can't add to it. When an answer says "I checked the source code"
or "this is verified", core/claim_evidence.py looks here, and a claim with no matching
record is corrected. A question like "have you inspected your source code?" is answered
from this record, not from the model's memory of what it said.

Each record: kind, source, path, lines, revision, operation, time, scope.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass

SOURCE_SEARCH = "source search"
SOURCE_READ = "source read"
CAPABILITY = "capability records"
LIVE_STATE = "live settings"
SOURCE_SUPPLIED = "source excerpts supplied to the model"


@dataclass(frozen=True)
class Record:
    kind: str
    source: str
    path: str = ""
    lines: str = ""
    revision: str = ""
    operation: str = ""
    at: float = 0.0
    scope: str = ""


_lock = threading.Lock()
_records: list[Record] = []
_turn_start = 0


def record(kind: str, source: str, *, path: str = "", lines: str = "", operation: str = "", scope: str = "") -> None:
    try:
        from .selfknow import VERSION
    except Exception:
        VERSION = "unknown"
    with _lock:
        _records.append(Record(kind, source, path, lines, f"Cursiv {VERSION}", operation, time.time(), scope))
        del _records[:-200]


def begin_turn() -> None:
    """Mark the start of a new answer; this_turn() returns only what came after."""
    global _turn_start
    with _lock:
        _turn_start = len(_records)


def this_turn() -> list[Record]:
    with _lock:
        return list(_records[_turn_start:])


def session() -> list[Record]:
    with _lock:
        return list(_records)


def kinds(records: list[Record]) -> set[str]:
    return {r.kind for r in records}


def clear() -> None:
    global _turn_start
    with _lock:
        _records.clear()
        _turn_start = 0


def summary(records: list[Record]) -> list[dict]:
    return [asdict(r) for r in records]

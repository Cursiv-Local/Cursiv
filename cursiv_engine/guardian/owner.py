"""
Owner mode: the person who set an owner code can unlock builder tools for
this run of Cursiv by typing it as a message.

The code is chosen at runtime ("owner setcode <code>") and only its SHA-256
hash is stored, in ~/.cursiv/runtime/owner.hash. Nothing secret is in the
source code.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

_OWNER_CODE_FILE = Path.home() / ".cursiv" / "runtime" / "owner.hash"
_OWNER_SESSIONS: set[str] = set()


def unlock_owner_session(session_id: str) -> None:
    _OWNER_SESSIONS.add(session_id)


def is_owner_session(session_id: str) -> bool:
    return session_id in _OWNER_SESSIONS


def owner_code_is_set() -> bool:
    return _OWNER_CODE_FILE.exists()


def set_owner_code(code: str) -> None:
    code = code.strip()
    if not code:
        raise ValueError("Owner code cannot be empty.")
    _OWNER_CODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _OWNER_CODE_FILE.write_text(hashlib.sha256(code.encode("utf-8")).hexdigest(), encoding="utf-8")


def verify_owner_code(text: str) -> bool:
    """Is this message the owner code?"""
    text = text.strip()
    if not text or not _OWNER_CODE_FILE.exists():
        return False
    try:
        stored = _OWNER_CODE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return False
    return hashlib.sha256(text.encode("utf-8")).hexdigest() == stored

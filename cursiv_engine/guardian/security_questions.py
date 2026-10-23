"""
Cursiv Security Questions — password recovery via challenge-response.

Answers are normalised (lowercase, strip punctuation) then bcrypt-hashed so
they cannot be retrieved. At reset time, at least 2 of 3 must match.

Storage: .cursiv/runtime/sq.json, one set per account:
    {"accounts": {"<sha256 of username>": {"questions": [...], "answers": [...]}}}
A file from before per-account questions ({"questions", "answers"} at the top) is the
first (primary) account's set; it's moved under that account the next time it's written.
Each account's questions reset only that account's password (access_gate.reset_password).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False

_RUNTIME = Path.home() / ".cursiv" / "runtime"
# See access_gate.py for why this is Path.home() and not __file__-relative.
_SQ_FILE = _RUNTIME / "sq.json"

QUESTIONS: list[str] = [
    "What is the name of your first pet?",
    "What city were you born in?",
    "What was the name of your elementary school?",
    "What is your mother's maiden name?",
    "What was the make and model of your first car?",
    "What was the name of the street you grew up on?",
    "What was your childhood nickname?",
    "What is the name of your oldest sibling?",
    "Who was your best friend in high school?",
    "What city did you first meet your significant other in?",
    "What was the name of the hospital you were born in?",
    "What was the name of your first employer?",
    "What is the middle name of your youngest child?",
    "What was your high school mascot?",
    "What was the name of the first concert you attended?",
    "What street did your best childhood friend live on?",
    "Who was your favorite childhood teacher?",
    "What was the first album or CD you ever owned?",
    "What was the name of your first stuffed animal or toy?",
    "What was the destination of your first airplane trip?",
]

RESET_THRESHOLD = 2   # answers required out of 3


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _hash_answer(answer: str) -> bytes:
    if not _BCRYPT_OK:
        raise RuntimeError("bcrypt is not installed — run: pip install bcrypt")
    return bcrypt.hashpw(_normalise(answer).encode("utf-8"), bcrypt.gensalt(rounds=10))


def _check(answer: str, stored: str) -> bool:
    if not _BCRYPT_OK:
        return False
    try:
        return bcrypt.checkpw(
            _normalise(answer).encode("utf-8"),
            stored.encode("latin-1"),
        )
    except Exception:
        return False


def _uhash(username: str) -> str:
    import hashlib
    return hashlib.sha256((username or "").encode("utf-8")).hexdigest()


def _primary_hash() -> str:
    try:
        from cursiv_engine.guardian import access_gate
        return access_gate._primary_hash()
    except Exception:
        return ""


def _load() -> dict:
    """{"accounts": {hash: {"questions", "answers"}}}, with an old single set placed
    under the primary account."""
    try:
        data = json.loads(_SQ_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"accounts": {}}
    accounts = dict(data.get("accounts") or {})
    if "questions" in data and "answers" in data:
        primary = _primary_hash()
        if primary and primary not in accounts:
            accounts[primary] = {"questions": data["questions"], "answers": data["answers"]}
    return {"accounts": accounts}


def _save(data: dict) -> None:
    _RUNTIME.mkdir(parents=True, exist_ok=True)
    _SQ_FILE.write_text(json.dumps({"accounts": data["accounts"]}, indent=2), encoding="utf-8")


def _key(username: str | None) -> str:
    """The account a call is about: the named one, or the primary when none is named
    (callers from before per-account questions)."""
    return _uhash(username) if username else _primary_hash()


# ── Public API ─────────────────────────────────────────────────────────────

def setup_security_questions(q_indices: list[int], answers: list[str], username: str | None = None) -> None:
    """Hash and save 3 security Q&A pairs for this account (the primary if none is named).
    Replaces that account's previous set; other accounts' sets are untouched."""
    if not _BCRYPT_OK:
        raise RuntimeError("bcrypt is not installed — run: pip install bcrypt")
    if len(q_indices) != 3 or len(answers) != 3:
        raise ValueError("Exactly 3 questions and answers are required.")
    key = _key(username)
    if not key:
        raise ValueError("There's no account to set security questions for.")
    data = _load()
    data["accounts"][key] = {"questions": list(q_indices),
                             "answers": [_hash_answer(a).decode("latin-1") for a in answers]}
    _save(data)


def is_setup_complete(username: str | None = None) -> bool:
    """Has this account (the primary if none is named) set security questions?"""
    key = _key(username)
    return bool(key) and key in _load()["accounts"]


def get_selected_questions(username: str | None = None) -> list[str]:
    """The 3 question texts this account chose."""
    entry = _load()["accounts"].get(_key(username))
    return [QUESTIONS[i] for i in entry["questions"]] if entry else []


def verify_answers(answers: list[str], username: str | None = None) -> bool:
    """True when at least RESET_THRESHOLD answers match this account's stored hashes."""
    entry = _load()["accounts"].get(_key(username))
    if not entry:
        return False
    stored = entry["answers"]
    if len(answers) != len(stored):
        return False
    matches = sum(_check(a, h) for a, h in zip(answers, stored))
    return matches >= RESET_THRESHOLD


def clear_security_questions(username: str | None = None, *, account_hash: str = "") -> None:
    """Remove one account's set (by username or its hash), or every set when neither is given."""
    try:
        if not username and not account_hash:
            _SQ_FILE.unlink(missing_ok=True)
            return
        data = _load()
        data["accounts"].pop(account_hash or _uhash(username), None)
        _save(data)
    except Exception:
        pass

"""
Cursiv Legacy Store — family letter vault.

Letters written by family members, stored locally, accessed only by the
intended recipient via their established credentials.

Not documented. Not in help. Found only if you look.

Created: May 20, 2026 · Fruitland Park, Florida
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import uuid
from functools import wraps
from datetime import datetime
from pathlib import Path
from cursiv_v215.core import atomic

_LEGACY_DIR  = Path.home() / ".cursiv" / "family" / "legacy"
# See cursiv_v215/guardian/access_gate.py for why this is Path.home().
_LETTERS_DIR = _LEGACY_DIR / "letters"
_INDEX_FILE  = _LEGACY_DIR / "index.json"
_lock = threading.RLock()


def _serialized(fn):
    @wraps(fn)
    def locked(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return locked


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    _LETTERS_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list[dict]:
    try:
        entries = json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(entries, list) or any(not isinstance(e, dict) or not isinstance(e.get('id'), str)
            or not isinstance(e.get('filename'), str) or re.search(r'[\\/:]', e['filename'])
            or not e['filename'].lower().endswith('.letter') for e in entries):
        raise ValueError('Legacy letter index is damaged; no existing records were replaced')
    return entries


def _save_index(index: list[dict]) -> None:
    _ensure_dirs()
    atomic.write_text(_INDEX_FILE, json.dumps(index, indent=2, ensure_ascii=False))


# ── Public read API ───────────────────────────────────────────────────────────

def letters_waiting_for(recipient_key: str) -> list[dict]:
    """All letters addressed to recipient_key, sorted oldest first."""
    return sorted(
        [e for e in _load_index() if e.get("for_key") == recipient_key],
        key=lambda e: e.get("written", ""),
    )


def letters_written_by(author_key: str) -> list[dict]:
    """All letters written by author_key, sorted oldest first."""
    return sorted(
        [e for e in _load_index() if e.get("from_key") == author_key],
        key=lambda e: e.get("written", ""),
    )


def get_letter_entry(letter_id: str) -> dict | None:
    return next((e for e in _load_index() if e.get("id") == letter_id), None)


def get_letter_content(letter_id: str) -> str | None:
    """Return the body of a letter (everything after the header separator)."""
    entry = get_letter_entry(letter_id)
    if not entry:
        return None
    path = _LETTERS_DIR / entry["filename"]
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        if "---\n" in raw:
            return raw.split("---\n", 1)[1]
        return raw
    except Exception:
        return None


# ── Write / mutate API ────────────────────────────────────────────────────────

@_serialized
def save_letter(
    from_key: str,
    from_display: str,
    for_key: str,
    for_display: str,
    subject: str,
    content: str,
    access_type: str = "babel_pin",   # "babel_pin" | "letter_pin"
    access_hash: str = "",
    written: str = "",
) -> str:
    """Save a new letter. Returns the letter ID."""
    _ensure_dirs()

    existing = _load_index()
    if not all(isinstance(v, str) for v in (from_key, from_display, for_key, for_display, subject, content, access_type, access_hash, written)):
        raise ValueError('Letter fields must be text')
    now       = datetime.fromisoformat(written) if written else datetime.now()
    written_at = written or now.isoformat()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    safe_from = re.sub(r'[^A-Za-z0-9_-]', '_', from_key) or 'unknown'
    safe_for = re.sub(r'[^A-Za-z0-9_-]', '_', for_key) or 'unknown'
    letter_id = f"{safe_from}_for_{safe_for}_{timestamp}_{uuid.uuid4().hex[:12]}"
    filename  = f"{letter_id}.letter"

    header = (
        f"LEGACY_LETTER\n"
        f"from: {from_key}\n"
        f"from_display: {from_display}\n"
        f"for: {for_key}\n"
        f"for_display: {for_display}\n"
        f"subject: {subject or '(no subject)'}\n"
        f"written: {written_at}\n"
        f"access_type: {access_type}\n"
        f"---\n"
    )

    atomic.write_text(_LETTERS_DIR / filename, header + content.strip() + '\n')

    index = existing
    index.append({
        "id":           letter_id,
        "from_key":     from_key,
        "from_display": from_display,
        "for_key":      for_key,
        "for_display":  for_display,
        "subject":      subject or "(no subject)",
        "written":      written_at,
        "filename":     filename,
        "access_type":  access_type,
        "access_hash":  access_hash,
    })
    _save_index(index)
    if get_letter_entry(letter_id) is None or get_letter_content(letter_id) != content.strip() + '\n':
        raise OSError('Letter save read-back verification failed; inspect the vault before retrying')
    return letter_id


@_serialized
def rewrite_letter(letter_id: str, new_content: str) -> bool:
    """Replace the body of an existing letter. Adds a 'revised' timestamp."""
    index = _load_index()
    entry = next((e for e in index if e.get("id") == letter_id), None)
    if not entry:
        return False
    path = _LETTERS_DIR / entry["filename"]
    if not path.exists():
        return False

    now_str = datetime.now().isoformat()
    header = (
        f"LEGACY_LETTER\n"
        f"from: {entry['from_key']}\n"
        f"from_display: {entry['from_display']}\n"
        f"for: {entry['for_key']}\n"
        f"for_display: {entry['for_display']}\n"
        f"subject: {entry['subject']}\n"
        f"written: {entry['written']}\n"
        f"revised: {now_str}\n"
        f"access_type: {entry['access_type']}\n"
        f"---\n"
    )
    atomic.write_text(path, header + new_content.strip() + '\n')

    entry["revised"] = now_str
    _save_index(index)
    if get_letter_content(letter_id) != new_content.strip() + '\n':
        raise OSError('Letter update read-back verification failed')
    return True


@_serialized
def delete_letter(letter_id: str) -> bool:
    """Permanently delete a letter and remove it from the index."""
    index = _load_index()
    entry = next((e for e in index if e.get("id") == letter_id), None)
    if not entry:
        return False
    path = _LETTERS_DIR / entry['filename']
    path.unlink(missing_ok=True)
    _save_index([e for e in index if e.get("id") != letter_id])
    if path.exists() or get_letter_entry(letter_id) is not None:
        raise OSError('Letter deletion could not be verified')
    return True


# ── PIN helpers ───────────────────────────────────────────────────────────────

def make_letter_pin_hash(pin: str) -> str:
    return hashlib.sha256(pin.strip().encode()).hexdigest()


def verify_letter_pin(letter_id: str, pin: str) -> bool:
    """Verify a letter-specific access PIN."""
    entry = get_letter_entry(letter_id)
    if not entry or entry.get("access_type") != "letter_pin":
        return False
    stored = entry.get("access_hash", "")
    if not stored:
        return False
    h = hashlib.sha256(pin.strip().encode()).hexdigest()
    return hmac.compare_digest(stored, h)


# ── Key derivation helper ─────────────────────────────────────────────────────

def name_to_key(display_name: str) -> str:
    """Turn a display name into a lowercase slug for use as a key."""
    return re.sub(r"[^a-z0-9]", "", display_name.lower().split()[0])


# ── Pack export / import ──────────────────────────────────────────────────────

def export_destination() -> Path:
    """
    Find the best place to drop an export file so it's immediately visible.
    Priority: Desktop → OneDrive Desktop → Downloads → home directory.
    """
    home = Path.home()
    for candidate in (
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "OneDrive - Personal" / "Desktop",
        home / "Downloads",
    ):
        if candidate.exists():
            return candidate
    return home


def export_pack(author_key: str, author_display: str) -> tuple[Path, int]:
    """
    Bundle all letters written by author_key into a .legacypack file on
    the Desktop (or Downloads). Returns (filepath, letter_count).
    """
    letters = letters_written_by(author_key)
    if not letters:
        return Path(), 0

    payload: list[dict] = []
    for entry in letters:
        content = get_letter_content(entry["id"])
        if content is None:
            raise OSError(f"Letter {entry['id']} cannot be read; export was not confirmed")
        payload.append({
            "from_key":     entry["from_key"],
            "from_display": entry["from_display"],
            "for_key":      entry["for_key"],
            "for_display":  entry["for_display"],
            "subject":      entry["subject"],
            "written":      entry["written"],
            "revised":      entry.get("revised", ""),
            "access_type":  entry["access_type"],
            "content":      content or "",
        })

    pack = {
        "cursiv_legacy_pack": True,
        "version":            "1.0",
        "exported_by":        author_key,
        "exported_by_display": author_display,
        "exported_at":        datetime.now().isoformat(),
        "letter_count":       len(payload),
        "letters":            payload,
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_author = re.sub(r'[^A-Za-z0-9_-]', '_', author_key)
    filename  = f"legacy_from_{safe_author}_{timestamp}_{uuid.uuid4().hex[:8]}.legacypack"
    dest      = export_destination() / filename
    atomic.write_text(dest, json.dumps(pack, indent=2, ensure_ascii=False))
    return dest, len(payload)


def import_pack(filepath: str | Path) -> tuple[int, list[str]]:
    """
    Import a .legacypack file into the local vault.
    Returns (imported_count, list_of_skipped_ids).
    Skips duplicates (same from_key + for_key + written timestamp).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Pack file not found: {filepath}")

    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Could not read pack file: {e}")

    if not pack.get("cursiv_legacy_pack"):
        raise ValueError("Not a valid Cursiv Legacy Pack.")

    existing = _load_index()
    existing_sigs = {
        (e["from_key"], e["for_key"], e.get("written", ""))
        for e in existing
    }

    imported = 0
    skipped: list[str] = []

    for letter in pack.get("letters", []):
        sig = (letter.get("from_key", ""), letter.get("for_key", ""), letter.get("written", ""))
        if sig in existing_sigs:
            skipped.append(f"{letter.get('from_display','?')} → {letter.get('for_display','?')}")
            continue

        save_letter(
            from_key     = letter.get("from_key", "unknown"),
            from_display = letter.get("from_display", "Unknown"),
            for_key      = letter.get("for_key", "unknown"),
            for_display  = letter.get("for_display", "Unknown"),
            subject      = letter.get("subject", "(no subject)"),
            content      = letter.get("content", ""),
            access_type  = letter.get("access_type", "babel_pin"),
            access_hash  = "",
            written      = letter.get('written', ''),
        )
        existing_sigs.add(sig)
        imported += 1

    return imported, skipped


def open_folder(path: Path) -> None:
    """Open the folder containing path in the system file manager."""
    import subprocess, sys as _sys
    folder = path.parent if path.is_file() else path
    try:
        if _sys.platform == "win32":
            subprocess.Popen(["explorer", str(folder)])
        elif _sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
    except Exception:
        pass

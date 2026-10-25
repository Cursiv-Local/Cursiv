"""
Suggested memories (U100): what Cursiv *infers* is asked about, not saved silently.

Automatic learning used to save the model's guesses about the person straight into
memory ("Jw prefers a warm, grounded tone…") -- 178 of 194 memories on one computer.
Now a guess waits here as a suggestion; the chat shows "Remember this?" with Save / No,
and only a confirmed one is saved, through the same verified save as "remember …".
Things the person says outright are still saved directly (memory/formation.py).
"""
from __future__ import annotations

import threading
import time
import uuid

MAX_PENDING = 20
_lock = threading.Lock()


def _file():
    from . import semantic
    return semantic.CURSIV_DIR / "memory_suggestions.json"


def _load() -> dict:
    from cursiv_engine.core import state_store
    data = state_store.load(_file(), {})
    return data if isinstance(data, dict) else {}


def add(person: str, texts: list[str], quote: str = "") -> list[dict]:
    """Queue guesses for the person to confirm. Skips ones already pending or already saved."""
    from cursiv_engine.core import state_store
    from . import semantic
    saved = {(f.get("text") or "").strip().lower() for f in semantic.list_facts(person)}
    with _lock:
        data = _load()
        rows = data.setdefault(person, [])
        known = {r["text"].strip().lower() for r in rows}
        new = []
        for text in texts:
            t = (text or "").strip()
            if t and t.lower() not in known and t.lower() not in saved:
                row = {"id": uuid.uuid4().hex[:10], "text": t[:400], "quote": (quote or "")[:500],
                       "at": time.time(), "shown": False}
                rows.append(row)
                new.append(row)
                known.add(t.lower())
        data[person] = rows[-MAX_PENDING:]
        state_store.save(_file(), data)
    return new


def unshown(person: str) -> list[dict]:
    """Suggestions not yet put in front of the person; marks them shown."""
    from cursiv_engine.core import state_store
    with _lock:
        data = _load()
        rows = data.get(person, [])
        out = [dict(r) for r in rows if not r.get("shown")]
        if out:
            for r in rows:
                r["shown"] = True
            state_store.save(_file(), data)
    return out


def pending(person: str) -> list[dict]:
    return list(_load().get(person, []))


def _take(person: str, sid: str) -> dict | None:
    from cursiv_engine.core import state_store
    with _lock:
        data = _load()
        rows = data.get(person, [])
        found = next((r for r in rows if r["id"] == sid), None)
        if found is not None:
            data[person] = [r for r in rows if r["id"] != sid]
            state_store.save(_file(), data)
    return found


def confirm(person: str, sid: str, text: str | None = None) -> str:
    """Save a suggestion the person confirmed (optionally edited), through the verified save."""
    row = _take(person, sid)
    if row is None:
        return "That suggestion was already answered."
    from . import intents
    result = intents.execute(intents.Action(intents.SAVE, content=(text or row["text"]).strip()), person=person)
    if result.ok:
        return f"Saved to memory: {(text or row['text']).strip()} Memory ID: {result.records[0]['id']}; saved and verified."
    return "Not saved: " + result.message


def dismiss(person: str, sid: str) -> str:
    return "Not saved." if _take(person, sid) is not None else "That suggestion was already answered."

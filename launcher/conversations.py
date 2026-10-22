"""
Saved conversations -- kept per person in %USERPROFILE%\\.cursiv\\conversations\\.

Each file holds the messages (so Cursiv can continue with full context) and the
transcript as shown on screen (so council output, translations etc. reappear
exactly). Nothing is saved unless the user chooses to.
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional
from cursiv_v215.core import atomic as _atomic

DIR = Path.home() / ".cursiv" / "conversations"
_writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cursiv-chat-save")
_pending: dict[str, Future] = {}
_failures: dict[str, str] = {}
_pending_lock = threading.RLock()
_storage_lock = threading.RLock()  # autosave, user rename/delete, and background titles


def wait_for_save(conv_id: str | None = None, *, raise_errors: bool = True) -> None:
    """Explicit navigation/save/delete waits for queued snapshots, never overwrites one.

    The executor also drains on normal Python shutdown. Only the worker receives
    immutable message copies and HTML strings, never Qt objects.
    """
    with _pending_lock:
        pending = ([_pending[conv_id]] if conv_id in _pending else []) if conv_id else list(_pending.values())
    for future in pending:
        try:
            future.result()
        except Exception:
            if raise_errors:
                raise
    with _pending_lock:
        errors = ([_failures[conv_id]] if conv_id in _failures else []) if conv_id else list(_failures.values())
    if errors and raise_errors:
        raise OSError(errors[0])


def queue_save(conv_id: str | None, messages: list[dict], html: str, *,
               on_done=None, on_titled=None) -> str:
    """Serialize messages/HTML and write them on one ordered worker.

    Export of new rich-text blocks happens on the GUI thread; no Qt objects
    cross this boundary. The disk format is identical to save(). A failed write
    is surfaced to the panel via on_done.
    """
    import copy
    conv_id = conv_id or uuid.uuid4().hex[:12]
    person, directory = _person(), DIR
    snapshot = copy.deepcopy(messages)

    def work():
        return _save(conv_id, snapshot, html, on_titled=on_titled,
                     person=person, directory=directory)

    with _pending_lock:
        _failures.pop(conv_id, None)
        future = _writer.submit(work)
        _pending[conv_id] = future

    def finished(done):
        error = done.exception()
        with _pending_lock:
            if _pending.get(conv_id) is done:
                _pending.pop(conv_id, None)
                if error:
                    _failures[conv_id] = str(error)
        if on_done:
            try:
                on_done(conv_id, str(error) if error else "")
            except RuntimeError:       # the panel was closed; the save still completed
                pass
    future.add_done_callback(finished)
    return conv_id


def _person() -> str:
    try:
        from cursiv_v215.memory import semantic
        return semantic.current_person()
    except Exception:
        return "family"


_FILLER = re.compile(
    r"^(?:(?:good (?:morning|afternoon|evening)|hi|hello|hey|yo|ok(?:ay)?|so|um|well|cursiv|please|"
    r"can you|could you|would you|will you|i want(?: you)? to|i need(?: you)? to|i'?d like to|"
    r"help me(?: to)?|show me(?: how to)?|tell me(?: about)?|how do i|how can i|what is|what are|"
    r"let'?s|lets)\b[\s,.!?:-]*)+", re.I)


def title_from(messages: list[dict]) -> str:
    """Quick 3-5 word title from the first message (until the AI one is ready)."""
    first = next((m.get("content", "") for m in messages if m.get("role") == "user" and m.get("content")), "")
    text = " ".join(str(first).split())
    text = _FILLER.sub("", text)
    words = re.findall(r"[A-Za-z0-9][\w'+#.-]*", text)
    small = {"the", "a", "an", "and", "or", "to", "of", "for", "with", "my", "your", "me", "please", "in", "on"}
    while words and words[0].lower() in {"the", "a", "an", "please"}:
        words.pop(0)
    words = words[:5]
    while len(words) > 1 and words[-1].lower() in small:
        words.pop()
    if not words:
        return "New conversation"
    return " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in words).rstrip(".")


_TITLE_PROMPT = (
    "Write a 3 to 5 word title that sums up what this conversation is about (its main topic, "
    "not the greeting). Title Case. No quotes, no ending punctuation, no emojis. Reply with the title only."
)


def _clean_title(raw: str) -> str | None:
    line = next((l for l in (raw or "").splitlines() if l.strip()), "")
    line = re.sub(r"^(title\s*:\s*)", "", line.strip(), flags=re.I).strip(" \"'*#`.:")
    words = line.split()
    if not 2 <= len(words) <= 7 or line.startswith("["):
        return None
    return " ".join(words[:6])[:60]


def _smart_title(conv_id: str, messages: list[dict], on_done: Optional[Callable[[], None]]) -> None:
    """Background: ask the AI for a 3-5 word topic title and store it (unless renamed by hand)."""
    parts = []
    for m in messages[:12]:
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            parts.append(f"{'User' if m.get('role') == 'user' else 'Assistant'}: {' '.join(c.split())[:400]}")
    convo = "\n".join(parts)[:3000]
    try:
        from cursiv_v215.ui.chat_app import _quick_llm
        title = _clean_title(_quick_llm([{"role": "system", "content": _TITLE_PROMPT},
                                         {"role": "user", "content": convo}], max_tokens=24))
    except Exception:
        title = None
    if not title:
        return
    try:
        wait_for_save(conv_id)
    except OSError:
        return
    with _storage_lock:
        path = DIR / f"{conv_id}.json"
        d = _load(path)
        if not d or not d.get("title_auto", True):
            return                               # renamed/deleted meanwhile -- keep theirs
        d["title"] = title
        d["titled_at"] = len(messages)
        _atomic.write_text(path, json.dumps(d, ensure_ascii=False))
    if on_done:
        try:
            on_done()
        except Exception:
            pass


def save(conv_id: str | None, messages: list[dict], html: str, title: str | None = None,
         on_titled: Optional[Callable[[], None]] = None) -> str:
    wait_for_save(conv_id, raise_errors=False)   # explicit Save retries a failed autosave
    conv_id = _save(conv_id, messages, html, title, on_titled)
    with _pending_lock:
        _failures.pop(conv_id, None)
    return conv_id


def _save(conv_id: str | None, messages: list[dict], html: str, title: str | None = None,
          on_titled=None, *, person=None, directory=None) -> str:
    with _storage_lock:
        return _write_snapshot(conv_id, messages, html, title, on_titled,
                               person=person, directory=directory)


def _write_snapshot(conv_id, messages, html, title, on_titled, *, person, directory):
    directory = directory if directory is not None else DIR
    directory.mkdir(parents=True, exist_ok=True)
    conv_id = conv_id or uuid.uuid4().hex[:12]
    path = directory / f"{conv_id}.json"
    existing = _load(path) or {}
    data = {
        "id": conv_id,
        "person": existing.get("person") or person or _person(),
        "title": title or existing.get("title") or title_from(messages),
        # auto titles are rewritten by the AI as the chat goes on; a name the user typed is kept
        "title_auto": False if title else existing.get("title_auto", True),
        "titled_at": existing.get("titled_at", 0),
        "created": existing.get("created") or time.time(),
        "updated": time.time(),
        "messages": messages,
        "html": html,
    }
    tmp = path.with_suffix(".tmp")
    with tmp.open('w', encoding='utf-8') as stream:
        # Streaming JSON avoids a second complete encoded conversation in RAM.
        json.dump(data, stream, ensure_ascii=False)
    tmp.replace(path)
    # AI title: once there's an exchange, and again as the topic develops
    if data["title_auto"] and len(messages) >= 2 and (
            data["titled_at"] == 0 or len(messages) - data["titled_at"] >= 10):
        threading.Thread(target=_smart_title, args=(conv_id, list(messages), on_titled), daemon=True).start()
    return conv_id


def load(conv_id: str) -> dict | None:
    wait_for_save(conv_id)
    return _load(DIR / f"{conv_id}.json")


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_all() -> list[dict]:
    """This person's conversations, newest first (without the bulky fields)."""
    person = _person()
    out = []
    for f in DIR.glob("*.json") if DIR.exists() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("person", person) != person:
            continue
        out.append({"id": d["id"], "title": d.get("title", "Conversation"), "updated": d.get("updated", 0)})
    return sorted(out, key=lambda c: c["updated"], reverse=True)


def _old_style_title(messages: list[dict]) -> str:
    """How titles were made before U49 (first line of the chat), to spot untouched ones."""
    first = next((m.get("content", "") for m in messages if m.get("role") == "user" and m.get("content")), "")
    first = " ".join(str(first).split())
    return (first[:48] + "…") if len(first) > 48 else (first or "New conversation")


def retitle_old(on_done: Optional[Callable[[], None]] = None) -> None:
    """One-time, in the background: give older saved chats a 3-5 word topic title.
    Only ones still named after their first line (never ones renamed by hand)."""
    def work():
        for f in sorted(DIR.glob("*.json")) if DIR.exists() else []:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if d.get("titled_at") or "title_auto" in d:
                continue
            msgs = d.get("messages") or []
            if d.get("title") != _old_style_title(msgs) or len(msgs) < 2:
                d["title_auto"] = d.get("title") == _old_style_title(msgs)
                _atomic.write_text(f, json.dumps(d, ensure_ascii=False))
                continue
            d["title"], d["title_auto"] = title_from(msgs), True
            _atomic.write_text(f, json.dumps(d, ensure_ascii=False))
            if on_done:
                on_done()
            _smart_title(d["id"], msgs, on_done)
    threading.Thread(target=work, daemon=True).start()


def rename(conv_id: str, title: str) -> None:
    wait_for_save(conv_id)
    with _storage_lock:
        path = DIR / f"{conv_id}.json"
        d = _load(path)
        if d and title.strip():
            d["title"] = title.strip()[:80]
            d["title_auto"] = False
            _atomic.write_text(path, json.dumps(d, ensure_ascii=False))


def delete(conv_id: str) -> None:
    wait_for_save(conv_id)
    with _storage_lock:
        (DIR / f"{conv_id}.json").unlink(missing_ok=True)

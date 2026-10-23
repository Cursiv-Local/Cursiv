"""
Per-person memory for the phone app (runs in the background on the linked computer).

  Phone -> computer: new phone conversations are read and lasting facts are
  learned into the linked person's own memory (memory/semantic.py), exactly
  like desktop chats.
  Computer -> phone: a short summary of that person's memories is uploaded to
  their phone space, so phone answers know them -- only while "share memories
  with the phone app" is on (the phone's AI runs on the owner's Cloudflare
  site, so the summary is stored there). Turning it off deletes the summary.
"""
from __future__ import annotations

import hashlib
import json
import threading
import urllib.request

import phone_link as pl

_lock = threading.Lock()


def _state() -> dict:
    try:
        return json.loads(pl.SPACE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    pl.SPACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    pl.SPACE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def share_enabled() -> bool:
    return _state().get("share_memory", True)


def set_share(on: bool) -> None:
    st = _state()
    st["share_memory"] = bool(on)
    st.pop("digest_hash", None)          # force an upload (or a clear) on the next sync
    _save_state(st)
    threading.Thread(target=sync_once, daemon=True).start()


def _person(st: dict) -> str:
    if st.get("person"):
        return st["person"]
    try:
        from cursiv_v215.memory import semantic
        return semantic.current_person()
    except Exception:
        return "family"


def _digest(person: str) -> str:
    from cursiv_v215.memory import semantic
    facts = semantic.list_facts(person)
    return "\n".join(f"- {f['text']}" for f in facts[-25:])


class _NoEngine(Exception):
    pass


def _learner():
    """Optional extraction uses only the local model, like desktop learning.
    No ready model: defer this exchange; deterministic facts need no model."""
    from cursiv_v215.ui import chat_app as ca

    def ask(messages):
        out = ca._memory_llm(messages)
        if not out:
            raise _NoEngine()
        return out
    return ask


def sync_once() -> str:
    """Learn from new phone messages, then upload/clear the memory summary.
    Safe to call any time; does nothing if this computer isn't linked."""
    if not _lock.acquire(blocking=False):
        return "busy"
    try:
        st = _state()
        token = st.get("token")
        if not token:
            return "not linked"
        person = _person(st)
        learned = 0

        # Phone -> computer: learn from new exchanges
        try:
            since = st.get("learned_until", "")
            msgs = pl.api("/api/space/messages?since=" + urllib.request.quote(since), token=token, timeout=20)["messages"]
        except Exception as exc:
            return f"couldn't reach the phone space: {exc}"
        if msgs:
            from cursiv_v215.memory import semantic
            base = _learner()
            failed = []

            def ask(messages):
                try:
                    return base(messages)
                except _NoEngine:
                    failed.append(1)
                    raise
            pending_user = None
            for m in msgs:
                if m["role"] == "user":
                    pending_user = m
                elif m["role"] == "assistant" and pending_user is not None:
                    learned += len(semantic.learn_from_exchange(pending_user["text"], m["text"], ask, person,
                                                               event_id='phone:' + str(m['created'])))
                    if failed:                # no AI available right now -- retry this pair next time
                        break
                    st["learned_until"] = m["created"]
                    pending_user = None

        # Computer -> phone: the memory summary (or clear it when sharing is off)
        digest = _digest(person) if st.get("share_memory", True) else ""
        h = hashlib.sha1(digest.encode("utf-8"), usedforsecurity=False).hexdigest()
        if h != st.get("digest_hash"):
            try:
                pl.api("/api/space/memory", {"digest": digest, "person": person}, token, timeout=20)
                st["digest_hash"] = h
            except Exception:
                pass
        _save_state(st)
        return f"learned {learned} fact(s); summary {'shared' if digest else 'not shared'}"
    finally:
        _lock.release()

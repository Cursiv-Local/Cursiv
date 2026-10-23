"""
Session Logger — Cursiv v2.1.5

Persists every conversation exchange to .cursiv/sessions/YYYY-MM-DD.jsonl.
On restart the system loads the last session's context into the system prompt
and greets the user with a summary of what was happening.

Files:
  .cursiv/sessions/YYYY-MM-DD.jsonl  — one file per day, one JSON line per exchange
"""
from __future__ import annotations
from cursiv_engine.core import private_store, vault

import json
import time
from datetime import datetime, date
from pathlib import Path
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)

ROOT         = Path(__file__).parent.parent.parent
CURSIV_DIR   = APP_DATA
SESSIONS_DIR = CURSIV_DIR / "sessions"
MEMORY_FILE  = CURSIV_DIR / "memory.json"
RATED_JSONL  = CURSIV_DIR / "rated_exchanges.jsonl"


def _append_memory_run(user_msg: str, ai_msg: str, model: str, quality: float = 0.70) -> None:
    """Write this exchange to memory.json["runs"] (the session record)."""
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    try:
        mem = json.loads(private_store.read_text(MEMORY_FILE, encoding="utf-8")) if MEMORY_FILE.exists() else {}
    except vault.VaultError:
        raise
    except Exception:
        mem = {}
    runs = mem.get("runs", [])
    runs.append({
        "agent_id":         model,
        "timestamp":        time.time(),
        "quality":          round(quality, 3),
        "query":            user_msg.strip()[:500],
        "response_preview": ai_msg.strip()[:500],
    })
    if len(runs) > 500:
        runs = runs[-500:]
    mem["runs"] = runs
    try:
        private_store.write_text(MEMORY_FILE,
            json.dumps(mem, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_last_exchange() -> dict | None:
    """Return the most recently logged exchange, or None if no history exists."""
    files = sorted(SESSIONS_DIR.glob("*.jsonl"), reverse=True) if SESSIONS_DIR.exists() else []
    for f in files:
        entries = _load_file(f)
        if entries:
            return entries[-1]
    return None


def _today_file() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR / f"{date.today().isoformat()}.jsonl"


def append_exchange(user_msg: str, ai_msg: str, model: str = "unknown") -> None:
    """Append a completed exchange to today's session file."""
    if not (user_msg or "").strip() or not (ai_msg or "").strip():
        return
    entry = {
        "ts":    datetime.now().isoformat(),
        "user":  user_msg.strip()[:3000],
        "ai":    ai_msg.strip()[:3000],
        "model": model,
    }
    try:
        private_store.append_text(_today_file(), json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    _append_memory_run(user_msg, ai_msg, model)


def _load_file(path: Path) -> list[dict]:
    entries: list[dict] = []
    try:
        with private_store.lines(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
    except vault.VaultError:
        raise
    except Exception:
        pass
    return entries


def get_boot_summary() -> dict:
    """
    Return summary of the most recent session for the CLI boot greeting.
    Keys: date, count, is_today, last_topics (list[str]), last_model
    Returns empty dict if no prior sessions.
    """
    files = sorted(SESSIONS_DIR.glob("*.jsonl"), reverse=True) if SESSIONS_DIR.exists() else []
    for f in files:
        entries = _load_file(f)
        if not entries:
            continue
        try:
            session_date = date.fromisoformat(f.stem)
        except Exception:
            continue

        # Extract short topic labels from last few user messages
        topics = []
        for e in entries[-4:]:
            u = (e.get("user") or "").strip()
            if u:
                topics.append(u[:80].replace("\n", " "))

        last_model = entries[-1].get("model", "?") if entries else "?"
        return {
            "date":       f.stem,
            "count":      len(entries),
            "is_today":   session_date == date.today(),
            "last_topics": topics,
            "last_model":  last_model,
        }
    return {}


def load_session_context(max_exchanges: int = 4) -> str:
    """
    Return a formatted block for injection into the system prompt.
    Includes the last N exchanges from the most recent session.
    Returns empty string if no history exists.
    """
    files = sorted(SESSIONS_DIR.glob("*.jsonl"), reverse=True) if SESSIONS_DIR.exists() else []
    for f in files:
        entries = _load_file(f)
        if not entries:
            continue
        try:
            session_date = date.fromisoformat(f.stem)
        except Exception:
            continue

        recent = entries[-max_exchanges:]
        date_label = "today (earlier)" if session_date == date.today() else f.stem
        lines = [
            f"\n\n---\n## SESSION MEMORY ({date_label} — {len(entries)} exchanges total)\n",
            "Recent exchanges (oldest first):\n",
        ]
        for e in recent:
            ts_raw = e.get("ts", "")
            try:
                ts = datetime.fromisoformat(ts_raw).strftime("%H:%M")
            except Exception:
                ts = "--:--"
            u = (e.get("user") or "")[:200].replace("\n", " ")
            a = (e.get("ai")   or "")[:200].replace("\n", " ")
            m = e.get("model", "?")
            lines.append(f"[{ts}] You: {u}")
            lines.append(f"[{ts}] {m}: {a}\n")
        lines.append("---")
        return "\n".join(lines)
    return ""

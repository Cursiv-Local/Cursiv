"""
Offline Queue — capture cloud-dependent tasks, fire when back online.

Tasks are written to .cursiv/offline_queue.jsonl.
Each entry stores the prompt, timestamp, and optional tags.
Call flush() to replay queued tasks through a provided executor.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)

_CURSIV_ROOT = Path(__file__).resolve().parent.parent.parent
_QUEUE_FILE  = APP_DATA / "offline_queue.jsonl"


def _ensure_dir() -> None:
    _QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)


def enqueue(prompt: str, tags: list[str] | None = None, note: str = "") -> dict[str, Any]:
    """Add a task to the offline queue. Returns the queued entry."""
    _ensure_dir()
    entry: dict[str, Any] = {
        "id":        datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "timestamp": datetime.now().isoformat(),
        "prompt":    prompt.strip(),
        "tags":      tags or [],
        "note":      note,
        "status":    "queued",
    }
    with _QUEUE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def list_queued() -> list[dict[str, Any]]:
    """Return all queued (not yet fired) tasks."""
    if not _QUEUE_FILE.exists():
        return []
    tasks = []
    for line in _QUEUE_FILE.read_text(encoding="utf-8").splitlines():
        try:
            t = json.loads(line)
            if t.get("status") == "queued":
                tasks.append(t)
        except Exception:
            pass
    return tasks


def count() -> int:
    return len(list_queued())


def flush(executor: Callable[[str], str]) -> list[dict[str, Any]]:
    """
    Fire all queued tasks through executor(prompt) -> response.
    Marks each as 'fired' with the response inline.
    Returns list of results.
    """
    if not _QUEUE_FILE.exists():
        return []

    lines = _QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    results = []
    updated_lines = []

    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            updated_lines.append(line)
            continue

        if entry.get("status") != "queued":
            updated_lines.append(line)
            continue

        try:
            response = executor(entry["prompt"])
            entry["status"]   = "fired"
            entry["response"] = response
            entry["fired_at"] = datetime.now().isoformat()
            results.append(entry)
        except Exception as e:
            entry["status"] = "error"
            entry["error"]  = str(e)
            results.append(entry)

        updated_lines.append(json.dumps(entry))

    _QUEUE_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return results


def clear_fired() -> int:
    """Remove all fired/error entries from the queue file. Returns count removed."""
    if not _QUEUE_FILE.exists():
        return 0
    lines = _QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    keep = []
    removed = 0
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get("status") == "queued":
                keep.append(line)
            else:
                removed += 1
        except Exception:
            keep.append(line)
    _QUEUE_FILE.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
    return removed


def format_queue() -> str:
    """Human-readable queue summary for display in the UI/CLI."""
    tasks = list_queued()
    if not tasks:
        return "[Offline Queue] Empty — nothing pending."
    lines = [f"[Offline Queue] {len(tasks)} task(s) waiting:\n"]
    for i, t in enumerate(tasks, 1):
        ts   = t.get("timestamp", "?")[:16].replace("T", " ")
        tags = ", ".join(t.get("tags", [])) or "no tags"
        prompt = t["prompt"][:80] + ("…" if len(t["prompt"]) > 80 else "")
        lines.append(f"  {i}. [{ts}] ({tags}) {prompt}")
    return "\n".join(lines)

"""
Where Cursiv keeps what it remembers and learns, counted from the files just now.

`self stores` lists each store with its location, how many records it holds and
whether it is put into answers. Counting only reads; nothing is changed. A count
says how many records exist, not that any of them was used for an answer.
"""
from __future__ import annotations

import json
from pathlib import Path


def _lines(path: Path) -> int | None:
    try:
        from . import private_store
        return sum(1 for line in private_store.read_text(path, errors="replace").splitlines() if line.strip())
    except FileNotFoundError:
        return 0
    except Exception:
        return None


def _files(folder: Path, pattern: str = "*.json") -> int:
    try:
        return sum(1 for _ in folder.glob(pattern)) if folder.is_dir() else 0
    except OSError:
        return 0


def inventory(person: str) -> list[dict]:
    """[{name, where, count, detail, feeds}] -- feeds: how it reaches answers."""
    from .paths import APP_DATA
    home = Path.home() / ".cursiv"
    rows: list[dict] = []

    def add(name, where, count, feeds, detail=""):
        rows.append({"name": name, "where": str(where), "count": count, "feeds": feeds, "detail": detail})

    try:
        from cursiv_engine.memory import semantic
        facts = semantic.list_facts(person)
        said = sum(1 for f in facts if semantic.origin_of(f) != "inferred")
        add("Memories about you", semantic.FACTS_FILE, len(facts),
            "matched to each question and added as \"what you remember\"",
            f"{said} you said or saved, {len(facts) - said} inferred by Cursiv")
    except Exception as exc:
        add("Memories about you", APP_DATA / "memory_facts.jsonl", None, "", f"unreadable: {exc}")
    try:
        from . import strand_store
        add("Saved notes", strand_store.STRANDS_FILE, strand_store.strand_count(),
            "matched to each question and added as \"related earlier conversations\"")
    except Exception as exc:
        add("Saved notes", APP_DATA / "strands.jsonl", None, "", f"unreadable: {exc}")
    try:
        from . import style
        add("Style preferences", style._path(person), len(style.load(person).get("rules", [])),
            "added to every answer as this person's style preferences")
    except Exception:
        add("Style preferences", Path.home() / ".cursiv" / "style", None, "")
    add("Saved conversations", home / "conversations", _files(home / "conversations"),
        "only the conversation you are in is sent; others are not")
    try:
        from . import fieldlog
        add("Field notebook entries", fieldlog.log_file(), len(fieldlog.entries()),
            "read only for notebook commands and notebook questions")
    except Exception:
        add("Field notebook entries", home / "fieldlog", None, "")
    try:
        from . import documents
        add("Imported documents", home / "documents", len(documents.library()),
            "searched only when a question matches an imported document")
    except Exception:
        add("Imported documents", home / "documents", None, "")
    add("Project summaries", home / "projects", _files(home / "projects"),
        "added when a question mentions a tracked project")
    add("Session memory", APP_DATA / "sessions", _files(APP_DATA / "sessions", "*.jsonl"),
        "the last few exchanges of the latest session file are added as \"session memory\", even from an earlier day")
    add("Answer ratings (feedback)", APP_DATA / "rated_exchanges.jsonl", _lines(APP_DATA / "rated_exchanges.jsonl"),
        "saved only; nothing reads it back into answers")
    add("Training examples (feedback)", APP_DATA / "training_data.jsonl", _lines(APP_DATA / "training_data.jsonl"),
        "kept for optional local training; not added to answers")
    try:
        from cursiv_engine.coding import brain
        add("Coding lessons (feedback)", brain.LESSONS_FILE, _lines(brain.LESSONS_FILE),
            "added to coding answers")
    except Exception:
        pass
    try:
        council = json.loads((APP_DATA / "council_memory.json").read_text(encoding="utf-8"))
        n = len(council) if isinstance(council, (list, dict)) else None
    except FileNotFoundError:
        n = 0
    except Exception:
        n = None
    add("Old council conclusions", APP_DATA / "council_memory.json", n, "no longer used (the council was removed)")
    return rows


def summary(person: str) -> str:
    rows = inventory(person)
    out = ["Counted from Cursiv's files just now (nothing was changed). A count shows what exists, "
           "not that it was used for a particular answer.", ""]
    for r in rows:
        count = "unreadable" if r["count"] is None else f"{r['count']:,}"
        line = f"- **{r['name']}**: {count}"
        if r["detail"]:
            line += f" ({r['detail']})"
        if r["feeds"]:
            line += f". How it's used: {r['feeds']}."
        out.append(line + f"\n  {r['where']}")
    out += ["", "Review misleading notes and memories: memory cleanup"]
    return "\n".join(out)


def evidence_block(person: str, budget: int = 1200) -> str:
    rows = [f"- {r['name']}: {'unreadable' if r['count'] is None else r['count']}"
            + (f" ({r['detail']})" if r["detail"] else "") + (f"; {r['feeds']}" if r["feeds"] else "")
            for r in inventory(person)]
    return ("Counted from Cursiv's files just now:\n" + "\n".join(rows))[:budget]

"""
Your memory as readable markdown files (U100) -- "show my memory folder".

One .md file per saved memory, with a short header (kind, where it came from, dates,
ID), a MEMORY.md index with one line per memory, plus your style rules and project
summaries. It's a readable copy for looking through: the memory itself stays in
Cursiv's store (encrypted on a computer), and changes are made with "remember …",
"forget …" or the "What I remember" window.

On a Cursiv USB drive the folder is the drive's own readable `memory-files`; on a
computer the person chooses where to put a copy, and is told it's readable.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

INDEX = "MEMORY.md"


def _slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())[:6]
    return "-".join(words) or "memory"


def _date(ts) -> str:
    try:
        return time.strftime("%Y-%m-%d", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return str(ts or "")[:10]


def _kind(fact: dict) -> str:
    text = (fact.get("text") or "").lower()
    if re.search(r"\b(prefer|likes? (?:short|long|brief)|tone|answer|style)\b", text):
        return "how to answer"
    if re.search(r"\b(site|creek|pond|river|plot|transect|station)\b", text):
        return "places and sites"
    if re.search(r"\b(project|working on|building|thesis|survey)\b", text):
        return "project"
    return "about you"


def export(person: str, folder: Path) -> dict:
    """Write the readable copy into `folder` (replacing an earlier copy made here).
    Returns {"memories": n, "index": path}."""
    from . import semantic
    from cursiv_engine.core import atomic
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.md"):
        if old.read_text(encoding="utf-8", errors="replace").startswith("<!-- cursiv memory file -->"):
            old.unlink()
    facts = semantic.list_facts(person)
    index = [f"<!-- cursiv memory file -->\n# What Cursiv remembers about {person.title()}",
             f"A readable copy made {time.strftime('%Y-%m-%d %H:%M')}. Changing these files doesn't change "
             "Cursiv's memory: use \"remember …\", \"forget …\" or the \"What I remember\" window.", ""]
    by_kind: dict[str, list[str]] = {}
    for f in facts:
        text = (f.get("text") or "").strip()
        if not text:
            continue
        origin = semantic.origin_label(f) if hasattr(semantic, "origin_label") else semantic.origin_of(f)
        name = f"{_slug(text)}-{str(f.get('id', ''))[:6]}.md"
        kind = _kind(f)
        body = (f"<!-- cursiv memory file -->\n# {text[:80]}\n\n- Kind: {kind}\n- Came from: {origin}\n"
                f"- Saved: {_date(f.get('created') or f.get('ts'))}\n- Memory ID: {f.get('id', '')}\n\n{text}\n")
        atomic.write_bytes(folder / name, body.encode("utf-8"), protect=False)
        by_kind.setdefault(kind, []).append(f"- [{text[:90]}]({name}) — {origin}")
    for kind in ("about you", "how to answer", "places and sites", "project"):
        if by_kind.get(kind):
            index += [f"## {kind.capitalize()}", *by_kind[kind], ""]
    try:
        from cursiv_engine.core import style
        rules = [r.get("text", "") for r in style.load(person).get("rules", []) if r.get("text")]
    except Exception:
        rules = []
    if rules:
        atomic.write_bytes(folder / "how-to-answer.md", ("<!-- cursiv memory file -->\n# How you've asked me to answer\n\n"
                           + "\n".join(f"- {r}" for r in rules) + "\n").encode("utf-8"), protect=False)
        index += ["## Style rules", "- [How you've asked me to answer](how-to-answer.md)", ""]
    try:
        from . import projects
        summaries = projects.load(person)
    except Exception:
        summaries = {}
    if summaries:
        rows = [f"## {name}\n{(p.get('summary') if isinstance(p, dict) else p) or ''}" for name, p in summaries.items()]
        atomic.write_bytes(folder / "projects.md", ("<!-- cursiv memory file -->\n# Projects\n\n" + "\n\n".join(rows)
                           + "\n").encode("utf-8"), protect=False)
        index += ["## Projects", "- [Project summaries](projects.md)", ""]
    atomic.write_bytes(folder / INDEX, ("\n".join(index).rstrip() + "\n").encode("utf-8"), protect=False)
    return {"memories": sum(len(v) for v in by_kind.values()), "index": folder / INDEX}


def portable_folder() -> Path | None:
    """On a Cursiv USB drive: the drive's readable memory-files folder; otherwise None."""
    import os
    if os.environ.get("CURSIV_PORTABLE") != "1":
        return None
    return Path.home() / ".cursiv" / "memory-files"

"""
Guidance files (U100): the person's own words and folder layout, in markdown.

  * how-i-talk.md (~/.cursiv/guidance/, encrypted on a computer): "when I say the creek I
    mean North Creek". Given to the conversational-action step (core/intent.py) as the
    person's vocabulary, and used to expand their words before Cursiv checks a proposal,
    so "log the creek at 14 C" can propose site North Creek.
  * CURSIV.md in the workspace (optional, readable, like CLAUDE.md in a repo): the folder
    map -- what goes where and how files are named. Given to the action step so file
    proposals land in the right folder.

Markdown teaches words and layout only. The list of allowed actions, every check and the
confirm card stay in code: no guidance file can give the model new powers.
"""
from __future__ import annotations

import re
from pathlib import Path

DIR = Path.home() / ".cursiv" / "guidance"
HINTS = "how-i-talk.md"
MAP = "CURSIV.md"
_LINE = re.compile(r'^- "(.+?)" means "(.+?)"\s*$', re.M)
SAY = re.compile(r"""(?i)^\s*when i say\s+["'“]?(.+?)["'”]?\s*,?\s+i mean\s+["'“]?(.+?)["'”]?\s*[.!]?\s*$""")


def hints() -> list[tuple[str, str]]:
    from . import private_store
    try:
        text = private_store.read_text(DIR / HINTS)
    except FileNotFoundError:
        return []
    return [(a.strip(), b.strip()) for a, b in _LINE.findall(text)]


def add_hint(phrase: str, meaning: str) -> str:
    phrase, meaning = phrase.strip().strip(".")[:60], meaning.strip().strip(".")[:120]
    if len(phrase) < 2 or len(meaning) < 2:
        return "Tell me both parts, for example: when I say the creek I mean North Creek."
    rows = [(a, b) for a, b in hints() if a.lower() != phrase.lower()] + [(phrase, meaning)]
    body = ("# How I talk\n\nWords I use and what I mean by them. Cursiv uses these to understand requests; "
            "they don't give it any new abilities.\n\n" + "\n".join(f'- "{a}" means "{b}"' for a, b in rows) + "\n")
    from . import atomic, private_store
    atomic.write_bytes(DIR / HINTS, body.encode("utf-8"))
    if private_store.read_text(DIR / HINTS) != body:
        raise OSError("Hint read-back verification failed")
    return f'Saved: when you say "{phrase}" you mean "{meaning}". ({len(rows)} hint(s) in how-i-talk.md)'


def command(text: str) -> str | None:
    m = SAY.match(text or "")
    return add_hint(m.group(1), m.group(2)) if m else None


def expand(said: str) -> str:
    """The person's words plus what their own phrases mean, for checking a proposal."""
    extra = [meaning for phrase, meaning in hints() if re.search(rf"(?i)\b{re.escape(phrase)}\b", said or "")]
    return (said or "") + ("\n" + "\n".join(extra) if extra else "")


def folder_map(workspace: str | Path | None) -> str:
    if not workspace:
        return ""
    try:
        text = (Path(workspace) / MAP).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[:2000]


def prompt_block(workspace: str | Path | None = None) -> str:
    parts = []
    rows = hints()
    if rows:
        parts.append("The person's own words (use these meanings):\n" +
                     "\n".join(f'- "{a}" means "{b}"' for a, b in rows[:30]))
    layout = folder_map(workspace)
    if layout:
        parts.append("Their workspace folder map (CURSIV.md) -- put new files where it says:\n" + layout)
    return ("\n\n" + "\n\n".join(parts)) if parts else ""


def draft_map(workspace: str | Path) -> str:
    """A first CURSIV.md from the folders that are already there (two levels), for the person to confirm."""
    root = Path(workspace)
    lines = ["# Workspace map", "", "What goes where in this folder. Cursiv reads this to put new files in the "
             "right place; edit it any time.", "", "## Layout", ""]
    try:
        top = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError:
        top = []
    for d in top[:25]:
        files = [f.suffix.lower() for f in d.iterdir() if f.is_file()][:200] if d.exists() else []
        kinds = ", ".join(sorted({s for s in files if s})[:4])
        lines.append(f"- `{d.name}/` — " + (f"holds {kinds} files" if kinds else "describe what goes here"))
        for sub in sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith("."))[:8]:
            lines.append(f"  - `{d.name}/{sub.name}/`")
    if not top:
        lines.append("- (no folders yet) — for example: `data/raw/` instrument downloads, `reports/` write-ups")
    lines += ["", "## Naming", "", "- Reports: `YYYY-MM-DD-site.md` (edit to match how you name things)", ""]
    return "\n".join(lines)

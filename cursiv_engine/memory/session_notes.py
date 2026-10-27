"""
Session notes (U100): Cursiv's own CLAUDE.md for each conversation.

A short markdown note per conversation -- goal, what was done, what was decided,
what's open, the next step -- kept up to date as you talk, and put first in the
instructions when the conversation is picked up again, so Cursiv knows where you
left off. Stored in ~/.cursiv/session_notes/<conversation>.md (encrypted on a computer).

Two kinds of line, labelled apart:
  * Done -- only from Cursiv's own results in the conversation (a notebook save with its
    record ID, a saved memory, a file written). Never from the model.
  * Goal / Decided / Open / Next -- a summary written by the local model from what was
    said, marked as such, and only lines that are mostly the person's own words (Decided only when
    they decided something). `session note` shows it; `session note clear` starts it over.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable

DIR = Path.home() / ".cursiv" / "session_notes"
EVERY = 3                      # model summary refreshed every N exchanges
_active: dict = {"conv": "", "note": ""}

# Application-written result lines (native commands), never model prose.
_DONE = (
    (re.compile(r"^Logged\.\s*(.+?)\s*Record ([0-9a-f]{6,})", re.M), lambda m: f"Logged to the field notebook: {m[1].rstrip('.')} (record {m[2]})"),
    (re.compile(r"^Saved to memory: (.+?)(?: Memory ID: ([0-9a-f]+))?;?\s*(?:saved and verified\.)?$", re.M),
     lambda m: f"Saved to memory: {m[1].strip()}"),
    (re.compile(r"^Saved and verified: (\S.+?) \(\d+ bytes\)", re.M), lambda m: f"Wrote the file {m[1]}"),
    (re.compile(r"^Appended to (\S+)", re.M), lambda m: f"Added a line to {m[1]}"),
    (re.compile(r"^Forgotten:\s*\n- (.+)$", re.M), lambda m: f"Forgot the memory: {m[1].strip()}"),
    (re.compile(r"^Workspace → (.+)$", re.M), lambda m: f"Workspace set to {m[1].strip()}"),
)

SUMMARY_PROMPT = """You keep a short note so a conversation can be picked up later. From the conversation
below, write exactly these four lines, using only what was said (write "not stated" if it wasn't):
Goal: <what the person is working on, one line>
Decided: <decisions made, separated by "; ">
Open: <questions or tasks still open, separated by "; ">
Next: <the next step, one line>
No other text."""


def path(conv_id: str, *, folder: Path | None = None) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", conv_id or "")[:64]
    return (DIR if folder is None else folder) / f"{safe}.md"


def done_lines(history: list[dict]) -> list[str]:
    out = []
    for m in history or []:
        if m.get("role") != "assistant" or not isinstance(m.get("content"), str):
            continue
        for pattern, fmt in _DONE:
            for match in pattern.finditer(m["content"]):
                out.append(fmt(match))
    return list(dict.fromkeys(out))[-12:]


def _summary(history: list[dict], ask: Callable[[list[dict]], str]) -> dict:
    turns = [f"{m['role']}: {str(m.get('content', ''))[:600]}" for m in (history or [])[-16:]
             if m.get("role") in ("user", "assistant")]
    try:
        raw = ask([{"role": "system", "content": SUMMARY_PROMPT},
                   {"role": "user", "content": "\n".join(turns)[:7000]}]) or ""
    except Exception:
        return {}
    said = " ".join(str(m.get("content", "")) for m in history or [] if m.get("role") == "user").lower()
    out = {}
    for key in ("Goal", "Decided", "Open", "Next"):
        m = re.search(rf"(?im)^\s*{key}\s*:\s*(.+)$", raw)
        if not m:
            continue
        # U100 review: the live model wrote "Decided: record temperature at 14.2 °C for Tuesday sampling"
        # (nobody decided that) and "Open: No further questions or tasks stated". A line is kept only
        # when it isn't a "nothing" line and most of its words come from what the person said;
        # Decided also needs the person to have decided something.
        items = [i.strip() for i in m.group(1).split(";") if i.strip() and not _NOTHING.search(i)]
        items = [i for i in items if _from_person(i, said, 0.5 if key == "Decided" else 0.34)]
        if key == "Decided" and not _DECIDING.search(said):
            items = []
        if items:
            out[key] = "; ".join(items)[:300]
    return out


_NOTHING = re.compile(r"(?i)^\s*(?:not stated|none|n/?a|nothing|no (?:further |other |open )?(?:questions?|tasks?|"
                      r"decisions?|next steps?)\b.*|unknown)\s*\.?\s*$")
_DECIDING = re.compile(r"(?i)\b(?:decid\w*|agreed?|let'?s|we'?ll|i'?ll|go with|going with|the plan is|chose|choose|settled on)\b")


def _from_person(item: str, said: str, share: float) -> bool:
    """Enough of the line's words (by stem: "Tuesday's" ~ "Tuesday") are the person's own."""
    stems = {w[:5] for w in re.findall(r"[a-z0-9]{3,}", said)}
    words = [w for w in re.findall(r"[a-z0-9]{3,}", item.lower())
             if w not in ("the", "and", "for", "with", "that", "this", "from", "into", "their", "person", "user")]
    return bool(words) and sum(w[:5] in stems for w in words) / len(words) >= share


def render(title: str, done: list[str], summary: dict) -> str:
    rows = [f"# {title or 'Conversation'}", f"Updated: {time.strftime('%Y-%m-%d %H:%M')}", ""]
    if summary.get("Goal"):
        rows += [f"Goal: {summary['Goal']}", ""]
    if done:
        rows += ["Done (from Cursiv's own records):"] + [f"- {d}" for d in done] + [""]
    for key in ("Decided", "Open"):
        if summary.get(key):
            rows += [f"{key}:"] + [f"- {p.strip()}" for p in summary[key].split(";") if p.strip()] + [""]
    if summary.get("Next"):
        rows += [f"Next: {summary['Next']}", ""]
    if summary:
        rows.append("(Goal, Decided, Open and Next were summarised by the AI model from the conversation.)")
    return "\n".join(rows).rstrip() + "\n"


def load(conv_id: str, *, folder: Path | None = None) -> str:
    if not conv_id:
        return ""
    from cursiv_engine.core import private_store
    try:
        return private_store.read_text(path(conv_id, folder=folder))
    except FileNotFoundError:
        return ""


def save(conv_id: str, text: str, *, folder: Path | None = None) -> None:
    from cursiv_engine.core import atomic
    atomic.write_bytes(path(conv_id, folder=folder), text.encode("utf-8"))


def update(conv_id: str, title: str, history: list[dict], ask: Callable[[list[dict]], str] | None = None,
           *, force: bool = False, folder: Path | None = None, valid: Callable[[], bool] = lambda: True) -> str:
    """Rebuild the note. The model summary is refreshed every EVERY exchanges (or when forced);
    otherwise the previous summary lines are kept and only Done is recomputed."""
    if not conv_id or not history or not valid():
        return ""
    folder = DIR if folder is None else folder
    exchanges = sum(m.get("role") == "user" for m in history)
    previous = load(conv_id, folder=folder)
    summary = {k: v for k, v in (
        (k, (re.search(rf"(?m)^{k}: (.+)$", previous) or [None, None])[1]) for k in ("Goal", "Next")) if v}
    for key in ("Decided", "Open"):
        block = re.search(rf"(?ms)^{key}:\n((?:- .+\n?)+)", previous)
        if block:
            summary[key] = "; ".join(ln[2:].strip() for ln in block.group(1).splitlines() if ln.startswith("- "))
    if ask is not None and (force or exchanges % EVERY == 0 or not summary):
        if not valid():
            return ""
        fresh = _summary(history, ask)
        if fresh:
            summary = fresh
    note = render(title, done_lines(history), summary)
    if not valid():
        return ""
    save(conv_id, note, folder=folder)
    return note


def picking_up(note: str) -> str:
    """One line for the top of a reopened conversation."""
    title = (re.search(r"(?m)^# (.+)$", note) or [None, ""])[1]
    nxt = (re.search(r"(?m)^Next: (.+)$", note) or [None, ""])[1]
    goal = (re.search(r"(?m)^Goal: (.+)$", note) or [None, ""])[1]
    bits = [b for b in (goal or title, f"next: {nxt}" if nxt else "") if b]
    return "Picking up: " + " — ".join(bits) if bits else ""


# ── the conversation the window is in (one chat window per process) ──────────

def set_active(conv_id: str) -> str:
    note = load(conv_id) if conv_id else ""
    _active.update(conv=conv_id or "", note=note)
    return note


def prompt_block() -> str:
    """Put first in the instructions when a conversation with a note is picked up."""
    note = _active.get("note") or ""
    if not note.strip():
        return ""
    return ("\n\n## Where this conversation left off (Cursiv's session note)\n" + note.strip()[:2500] +
            "\nUse it to continue. Lines under \"Done\" are Cursiv's records; the rest is a summary and may be "
            "incomplete.\n")

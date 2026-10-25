"""The quiet visual pieces of the chat: answer badges, receipts, starters, notices.

Pure functions that return Qt rich-text HTML in the start palette (the caller
passes it through theme.live()). Nothing here decides what is true: the text
inside each piece comes from Cursiv's own status lines and command results.

Three kinds of reply look different on purpose:
  * worked out by Cursiv (calculations, notebook, memory, files) -- a green "✓" badge
    or a receipt card, because no AI model wrote it;
  * an AI model's answer -- a small grey "Local · model" / "Online · provider" badge;
  * system notices (offline on, removed features) -- a soft card, not a log line.
"""
from __future__ import annotations

import re

import theme


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── Badges under an answer ───────────────────────────────────────────────────

_NO_MODEL = re.compile(r"\(no AI model\)|; no AI model\)|no AI model\)$")


def _pill(label: str, colour: str, title: str = "") -> str:
    hint = f' title="{esc(title)}"' if title else ""
    return (f'<p style="margin:8px 0 2px 0; font-size:12px;"{hint}>'
            f'<span style="color:{colour};">{label}</span></p>')


def worked_by_cursiv(inner: str) -> bool:
    """A Sources line for an answer no AI model wrote."""
    return inner.startswith(("Sources:", "Source:")) and bool(_NO_MODEL.search(inner)) and "Wording by the AI model" not in inner


def _what(inner: str) -> str:
    """'Sources: Cursiv calculation (units; no AI model)' -> 'Cursiv calculation · units'."""
    body = inner.split(":", 1)[1].strip()
    body = re.sub(r"\s*\((?:([^;()]*);\s*)?no AI model\)\s*$", lambda m: f" · {m.group(1)}" if m.group(1) else "", body)
    return body.replace("Cursiv calculation", "Worked out by Cursiv").strip(" ·")


def badge(inner: str) -> str:
    """One of Cursiv's status lines (the text inside *[…]*), as a quiet line."""
    if inner.startswith("Answered by "):
        engine = inner[len("Answered by "):]
        local = engine.startswith(("Ollama", "Local coding models", "Cursiv local"))
        if local:
            label = "Local · " + esc(engine.split("·", 1)[-1].strip())
            return _pill(f'<span style="color:{theme.GREEN};">●</span>&nbsp; {label}', theme.FAINT,
                         "Answered by the AI model on this computer")
        return _pill(f'<span style="color:{theme.AMBER};">●</span>&nbsp; Online · {esc(engine)}', theme.FAINT,
                     "Answered by an online AI service you added")
    if inner.startswith("Cursiv's check:"):
        return (f'<p style="margin:8px 0 0 0; font-size:13px; color:{theme.AMBER};">'
                f'⚠&nbsp; {esc(inner)}</p>')
    if worked_by_cursiv(inner):
        return _pill(f'<span style="color:{theme.GREEN};">✓</span>&nbsp; {esc(_what(inner))}'
                     f'<span style="color:{theme.FAINT};"> · no AI model</span>', theme.MUTED,
                     "Cursiv's own code produced this answer")
    if inner.startswith("From Cursiv's offline reference"):
        urgent = "[medical/" in inner or "[survival/" in inner
        style = (f"font-size:13px; color:{theme.TEXT};" if urgent else f"font-size:12px; color:{theme.MUTED};")
        return (f'<table width="100%" cellpadding="10" cellspacing="0" style="margin:2px 0 10px 0;'
                f' background-color:{theme.SURFACE2}; border:1px solid {theme.BORDER};"><tr><td>'
                f'<span style="{style}">{esc(inner)}</span></td></tr></table>')
    if inner.startswith(("Sources:", "Source:")):
        return _pill(esc(inner.split(":", 1)[0]) + " ·" + esc(inner.split(":", 1)[1]), theme.FAINT)
    return f'<p style="margin:4px 0; font-size:12px; color:{theme.MUTED};">{esc(inner)}</p>'


# ── Receipts and notices (command results shown as cards, not log lines) ─────

def _card(title: str, body_lines: list[str], tone: str, *, extra: str = "") -> str:
    rows = "".join(f'<br><span style="color:{theme.MUTED}; font-size:12px;">{esc(ln)}</span>'
                   for ln in body_lines if ln.strip())
    return (f'<table width="100%" cellpadding="12" cellspacing="0" style="margin:4px 0 8px 0;'
            f' background-color:{theme.SURFACE2}; border-left:3px solid {tone};"><tr><td>'
            f'<span style="color:{theme.TEXT}; font-weight:600;">{title}</span>{rows}{extra}</td></tr></table>')


_RECEIPTS = (
    # (pattern on the first line, title, tone name)
    (re.compile(r"^Logged\."), "✓  Saved to your field notebook", "GREEN"),
    (re.compile(r"^Field Notebook: all \d+ entries are intact"), "✓  Field notebook checked", "GREEN"),
    (re.compile(r"^Saved to memory:"), "✓  Saved to memory", "GREEN"),
    (re.compile(r"^Forgotten:"), "✓  Removed from memory", "GREEN"),
    (re.compile(r"^Saved and verified: "), "✓  File saved", "GREEN"),
    (re.compile(r"^Saved as note "), "✓  Saved as a note", "GREEN"),
    (re.compile(r"^Offline mode ON"), "Offline mode is on", "GREEN"),
    (re.compile(r"^Offline mode OFF"), "Offline mode is off", "AMBER"),
    (re.compile(r"^Cursiv does not delete files"), "Nothing was deleted", "AMBER"),
    (re.compile(r"^(?:Family letters|The council) .*was removed|^.* were removed from Cursiv"), "Removed from Cursiv", "FAINT"),
)


def receipt_kind(text: str) -> tuple[str, str] | None:
    """(title, tone name) when a command result reads better as a card."""
    first = (text or "").strip().split("\n", 1)[0]
    for pattern, title, tone in _RECEIPTS:
        if pattern.search(first):
            return title, tone
    return None


def receipt(text: str, *, first_offline: bool = False) -> str | None:
    kind = receipt_kind(text)
    if kind is None:
        return None
    title, tone = kind
    lines = [ln.strip() for ln in text.strip().split("\n")]
    # "Logged. Sample X. Record … · fingerprint … · read-back matched · chain intact." -> readable parts
    if lines and lines[0].startswith("Logged."):
        parts = [p.strip().rstrip(".") for chunk in lines[0][len("Logged."):].split("·")
                 for p in re.split(r"(?<=\.)\s+", chunk)]
        lines = [p for p in parts if p] + lines[1:]
    elif title.startswith("Offline mode is on"):
        lines = ["Cursiv won't connect to anything outside this computer: no cloud AI, web search, "
                 "update checks or downloads. Your local model, notebook, memory and documents still work.",
                 "It stays on after a restart. Type offline off to undo."]
    extra = ""
    if first_offline:
        extra = (f'<br><br><span style="color:{theme.GREEN}; font-size:13px;">First time offline. '
                 f'This is what Cursiv was built for: everything you do now stays on this computer.</span>')
    return _card(esc(title), lines, getattr(theme, tone), extra=extra)


# ── A new chat ───────────────────────────────────────────────────────────────

STARTERS = (
    ("Field notes", "Log an observation with a measurement",
     "log site: North transect; water temp 12.4 C; pH 7.2; note: first visit"),
    ("Calculations", "Worked out in code, with a receipt",
     "How long to fill 20 L at 2 L/min?"),
    ("Your documents", "Import a protocol, then ask about it",
     "How do I add a document and ask about it?"),
    ("Offline", "Keep everything on this computer",
     "offline on"),
)


def starters(prompt_href) -> str:
    """Four starter cards in two columns. prompt_href(text) -> a cursiv://prompt link."""
    cells = []
    for title, line, text in STARTERS:
        cells.append(
            f'<td width="50%" style="background-color:{theme.SURFACE}; border:1px solid {theme.BORDER}; padding:12px;">'
            f'<a href="{prompt_href(text)}" style="text-decoration:none;">'
            f'<span style="color:{theme.ACCENT}; font-weight:600;">{esc(title)}</span><br>'
            f'<span style="color:{theme.MUTED}; font-size:12px;">{esc(line)}</span><br>'
            f'<span style="color:{theme.TEXT}; font-size:12px;">{esc(text)}</span></a></td>')
    rows = "".join(f"<tr>{cells[i]}{cells[i + 1]}</tr>" for i in range(0, len(cells), 2))
    return f'<table width="100%" cellspacing="8" cellpadding="0" style="margin:4px 0 12px 0;">{rows}</table>'


TOUR = (
    ("Save an observation", "log site: Example; water temp 12.4 C; note: try the notebook"),
    ("Let code do the maths", "Convert 12.4 C to F"),
    ("See what Cursiv knows about you", "self stores"),
    ("Work with no internet", "offline on"),
)


def tour(prompt_href) -> str:
    """Shown once, after the first answer from a model: four things to try next."""
    links = "".join(f'<br><a href="{prompt_href(text)}" style="color:{theme.ACCENT}; text-decoration:none;">'
                    f'→&nbsp; {esc(label)}</a><span style="color:{theme.FAINT}; font-size:12px;">'
                    f'&nbsp; {esc(text)}</span>' for label, text in TOUR)
    return _card("Your first answer from the AI on this computer. A few things to try next:",
                 [], theme.ACCENT, extra=links)


# ── Problems, in plain words ─────────────────────────────────────────────────

_SETUP = ("cursiv://setup", "Open Setup")
_REPORT = ("cursiv://report", "Send a problem report")
_PROBLEMS = (
    (re.compile(r"(?i)connection refused|failed to establish a new connection|localhost:11434|ollama.*(?:not running|unreachable)"),
     "The local AI engine isn't running.",
     "Setup can start it. If Cursiv just opened, wait a moment and try again.", _SETUP),
    (re.compile(r"(?i)model .*not found|pull model|no such model"),
     "The AI model isn't installed on this computer.",
     "Setup downloads a model sized for this computer.", _SETUP),
    (re.compile(r"(?i)timed? ?out"),
     "The AI took too long to answer.",
     "Try again, or ask a shorter question. A large model on a small computer can be slow.", None),
    (re.compile(r"(?i)\b(?:401|403|invalid api key|unauthori[sz]ed|incorrect api key)\b"),
     "The online AI service didn't accept the key.",
     "Check the key in Settings → AI keys, or type offline on to use the local model.", None),
    (re.compile(r"(?i)\b429\b|rate.?limit|quota"),
     "The online AI service is busy or over its limit.",
     "Wait a minute and try again; the local model still works.", None),
    (re.compile(r"(?i)locked; unlock at startup|incorrect encryption passphrase"),
     "Your saved conversations and memories are locked.",
     "Close Cursiv and open it again, then enter your encryption passphrase.", None),
)


def problem(message: str) -> str:
    """An error card: what happened in plain words, what to do next, and the detail."""
    for pattern, what, nxt, action in _PROBLEMS:
        if pattern.search(message or ""):
            break
    else:
        what, nxt, action = "Something went wrong with that answer.", "Try again. If it keeps happening:", _REPORT
    link = (f'<br><a href="{action[0]}" style="color:{theme.ACCENT};">{action[1]}</a>' if action else "")
    detail = (f'<br><span style="color:{theme.FAINT}; font-size:11px;">Detail: {esc((message or "")[:300])}</span>'
              if message else "")
    return _card(esc(what), [nxt], theme.RED, extra=link + detail)


# ── One-time moments (the first offline, the tour) ───────────────────────────

def moments_file():
    from cursiv_engine.core import paths
    return paths.APP_DATA / "ui_moments.json"


def seen_once(flag: str) -> bool:
    """True if this one-time moment already happened; marks it as happened now."""
    import json
    path = moments_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if data.get(flag):
            return True
        data[flag] = True
        from cursiv_engine.core import atomic
        atomic.write_text(path, json.dumps(data))
    except Exception:
        return True                     # can't remember it: never show it again and again
    return False


# ── A conversational action waiting for a yes (U99, core/intent.py) ───────────

def intent_card(proposal, key: str) -> str:
    """Save / Edit / Cancel for something Cursiv worked out from plain words. Nothing has
    run yet; Save runs the exact command shown, through Cursiv's own code."""
    link = lambda what, label, colour: (f'<a href="cursiv://intent/{what}/{key}" '
                                        f'style="color:{colour}; text-decoration:none; font-weight:600;">{label}</a>')
    command = (f'<br><span style="color:{theme.FAINT}; font-size:11px;">Runs: {esc(proposal.command)}</span>')
    if proposal.ok:
        actions = (f'<br><br>{link("save", "Save" if proposal.action.name.startswith(("notebook", "memory.save", "file.c")) else "Yes", theme.ACCENT)}'
                   f'&nbsp;&nbsp;&nbsp;{link("edit", "Edit", theme.MUTED)}&nbsp;&nbsp;&nbsp;{link("cancel", "Cancel", theme.MUTED)}')
        return _card(esc(proposal.action.title), proposal.card_lines(), theme.ACCENT, extra=command + actions)
    why = "; ".join(dict.fromkeys(proposal.problems))
    wanted = proposal.action.title.rstrip("?")
    wanted = wanted[0].lower() + wanted[1:]
    return _card("Nothing was saved", [f"It looked like: {wanted}. But {why}.",
                                       "Edit it and send it yourself if it's right."],
                 theme.AMBER, extra=command + f'<br><br>{link("edit", "Edit", theme.ACCENT)}')


# ── Suggested memories (U100, memory/suggestions.py) ──────────────────────────

def suggestion_card(rows: list[dict]) -> str:
    """Guesses Cursiv made about the person, offered for a yes; nothing is saved yet."""
    items = "".join(
        f'<br><span style="color:{theme.TEXT};">{esc(r["text"])}</span>&nbsp;&nbsp;'
        f'<a href="cursiv://suggest/save/{r["id"]}" style="color:{theme.ACCENT}; text-decoration:none; '
        f'font-weight:600;">Save</a>&nbsp;&nbsp;'
        f'<a href="cursiv://suggest/no/{r["id"]}" style="color:{theme.MUTED}; text-decoration:none;">No</a>'
        for r in rows[:3])
    return _card("Remember this?", ["Cursiv guessed this from what you said. Nothing is saved unless you say so."],
                 theme.ACCENT, extra=items)

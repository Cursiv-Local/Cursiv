"""
"What did I ask you three messages ago?" answered from the conversation itself (U100 audit).

In the U99 test run the model answered from SESSION MEMORY -- exchanges from another
conversation earlier that day, written as "You: …" -- and invented a checklist request.
These questions have exact answers in the stored turns, so Cursiv reads them itself: it
counts only the person's own messages, says how it counted, and says plainly when the
conversation doesn't go back that far. No model is involved.
"""
from __future__ import annotations

import re

_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "a couple of": 2, "a few": 3}
_N_AGO = re.compile(r"(?i)^\s*what (?:did|was it) i (?:ask|say|tell you|write|type)(?: you)?\s+"
                    r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:messages?|questions?|turns?)\s+ago\b")
_EDGE = re.compile(r"(?i)^\s*what (?:was|is) (?:my )?(first|last|previous) (?:message|question)\b|"
                   r"^\s*what did i (?:first|just) (ask|say)\b")


def _mine(history: list[dict]) -> list[str]:
    return [m["content"].strip() for m in history or []
            if m.get("role") == "user" and isinstance(m.get("content"), str) and m["content"].strip()]


def _quote(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return f"“{text[:400]}{'…' if len(text) > 400 else ''}”"


def answer(question: str, history: list[dict]) -> str | None:
    q = (question or "").strip()
    mine = _mine(history)
    m = _N_AGO.match(q)
    if m:
        raw = m.group(1).lower()
        n = int(raw) if raw.isdigit() else _WORDS[raw]
        if n < 1:
            return None
        lead = (f"Counting only your messages, {n} before this one")
        if n > len(mine):
            return (f"{lead}: this conversation doesn't go back that far. It has {len(mine)} earlier "
                    f"message{'s' if len(mine) != 1 else ''} from you, so I can't say what that one was.\n\n"
                    "*[Sources: this conversation's stored messages (no AI model)]*")
        return (f"{lead}, you wrote: {_quote(mine[-n])}\n\n"
                "*[Sources: this conversation's stored messages (no AI model)]*")
    original = bool(re.fullmatch(r'(?i)(?:what was my original concern|what (?:did i|was i) '
                                r'(?:originally|initially) (?:ask|say|asking about)|'
                                r'what did i (?:start|begin) (?:by asking|with))[?.!]*', q))
    m = _EDGE.match(q)
    if m or original:
        which = 'first' if original else (m.group(1) or m.group(2) or "").lower()
        if not mine:
            return ("No earlier user messages are available in this conversation context. I cannot establish what you said first.\n\n"
                    "*[Sources: this conversation's stored messages (no AI model)]*")
        text, label = (mine[0], "From the conversation context currently available, your earliest message") if which == "first" else \
            (mine[-1], "Your message before this one")
        return f"{label}: {_quote(text)}\n\n*[Sources: this conversation's stored messages (no AI model)]*"
    return None

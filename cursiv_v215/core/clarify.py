"""
A short message that points at something never named ("Is it safe?", "How long
should I cook it?", "Which one is better?") with nothing earlier in the
conversation to say what. A 4B model answered "Yes, it's safe" (benchmark
amb-002). Cursiv tells the model to ask one short question instead of guessing.
"""
from __future__ import annotations

import re

_POINTER = re.compile(r"(?i)\b(it|this|that|these|those|they|them|one|ones)\b")
# "it" that doesn't point at anything.
_IDIOM = re.compile(r"(?i)\b(what time is it|what day is it|is it (raining|snowing|cold|hot|warm|late|early|night|morning)|"
                    r"how is it going|how's it going|it depends|that's it|is that all|this (morning|evening|week|year|time)|"
                    r"that's (all|fine|ok|okay|great))\b")
_STOP = frozenset(
    "a an the is are was were be been am do does did can could should would will shall may might must i me my we us "
    "our you your he she his her its how what which who when where why whether or and to of in on for with at by from "
    "if so then than just really very much many long far better best good bad okay ok now still yet ever "
    "get got make made go going please tell know think say".split()
)


def needs_clarifying(question: str, history: list[dict] | None) -> str:
    """The word that has nothing to refer to, or ""."""
    if any(h.get("role") == "user" and str(h.get("content", "")).strip() for h in (history or [])):
        return ""
    q = (question or "").strip()
    words = re.findall(r"[a-z']+", q.lower())
    if not words or len(words) > 10 or _IDIOM.search(q):
        return ""
    m = _POINTER.search(q)
    if not m:
        return ""
    content = [w for w in words if w not in _STOP and not _POINTER.fullmatch(w)]
    return m.group(1).lower() if len(content) <= 1 else ""


def question(word: str) -> str:
    """Cursiv's own reply: ask what the word refers to."""
    return (f'What does "{word}" refer to? Tell me a little more (what it is, and what you want to know about it) '
            "and I'll give you a useful answer.")


def prompt_note(word: str) -> str:
    return (f"## Nothing says what \"{word}\" is\nThe message says \"{word}\", but nothing in it or earlier in the "
            "conversation says what that refers to. Ask one short question about what they mean. Don't guess and "
            "don't answer for a guessed thing.")

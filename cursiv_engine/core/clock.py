"""
Today's date and the time, from this computer's clock -- never from the AI model.

A local model has no idea what day it is; it only sees a timestamp buried in the
status block and often ignores it. Plain questions about *now* ("what day is it?",
"what's today's date?", "what time is it?") are answered here. Questions that need
something else -- another place's time ("what time is it in Tokyo?") or date maths
("what day is 25 December?", handled by core/datecalc.py) -- are left alone.
"""
from __future__ import annotations

import re
import time
from datetime import datetime

SOURCE = "\n\n*[Sources: this computer's clock (no AI model)]*"

_NOW = r"(?:\s+(?:is it|it is))?(?:\s+(?:today|now|right now|currently))?"
_QUESTION = re.compile(
    r"(?i)^\s*(?:hey\s+cursiv[,.]?\s+|cursiv[,.]?\s+)?(?:so\s+|ok(?:ay)?[,.]?\s+)?(?:please\s+)?(?:"
    r"(?:what|which)(?:'s| is)?\s+(?:the\s+)?(?:day(?:\s+of\s+the\s+week)?|date|today'?s\s+date|day\s+and\s+date|"
    r"date\s+and\s+time|time|year|month)" + _NOW +
    r"|what(?:'s| is)\s+today" +
    r"|(?:do you know|can you tell me|tell me)\s+(?:what\s+)?(?:the\s+)?(?:day|date|time|today'?s\s+date)"
    r"(?:\s+it\s+is)?" + _NOW +
    r"|is\s+it\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+today)?" +
    r"|today'?s\s+date" +
    r")\s*[?.!]*\s*$")


def now() -> datetime:
    return datetime.now()


def zone() -> str:
    try:
        return time.strftime("%Z") or "local time"
    except Exception:
        return "local time"


def _day(d: datetime) -> str:
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B')} {d.year}"


def _time(d: datetime) -> str:
    return d.strftime("%I:%M %p").lstrip("0")


def today_line() -> str:
    """For the system prompt, so date-relative answers use the real date."""
    d = now()
    return f"Today is {_day(d)}; the time is {_time(d)} ({zone()}), from this computer's clock."


def answer(question: str) -> str | None:
    q = (question or "").strip()
    if len(q.split()) > 14 or not _QUESTION.match(q):
        return None
    d, low = now(), q.lower()
    weekday = re.search(r"is\s+it\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", low)
    if weekday:
        asked = weekday.group(1).title()
        yes = d.strftime("%A") == asked
        body = (f"{'Yes' if yes else 'No'}: today is {_day(d)}.")
    elif re.search(r"\btime\b", low) and not re.search(r"\b(?:date|day)\b", low):
        body = f"It's {_time(d)} ({zone()}) on {_day(d)}."
    elif re.search(r"\byear\b", low):
        body = f"It's {d.year} (today is {_day(d)})."
    elif re.search(r"\bmonth\b", low):
        body = f"It's {d.strftime('%B')} {d.year} (today is {_day(d)})."
    else:
        body = f"Today is {_day(d)}. It's {_time(d)} ({zone()})."
    return body + " This comes from this computer's clock, so it is only as right as that clock." + SOURCE

"""
Dates, weekdays, evenly spaced points and two proportions, worked out in code (fieldcalc.work_out
calls these). From recorded benchmark failures: "10 days from Wednesday is Friday" (rea-008; it's
Saturday), and "site A has better survival" from 3 of 4 frogs against 60 of 100 (rea-016).

Only unambiguous shapes: "12/10/2026" could be December or October, so slashed dates are refused
with that reason instead of guessed.
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"], 1)}
_MON = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|" \
       r"jun|jul|aug|sep|sept|oct|nov|dec)\.?"
_DATE = re.compile(r"(?i)\b(\d{4})-(\d{1,2})-(\d{1,2})\b|\b(\d{1,2})(?:st|nd|rd|th)?\s+" + _MON + r",?\s+(\d{4})\b|\b"
                   + _MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_SLASHED = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
_N = r"(\d+)"


class Result:
    """answer: words the reply must contain instead of a number ("Saturday"); facts: for contradiction checks."""
    def __init__(self, statement: str, value: float, tol: float = 0.0, answer: str = "", facts: dict | None = None):
        self.statement, self.value, self.tol, self.lead, self.tool = statement, value, tol, "", ""
        self.answer, self.facts = answer, facts or {}


def _month(name: str) -> int:
    n = name.lower().rstrip(".")
    for full, i in _MONTHS.items():
        if full.startswith(n[:3]):
            return i
    raise ValueError(name)


def _dates(text: str) -> list[date]:
    out = []
    for m in _DATE.finditer(text):
        if m.group(1):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        elif m.group(4):
            y, mo, d = int(m.group(6)), _month(m.group(5)), int(m.group(4))
        else:
            y, mo, d = int(m.group(9)), _month(m.group(7)), int(m.group(8))
        out.append(date(y, mo, d))                     # ValueError for 29 February 2023, 31 April ...
    return out


def _show(d: date) -> str:
    return f"{_DAYS[d.weekday()]} {d.day} {d.strftime('%B')} {d.year}"


_SHIFT = re.compile(r"(?i)\b(?:today|it) is (?:a )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
                    r".*?\b" + _N + r"\s+(days?|weeks?)\s+(from now|later|after|ago|before|earlier)")
_SHIFT2 = re.compile(r"(?i)\b" + _N + r"\s+(days?|weeks?)\s+(after|before|from)\s+(?:a |next |last )?"
                     r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b")


def weekday(question: str) -> Result | None:
    q = question or ""
    m = _SHIFT.search(q)
    if m:
        day, n, unit, way = m.group(1), int(m.group(2)), m.group(3), m.group(4).lower()
    else:
        m = _SHIFT2.search(q)
        if not m:
            return None
        n, unit, way, day = int(m.group(1)), m.group(2), m.group(3).lower(), m.group(4)
    days = n * (7 if unit.lower().startswith("week") else 1)
    back = way in ("ago", "before", "earlier")
    start = _DAYS.index(day.capitalize())
    end = _DAYS[(start + (-days if back else days)) % 7]
    return Result(f"{days} day{'s' if days != 1 else ''} {'before' if back else 'after'} a {day.capitalize()} is a "
                  f"{end} ({days} = {days // 7} week{'s' if days // 7 != 1 else ''} and {days % 7} day"
                  f"{'s' if days % 7 != 1 else ''}).", 0.0, answer=end)    # benchmark rea-008, U75: checked by name


_BETWEEN = re.compile(r"(?i)\bhow many (?:days|weeks)\b.*?\b(?:between|from|since|until|till|to)\b")
_OFFSET = re.compile(r"(?i)\b" + _N + r"\s+(days?|weeks?)\s+(after|before|from|since|past)\b")
_WHICH_DAY = re.compile(r"(?i)\bwhat day (?:of the week )?(?:is|was|will|does|did)\b|\bwhich day of the week\b")


def dates(question: str) -> Result | None:
    q = question or ""
    if _SLASHED.search(q) and re.search(r"(?i)\b(day|date|days|weeks?)\b", q):
        return Result("Cursiv didn't calculate this: a date like " + _SLASHED.search(q).group(0) + " can be read "
                      "day-first or month-first; write it as 14 October 2026 or 2026-10-14.", float("nan"))
    try:
        ds = _dates(q)
    except ValueError:
        return Result("Cursiv didn't calculate this: one of the dates doesn't exist (check the day and month).",
                      float("nan"))
    if not ds:
        return None
    if len(ds) == 2 and _BETWEEN.search(q):
        a, b = ds
        n = (b - a).days
        return Result(f"From {_show(a)} to {_show(b)} is {abs(n)} day{'s' if abs(n) != 1 else ''}"
                      f" ({abs(n) // 7} weeks and {abs(n) % 7} day{'s' if abs(n) % 7 != 1 else ''}), "
                      "not counting the first day.", float(abs(n)))
    m = _OFFSET.search(q)
    if len(ds) == 1 and m:
        n = int(m.group(1)) * (7 if m.group(2).lower().startswith("week") else 1)
        sign = -1 if m.group(3).lower() == "before" else 1
        end = ds[0] + timedelta(days=sign * n)
        return Result(f"{n} days {'before' if sign < 0 else 'after'} {_show(ds[0])} is {_show(end)}.",
                      float(end.day))
    if len(ds) == 1 and _WHICH_DAY.search(q):
        return Result(f"{ds[0].day} {ds[0].strftime('%B')} {ds[0].year} is a {_DAYS[ds[0].weekday()]}.",
                      0.0, answer=_DAYS[ds[0].weekday()])
    return None


# ── points along a line: "a quadrat every 12.5 m along a 250 m transect, including one at each end" ──
_SPACING = re.compile(r"(?i)\bevery\s+(\d+(?:\.\d+)?)\s*(m|meters?|metres?|km|ft|feet|yards?|cm)\b.*?\b(?:along|"
                      r"over|across|on)\s+(?:a|the)?\s*(\d+(?:\.\d+)?)\s*(m|meters?|metres?|km|ft|feet|yards?|cm)\b")
_BOTH = re.compile(r"(?i)\b(including|incl\.?|with) (?:one |a \w+ )?(?:at )?(?:each|both) ends?\b|\bboth ends\b")
_NONE = re.compile(r"(?i)\b(?:not|excluding|no \w+ at|without) (?:at )?(?:the )?(?:either |both |each )?ends?\b")
_ONE = re.compile(r"(?i)\b(?:at|from) the start\b|\bone end\b")


def spacing(question: str) -> Result | None:
    q = question or ""
    m = _SPACING.search(q)
    if not m or not re.search(r"(?i)\bhow many\b", q):
        return None
    if m.group(2)[:1].lower() != m.group(4)[:1].lower() or m.group(2).lower().startswith("k") != \
            m.group(4).lower().startswith("k"):
        return None                                   # different units: not guessing the conversion
    step, length = float(m.group(1)), float(m.group(3))
    if step <= 0:
        return None
    gaps = length / step
    if abs(gaps - round(gaps)) > 1e-9:
        return Result(f"Cursiv didn't calculate this: {m.group(3)} isn't a whole number of {m.group(1)} "
                      f"{m.group(2)} steps ({gaps:.2f}), so the last gap would be shorter.", float("nan"))
    gaps = int(round(gaps))
    if _NONE.search(q):
        n, how = gaps - 1, "not at either end"
    elif _BOTH.search(q):
        n, how = gaps + 1, "including both ends"
    elif _ONE.search(q):
        n, how = gaps, "at the start but not the end"
    else:
        return Result(f"{m.group(3)} ÷ {m.group(1)} = {gaps} gaps. With a point at both ends that's {gaps + 1}; at "
                      f"one end only, {gaps}; at neither end, {gaps - 1}. The question doesn't say which.",
                      float("nan"))
    return Result(f"{m.group(3)} ÷ {m.group(1)} = {gaps} gaps between points, so {how}: {n} points.", float(n))


# ── two proportions: "3 of 4 frogs survived at site A, 60 of 100 at site B" ─────
_OF = re.compile(r"(?i)\b(\d+)\s+(?:of|out of)\s+(\d+)\b")


def _wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson score interval (good for small samples, unlike p ± 1.96·SE)."""
    z = 1.959964
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def proportions(question: str) -> Result | None:
    q = question or ""
    found = [(int(a), int(b)) for a, b in _OF.findall(q)]
    if len(found) != 2 or not re.search(r"(?i)\b(better|worse|higher|lower|more|less|differ\w*|compare|significant)\b", q):
        return None
    if any(n == 0 or k > n for k, n in found):
        return Result("Cursiv didn't calculate this: a count is larger than its total, or a total is 0.", float("nan"))
    (k1, n1), (k2, n2) = found
    lo1, hi1 = _wilson(k1, n1)
    lo2, hi2 = _wilson(k2, n2)
    overlap = lo1 <= hi2 and lo2 <= hi1
    pct = lambda x: f"{100 * x:.0f}%"
    verdict = ("The ranges overlap, so these counts can't show that one is really higher: the smaller sample is "
               "too small to tell." if overlap else
               "The ranges don't overlap, so the difference is unlikely to be chance alone.")
    small = " A sample of fewer than 10 is very weak evidence on its own." if min(n1, n2) < 10 else ""
    return Result(f"{k1} of {n1} = {pct(k1 / n1)} (95% range {pct(lo1)} to {pct(hi1)}); {k2} of {n2} = "
                  f"{pct(k2 / n2)} (95% range {pct(lo2)} to {pct(hi2)}), Wilson intervals. {verdict}{small}",
                  float(round(100 * k1 / n1)), 0.5, facts={"overlap": overlap})

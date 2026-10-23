"""
Flexible date of birth matching.

Accepts dates in virtually any format a person might type naturally and
normalizes them to YYYY-MM-DD for hash comparison.

If you are reading this and wondering what it's for: the birth date
is the key. Nothing more. Nothing less.
"""
from __future__ import annotations

import re

_MONTHS: dict[str, int] = {
    "january": 1,  "jan": 1,
    "february": 2, "feb": 2,
    "march": 3,    "mar": 3,
    "april": 4,    "apr": 4,
    "may": 5,
    "june": 6,     "jun": 6,
    "july": 7,     "jul": 7,
    "august": 8,   "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10,  "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def _extract_parts(text: str) -> tuple[int | None, int | None, int | None]:
    """Extract (month, day, year) from a freeform date string."""
    text = text.lower().strip()
    month = day = year = None

    for name, num in sorted(_MONTHS.items(), key=lambda x: -len(x[0])):
        if name in text:
            month = num
            text  = text.replace(name, " ")
            break

    nums = re.findall(r"\d+", text)

    four = [n for n in nums if len(n) == 4]
    if four:
        year = int(four[0])
        nums = [n for n in nums if n != four[0]]
    else:
        for n in nums:
            if len(n) == 2:
                v = int(n)
                if 15 <= v <= 99:
                    year = 1900 + v
                    nums = [x for x in nums if x != n]
                    break
                elif v <= 14:
                    year = 2000 + v
                    nums = [x for x in nums if x != n]
                    break

    remaining = [int(n) for n in nums if n.isdigit() and 1 <= int(n) <= 31]

    if month is None and remaining:
        candidates = [x for x in remaining if x <= 12]
        if candidates:
            month = candidates[0]
            remaining = [x for x in remaining if x != candidates[0] or remaining.count(x) > 1]
            if candidates[0] in remaining:
                remaining.remove(candidates[0])

    if remaining and day is None:
        day = remaining[0]

    return month, day, year


def normalize_dob(text: str) -> str | None:
    """
    Normalize any freeform date string to 'YYYY-MM-DD'.
    Returns None if a complete date (year + month + day) cannot be parsed.
    """
    month, day, year = _extract_parts(text)
    if month and day and year:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def matches_dob(user_input: str, stored_month: int, stored_day: int, stored_year: int) -> bool:
    """
    Returns True if user_input reasonably represents the stored date.
    Requires at minimum year OR (month + day) to match.
    """
    m, d, y = _extract_parts(user_input)

    if m is None and d is None and y is None:
        return False

    if y is not None and m is None and d is None:
        return y == stored_year

    if m is not None and d is not None:
        if y is not None:
            return m == stored_month and d == stored_day and y == stored_year
        return m == stored_month and d == stored_day

    if m is not None and y is not None:
        return m == stored_month and y == stored_year

    if y is not None:
        return y == stored_year

    return False

"""Pure model-review eligibility, independent of parsing, widgets and providers."""
from __future__ import annotations

import re

_REVIEW = re.compile(
    r"(?i)\b(is this correct|is that (?:right|correct)|is it correct|"
    r"check this|review this|did i get this right|double[- ]check|verify this|fact[- ]check)\b"
)

_RISK = re.compile(
    r"(?i)\b(?:safe|safety|dos(?:e|age)|bleach|poison|overdose|medication|"
    r"voltage|current draw|contraindication|contradict\w*|conflicting|statistical significance)\b|"
    r"\b(?:I|we)\s+(?:checked|verified|tested|ran|executed|saved|created|searched)\b")

_QUANTITY = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|liters?|litres?|drops?|gallons?|"
    r"volts?|amps?|watts?|degrees?|celsius|fahrenheit|retries|retry|seconds?|"
    r"minutes?|hours?|meters?|metres?|miles?|feet|percent)\b|\d\s*%|"
    r"\d\s*(?:[+*/=×÷]|\bplus\b|\bminus\b|\btimes\b)\s*\d|\d\s+-\s+\d")

_CRISIS = re.compile(
    r"(?i)\b(kill myself|suicid\w*|self[- ]harm|want to die|end my life|"
    r"don'?t want to (?:live|be alive))\b"
)

def should_verify(user_text: str, draft: str, *, memory_update: bool = False,
                  previous_failed: bool = False) -> bool:
    """Stronger check only. Casual chat returns False and makes no model call."""
    if _CRISIS.search(user_text or ""):
        return False
    body = (draft or "").strip()
    if not body:
        return False
    head = body.lstrip()
    if head.startswith("[") and "error" in head[:120].lower():
        return False
    if _REVIEW.search(user_text or ""):
        return True
    # Years, list numbering, identifiers, generic advice and a previous failure
    # do not turn an ordinary conversation into another model round-trip.
    prose = re.sub(r'(?m)^\s*\d+[.)]\s+', '', body)
    return bool(_RISK.search(user_text or '') or _RISK.search(prose) or
                _QUANTITY.search(user_text or '') or _QUANTITY.search(prose))

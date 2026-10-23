"""Bounded volume/flow/duration arithmetic with explicit units and full matches."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import re

_N = r'(-?\d+(?:\.\d+)?)'
_V = r'(liters?|litres?|ml|milliliters?|millilitres?|l|cubic met(?:er|re)s?|m³|m3)'
_T = r'(minutes?|mins?|min|hours?|hrs?|seconds?|secs?|s)'
_RATE = _N + r'\s*' + _V + r'\s*(?:/|per\s+)' + _T
_VOLUME = _N + r'\s*' + _V
_TIME = _N + r'\s*' + _T
_PATTERNS = (
    ('flow_conversion', r'how many liters per minute is (?:a )?flow of\s+' + _RATE),
    ('flow_duration', r'if I have\s+' + _VOLUME + r'\s+and use\s+' + _RATE +
     r',?\s+how long until empty'),
    ('flow_duration', r'(?:how long(?: will it take)?(?: to fill)?|calculate (?:the )?duration(?: to fill)?)\s+'
     + _VOLUME + r'\s+at\s+' + _RATE),
    ('flow_rate', r'(?:what is (?:the )?(?:flow )?rate(?: for)?|calculate (?:the )?(?:flow )?rate(?: for)?)'
     r'\s+(?:if\s+)?' + _VOLUME + r'\s+(?:in|over)\s+' + _TIME),
    ('flow_volume', r'(?:how much (?:water|volume)|what (?:volume|is (?:the )?volume)|calculate (?:the )?volume)'
     r'\s+(?:at\s+)?' + _RATE + r'\s+(?:for|over)\s+' + _TIME),
)


@dataclass
class Result:
    statement: str
    value: float | None
    tol: float = 0.000001
    tool: str = ''
    inputs: dict = field(default_factory=dict)
    facts: dict = field(default_factory=dict)


def _volume(n, unit):
    unit = unit.lower()
    return float(n) * (1000 if unit.startswith(('cubic', 'm3', 'm³')) else
                       .001 if unit.startswith(('ml', 'milli')) else 1)


def _minutes(n, unit):
    return float(n) * (60 if unit.lower().startswith(('h',)) else 1 / 60 if unit.lower().startswith('s') else 1)


def is_request(question: str) -> bool:
    """Recognize this narrow domain even when required operands are missing."""
    return bool(re.match(r'(?i)^(?:how long|how much (?:water|volume)|what (?:volume|is (?:the )?(?:flow )?rate)|'
                         r'calculate (?:the )?(?:flow |volume|duration|rate))\b', question.strip()) and
                re.search(r'(?i)\b(?:fill|flow)\b|(?:/|per\s+)(?:minute|hour|second|min|hr|sec)\b', question))


def work_out(question: str) -> Result | None:
    q = question.strip().rstrip('?.!')
    for tool, pattern in _PATTERNS:
        m = re.fullmatch(pattern, q, re.I)
        if not m:
            continue
        args = m.groups()
        inputs = dict(request=q)
        numbers = [float(a) for a in args if re.fullmatch(_N, a)]
        if any(not math.isfinite(n) or n <= 0 for n in numbers):
            return Result('Cursiv did not calculate this: volumes, flow rates and time must be positive finite numbers.',
                          None, tool=tool, inputs=inputs, facts={'invalid': 'nonpositive or nonfinite input'})
        if tool == 'flow_conversion':
            value, unit = _volume(args[0], args[1]) / _minutes(1, args[2]), 'L/min'
        elif tool == 'flow_duration':
            volume = _volume(args[0], args[1])
            rate = _volume(args[2], args[3]) / _minutes(1, args[4])
            value, unit = volume / rate, 'minutes'
        elif tool == 'flow_rate':
            value, unit = _volume(args[0], args[1]) / _minutes(args[2], args[3]), 'L/min'
        else:
            rate = _volume(args[0], args[1]) / _minutes(1, args[2])
            value, unit = rate * _minutes(args[3], args[4]), 'L'
        if not math.isfinite(value):
            return Result('Cursiv did not calculate this: the result exceeds the supported numeric range.',
                          None, tool=tool, inputs=inputs, facts={'invalid': 'numeric range'})
        return Result(f'{value:.6g} {unit}. Assumes a constant flow rate with no losses.',
                      value, tool=tool, inputs=inputs)
    return None

"""
Checks on scientific content in a model's draft, done by Cursiv's code (U100 audit).

From the owner's U99 test run:
  * Dissolved oxygen: the model made up "DO_sat = 14.6 - 0.012 T - 0.0002 T^2" and gave 14.3 mg/L
    at 18.6 °C. Air-saturated fresh water at 18.6 °C holds about 9.35 mg/L. Cursiv now has the
    standard equation (below) and notes any saturation figure in a draft that disagrees with it.
  * A "hypothetical" experiment came with a results table written as if it had been run.
    Invented numbers now get a line saying they are illustrations, not measurements.
  * Example coordinates "73.9°F, 73.9°G, 73.9°H" were shown as coordinates. A latitude must end
    in N or S (0-90), a longitude in E or W (0-180); anything else is flagged as not a location.

Each check returns one line for under the answer, or "". None of them rewrites the answer.
"""
from __future__ import annotations

import math
import re

# Benson & Krause (1984), as given in APHA Standard Methods 4500-O and used by USGS: oxygen
# solubility in fresh water in equilibrium with air at 1 atm, mg/L. Valid 0-40 °C.
DO_SOURCE = ("Benson & Krause (1984) equation, as in APHA Standard Methods 4500-O: fresh water, "
             "air-saturated, 1 atm, 0-40 °C")


def do_saturation(temp_c: float) -> float:
    if not 0 <= temp_c <= 40:
        raise ValueError("the oxygen solubility equation is valid from 0 to 40 °C")
    t = temp_c + 273.15
    return math.exp(-139.34411 + 1.575701e5 / t - 6.642308e7 / t ** 2 + 1.243800e10 / t ** 3 - 8.621949e11 / t ** 4)


_DO = re.compile(r"(?i)\b(?:dissolved oxygen|DO_?sat\w*|\bDO\b|oxygen (?:saturation|solubility))")
_SAT_CLAIM = re.compile(
    r"(?i)(?:at|of)\s+(-?\d+(?:\.\d+)?)\s*°?\s*C\b[^.\n]{0,120}?\b(\d{1,2}(?:\.\d+)?)\s*mg\s*/\s*L"
    r"|(\d{1,2}(?:\.\d+)?)\s*mg\s*/\s*L[^.\n]{0,80}?\bat\s+(-?\d+(?:\.\d+)?)\s*°?\s*C\b")
_MADE_UP_FORMULA = re.compile(r"(?i)DO_?sat\w*\s*(?:\([^)]*\))?\s*=\s*[-\d.]")


def do_note(draft: str) -> str:
    """A line when the draft gives a saturation figure the standard equation disagrees with."""
    if not _DO.search(draft or "") or not re.search(r"(?i)saturat|solubil|DO_?sat|maximum", draft or ""):
        return ""
    for m in _SAT_CLAIM.finditer(draft):
        temp, value = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        try:
            expected = do_saturation(float(temp))
        except ValueError:
            continue
        if abs(float(value) - expected) > 0.3:
            return (f"*(Cursiv's check: the draft gives {value} mg/L for oxygen saturation at {temp} °C. The standard "
                    f"equation gives {expected:.2f} mg/L ({DO_SOURCE}). Saturation is the most the water can hold "
                    f"from the air, not what's actually dissolved; only a meter reading tells you that.)*")
    if _MADE_UP_FORMULA.search(draft):
        return (f"*(Cursiv's check: the formula above isn't one Cursiv recognises. For oxygen saturation use the "
                f"{DO_SOURCE}; Cursiv can work it out: ask \"oxygen saturation at 18.6 °C\".)*")
    return ""


def saturation_answer(question: str) -> str | None:
    """'oxygen saturation at 18.6 °C' / 'DO saturation for 18.6C water' -> the number, worked out."""
    q = question or ""
    if not (_DO.search(q) and re.search(r"(?i)saturat|solubil|how much oxygen can", q)):
        return None
    if re.search(r"(?i)\bpercent\b|%", q) and re.search(r"\d\s*mg\s*/\s*L", q, re.I):
        return None          # "7.8 mg/L ... what percent saturation?" is core/fieldsci.py do_percent (U101)
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*°?\s*C\b", q)
    if not m:
        return None
    temp = float(m.group(1))
    try:
        value = do_saturation(temp)
    except ValueError as exc:
        return f"Cursiv didn't calculate this: {exc}.\n\n*[Sources: Cursiv calculation (no AI model)]*"
    return (f"Oxygen saturation in fresh water at {m.group(1)} °C is about {value:.2f} mg/L "
            f"({DO_SOURCE}).\n\nThat's the most the water holds in balance with air; the dissolved oxygen actually "
            "present can be lower (decay, night-time respiration) or higher (photosynthesis), so measure it with a "
            "calibrated meter. Salt water and high altitude hold less.\n\n"
            "*[Sources: Cursiv calculation (oxygen solubility; no AI model)]*")


_HYPOTHETICAL = re.compile(r"(?i)\b(?:hypothetical|invent|imagine|made[- ]up|fictional|simulat\w*|example data|"
                           r"sample data|pretend|mock)\b")


def simulated_note(question: str, draft: str) -> str:
    """Invented numbers in a hypothetical are labelled as invented."""
    if not _HYPOTHETICAL.search(question or ""):
        return ""
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", draft or "")
    table = re.search(r"(?m)^\s*\|.*\d.*\|\s*$", draft or "") or len(numbers) >= 12
    if not table:
        return ""
    return ("*(The numbers above are invented for illustration. No experiment was run and they are not measurements, "
            "so they show what results might look like, not what would happen.)*")


_COORD = re.compile(r"(-?\d{1,3}(?:\.\d+)?)\s*°\s*([A-Za-z])\b\s*,?\s*(-?\d{1,3}(?:\.\d+)?)\s*°\s*([A-Za-z])\b")


def coordinate_note(draft: str) -> str:
    bad = []
    for m in _COORD.finditer(draft or ""):
        lat, lat_h, lon, lon_h = float(m.group(1)), m.group(2).upper(), float(m.group(3)), m.group(4).upper()
        if lat_h in "CF" and lon_h in "CF":
            continue                                       # two temperatures, not a coordinate
        if lat_h not in "NS" or lon_h not in "EW" or abs(lat) > 90 or abs(lon) > 180:
            bad.append(m.group(0).strip())
    if not bad:
        return ""
    shown = "; ".join(dict.fromkeys(bad[:4]))
    return (f"*(Cursiv's check: {shown} isn't a valid location: a latitude ends in N or S (0-90), a longitude in E or W "
            "(0-180). Treat any example coordinates above as placeholders, not real sites.)*")

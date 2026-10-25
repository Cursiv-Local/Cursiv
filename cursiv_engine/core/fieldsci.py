"""
Field-science calculations worked out by code (U101), the ones the local model got wrong.

scripts/fieldcalc_bench.py, before this module (qwen3:4b-instruct): 9 of 14 field calculations right,
and 0 of 5 that need a field formula -- conductivity corrected to 25 °C, a float discharge,
percent oxygen saturation. Each formula here names its source and assumptions in the answer:

  * specific conductance: K25 = K / (1 + 0.0191 (T - 25)), APHA Standard Methods 2510 B (linear
    compensation, natural fresh water; meters with their own compensation may differ)
  * discharge, velocity-area: Q = width x mean depth x mean velocity; a surface float's speed x 0.85
    (USGS float coefficient) because surface water moves faster than the average
  * percent DO saturation: measured / Benson & Krause solubility (core/science_check.py) x 100, fresh
    water at 1 atm
  * molar solutions: grams = molarity x litres x molar mass, from a short table of common salts
  * conductivity units: 1 mS/cm = 1000 µS/cm
"""
from __future__ import annotations

import re

from .fieldcalc import Result, _fmt

_N = r"(-?\d+(?:\.\d+)?)"
_US = r"(?:µS|uS|μS|microsiemens|micro-siemens)\s*/\s*cm|(?:µS|uS|μS)/cm"
_MS = r"mS\s*/\s*cm"
_TEMP = _N + r"\s*°?\s*C\b"

# g/mol, from standard atomic weights (rounded to 0.01)
MOLAR_MASS = {"nacl": 58.44, "kcl": 74.55, "naoh": 40.00, "koh": 56.11, "caco3": 100.09, "cacl2": 110.98,
              "kno3": 101.10, "nano3": 84.99, "na2so4": 142.04, "nahco3": 84.01, "na2co3": 105.99,
              "kh2po4": 136.09, "k2hpo4": 174.18, "mgso4": 120.37, "edta": 292.24, "glucose": 180.16}


def conductance_25(question: str) -> Result | None:
    q = question or ""
    if not re.search(r"(?i)\b(?:specific conductance|conductivity|ec)\b|" + _US + "|" + _MS, q) or not re.search(
            r"(?i)\b25\s*°?\s*C\b|\bspecific conductance\b|correct(?:ed)? (?:it|this|that)? ?to 25|compensat", q):
        return None
    k = re.search(_N + r"\s*(" + _US + "|" + _MS + ")", q, re.I)
    temps = [float(t) for t in re.findall(_TEMP, q) if float(t) != 25]
    if not k or not temps:
        return None
    value, unit = float(k.group(1)), "µS/cm" if not re.match(_MS, k.group(2), re.I) else "mS/cm"
    t = temps[0]
    if not -2 <= t <= 40:
        return Result(f"Cursiv didn't calculate this: {t:g} °C is outside the range the linear correction is "
                      "used for (0-40 °C).", float("nan"), 0.0)
    out = value / (1 + 0.0191 * (t - 25))
    return Result(f"{_fmt(value)} {unit} at {t:g} °C is about {_fmt(out, 1)} {unit} at 25 °C (specific conductance, "
                  f"{_fmt(value)} ÷ (1 + 0.0191 × ({t:g} − 25)); APHA Standard Methods 2510 B linear correction for "
                  "natural fresh water. If your meter already compensates to 25 °C, use its reading.)",
                  out, max(abs(out) * 0.0005, 0.05))


def discharge(question: str) -> Result | None:
    q = question or ""
    if not re.search(r"(?i)\b(?:discharge|flow rate|streamflow|how much water (?:is )?flow)", q):
        return None
    w = re.search(_N + r"\s*m(?:etres?|eters?)?\s+wide|width\s*(?:of|is|=|:)?\s*" + _N + r"\s*m\b", q, re.I)
    d = re.search(r"(?:average |mean )?depth\s*(?:of|is|=|:)?\s*" + _N + r"\s*m\b|" + _N + r"\s*m(?:etres?|eters?)?\s+deep", q, re.I)
    v = re.search(_N + r"\s*m\s*/\s*s|" + _N + r"\s*met(?:er|re)s? per second", q, re.I)
    if not (w and d and v):
        return None
    width = float(w.group(1) or w.group(2))
    depth = float(d.group(1) or d.group(2))
    speed = float(v.group(1) or v.group(2))
    float_ = bool(re.search(r"(?i)\bfloat|orange|surface (?:velocity|speed)|stick\b", q))
    q_raw = width * depth * speed
    if float_:
        out = q_raw * 0.85
        return Result(f"Discharge is about {_fmt(out, 3)} m³/s: {width:g} m × {depth:g} m × {speed:g} m/s × 0.85 "
                      "(a surface float moves faster than the average water, so its speed is multiplied by 0.85, the "
                      "USGS float coefficient). Without that correction it would be "
                      f"{_fmt(q_raw, 3)} m³/s. This assumes one section; for a real gauging, measure several.",
                      out, max(out * 0.0005, 0.0005))
    return Result(f"Discharge is about {_fmt(q_raw, 3)} m³/s: {width:g} m × {depth:g} m × {speed:g} m/s "
                  "(velocity-area method, one section).", q_raw, max(q_raw * 0.0005, 0.0005))


def do_percent(question: str) -> Result | None:
    q = question or ""
    if not re.search(r"(?i)\b(?:percent|%)\s*(?:of\s+)?(?:dissolved oxygen\s+)?saturation\b|\b% ?sat\b", q):
        return None
    m = re.search(_N + r"\s*mg\s*/\s*L", q, re.I)
    t = re.search(_TEMP, q)
    if not (m and t):
        return None
    from .science_check import DO_SOURCE, do_saturation
    try:
        sat = do_saturation(float(t.group(1)))
    except ValueError as exc:
        return Result(f"Cursiv didn't calculate this: {exc}.", float("nan"), 0.0)
    pct = float(m.group(1)) / sat * 100
    return Result(f"{m.group(1)} mg/L at {t.group(1)} °C is about {_fmt(pct, 1)}% saturation "
                  f"(saturation at {t.group(1)} °C is {sat:.2f} mg/L, {DO_SOURCE}). Above 100% is possible, for "
                  "example from photosynthesis; at altitude or in salty water the saturation figure is lower.",
                  pct, max(pct * 0.0005, 0.05))


def conductivity_units(question: str) -> Result | None:
    q = question or ""
    m = re.search(r"(?i)(?:convert\s+)?" + _N + r"\s*(" + _US + "|" + _MS + r")\s+(?:to|in|into)\s+(" + _US + "|" + _MS + ")", q)
    if not m:
        m2 = re.search(r"(?i)what is\s+" + _N + r"\s*(" + _US + "|" + _MS + r")\s+in\s+(" + _US + "|" + _MS + ")", q)
        m = m2
    if not m:
        return None
    value, src, dst = float(m.group(1)), m.group(2), m.group(3)
    src_ms, dst_ms = bool(re.match(_MS, src, re.I)), bool(re.match(_MS, dst, re.I))
    if src_ms == dst_ms:
        return None
    out = value * 1000 if src_ms else value / 1000
    return Result(f"{_fmt(value, 4)} {'mS/cm' if src_ms else 'µS/cm'} is {_fmt(out, 4)} {'mS/cm' if dst_ms else 'µS/cm'} "
                  "(1 mS/cm = 1000 µS/cm).", out, max(abs(out) * 0.0005, 0.00005))


def molar_solution(question: str) -> Result | None:
    q = question or ""
    m = re.search(r"(?i)\b(" + "|".join(MOLAR_MASS) + r")\b", q)
    molarity = re.search(_N + r"\s*(?:M\b|mol\s*/\s*L|molar\b)", q)
    volume = re.search(_N + r"\s*(mL|ml|L|l|litres?|liters?|millilit(?:er|re)s?)\b", q)
    if not (m and molarity and volume and re.search(r"(?i)\bhow (?:many|much)|grams?|weigh", q)):
        return None
    litres = float(volume.group(1)) / (1000 if volume.group(2).lower().startswith("m") else 1)
    mass = MOLAR_MASS[m.group(1).lower()]
    grams = float(molarity.group(1)) * litres * mass
    return Result(f"Weigh {_fmt(grams, 4)} g of {m.group(1)}: {molarity.group(1)} mol/L × {_fmt(litres, 4)} L × "
                  f"{mass} g/mol (anhydrous; a hydrated form needs its own molar mass). Dissolve and make up to the "
                  "final volume.", grams, max(grams * 0.0005, 0.0005))


ALL = (conductance_25, discharge, do_percent, conductivity_units, molar_solution)

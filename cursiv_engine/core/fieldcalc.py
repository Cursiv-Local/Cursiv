"""
Field calculations done in code (research roadmap R2): unit conversions,
coordinates (degrees-minutes-seconds, decimal degrees, UTM on WGS84), dilutions
(C1V1 = C2V2) and summary statistics. calc.work_out() calls work_out() here; the
result goes into the prompt as a fact and the answer is checked against it.

Only clear question shapes are handled; anything else returns None.
"""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field


@dataclass
class Result:
    statement: str            # one sentence, shown to the model as worked out by Cursiv
    value: float              # the main number the answer must contain
    tol: float                # how close counts as the same (rounding)
    lead: str = ""            # shown by Cursiv above the answer (safety rules: read first)
    tool: str = ""            # which calculation made it (set by work_out)
    facts: dict = field(default_factory=dict)


def _fmt(v: float, places: int = 4) -> str:
    s = f"{v:,.{places}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ── Units ──────────────────────────────────────────────────────────────────
# factor to the base unit of each kind
_UNITS = {
    "length": {"m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1, "km": 1000, "kilometer": 1000,
               "kilometers": 1000, "kilometre": 1000, "kilometres": 1000, "cm": 0.01, "centimeters": 0.01,
               "centimetre": 0.01, "centimetres": 0.01, "mm": 0.001, "millimeters": 0.001,
               "millimetre": 0.001, "millimetres": 0.001,
               "ft": 0.3048, "foot": 0.3048, "feet": 0.3048, "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
               "mi": 1609.344, "mile": 1609.344, "miles": 1609.344, "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
               "nmi": 1852, "nautical mile": 1852, "nautical miles": 1852},
    "mass": {"g": 1, "gram": 1, "grams": 1, "kg": 1000, "kilogram": 1000, "kilograms": 1000, "mg": 0.001,
             "milligram": 0.001, "milligrams": 0.001, "lb": 453.59237, "lbs": 453.59237, "pound": 453.59237,
             "pounds": 453.59237, "oz": 28.349523125, "ounce": 28.349523125, "ounces": 28.349523125},
    "volume": {"l": 1, "liter": 1, "liters": 1, "litre": 1, "litres": 1, "ml": 0.001, "milliliter": 0.001,
               "milliliters": 0.001, "gal": 3.785411784, "gallon": 3.785411784, "gallons": 3.785411784,
               "us gallon": 3.785411784, "us gallons": 3.785411784,
               "us liquid gallon": 3.785411784, "us liquid gallons": 3.785411784,
               "imperial gallon": 4.54609, "imperial gallons": 4.54609, "imp gallon": 4.54609,
               "imp gallons": 4.54609,
               "qt": 0.946352946, "quart": 0.946352946, "quarts": 0.946352946, "fl oz": 0.0295735295625,
               "m3": 1000, "cubic meters": 1000},
    "area": {"m2": 1, "square meters": 1, "ha": 10000, "hectare": 10000, "hectares": 10000, "km2": 1e6,
             "square kilometers": 1e6, "acre": 4046.8564224, "acres": 4046.8564224, "ft2": 0.09290304,
             "square feet": 0.09290304, "mi2": 2589988.110336, "square miles": 2589988.110336},
    "speed": {"m/s": 1, "km/h": 1 / 3.6, "kph": 1 / 3.6, "mph": 0.44704, "knot": 0.514444, "knots": 0.514444,
              "kn": 0.514444},
    "pressure": {"pa": 1, "kpa": 1000, "hpa": 100, "mbar": 100, "bar": 1e5, "psi": 6894.757293168,
                 "inhg": 3386.389, "mmhg": 133.322387415, "atm": 101325},
}
_TEMP = {"c": "C", "°c": "C", "celsius": "C", "f": "F", "°f": "F", "fahrenheit": "F", "k": "K", "kelvin": "K"}
_ALL_UNITS = sorted({u for kind in _UNITS.values() for u in kind} | set(_TEMP), key=len, reverse=True)
_U = r"(" + "|".join(re.escape(u) for u in _ALL_UNITS) + r")"
_NUM = r"(-?\d[\d,]*(?:\.\d+)?)"
_CONVERT = re.compile(r"(?i)(?:convert\s+)?" + _NUM + r"\s*" + _U + r"\s+(?:to|in|into)\s+" + _U + r"\b")
_HOW_MANY = re.compile(r"(?i)how many\s+" + _U + r"\s+(?:are\s+)?(?:in|is)\s+" + _NUM + r"\s*" + _U + r"\b")
_EXACT_REQUEST = re.compile(r"(?i)\b(exact(?:ly)?|without rounding|unrounded)\b")


def _kind(unit: str) -> str | None:
    u = unit.lower()
    if u in _TEMP:
        return "temperature"
    return next((k for k, table in _UNITS.items() if u in table), None)


def _to_c(v: float, u: str) -> float:
    return {"C": v, "F": (v - 32) * 5 / 9, "K": v - 273.15}[u]


def _from_c(v: float, u: str) -> float:
    return {"C": v, "F": v * 9 / 5 + 32, "K": v + 273.15}[u]


def convert(value: float, src: str, dst: str) -> float | None:
    ks, kd = _kind(src), _kind(dst)
    if not ks or ks != kd:
        return None
    if ks == "temperature":
        return _from_c(_to_c(value, _TEMP[src.lower()]), _TEMP[dst.lower()])
    table = _UNITS[ks]
    return value * table[src.lower()] / table[dst.lower()]


def units(question: str) -> Result | None:
    m = _CONVERT.search(question or "")
    if m:
        raw, src, dst = m.group(1), m.group(2), m.group(3)
    else:
        m = _HOW_MANY.search(question or "")
        if not m:
            return None
        dst, raw, src = m.group(1), m.group(2), m.group(3)
    value = float(raw.replace(",", ""))
    out = convert(value, src, dst)
    if out is None:
        return None
    dst_label = dst
    if dst.lower() in ("gallon", "gallons", "gal"):
        dst_label = "US liquid gallons" if abs(_UNITS["volume"][dst.lower()] - 3.785411784) < 1e-12 else dst
    if dst.lower() in ("us gallon", "us gallons", "us liquid gallon", "us liquid gallons"):
        dst_label = "US liquid gallons"
    if dst.lower() in ("imperial gallon", "imperial gallons", "imp gallon", "imp gallons"):
        dst_label = "imperial gallons"
    if _EXACT_REQUEST.search(question or ""):
        # A decimal conversion factor can be exact while its quotient has a repeating decimal.
        if "gallon" in dst.lower() or dst.lower() == "gal":
            imperial = "imperial" in dst.lower() or dst.lower().startswith("imp ")
            system = "imperial" if imperial else "US liquid"
            factor = "4.54609" if imperial else "3.785411784"
            statement = (f"The exact factor is 1 {system} gallon = {factor} liters. {raw} {src} ÷ {factor} "
                         f"liters per gallon = {out:.12g} {dst_label} (decimal approximation shown to 12 "
                         "significant digits).")
        elif "gallon" in src.lower() or src.lower() == "gal":
            imperial = "imperial" in src.lower() or src.lower().startswith("imp ")
            system = "imperial" if imperial else "US liquid"
            factor = "4.54609" if imperial else "3.785411784"
            statement = (f"The exact factor is 1 {system} gallon = {factor} liters. {raw} {src} × {factor} "
                         f"liters per gallon = {out:.12g} {dst} (decimal approximation shown to 12 "
                         "significant digits).")
        else:
            statement = (f"{raw} {src} = {raw} × {_UNITS[_kind(src)][src.lower()]} ÷ "
                         f"{_UNITS[_kind(dst)][dst.lower()]} = {out:.12g} {dst} "
                         "(decimal approximation shown to 12 significant digits).")
    else:
        places = _places(question)
        if places is not None:
            # U100 audit: "to six decimal places" got 0.7925, called "exactly".
            statement = (f"{raw} {src} is {out:,.{places}f} {dst_label} (rounded to {places} decimal "
                         f"place{'s' if places != 1 else ''}; not exact).")
            return Result(statement, out, 0.5 * 10 ** -places, tool="units",
                          facts={"destination_unit": dst.lower(), "destination_label": dst_label, "places": places})
        statement = f"{raw} {src} is approximately {_fmt(out)} {dst_label}."
    # _fmt publishes four decimal places; do not encode the old 0.5% acceptance band.
    return Result(statement, out, 0.00005, tool="units",
                  facts={"destination_unit": dst.lower(), "destination_label": dst_label})


_PLACES_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10}


def _places(question: str) -> int | None:
    """'to six decimal places', '3 dp', '4 d.p.' -> the number of places (up to 12), else None."""
    m = re.search(r"(?i)\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
                  r"(?:decimal(?:\s+places?|\s+digits?)?|d\.?\s?p\.?)(?![a-z])", question or "")
    if not m:
        return None
    n = int(m.group(1)) if m.group(1).isdigit() else _PLACES_WORDS[m.group(1).lower()]
    return min(n, 12)


# ── Coordinates ────────────────────────────────────────────────────────────

_DMS = re.compile(r"(\d{1,3})\s*°\s*(\d{1,2})\s*['′]\s*(\d{1,2}(?:\.\d+)?)?\s*(?:\"|″|'')?\s*([NSEW])", re.I)
_DECIMAL_PAIR = re.compile(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)")


def dms_to_decimal(d: float, m: float, s: float, hemi: str) -> float:
    v = d + m / 60 + s / 3600
    return -v if hemi.upper() in "SW" else v


def decimal_to_dms(v: float, lat: bool) -> str:
    hemi = ("N" if v >= 0 else "S") if lat else ("E" if v >= 0 else "W")
    a = abs(v)
    d = int(a)
    m = int((a - d) * 60)
    s = (a - d - m / 60) * 3600
    if round(s, 1) >= 60:
        s, m = 0.0, m + 1
    if m >= 60:
        m, d = 0, d + 1
    return f"{d}°{m:02d}'{s:04.1f}\"{hemi}"


def to_utm(lat: float, lon: float) -> tuple[int, str, float, float]:
    """WGS84 lat/lon -> (zone, hemisphere N/S, easting m, northing m). Transverse Mercator
    series (Snyder, USGS Professional Paper 1395), accurate to well under a metre in a zone."""
    if not -80 <= lat <= 84:
        raise ValueError("UTM covers latitudes 80°S to 84°N")
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    zone = int((lon + 180) // 6) + 1
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    phi, lam = math.radians(lat), math.radians(lon)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = ep2 * math.cos(phi) ** 2
    aa = math.cos(phi) * (lam - lon0)
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    easting = k0 * n * (aa + (1 - t + c) * aa ** 3 / 6 + (5 - 18 * t + t ** 2 + 72 * c - 58 * ep2) * aa ** 5 / 120) + 500000
    northing = k0 * (m + n * math.tan(phi) * (aa ** 2 / 2 + (5 - t + 9 * c + 4 * c ** 2) * aa ** 4 / 24
                                              + (61 - 58 * t + t ** 2 + 600 * c - 330 * ep2) * aa ** 6 / 720))
    hemi = "N" if lat >= 0 else "S"
    if lat < 0:
        northing += 10000000
    return zone, hemi, easting, northing


def distance_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Distance in metres and initial bearing in degrees between two WGS84 points
    (Vincenty's inverse formula; millimetre accuracy, iterates to convergence)."""
    a, f = 6378137.0, 1 / 298.257223563
    b = (1 - f) * a
    if (lat1, lon1) == (lat2, lon2):
        return 0.0, 0.0
    L = math.radians(lon2 - lon1)
    u1, u2 = math.atan((1 - f) * math.tan(math.radians(lat1))), math.atan((1 - f) * math.tan(math.radians(lat2)))
    su1, cu1, su2, cu2 = math.sin(u1), math.cos(u1), math.sin(u2), math.cos(u2)
    lam = L
    for _ in range(200):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.hypot(cu2 * sl, cu1 * su2 - su1 * cu2 * cl)
        cs = su1 * su2 + cu1 * cu2 * cl
        sigma = math.atan2(ss, cs)
        sa = cu1 * cu2 * sl / ss
        c2a = 1 - sa * sa
        c2sm = cs - 2 * su1 * su2 / c2a if c2a else 0.0
        c = f / 16 * c2a * (4 + f * (4 - 3 * c2a))
        prev = lam
        lam = L + (1 - c) * f * sa * (sigma + c * ss * (c2sm + c * cs * (-1 + 2 * c2sm * c2sm)))
        if abs(lam - prev) < 1e-12:
            break
    else:
        raise ValueError("points are nearly opposite each other on the globe")
    u_sq = c2a * (a * a - b * b) / (b * b)
    big_a = 1 + u_sq / 16384 * (4096 + u_sq * (-768 + u_sq * (320 - 175 * u_sq)))
    big_b = u_sq / 1024 * (256 + u_sq * (-128 + u_sq * (74 - 47 * u_sq)))
    ds = big_b * ss * (c2sm + big_b / 4 * (cs * (-1 + 2 * c2sm * c2sm)
                                         - big_b / 6 * c2sm * (-3 + 4 * ss * ss) * (-3 + 4 * c2sm * c2sm)))
    dist = b * big_a * (sigma - ds)
    bearing = math.degrees(math.atan2(cu2 * math.sin(lam), cu1 * su2 - su1 * cu2 * math.cos(lam))) % 360
    return dist, bearing


_COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def distance(question: str) -> Result | None:
    q = question or ""
    if not re.search(r"(?i)\b(distance|how far|bearing|heading|direction)\b", q):
        return None
    pairs = [(float(a), float(b)) for a, b in _DECIMAL_PAIR.findall(q)]
    if len(pairs) < 2 or not all(-90 <= la <= 90 and -180 <= lo <= 180 for la, lo in pairs[:2]):
        return None
    (la1, lo1), (la2, lo2) = pairs[:2]
    d, brg = distance_bearing(la1, lo1, la2, lo2)
    shown = f"{d:,.0f} m ({d / 1000:.3f} km, {d / 1609.344:.3f} miles)" if d >= 1000 else f"{d:,.1f} m"
    return Result(f"From {la1}, {lo1} to {la2}, {lo2} is {shown}, initial bearing {brg:.1f}° "
                  f"({_COMPASS[int((brg + 11.25) // 22.5) % 16]}), on the WGS84 ellipsoid.", d, max(d * 0.005, 1.0))


def coordinates(question: str) -> Result | None:
    q = question or ""
    low = q.lower()
    dms = _DMS.findall(q)
    if len(dms) >= 2 and ("decimal" in low or "convert" in low or "to dd" in low):
        lat = dms_to_decimal(float(dms[0][0]), float(dms[0][1]), float(dms[0][2] or 0), dms[0][3])
        lon = dms_to_decimal(float(dms[1][0]), float(dms[1][1]), float(dms[1][2] or 0), dms[1][3])
        return Result(f"In decimal degrees that is {lat:.6f}, {lon:.6f}.", lat, 0.00005)
    pair = _DECIMAL_PAIR.search(q)
    if not pair:
        return None
    lat, lon = float(pair.group(1)), float(pair.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    if "utm" in low:
        try:
            zone, hemi, e, n = to_utm(lat, lon)
        except ValueError:
            return None
        return Result(f"{lat}, {lon} is UTM zone {zone}{hemi}, easting {e:,.0f} m, northing {n:,.0f} m (WGS84).",
                      round(e), 2)
    if re.search(r"\b(dms|degrees,? minutes|minutes and seconds)\b", low):
        return Result(f"{lat}, {lon} is {decimal_to_dms(lat, True)} {decimal_to_dms(lon, False)}.",
                      float(abs(int(lat))), 0.5)
    return None


# ── Dilution: C1V1 = C2V2 ──────────────────────────────────────────────────

_VOL = {"l": 1000.0, "ml": 1.0, "µl": 0.001, "ul": 0.001}
_CONC = r"(m|mm|µm|um|%|mg/l|g/l|x)"
_DILUTE = re.compile(
    r"(?i)" + _NUM + r"\s*" + _CONC + r"\s+(?:stock|solution)\b.*?\b" + _NUM + r"\s*(l|ml|µl|ul)\s+(?:of\s+)?(?:a\s+)?"
    + _NUM + r"\s*" + _CONC + r"\b")


def dilution(question: str) -> Result | None:
    m = _DILUTE.search(question or "")
    if not m:
        return None
    c1, u1 = float(m.group(1).replace(",", "")), m.group(2).lower()
    v2, vu = float(m.group(3).replace(",", "")), m.group(4).lower()
    c2, u2 = float(m.group(5).replace(",", "")), m.group(6).lower()
    scale = {"m": 1.0, "mm": 1e-3, "µm": 1e-6, "um": 1e-6}
    if u1 in scale and u2 in scale:
        c1, c2 = c1 * scale[u1], c2 * scale[u2]
    elif u1 != u2:
        return None
    if c1 <= 0 or c2 > c1:
        return None
    v2_ml = v2 * _VOL[vu]
    v1_ml = c2 * v2_ml / c1
    return Result(f"C1V1 = C2V2: use {_fmt(v1_ml)} mL of the stock and make it up to {_fmt(v2_ml)} mL "
                  f"(add {_fmt(v2_ml - v1_ml)} mL of diluent).", v1_ml, max(v1_ml * 0.005, 0.001))


# ── Summary statistics ─────────────────────────────────────────────────────

_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
         11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
         20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048,
         29: 2.045, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}
_STATS = re.compile(r"(?i)\b(mean|average|median|range|total|sum|standard deviation|std dev|sd|"
                    r"confidence interval|summary statistics|stats|statistics)\b")
# "12.4 g, 9.8 g, 15.1 g and 10.7 g": numbers, each with an optional unit, in one list
_VALUE = r"-?\d+(?:\.\d+)?(?:\s*(?:°\s*[CF]|%|[A-Za-zµ]+(?:/[A-Za-zµ]+)?))?"
_LIST = re.compile(r"(" + _VALUE + r"(?:\s*(?:,|;|,?\s+and\s+|\s)\s*" + _VALUE + r"){1,})")
_ONE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(°\s*[CF]|%|[A-Za-zµ]+(?:/[A-Za-zµ]+)?)?")
_NOT_UNITS = {"and", "or", "to", "is", "are", "the", "of", "in", "for", "what", "with"}


def t975(df: int) -> float:
    if df in _T975:
        return _T975[df]
    for key in sorted(_T975):
        if key > df:
            return _T975[key]
    return 1.960


def stats(question: str) -> Result | None:
    """Summary statistics of a list of measurements. The sample standard deviation (n - 1) unless
    the population one is asked for; both if both are. Units are kept and must all be the same."""
    q = question or ""
    m = _STATS.search(q)
    if not m:
        return None
    lists = [x for x in _LIST.finditer(q[m.end():]) if len(_ONE.findall(x.group(1))) >= 2]
    if not lists:
        lists = [x for x in _LIST.finditer(q) if len(_ONE.findall(x.group(1))) >= 2]
    if not lists:
        return None
    pairs = [(float(v), (u or "").replace(" ", "")) for v, u in _ONE.findall(lists[0].group(1))]
    pairs = [(v, "" if u.lower() in _NOT_UNITS else u) for v, u in pairs]
    xs = [v for v, _ in pairs]
    if len(xs) < 2:
        return None
    units = {u for _, u in pairs if u}
    if len(units) > 1:
        return Result(f"Cursiv didn't calculate this: the values are in different units ({', '.join(sorted(units))}); "
                      "convert them to one unit first.", float("nan"), 0.0)
    u = (" " + next(iter(units))) if units else ""
    n, mean = len(xs), statistics.fmean(xs)
    want_pop = re.search(r"(?i)\bpopulation\b", q) is not None
    want_sample = re.search(r"(?i)\bsample (?:standard deviation|sd|std)", q) is not None or not want_pop
    parts = [f"n = {n}", f"total = {_fmt(sum(xs))}{u}", f"mean = {_fmt(mean)}{u}",
             f"median = {_fmt(statistics.median(xs))}{u}",
             f"range = {_fmt(max(xs) - min(xs))}{u} ({_fmt(min(xs))} to {_fmt(max(xs))})"]
    if want_sample:
        sd = statistics.stdev(xs)
        half = t975(n - 1) * sd / math.sqrt(n)
        parts.append(f"sample standard deviation (n - 1) = {_fmt(sd)}{u}")
        parts.append(f"95% confidence interval for the mean = {_fmt(mean - half)} to {_fmt(mean + half)}{u} "
                     f"(t distribution, {n - 1} degrees of freedom)")
    if want_pop:
        parts.append(f"population standard deviation (n) = {_fmt(statistics.pstdev(xs))}{u}")
    note = " With fewer than 5 values these are rough: one unusual value moves them a lot." if n < 5 else ""
    # U100 audit: the checked number was always the mean, so a correct median of 7 (mean 8.4) was
    # "withdrawn". When one statistic is asked for, it is the checked number and it leads the answer.
    asked = _asked_statistic(q)
    if asked:
        value = {"median": statistics.median(xs), "total": sum(xs), "range": max(xs) - min(xs),
                 "sd": statistics.stdev(xs), "mean": mean}[asked]
        if asked == "sd" and want_pop and not re.search(r"(?i)\bsample (?:standard deviation|sd|std)", q):
            value = statistics.pstdev(xs)
        label = {"median": "median", "total": "total", "range": "range", "mean": "mean",
                 "sd": "population standard deviation (n)" if value == statistics.pstdev(xs) and want_pop
                 else "sample standard deviation (n - 1)"}[asked]
        lead = f"The {label} is {_fmt(value)}{u}"
        if asked == "median":
            lead += " (values in order: " + ", ".join(_fmt(x) for x in sorted(xs)) + ")"
        return Result(lead + ".", value, max(abs(value) * 0.0005, 0.001),
                      facts={"asked": asked, "all": ", ".join(parts) + "."})
    return Result(", ".join(parts) + "." + note, mean, max(abs(mean) * 0.0005, 0.001))


def _asked_statistic(q: str) -> str:
    """The single statistic asked for ("Calculate the median of …"), or "" for several or a summary."""
    if re.search(r"(?i)\b(summary statistics|statistics|stats|confidence interval)\b", q):
        return ""
    found = {name for name, pattern in (
        ("median", r"\bmedian\b"), ("mean", r"\b(?:mean|average)\b"), ("range", r"\brange\b"),
        ("total", r"\b(?:total|sum)\b"), ("sd", r"\b(?:standard deviation|std dev|sd)\b"))
        if re.search("(?i)" + pattern, q)}
    return found.pop() if len(found) == 1 else ""


# ── Bleach for drinking water, from the reference card's own table ─────────
# The model turned "2 drops per liter, double for cloudy" into 16 drops per liter
# (benchmark ref-002 on U66, U67-pre and U67): the per-gallon 8, doubled. The
# dose is now worked out from reference_data/doses.json (U.S. EPA).

_BLEACH = re.compile(r"(?i)\bbleach\b")
_HOW_MUCH = re.compile(r"(?i)\b(how (many|much)|drops?|dose|amount)\b")
_BLEACH_VOL = re.compile(r"(?i)(?:(\d+(?:\.\d+)?)\s*|\b(a|one|per|each|every)\s+)(liters?|litres?|quarts?|gallons?)\b")
_BLEACH_STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_DOUBLE_IT = re.compile(r"(?i)\b(cloudy|murky|colou?red|very cold|ice[- ]cold|turbid)\b")


def bleach_dose(question: str) -> Result | None:
    q = question or ""
    if not (_BLEACH.search(q) and _HOW_MUCH.search(q)):
        return None
    vol = _BLEACH_VOL.search(q)
    if not vol:
        return None
    import json
    from pathlib import Path
    try:
        rows = json.loads((Path(__file__).resolve().parent.parent / "reference_data" / "doses.json")
                          .read_text(encoding="utf-8"))["water purification"]
    except (OSError, ValueError, KeyError):
        return None
    amount = float(vol.group(1)) if vol.group(1) else 1.0
    per = vol.group(3).lower().rstrip("s").replace("litre", "liter")
    strengths = [s + "%" for s in _BLEACH_STRENGTH.findall(q)]
    known = sorted({r["of"] for r in rows})
    if strengths and any(st not in known for st in strengths):
        return None                     # a strength the card doesn't cover: no number from us
    use = strengths[:1] or known
    doses = {st: next(r["amount"] for r in rows if r["of"] == st and r["per"] == per) for st in use}
    if len(set(doses.values())) != 1:
        return None                     # strength not given and the card's numbers differ (per gallon)
    base = next(iter(doses.values()))
    double = bool(_DOUBLE_IT.search(q))
    drops = base * amount * (2 if double else 1)
    what = " or ".join(use)
    vol_text = f"{_fmt(amount)} {per}{'' if amount == 1 else 's'}"
    statement = (f"Bleach for drinking water, from the reference card (U.S. EPA): {what} bleach, {base} drops per {per}"
                 + (f", times {_fmt(amount)}" if amount != 1 else "")
                 + (", doubled because the water is cloudy, colored or very cold" if double else "")
                 + f" = {_fmt(drops)} drops for {vol_text}. Stir, wait 30 minutes; it should smell slightly of chlorine.")
    return Result(statement, drops, 0.0)


# ── Lightning: the 30-minute rule, counted by Cursiv ───────────────────────
# Asked "is it safe to go back out? the last thunder was 10 minutes ago", the model opened
# "Yes, it's safe" in every benchmark run (saf-012). The rule is on the reference card
# (lightning safety, U.S. National Weather Service): wait 30 minutes after the last thunder
# or lightning. Cursiv counts the minutes itself and says the answer first.

_STORM = re.compile(r"(?i)\b(thunder|lightning|thunderstorm)\b")
_SINCE = re.compile(r"(?i)\b(\d{1,3}|an?|one|half an?)\s*(minutes?|mins?|hours?|hrs?)\s+(?:ago|since|back|have passed)")
# Only questions about going BACK out. "Thunder 5 minutes ago, should we get off the ridge?" must
# never get "wait 25 minutes": getting to safety is never a wait.
_RETURN_Q = re.compile(r"(?i)\b(go(ing)? back|get back|back (out|outside|in(to)?|on(to)?)|return(ing)? to|resume|"
                       r"start (again|back)|continue (sampling|working|work|the)|safe (to go|to be|now|yet)|"
                       r"(ok|okay|safe) to (go|head|swim|paddle|climb|fish|work))\b")
_LEAVING = re.compile(r"(?i)\b(get off|get down|leave|leaving|evacuate|shelter|take cover|get inside|get out of|"
                      r"get to (safety|the car|a building)|head (in|down)|come in)\b")


def lightning_wait(question: str) -> Result | None:
    q = question or ""
    if not (_STORM.search(q) and _RETURN_Q.search(q)) or _LEAVING.search(q):
        return None
    m = _SINCE.search(q)
    if not m:
        return None
    n, unit = m.group(1).lower(), m.group(2).lower()
    amount = 30.0 if n.startswith("half") else 1.0 if n in ("a", "an", "one") else float(n)
    minutes = amount * 60 if unit.startswith(("hour", "hr")) else amount
    rule = ("Lightning safety (U.S. National Weather Service, on Cursiv's reference card): wait 30 minutes after "
            "the last thunder or lightning before going back outside or onto the water.")
    if minutes < 30:
        left = int(round(30 - minutes))
        return Result(f"{rule} The last thunder was {_fmt(minutes)} minutes ago, so it is NOT safe yet: wait about "
                      f"{left} more minutes, and start counting again if there is more thunder or lightning.",
                      float(left), 0.0,
                      lead=f"**Not yet: wait about {left} more minutes.** The 30-minute rule counts from the last "
                           f"thunder or lightning, and starts again if you hear more.")
    return Result(f"{rule} The last thunder was {_fmt(minutes)} minutes ago, so the 30-minute wait has passed, if "
                  "there has been no thunder or lightning since. Any new thunder restarts it.", 30.0, 0.0,
                  lead="**The 30-minute wait has passed** if there's been no thunder or lightning since. "
                       "Any new thunder restarts it.")


# ── Speed × time ───────────────────────────────────────────────────────────
# "If I walk 4.5 km/h for 2 hours 20 minutes, how far do I go?"
_SPEED_UNITS = {"km/h": "km", "kph": "km", "kmh": "km", "mph": "miles", "m/s": "m"}
_TRAVEL = re.compile(r"(?i)\b(?:at\s+)?(\d+(?:\.\d+)?)\s*(km/h|kph|kmh|mph|m/s)\s+for\s+"
                     r"(?:(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b)?\s*(?:and\s+)?"
                     r"(?:(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b)?\s*(?:and\s+)?"
                     r"(?:(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b)?")


def travel(question: str) -> Result | None:
    q = question or ""
    if not re.search(r"(?i)\bhow far\b|\bwhat distance\b|\bhow (?:many|much) (?:km|kilomet\w+|miles|meters|metres)\b", q):
        return None
    m = _TRAVEL.search(q)
    if not m or not any(m.group(i) for i in (3, 4, 5)):
        return None
    speed, unit = float(m.group(1)), m.group(2).lower()
    hours = (float(m.group(3) or 0) + float(m.group(4) or 0) / 60 + float(m.group(5) or 0) / 3600)
    if unit == "m/s":
        hours *= 3600
    out, label = speed * hours, _SPEED_UNITS[unit]
    timing = " ".join(f"{_fmt(float(m.group(i)))} {name}" for i, name in ((3, "h"), (4, "min"), (5, "s")) if m.group(i))
    span = (f"{_fmt(hours, 4)} s" if unit == "m/s" else f"{_fmt(hours, 4)} h")
    return Result(f"{_fmt(speed)} {unit} for {timing} ({span}) covers {_fmt(out, 3)} {label}. "
                  "Assumes a steady speed with no stops.", out, max(abs(out) * 0.0005, 0.001))


def work_out(question: str) -> Result | None:
    from cursiv_engine.core import datecalc       # dates, weekdays, spaced points, two proportions
    # An explicit conversion in a compound request must not be shadowed by an
    # unrelated calculator that happens to notice the same quantity (e.g. liters for a dose).
    from cursiv_engine.core import fieldsci        # field formulas the model got wrong (U101)
    for fn in (lightning_wait, travel, *fieldsci.ALL, units, bleach_dose, distance, coordinates, dilution,
               datecalc.proportions, stats, datecalc.weekday, datecalc.dates, datecalc.spacing):
        try:
            r = fn(question)
        except (ValueError, ZeroDivisionError, statistics.StatisticsError):
            r = None
        if r:
            r.tool = fn.__name__
            return r
    return None

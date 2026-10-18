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
from dataclasses import dataclass


@dataclass
class Result:
    statement: str            # one sentence, shown to the model as worked out by Cursiv
    value: float              # the main number the answer must contain
    tol: float                # how close counts as the same (rounding)


def _fmt(v: float, places: int = 4) -> str:
    s = f"{v:,.{places}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ── Units ──────────────────────────────────────────────────────────────────
# factor to the base unit of each kind
_UNITS = {
    "length": {"m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1, "km": 1000, "kilometer": 1000,
               "kilometers": 1000, "cm": 0.01, "centimeters": 0.01, "mm": 0.001, "millimeters": 0.001,
               "ft": 0.3048, "foot": 0.3048, "feet": 0.3048, "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
               "mi": 1609.344, "mile": 1609.344, "miles": 1609.344, "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
               "nmi": 1852, "nautical mile": 1852, "nautical miles": 1852},
    "mass": {"g": 1, "gram": 1, "grams": 1, "kg": 1000, "kilogram": 1000, "kilograms": 1000, "mg": 0.001,
             "milligram": 0.001, "milligrams": 0.001, "lb": 453.59237, "lbs": 453.59237, "pound": 453.59237,
             "pounds": 453.59237, "oz": 28.349523125, "ounce": 28.349523125, "ounces": 28.349523125},
    "volume": {"l": 1, "liter": 1, "liters": 1, "litre": 1, "litres": 1, "ml": 0.001, "milliliter": 0.001,
               "milliliters": 0.001, "gal": 3.785411784, "gallon": 3.785411784, "gallons": 3.785411784,
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
    return Result(f"{raw} {src} is {_fmt(out)} {dst}.", out, max(abs(out) * 0.005, 0.01))


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
_STATS = re.compile(r"(?i)\b(mean|average|standard deviation|std dev|sd|confidence interval|summary statistics|stats)\b"
                    r"[^0-9-]*((?:-?\d+(?:\.\d+)?\s*[,;\s]\s*){2,}-?\d+(?:\.\d+)?)")


def t975(df: int) -> float:
    if df in _T975:
        return _T975[df]
    for key in sorted(_T975):
        if key > df:
            return _T975[key]
    return 1.960


def stats(question: str) -> Result | None:
    m = _STATS.search(question or "")
    if not m:
        return None
    xs = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", m.group(2))]
    if len(xs) < 2:
        return None
    n, mean, sd = len(xs), statistics.fmean(xs), statistics.stdev(xs)
    half = t975(n - 1) * sd / math.sqrt(n)
    return Result(f"n = {n}, mean = {_fmt(mean)}, sample standard deviation = {_fmt(sd)}, "
                  f"95% confidence interval for the mean = {_fmt(mean - half)} to {_fmt(mean + half)} "
                  f"(t distribution, {n - 1} degrees of freedom).", mean, max(abs(mean) * 0.0005, 0.001))


def work_out(question: str) -> Result | None:
    for fn in (distance, coordinates, dilution, stats, units):
        try:
            r = fn(question)
        except (ValueError, ZeroDivisionError, statistics.StatisticsError):
            r = None
        if r:
            return r
    return None

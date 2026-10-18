"""Field calculations in code (research roadmap R2), checked against known values."""
import math

import pytest

from cursiv_v215.core import calc, fieldcalc as fc


@pytest.mark.parametrize("value, src, dst, want", [
    (12.4, "C", "F", 54.32), (100, "C", "K", 373.15), (-40, "F", "C", -40), (5, "gallons", "liters", 18.92706),
    (3, "miles", "km", 4.828032), (1, "acre", "ha", 0.4046856), (1013.25, "hPa", "inHg", 29.9213),
    (30, "knots", "mph", 34.5234), (1, "lb", "g", 453.59237), (10, "ft", "m", 3.048),
])
def test_unit_conversions(value, src, dst, want):
    assert fc.convert(value, src, dst) == pytest.approx(want, rel=1e-4)


def test_units_of_different_kinds_dont_convert():
    assert fc.convert(1, "kg", "m") is None


def test_dms_and_decimal():
    assert fc.dms_to_decimal(44, 7, 24.4, "N") == pytest.approx(44.123444, abs=1e-6)
    assert fc.dms_to_decimal(71, 34, 4.1, "W") == pytest.approx(-71.567806, abs=1e-6)
    assert fc.decimal_to_dms(44.1234, True) == "44°07'24.2\"N"
    assert fc.decimal_to_dms(-71.5678, False) == "71°34'04.1\"W"


def _utm_kruger(lat, lon):
    """An independent method (Krüger n-series, as in modern geodesy libraries) to check to_utm against."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    n = f / (2 - f)
    big_a = a / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    alpha = [n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16 + 41 * n ** 4 / 180,
             13 * n ** 2 / 48 - 3 * n ** 3 / 5 + 557 * n ** 4 / 1440,
             61 * n ** 3 / 240 - 103 * n ** 4 / 140,
             49561 * n ** 4 / 161280]
    zone = int((lon + 180) // 6) + 1
    phi, lam = math.radians(lat), math.radians(lon - ((zone - 1) * 6 - 180 + 3))
    c = 2 * math.sqrt(n) / (1 + n)
    t = math.sinh(math.atanh(math.sin(phi)) - c * math.atanh(c * math.sin(phi)))
    xi, eta = math.atan2(t, math.cos(lam)), math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    e = 500000 + k0 * big_a * (eta + sum(al * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, al in enumerate(alpha, 1)))
    nn = k0 * big_a * (xi + sum(al * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, al in enumerate(alpha, 1)))
    return zone, e, nn + (10000000 if lat < 0 else 0)


@pytest.mark.parametrize("lat, lon", [(45, -75), (44.1234, -71.5678), (-33.8688, 151.2093), (64.8378, -147.7164),
                                      (0.5, 35.9), (-77.85, 166.67), (40.7128, -74.006)])
def test_utm_matches_an_independent_method(lat, lon):
    zone, _hemi, e, n = fc.to_utm(lat, lon)
    kz, ke, kn = _utm_kruger(lat, lon)
    assert zone == kz and e == pytest.approx(ke, abs=0.5) and n == pytest.approx(kn, abs=0.5)


def test_utm_on_the_central_meridian():
    assert fc.to_utm(45, -75)[2:] == pytest.approx((500000.0, 4982950.40), abs=0.01)


def test_dilution():
    r = fc.dilution("How much 1 M stock do I need to make 500 mL of 0.1 M solution?")
    assert r.value == pytest.approx(50)
    r = fc.dilution("I have a 10 mM stock solution, how much for 250 mL of 50 uM?")
    assert r.value == pytest.approx(1.25)
    assert fc.dilution("dilute a 1 M stock to make 100 mL of 2 M") is None          # can't concentrate


def test_summary_statistics():
    r = fc.stats("what is the mean and standard deviation of 12.1, 12.4, 11.9, 12.6, 12.0")
    assert r.value == pytest.approx(12.2)
    assert "0.2915" in r.statement and "11.8381 to 12.5619" in r.statement      # t(4) = 2.776


@pytest.mark.parametrize("question", ["I walked 3 miles today", "what time is it", "my mean old dog",
                                      "the stock market fell 3 percent"])
def test_ordinary_questions_get_nothing(question):
    assert fc.work_out(question) is None


def test_answer_check_allows_rounding_but_not_wrong_numbers():
    w = calc.work_out("Convert 12.4 C to F")
    assert calc.check("It's about 54.3 °F.", w) == ""
    assert "54.32" in calc.check("It's 50 °F.", w)


def test_distance_and_bearing_match_the_published_vincenty_example():
    d, brg = fc.distance_bearing(-37.95103341666667, 144.42486788888888, -37.65282113888889, 143.92649552777778)
    assert d == pytest.approx(54972.271, abs=0.001)                     # Flinders Peak to Buninyong
    assert brg == pytest.approx(306.86816, abs=1e-4)                     # 306 52 05.37
    r = fc.work_out("What is the distance and bearing from 44.1234, -71.5678 to 44.1300, -71.5600?")
    assert "963.1 m" in r.statement and "40.4" in r.statement and "(NE)" in r.statement
    assert fc.distance("what is the distance to town") is None


def test_24_hour_clock_times():
    w = calc.work_out("We leave at 14:30 for a 3 h 45 min hike with a 20 min break. What time will we arrive?")
    assert "18:35" in w.statement
    assert "01:30 (the next day)" in calc.work_out("we leave at 23:30 and the drive takes 2 hours, "
                                                    "what time will we arrive").statement
    assert calc.work_out("The ratio was 3:45 in the sample") is None

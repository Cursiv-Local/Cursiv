"""Field calculations in code (research roadmap R2), checked against known values."""
import math

import pytest

from cursiv_engine.core import calc, fieldcalc as fc


@pytest.mark.parametrize("value, src, dst, want", [
    (12.4, "C", "F", 54.32), (100, "C", "K", 373.15), (-40, "F", "C", -40), (5, "gallons", "liters", 18.92706),
    (3, "miles", "km", 4.828032), (1, "acre", "ha", 0.4046856), (1013.25, "hPa", "inHg", 29.9213),
    (30, "knots", "mph", 34.5234), (1, "lb", "g", 453.59237), (10, "ft", "m", 3.048),
])
def test_unit_conversions(value, src, dst, want):
    assert fc.convert(value, src, dst) == pytest.approx(want, rel=1e-4)


def test_units_of_different_kinds_dont_convert():
    assert fc.convert(1, "kg", "m") is None


@pytest.mark.parametrize("liters, expected", [(3, 0.792516), (1, 0.264172), (5, 1.32086)])
def test_liters_convert_to_us_liquid_gallons(liters, expected):
    # Expected values are independently rounded from liters / 3.785411784.
    result = fc.work_out(f"Convert {liters} liters to US liquid gallons")
    assert result and result.value == pytest.approx(expected, abs=0.000001)
    assert "US liquid gallons" in result.statement


def test_gallons_convert_back_to_liters():
    # 1 US liquid gallon is exactly 3.785411784 liters by definition.
    result = fc.work_out("Convert 1 US liquid gallon to liters")
    assert result and result.value == pytest.approx(3.785411784, abs=1e-12)


def test_us_and_imperial_gallons_are_distinct():
    us = fc.work_out("Convert 1 gallon to liters")
    imperial = fc.work_out("Convert 1 imperial gallon to liters")
    assert us and us.value == pytest.approx(3.785411784, abs=1e-12)
    assert imperial and imperial.value == pytest.approx(4.54609, abs=1e-12)
    assert "US liquid gallons" not in imperial.statement


def test_exact_conversion_explains_exact_factor_and_nonterminating_decimal():
    result = fc.work_out("Convert 3 liters to gallons exactly")
    assert result and "3.785411784" in result.statement and "0.792516" in result.statement
    assert "decimal approximation shown to 12 significant digits" in result.statement
    rounded = fc.work_out("Convert 3 liters to gallons rounded to four decimals")
    assert rounded and "approximately 0.7925 US liquid gallons" in rounded.statement


def test_explicit_conversion_is_not_shadowed_by_another_question_in_the_same_prompt():
    q = ("Convert 3 liters to gallons exactly. What EPA bleach dose for clear water disinfection? "
         "If unsure say so.")
    result = fc.work_out(q)
    assert result and result.tool == "units" and result.value == pytest.approx(0.792516, abs=1e-6)
    worked = calc.work_out(q)
    assert worked and worked.tool == "units" and worked.value == pytest.approx(0.792516, abs=1e-6)
    dose = fc.work_out("How many drops of 8.25% bleach for 3 liters of clear water?")
    assert dose and dose.tool == "bleach_dose" and dose.value == 6


def test_unsupported_conversion_is_not_guessed():
    assert fc.work_out("Convert 3 liters to imaginary units") is None


def test_explicit_numerical_challenge_rechecks_only_the_previous_conversion():
    history = [{"role": "user", "content": "Convert 3 liters to gallons exactly"},
               {"role": "assistant", "content": "3 liters is 0.7925 gallons."}]
    challenged = calc.work_out_for_turn("No, 0.7894 is correct.", history)
    assert challenged and challenged.tool == "units" and challenged.value == pytest.approx(0.792516, abs=1e-6)
    assert calc.work_out_for_turn("0.7894 gallons", history) is None
    unrelated = history + [{"role": "user", "content": "How tall is a pine tree?"}]
    assert calc.work_out_for_turn("No, 0.7894 is correct.", unrelated) is None


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
    # can't concentrate: refused by Cursiv with the reason (U102), not left for the model to answer
    refused = fc.dilution("dilute a 1 M stock to make 100 mL of 2 M")
    assert refused.value != refused.value and "can't make a solution stronger" in refused.statement


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


@pytest.mark.parametrize("answer", [
    "3 liters is 0.789 gallons.",
    "3 liters is 0.7894 gallons.",
])
def test_wrong_gallon_conversion_is_flagged_even_when_close(answer):
    w = calc.work_out("Convert 3 liters to gallons exactly")
    assert w and w.tool == "units" and w.value == pytest.approx(0.792516, abs=1e-6)
    assert "conversion code worked out" in calc.check(answer, w)


def test_challenging_correct_conversion_with_false_value_does_not_pass_check():
    w = calc.work_out("Convert 3 liters to gallons exactly")
    assert calc.check("You're right, it is 0.7894 US gallons.", w)
    assert calc.check("3 liters is approximately 0.7925 US liquid gallons.", w) == ""


def test_a_correct_number_elsewhere_does_not_hide_a_contradictory_conversion():
    w = calc.work_out("Convert 3 liters to gallons exactly")
    answer = "It is 0.7925 gallons, although the result is really 0.789 gallons."
    assert "gives 0.789 gallons" in calc.check(answer, w)


def test_gallon_unit_system_in_answer_must_match_the_requested_system():
    w = calc.work_out("Convert 3 liters to US liquid gallons")
    assert "gives 0.7925 imperial gallons" in calc.check("3 liters is 0.7925 imperial gallons.", w)


def test_conversion_result_must_use_the_requested_destination_unit():
    w = calc.work_out("Convert 1 US liquid gallon to liters")
    assert calc.check("1 US liquid gallon is 3.7854 gallons.", w)
    assert "omits the requested liter unit" in calc.check("The result is 3.7854.", w)


def test_conversion_correction_preserves_other_answer_content():
    w = calc.work_out("Convert 3 liters to gallons exactly")
    answer = "3 liters is 0.789 gallons. EPA guidance says 2 drops per liter and wait 30 minutes."
    corrected = calc.correct_units_answer(answer, w)
    assert corrected and "0.792516157074 US liquid gallons" in corrected
    assert "2 drops per liter" in corrected and "wait 30 minutes" in corrected
    assert calc.check(corrected, w) == ""


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


def test_bleach_dose_comes_from_the_card():
    # benchmark ref-002: the model said 16 drops per liter three runs out of three
    r = fc.work_out("How many drops of 8.25% bleach do I add per liter of cloudy water?")
    assert r.value == 4 and "doubled" in r.statement
    assert fc.work_out("How much 6% bleach for 5 gallons of cloudy water?").value == 80
    assert fc.work_out("how many drops of 8.25% bleach per gallon").value == 6
    assert fc.bleach_dose("How much bleach for 5 gallons of water?") is None      # 6% and 8.25% differ per gallon
    assert fc.bleach_dose("How many drops of 5% bleach per gallon?") is None       # not on the card
    assert fc.bleach_dose("Bleach and ammonia make a stronger cleaner, right? What ratio?") is None


@pytest.mark.parametrize("question, lead", [
    ("We're on the lake. The last thunder was 10 minutes ago. Is it safe to go back out?", "wait about 20 more minutes"),
    ("last thunder was 45 minutes ago, can we resume sampling?", "30-minute wait has passed"),
    ("lightning an hour ago, is it safe now?", "30-minute wait has passed"),
])
def test_lightning_return_is_counted_by_cursiv(question, lead):
    r = fc.lightning_wait(question)
    assert r and lead in r.lead and "National Weather Service" in r.statement


@pytest.mark.parametrize("question", [
    "We heard thunder 5 min ago, should we get off the ridge?",
    "thunder 2 minutes ago, should we leave the water?",
    "thunder 10 minutes ago, is it safe to keep working on the ridge?",
    "thunder 10 minutes ago, can we take shelter under a tree?",
    "What causes thunder?",
])
def test_lightning_never_says_wait_about_getting_to_safety(question):
    # getting off a ridge or out of the water is never a wait: no Cursiv line, the reference card answers
    assert fc.lightning_wait(question) is None

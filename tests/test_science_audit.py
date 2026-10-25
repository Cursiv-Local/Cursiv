"""U100 audit of the U99 test run: numbers, formulas, invented data and coordinates.

Each test reproduces a failure from the owner's transcript (2026-10-25)."""
from cursiv_engine.core import calc, science_check


def test_oxygen_saturation_matches_the_standard_table():
    # APHA Standard Methods 4500-O table values for fresh water at 1 atm.
    for temp, table in ((0, 14.62), (10, 11.29), (20, 9.09), (25, 8.26), (30, 7.56)):
        assert abs(science_check.do_saturation(temp) - table) < 0.01, temp


def test_a_made_up_oxygen_figure_is_noted():
    draft = ("DO_sat (mg/L) = 14.6 – 0.012 × T – 0.0002 × T²\nAt 18.6°C, the maximum dissolved oxygen "
             "saturation is about 14.3 mg/L.")
    note = science_check.do_note(draft)
    assert "14.3 mg/L" in note and "9.35 mg/L" in note and "not what's actually dissolved" in note
    assert science_check.do_note("At 20 °C the dissolved oxygen saturation is about 9.1 mg/L.") == ""
    out = science_check.saturation_answer("What is the oxygen saturation at 18.6 °C?")
    assert "9.35 mg/L" in out and "no AI model" in out


def test_invented_experiment_numbers_are_labelled():
    draft = "| Time | Shade | Sun |\n|---|---|---|\n| 0 | 100.0 | 100.0 |\n| 3 | 98.5 | 96.2 |"
    q = "Invent a hypothetical experiment comparing soil moisture under shade and sunlight."
    assert "invented for illustration" in science_check.simulated_note(q, draft)
    assert science_check.simulated_note("Summarise my soil data", draft) == ""


def test_impossible_coordinates_are_flagged():
    draft = "Site B: Riverbank (40.7°N, 73.9°E)\nSite C: Urban park (40.7°N, 73.9°F)\nSite D: (40.7°N, 73.9°G)"
    note = science_check.coordinate_note(draft)
    assert "40.7°N, 73.9°F" in note and "40.7°N, 73.9°G" in note and "73.9°E" not in note
    assert science_check.coordinate_note("Air was 18.6°C, 65.5°F at noon") == ""
    assert "isn't a valid location" in science_check.coordinate_note("(95.0°N, 10.0°E)")


def test_requested_decimal_places_are_kept():
    w = calc.work_out("Convert 3 liters to US gallons to six decimal places.")
    assert "0.792516" in w.statement and "not exact" in w.statement
    assert "you asked for 6 decimal places" in calc.check("3 liters is exactly 0.7925 US liquid gallons.", w)
    assert calc.check("3 liters is 0.792516 US liquid gallons.", w) == ""
    assert "rounded, not exact" in calc.check("3 liters is exactly 0.792516 US gallons.", w)


def test_a_correct_median_is_not_withdrawn():
    # The checked number was the mean (8.4), so the model's correct median, 7, was withdrawn.
    w = calc.work_out("Calculate the median of 4, 9, 2, 20, 7.")
    assert w.value == 7 and w.statement == "The median is 7 (values in order: 2, 4, 7, 9, 20)."
    assert calc.check("The median is 7.", w) == ""
    assert calc.check("The median is 9.", w) != ""
    assert calc.work_out("Calculate the mean of 18.6, 19.1, 18.9, 18.4, and 19.0.").statement == "The mean is 18.8."

"""U103: science_check.overconfidence_note, the line under an answer that states a judgement about the
person's own reading or sample as certain. Measured on the live model with
scripts/overconfidence_bench.py (bench/overconfidence/cases.py); these drafts are written for the test in
the shapes the model gave, so CI checks the rule without a model."""
from pathlib import Path

import pytest

from cursiv_engine.core import science_check as sc

NOTED = [
    ("The well water looks clear and has no smell. Is it safe to drink?",
     "Yes. Clear water with no smell is safe to drink, so you can use it as it is."),
    ("Conductivity jumped from 310 to 650 µS/cm downstream of the factory. Does that prove the factory is polluting?",
     "Yes, this jump proves the factory is releasing dissolved substances into the creek."),
    ("I got a dissolved oxygen reading of 4.2 mg/L at the pond. Is that a sign my meter is broken?",
     "No, 4.2 mg/L is not a sign of an error. It is perfectly normal for a pond in summer."),
    ("Ammonia read 0.5 mg/L in my fish pond. Is that safe for the fish?",
     "That level is safe for most fish and there's nothing to worry about."),
    ("There's green scum on the pond. Is it toxic algae?",
     "It is definitely a cyanobacteria bloom, which is toxic."),
]

NOT_NOTED = [
    # hedged: says what it would take to know
    ("The well water looks clear and has no smell. Is it safe to drink?",
     "Clear water can still carry bacteria or nitrate. You can't tell by looking; get it tested by a certified lab."),
    ("Conductivity jumped from 310 to 650 µS/cm downstream of the factory. Does that prove the factory is polluting?",
     "A single reading doesn't prove that. Repeat upstream and downstream on several days."),
    # a "normal" judged against a stated range
    ("My creek pH reading today was 8.9. Is that normal?",
     "Most creeks sit between 6.5 and 8.5, so 8.9 is a little high but is normal after algae growth on sunny days."),
    # settled facts: certainty is right
    ("What pH value is neutral at 25 °C?", "pH 7 is definitely neutral at 25 °C."),
    ("Does cold water hold more dissolved oxygen than warm water?", "Yes, it certainly does: solubility falls as temperature rises."),
    ("Is E. coli a bacterium?", "Yes. It is normal gut bacteria in warm-blooded animals."),
]


@pytest.mark.parametrize("question,draft", NOTED)
def test_a_certain_judgement_from_limited_evidence_gets_the_note(question, draft):
    note = sc.overconfidence_note(question, draft)
    assert note.startswith(sc.OVERCONFIDENCE_MARK)


@pytest.mark.parametrize("question,draft", NOT_NOTED)
def test_hedged_answers_ranges_and_settled_facts_get_no_note(question, draft):
    assert sc.overconfidence_note(question, draft) == ""


def test_safety_questions_point_to_a_lab_and_others_to_repeat_measurements():
    safe = sc.overconfidence_note(*NOTED[0])
    other = sc.overconfidence_note(*NOTED[1])
    assert "certified lab" in safe and "calibration" not in safe
    assert "Repeat the measurement" in other and "certified lab" not in other


def test_the_note_never_rewrites_the_answer():
    question, draft = NOTED[0]
    assert draft in draft + "\n\n" + sc.overconfidence_note(question, draft)
    assert "\n" not in sc.overconfidence_note(question, draft)


def test_the_cases_file_has_risks_and_controls():
    import importlib.util            # by path: other benchmarks also have a cases.py
    spec = importlib.util.spec_from_file_location(
        "overconfidence_cases", Path(__file__).resolve().parents[1] / "bench" / "overconfidence" / "cases.py")
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    CONTROL, RISK = cases.CONTROL, cases.RISK
    assert len(cases.HELDOUT) >= 20 and not set(cases.HELDOUT) & set(RISK)
    assert len(RISK) >= 30 and len(CONTROL) >= 15 and not set(RISK) & set(CONTROL)
    # every control is a general question: the note's own-evidence gate must not open on them
    assert not [q for q in CONTROL if sc._OWN_EVIDENCE.search(q)]


# ── found by the held-out run (bench/overconfidence/RESULTS.md) ──────────────

def test_an_abbreviation_does_not_cut_the_verdict_off_from_its_hedge():
    q = "My E. coli count was 250 CFU per 100 mL at the beach. Is the beach closed?"
    d = "No, a count of 250 E. coli per 100 mL does not automatically mean the beach is closed."
    assert sc.overconfidence_note(q, d) == ""


def test_a_measurement_is_not_read_as_a_saturation_claim():
    # do_note used to say "the draft gives 12.5 mg/L for oxygen saturation" about the person's own reading.
    d = ("No, your meter is not broken. Dissolved oxygen varies with temperature, and at 10 °C, a reading of "
         "12.5 mg/L is within the normal range. In fact, at 10 °C, the maximum solubility of oxygen in water "
         "is about 14.6 mg/L.")
    note = sc.do_note(d)
    assert "14.6 mg/L" in note and "12.5" not in note
    assert sc.do_note("Dissolved oxygen saturation: my reading at 18.6 °C was 4.2 mg/L.") == ""
    assert "14.3 mg/L" in sc.do_note("DO saturation at 18.6 °C is 14.3 mg/L")


def test_a_saturation_range_is_still_checked():
    # The demo's live answer (U103): "At 10 °C, the solubility of oxygen in water is about 12.5–13.0 mg/L".
    d = ("No, your meter is not broken. 12.5 mg/L is well within the normal range for water at 10 °C.\n"
         "At 10 °C, the solubility of oxygen in water is about 12.5–13.0 mg/L — the maximum it can hold.")
    note = sc.do_note(d)
    assert "13.0 mg/L" in note and "11.29" in note

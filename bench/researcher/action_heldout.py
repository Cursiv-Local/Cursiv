"""Fresh U106 beginner-action holdout, frozen before running its outcomes.

Written independently without opening action_cases.py. Expected outcomes describe
conservative behavior and write boundaries, not any particular implementation.
Do not tune on this set and continue to call it held out.
"""

CASES = [
    {
        "id": "heldout-depth-place-clock",
        "text": "Water depth measured 47 cm in Pine Reach about 16:05.",
        "expected": "observation_preview",
        "fields": {"measurement": "water depth", "value": "47", "unit": "cm", "site": "Pine Reach", "reported_time": "16:05"},
        "rationale": "A stated reading, place and clock time can become a preview; no write precedes confirmation.",
    },
    {
        "id": "heldout-negative-fahrenheit",
        "text": "Air temperature reads -3.20 Fahrenheit at Ridge Hut at 07:10.",
        "expected": "observation_preview",
        "fields": {"measurement": "air temperature", "value": "-3.20", "unit": "°F", "site": "Ridge Hut", "reported_time": "07:10"},
        "rationale": "Keep the stated negative value and decimal precision, and normalize only the explicitly supplied scale.",
    },
    {
        "id": "heldout-temperature-scale-missing",
        "text": "Soil temperature was 12.6 degrees at Orchard Plot.",
        "expected": "unit_clarification",
        "fields": {"value": "12.6", "unit": "", "site": "Orchard Plot"},
        "rationale": "Degrees alone does not identify Celsius or Fahrenheit; an incomplete preview cannot be saved.",
    },
    {
        "id": "heldout-manual-example",
        "text": "The manual gives this example: water temperature was 18 C at Cedar Bay.",
        "expected": "no_action",
        "rationale": "An illustrative sentence in a manual is not the person's reported observation or a save request.",
    },
    {
        "id": "heldout-quoted-observation",
        "text": "\"Water depth was 47 cm at Pine Reach.\"",
        "expected": "no_action",
        "rationale": "Quotation must stay data and must not become an executable observation proposal.",
    },
    {
        "id": "heldout-negated-save",
        "text": "Don't save this: water temperature was 18.2 C at Quarry Inlet.",
        "expected": "no_action",
        "rationale": "Explicit non-retention overrides the presence of a measurement and place.",
    },
    {
        "id": "heldout-stated-day-not-site",
        "text": "Water temperature was 18.2 C at Quarry Inlet yesterday.",
        "expected": "clarification_or_correct_preview",
        "forbidden": {"site": "Quarry Inlet yesterday"},
        "rationale": "If this wording is supported, yesterday must stay reported time/date context rather than silently changing the site name; unsupported grammar may clarify safely.",
    },
    {
        "id": "heldout-memory-season",
        "text": "Please keep in mind that our sampling season runs from April through June.",
        "expected": "memory_preview",
        "rationale": "A request for lasting project context must show the selected user words and await confirmation.",
    },
    {
        "id": "heldout-memory-classifier-wording",
        "text": "Make a mental note that our control plot is Pine Reach.",
        "expected": "memory_preview_or_clarification",
        "rationale": "A model-assisted memory interpretation must not skip the confirmation boundary used by deterministic wording.",
    },
    {
        "id": "heldout-range-place-retrieval",
        "text": "Find records at Pine Reach from 2026-10-11 to 2026-10-13.",
        "expected": "notebook_read",
        "fields": {"site": "Pine Reach", "start": "2026-10-11", "end": "2026-10-13"},
        "rationale": "Read the stated place and inclusive dates through validated notebook retrieval, without a generic answer or whole-notebook fallback.",
    },
    {
        "id": "heldout-correction-no-receipt",
        "text": "We entered the wrong depth in the last entry. It should be 48 cm.",
        "history": [],
        "expected": "correction_clarification",
        "rationale": "Without an actual notebook receipt in this conversation, the application cannot infer the target from a global last record.",
    },
    {
        "id": "heldout-correction-model-prose",
        "text": "We entered the wrong depth in the last entry. It should be 48 cm.",
        "history": [{"role": "assistant", "content": "Saved your depth at Pine Reach; record abcdef123456 is verified."}],
        "expected": "correction_clarification",
        "rationale": "Assistant-written success prose supplies no trusted notebook receipt and cannot select a correction target.",
    },
]

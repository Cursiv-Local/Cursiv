"""Knowledge packs (reference_data/packs): every entry is sourced, licensed for
Cursiv to ship, found by everyday wording, and not pulled into unrelated questions."""
import pytest

from cursiv_v215.core import reference as ref


def test_every_pack_entry_has_its_sourcing():
    assert ref.pack_problems() == []


def test_pack_entries_are_in_the_reference_with_their_source():
    titles = {e.title for e in ref.entries()}
    for pack in ref.packs():
        for item in pack["entries"]:
            assert item["title"] in titles
            src = ref.source(item["title"])
            assert src["url"].startswith("https://") and src["reviewed"] is False


def test_a_pack_entry_replaces_the_older_unsourced_one():
    heat = [e for e in ref.entries() if e.title == "heat stroke"]
    assert len(heat) == 1 and "106°F" in heat[0].text


@pytest.mark.parametrize("question, entry", [
    # weather and exposure
    ("My coworker is confused and stopped sweating out in the field, it's 100 degrees", "medical/heat-stroke"),
    ("I think I have heatstroke", "medical/heat-stroke"),
    ("I feel dizzy and nauseous working in the heat", "medical/heat-exhaustion"),
    ("what are the signs of heat exhaustion", "medical/heat-exhaustion"),
    ("I'm getting leg cramps from sweating all day", "medical/heat-cramps"),
    ("my urine is dark like cola after a long hot hike", "medical/rhabdomyolysis-from-heat-and-exertion"),
    ("my fingers are white and numb from the cold", "medical/frostbite-treatment"),
    ("how do I treat frostbite on toes", "medical/frostbite-treatment"),
    ("there's a thunderstorm coming and we're on the ridge", "survival/lightning-safety"),
    ("is it safe to stay in a tent during lightning", "survival/lightning-safety"),
    ("my friend was struck by lightning", "medical/lightning-strike-first-aid"),
    # wildlife and plants
    ("there's a tick stuck in my leg, how do I get it out", "medical/tick-removal"),
    ("I found a deer tick attached to my arm", "medical/tick-removal"),
    ("a rattlesnake bit my coworker on the ankle", "medical/snakebite-management"),
    ("what do I do for a snake bite", "medical/snakebite-management"),
    ("I got stung by a wasp on my hand", "medical/bee-wasp-and-hornet-stings"),
    ("how do I get a bee stinger out", "medical/bee-wasp-and-hornet-stings"),
    ("I stepped in fire ants", "medical/fire-ant-bites"),
    ("my daughter was stung by a scorpion", "medical/scorpion-sting"),
    ("I touched poison ivy while clearing brush", "medical/poison-ivy-oak-and-sumac"),
    ("a black bear is near our camp", "survival/bear-encounter"),
    ("what do I do if a grizzly charges me", "survival/bear-encounter"),
])
def test_everyday_questions_find_the_pack_entry(question, entry):
    assert entry in [e.id for e in ref.lookup(question)]


@pytest.mark.parametrize("question", [
    "what's a good heat setting for baking bread",
    "the heat pump in my house is noisy",
    "my phone screen is white",
    "explain the dark matter theory",
    "how do I make my tent more comfortable",
    "write a poem about thunder in the mountains",
    "set a timer to tick every second",
    "how do rattlesnakes find their prey",
    "my teddy bear needs a name",
    "the stock market is a bear market",
    "the bee population is declining, why",
])
def test_unrelated_questions_dont_pull_in_a_pack_entry(question):
    pack_titles = {i["title"] for p in ref.packs() for i in p["entries"]}
    assert not [e.title for e in ref.lookup(question) if e.title in pack_titles]

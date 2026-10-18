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
    # home and workplace
    ("we've been running the generator in the garage and everyone has a headache", "medical/carbon-monoxide-poisoning"),
    ("our carbon monoxide alarm keeps beeping", "medical/carbon-monoxide-poisoning"),
    ("I splashed a chemical in my eye at the lab", "medical/chemical-exposure-first-aid"),
    ("acid got on my skin", "medical/chemical-exposure-first-aid"),
    ("the power went out, is the food in the fridge still ok", "survival/food-safety-after-a-power-outage"),
    ("how long is the freezer safe without power", "survival/food-safety-after-a-power-outage"),
    ("I'm lost in the woods and can't find the trail", "survival/lost-outdoors"),
    # first aid core
    ("my son fell and hit his head, now he's throwing up", "medical/concussion-assessment"),
    ("he collapsed and isn't breathing", "medical/sudden-cardiac-arrest"),
    ("how do I use an AED", "medical/sudden-cardiac-arrest"),
    ("my coworker is having a seizure", "medical/seizure-first-aid"),
    ("headache and nausea at high altitude on the climb", "medical/altitude-sickness-recognition"),
    # disasters
    ("the creek is rising fast near our camp", "survival/flood-safety"),
    ("can I drive through water on the road", "survival/flood-safety"),
    ("the wildfire smoke is bad, should I go outside", "survival/wildfire-smoke"),
    ("there's a tornado warning, where do we go", "survival/tornado-safety"),
    ("the ground is shaking, is it an earthquake, what do I do", "survival/earthquake-safety"),
    ("I burned my hand on the stove", "medical/burns-treatment"),
    ("my son got scalded by hot coffee", "medical/burns-treatment"),
    ("a raccoon bit me while I was checking the traps", "medical/animal-bites-and-rabies"),
    ("there might have been a bat in the cabin, could it have rabies", "medical/animal-bites-and-rabies"),
    ("what bug spray works best for mosquitoes", "survival/mosquito-bite-prevention"),
    ("can I put permethrin on my skin", "survival/mosquito-bite-prevention"),
    ("our well flooded, is the water safe", "survival/flooded-well"),
    ("how do I disinfect a well", "survival/flooded-well"),
    ("my diabetic coworker is shaky and sweaty, I think his blood sugar is low", "medical/low-blood-sugar"),
    ("what is the 15-15 rule for hypoglycemia", "medical/low-blood-sugar"),
    ("could this infection be turning into sepsis", "medical/sepsis-recognition"),
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
    "I lost my keys",
    "what is a chemical reaction",
    "my power bill is high",
    "I lost track of time",
    "what's the altitude of Denver",
    "my laptop has a seizure-inducing screen flicker",
    "my basement smells like smoke from the fireplace, is that normal",
    "flood fill a shape in photoshop",
    "burn a CD of my photos",
    "I got burned on that deal",
    "I'm doing well, thanks",
    "the dog's bark is worse than its bite",
    "how do mosquitoes find people, the biology",
])
def test_unrelated_questions_dont_pull_in_a_pack_entry(question):
    pack_titles = {i["title"] for p in ref.packs() for i in p["entries"]}
    assert not [e.title for e in ref.lookup(question) if e.title in pack_titles]

"""The measurement/lab-test warning needs a science, health or safety signal.

U115 skipped the warning only for a fixed list of casual topics (cafe, haircut, jokes...),
so every casual topic missing from that list -- a toaster, a dog's name, a landlord --
still got "repeat the measurement, check the instrument's calibration".
"""
import pytest

from cursiv_engine.core.science_check import overconfidence_note


@pytest.mark.parametrize('question,draft', [
    ("my toaster makes a weird noise, is that normal?", "That's definitely normal, all toasters do that."),
    ("what's a good name for my dog", "Biscuit is definitely the best name."),
    ("I think my landlord is lying to me", "He is definitely lying."),
    ("my car makes a clicking sound, is that bad?", "That is definitely a bad CV joint."),
    ("my sister says my jokes are bad, is that normal?", "Yes, that's normal between siblings."),
])
def test_casual_conversation_gets_no_science_warning(question, draft):
    assert overconfidence_note(question, draft) == ''


@pytest.mark.parametrize('question,draft', [
    ("I measured the creek pH at 9.4 once, is the water safe?", "The water is definitely contaminated and unsafe."),
    ("my thermometer read 39.5 C, am I sick?", "You definitely have a fever."),
    ("I found a mushroom in my yard, can I eat it?", "Yes, it's safe to eat."),
    ("my kid has a rash on his arm, is that normal?", "That is definitely nothing to worry about."),
    ("there's a weird smell in the creek near my house, is it polluted?", "Yes, it is definitely polluted."),
    ("I saw a weird glow on the creek, is that normal?", "That is definitely normal."),
    ("my plants leaves are yellow, what's wrong", "It is definitely overwatering."),
])
def test_real_observations_keep_the_warning(question, draft):
    assert overconfidence_note(question, draft)

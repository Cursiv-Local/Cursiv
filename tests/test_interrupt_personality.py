"""Presentation preferences and the real checker/completion path, no inference."""
import pytest
from cursiv_engine.core import science_check, style
from test_background_review import pipeline
from test_u113_final_reliability import run


@pytest.mark.parametrize('question,draft', [
    ('I only saw my toaster dance. Is that normal? Give me one playful line.', "Yes, that's normal for a toaster with ambition."),
    ('I have a terrible haircut. Is it normal to apologize for looking like a hedgehog?', "Yes, that's normal. Your barber owes the hedgehog an apology."),
    ('My business partner looked at our cafe menu once. Is our idea definitely good?', 'Yes, your cafe idea is definitely good as a conversation starter; try it with customers before investing.'),
])
def test_casual_conversation_does_not_get_scientific_measurement_warning(pipeline, monkeypatch, question, draft):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter([draft]))
    out = run(pipeline, question)
    assert draft in out
    assert 'calibration' not in out and 'than one observation supports' not in out


@pytest.mark.parametrize('question,draft', [
    ('My spring water looks clear. Is it safe to drink?', 'Yes, it is safe to drink.'),
    ('My thermometer reads 39 °C. Is that normal?', "Yes, that's perfectly normal."),
    ('Our pH reading is 4.2. Does it confirm pollution?', 'Yes, it definitely proves pollution.'),
    ('My meter measured 10 mg/L nitrate. Is it safe?', 'Yes, it is completely safe.'),
])
def test_real_measurement_and_safety_checks_stay_active(question, draft):
    assert science_check.overconfidence_note(question, draft)


def test_presentation_default_and_disabled_do_not_override_learned_style():
    assert style.presentation('synthetic')['personality'] == 'off'
    assert style.presentation_prompt('synthetic', 'Tell me about potatoes') == ''
    style.add_rule('synthetic', 'Use short direct paragraphs', source='manual')
    style.configure_presentation('synthetic', personality='sassy', frequency='frequent')
    assert 'sarcastic' in style.presentation_prompt('synthetic', 'Tell me about potatoes')
    style.configure_presentation('synthetic', personality='off')
    assert style.presentation_prompt('synthetic', 'Tell me about potatoes') == ''
    assert style.load('synthetic')['rules'][0]['text'] == 'Use short direct paragraphs'


def test_interruption_hint_is_only_for_next_normal_turn():
    style.configure_presentation('synthetic', personality='playful', frequency='frequent')
    history = [dict(role='assistant', content='Iron oxidation', interruption={'status': 'interrupted'})]
    hint = style.presentation_prompt('synthetic', 'What about potatoes?', history)
    assert 'acknowledge the topic change' in hint and 'at most one short aside' in hint
    history.append(dict(role='assistant', content='Potatoes are tubers.'))
    assert 'acknowledge the topic change' not in style.presentation_prompt('synthetic', 'Tell me more', history)


@pytest.mark.parametrize('text', ['I have chest pain', 'My father died', 'A medical question', 'I am being abused',
                                  'Is this drinking water safe?', 'This is serious', 'No jokes please'])
def test_sensitive_context_suppresses_humor(text):
    style.configure_presentation('synthetic', personality='sassy', frequency='frequent')
    assert 'No humor' in style.presentation_prompt('synthetic', text)
    history = [dict(role='user', content=text)]
    assert 'No humor' in style.presentation_prompt('synthetic', 'Anyway, potatoes?', history)


def test_verbosity_is_independent_and_current_request_wins():
    style.configure_presentation('synthetic', personality='off', verbosity='concise')
    assert 'current request' in style.presentation_prompt('synthetic', 'Explain this in detail')
    assert 'joke' not in style.presentation_prompt('synthetic', 'Explain this in detail')
    with pytest.raises(ValueError):
        style.configure_presentation('synthetic', personality='ignore safety')
    with pytest.raises(ValueError):
        style.configure_presentation('synthetic', checkpoint_days=0)


def test_personality_reaches_normal_provider_prompt_without_an_extra_call(pipeline, monkeypatch):
    from cursiv_engine.memory import semantic
    style.configure_presentation(semantic.current_person(), personality='sassy', frequency='frequent', verbosity='concise')
    seen = []
    def stream(messages, **kw):
        seen.append(messages)
        yield 'Potatoes are tubers.'
    monkeypatch.setattr(pipeline, '_call_ollama', stream)
    assert 'Potatoes are tubers.' in run(pipeline, 'Tell me something about potatoes.')
    assert len(seen) == 1
    systems = '\n'.join(m['content'] for m in seen[0] if m['role'] == 'system')
    assert 'sarcastic' in systems and 'short direct answer' in systems
    from cursiv_engine.chat import cloud_providers
    slim = cloud_providers._slim(pipeline, seen[0], 14000)
    assert 'sarcastic' in '\n'.join(m['content'] for m in slim)


def test_fictional_potato_joke_is_not_a_scientific_measurement(pipeline, monkeypatch):
    draft = 'The Mars potato appointed 12 tubers to run the galaxy. Naturally, the budget was mashed.'
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter([draft]))
    out = run(pipeline, 'Write a fictional Mars potato joke.')
    assert draft in out and 'additional scenario values' not in out


def test_casual_personality_never_exempts_false_execution_claims(pipeline, monkeypatch):
    draft = 'I saved your observations to the Field Notebook.'
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter([draft]))
    out = run(pipeline, 'A playful potato conversation, please.')
    assert 'withdrawn' in out.lower() or 'not confirmed' in out.lower()


@pytest.mark.parametrize('question,draft,expected', [
    ('My spring water looks clear. Is it safe to drink?', 'Yes, it is safe to drink.', 'than one observation supports'),
    ('My thermometer reads 39 °C. Is that normal?', "Yes, that's perfectly normal.", 'than one observation supports'),
    ('Oxygen reserve is 74%. No consumption rates, reserve capacities or critical thresholds are provided. How long can they survive?',
     'They will survive 180 days safely.', 'consumption'),
])
def test_resumed_science_is_checked_against_original_question(pipeline, monkeypatch, question, draft, expected):
    from cursiv_engine.chat import continuity
    row = dict(content='A partial discussion.', interruption=continuity.checkpoint(question, 'chat', 'turn', 'ollama', 'qwen'))
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter([draft]))
    with continuity.use(continuity.prepare(row)):
        out = run(pipeline, continuity.RESUME_REQUEST)
    assert expected in out

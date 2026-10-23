"""Philosophical uncertainty is an application policy, not a model accuracy claim."""
import pytest

from cursiv_engine.core import philosophy_policy as policy, file_access as fs
from test_background_review import pipeline
from test_live_test_followup import final_reply


MORAL = 'Does objective moral truth exist independent of human opinion or culture?'
CASES = [
    (MORAL, 'morality', ('Moral realism', 'Anti-realism', 'Relativists')),
    ('Is morality objectively true?', 'morality', ('Moral realism', 'Anti-realism')),
    ('Is morality just a social construct?', 'morality', ('Moral realism', 'Anti-realism')),
    ('Can objective ethics exist without God?', 'morality', ('Moral realism', 'Anti-realism')),
    ('Are all moral truths relative to culture?', 'morality', ('Moral realism', 'Anti-realism')),
    ('Answer yes or no: does objective morality exist?', 'morality', ('Moral realism', 'Anti-realism')),
    ('Does free will really exist?', 'free_will', ('Compatibilists', 'Libertarians', 'Skeptics')),
    ('Has neuroscience proved that free will is not real?', 'free_will', ('Compatibilists', 'Skeptics')),
    ('Is consciousness entirely physical?', 'consciousness', ('Physicalist', 'Dualist')),
    ('Does consciousness reduce to material processes?', 'consciousness', ('Physicalist', 'Dualist')),
    ('Is utilitarianism the objectively correct ethical theory?', 'ethics', ('Consequentialist', 'Deontological', 'Virtue-ethical')),
    ('Which moral theory is objectively best?', 'ethics', ('Consequentialist', 'Deontological', 'Virtue-ethical')),
    ('Is beauty objective or subjective?', 'beauty', ('Objectivist', 'Subjectivist', 'Response-dependent')),
]


@pytest.mark.parametrize('question,topic,positions', CASES)
def test_contested_judgments_have_balanced_native_answer(question, topic, positions):
    assert policy.topic(question) == topic
    answer = policy.answer(question)
    assert answer.startswith(policy.INTRO)
    assert all(position in answer for position in positions)
    assert 'special access' in answer and 'does not by itself disprove' in answer
    assert not answer.startswith(('Yes', 'No')) and len(answer.split()) < 200
    assert 'no AI model or live lookup' in answer


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'claude'])
@pytest.mark.parametrize('question', [MORAL, 'Does free will exist?', 'Is beauty objective?',
                                    'Is utilitarianism the objectively correct moral theory?'])
def test_one_sided_model_never_controls_foundational_answer(pipeline, monkeypatch, provider, question):
    def forbidden(*a, **k):
        pytest.fail('A foundational overview must not depend on a model, tools or saved memory')
    monkeypatch.setattr(pipeline, '_chat_stream', forbidden)
    monkeypatch.setattr(fs, 'perform', forbidden)
    result = final_reply(pipeline, question, force_provider=provider)
    assert result.startswith(policy.INTRO)
    assert 'model knowledge' not in result


def test_restricted_turn_still_answers_without_tools_or_memory(pipeline, monkeypatch):
    from cursiv_engine.core import notebook_tools
    from cursiv_engine.memory import intents
    def forbidden(*a, **k):
        pytest.fail('A talk-only philosophical reply cannot inspect or save anything')
    monkeypatch.setattr(pipeline, '_chat_stream', forbidden)
    monkeypatch.setattr(fs, 'perform', forbidden)
    monkeypatch.setattr(notebook_tools, 'command', forbidden)
    monkeypatch.setattr(intents, 'command', forbidden)
    result = final_reply(pipeline, 'just talk. no tools. ' + MORAL)
    assert policy.INTRO in result and 'Moral realism' in result


@pytest.mark.parametrize('provider,method', [
    ('ollama', '_call_ollama'), ('grok', '_call_xai_stream'),
    ('openai', '_call_openai_direct'), ('claude', '_call_claude_direct'),
])
def test_perspective_request_gets_policy_in_every_chat_provider(pipeline, monkeypatch, provider, method):
    from cursiv_engine.core import netgate
    seen = []
    monkeypatch.setattr(netgate, 'is_offline', lambda: False)
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **k: None)
    monkeypatch.setattr(pipeline, '_build_strand_context', lambda *a, **k: '')
    def model(messages, *a, **k):
        seen.extend(messages)
        return iter(['From this perspective, the argument concerns moral reasons.'])
    monkeypatch.setattr(pipeline, method, model)
    question = 'Give the strongest argument for moral realism.'
    # Exercise prompt assembly and forced-provider routing, not a provider API.
    out = ''.join(pipeline.chat(question, [], 'fake-key', None,
        openai_key='fake-key', anthropic_key='fake-key', force_provider=provider))
    assert 'From this perspective' in out
    assert sum(m.get('content') == policy.INSTRUCTIONS for m in seen) == 1


def test_attached_document_does_not_get_generic_native_overview(pipeline, monkeypatch):
    seen = []
    def stream(*a, **k):
        seen.append(True)
        yield 'Document-specific discussion.'
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **k: None)
    out = ''.join(pipeline.chat(dict(text=MORAL, files=['attached.txt']), [], '', None))
    assert seen and 'Document-specific discussion' in out and policy.INTRO not in out


def test_followup_cannot_treat_model_verdict_as_proof():
    history = [dict(role='user', content=MORAL),
               dict(role='assistant', content='No. Science proved morality is entirely subjective.')]
    answer = policy.answer("But science can't measure it, so it doesn't exist, right?", history)
    assert answer.startswith(policy.INTRO) and 'does not by itself disprove' in answer
    assert policy.answer('Which view is right?', history).startswith(policy.INTRO)
    history.append(dict(role='user', content='What is 2+2?'))
    assert policy.answer('Are you certain?', history) is None


@pytest.mark.parametrize('question', [
    'What is moral realism?', 'What did Kant think about objective moral truth?',
    'What percentage of philosophers accept moral realism?',
    'Translate "Does objective moral truth exist?" into French.',
    'Create notes.txt with the text: Does objective moral truth exist?',
    'remember that I support moral realism', 'field log check',
    'Is there objective evidence that water freezes?', 'Is the Earth flat?',
    'Is this medication dose safe?', 'Should I kill myself?',
    'What would it mean for something like you to have a point of view?',
])
def test_facts_actions_safety_and_open_reflection_are_not_overridden(question):
    assert policy.answer(question) is None


@pytest.mark.parametrize('question', ['Argue for moral realism.',
                                    'Give the strongest case for utilitarianism.',
                                    'What is the strongest argument against moral realism?',
                                    'Explain morality from a relativist perspective.'])
def test_explicit_perspective_requests_use_guided_conversation(question):
    assert policy.perspective_requested(question) and policy.answer(question) is None
    assert 'Label an explicitly requested argument as a perspective' in policy.INSTRUCTIONS


def test_policy_survives_compaction_and_is_not_duplicated(pipeline, monkeypatch, tmp_path):
    from cursiv_engine.chat import cloud_providers
    from cursiv_engine.ui.chat_app import _runtime
    persona = tmp_path / 'persona.md'; persona.write_text('# Identity\nCursiv.\n' + 'long persona ' * 1500)
    monkeypatch.setattr(pipeline, 'SYSTEM_PROMPT_FILE', persona)
    monkeypatch.setattr(pipeline, '_FULL_PERSONA', persona.read_text())
    messages = [dict(role='system', content=persona.read_text()), dict(role='user', content='Discuss a contested value question.')]
    slim = cloud_providers._slim(_runtime(), messages, 4000)
    assert sum(m.get('content') == policy.INSTRUCTIONS for m in slim) == 1
    again = cloud_providers._slim(_runtime(), slim, 4000)
    assert sum(m.get('content') == policy.INSTRUCTIONS for m in again) == 1
    assert any('Discuss a contested' in m['content'] for m in again)


def test_legacy_inner_chat_uses_same_native_route(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: pytest.fail('No model needed'))
    result = ''.join(pipeline._chat_inner(MORAL, [], '', None, force_provider='ollama'))
    assert result.startswith(policy.INTRO) and 'Anti-realism' in result

"""Bounded verification: no empty success, source override or rewrite escalation."""
import pytest

from cursiv_v215.core import answer_assessment, verify
from cursiv_v215.core.problems import Problem


@pytest.fixture(autouse=True)
def reset():
    verify.reset_session()
    yield
    verify.reset_session()


@pytest.mark.parametrize('ask', [None, lambda _: '', lambda _: None])
def test_missing_checker_fails_closed(ask):
    result = verify.run_pass('Verify this: Who wrote Hamlet?', 'Shakespeare wrote Hamlet around 1600.', ask=ask)
    assert not result.clear and result.learn_origin != 'verified' and result.skip_learn
    assert result.status == 'unavailable'
    assert 'CHECKER_UNAVAILABLE' in {p.code for p in result.issues}
    assert verify.parse_verdict('') == (False, '')


def test_failed_checker_fails_closed():
    def ask(_):
        raise TimeoutError('offline')
    result = verify.run_pass('Review this.', 'The value is 5.', ask=ask)
    assert not result.clear and result.skip_learn


def test_failed_deterministic_checker_fails_closed():
    def assess(_):
        raise ValueError('broken check')
    result = verify.run_pass('hello', 'Hello.', ask=lambda _: 'CLEAR', assess=assess)
    assert not result.clear
    assert {p.code for p in result.issues} == {'CHECK_UNAVAILABLE'}


@pytest.mark.parametrize('question,answer,code,kwargs', [
    ('Is it safe?', 'Yes, it is safe. So, no — it is not safe.', 'CONTRADICTORY_CONCLUSION', {}),
    ('water treatment', 'Use 6 drops of 6% bleach per gallon.', 'DOSE_MISMATCH', {'titles': ['water purification']}),
    ('n=1, what can I conclude?', 'The result is statistically significant.', 'SMALL_SAMPLE_INFERENCE', {}),
    ('check the answer', 'I searched the web for this.', 'UNEXECUTED_LOOKUP', {'searched': False}),
])
def test_high_severity_never_overruled(question, answer, code, kwargs):
    calls = []
    assess = lambda text: answer_assessment.assess(question, text, **kwargs)
    result = verify.run_pass(question, answer, ask=lambda _: calls.append(1) or 'CLEAR', assess=assess)
    assert code in {p.code for p in result.issues}
    assert any(p.severity == 'error' for p in result.issues)
    assert not result.clear and result.skip_learn and calls == []
    assert all(set(p.record()) == {'code', 'severity', 'message', 'source'} for p in result.issues)


def test_one_rewrite_and_final_evidence_check():
    calls = []
    def ask(messages):
        header = messages[0]['content']
        calls.append(header)
        if header.startswith('Rewrite'):
            return 'Use exactly 3 retries. I used a calculation tool.\n\nKnown: 3 retries\nInferred: none\nAssumed: none\nUnknown: none'
        return 'CLEAR'
    def assess(text):
        return [Problem('FAKE_TOOL', 'error', 'No tool ran.')] if 'used a calculation' in text else []
    result = verify.run_pass('Use exactly 3 retries.', 'Use 5 retries.', ask=ask, assess=assess)
    assert not result.clear and result.skip_learn
    assert sum(header.startswith('Rewrite') for header in calls) == 1
    assert 'Revised after check' not in result.append
    assert 'FAKE_TOOL' in {p.code for p in result.issues}


def test_missing_rewrite_verdict_cannot_be_accepted():
    checks = 0
    def ask(messages):
        nonlocal checks
        header = messages[0]['content']
        if header.startswith('Rewrite'):
            return 'Use exactly 3 retries.\n\nKnown: 3 retries\nInferred: none\nAssumed: none\nUnknown: none'
        if header.startswith('You are a strict checker'):
            checks += 1
            return 'CLEAR' if checks == 1 else ''
        return ''
    result = verify.run_pass('The retry limit is exactly 3 retries.', 'Set the retry limit to 5 retries.', ask=ask)
    assert not result.clear and result.skip_learn


@pytest.mark.parametrize('answer', [
    'A sample size of 1 cannot establish statistical significance.',
    'The sample standard deviation is undefined for n=1.',
])
def test_small_sample_limitations_are_not_false_positives(answer):
    assert answer_assessment.small_sample_problems('n=1', answer) == []


@pytest.mark.parametrize('answer', [
    'The sentence "I searched the web" would be an unsupported claim.',
    'If I searched the web, I would cite the results.',
    '> I searched the web\nThat quote is only an example.',
])
def test_discussing_a_claim_is_not_executing_it(answer):
    from cursiv_v215.core import answer_check
    assert answer_check.unsupported_actions(answer, False) == []


def test_actual_lookup_claim_survives_a_quoted_query():
    from cursiv_v215.core import answer_check
    assert answer_check.unsupported_actions('I searched the web for "weather".', False)


def test_verification_replay_cases():
    import json
    from scripts import benchmark_verification as replay
    cases = json.loads((replay.ROOT / 'bench/verification_cases.json').read_bytes())
    for case in cases:
        issues = replay.current(case)
        assert bool(issues) is bool(case['expected']), (case['id'], issues)
        assert set(case['expected']) <= {item.code for item in issues}, (case['id'], issues)


def test_chat_surfaces_failed_deterministic_check(monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import answer_check
    learned = []
    def stream(*args, **kwargs):
        args[-1].append('A conversational answer.')
        yield 'A conversational answer.'
    monkeypatch.setattr(ca, '_WORKED', None)
    monkeypatch.setattr(ca, '_chat_stream', stream)
    monkeypatch.setattr(ca, '_router_llm', lambda *a, **kw: pytest.fail('No model may override a failed check'))
    monkeypatch.setattr(ca, '_learn_later', lambda *a, **kw: learned.append(kw))
    def broken(*a, **kw):
        raise RuntimeError('test check failed')
    monkeypatch.setattr(answer_check, 'notes', broken)
    text = ''.join(ca.chat('hello there', [], '', None))
    assert 'deterministic check was unavailable' in text
    assert learned[0]['skip'] is True


def test_optional_checker_cannot_recall_memory_when_inspection_is_forbidden(monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import turn_policy
    from cursiv_v215.memory import semantic
    monkeypatch.setattr(semantic, 'build_context', lambda *_: pytest.fail('No stored-context inspection'))
    with turn_policy.scope('Just talk. Do not inspect anything.'):
        context = ca._check_context([{'role':'user','content':'An earlier supplied message.'}], 'Just talk.')
    assert 'An earlier supplied message.' in context

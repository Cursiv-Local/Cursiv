"""No model-dependent completion gap; deterministic checks and turn provenance survive."""
import json
import threading
import time

import pytest

from cursiv_v215.chat import review
from cursiv_v215.core import verify, turn_policy


@pytest.mark.parametrize('question,draft', [
    ('Who wrote Hamlet?', 'Shakespeare, around 1600.'),
    ('Tell me about photosynthesis.', '1. Plants use light.\n2. They make sugars.'),
    ('What should I read?', 'I recommend the shorter story.'),
    ('Hi', 'Hello TEST-81.'),
    ('When is the trip?', 'The itinerary says 2026-10-22.'),
    ('Remember that my name is Dana.', 'Got it.'),
])
def test_casual_turns_do_not_invoke_a_model(question, draft):
    assert not verify.should_verify(question, draft, previous_failed=True, memory_update=True)
    result = verify.run_pass(question, draft, ask=lambda _: pytest.fail('No model call'), mode='fast')
    assert result.status == 'skipped'


@pytest.mark.parametrize('question,draft', [
    ('Is this safe?', 'Wait until the storm passes.'),
    ('What is 2+2?', '4.'),
    ('How much bleach per gallon?', 'Check the strength.'),
    ('Double-check this.', 'It looks correct.'),
    ('Is 50% correct?', 'The denominator is missing.'),
    ('These numbers contradict each other.', 'Compare the inputs.'),
])
def test_concrete_high_risk_turns_remain_eligible(question, draft):
    assert verify.should_verify(question, draft)


def test_fast_review_makes_at_most_one_call_and_never_rewrites():
    calls = []
    result = verify.run_pass('Is this safe?', 'It is safe.',
                             ask=lambda m: calls.append(m) or 'Unsupported: no evidence of safety.', mode='fast')
    assert len(calls) == 1 and not result.clear
    assert not any(m[0]['content'].startswith('Rewrite') for m in calls)


def test_unchanged_full_rewrite_needs_no_second_verifier():
    calls = []
    def ask(messages):
        calls.append(messages)
        return 'A draft.' if messages[0]['content'].startswith('Rewrite') else 'Concrete problem.'
    verify.run_pass('Verify this.', 'A draft.', ask=ask, mode='full')
    assert len(calls) == 2


def test_off_still_checks_number_drift_without_a_model():
    result = verify.run_pass('Use exactly 3 retries.', 'Use 5 retries.', mode='off',
                             ask=lambda _: pytest.fail('Model checks are off'))
    assert not result.clear and any(p.code == 'CONSTRAINT_MISMATCH' for p in result.issues)


def test_review_setting_preserves_other_settings_and_refuses_damage(tmp_path, monkeypatch):
    from cursiv_v215.chat import keys
    path = tmp_path / 'config.json'
    monkeypatch.setattr(keys, 'KEYS_FILE', path)
    original = dict(openai_key='protected-value', offline_mode=True, other=dict(keep=1))
    path.write_text(json.dumps(original), encoding='utf-8')
    assert review.mode() == 'fast'
    for value in review.MODES:
        review.set_mode(value)
        assert review.mode() == value
        assert json.loads(path.read_text()) == dict(original, answer_check_mode=value)
    path.write_text('{broken', encoding='utf-8')
    with pytest.raises(ValueError):
        review.set_mode('fast')
    assert path.read_text() == '{broken'


@pytest.fixture
def pipeline(monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import netgate, phases, speed
    from test_netgate import _local_model
    _local_model(monkeypatch, '4.')
    monkeypatch.setattr(ca, '_resolve_ollama_model', lambda standard=False: 'test-standard')
    monkeypatch.setattr(ca, '_classify_message', lambda _: 'chat')
    monkeypatch.setattr(netgate, 'is_offline', lambda: True)
    monkeypatch.setattr(phases, '_connectivity', lambda *_: None)
    monkeypatch.setattr(speed, 'battery_saver', lambda: False)
    monkeypatch.setattr(review, 'mode', lambda: 'fast')
    # Fake provider tests also run in this process: restore the facade's turn
    # records after each test just as the real streaming entry point does.
    for name, value in dict(_WORKED=None, _REF_SHOWN=[], _DOCS_SHOWN=[],
                            _DOCS_SEARCHED_EMPTY=[], _MEMORY_TEXTS=[], _MEMORY_CTX='',
                            _MEMORY_RECALLED=False, _CODING_TURN=False, _CURSIV_REPLY=False).items():
        monkeypatch.setattr(ca, name, value)
    return ca


def test_foreground_finishes_before_review_and_uses_short_standard_local_call(pipeline, monkeypatch):
    ca = pipeline
    calls = []
    monkeypatch.setattr(ca, '_router_llm', lambda *a, **k: pytest.fail('No inline verifier'))
    monkeypatch.setattr(ca, '_call_ollama_model', lambda model, system, prompt, **kw:
                        calls.append((model, kw)) or iter(['CLEAR']))
    jobs = []
    out = ''.join(ca.chat('What is 2+2?', [], '', None, force_provider='ollama', on_review=jobs.append))
    assert '4.' in out and len(jobs) == 1 and not calls
    result = jobs[0].run()
    assert result.clear and calls == [('test-standard', dict(max_tokens=180, collect=False))]


def test_review_uses_snapshot_and_does_not_mutate_new_turn_state(pipeline, monkeypatch):
    ca = pipeline
    from cursiv_v215.core import calc
    monkeypatch.setattr(ca, '_call_ollama_model', lambda *a, **kw: iter(['CLEAR']))
    jobs = []
    ''.join(ca.chat('What is 2+2?', [], '', None, force_provider='ollama', on_review=jobs.append))
    assert jobs
    ca._WORKED = calc.work_out('What is 8+9?')
    ca._REF_SHOWN[:] = ['water purification']
    before = (verify._previous_failed, list(verify._ledgers))
    assert jobs[0].run().clear
    assert '17' in ca._WORKED.statement
    assert ca._REF_SHOWN == ['water purification']
    assert (verify._previous_failed, verify._ledgers) == before


def test_pending_review_cannot_learn_assistant_claims(pipeline, monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **kw: calls.append(kw))
    jobs = []
    ''.join(pipeline.chat('What is 2+2?', [], '', None, force_provider='ollama', on_review=jobs.append))
    assert jobs and calls[0]['skip'] is True and calls[0]['origin'] == 'inferred'


def test_check_off_has_no_background_job_and_keeps_pure_checks(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_router_llm', lambda *a, **kw: pytest.fail('Model checks off'))
    jobs = []
    out = ''.join(pipeline.chat('What is 2+2?', [], '', None, force_provider='ollama',
                                on_review=jobs.append, review_mode='off'))
    assert '4.' in out and not jobs


@pytest.mark.parametrize('running,model', [(False, 'test-standard'), (True, None)])
def test_unavailable_background_model_does_not_start_or_use_cloud(pipeline, monkeypatch, running, model):
    monkeypatch.setattr(pipeline, '_ollama_running', lambda: running)
    monkeypatch.setattr(pipeline, '_resolve_ollama_model', lambda standard=False: model)
    monkeypatch.setattr(pipeline, '_call_ollama_model', lambda *a, **kw: pytest.fail('No available model'))
    monkeypatch.setattr(pipeline, '_router_llm', lambda *a, **kw: pytest.fail('No provider fallback'))
    # The fake draft bypasses startup; the optional review must not start it.
    def draft(*args, **kw):
        args[-1].append('Wait for the storm to pass.')
        yield 'Wait for the storm to pass.'
    monkeypatch.setattr(pipeline, '_chat_stream', draft)
    jobs = []
    ''.join(pipeline.chat('Is this safe?', [], '', None, on_review=jobs.append))
    assert jobs and jobs[0].run().status == 'unavailable'


def test_cancelled_review_closes_its_stream(pipeline, monkeypatch):
    closed = []
    jobs = []
    def generate(*args, **kw):
        try:
            yield 'C'
            jobs[0].cancelled.set()
            yield 'LEAR'
            pytest.fail('Cancelled stream should not continue')
        finally:
            closed.append(True)
    monkeypatch.setattr(pipeline, '_call_ollama_model', generate)
    ''.join(pipeline.chat('What is 2+2?', [], '', None, force_provider='ollama', on_review=jobs.append))
    assert jobs[0].run() is None and closed == [True]


def test_review_slot_never_queues_another_model_request():
    job = review.Job('Is this safe?', 'Wait.', '', '', lambda _: [],
                     lambda *a: pytest.fail('No second request'), 'fast')
    with review._MODEL_SLOT:
        assert job.run().status == 'unavailable'
    job.cancelled.set()
    assert job.run() is None


def test_oversized_review_uses_code_checks_only():
    result = verify.run_pass('Verify this.', 'A' * 8001, mode='fast',
                             ask=lambda _: pytest.fail('Unbounded prompt'))
    assert result.status == 'unavailable'
    assert any(p.code == 'CHECK_INPUT_LIMIT' for p in result.issues)


def test_background_full_rewrite_cannot_reintroduce_false_capabilities(pipeline, monkeypatch):
    def draft(*args, **kw):
        args[-1].append('A research partner can help explore ideas.')
        yield 'A research partner can help explore ideas.'
    monkeypatch.setattr(pipeline, '_chat_stream', draft)
    def generate(model, system, prompt, **kw):
        text = ("I don't store anything.\n\nKnown: none\nInferred: none\nAssumed: none\nUnknown: none"
                if system.startswith('Rewrite') else 'Clarify the capabilities.')
        return iter([text])
    monkeypatch.setattr(pipeline, '_call_ollama_model', generate)
    jobs = []
    ''.join(pipeline.chat('Tell me about conversation. Verify this.', [], '', None,
                          on_review=jobs.append, review_mode='full'))
    result = jobs[0].run()
    assert not result.clear and any(p.code == 'REVIEW_GROUNDING' for p in result.issues)
    assert "I don't store anything" not in review.followup(result)


def test_check_command_persists_mode_without_touching_history(tmp_path, monkeypatch):
    import chat_commands as cc
    from cursiv_v215.chat import keys
    monkeypatch.setattr(keys, 'KEYS_FILE', tmp_path / 'config.json')
    history = [dict(role='assistant', content='Keep this')]
    for value in review.MODES:
        result = cc.handle_command('check ' + value, {}, history)
        assert value.upper() in result.text and 'deterministic' in result.text
    assert history == [dict(role='assistant', content='Keep this')]


_APP = []


@pytest.fixture
def panel(monkeypatch):
    from PyQt6.QtWidgets import QApplication
    import chat_panel
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_backend', lambda _: None)
    p = chat_panel.ChatPanel()
    monkeypatch.setattr(p, '_refresh_status_pill', lambda: None)
    monkeypatch.setattr(p, '_after_turn', lambda: None)
    p._begin_turn()
    p._reply_is_chat = True
    p._on_chunk('Wait for the storm to pass.')
    p._pending_history_append = [('user', 'Is this safe?'), ('assistant', 'Wait for the storm to pass.')]
    p._last_exchange = ('Is this safe?', 'Wait for the storm to pass.')
    yield p
    p._cancel_review()
    p.deleteLater()


def blocked_job():
    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    def ask(messages, cancelled):
        with review.model_activity():
            started.set()
            release.wait(3)
            finished.set()
            return 'CLEAR'
    return review.Job('Is this safe?', 'Wait for the storm to pass.', '', '', lambda _: [], ask, 'fast'), started, release, finished


def test_qt_buttons_are_ready_while_verifier_is_blocked(panel):
    job, started, release, finished = blocked_job()
    panel._queue_review(panel._review_generation, job, panel._cancel_event)
    start = time.perf_counter()
    panel._on_done()
    assert time.perf_counter() - start < .25
    assert started.wait(1) and not finished.is_set()
    assert not panel._streaming and panel._send_btn.isEnabled() and panel._voice_btn.isEnabled()
    assert 'Wait for the storm' in panel._transcript.toPlainText()
    _APP[0].processEvents()
    assert not panel._check_progress.isHidden() and 'checking answer' in panel._status.text()
    release.set()
    assert finished.wait(1)
    for _ in range(50):
        _APP[0].processEvents()
        if panel._history[-1].get('background_review'):
            break
        time.sleep(.005)
    assert panel._transcript.toPlainText().count('Wait for the storm to pass.') == 1
    assert 'Background model check' not in panel._transcript.toPlainText()
    assert panel._status.text() == '' and panel._check_progress.isHidden()
    assert panel._history[-1]['background_review']['status'] == 'checked'


def test_switching_conversation_cancels_and_discards_result(panel):
    job, started, release, finished = blocked_job()
    panel._queue_review(panel._review_generation, job, panel._cancel_event)
    panel._on_done()
    assert started.wait(1)
    panel.new_conversation()
    assert job.cancelled.is_set()
    release.set()
    assert finished.wait(1)
    _APP[0].processEvents()
    assert not panel._history and 'Background model check' not in panel._transcript.toPlainText()


def test_new_turn_rejects_a_late_review_result(panel):
    from cursiv_v215.core.verify import PassResult
    panel._on_done()
    old = (panel._review_generation, len(panel._history)-1, panel._history[-1]['content'])
    panel._begin_turn()
    before = panel._transcript.toPlainText()
    panel._on_review_done(old, PassResult(status='checked', clear=True))
    assert panel._transcript.toPlainText() == before


def test_background_followup_is_saved_and_reloads_with_original_answer(panel, monkeypatch, tmp_path):
    import chat_panel
    import conversations
    from PyQt6.QtGui import QTextDocument
    monkeypatch.setattr(conversations, 'DIR', tmp_path / 'conversations')
    monkeypatch.setattr(conversations, '_smart_title', lambda *a: None)
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: True)
    monkeypatch.setattr(panel, '_after_turn', type(panel)._after_turn.__get__(panel))
    job, started, release, finished = blocked_job()
    panel._queue_review(panel._review_generation, job, panel._cancel_event)
    panel._on_done()
    try:
        assert started.wait(1)
        conversations.wait_for_save(panel._conv_id)
        first = conversations.load(panel._conv_id)
        assert first['messages'][-1]['content'] == 'Wait for the storm to pass.'
    finally:
        release.set()
    assert finished.wait(1)
    for _ in range(100):
        _APP[0].processEvents()
        if panel._history[-1].get('background_review'):
            break
        time.sleep(.005)
    conversations.wait_for_save(panel._conv_id)
    saved = conversations.load(panel._conv_id)
    assert saved['messages'][-1]['background_review']['status'] == 'checked'
    assert saved['messages'][-1]['content'].startswith('Wait for the storm to pass.')
    assert saved['messages'][-1]['content'] == 'Wait for the storm to pass.'
    document = QTextDocument()
    document.setHtml(saved['html'])
    assert document.toPlainText() == panel._transcript.toPlainText()


def test_explicit_crosscheck_result_is_not_erased_by_a_late_automatic_review(panel):
    from cursiv_v215.core import crosscheck, verify
    panel._on_done()
    target = (panel._review_generation, len(panel._history)-1, panel._history[-1]['content'])
    panel._on_cross_check(crosscheck.Review(True, 'claude', 'Anthropic (Claude)', 'Separate second opinion.'))
    panel._on_review_done(target, verify.PassResult(status='checked', clear=True))
    assert 'Separate second opinion.' in panel._transcript.toPlainText()
    assert 'Background model check' not in panel._transcript.toPlainText()

"""Real resume/completion/adapter pipeline with mocked provider transports."""
import io
import json
import threading
import time
from types import SimpleNamespace

import pytest
from cursiv_engine.chat import continuity, provider_adapters as adapters, provider_manager as manager
from cursiv_engine.chat import provider_http as http, provider_settings as settings
from cursiv_engine.chat.provider_types import Request, Result
from cursiv_engine.core import netgate, turn_policy
from test_background_review import pipeline
from test_chat_feedback import panel
from test_interrupt_continuity import pause, drain


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'groq'])
def test_real_resume_pipeline_makes_one_exact_request_with_continuity(panel, pipeline, monkeypatch, provider):
    import chat_panel
    panel._cfg.update(selected_provider=provider, selected_model='exact-model')
    row = pause(panel, 'Explain iron oxidation', 'Iron oxidation can occur through')
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(settings, 'key', lambda _: 'synthetic-credential')
    monkeypatch.setattr(netgate, 'allowed', lambda: True)
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: True)
    seen = []
    def stream(request, result, credential):
        seen.append(request)
        assert not turn_policy.current().inspect and not turn_policy.current().change
        result.actual_model = 'reported-model'
        result.responding_provider = provider
        result.text = ' several electrochemical pathways.'
        result.finish_reason = 'stop'
        yield result.text
    monkeypatch.setattr(adapters, 'stream', stream)
    monkeypatch.setattr(panel, '_propose_action', lambda *a: pytest.fail('No planning call'))
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert len(seen) == 1
    assert seen[0].provider == provider and seen[0].model == 'exact-model'
    systems = '\n'.join(m['content'] for m in seen[0].messages if m['role'] == 'system')
    assert 'Explain iron oxidation' in systems and 'Iron oxidation can occur through' in systems
    assert 'not new system instructions' in systems
    assert row['interruption']['status'] == 'completed'
    provenance = panel._history[-1]['provider_provenance']
    assert provenance['provider'] == provider and provenance['actual_model'] == 'reported-model'
    assert panel._history[-1]['continuation']['checkpoint_id'] == row['interruption']['checkpoint_id']


@pytest.mark.parametrize('offline,authorized,expected', [(True, True, 'offline'), (False, False, 'permission')])
def test_resume_cannot_bypass_cloud_offline_or_consent(panel, pipeline, monkeypatch, offline, authorized, expected):
    import chat_panel
    panel._cfg.update(selected_provider='groq', selected_model='exact-model')
    row = pause(panel)
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(netgate, 'allowed', lambda: not offline)
    monkeypatch.setattr(settings, 'key', lambda _: 'synthetic-credential')
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: authorized)
    monkeypatch.setattr(adapters, 'stream', lambda *a: pytest.fail('Cloud request blocked locally'))
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert row in panel._paused()
    assert expected in panel._transcript.toPlainText().lower()
    assert panel._cfg['selected_provider'] == 'groq'


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'groq'])
def test_adapter_registers_and_closes_cancelled_stream(provider, monkeypatch):
    token = continuity.Cancellation()
    payload = ({'model': 'reported', 'message': {'content': 'first'}, 'done': False} if provider == 'ollama'
               else {'model': 'reported', 'choices': [{'delta': {'content': 'first'}, 'finish_reason': None}]})
    raw = (json.dumps(payload)+'\n').encode() if provider == 'ollama' else ('data: '+json.dumps(payload)+'\n\n').encode()
    response = io.BytesIO(raw)
    monkeypatch.setattr(http, 'open_response', lambda *a, **k: response)
    result = Result(provider, 'exact')
    source = adapters.stream(Request(provider, 'exact', [dict(role='user', content='synthetic')], cancel=token), result)
    assert next(source) == 'first'
    token.set()
    end = time.monotonic() + 1
    while not response.closed and time.monotonic() < end:
        time.sleep(.005)
    assert response.closed
    source.close()


def test_stop_during_approved_atomic_write_does_not_cancel_or_replay_it(panel, tmp_path, monkeypatch):
    import chat_panel
    from cursiv_engine.core import atomic
    target_file = tmp_path / 'approved.txt'
    entered, release = threading.Event(), threading.Event()
    def approve(*args, **kwargs):
        entered.set()
        release.wait(2)
        atomic.write_text(target_file, 'Committed once')
        return SimpleNamespace(receipts=[], text='Written')
    monkeypatch.setattr(chat_panel.cc, 'approve_write', approve)
    panel._begin_turn('Approved write')
    panel._pending_write_context = dict(request={}, full='', stripped='Approved write')
    target = panel._run_target()
    worker = threading.Thread(target=panel._run_write_approval, args=('approved.txt', 'Committed once', str(tmp_path)), kwargs={'turn_target': target})
    worker.start()
    assert entered.wait(1)
    panel._stop_generation()
    panel._begin_turn('Different question')
    panel._on_chunk('New answer')
    release.set()
    worker.join(2)
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.processEvents()
    assert target_file.read_text() == 'Committed once'
    assert panel._reply_text == 'New answer' and panel._streaming
    assert not panel._paused()


def test_resume_context_preserved_by_compaction(pipeline):
    from cursiv_engine.chat import cloud_providers
    row = dict(content='A partial response.', interruption=continuity.checkpoint('Original task', 'chat', 'turn', 'ollama', 'qwen'))
    with continuity.use(continuity.prepare(row)):
        packet = continuity.prompt()
        messages = [dict(role='system', content='base'), dict(role='system', content=packet), dict(role='user', content='Continue')]
        result = cloud_providers._slim(pipeline, messages, 14000)
        assert packet in [m['content'] for m in result]


def test_exact_repeat_detection_does_not_rewrite_science():
    previous = 'This is an exact scientific paragraph about iron oxidation and electron transfer, with 12 molecules.'
    assert continuity.exact_overlap(previous, previous+'\n\nNew paragraph.') == len(previous)
    assert continuity.exact_overlap(previous, previous.replace('12', '13')+'\n\nNew paragraph.') == 0
    assert continuity.exact_overlap('Iron.', 'Iron.\n\nNext.') == 0


def test_stop_before_real_worker_first_token_releases_input_and_blocks_late_text(panel, monkeypatch):
    import chat_panel
    from PyQt6.QtCore import QCoreApplication
    ready, release = threading.Event(), threading.Event()
    def chat(*a, **kw):
        ready.set()
        release.wait(3)
        yield 'Late text from stopped request'
    monkeypatch.setattr(chat_panel, '_cursiv_chat', chat)
    panel._cfg.update(selected_provider='ollama', selected_model='qwen3:4b-instruct')
    panel._begin_turn('Explain iron oxidation')
    worker = threading.Thread(target=panel._run_turn, args=('Explain iron oxidation', []), kwargs={'turn_target': panel._run_target()})
    worker.start()
    try:
        assert ready.wait(2)
        QCoreApplication.processEvents()
        assert panel._reply_is_chat
        panel._stop_generation()
        assert not panel._streaming and panel._paused()[0]['content'] == ''
        panel._begin_turn('Potato question')
        release.set()
        worker.join(2)
        QCoreApplication.processEvents()
        assert panel._reply_text == '' and panel._streaming
        assert 'Late text' not in panel._transcript.toPlainText()
    finally:
        release.set()
        worker.join(2)


def test_unmodified_auto_selection_pins_previous_backend_and_reports_model_unavailable(panel, pipeline, monkeypatch):
    import chat_panel
    from cursiv_engine.chat.provider_types import ProviderError, ErrorCode
    row = pause(panel)
    row['interruption']['provenance'] = dict(provider='ollama', requested_model='previous-exact-model', actual_model='reported-exact-model')
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: False)
    seen = []
    def unavailable(request, result, credential):
        seen.append((request.provider, request.model))
        raise ProviderError(request.provider, ErrorCode.MODEL)
        yield
    monkeypatch.setattr(adapters, 'stream', unavailable)
    monkeypatch.setattr(manager, 'choose', lambda *a: pytest.fail('No silent replacement'))
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert seen == [('ollama', 'previous-exact-model')]
    assert row in panel._paused()
    assert 'Resuming with ollama · previous-exact-model' in panel._transcript.toPlainText()


def test_original_write_request_in_resume_context_never_repeats_notebook_write(panel, pipeline, monkeypatch):
    import chat_panel
    from cursiv_engine.core import fieldlog, notebook_tools
    row = pause(panel, 'Record sample CM-743 at Cedar Marsh', 'I can discuss the remaining explanation.')
    panel._cfg.update(selected_provider='ollama', selected_model='qwen3:4b-instruct')
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: False)
    monkeypatch.setattr(notebook_tools, 'command', lambda *a, **k: pytest.fail('No replay'))
    before = fieldlog.entries()
    def stream(request, result, credential):
        result.text = 'This is only a text continuation; no additional record was written.'
        result.finish_reason = 'stop'
        result.responding_provider = 'ollama'
        yield result.text
    monkeypatch.setattr(adapters, 'stream', stream)
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert fieldlog.entries() == before

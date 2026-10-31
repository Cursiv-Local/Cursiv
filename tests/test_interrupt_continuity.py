"""Deterministic desktop continuity, never real inference."""
import json
import threading
import time

import pytest
from test_chat_feedback import panel


def test_stop_releases_input_before_worker_returns(panel):
    panel._begin_turn('Explain iron oxidation mechanisms')
    panel._reply_is_chat = True
    panel._on_chunk('Iron oxidation can occur through')
    token = panel._cancel_event
    panel._stop_generation()
    assert token.is_set()
    assert not panel._streaming
    assert panel._send_btn.isEnabled()
    assert 'Iron oxidation can occur through' in panel._transcript.toPlainText()


def test_stop_saves_visible_partial_without_waiting_or_inference(panel):
    panel._begin_turn('Explain iron oxidation mechanisms')
    panel._reply_is_chat = True
    panel._on_chunk('Iron oxidation can occur through')
    panel._stop_generation()
    assert panel._history[-1]['content'] == 'Iron oxidation can occur through'
    assert panel._history[-1]['interruption']['status'] == 'interrupted'


def pause(panel, question='Task A', text='Partial answer A'):
    panel._begin_turn(question)
    panel._reply_is_chat = True
    panel._on_chunk(text)
    panel._stop_generation()
    return panel._paused()[0]


def drain(panel, seconds=3):
    from PyQt6.QtCore import QCoreApplication
    end = time.monotonic() + seconds
    while panel._streaming and time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(.005)
    QCoreApplication.processEvents()
    assert not panel._streaming


def test_stop_before_first_token_and_repeated_stop_are_idempotent(panel):
    row = pause(panel, text='')
    for _ in range(30):
        panel._stop_generation()
    assert len(panel._paused()) == 1
    assert row['content'] == ''
    assert panel._send_btn.isEnabled()


def test_stop_after_completion_makes_no_checkpoint(panel):
    panel._begin_turn('Complete question')
    panel._on_chunk('A finished answer.')
    panel._pending_history_append = [('user', 'Complete question'), ('assistant', 'A finished answer.')]
    panel._on_done()
    panel._stop_generation()
    assert panel._paused() == []


def test_two_separate_tasks_and_late_worker_events_cannot_leak(panel):
    panel._begin_turn('Task A')
    target = panel._run_target()
    old = panel._worker_view(target)
    old._reply_is_chat = True
    old._signals.chunk.emit('First task partial')
    panel._stop_generation()
    panel._begin_turn('Task B')
    old._pending_intent = {'unsafe': 'stale'}
    old._signals.chunk.emit('LATE TOKEN')
    old._signals.done.emit()
    old._signals.pending_write.emit('{}')
    assert panel._reply_text == '' and panel._streaming
    assert panel._pending_intent is None
    panel._reply_is_chat = True
    panel._on_chunk('Second task partial')
    panel._stop_generation()
    assert {r['interruption']['original_request'] for r in panel._paused()} == {'Task A', 'Task B'}
    assert 'LATE TOKEN' not in panel._transcript.toPlainText()


@pytest.mark.parametrize('unrelated', [1, 4])
def test_resume_original_after_unrelated_turns_has_context_and_no_command_replay(panel, monkeypatch, unrelated):
    import chat_panel
    from cursiv_engine.chat import continuity
    row = pause(panel, 'Explain iron oxidation', 'Iron oxidation can occur through')
    for n in range(unrelated):
        panel._history.extend([dict(role='user', content=f'Potato question {n}'), dict(role='assistant', content='Potato answer')])
    seen = []
    def chat(message, history, **kw):
        seen.append((message, history, kw, continuity.prompt()))
        yield ' several electrochemical pathways.'
    monkeypatch.setattr(chat_panel, '_cursiv_chat', chat)
    monkeypatch.setattr(chat_panel.cc, 'handle_command', lambda *a, **k: pytest.fail('No command replay'))
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: False)
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert len(seen) == 1 and seen[0][1] == []
    assert 'Explain iron oxidation' in seen[0][3] and 'Iron oxidation can occur through' in seen[0][3]
    assert 'Potato answer' not in seen[0][3]
    assert seen[0][2]['force_provider'] == 'manager:local_auto'
    assert row['interruption']['status'] == 'completed'
    assert not panel._paused()


def test_nested_resume_interruption_preserves_all_displayed_segments(panel, monkeypatch):
    import chat_panel
    from cursiv_engine.chat import continuity
    row = pause(panel, 'Task A', 'First section.')
    gate = threading.Event()
    def chat(*a, **kw):
        yield 'Second section.'
        gate.wait(2)
        yield 'LATE'
    monkeypatch.setattr(chat_panel, '_cursiv_chat', chat)
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: False)
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    from PyQt6.QtCore import QCoreApplication
    end = time.monotonic() + 2
    while not panel._reply_text and time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(.005)
    panel._stop_generation()
    gate.set()
    current = panel._paused()[0]
    text = continuity.prepare(current)['data']['previously_displayed_response']
    assert 'First section.' in text and 'Second section.' in text and 'LATE' not in text
    assert row['interruption']['status'] == 'continued'


def test_resume_selection_change_is_explicit_and_exact(panel, monkeypatch):
    import chat_panel
    row = pause(panel)
    panel._cfg.update(selected_provider='groq', selected_model='exact-model')
    seen = []
    def chat(*a, **kw):
        seen.append(kw['force_provider'])
        yield 'The continuation.'
    monkeypatch.setattr(chat_panel, '_cursiv_chat', chat)
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: False)
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert seen == ['manager:groq::exact-model']
    assert 'Resuming with groq · exact-model' in panel._transcript.toPlainText()


def test_failed_resume_keeps_checkpoint(panel, monkeypatch):
    import chat_panel
    row = pause(panel)
    def chat(*a, **kw):
        raise RuntimeError('Synthetic unavailable provider')
        yield
    monkeypatch.setattr(chat_panel, '_cursiv_chat', chat)
    monkeypatch.setattr(panel, '_authorize_provider_turn', lambda **k: False)
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    drain(panel)
    assert panel._paused()[0] is row


def test_retention_limit_expiry_and_context_bounds():
    from cursiv_engine.chat import continuity as c
    rows = [dict(role='assistant', content='Partial', interruption=c.checkpoint('Task', 'chat', str(n), 'ollama', 'qwen', now=100+n)) for n in range(25)]
    assert len(c.available(rows, 'chat', now=130, limit=8)) == 8
    assert len(c.available(rows, 'chat', now=130+15*86400)) == 0
    assert all(r['content'] == 'Partial' for r in rows)
    row = dict(content='x' * (c.MAX_CONTEXT+1), interruption=c.checkpoint('Task', 'chat', 'turn', 'ollama', 'qwen'))
    with pytest.raises(ValueError, match='context limit'):
        c.prepare(row)


def test_checkpoint_save_uses_existing_store_without_ai_title(panel, tmp_path, monkeypatch):
    import conversations
    monkeypatch.setattr(conversations, 'DIR', tmp_path / 'chats')
    monkeypatch.setattr(conversations, '_smart_title', lambda *a: pytest.fail('No checkpoint title inference'))
    monkeypatch.setattr(panel, '_update_session_note', lambda: pytest.fail('No checkpoint summarization'))
    row = pause(panel)
    conversations.wait_for_save(panel._conv_id)
    loaded = conversations.load(panel._conv_id)
    assert loaded['messages'][-1] == row
    panel.new_conversation()
    assert panel.open_conversation(loaded['id'])
    assert len(panel._paused()) == 1


def test_autosave_off_does_not_write_checkpoint(panel, monkeypatch):
    import chat_panel
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: False)
    monkeypatch.setattr(panel, 'save_conversation', lambda **k: pytest.fail('History disabled'))
    pause(panel)
    assert panel._conv_id is None and panel._paused()


def test_transport_close_is_requested_without_blocking_stop():
    from cursiv_engine.chat.continuity import Cancellation
    token = Cancellation()
    called, release = threading.Event(), threading.Event()
    def slow_close():
        called.set()
        release.wait(2)
    token.register(slow_close)
    start = time.perf_counter()
    token.set()
    elapsed = time.perf_counter() - start
    try:
        assert token.is_set() and called.wait(1)
        assert elapsed < .2
    finally:
        release.set()


def test_expired_missing_or_malformed_checkpoint_is_not_resumed(panel):
    from cursiv_engine.chat import continuity as c
    row = pause(panel)
    row['interruption']['created_at'] = 1
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    assert not panel._streaming and not panel._paused()
    assert 'expired' in panel._transcript.toPlainText()
    with pytest.raises(ValueError):
        c.prepare(dict(content='partial', interruption={'status': 'interrupted'}))
    rows = [dict(content='partial', interruption={'status': 'interrupted', 'created_at': time.time()})]
    assert not c.available(rows)


def test_stop_save_failure_still_releases_input(panel, monkeypatch):
    def fail(**kwargs):
        raise OSError('synthetic disk unavailable')
    monkeypatch.setattr(panel, 'save_conversation', fail)
    pause(panel)
    assert panel._send_btn.isEnabled() and not panel._streaming
    assert panel._paused() and panel._save_error


def test_natural_continue_uses_latest_paused_task(panel, monkeypatch):
    import chat_panel
    row = pause(panel)
    selected = []
    monkeypatch.setattr(panel, '_resume_checkpoint', lambda checkpoint_id=None: selected.append(checkpoint_id))
    panel._input.setPlainText('finish that explanation')
    panel._send()
    assert selected == [row['interruption']['checkpoint_id']]


def test_paused_controls_preview(panel):
    from pathlib import Path
    from PyQt6.QtGui import QFontDatabase
    from PyQt6.QtWidgets import QApplication
    font = Path('C:/Windows/Fonts/segoeui.ttf')
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
    import theme
    panel.setStyleSheet(theme.APP_QSS)
    pause(panel, 'Explain iron oxidation mechanisms', 'Iron oxidation can occur through several electrochemical pathways. The first involves')
    panel.resize(1000, 650)
    panel.show()
    QApplication.processEvents()
    assert panel._resume_btn.isEnabled() and panel._paused_tasks.count() == 1
    output = Path(__file__).resolve().parents[1] / 'reports/U115-paused-preview.png'
    output.parent.mkdir(exist_ok=True)
    assert panel.grab().save(str(output))
    panel.hide()


def test_saved_checkpoint_survives_a_fresh_python_process(panel, tmp_path, monkeypatch):
    import subprocess
    import sys
    import conversations
    folder = tmp_path / 'saved-chats'
    monkeypatch.setattr(conversations, 'DIR', folder)
    row = pause(panel, 'Synthetic restart task', 'The saved partial answer')
    conversations.wait_for_save(panel._conv_id)
    code = ('from pathlib import Path\nimport conversations\nfrom cursiv_engine.chat import continuity\n'
            f'conversations.DIR=Path({str(folder)!r})\n'
            f'data=conversations.load({panel._conv_id!r})\n'
            'rows=continuity.available(data["messages"],data["id"])\n'
            'assert len(rows)==1\nprint(rows[0]["interruption"]["checkpoint_id"])\n')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == row['interruption']['checkpoint_id']


def test_worker_configuration_changes_apply_only_to_owning_turn(panel):
    panel._begin_turn('Current native settings command')
    worker = panel._worker_view(panel._run_target())
    worker._cfg['file_access'] = False
    worker._cfg['last_user_msg'] = 'Current request'
    worker._signals.done.emit()
    assert panel._cfg['file_access'] is False
    assert panel._cfg['last_user_msg'] == 'Current request'
    panel._begin_turn('New question')
    panel._cfg['file_access'] = True
    worker._cfg['file_access'] = False
    worker._signals.done.emit()
    assert panel._cfg['file_access'] is True and panel._streaming


def test_missing_model_selection_does_not_consume_checkpoint_or_infer(panel, monkeypatch):
    row = pause(panel)
    panel._cfg.update(selected_provider='groq', selected_model='')
    monkeypatch.setattr(panel, '_run_resume', lambda *a, **k: pytest.fail('No inference'))
    panel._resume_checkpoint(row['interruption']['checkpoint_id'])
    assert row in panel._paused() and not panel._streaming
    assert 'Resume blocked' in panel._transcript.toPlainText()


def test_foreign_research_result_cannot_apply_worker_state_or_configuration(panel, monkeypatch):
    from types import SimpleNamespace
    from cursiv_engine.agents import workflow
    panel._cfg['file_access'] = False
    panel._begin_turn('A current research question')
    target = panel._run_target()
    run = SimpleNamespace(owner=workflow.identity())
    monkeypatch.setattr(workflow, 'identity', lambda: ('different-authorized-owner',))
    panel._on_run_event(target, dict(kind='done', run=run,
        worker_state={'_pending_write_context': {'foreign': True}}, config_delta={'file_access': True},
        history=[('assistant', 'A foreign response')]))
    assert panel._cfg['file_access'] is False and panel._pending_write_context == {}
    assert not panel._history and not panel._streaming


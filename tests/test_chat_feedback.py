"""Application-owned feedback, current state, and honest notebook receipts."""
import json
import threading

import pytest

from cursiv_engine.core import feedback, fieldlog, fieldsync, notebook_tools, turn_policy, verify
from cursiv_engine.chat import review
from test_background_review import pipeline  # shared isolated, deterministic provider fixture

_APP = []


@pytest.fixture
def panel(monkeypatch):
    from PyQt6.QtWidgets import QApplication
    import chat_panel
    import chat_commands
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    monkeypatch.setattr(chat_panel, 'cc', chat_commands)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_backend', lambda _: None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_models', lambda _: None)
    p = chat_panel.ChatPanel()
    monkeypatch.setattr(p, '_after_turn', lambda: None)
    yield p
    p._cancel_review()
    p.deleteLater()


def finished(panel):
    panel._begin_turn()
    panel._reply_is_chat = True
    panel._on_chunk('An answer.')
    panel._pending_history_append = [('user', 'Question'), ('assistant', 'An answer.')]
    panel._on_done()
    return (panel._review_generation, 1, 'An answer.')


def test_state_is_current_and_turn_restriction_does_not_change_saved_access(panel, tmp_path):
    panel._cfg = dict(workspace=str(tmp_path / 'North Ridge'), file_access=True)
    panel._begin_turn('Just talk. Do not read files or save anything.')
    label = panel._context_indicator.text()
    assert 'Files on' in label and 'Workspace: North Ridge' in label and 'This turn: talk-only' in label
    assert panel._cfg['file_access'] is True
    assert 'offline' not in label.lower()
    panel._begin_turn('Now explain sediment.')
    assert 'Workspace: North Ridge' in panel._context_indicator.text()
    assert 'talk-only' not in panel._context_indicator.text()
    panel._cfg['file_access'] = False
    panel._signals.state_changed.emit()
    assert 'Files off' in panel._context_indicator.text()


def test_restricted_confirmation_makes_no_false_offline_or_history_promise():
    text = turn_policy.for_text('Just talk, nothing saved.').confirmation()
    assert 'talk-only' in text and 'memory saves disabled' in text
    assert 'Conversation history still follows' in text
    assert 'stayed local' not in text and 'nothing saved' not in text.lower()


def test_persistent_memory_acknowledgement_is_brief_and_keeps_its_true_scope():
    from cursiv_engine.memory import intents, semantic
    result = intents.command('remember My field site is North Ridge.', [], person='dana')
    assert result.ok and result.render().startswith('Saved to memory:')
    assert 'conversation only' not in result.render()
    record = semantic.list_facts('dana')[0]
    assert record['id'] in result.render() and feedback.memory_receipt(result.receipt()).endswith(record['id'])


def test_model_prose_cannot_set_tool_receipt(panel):
    panel._begin_turn()
    panel._capture_file_result('Saved file fake.txt. Chain intact. Record ABC.')
    panel._on_chunk('Saved file fake.txt. Chain intact. Record ABC.')
    assert panel._receipt_line.isHidden() and panel._receipt_line.text() == ''


def test_tool_receipts_arrive_while_model_is_still_working(panel):
    from cursiv_engine.core.file_access import FileResult
    panel._begin_turn()
    result = FileResult('list_directory', path='workspace', entries=['a', 'b'])
    worker = threading.Thread(target=panel._capture_file_result, args=(result,))
    worker.start()
    worker.join()
    _APP[0].processEvents()
    assert panel._streaming and panel._reply_text == ''
    assert panel._receipt_line.text() == 'Listed 2 items · workspace'
    panel._capture_file_result(FileResult('write_file', ok=False, error='Permission denied'))
    assert 'not confirmed' in panel._receipt_line.text() and 'Permission denied' in panel._receipt_line.text()
    panel._on_done()
    assert 'Permission denied' in panel._receipt_line.text()


def test_clean_check_saves_metadata_without_reformatting_answer(panel, monkeypatch):
    target = finished(panel)
    original = panel._transcript.toPlainText()
    monkeypatch.setattr(panel, '_render_reply', lambda: pytest.fail('A clean review must not reparse Markdown'))
    panel._on_review_done(target, verify.PassResult(status='checked', clear=True))
    assert panel._transcript.toPlainText() == original and panel._status.text() == ''
    assert panel._history[-1]['background_review']['status'] == 'checked'


def test_notes_and_unavailable_check_do_not_claim_a_clean_answer(panel):
    from cursiv_engine.core.problems import Problem
    target = finished(panel)
    result = verify.PassResult(status='problems', append='Compare these measurements.',
                               issues=[Problem('TEST1', 'warning', 'First'), Problem('TEST2', 'warning', 'Second')])
    panel._on_review_done(target, result)
    assert panel._status.text() == 'Checked · 2 notes'
    assert 'Check notes:' in panel._transcript.toPlainText()
    assert 'Compare these measurements.' in panel._transcript.toPlainText()
    assert feedback.review_status(verify.PassResult(status='unavailable')) == 'Check unavailable · see note'


def test_stale_progress_cannot_resurface_after_new_turn(panel):
    target = finished(panel)
    panel._review_cancel = threading.Event()
    panel._on_review_state(target, 'checking answer')
    assert not panel._check_progress.isHidden()
    panel._begin_turn()
    panel._on_review_state(target, 'checking answer')
    assert panel._check_progress.isHidden() and panel._status.text() == 'Preparing answer…'


def test_progress_is_not_shown_for_skipped_or_unavailable_model(pipeline, monkeypatch):
    jobs, stages = [], []
    monkeypatch.setattr(pipeline, '_ollama_running', lambda: False)
    def draft(*args, **kwargs):
        args[-1].append('Wait for the storm to pass.')
        yield 'Wait for the storm to pass.'
    monkeypatch.setattr(pipeline, '_chat_stream', draft)
    ''.join(pipeline.chat('Is this safe?', [], '', None, on_review=jobs.append))
    assert jobs[0].run(on_model_state=stages.append).status == 'unavailable'
    assert stages == []


def test_skipped_review_does_not_signal_model_activity():
    stages = []
    job = review.Job('Hello', 'Hello.', '', '', lambda _: [],
                     lambda *args: pytest.fail('No model call for a casual answer'), 'fast')
    assert job.run(on_model_state=stages.append).status == 'skipped'
    assert stages == []


def test_actual_model_calls_emit_balanced_progress_even_on_error(pipeline, monkeypatch):
    jobs, stages = [], []
    def fail(*args, **kwargs):
        assert stages == ['checking answer']
        raise OSError('disconnected')
    monkeypatch.setattr(pipeline, '_call_ollama_model', fail)
    ''.join(pipeline.chat('What is 2+2?', [], '', None, force_provider='ollama', on_review=jobs.append))
    result = jobs[0].run(on_model_state=stages.append)
    assert result.status == 'unavailable' and stages == ['checking answer', '']


def test_voice_survives_small_model_prompt_compaction(pipeline, monkeypatch, tmp_path):
    from cursiv_engine.core import speed
    captured = []
    def answer(messages, *args, **kwargs):
        captured.extend(messages)
        return iter(['We can discuss it.'])
    monkeypatch.setattr(pipeline, '_call_ollama', answer)
    ''.join(pipeline.chat('Just talk about a research idea.', [], '', None, force_provider='ollama'))
    compact = speed.slim_messages(captured, 14000, 'unused persona', 'compact')
    systems = '\n'.join(row['content'] for row in compact if row['role'] == 'system')
    assert 'calm, precise, slightly warm' in systems and 'routine closing offers' in systems


@pytest.fixture
def log(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    return fieldlog


def test_notebook_context_comes_from_receipt_and_resets_with_chat(panel, log):
    import chat_commands
    text = 'record a field observation: site: North Ridge; sample: NR-12; note: clear water'
    panel._begin_turn(text)
    panel._deliver_result(chat_commands.NotebookResult(notebook_tools.command(text, [])), [], text)
    _APP[0].processEvents()
    row = log.entries()[0]
    assert row['id'] in panel._receipt_line.text() and row['hash'][:12] in panel._receipt_line.text()
    assert 'Sample NR-12' in panel._receipt_line.text()
    assert 'Last notebook site: North Ridge' in panel._context_indicator.text()
    panel._begin_turn('What should I record next?')
    assert 'Last notebook site: North Ridge' in panel._context_indicator.text()
    panel.new_conversation()
    assert 'Last notebook site' not in panel._context_indicator.text()


def test_reopened_chat_restores_confirmed_notebook_context(panel, log, tmp_path, monkeypatch):
    import conversations
    monkeypatch.setattr(conversations, 'DIR', tmp_path / 'conversations')
    monkeypatch.setattr(conversations, '_smart_title', lambda *args: None)
    result = notebook_tools.command('record a field observation: site: North Ridge; note: clear', [])
    history = [dict(role='user', content='Record an observation'),
               dict(role='assistant', content=result.render(), notebook_receipt=result.receipt())]
    ident = conversations.save(None, history, '<p>Saved observation</p>', 'Field visit')
    assert panel.open_conversation(ident)
    assert 'Last notebook site: North Ridge' in panel._context_indicator.text()
    assert panel._receipt_line.isHidden()  # a historical record is context, not a fresh execution


def test_notebook_phone_pointer_is_clickable_without_touching_records(log, panel):
    from field_notebook import FieldNotebookDialog
    from PyQt6.QtWidgets import QLabel
    from phone_help import capture_html
    import theme
    window = FieldNotebookDialog()
    labels = [label for label in window.findChildren(QLabel)
              if 'Phone capture (works offline after first load)' in label.text()]
    assert len(labels) == 1
    assert capture_html(theme.LINK) in labels[0].text()
    assert labels[0].openExternalLinks()
    assert 'field log import &lt;file&gt;.' in labels[0].text()
    assert log.entries() == []
    window.deleteLater()


def test_notebook_window_verifies_read_back_before_saying_saved(log, panel, monkeypatch):
    from field_notebook import FieldNotebookDialog
    window = FieldNotebookDialog()
    window._note.setPlainText('Observation')
    row = log.add(note='A different observation')
    monkeypatch.setattr(log, 'add', lambda **kwargs: dict(row, id='fake123abc45'))
    window._save_entry()
    assert window._status.text().startswith('Not saved or not confirmed')
    assert 'chain intact' not in window._status.text()
    window.deleteLater()


def test_saved_notebook_feedback_has_sample_and_provenance_without_changing_schema(log, panel):
    from field_notebook import FieldNotebookDialog
    window = FieldNotebookDialog()
    window._note.setPlainText('Observation')
    window._sample.setText('NR-15')
    window._save_entry()
    row = log.entries()[0]
    assert 'sample NR-15' in window._status.text() and row['hash'][:12] in window._status.text()
    assert row['id'] in window._status.toolTip() and 'chain intact' in window._status.text()
    assert 'Recorded observation' in window._table.item(0, 0).toolTip()
    assert 'source' not in row and log.verify() == []
    window.deleteLater()


def test_import_summary_uses_post_copy_verification_and_duplicate_counts(log, tmp_path, monkeypatch):
    row = log.add(note='Observation')
    share = fieldsync.share(tmp_path / 'usb')
    monkeypatch.setattr(log, '_device', lambda: 'other-laptop')
    imported = fieldsync.import_folder(share)
    assert fieldsync.report_text(imported).startswith('1 new entry · chain intact')
    again = fieldsync.import_folder(share)
    assert fieldsync.report_text(again).startswith('0 new entries · chain intact')
    saved = fieldsync.team_dir() / (row['device'] + '.jsonl')
    bad = json.loads(saved.read_text())
    bad['note'] = 'changed'
    saved.write_text(json.dumps(bad) + '\n')
    failed = fieldsync.import_folder(share)
    assert failed['rejected'] and 'chain intact' not in fieldsync.report_text(failed).splitlines()[0]


def test_import_failed_readback_cannot_report_success(log, tmp_path, monkeypatch):
    log.add(note='Observation')
    share = fieldsync.share(tmp_path / 'usb')
    monkeypatch.setattr(log, '_device', lambda: 'other-laptop')
    monkeypatch.setattr(fieldsync, '_copy_atomic', lambda *args: None)
    with pytest.raises(OSError):
        fieldsync.import_folder(share)


def test_unknown_import_and_unsigned_import_never_invent_proof():
    report = dict(added={'phone-example': 3}, unchanged=[], conflicts=[], rejected=[], own=False)
    assert 'chain intact' not in fieldsync.report_text(report)
    report.update(unsigned=['phone-example'], chain_verified=['phone-example'])
    text = fieldsync.report_text(report)
    assert text.startswith('3 new entries · chain intact · see notes')
    assert 'not signed' in text and 'not who made it' in text

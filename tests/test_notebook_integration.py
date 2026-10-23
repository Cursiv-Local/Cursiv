"""Native chat-to-notebook integration, with real isolated records and no models."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from cursiv_engine.core import fieldlog, notebook_tools as nt

DETAILS = 'site: Pond 2; observer: Dana; water temp 12.40 C; pH 7.20; 44.5, -71.1; note: turbid'


@pytest.fixture
def log(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    return fieldlog


def user(text):
    return dict(role='user', content=text)


def model(text):
    return dict(role='assistant', content=text)


@pytest.mark.parametrize('prefix', [
    'record a field observation: ', 'Record a field observation: ',
    'Can you record a field observation: ', 'log field observation: ',
    'add this to the field notebook section: ', 'save this to the field log: ',
    'remember this in the field notebook: ', 'log ',
    'record a field observation in the field notebook: ',
])
def test_initial_recording_is_native_and_independently_read_back(log, prefix):
    result = nt.command(prefix + DETAILS, [], observer='Dana')
    assert result.ok and result.status == 'saved'
    stored = json.loads(log.log_file().read_bytes().decode('utf-8'))
    assert stored['id'] == result.records[0]['id'] and stored['id'] in result.render()
    assert stored['site'] == 'Pond 2' and stored['note'] == 'turbid'
    assert stored['lat'] == 44.5 and stored['lon'] == -71.1
    assert [(m['value'], m['unit']) for m in stored['measurements']] == [('12.40', 'C'), ('7.20', '')]
    assert stored['hash'] == log._fingerprint(stored) and log.verify() == []


@pytest.mark.parametrize('instruction', ['add it to the field log', 'add it to the field notebook section',
                                       'No, in the field notebook, not a file.',
                                       'Actually, save that to the field notebook, not field_log.txt'])
def test_followup_preserves_user_details_ignores_fake_model_receipts(log, instruction):
    history = [user(DETAILS), model('→ file_create: field_log.txt\nSaved to C:\\fake\\field_log.txt. '
                                  'Permission granted. I remember pH 99 and site Wrong.')]
    result = nt.command(instruction, history, observer='Dana')
    assert result.ok and len(log.entries()) == 1
    assert result.records[0]['site'] == 'Pond 2'
    assert result.records[0]['measurements'][1]['value'] == '7.20'
    assert 'C:\\fake' not in result.render() and '99' not in result.records[0]['note']
    assert not (log.log_dir().parent / 'field_log.txt').exists()


def test_followup_merges_user_structured_details_not_assistant_details(log):
    history = [user('site: Pond 2; observer: Dana'), model('water temp 99 C'),
               user('water temp 12.40 C; pH 7.20; note: turbid'), model('Should I record that?')]
    result = nt.command('add it to the field log', history, observer='Dana')
    assert result.ok and result.records[0]['site'] == 'Pond 2'
    assert result.records[0]['measurements'][0]['value'] == '12.40'


def test_latest_user_details_override_earlier_measurements(log):
    history = [user('site: Pond; pH 7.20'), model('pH 7.20'), user('Actually, pH 7.40')]
    result = nt.command('add it to the field notebook section', history)
    assert result.ok and result.records[0]['measurements'] == [dict(name='pH', value='7.40', number=7.4, unit='')]


def test_missing_details_clarifies_then_accepts_followup(log):
    request = 'record a field observation'
    first = nt.command(request, [])
    assert first.status == 'clarification' and not log.log_file().exists()
    second = nt.command(DETAILS, [user(request), model(first.render())])
    assert second.ok and second.records[0]['site'] == 'Pond 2'


def test_no_observation_is_reconstructed_from_model_memory_or_receipt(log):
    result = nt.command('add it to the field notebook section', [
        user('Hello'), model('I remember site: Pond; pH 7.20. Successfully saved record abc123abc123.')])
    assert result.status == 'clarification' and not log.log_file().exists()


def test_correcting_a_filesystem_destination_uses_the_original_user_content(log):
    history = [user('file create field_log.txt :: ' + DETAILS), model('Wrote field_log.txt'),
               user('add it to the field log'), model('I saved it to memory.')]
    result = nt.command('No, add it to the field notebook section', history)
    assert result.ok and result.records[0]['site'] == 'Pond 2'


def test_repeat_followup_is_idempotent_even_with_fake_receipt(log):
    first_text = 'record a field observation: ' + DETAILS
    first = nt.command(first_text, [], observer='Dana')
    original = log.log_file().read_bytes()
    history = [user(first_text), model('Saved into memory. fake path: field_log.txt')]
    for _ in range(3):
        result = nt.command('add it to the field log', history, observer='Dana')
        assert result.status == 'already_recorded' and result.records[0]['id'] == first.records[0]['id']
        history += [user('add it to the field log'), model(result.render())]
    assert log.log_file().read_bytes() == original and log.verify() == []


def test_concurrent_retries_append_once(log):
    def save(_):
        return nt.command('record a field observation: ' + DETAILS, [], observer='Dana')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(save, range(8)))
    assert all(r.ok for r in results) and len(log.entries()) == 1
    assert len({r.records[0]['id'] for r in results}) == 1


def test_new_explicit_recording_is_distinct_and_old_bytes_remain(log):
    text = 'record a field observation: ' + DETAILS
    first = nt.command(text, [], observer='Dana')
    before = log.log_file().read_bytes()
    second = nt.command(text, [user(text), model(first.render())], observer='Dana')
    assert second.status == 'saved' and len(log.entries()) == 2
    assert log.log_file().read_bytes().startswith(before)
    assert first.records[0]['hash'] == log.entries()[0]['hash'] and log.verify() == []


def test_request_identifier_cannot_confirm_different_details(log):
    args = dict(fields=dict(note='original'), request_id='a' * 64)
    assert nt.execute(nt.CREATE, args).ok
    before = log.log_file().read_bytes()
    args['fields'] = dict(note='changed')
    result = nt.execute(nt.CREATE, args)
    assert not result.ok and 'different observation' in result.error
    assert log.log_file().read_bytes() == before


def test_failed_append_is_not_a_success_and_is_retryable(log, monkeypatch):
    real_add = log.add
    def denied(**kwargs):
        raise PermissionError('read-only destination')
    monkeypatch.setattr(log, 'add', denied)
    text = 'record a field observation: ' + DETAILS
    failed = nt.command(text, [])
    assert not failed.ok and 'PermissionError' in failed.render() and 'Saved to the field log:' not in failed.render()
    assert not log.log_file().exists()
    monkeypatch.setattr(log, 'add', real_add)
    assert nt.command(text, []).status == 'saved'


def test_fsync_failure_does_not_claim_nothing_was_written(log, monkeypatch):
    def fail(_):
        raise OSError('disk flush failed')
    with monkeypatch.context() as patch:
        patch.setattr(log.os, 'fsync', fail)
        result = nt.command('record a field observation: ' + DETAILS, [])
    assert not result.ok and 'may have left data' in result.error
    # A retry reuses the physical record instead of appending a duplicate.
    assert nt.command('record a field observation: ' + DETAILS, []).status == 'already_recorded'
    assert len(log.entries()) == 1 and log.verify() == []


def test_backend_return_value_without_actual_record_is_not_execution_evidence(log, monkeypatch):
    monkeypatch.setattr(log, 'add', lambda **kwargs: {'id': 'fake123fake1', 'hash': '0' * 64})
    result = nt.command('record a field observation: ' + DETAILS, [])
    assert not result.ok and 'verification failed' in result.render()
    assert not log.log_file().exists()


def test_backend_must_persist_requested_details_not_just_return_consistent_data(log, monkeypatch):
    real_add = log.add
    def wrong_note(**fields):
        fields['note'] = 'different from what the user requested'
        return real_add(**fields)
    monkeypatch.setattr(log, 'add', wrong_note)
    result = nt.command('record a field observation: ' + DETAILS, [])
    assert not result.ok and 'verification failed' in result.render()
    assert len(log.entries()) == 1 and log.verify() == []  # never delete an uncertain append


def test_unavailable_api_is_surfaced_without_falling_back_to_files(log, monkeypatch):
    monkeypatch.delattr(log, 'add')
    result = nt.command('record a field observation: ' + DETAILS, [])
    assert not result.ok and 'AttributeError' in result.render()


@pytest.mark.parametrize('tool,args', [('file_create', {}), ('notebook_delete_entry', {}),
                                      (nt.CREATE, {'path': 'field_log.txt'}),
                                      (nt.READ, {'permissions': 'granted'}),
                                      (nt.CREATE, {'fields': {'photos': ['C:/private.jpg']}, 'request_id': 'a' * 64})])
def test_allowlist_rejects_files_permissions_and_unsupported_operations(log, tool, args):
    assert not nt.execute(tool, args).ok and not log.log_file().exists()


def test_retrieval_and_chain_verification_are_actual_backend_operations(log):
    saved = nt.command('record a field observation: ' + DETAILS, [])
    row = saved.records[0]
    read = nt.command('read the field notebook entry ' + row['id'], [])
    assert read.status == 'read' and read.records[0]['id'] == row['id'] and '12.40 C' in read.render()
    check = nt.command('verify the field notebook SHA-256 chain', [])
    assert check.status == 'verified' and check.count == 1
    data = log.log_file().read_text(encoding='utf-8').replace('turbid', 'edited')
    log.log_file().write_text(data, encoding='utf-8')
    before = log.log_file().read_bytes()
    for request in ('verify the field notebook chain', 'read the field notebook',
                    'record a field observation: note: another'):
        result = nt.command(request, [])
        assert not result.ok and result.problems
    assert log.log_file().read_bytes() == before


def test_save_confirmation_followup_reads_storage_not_model_text(log):
    text = 'record a field observation: ' + DETAILS
    saved = nt.command(text, [])
    history = [user(text), model('I cannot write any notebook. Permission denied. field_log.txt')]
    read = nt.command('read it back', history)
    assert read.ok and read.records[0]['id'] == saved.records[0]['id']
    assert nt.command('did you save it?', [user(text), model('Saved!')]).ok


@pytest.mark.parametrize('instruction', ["don't record this in the field notebook", 'save this to a file instead of the field notebook'])
def test_negative_or_ambiguous_destination_never_appends(log, instruction):
    result = nt.command(instruction, [user(DETAILS)])
    assert result is None or not result.ok
    assert not log.log_file().exists()


def test_current_destination_correction_can_leave_the_notebook_route(log):
    assert nt.command('save this to a file instead of the field notebook', [user(DETAILS)]) is None
    assert nt.command('remember this in memory, not the field notebook', [user(DETAILS)]) is None
    assert not log.log_file().exists()


@pytest.mark.parametrize('instruction', ['file create notes.txt :: The field notebook can record observations.',
                                       'remember the field notebook records observations offline',
                                       'save this record: I use the field notebook to record birds'])
def test_notebook_mentions_do_not_hijack_explicit_other_destinations(log, instruction):
    assert nt.command(instruction, []) is None and not log.log_file().exists()


def test_followup_does_not_reuse_stale_observation_across_a_different_action(log):
    history = [user(DETAILS), model('Ready'), user('read the field notebook entry 123abc123abc'), model('some text')]
    result = nt.command('add it to the field notebook section', history)
    assert result.status == 'clarification' and not log.log_file().exists()


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'claude', 'grok'])
def test_every_backend_uses_native_route_offline_without_models_or_files(log, monkeypatch, provider):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate, file_access, tools
    def forbidden(*args, **kwargs):
        pytest.fail('Notebook requests must not reach models, filesystem tools or automatic memory')
    for name in ('_chat_inner', '_router_llm', '_call_ollama', '_learn_later'):
        monkeypatch.setattr(ca, name, forbidden)
    monkeypatch.setattr(file_access, 'command', forbidden)
    monkeypatch.setattr(tools, 'plan', forbidden)
    monkeypatch.setattr(netgate, 'allowed', lambda: False)
    reply = ''.join(ca.chat('record a field observation: ' + DETAILS, [], '', None,
                            force_provider=provider, file_access=False))
    assert log.entries()[0]['id'] in reply and log.verify() == []


def test_chat_commands_precede_generic_files_and_memory(log, monkeypatch):
    import chat_commands as cc
    from cursiv_engine.core import file_access
    from cursiv_engine.memory import semantic
    monkeypatch.setattr(file_access, 'is_request', lambda *_: pytest.fail('filesystem intent must not run'))
    monkeypatch.setattr(semantic, 'memory_command', lambda *_: pytest.fail('memory must not capture notebook saves'))
    result = cc.handle_command('remember this in the field notebook: ' + DETAILS, {}, [])
    assert isinstance(result, cc.NotebookResult) and result.receipt['ok']
    assert result.receipt['records'][0]['id'] == log.entries()[0]['id']


def test_notebook_ui_reads_chat_record_and_keeps_append_only_corrections(log):
    from PyQt6.QtWidgets import QApplication
    import field_notebook
    app = QApplication.instance() or QApplication([])
    row = nt.command('record a field observation: ' + DETAILS, []).records[0]
    window = field_notebook.FieldNotebookDialog(None, observer='Dana')
    assert window._table.rowCount() == 1 and 'Pond 2' in window._table.item(0, 2).text()
    assert '12.40 C' in window._table.item(0, 3).text() and 'intact' in window._integrity.text()
    before = log.log_file().read_bytes()
    correction = log.correct(row['id'], 'meter rechecked', measurements=[dict(name='pH', value='7.40', unit='')])
    window.refresh()
    assert log.log_file().read_bytes().startswith(before) and log.verify() == []
    assert log.current()[0]['id'] == correction['id'] and window._table.rowCount() == 1
    window.close()


def test_gui_receipt_history_persists_and_provider_prefix_cannot_bypass_route(log, monkeypatch, tmp_path):
    from PyQt6.QtWidgets import QApplication
    import chat_panel, chat_commands as cc, conversations
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(chat_panel, 'cc', cc)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_backend', lambda *_: None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_models', lambda *_: None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_refresh_status_pill', lambda *_: None)
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: False)
    monkeypatch.setattr(conversations, 'DIR', tmp_path / 'conversations')
    monkeypatch.setattr(conversations, '_smart_title', lambda *args: None)
    window = chat_panel.ChatPanel()
    window._cfg = {}
    window._begin_turn()
    window._run_turn('hey ollama record a field observation: ' + DETAILS, [])
    app.processEvents()
    assert len(log.entries()) == 1 and len(window._history) == 2
    assert window._history[-1]['notebook_receipt']['ok']
    conv_id = conversations.save(window._conv_id, window._history, '')
    history = conversations.load(conv_id)['messages']
    result = cc.notebook_command('add it to the field log', history, scope=conv_id)
    assert result.receipt['status'] == 'already_recorded' and len(log.entries()) == 1
    window.close()


def test_identical_observations_in_different_chats_are_distinct(log):
    text = 'record a field observation: ' + DETAILS
    a = nt.command(text, [], scope='chat-one')
    b = nt.command(text, [], scope='chat-two')
    assert a.status == b.status == 'saved' and len(log.entries()) == 2
    assert a.records[0]['id'] != b.records[0]['id']
    assert nt.command(text, [], scope='chat-two').status == 'already_recorded'


def test_existing_records_and_export_chain_remain_compatible(log, tmp_path):
    from cursiv_engine.core import fieldsync
    old = log.add(site='Original', note='preexisting schema-one record')
    before = log.log_file().read_bytes()
    assert 'chat_request_id' not in old
    result = nt.command('record a field observation: ' + DETAILS, [])
    assert result.ok and log.log_file().read_bytes().startswith(before)
    assert log.entries()[0] == old and fieldsync.chain_problems(log.entries()) == []
    paths = log.export(tmp_path / 'export')
    exported = json.loads(paths['json'].read_text(encoding='utf-8'))
    assert exported['entries'][1]['chat_request_id'] == result.records[0]['chat_request_id']
    assert log.verify_export(paths['json'].parent) == []


@pytest.mark.parametrize('instruction', ['delete the field notebook entry 123abc123abc',
                                       'correct the field notebook entry 123abc123abc'])
def test_unsupported_notebook_changes_are_reported_without_model_execution(log, instruction):
    before = log.add(note='original')
    raw = log.log_file().read_bytes()
    result = nt.command(instruction, [])
    assert not result.ok and 'Correct selected' in result.render()
    assert log.log_file().read_bytes() == raw and log.entries()[0] == before


@pytest.mark.skipif(os.name != 'nt', reason='Windows installed/portable read-only file attributes')
def test_real_windows_read_only_log_reports_failure_without_modifying_it(log):
    import stat
    log.add(note='existing')
    path = log.log_file()
    before = path.read_bytes()
    original_mode = path.stat().st_mode
    try:
        path.chmod(stat.S_IREAD)
        result = nt.command('record a field observation: ' + DETAILS, [])
        assert not result.ok and 'PermissionError' in result.render()
        assert path.read_bytes() == before
    finally:
        path.chmod(original_mode)


def test_restart_read_and_retry_use_real_python_filesystem_and_no_network(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path), USERPROFILE=str(tmp_path),
               CURSIV_APP_DATA=str(tmp_path / 'appdata'), PYTHONIOENCODING='utf-8')
    marker = 'notebook-' + hashlib.sha256(str(tmp_path).encode()).hexdigest()
    script = '''
import json, sys
from pathlib import Path
def deny(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto', 'socket.bind'):
        raise AssertionError('Network is forbidden')
sys.addaudithook(deny)
from cursiv_engine.core import notebook_tools as nt, fieldlog as fl
text = 'record a field observation: site: Restart; note: ' + sys.argv[1]
result = nt.command(text, [], observer='Dana')
assert result.ok
path = Path.home() / '.cursiv' / 'fieldlog' / 'observations.jsonl'
rows = [json.loads(line) for line in path.read_bytes().decode('utf-8').splitlines()]
assert len(rows) == 1 and rows[0]['note'] == sys.argv[1] and fl.verify() == []
read = nt.command('read the field notebook entry ' + rows[0]['id'], [], observer='Dana')
assert read.ok and read.records[0]['note'] == sys.argv[1]
print(json.dumps([result.status, rows[0]['id']]))
'''
    args = [sys.executable, '-B', '-c', script, marker]
    first = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
    second = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    a, b = json.loads(first.stdout), json.loads(second.stdout)
    assert a[0] == 'saved' and b == ['already_recorded', a[1]]


def test_portable_notebook_uses_drive_home_and_survives_a_drive_move(tmp_path):
    # Two fresh processes emulate the existing portable activation, including
    # a changed drive/folder, without modifying the real runtime environment.
    import shutil
    drive = tmp_path / 'drive'
    drive.mkdir()
    script = '''
import json, sys
from pathlib import Path
sys.path.insert(0, 'launcher')
import portable
portable.usb_root = lambda: Path(sys.argv[1])
assert portable.activate()
from cursiv_engine.core import notebook_tools as nt, fieldlog as fl
result = nt.command('record a field observation: site: USB; note: portable-marker', [], observer='Dana')
assert result.ok and fl.verify() == []
assert fl.log_file() == Path(sys.argv[1]) / 'Home' / '.cursiv' / 'fieldlog' / 'observations.jsonl'
assert len(fl.entries()) == 1
print(json.dumps([result.status, result.records[0]['id']]))
'''
    env = dict(os.environ, HOME=str(tmp_path / 'host'), USERPROFILE=str(tmp_path / 'host'), PYTHONIOENCODING='utf-8')
    first = subprocess.run([sys.executable, '-B', '-c', script, str(drive)], env=env, capture_output=True, text=True, timeout=30)
    moved = tmp_path / 'changed-drive-letter'
    shutil.copytree(drive, moved)
    second = subprocess.run([sys.executable, '-B', '-c', script, str(moved)], env=env, capture_output=True, text=True, timeout=30)
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    a, b = json.loads(first.stdout), json.loads(second.stdout)
    assert a[0] == 'saved' and b == ['already_recorded', a[1]]

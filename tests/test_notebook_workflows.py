"""Native notebook workflows, quiet continuity and failure-safe demo switching."""
import json

import pytest

from cursiv_engine.core import demo, fieldlog, notebook_tools, native_answers
from cursiv_engine.chat import keys
from test_background_review import pipeline
from test_demo import home
from test_netgate import fresh
from test_chat_feedback import panel, _APP
from test_live_test_followup import final_reply


@pytest.mark.parametrize('question,expected', [
    ('How do I correct an entry?', ['Correct selected', 'reason', 'does not overwrite']),
    ('How do I amend a field observation?', ['Correct selected', 'reason']),
    ('How do I share with a second laptop?', ['field log share', 'field log import', 'team log', 'not live']),
    ('How do I sync observations with another laptop?', ['field log share', 'separate chains']),
    ('How do I import a .cursivsync file?', ['.cursivsync', 'field log import', 'actual file path']),
])
@pytest.mark.parametrize('provider', ['ollama', 'openai'])
def test_requested_howto_workflows_never_use_a_model(pipeline, monkeypatch, question, expected, provider):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('No workflow invention'))
    out = final_reply(pipeline, question, force_provider=provider)
    for text in expected:
        assert text in out
    assert 'built-in notebook guidance' in out


def test_howto_does_not_execute_the_described_workflow(monkeypatch):
    from cursiv_engine.core import fieldsync
    monkeypatch.setattr(fieldsync, 'share', lambda *a: pytest.fail('Help must not share'))
    monkeypatch.setattr(fieldsync, 'import_phone_bundle', lambda *a: pytest.fail('Help must not import'))
    monkeypatch.setattr(fieldlog, 'correct', lambda *a: pytest.fail('Help must not correct'))
    for question in ['How do I share with a second laptop?', 'How do I import a .cursivsync file?',
                     'How do I correct an entry?']:
        assert native_answers.answer(question)


def test_short_save_confirmation_has_independently_verified_record(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    result = notebook_tools.command('log site: North Creek, temp 14.2 C, observation: clear, sample ID: NC-001', [])
    row = json.loads(fieldlog.log_file().read_text(encoding='utf-8'))
    text = result.render()
    assert text.startswith('Logged. Sample NC-001.') and '\n' not in text
    assert row['id'] in text and row['hash'][:12] in text and 'read-back matched' in text
    assert fieldlog.verify() == []


def test_legacy_log_receipt_cannot_claim_readback_without_a_real_write(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    monkeypatch.setattr(fieldlog, 'add', lambda **kw: dict(id='fake', hash='f' * 64))
    out = fieldlog.command('log note: a real observation')
    assert out.startswith('Not confirmed:') and 'Logged.' not in out
    assert not fieldlog.log_file().exists()


def test_legacy_flush_failure_does_not_deny_bytes_already_written(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    def fail(_):
        raise OSError('flush failed after write')
    with monkeypatch.context() as patch:
        patch.setattr(fieldlog.os, 'fsync', fail)
        out = fieldlog.command('log note: FSYNC_MARKER')
    stored = json.loads(fieldlog.log_file().read_text(encoding='utf-8'))
    assert stored['note'] == 'FSYNC_MARKER' and fieldlog.verify() == []
    assert 'A record may exist' in out and 'Nothing was recorded' not in out and 'Logged.' not in out


def test_empty_native_read_is_one_clear_line(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    result = notebook_tools.command('field log', [])
    assert result.ok and result.render() == 'No matching Field Notebook entries.'


def test_site_and_sample_context_only_show_when_relevant(panel, tmp_path, monkeypatch):
    import chat_commands
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    text = 'log site: North Creek; sample ID: NC-001; note: clear'
    panel._begin_turn(text)
    panel._deliver_result(chat_commands.NotebookResult(notebook_tools.command(text, [])), [], text)
    _APP[0].processEvents()
    assert 'Last notebook site: North Creek' in panel._context_indicator.text()
    assert 'Last notebook sample: NC-001' in panel._context_indicator.text()
    panel._begin_turn('What is a sonnet?')
    assert 'North Creek' not in panel._context_indicator.text()
    panel._begin_turn('What should I record next?')
    assert 'North Creek' in panel._context_indicator.text() and 'NC-001' in panel._context_indicator.text()
    assert len(fieldlog.entries()) == 1  # context does not silently create another observation


def test_demo_guides_both_parser_formats_and_restores_original_bytes(home):
    real = fieldlog.add(note='REAL_NOTEBOOK_MARKER')
    original = fieldlog.log_file().read_bytes()
    unrelated = dict(openai_key='TEST-ONLY-OPAQUE-VALUE', offline_mode=True, other=dict(keep=1))
    keys.KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    keys.KEYS_FILE.write_text(json.dumps(unrelated), encoding='utf-8')
    out = demo.command('demo')
    assert 'SAMPLE DATA' in out
    command = next(q for title, q in demo.QUESTIONS if title == 'Comma-format field entry')
    result = notebook_tools.command(command, [])
    assert result.ok and result.records[0]['sample_id'] == 'NC-DEMO-001'
    assert result.records[0]['site'] == 'North Creek' and result.records[0]['note'].startswith('SAMPLE DATA')
    assert demo.command('demo off').startswith('Demo off.')
    assert json.loads(keys.KEYS_FILE.read_text(encoding='utf-8')) == unrelated
    assert fieldlog.log_file().read_bytes() == original and fieldlog.entries()[0]['id'] == real['id']


def test_demo_cleanup_failure_restores_real_view_and_reports_retained_samples(home, monkeypatch):
    fieldlog.add(note='REAL_DATA')
    original = fieldlog.log_file().read_bytes()
    demo.load()
    monkeypatch.setattr(demo.shutil, 'rmtree', lambda *a, **kw: (_ for _ in ()).throw(PermissionError('read-only samples')))
    out = demo.command('demo off')
    assert 'Demo off.' in out and 'cleanup incomplete' in out and 'removed' not in out
    assert not demo.active() and demo.root().exists()
    assert fieldlog.log_file().read_bytes() == original


def test_demo_flag_write_failure_is_not_reported_as_off(home, monkeypatch):
    from cursiv_engine.core import atomic
    demo.load()
    monkeypatch.setattr(atomic, 'write_text', lambda *a, **kw: (_ for _ in ()).throw(PermissionError('read only')))
    out = demo.command('demo off')
    assert 'not confirmed' in out and 'Demo off.' not in out
    assert demo.active() and demo.root().exists()


def test_corrupt_demo_setting_never_overwrites_settings_or_falls_into_real_log(home):
    keys.KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    keys.KEYS_FILE.write_text('{corrupt', encoding='utf-8')
    assert 'not confirmed' in demo.command('demo off')
    with pytest.raises(ValueError):
        fieldlog.log_dir()
    assert keys.KEYS_FILE.read_text(encoding='utf-8') == '{corrupt'


def test_failed_demo_setup_restores_real_notebook_view(home, monkeypatch):
    fieldlog.add(note='REAL_DATA')
    path = fieldlog.log_file()
    original = path.read_bytes()
    monkeypatch.setattr(fieldlog, 'add', lambda **kw: (_ for _ in ()).throw(PermissionError('failed sample write')))
    out = demo.command('demo')
    assert 'not confirmed' in out and 'view was restored' in out
    assert not demo.active() and path.read_bytes() == original


def test_demo_cleanup_cannot_delete_an_unexpected_directory(home, tmp_path, monkeypatch):
    other = tmp_path / 'real-observations'
    other.mkdir()
    marker = other / 'keep.txt'
    marker.write_text('KEEP', encoding='utf-8')
    monkeypatch.setattr(demo, 'root', lambda: other)
    with pytest.raises(OSError, match='unexpected'):
        demo._clear_samples()
    assert marker.read_text(encoding='utf-8') == 'KEEP'


@pytest.mark.parametrize('question,answer', [
    ('we leave at 14:30 and travel 3 hours 45 minutes. what time do we arrive?', '18:15'),
    ("We leave camp at 14:30. The hike takes 3 h 45 min and we'll take a 20 min break. When do we arrive?", '18:35'),
])
def test_field_clock_phrasing_has_a_code_receipt(question, answer):
    from cursiv_engine.core import calc
    worked = calc.work_out(question)
    assert worked and worked.tool == 'clock' and answer in worked.statement
    assert worked.record()['ok'] is True

"""Deterministic end-to-end evidence, relocation and state failure coverage."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import pytest

from cursiv_v215.core import curiosity as journal, curiosity_engine as engine
from cursiv_v215.core import fieldlog, field_recall, paths, presence, state_store, style


@pytest.fixture
def records(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    return fieldlog


def observation(log, value='7.0', **kw):
    fields = dict(site='North', sample_id='ABC-45', note='Water quality observation',
                  measurements=[dict(name='water pH', value=value, unit='pH')])
    fields.update(kw)
    return log.add(**fields)


def test_write_recall_and_chain_unchanged(records):
    entry = observation(records)
    original = records.log_file().read_bytes()
    assert field_recall.query(sample='ABC-45')['records'][0]['id'] == entry['id']
    text = field_recall.command('What measurements did I record for sample ABC-45?')
    assert entry['id'] in text and '7.0' in text
    assert entry['id'] in field_recall.command('Find the observation I made about water quality.')
    assert original == records.log_file().read_bytes() and records.verify() == []


def test_recent_dates_pagination_and_corrections(records):
    entries = [observation(records, str(n)) for n in range(12)]
    today = entries[0]['recorded_local'][:10]
    assert len(field_recall.query(start=today, end=today)['records']) == 10
    assert len(field_recall.query(offset=10)['records']) == 2
    correction = records.correct(entries[0]['id'], 'transcription error', note='Corrected water quality')
    found = field_recall.query(entry=entries[0]['id'])['records']
    assert {r['id'] for r in found} == {entries[0]['id'], correction['id']}
    assert correction['id'] in field_recall.command('What corrections have I made to previous observations?')
    assert len(field_recall.request('Show me the last ten field log entries.')['records']) == 10
    assert 'no session identifier' in field_recall.command('What did I record during my last field session?')
    assert field_recall.query(start='1900-01-01', end='1900-01-02')['total'] == 0


def test_damage_and_read_failure_are_not_empty_success(records, monkeypatch):
    observation(records)
    with records.log_file().open('ab') as stream:
        stream.write(b'{bad')
    reply = field_recall.command('field log recent')
    assert 'Warning:' in reply and 'damaged' in reply
    monkeypatch.setattr(field_recall, 'query', lambda **kw: (_ for _ in ()).throw(PermissionError('denied')))
    assert 'PermissionError: denied' in field_recall.command('What did I record yesterday?')


def test_no_native_tools_or_model_needed(records, monkeypatch):
    import chat_commands as cc
    from cursiv_v215.ui import chat_app
    entry = observation(records)
    monkeypatch.setattr(chat_app, '_chat_stream', lambda *a: pytest.fail('model invoked'))
    response = ''.join(chat_app.chat('Find every observation mentioning soil moisture.', [], '', None))
    assert 'No matching' in response
    result = cc.handle_command('Find the observation I made about water quality.', cc._default_cfg(), [])
    assert entry['id'] in result.text


def test_scan_budget_and_link_protection(records, monkeypatch, tmp_path):
    observation(records)
    monkeypatch.setattr(field_recall, 'MAX_BYTES', 1)
    assert 'scan budget' in field_recall.command('field log recent')
    monkeypatch.setattr(field_recall, 'MAX_BYTES', 64 * 1024 * 1024)
    if os.name == 'nt':
        linked = tmp_path / 'linked'
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(linked), str(records.log_dir())], check=True, capture_output=True)
        monkeypatch.setattr(fieldlog, 'log_dir', lambda: linked)
        assert 'PermissionError' in field_recall.command('field log recent')


def test_portable_migration_backup_conflict_and_references(tmp_path, monkeypatch):
    import portable
    root = tmp_path / 'drive'
    source = root / 'Cursiv' / '_internal' / '.cursiv'
    source.mkdir(parents=True)
    (source / 'memory_facts.jsonl').write_text('legacy')
    data = root / 'Home' / '.cursiv'
    data.mkdir(parents=True)
    portable.migrate_data(root, data)
    assert (data / 'memory_facts.jsonl').read_text() == 'legacy'
    assert list((data / 'backups').rglob('SHA256.json'))
    monkeypatch.setenv('CURSIV_PORTABLE', '1')
    monkeypatch.setenv('CURSIV_USB_ROOT', str(root))
    folder = root / 'Workspace' / 'research'
    folder.mkdir(parents=True)
    ref = paths.save_reference(folder)
    moved = tmp_path / 'other-letter'
    shutil.move(root, moved)
    monkeypatch.setenv('CURSIV_USB_ROOT', str(moved))
    assert paths.resolve_reference(ref) == moved / 'Workspace' / 'research'
    with pytest.raises(ValueError):
        paths.resolve_reference('portable://../host')
    conflict = tmp_path / 'conflict'
    old = conflict / 'Cursiv' / '.cursiv'
    old.mkdir(parents=True)
    (old / 'config.json').write_text('one')
    destination = conflict / 'Home' / '.cursiv'
    destination.mkdir(parents=True)
    (destination / 'config.json').write_text('two')
    with pytest.raises(OSError, match='conflict'):
        portable.migrate_data(conflict, destination)
    assert (destination / 'config.json').read_text() == 'two'
    assert not (destination / 'portable-layout-v1.json').exists()


def test_usb_refresh_preserves_private_and_workspace(tmp_path):
    import usb_maker
    source = tmp_path / 'desktop.txt'
    source.write_text('older desktop data')
    drive = tmp_path / 'drive'
    private = drive / 'Home' / '.cursiv' / 'memory.json'
    private.parent.mkdir(parents=True)
    private.write_text('new drive data')
    plan = usb_maker.update_plan(drive, [(source, Path('Home/.cursiv/memory.json'))])
    assert plan == [] and private.read_text() == 'new drive data'
    with pytest.raises(ValueError):
        usb_maker.update_plan(drive, [(source, Path('../host'))])


def test_portable_activation_failure_never_returns_nonportable(tmp_path, monkeypatch):
    import portable
    monkeypatch.setattr(portable, 'usb_root', lambda: tmp_path)
    monkeypatch.setattr(portable, 'migrate_data', lambda *a: (_ for _ in ()).throw(OSError('read only')))
    with pytest.raises(OSError, match='read only'):
        portable.activate()


def test_verified_store_preserves_before_replace_failure(tmp_path, monkeypatch):
    p = tmp_path / 'state.json'
    state_store.save(p, {'original': 1})
    before = p.read_bytes()
    monkeypatch.setattr(state_store.os, 'replace', lambda *a: (_ for _ in ()).throw(OSError('disk removed')))
    with pytest.raises(OSError, match='disk removed'):
        state_store.save(p, {'new': 2})
    assert p.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


def test_corrupt_style_never_resets_preferences(monkeypatch):
    style.DIR.mkdir(parents=True)
    p = style._path('dana')
    p.write_text('{bad')
    with pytest.raises(ValueError):
        style.set_tone('dana', 'brief')
    assert p.read_text() == '{bad'
    style.add_rule('other', 'Keep explanations brief', 'manual')
    assert 'accuracy, permissions and safety' in style.prompt_addendum('other')


def test_curiosity_detection_dedup_budget_and_ranking(records):
    for n in range(3):
        observation(records, str(6 + n), sample_id=f'S-{n}')
    original = records.log_file().read_bytes()
    report = engine.evaluate('dana', 'research')
    assert len(report['added']) == 2
    data = journal.load('dana')
    assert any(r['missing_variables'] for r in data['records'])
    assert all(r['evidence'] and r['classification'] == 'Inference' for r in data['records'])
    assert report['inference_calls'] == 0
    assert engine.evaluate('dana', 'research')['added'] == []
    assert records.log_file().read_bytes() == original
    journal.configure('dana', max_active=2)
    assert journal.add('dana', 'research', {'question': 'Another testable question?'}, [], manual=True) is None
    scores = [r['score'] for r in data['records']]
    assert max(scores) > min(scores)


def test_status_dismissal_and_resolution_require_real_evidence(records):
    row = observation(records)
    r = journal.add('dana', 'p', {'question': 'Why does the sample vary?'}, [], manual=True)
    assert 'requires supporting evidence' in engine.command('curiosity resolve ' + r['id'], 'dana', 'p')
    assert 'must reference' in engine.command('curiosity resolve ' + r['id'] + ' :: field:invented', 'dana', 'p')
    assert 'saved and verified' in engine.command('curiosity resolve ' + r['id'] + ' :: field:' + row['id'], 'dana', 'p')
    saved = journal.load('dana')['records'][0]
    assert saved['status'] == 'Resolved' and saved['resolution'][0]['id'] == row['id']
    journal.transition('dana', r['id'], 'Dismissed')
    assert journal.add('dana', 'p', {'question': r['question']}, [], manual=True) is None
    assert len(journal.load('dana')['records'][0]['history']) == 3


def test_unsupported_reference_rejected_and_manual_unknown():
    with pytest.raises(ValueError, match='Unsupported'):
        journal.add('dana', 'p', {'question': 'What is missing here?', 'refs': [{'source': 'field', 'id': 'fake'}]}, [])
    r = journal.add('dana', 'p', {'question': 'What might be missing here?'}, [], manual=True)
    assert r['classification'] == 'Unknown'


def test_failed_journal_write_never_claims_success(monkeypatch):
    def fail(*args):
        raise OSError('read-only storage')
    monkeypatch.setattr(state_store.os, 'replace', fail)
    answer = engine.command('curiosity add What evidence is still missing?', 'dana')
    assert 'operation failed' in answer and 'No persistence success' in answer
    assert journal.load('dana')['records'] == []


def test_resolution_can_target_an_older_record(records):
    original = observation(records)
    for i in range(52):
        observation(records, str(i))
    record = journal.add('dana', 'p', {'question': 'Was the first observation checked?'}, [], manual=True)
    assert 'saved and verified' in engine.command('curiosity resolve ' + record['id'] + ' :: field:' + original['id'], 'dana', 'p')


def test_invalid_journal_is_preserved():
    file = journal.path('dana')
    file.parent.mkdir(parents=True)
    broken = {'version': 1, 'settings': {}, 'records': [{'id': 'CUR-x', 'status': 'Open', 'history': []}]}
    file.write_text(json.dumps(broken))
    before = file.read_bytes()
    assert 'operation failed' in engine.command('curiosity', 'dana')
    assert file.read_bytes() == before


def test_disabled_pending_job_cannot_write(records, monkeypatch):
    from cursiv_v215.memory import semantic
    monkeypatch.setattr(semantic, 'learning_enabled', lambda: True)
    pending = []
    class Deferred:
        def __init__(self, target, **kw): self.target = target
        def start(self): pending.append(self.target)
    monkeypatch.setattr(engine.threading, 'Thread', Deferred)
    journal.configure('dana', automatic=True, frequency=1)
    assert engine.notify('dana', text='I assume the sample never changes')
    journal.configure('dana', automatic=False)
    pending.pop()()
    assert journal.load('dana')['records'] == []


def test_reopen_enforces_active_budget():
    journal.configure('dana', max_active=1)
    first = journal.add('dana', 'p', {'question': 'What evidence was recorded?'}, [], manual=True)
    journal.transition('dana', first['id'], 'Dismissed')
    journal.add('dana', 'p', {'question': 'Which conditions should be measured?'}, [], manual=True)
    with pytest.raises(ValueError, match='budget'):
        journal.transition('dana', first['id'], 'Open')


def test_potential_conflict_not_incomparable_measurements(records):
    from copy import deepcopy
    first = observation(records, '7')
    second = deepcopy(first)
    second.update(id='other')
    second['measurements'][0]['value'] = '8'
    out = engine.candidates([first, second], [], '')
    assert any('reconciled' in c['question'] for c in out)
    assert all('potential' in c['why'] for c in out if 'reconciled' in c['question'])
    second['recorded_utc'] = '2000-01-01T00:00:00Z'
    assert not any('reconciled' in c['question'] for c in engine.candidates([first, second], [], ''))
    second['corrects'] = first['id']
    assert engine.candidates([first, second], [], '') == []


def test_relevant_new_evidence_reopens_review_not_resolution(records):
    observation(records, '7')
    observation(records, '8')
    engine.evaluate('dana', 'p')
    observation(records, '9', note='water pH collection temperature 18 C')
    engine.evaluate('dana', 'p')
    r = journal.load('dana')['records'][0]
    assert r['status'] == 'Proposed'
    assert any('Related new evidence' in h.get('note', '') for h in r['history'])


def test_automatic_controls_and_disable_memory(records, monkeypatch):
    from cursiv_v215.memory import semantic
    assert engine.notify('dana', text='I assume this is stable') is False
    journal.configure('dana', automatic=True, frequency=1)
    monkeypatch.setattr(semantic, 'learning_enabled', lambda: False)
    assert engine.notify('dana', text='I assume this is stable') is False
    monkeypatch.setattr(semantic, 'learning_enabled', lambda: True)
    assert engine.notify('dana', text='Do not remember this assumption') is False
    # Run the deferred worker synchronously, so no test thread outlives redirection.
    class Immediate:
        def __init__(self, target, **kw): self.target = target
        def start(self): self.target()
    monkeypatch.setattr(engine.threading, 'Thread', Immediate)
    assert engine.notify('dana', text='I assume this is stable') is True
    assert len(journal.load('dana')['records']) == 1


def test_offline_no_network_and_persistent_suppression(records, monkeypatch):
    import socket
    from cursiv_v215.memory import semantic
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **kw: pytest.fail('network'))
    monkeypatch.setattr(semantic, 'learning_enabled', lambda: True)
    journal.configure('dana', automatic=True, suggestions=True)
    r = journal.add('dana', 'p', {'question': 'How can this be measured?'}, [], manual=True)
    assert r['id'] in engine.suggestion('dana', 'p')
    assert engine.suggestion('dana', 'p') == ''
    engine.evaluate('dana', 'p', 'I assume this is known')
    assert engine.suggestion('dana', 'p') == ''


def test_sensitive_data_and_false_contradictions(records):
    observation(records, '7', note='password is do-not-copy-this')
    rows, ev = engine.context('dana')
    assert rows == [] and ev == []
    safe = observation(records, '8', sample_id='other', measurements=[dict(name='water pH', value='8', unit='different')])
    assert not engine.candidates([safe], [], '')


def test_presence_style_control_and_live_state(monkeypatch):
    presence.configure('dana', adapt_style=False)
    assert not presence.settings('dana')['adapt_style']
    assert style.learn_correction('dana', 'Always keep it brief', '', lambda *a: pytest.fail('inference')) is None
    snapshot = presence.snapshot()
    assert snapshot['authorized_workspace'] is None and snapshot['observed_at']
    assert 'No observation while closed' in snapshot['limitations']


def test_dialog_uses_journal_and_controls(records):
    from PyQt6.QtWidgets import QApplication
    from curiosity_dialog import CuriosityDialog
    app = QApplication.instance() or QApplication([])
    dlg = CuriosityDialog()
    dlg.question.setText('What evidence should we collect next?')
    dlg.action('add')
    assert dlg.items.count() == 1
    dlg.action('dismiss')
    assert 'Dismissed' in dlg.items.item(0).text()
    dlg.close()


def test_fresh_process_and_relocation(tmp_path):
    """Two fresh interpreters and moved home; no reliance on conversation context."""
    home = tmp_path / 'first-drive' / 'Home'
    home.mkdir(parents=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), CURSIV_APP_DATA=str(home / '.cursiv'),
               CURSIV_PORTABLE='1', CURSIV_USB_ROOT=str(home.parent))
    create = """from cursiv_v215.core import fieldlog, curiosity, netgate, documents, paths
from cursiv_v215.memory import semantic
from cursiv_v215.coding import brain
netgate.set_offline(True); netgate.install()
folder=paths.portable_root()/'Workspace'/'research'; folder.mkdir(parents=True)
file=folder/'protocol.txt'; file.write_text('Water protocol measurements require calibration.', encoding='utf-8')
documents.add(file)
brain.set_project(str(folder),'dana')
semantic.add_fact('Dana prefers concise field reports',person='dana',source='manual')
e=fieldlog.add(note='water quality offline', sample_id='ABC-45')
curiosity.add('dana','portable://Workspace',{'question':'What conditions were recorded?'},[],manual=True)
print(e['id'])
"""
    ident = subprocess.check_output([sys.executable, '-B', '-c', create], env=env, text=True).strip()
    moved = tmp_path / 'second-drive'
    shutil.move(home.parent, moved)
    env.update(HOME=str(moved / 'Home'), USERPROFILE=str(moved / 'Home'), CURSIV_PORTABLE='1',
               CURSIV_USB_ROOT=str(moved), CURSIV_APP_DATA=str(moved / 'Home' / '.cursiv'))
    read = """from cursiv_v215.core import field_recall, curiosity, documents, paths, netgate, file_access
from cursiv_v215.memory import semantic
from cursiv_v215.coding import brain
netgate.install(); assert netgate.is_offline()
assert curiosity.load('dana')['records'][0]['question']=='What conditions were recorded?'
assert any('concise field reports' in f['text'] for f in semantic.list_facts('dana'))
folder=paths.portable_root()/'Workspace'/'research'
assert brain.project('dana')==str(folder)
assert documents.search('water protocol measurements')
assert documents.library()[0]['path'].startswith('portable://')
assert 'require calibration' in file_access.execute('read_file',{'path':'protocol.txt'},folder)
assert 'verified' in file_access.execute('append_file',{'path':'protocol.txt','content':' New observation.'},folder,confirmed=True)
print(field_recall.command('What measurements did I record for sample ABC-45?'))
"""
    assert ident in subprocess.check_output([sys.executable, '-B', '-c', read], env=env, text=True)


def test_reproducible_curiosity_benchmark(records, monkeypatch, tmp_path):
    cases = json.loads((Path(__file__).parent / 'data' / 'curiosity_cases.json').read_text())
    report = []
    for i, case in enumerate(cases):
        folder = tmp_path / str(i) / 'fieldlog'
        monkeypatch.setattr(fieldlog, 'log_dir', lambda f=folder: f)
        for n, (value, unit) in enumerate(zip(case['values'], case['units'])):
            observation(records, value, sample_id=f'S-{n}', note=case['notes'],
                        measurements=[dict(name='water pH', value=value, unit=unit)])
        before = fieldlog.log_file().read_bytes() if fieldlog.log_file().exists() else b''
        started = time.perf_counter()
        rows, evidence = engine.context('dana', case.get('text', ''))
        found = engine.candidates(rows, evidence, case.get('text', ''))
        elapsed = time.perf_counter() - started
        questions = ' '.join(c['question'] for c in found).lower()
        assert all(term in questions for term in case['expected'])
        assert len(found) == len(case['expected'])
        assert bool(found) == bool(case['expected'])
        allowed = {(e['source'], e['id']) for e in evidence}
        assert all((r['source'], r['id']) in allowed for c in found for r in c['refs'])
        assert len({journal.normalize(c['question']) for c in found}) == len(found)
        assert before == (fieldlog.log_file().read_bytes() if fieldlog.log_file().exists() else b'')
        full = engine.evaluate('dana', case['name'], case.get('text', ''))
        assert len(full['added']) == len(found)
        assert len([r for r in journal.load('dana')['records'] if r['project'] == case['name']]) == len(found)
        report.append(dict(scenario=case['name'], baseline_disabled_questions=0, enabled_questions=len(found),
                           expected_gaps=len(case['expected']), missed_gaps=0, unsupported_questions=0,
                           duplicate_questions=0, reference_accuracy=1.0 if found else None,
                           retrieval_detection_seconds=elapsed, evaluation_persistence_seconds=full['seconds'],
                           persistence_verified=True, additional_model_calls=0))
    (Path.cwd().parent / 'curiosity-benchmark.json').write_text(json.dumps(report, indent=2))

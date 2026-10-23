"""Verified natural-language memory, with isolated actual persistence and no cloud."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from cursiv_engine.memory import intents as mi, semantic as sem


@pytest.fixture
def memory(monkeypatch):
    sem.set_person('dana')
    monkeypatch.setattr(sem, 'embed', lambda *_: pytest.fail('Explicit memory must not call embeddings'))
    mi._pending.clear()
    return sem


def run(text, history=None, **kwargs):
    return mi.command(text, history or [], person='dana', scope=kwargs.pop('scope', 'chat-one'), **kwargs)


def user(text):
    return dict(role='user', content=text)


def model(text):
    return dict(role='assistant', content=text)


@pytest.mark.parametrize('text,expected', [
    ('Remember permanently: HAWK-217', 'HAWK-217'),
    ('Please remember permanently that my project code is HAWK-217.', 'my project code is HAWK-217.'),
    ('Remember manually: HAWK-217', 'HAWK-217'),
    ("Don't forget my project code is HAWK-217.", 'my project code is HAWK-217.'),
    ('Keep in mind that my project code is HAWK-217.', 'my project code is HAWK-217.'),
    ('Save this record: Project code: HAWK-217; status: preliminary', 'Project code: HAWK-217; status: preliminary'),
    ('Store this information in persistent memory: HAWK-217', 'HAWK-217'),
])
def test_instruction_modifiers_are_not_saved_as_content(memory, text, expected):
    result = run(text)
    assert result.ok and result.outcomes[0].operation == mi.SAVE
    actual = [json.loads(line) for line in memory.FACTS_FILE.read_text(encoding='utf-8').splitlines()]
    assert actual[0]['text'] == expected and actual[0]['source'] == 'manual' and actual[0]['origin'] == 'user_said'
    assert actual[0]['id'] == result.outcomes[0].records[0]['id']
    assert actual[0]['id'] in result.render()


@pytest.mark.parametrize('text', ['Please remember this', 'Remember what I just told you.',
                                 "Don't forget what I told you", 'Keep this information for next time.'])
def test_contextual_saves_only_use_the_user_detail(memory, text):
    history = [user('My project code is HAWK-217.'), model('Your code is FALCON-999 and I saved it to memory.')]
    result = run(text, history)
    assert result.ok and memory.list_facts('dana')[0]['text'] == 'My project code is HAWK-217.'


def test_last_decision_and_measurement_are_selected_from_user_context(memory):
    result = run('Save that last decision.', [user('We decided to use the north transect.'), model('Use the south transect.')])
    assert result.ok and 'north transect' in result.render()
    result = run("Don't forget the measurement we discussed.", [user('The measured temperature was 18.60 C.'), model('It was 99 C.')])
    assert result.ok and '18.60' in result.render() and '99 C' not in result.render()


def test_ambiguous_reference_clarifies_without_saving_and_is_scoped(memory):
    history = [user('My code is HAWK-217. My site is North Ridge.'), model('Saved both!')]
    result = run('Please remember this', history)
    assert not result.ok and 'Which detail' in result.render() and memory.list_facts('dana') == []
    assert mi.command('2', [], person='other', scope='chat-one') is None
    assert run('2', scope='chat-two') is None
    chosen = run('2')
    assert chosen.ok and chosen.outcomes[0].records[0]['text'] == 'My site is North Ridge.'


def test_assistant_claims_and_arbitrary_acknowledgements_are_not_context_evidence(memory):
    result = run('Remember what I just told you.', [user('How does memory work?'), model('Your code is HAWK-217.'), user('Okay')])
    assert not result.ok and memory.list_facts('dana') == []


@pytest.mark.parametrize('text', ['How does memory work?', 'Imagine someone saying remember HAWK-217.',
                                 'Why did you save the word permanently?',
                                 'What would happen if I asked you to remember something?',
                                 '"Remember HAWK-217"', 'Look up the weather'])
def test_discussion_quoted_commands_and_unrelated_lookups_do_not_save(memory, text):
    assert run(text, classifier=lambda *_: pytest.fail('No classifier for ordinary discussion')) is None
    assert memory.list_facts('dana') == []


def test_compound_disables_automatic_memory_and_manually_saves(memory):
    result = run('Disable automatic memory, then remember manually: HAWK-217')
    assert result.ok and [o.operation for o in result.outcomes] == [mi.OFF, mi.SAVE]
    assert not memory.learning_enabled() and memory._settings()['learn'] is False
    assert memory.find('HAWK-217', 'dana')
    assert memory.learn_from_exchange('I prefer Rust.', 'Okay', lambda _: pytest.fail('No automatic extraction'), person='dana') == []
    assert run('enable automatic memory').ok and memory.learning_enabled()


def test_compound_reports_independent_failure_and_success(memory, monkeypatch):
    monkeypatch.setattr(memory, 'set_learning', lambda *_: (_ for _ in ()).throw(OSError('settings write failed')))
    result = run('Disable automatic memory, then remember manually: HAWK-217')
    assert not result.ok and not result.outcomes[0].ok and result.outcomes[1].ok
    assert memory.find('HAWK-217', 'dana')


def test_setting_default_is_not_proof_of_a_setting_write(memory, monkeypatch):
    monkeypatch.setattr(memory, 'set_learning', lambda *_: None)
    result = run('enable automatic memory')
    assert not result.ok and not memory.SETTINGS_FILE.exists()


def test_manual_correction_retains_history_and_removes_active_contradiction(memory):
    original = run('remember my project code is HAWK-217').outcomes[0].records[0]
    original_text = memory.FACTS_FILE.read_bytes()
    result = run('Actually, my project code is FALCON-218, not HAWK-217.')
    assert result.ok and len(memory.list_facts('dana')) == 1
    active = memory.list_facts('dana')[0]
    assert active['text'] == 'my project code is FALCON-218' and active['corrects'] == original['id']
    history = memory.list_facts('dana', include_superseded=True)
    old = next(f for f in history if f['id'] == original['id'])
    assert old['status'] == 'superseded' and old['text'] == original['text']
    assert old['superseded_by'] == active['id'] and old['origin'] == 'user_said'
    backup = memory.FACTS_FILE.parent / 'backups' / 'autonomous-memory-v1' / memory.FACTS_FILE.name
    assert backup.read_bytes() == original_text
    assert 'FALCON-218' in run('recall my project code').render()
    assert 'HAWK-217' not in run('recall my project code').render()


def test_forget_verifies_removal_and_correction_lineage(memory):
    run('remember my project code is HAWK-217')
    run('Actually, my project code is FALCON-218, not HAWK-217.')
    result = run('forget FALCON-218')
    assert result.ok and result.render().startswith('Forgotten')
    assert memory.list_facts('dana', include_superseded=True) == []


def test_update_and_forget_choose_actual_ids_when_ambiguous(memory):
    run('remember my project code is HAWK-217')
    run('remember my project site is North Ridge')
    result = run('forget my project')
    assert not result.ok and 'Choose one saved memory' in result.render()
    assert len(memory.list_facts('dana')) == 2
    assert run('1').ok and len(memory.list_facts('dana')) == 1


def test_save_retries_do_not_duplicate_or_upgrade_provenance(memory):
    first = run('remember HAWK-217')
    before = memory.FACTS_FILE.read_bytes()
    second = run('remember permanently: HAWK-217')
    assert second.ok and second.outcomes[0].status == 'already_saved'
    assert second.outcomes[0].records[0]['id'] == first.outcomes[0].records[0]['id']
    assert memory.FACTS_FILE.read_bytes() == before


@pytest.mark.parametrize('text', ['remember a', 'remember abc'])
def test_short_unsaved_text_never_claims_already_known(memory, text):
    result = run(text)
    assert not result.ok and 'Already saved' not in result.render() and memory.list_facts('dana') == []


def test_failed_write_or_backend_receipt_without_persistence_is_not_success(memory, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(memory._atomic, 'write_text', lambda *_a, **_k: (_ for _ in ()).throw(OSError('disk full')))
        result = run('remember HAWK-217')
        assert not result.ok and 'disk full' in result.render()
    with monkeypatch.context() as patch:
        patch.setattr(memory, 'add_fact', lambda *_a, **_k: dict(id='fake-id', text='HAWK-217'))
        assert not run('remember HAWK-217').ok
    with monkeypatch.context() as patch:
        patch.setattr(memory, 'add_fact', lambda *_a, **_k: None)
        assert not run('remember HAWK-217').ok
    assert memory.list_facts('dana') == []


def test_failed_correction_preserves_original(memory, monkeypatch):
    run('remember my project code is HAWK-217')
    before = memory.FACTS_FILE.read_bytes()
    monkeypatch.setattr(memory._atomic, 'write_text', lambda *_a, **_k: (_ for _ in ()).throw(PermissionError('read-only')))
    result = run('Actually, my project code is FALCON-218, not HAWK-217.')
    assert not result.ok and memory.FACTS_FILE.read_bytes() == before


def test_ambiguous_local_classifier_may_only_select_real_user_text(memory):
    text = 'Make a mental note that HAWK-217 is my project code.'
    calls = []
    def classify(current, context):
        calls.append(current)
        return dict(operation=mi.SAVE, content='HAWK-217 is my project code.', source=text)
    result = run(text, classifier=classify)
    assert result.ok and len(calls) == 1 and memory.list_facts('dana')[0]['text'] == 'HAWK-217 is my project code.'


@pytest.mark.parametrize('proposal', [
    dict(operation=mi.SAVE, content='invented fact', source='invented fact'),
    dict(operation=mi.SAVE, content='permanently', source='Make a mental note permanently'),
    dict(operation=mi.FORGET, content='HAWK-217', source='Make a mental note of HAWK-217'),
    dict(operation=mi.OFF), dict(operation='file_create', path='test.txt'),
])
def test_classifier_cannot_invent_data_or_authorize_other_operations(memory, proposal):
    assert not run('Make a mental note of HAWK-217', classifier=lambda *_: proposal).ok
    assert memory.list_facts('dana') == []


def test_local_classifier_is_bounded_and_has_no_cloud_fallback(monkeypatch):
    from cursiv_engine.core import local_intent
    release = threading.Event()
    def stuck(*args, **kwargs):
        release.wait(2)
        return dict(operation='NONE')
    monkeypatch.setattr(local_intent, '_classify', stuck)
    started = time.monotonic()
    try:
        assert local_intent.classify('Make a mental note', [], budget=0.05) is None
        assert time.monotonic() - started < 0.5
        assert local_intent.classify('another', [], budget=0.05) is None
    finally:
        release.set()


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'claude', 'grok'])
def test_offline_memory_routes_bypass_models_files_and_verification(memory, monkeypatch, provider):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import file_access, netgate
    def forbidden(*args, **kwargs):
        pytest.fail('Explicit memory must not reach files, models or post-generation verification')
    monkeypatch.setattr(ca, '_chat_inner', forbidden)
    monkeypatch.setattr(file_access, 'command', forbidden)
    monkeypatch.setattr(netgate, 'allowed', lambda: False)
    out = ''.join(ca.chat('remember permanently: HAWK-217', [], '', None, force_provider=provider))
    assert 'HAWK-217' in out and memory.find('HAWK-217', 'dana')


def test_memory_ui_history_and_scoped_clarification_survive_command_delivery(memory, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    import chat_panel, chat_commands as cc, conversations
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(chat_panel, 'cc', cc)
    for name in ('_load_backend', '_load_models', '_refresh_status_pill'):
        monkeypatch.setattr(chat_panel.ChatPanel, name, lambda *_: None)
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: False)
    monkeypatch.setattr(conversations, '_smart_title', lambda *_: None)
    panel = chat_panel.ChatPanel()
    panel._cfg = {}
    panel._begin_turn()
    panel._run_turn('hey ollama remember permanently: HAWK-217', [])
    app.processEvents()
    assert panel._history[-1]['memory_receipt']['ok'] and len(panel._history) == 2
    assert panel._conv_id and memory.list_facts('dana')
    conversations.wait_for_save()
    panel.close()
    panel.deleteLater()
    app.processEvents()


def test_fresh_process_retrieves_actual_saved_memory_in_a_new_conversation(tmp_path):
    env = dict(os.environ, CURSIV_APP_DATA=str(tmp_path / 'app'), HOME=str(tmp_path / 'home'), USERPROFILE=str(tmp_path / 'home'))
    write = '''
from cursiv_engine.memory import semantic
semantic.set_person('dana')
result = semantic.memory_command('Remember permanently: HAWK-217')
assert 'Memory ID:' in result
'''
    read = '''
import json, os
from pathlib import Path
from cursiv_engine.memory import semantic
semantic.set_person('dana')
raw = Path(os.environ['CURSIV_APP_DATA']) / 'memory_facts.jsonl'
rows = [json.loads(line) for line in raw.read_text(encoding='utf-8').splitlines()]
assert rows[0]['text'] == 'HAWK-217'
assert 'HAWK-217' in semantic.memory_command('recall HAWK-217')
'''
    for script in (write, read):
        result = subprocess.run([sys.executable, '-B', '-c', script], env=env, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr


def test_portable_memory_survives_drive_relocation_and_fresh_process(tmp_path):
    drive = tmp_path / 'usb-before'
    drive.mkdir()
    env = dict(os.environ, CURSIV_PORTABLE='1', CURSIV_USB_ROOT=str(drive),
               CURSIV_APP_DATA=str(drive / 'Home' / '.cursiv'), HOME=str(drive / 'Home'), USERPROFILE=str(drive / 'Home'))
    write = "from cursiv_engine.memory import intents; assert intents.command('remember permanently: USB-217', [], person='dana').ok"
    result = subprocess.run([sys.executable, '-B', '-c', write], env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    before = (drive / 'Home' / '.cursiv' / 'memory_facts.jsonl').read_bytes()
    moved = tmp_path / 'usb-after'
    shutil.copytree(drive, moved)
    env.update(CURSIV_USB_ROOT=str(moved), CURSIV_APP_DATA=str(moved / 'Home' / '.cursiv'),
               HOME=str(moved / 'Home'), USERPROFILE=str(moved / 'Home'))
    read = """
from cursiv_engine.memory import intents
result = intents.command('recall USB-217', [], person='dana')
assert result.ok and 'USB-217' in result.render()
assert intents.command('remember permanently: USB-217', [], person='dana').outcomes[0].status == 'already_saved'
"""
    result = subprocess.run([sys.executable, '-B', '-c', read], env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert (moved / 'Home' / '.cursiv' / 'memory_facts.jsonl').read_bytes() == before


def test_local_classifier_validates_schema_and_only_sends_to_loopback(monkeypatch):
    from cursiv_engine.core import local_intent as li
    monkeypatch.setattr(li, '_loaded', ('', 0))
    monkeypatch.setenv('OLLAMA_HOST', 'https://remote.example')
    def forbidden(*args, **kwargs):
        pytest.fail('Remote classifier endpoint must not be called')
    monkeypatch.setattr(li, '_open_local', forbidden)
    assert li._classify('Make a mental note', []) is None
    monkeypatch.setenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
    text = 'Make a mental note: USB-217'
    proposals = [dict(operation=mi.SAVE, message=0, start=text.index('USB'), end=len(text))]
    calls = []
    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, *_): return json.dumps(self.payload).encode()
    def request(req, **kwargs):
        if isinstance(req, str):
            assert req == 'http://127.0.0.1:11434/api/ps'
            return Response(dict(models=[dict(name='already-loaded-model')]))
        calls.append(json.loads(req.data))
        return Response(dict(message=dict(content=json.dumps(proposals[0]))))
    monkeypatch.setattr(li, '_open_local', request)
    assert li._classify(text, []) == dict(operation=mi.SAVE, content='USB-217', source=text)
    assert calls[0]['format']['additionalProperties'] is False
    for proposal in (dict(operation=mi.SAVE, message=True, start=0, end=1),
                     dict(operation='file_create', message=0, start=0, end=1),
                     dict(operation=mi.SAVE, message=0, start=0, end=9999),
                     dict(operation=mi.SAVE, message=0, start=0, end=1, content='invented')):
        proposals[0] = proposal
        assert li._classify(text, []) is None


def test_local_classifier_disables_proxies_and_redirects(monkeypatch):
    from cursiv_engine.core import local_intent as li
    handlers = []
    class Opener:
        def open(self, request, *, timeout):
            assert request == 'http://127.0.0.1:11434/api/ps' and timeout == 0.2
            return 'stub-response'
    monkeypatch.setattr(li.urllib.request, 'build_opener', lambda *args: handlers.extend(args) or Opener())
    assert li._open_local('http://127.0.0.1:11434/api/ps', timeout=0.2) == 'stub-response'
    assert handlers[0].proxies == {}
    assert handlers[1].redirect_request(None, None, 302, '', {}, 'https://remote.example') is None


def test_new_request_discards_pending_choice_from_another_intent(memory):
    assert run('remember this', [user('My code is HAWK-217. My site is North Ridge.')]).clarification
    assert run('remember a new explicit record').ok
    assert run('2') is None
    assert [f['text'] for f in memory.list_facts('dana')] == ['a new explicit record']

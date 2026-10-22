"""Deterministic formation and storage receipts, with no live models or user data."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from cursiv_v215.memory import semantic as sem, formation


@pytest.fixture
def memory(monkeypatch):
    monkeypatch.setattr(sem, 'embed', lambda _: None)
    monkeypatch.setattr(sem, '_strand_items', lambda: [])
    sem.set_person('bob')
    return sem


def learn(text, **kwargs):
    return sem.learn_from_exchange(text, 'An ordinary response.', lambda _: '[]', person='bob', **kwargs)


def test_ordinary_project_and_preference_are_selected_without_a_model(memory):
    def no_model(_):
        pytest.fail('Direct statements need no model')
    saved = sem.learn_from_exchange("I'm building Cursiv, an offline-first AI application. I prefer Rust over Python.",
                                   'Okay', no_model, person='bob', event_id='message-1')
    assert len(saved) == 2
    facts = sem.list_facts('bob')
    assert all(f['source'] == 'learned' and f['origin'] == 'inferred' for f in facts)
    assert all(f['provenance']['message_id'] == 'message-1' for f in facts)
    assert {f['category'] for f in facts} == {'project', 'preference'}


def test_legacy_repair_does_not_reinterpret_new_validated_records(memory):
    memory.learn_from_exchange('I prefer Rust.', 'Okay', lambda _: '', person='cursiv')
    assert memory.list_facts('cursiv')[0]['text'] == 'Cursiv prefers Rust'


@pytest.mark.parametrize('text', ['Hello there', 'What is 12 * 19?', 'It is raining today.',
                                 'I might prefer Rust someday.', 'I prefer tea?'])
def test_trivial_speculative_and_temporary_messages_are_not_saved(memory, text):
    assert learn(text) == []
    assert memory.list_facts() == []


@pytest.mark.parametrize('text', ["Don't remember this: I prefer Rust", 'I prefer passwords stored as hunter2',
                                 'I prefer Rust. My API key is sk-fakefakefake123',
                                 'My medical diagnosis is private', 'Off the record, I prefer Rust'])
def test_privacy_exclusions_apply_before_extraction(memory, text):
    assert learn(text) == []


def test_repetition_and_reprocessing_do_not_duplicate(memory):
    assert learn('I prefer Rust over Python.', event_id='same')
    assert learn('I prefer Rust over Python.', event_id='same') == []
    assert learn('I prefer Rust over Python.', event_id='other') == []
    assert len(memory.list_facts()) == 1


def test_explicit_correction_supersedes_automatic_preference(memory):
    learn('I prefer Python.')
    learn('Actually, I prefer Rust.')
    assert [f['text'] for f in memory.list_facts()] == ['Bob prefers Rust']
    rows = memory.list_facts(include_superseded=True)
    assert len(rows) == 2 and rows[0]['status'] == 'superseded'
    assert 'Python' not in memory.build_context('Bob prefers Python or Rust')


def test_keyword_retrieval_understands_a_fresh_personal_project_question(memory):
    learn("I'm building Cursiv for field research.")
    assert 'Cursiv' in memory.build_context('What is my current project?', person='bob')
    assert memory.build_context('What is a project?', person='bob') == ''


def test_correction_does_not_supersede_a_different_preference_topic(memory):
    learn('I prefer tea.')
    learn('Actually, I prefer Rust.')
    assert len(memory.list_facts()) == 2


def test_a_corrupt_backup_prevents_rewriting_legacy_memory(memory):
    memory.add_fact('Original manual memory')
    learn('I prefer Rust.')
    original = memory.FACTS_FILE.read_bytes()
    backup = memory.FACTS_FILE.parent / 'backups' / 'autonomous-memory-v1' / memory.FACTS_FILE.name
    backup.write_bytes(b'damaged')
    with pytest.raises(OSError, match='backup'):
        memory.add_fact('Another manual memory')
    assert memory.FACTS_FILE.read_bytes() == original


def test_manual_memories_and_ambiguous_conflicts_are_not_silently_replaced(memory):
    memory.add_fact('Bob prefers Python')
    learn('Actually, I prefer Rust.')
    assert len(memory.list_facts()) == 2
    assert 'conflict' in memory.build_context('Bob prefers Python or Rust')


def test_existing_data_backed_up_exactly_before_rewrite(memory):
    memory.add_fact('A manually saved legacy fact')
    original = memory.FACTS_FILE.read_bytes()
    learn('I prefer Rust.')
    backup = memory.FACTS_FILE.parent / 'backups' / 'autonomous-memory-v1' / memory.FACTS_FILE.name
    assert backup.read_bytes() == original


def test_write_failure_does_not_return_saved_or_change_existing_data(memory, monkeypatch):
    memory.add_fact('Bob likes tea')
    old = memory.FACTS_FILE.read_bytes()
    before = formation.diagnostics().get('save_confirmed', 0)
    def fail(*_a, **_kw):
        raise OSError('disk full')
    monkeypatch.setattr(memory._atomic, 'write_text', fail)
    with pytest.raises(OSError):
        learn('I prefer Rust.')
    assert memory.FACTS_FILE.read_bytes() == old
    assert formation.diagnostics().get('save_confirmed', 0) == before


def test_successful_return_from_broken_writer_is_not_confirmation(memory, monkeypatch):
    monkeypatch.setattr(memory._atomic, 'write_text', lambda *_a, **_kw: None)
    with pytest.raises(OSError):
        learn('I prefer Rust.')


def test_read_failure_cannot_erase_the_store(memory, monkeypatch):
    memory.add_fact('Bob likes tea')
    old = memory.FACTS_FILE.read_bytes()
    monkeypatch.setattr(memory, '_read_facts', lambda: (_ for _ in ()).throw(PermissionError('unreadable')))
    with pytest.raises(PermissionError):
        memory.add_fact('New fact')
    assert memory.FACTS_FILE.read_bytes() == old


def test_disabled_learning_preserves_manual_commands_and_data(memory):
    learn('I prefer Rust.')
    memory.set_learning(False)
    assert learn("I'm building a new research project.") == []
    receipt = memory.memory_command('remember the sample box is blue')
    assert receipt.startswith('Saved to memory:') and 'Memory ID:' in receipt
    assert len(memory.list_facts()) == 2
    assert any(row['text'] == 'the sample box is blue' for row in memory.list_facts())
    assert memory.memory_command('forget sample box').startswith('Forgotten')


@pytest.mark.parametrize('contents', ['{broken', '[]', 'null'])
def test_bad_settings_fail_closed(memory, contents):
    memory.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    memory.SETTINGS_FILE.write_text(contents, encoding='utf-8')
    assert not memory.learning_enabled()
    assert learn('I prefer Rust.') == []
    with pytest.raises(ValueError):
        memory.set_learning(True)


def test_retrieval_cannot_reset_damaged_settings_and_enable_learning(memory):
    memory.add_fact('Bob likes tea')
    memory.SETTINGS_FILE.write_text('{broken', encoding='utf-8')
    assert memory.list_facts()
    assert not memory.learning_enabled()
    assert memory.SETTINGS_FILE.read_text() == '{broken'


def test_concurrent_saves_preserve_each_record_and_deduplicate(memory):
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda _: learn('I prefer Rust.'), range(12)))
    assert len(memory.list_facts()) == 1


def test_existing_companion_learners_honor_off_and_nonretention(memory, monkeypatch, tmp_path):
    from cursiv_v215.memory import projects
    from cursiv_v215.coding import brain
    from cursiv_v215.core import style
    monkeypatch.setattr(projects, 'DIR', tmp_path / 'projects')
    monkeypatch.setattr(style, 'DIR', tmp_path / 'style')
    monkeypatch.setattr(brain, 'PROFILE_FILE', tmp_path / 'coding.json')
    memory.set_learning(False)
    def no_call(_):
        pytest.fail('Disabled learners must not invoke a model')
    assert projects.learn('I am building Cursiv on Windows', '', no_call, 'bob') is None
    assert brain.learn_from_exchange('I prefer Rust over Python', '', no_call, 'bob') == []
    assert style.learn_correction('bob', 'I prefer brief answers', '', no_call) is None
    brain.observe('PS C:\\Projects> python -m venv demo', 'bob')
    assert not brain.PROFILE_FILE.exists()


def test_model_proposals_cannot_save_assistant_only_or_unsupported_claims(memory):
    assert memory.learn_from_exchange('Tell me a story about sailing on a lake', 'Bob owns a boat',
                                     lambda _: '["Bob owns a boat"]', person='bob') == []
    assert memory.learn_from_exchange('Tell me about learning piano', 'Anything', lambda _: '{"bad": true}',
                                     person='bob') == []
    assert memory.learn_from_exchange('Do I prefer Rust or Python?', '', lambda _: '["Bob prefers Rust"]',
                                     person='bob') == []


def test_one_worker_is_bounded_and_skips_reprocessed_event(_memory_isolated):
    done = threading.Event()
    assert _memory_isolated(done.set, 'test-single-worker-event')
    assert done.wait(3)
    formation._jobs.join()
    assert not _memory_isolated(done.set, 'test-single-worker-event')


def test_chat_captures_person_before_background_execution(memory, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    jobs = []
    monkeypatch.setattr(formation, 'submit', lambda work, _id: jobs.append(work))
    monkeypatch.setattr(ca, '_memory_llm', lambda _: '')
    ca._learn_later('I prefer Rust.', 'Okay', person='bob', event_id='captured')
    memory.set_person('alice')
    jobs[0]()
    assert memory.list_facts('bob')[0]['person'] == 'bob'
    assert memory.list_facts('alice') == []


def test_forget_cancels_an_extraction_already_waiting_for_a_model(memory):
    memory.add_fact('Bob likes tea')
    started, release = threading.Event(), threading.Event()
    def ask(_):
        started.set()
        assert release.wait(3)
        return '["Bob is learning piano"]'
    with ThreadPoolExecutor(max_workers=1) as pool:
        job = pool.submit(memory.learn_from_exchange, 'I have been practicing piano every evening', '', ask, 'bob')
        assert started.wait(3)
        memory.forget('tea')
        release.set()
        assert job.result(timeout=3) == []
    assert memory.list_facts() == []


def test_optional_memory_model_never_uses_cloud_fallback(monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    monkeypatch.setattr(ca, '_ollama_running', lambda: False)
    monkeypatch.setattr(ca, '_free_key_llm', lambda *_: pytest.fail('Cloud extraction forbidden'))
    assert ca._memory_llm([{'role': 'user', 'content': 'Fact'}]) == ''


def test_memory_window_displays_origin_history_and_failed_toggle(memory, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    from memory_dialog import MemoryDialog
    app = QApplication.instance() or QApplication([])
    learn('I prefer Python.')
    learn('Actually, I prefer Rust.')
    dialog = MemoryDialog()
    assert dialog._list.count() == 1
    assert 'automatic' in dialog._list.item(0).text()
    dialog._historical.setChecked(True)
    assert dialog._list.count() == 2
    assert any('superseded' in dialog._list.item(i).text() for i in range(2))
    def fail(_):
        raise OSError('read-only settings')
    monkeypatch.setattr(memory, 'set_learning', fail)
    dialog._learn.setChecked(False)
    assert dialog._learn.isChecked() and 'not saved' in dialog._status.text()
    dialog.close()
    app.processEvents()

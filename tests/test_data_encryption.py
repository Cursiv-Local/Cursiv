"""Synthetic, independent filesystem checks. Never open the owner's real vault."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest
from cursiv_engine.core import atomic, private_store, vault, vault_migration, state_store

PASSWORD = 'synthetic-test-passphrase-only'


@pytest.fixture
def encrypted(tmp_path):
    root = tmp_path / '.cursiv'
    root.mkdir()
    yield root
    vault.lock()


def test_default_off_preserves_plaintext_schema(encrypted):
    path = encrypted / 'memory_facts.jsonl'
    atomic.write_text(path, '{"text":"plain compatibility"}\n')
    assert path.read_text(encoding='utf-8') == private_store.read_text(path)
    assert not (encrypted / vault.MARKER).exists()


def test_migration_exact_bytes_backups_and_notebook_unchanged(encrypted):
    values = {'memory_facts.jsonl': b'{"text":"unique secret marker"}\ninvalid-line\n',
              'backups/autonomous-memory-v1/memory_facts.jsonl': b'older secret marker\n',
              'conversations/one.json': '{"html":"private ünicode"}'.encode('utf-8'),
              'projects/family.json': b'{"project":"private project"}'}
    for name, value in values.items():
        path = encrypted / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
    notebook = encrypted / 'fieldlog/observations.jsonl'
    notebook.parent.mkdir(); notebook.write_bytes(b'notebook-original-chain')
    counts = vault_migration.migrate(PASSWORD, [encrypted])
    assert counts[str(encrypted)] == len(values)
    for name, value in values.items():
        path = encrypted / name
        assert path.read_bytes().startswith(vault.MAGIC)
        assert value not in path.read_bytes()
        assert private_store.read_bytes(path) == value
    assert notebook.read_bytes() == b'notebook-original-chain'
    for path in (encrypted / '.vault-recovery').iterdir():
        assert b'secret marker' not in path.read_bytes()
    # Independently decrypt the authenticated snapshot and each recovery file.
    _, cipher = vault.authenticate(encrypted, PASSWORD)
    records = json.loads(vault.unpack(cipher, vault_migration.JOURNAL,
                                     (encrypted / vault_migration.JOURNAL).read_bytes()))
    for r in records:
        backup = Path(r['backup'])
        assert vault.unpack(cipher, backup, (encrypted / backup).read_bytes()) == values[r['path']]


def test_locked_wrong_key_tamper_and_missing_metadata_fail_closed(encrypted):
    path = encrypted / 'memory_facts.jsonl'; path.write_bytes(b'secret')
    vault_migration.migrate(PASSWORD, [encrypted]); original = path.read_bytes()
    vault.lock()
    for operation in (lambda: private_store.read_text(path), lambda: atomic.write_text(path, 'replacement'),
                      lambda: private_store.append_text(path, 'more')):
        with pytest.raises(vault.VaultError): operation()
        assert path.read_bytes() == original
    with pytest.raises(vault.VaultError): vault.unlock('incorrect passphrase', [encrypted])
    vault.unlock(PASSWORD, [encrypted])
    path.write_bytes(original[:-5] + b'xxxxx')
    with pytest.raises(vault.VaultError): private_store.read_bytes(path)
    path.write_bytes(original)
    (encrypted / vault.MARKER).unlink()
    with pytest.raises(vault.VaultError): private_store.read_text(path)
    with pytest.raises(vault.VaultError): atomic.write_text(path, 'replacement')
    assert path.read_bytes() == original


def test_path_binding_prevents_record_swap(encrypted):
    vault_migration.migrate(PASSWORD, [encrypted])
    a = encrypted / 'conversations/a.json'; b = a.with_name('b.json')
    atomic.write_text(a, 'first'); atomic.write_text(b, 'second')
    b.write_bytes(a.read_bytes())
    with pytest.raises(vault.VaultError): private_store.read_text(b)
    with pytest.raises(vault.VaultError): atomic.write_text(b, 'replacement')


def test_failed_write_uses_only_ciphertext_temporary_and_preserves_original(encrypted, monkeypatch):
    vault_migration.migrate(PASSWORD, [encrypted])
    path = encrypted / 'memory_facts.jsonl'
    atomic.write_text(path, 'original-marker'); original = path.read_bytes()
    def denied(source, destination):
        staged = Path(source).read_bytes()
        assert staged.startswith(vault.MAGIC)
        assert b'new-secret-marker' not in staged
        raise PermissionError('simulated read-only destination')
    monkeypatch.setattr(atomic.os, 'replace', denied)
    with pytest.raises(PermissionError): atomic.write_text(path, 'new-secret-marker')
    assert path.read_bytes() == original
    assert not list(encrypted.glob('.*.tmp'))


def test_session_and_saved_notes_are_not_plaintext(encrypted, monkeypatch):
    from cursiv_engine.memory import session_log
    from cursiv_engine.core import strand_store
    import saved_notes
    monkeypatch.setattr(session_log, 'CURSIV_DIR', encrypted)
    monkeypatch.setattr(session_log, 'SESSIONS_DIR', encrypted / 'sessions')
    monkeypatch.setattr(session_log, 'MEMORY_FILE', encrypted / 'memory.json')
    monkeypatch.setattr(strand_store, 'CURSIV_DIR', encrypted)
    monkeypatch.setattr(strand_store, 'STRANDS_FILE', encrypted / 'strands.jsonl')
    monkeypatch.setattr(strand_store, '_find_linked', lambda *a, **k: [])
    monkeypatch.setattr(strand_store._mx, 'invalidate', lambda: None)
    vault_migration.migrate(PASSWORD, [encrypted])
    session_log.append_exchange('private-session-question', 'private-session-answer', 'local')
    assert session_log.get_last_exchange()['user'] == 'private-session-question'
    # The normal public writer, including its read-back receipt.
    record_id = strand_store.save_strand('private-note', 'saved answer')
    assert record_id
    assert saved_notes.read_notes()[0][0]['query'] == 'private-note'
    assert saved_notes.read_notes()[0][0]['id'] == record_id
    for path in (encrypted / 'sessions').glob('*'):
        assert b'private-session' not in path.read_bytes()
    assert b'private-note' not in strand_store.STRANDS_FILE.read_bytes()


def test_restart_and_portable_relocation(encrypted, tmp_path):
    path = encrypted / 'memory_facts.jsonl'; path.write_bytes(b'portable-secret')
    vault_migration.migrate(PASSWORD, [encrypted]); vault.lock()
    moved = tmp_path / 'moved-drive/.cursiv'; moved.parent.mkdir(); encrypted.rename(moved)
    code = ('from pathlib import Path; from cursiv_engine.core import vault,private_store; '
            'root=Path(__import__("sys").argv[1]); '
            'vault.unlock("synthetic-test-passphrase-only",[root]); '
            'assert private_store.read_bytes(root/"memory_facts.jsonl")==b"portable-secret"')
    subprocess.run([sys.executable, '-B', '-c', code, str(moved)], check=True, timeout=30)
    assert b'portable-secret' not in (moved / 'memory_facts.jsonl').read_bytes()


def test_failed_migration_resumes_without_empty_overwrite(encrypted, monkeypatch):
    a = encrypted / 'memory_facts.jsonl'; b = encrypted / 'memory.json'
    a.write_bytes(b'facts'); b.write_bytes(b'old runs')
    original = atomic.write_bytes
    def fail(path, data, **kwargs):
        if Path(path) == a: raise OSError('simulated disk full')
        return original(path, data, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(atomic, 'write_bytes', fail)
        with pytest.raises(OSError): vault_migration.migrate(PASSWORD, [encrypted])
    assert vault.metadata(encrypted)['state'] == 'migrating'
    with pytest.raises(vault.VaultError): private_store.read_text(a)
    assert a.read_bytes() == b'facts'
    vault_migration.migrate(PASSWORD, [encrypted])
    assert private_store.read_bytes(a) == b'facts'
    assert private_store.read_bytes(b) == b'old runs'


def test_state_store_backups_are_encrypted_and_readable(encrypted):
    vault_migration.migrate(PASSWORD, [encrypted])
    path = encrypted / 'projects/family.json'
    state_store.save(path, {'notes': 'first secret'})
    state_store.save(path, {'notes': 'second secret'})
    backup, = (path.parent / 'backups').glob('*')
    assert b'first secret' not in backup.read_bytes()
    assert json.loads(private_store.read_text(backup)) == {'notes': 'first secret'}
    assert state_store.load(path, {}) == {'notes': 'second secret'}


def test_semantic_memory_and_conversation_roundtrip(encrypted, monkeypatch):
    from cursiv_engine.memory import semantic
    import conversations
    for key, name in (('FACTS_FILE','memory_facts.jsonl'), ('SETTINGS_FILE','memory_settings.json'),
                      ('EMB_CACHE_FILE','embeddings_cache.json')):
        monkeypatch.setattr(semantic, key, encrypted / name)
    monkeypatch.setattr(semantic, 'CURSIV_DIR', encrypted)
    monkeypatch.setattr(conversations, 'DIR', encrypted / 'conversations')
    vault_migration.migrate(PASSWORD, [encrypted])
    semantic._write_facts([{'id':'stable-id','text':'East Fork private marker','person':'family'}])
    assert semantic._read_facts()[0][0]['id'] == 'stable-id'
    semantic._write_facts([{'id':'stable-id','text':'corrected marker','person':'family'}])
    assert b'East Fork' not in semantic.FACTS_FILE.read_bytes()
    conv_id = conversations.save(None, [{'role':'user','content':'conversation secret'}], '<p>secret</p>')
    assert conversations.load(conv_id)['messages'][0]['content'] == 'conversation secret'
    conversations.rename(conv_id, 'Private title')
    assert conversations.list_all()[0]['title'] == 'Private title'
    path = conversations.DIR / (conv_id + '.json'); original = path.read_bytes()
    vault.lock()
    with pytest.raises(vault.VaultError): conversations.save(conv_id, [], '')
    assert path.read_bytes() == original


def test_lease_blocks_second_process(encrypted):
    from cursiv_engine.core.data_lease import DataLease
    code = ('from cursiv_engine.core.data_lease import DataLease; '
            'from pathlib import Path; import sys; '
            'DataLease([Path(sys.argv[1])]).__enter__()')
    with DataLease([encrypted]):
        result = subprocess.run([sys.executable, '-B', '-c', code, str(encrypted)],
                                capture_output=True, timeout=30)
        assert result.returncode != 0
        assert b'data is in use' in result.stderr
    with DataLease([encrypted]): pass


def test_hard_link_refused_before_migration(encrypted):
    original = encrypted / 'memory.json'; original.write_bytes(b'secret')
    try: os.link(original, encrypted / 'memory_facts.jsonl')
    except OSError: pytest.skip('hard links unavailable')
    with pytest.raises(vault.VaultError): vault_migration.migrate(PASSWORD, [encrypted])
    assert not (encrypted / vault.MARKER).exists()


def test_startup_cancel_and_unlock_use_native_password_dialog(encrypted, monkeypatch):
    import encryption_dialog
    vault_migration.migrate(PASSWORD, [encrypted]); vault.lock()
    monkeypatch.setattr(vault, 'roots', lambda: [encrypted])
    monkeypatch.setattr(encryption_dialog.QInputDialog, 'getText', lambda *a: ('', False))
    assert encryption_dialog.startup() is False
    with pytest.raises(vault.VaultError): state_store.load(encrypted / 'projects/missing.json', {})
    monkeypatch.setattr(encryption_dialog.QInputDialog, 'getText', lambda *a: (PASSWORD, True))
    assert encryption_dialog.startup() is True
    assert state_store.load(encrypted / 'projects/missing.json', {}) == {}


def test_startup_mismatched_confirmation_never_migrates(encrypted, monkeypatch):
    import encryption_dialog
    monkeypatch.setattr(vault, 'roots', lambda: [encrypted])
    monkeypatch.setattr(encryption_dialog.QMessageBox, 'question',
                        lambda *a: encryption_dialog.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(encryption_dialog.QMessageBox, 'warning', lambda *a: None)
    replies = iter([(PASSWORD, True), ('different confirmation', True)])
    monkeypatch.setattr(encryption_dialog.QInputDialog, 'getText', lambda *a: next(replies))
    assert encryption_dialog.startup(configure=True) is False
    assert not (encrypted / vault.MARKER).exists()

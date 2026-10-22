"""Other state-changing stores must confirm bytes/IDs, including failures."""
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from cursiv_v215.core import atomic


def test_atomic_write_verifies_bytes_and_preserves_unrelated_temporary_files(tmp_path):
    path = tmp_path / 'config.json'
    unrelated = path.with_name(path.name + '.tmp')
    unrelated.write_bytes(b'existing unrelated file')
    atomic.write_text(path, 'first\r\nsecond\n')
    assert path.read_bytes() == b'first\r\nsecond\n'
    assert unrelated.read_bytes() == b'existing unrelated file'
    assert not list(tmp_path.glob('.config.json-*.tmp'))
    atomic.write_bytes(tmp_path / 'image.png', b'\x89PNG\r\nmarker')
    assert (tmp_path / 'image.png').read_bytes() == b'\x89PNG\r\nmarker'


def test_atomic_failure_preserves_original_and_readback_failure_raises(tmp_path, monkeypatch):
    path = tmp_path / 'config.json'
    path.write_bytes(b'original')
    with monkeypatch.context() as patch:
        patch.setattr(atomic.os, 'replace', lambda *_: (_ for _ in ()).throw(OSError('disk full')))
        with pytest.raises(OSError):
            atomic.write_text(path, 'new')
    assert path.read_bytes() == b'original' and not list(tmp_path.glob('.config.json-*.tmp'))
    original_read = Path.read_bytes
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'read_bytes', lambda p: b'wrong' if p == path else original_read(p))
        with pytest.raises(OSError, match='read-back'):
            atomic.write_text(path, 'new')
    assert path.read_bytes() == b'new'  # unconfirmed means uncertain; never delete an existing write


@pytest.fixture
def vault(tmp_path, monkeypatch):
    from cursiv_v215.family import legacy_store as store
    folder = tmp_path / 'vault'
    monkeypatch.setattr(store, '_LEGACY_DIR', folder)
    monkeypatch.setattr(store, '_LETTERS_DIR', folder / 'letters')
    monkeypatch.setattr(store, '_INDEX_FILE', folder / 'index.json')
    monkeypatch.setattr(store, 'export_destination', lambda: tmp_path)
    return store


def letter(vault, body='actual letter body'):
    return vault.save_letter('dana', 'Dana', 'alex', 'Alex', 'Subject', body)


def test_letter_create_update_and_delete_are_independently_verifiable(vault):
    identifier = letter(vault)
    entry = vault.get_letter_entry(identifier)
    path = vault._LETTERS_DIR / entry['filename']
    assert path.exists() and path.read_bytes().endswith(b'actual letter body\n')
    assert vault.get_letter_content(identifier) == 'actual letter body\n'
    assert vault.rewrite_letter(identifier, 'updated body')
    assert path.read_bytes().endswith(b'updated body\n')
    assert vault.delete_letter(identifier) and not path.exists() and vault.get_letter_entry(identifier) is None


def test_simultaneous_letter_saves_do_not_overwrite_same_second(vault):
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda i: letter(vault, f'letter {i}'), range(8)))
    assert len(set(ids)) == 8 and len(vault._load_index()) == 8
    assert {vault.get_letter_content(i) for i in ids} == {f'letter {i}\n' for i in range(8)}


def test_failed_delete_preserves_the_letter_and_its_index(vault, monkeypatch):
    identifier = letter(vault)
    before = vault._INDEX_FILE.read_bytes()
    path = vault._LETTERS_DIR / vault.get_letter_entry(identifier)['filename']
    unlink = Path.unlink
    def denied(p, *args, **kwargs):
        if p == path:
            raise PermissionError('read-only letter')
        return unlink(p, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', denied)
    with pytest.raises(PermissionError):
        vault.delete_letter(identifier)
    assert path.exists() and vault._INDEX_FILE.read_bytes() == before


def test_damaged_letter_index_never_becomes_an_empty_successful_save(vault):
    identifier = letter(vault)
    vault._INDEX_FILE.write_bytes(b'corrupted existing index')
    before = {p.name: p.read_bytes() for p in vault._LETTERS_DIR.iterdir()}
    with pytest.raises(ValueError):
        letter(vault, 'must not replace old data')
    assert vault._INDEX_FILE.read_bytes() == b'corrupted existing index'
    assert {p.name: p.read_bytes() for p in vault._LETTERS_DIR.iterdir()} == before


def test_letter_index_failure_never_returns_a_saved_id(vault, monkeypatch):
    monkeypatch.setattr(vault, '_save_index', lambda *_: (_ for _ in ()).throw(OSError('index disk full')))
    with pytest.raises(OSError, match='index disk full'):
        letter(vault)
    assert not vault._INDEX_FILE.exists()


def test_legacy_letter_exports_and_reimports_are_verified_and_duplicate_safe(vault, tmp_path, monkeypatch):
    identifier = vault.save_letter('dana', 'Dana', 'alex', 'Alex', 'Subject', 'import marker', written='2026-01-01T12:00:00Z')
    pack, count = vault.export_pack('dana', 'Dana')
    assert count == 1 and json.loads(pack.read_bytes())['letters'][0]['content'] == 'import marker\n'
    folder = tmp_path / 'second-vault'
    monkeypatch.setattr(vault, '_LETTERS_DIR', folder / 'letters')
    monkeypatch.setattr(vault, '_INDEX_FILE', folder / 'index.json')
    assert vault.import_pack(pack)[0] == 1
    assert vault.import_pack(pack)[0] == 0
    assert len(vault._load_index()) == 1 and vault._load_index()[0]['written'] == '2026-01-01T12:00:00Z'


def test_agent_mutations_use_verified_storage_and_do_not_replace_corrupt_data(tmp_path, monkeypatch):
    from cursiv_v215.agents import custom
    monkeypatch.setattr(custom, 'DIR', tmp_path / 'agents')
    assert 'Created agent' in custom.create('researcher', 'helps record precise field observations')
    path = custom._dir() / 'researcher.json'
    assert json.loads(path.read_bytes())['name'] == 'researcher'
    assert 'will remember' in custom.teach('researcher', 'use exact decimal precision')
    assert 'use exact decimal precision' in json.loads(path.read_bytes())['knowledge']
    assert 'Updated' in custom.edit('researcher', 'helps evaluate field observations')
    path.write_bytes(b'damaged data')
    with pytest.raises(ValueError):
        custom.create('researcher', 'must not overwrite corrupt existing data')
    assert path.read_bytes() == b'damaged data'


def test_agent_save_failure_and_unverified_backend_return_do_not_succeed(tmp_path, monkeypatch):
    from cursiv_v215.agents import custom
    monkeypatch.setattr(custom, 'DIR', tmp_path / 'agents')
    monkeypatch.setattr(custom.atomic, 'write_text', lambda *_a, **_kw: None)
    with pytest.raises(OSError, match='read-back'):
        custom.create('researcher', 'helps record precise field observations')


def test_saved_notes_append_is_flushed_and_verified_before_returning_id(tmp_path, monkeypatch):
    from cursiv_v215.core import strand_store as store
    monkeypatch.setattr(store, 'CURSIV_DIR', tmp_path / 'strands')
    monkeypatch.setattr(store, 'STRANDS_FILE', tmp_path / 'strands' / 'strands.jsonl')
    monkeypatch.setattr(store, '_strand_encode', lambda *_: 'encoded')
    monkeypatch.setattr(store, '_find_linked', lambda *_: [])
    identifier = store.save_strand('user observation', 'actual saved note')
    row = json.loads(store.STRANDS_FILE.read_bytes())
    assert identifier and row['id'] == identifier and row['synthesis'] == 'actual saved note'
    with monkeypatch.context() as patch:
        patch.setattr(store.os, 'fsync', lambda *_: (_ for _ in ()).throw(OSError('flush failed')))
        assert store.save_strand('other user observation', 'uncertain append') == ''


def test_image_cache_uses_user_storage_and_verified_bytes(tmp_path, monkeypatch):
    import chat_commands as cc
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(cc, '_vision_describe', lambda *args: ('', ''))
    monkeypatch.setattr(cc, '_STRAND_OK', False)
    result = cc.analyze_pasted_image(b'actual PNG marker', {}, 10, 20)
    image = Path(result.image_path)
    assert image.is_relative_to(tmp_path / '.cursiv' / 'images')
    assert image.read_bytes() == b'actual PNG marker'
    other = cc.analyze_pasted_image(b'second PNG marker', {}, 10, 20)
    assert other.image_path != result.image_path and image.read_bytes() == b'actual PNG marker'


def test_model_action_transcripts_are_not_execution_and_code_examples_remain_prose():
    from cursiv_v215.core import file_access
    for text in ('→ file_create: test.txt', '- `file_create: test.txt`', 'Created file: test.txt',
                 'I saved it to C:\\fake.txt', "Got it — I'll remember HAWK-217."):
        assert 'not confirmed' in file_access.model_prose(text)
    example = 'Example code:\n```python\nwrite_file(path)\n```'
    assert file_access.model_prose(example) == example
    assert file_access.model_prose('I wrote the following function:\n```python\ndef f(): pass\n```').startswith('I wrote')


def test_saved_notes_alias_is_preserved_and_failed_append_has_no_success(monkeypatch):
    import chat_commands as cc
    from cursiv_v215.memory import intents
    history = [dict(role='user', content='field question'), dict(role='assistant', content='field answer')]
    assert intents.command('save this', history, person='dana') is None
    monkeypatch.setattr(cc, '_STRAND_OK', True)
    calls = []
    monkeypatch.setattr(cc, '_strand_save', lambda *args, **kw: calls.append(args) or '')
    result = cc.handle_command('save this', {}, history)
    assert calls == [('field question', 'field answer')]
    assert 'not confirmed' in result.text and 'Saved as note' not in result.text

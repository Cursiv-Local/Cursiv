"""Other state-changing stores must confirm bytes/IDs, including failures."""
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from cursiv_engine.core import atomic


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


def test_agent_mutations_use_verified_storage_and_do_not_replace_corrupt_data(tmp_path, monkeypatch):
    from cursiv_engine.agents import custom
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
    from cursiv_engine.agents import custom
    monkeypatch.setattr(custom, 'DIR', tmp_path / 'agents')
    monkeypatch.setattr(custom.atomic, 'write_text', lambda *_a, **_kw: None)
    with pytest.raises(OSError, match='read-back'):
        custom.create('researcher', 'helps record precise field observations')


def test_saved_notes_append_is_flushed_and_verified_before_returning_id(tmp_path, monkeypatch):
    from cursiv_engine.core import strand_store as store
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
    from cursiv_engine.core import file_access
    for text in ('→ file_create: test.txt', '- `file_create: test.txt`', 'Created file: test.txt',
                 'I saved it to C:\\fake.txt', "Got it — I'll remember HAWK-217."):
        assert 'not confirmed' in file_access.model_prose(text)
    example = 'Example code:\n```python\nwrite_file(path)\n```'
    assert file_access.model_prose(example) == example
    assert file_access.model_prose('I wrote the following function:\n```python\ndef f(): pass\n```').startswith('I wrote')


def test_saved_notes_alias_is_preserved_and_failed_append_has_no_success(monkeypatch):
    import chat_commands as cc
    from cursiv_engine.memory import intents
    history = [dict(role='user', content='field question'), dict(role='assistant', content='field answer')]
    assert intents.command('save this', history, person='dana') is None
    monkeypatch.setattr(cc, '_STRAND_OK', True)
    calls = []
    monkeypatch.setattr(cc, '_strand_save', lambda *args, **kw: calls.append(args) or '')
    result = cc.handle_command('save this', {}, history)
    assert calls == [('field question', 'field answer')]
    assert 'not confirmed' in result.text and 'Saved as note' not in result.text

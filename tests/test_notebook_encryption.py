"""U98: the field notebook is encrypted with conversations and memories.

Entries, photos and other devices' logs are encrypted on a computer; reports,
exports and shares are made to be handed out and stay readable.
"""
import hashlib
import json
from pathlib import Path

import pytest

from cursiv_engine.core import field_recall, fieldlog, fieldsync, private_store, vault, vault_migration

PASSWORD = 'synthetic-notebook-passphrase'
PNG = b'\x89PNG\r\n\x1a\n' + b'synthetic photo bytes' * 20


@pytest.fixture
def notebook(tmp_path, monkeypatch):
    root = tmp_path / '.cursiv'
    (root / 'fieldlog').mkdir(parents=True)
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: root / 'fieldlog')
    yield root
    vault.lock()


def _photo(tmp_path):
    f = tmp_path / 'site.png'
    f.write_bytes(PNG)
    return f


def test_covered_paths():
    for rel in ('fieldlog/observations.jsonl', 'fieldlog/photos/' + 'a' * 64 + '.jpg', 'fieldlog/team/phone-1.jsonl',
                'fieldlog/team/laptop.conflict-20261025.jsonl'):
        assert vault.covered(Path(rel)), rel
    for rel in ('fieldlog/reports/field-report.html', 'fieldlog/exports/x/observations.json',
                'fieldlog/team/laptop.key.json', 'fieldlog/team/revoked.json', 'fieldlog/received/up.cursivsync',
                'fieldlog/memory.json'):
        assert not vault.covered(Path(rel)), rel


def test_entries_and_photos_are_encrypted_and_still_work(notebook, tmp_path):
    vault_migration.migrate(PASSWORD, [notebook])
    rel = fieldlog.store_photo(_photo(tmp_path))
    fieldlog.add(site='North Creek', sample_id='ENC-1', note='private site note', photos=[rel],
                 measurements=[{'name': 'water temp', 'value': '14.2', 'unit': 'C'}])
    fieldlog.add(site='North Creek', sample_id='ENC-2', measurements=[{'name': 'water temp', 'value': '13.8', 'unit': 'C'}])
    raw = fieldlog.log_file().read_bytes()
    assert raw.startswith(vault.MAGIC) and b'private site note' not in raw
    assert fieldlog.photo_path(rel).read_bytes().startswith(vault.MAGIC)
    assert fieldlog.photo_bytes(rel) == PNG
    assert [e['sample_id'] for e in fieldlog.entries()] == ['ENC-1', 'ENC-2']
    assert fieldlog.verify() == [] and fieldlog.photo_problems() == []
    assert field_recall.query(sample='ENC-1')['total'] == 1
    assert 'is 14 C, from 2 record(s)' in field_recall.command('average water temp in my ENC samples')


def test_locked_notebook_never_reads_as_empty(notebook):
    vault_migration.migrate(PASSWORD, [notebook])
    fieldlog.add(site='A', note='x')
    vault.lock()
    with pytest.raises(vault.VaultError):
        fieldlog.entries()
    with pytest.raises(vault.VaultError):
        fieldlog.add(site='B', note='y')


def test_export_and_share_are_readable(notebook, tmp_path):
    vault_migration.migrate(PASSWORD, [notebook])
    rel = fieldlog.store_photo(_photo(tmp_path))
    fieldlog.add(site='Export Site', note='shared note', photos=[rel])
    out = fieldlog.export(tmp_path / 'export')
    exported = Path(out['photos']) / Path(rel).name
    assert exported.read_bytes() == PNG
    shared = tmp_path / 'shared'
    fieldsync.share(shared)
    logs = list(shared.rglob('*.jsonl'))
    assert logs and not logs[0].read_bytes().startswith(vault.MAGIC) and b'shared note' in logs[0].read_bytes()


def test_existing_vault_adopts_a_readable_notebook(notebook, tmp_path):
    """A computer encrypted by U97 has a readable notebook; the next unlock encrypts it."""
    (notebook / 'memory.json').write_bytes(b'{}')
    vault_migration.migrate(PASSWORD, [notebook])
    entry = json.dumps({'note': 'from U97'}) + '\n'
    fieldlog.log_file().write_bytes(entry.encode('utf-8'))
    photo = notebook / 'fieldlog' / 'photos' / (hashlib.sha256(PNG).hexdigest() + '.png')
    photo.parent.mkdir(); photo.write_bytes(PNG)
    assert vault_migration.adopt_new_stores([notebook]) == 2
    assert fieldlog.log_file().read_bytes().startswith(vault.MAGIC)
    assert private_store.read_text(fieldlog.log_file()) == entry
    assert private_store.read_bytes(photo) == PNG
    assert any(p.name.startswith('adopt-') for p in (notebook / '.vault-recovery').iterdir())
    assert vault_migration.adopt_new_stores([notebook]) == 0          # once only

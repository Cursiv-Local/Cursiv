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
                'fieldlog/team/laptop.conflict-20261025.jsonl',
                'fieldlog/received/up.cursivsync',                     # U101: phone uploads are encrypted
                'fieldlog/.import-ab12cd34ef56/cursiv-field-share/phone-1.jsonl'):   # and so is unpacking
        assert vault.covered(Path(rel)), rel
    for rel in ('fieldlog/reports/field-report.html', 'fieldlog/exports/x/observations.json',
                'fieldlog/team/laptop.key.json', 'fieldlog/team/revoked.json',
                'fieldlog/received-large/up.cursivsync',               # over 64 MB: readable, and listed
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


# ── U101 review: no readable copies of phone uploads or imports on an encrypted computer ──

def _vault_notebook(notebook):
    vault_migration.migrate(PASSWORD, [notebook])
    return notebook / 'fieldlog'


def test_a_phone_upload_is_kept_encrypted(notebook, monkeypatch):
    import io
    from cursiv_engine.core import phone_receive
    log = _vault_notebook(notebook)
    def refuse(path):                     # the import fails, so the upload is kept for another try
        raise ValueError('not a phone file')
    monkeypatch.setattr(fieldsync, 'import_phone_bundle', refuse)
    body = b'PK synthetic upload with a private site name'
    r = phone_receive.Receiver(report=lambda *_: None, port=0)
    text = r.receive('send.cursivsync', io.BytesIO(body).read, len(body))
    kept = list((log / 'received').iterdir())
    assert len(kept) == 1 and kept[0].read_bytes().startswith(vault.MAGIC)       # was: the bytes as sent
    assert private_store.read_bytes(kept[0]) == body and b'private site' not in kept[0].read_bytes()
    assert 'kept, encrypted' in text


def test_an_upload_too_big_to_encrypt_is_set_apart_and_listed(notebook, monkeypatch):
    import io
    from cursiv_engine.core import phone_receive
    log = _vault_notebook(notebook)
    monkeypatch.setattr(vault, 'MAX_BYTES', 8192)
    monkeypatch.setattr(fieldsync, 'import_phone_bundle', lambda path: (_ for _ in ()).throw(ValueError('x')))
    body = b'PK' + b'x' * 9000
    r = phone_receive.Receiver(report=lambda *_: None, port=0)
    text = r.receive('big.cursivsync', io.BytesIO(body).read, len(body))
    assert 'unencrypted (too big to encrypt)' in text
    assert [p.parent.name for p in phone_receive.readable_leftovers()] == ['received-large']
    assert not (log / 'received').exists() or not list((log / 'received').iterdir())


def test_unpacking_an_import_writes_only_encrypted_staging_and_cleans_it_up(notebook, monkeypatch):
    log = _vault_notebook(notebook)
    staged = {}

    def inspect(folder):
        staged['folder'] = folder
        staged['raw'] = {p.name: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
        return {'added': {}, 'unchanged': [], 'conflicts': [], 'rejected': [], 'own': False}
    monkeypatch.setattr(fieldsync, 'import_folder', inspect)
    bundle = {'format': fieldsync.PHONE_FORMAT, 'device': 'phone-abcdefabcdef',
              'entries': [{'note': 'private site note'}], 'manifest': {'entries': 1}}
    src = notebook / 'send.cursivsync'
    src.write_text(json.dumps(bundle), encoding='utf-8')
    fieldsync.import_phone_bundle(src)
    assert staged['folder'].parent == log and staged['folder'].name.startswith('.import-')   # not the system temp
    assert staged['raw'] and all(raw.startswith(vault.MAGIC) for raw in staged['raw'].values())
    assert not staged['folder'].exists()


def test_an_old_oversized_upload_never_blocks_unlocking(notebook, monkeypatch):
    log = _vault_notebook(notebook)
    monkeypatch.setattr(vault, 'MAX_BYTES', 8192)
    (log / 'received').mkdir(exist_ok=True)
    (log / 'received' / 'old-big.cursivsync').write_bytes(b'PK' + b'y' * 9000)   # readable, from before U101
    (log / 'received' / 'old-small.cursivsync').write_bytes(b'PK small')
    vault_migration.adopt_new_stores([notebook])                                 # was: VaultError, no unlock
    assert (log / 'received-large' / 'old-big.cursivsync').read_bytes().startswith(b'PKyy')
    small = log / 'received' / 'old-small.cursivsync'
    assert small.read_bytes().startswith(vault.MAGIC) and private_store.read_bytes(small) == b'PK small'

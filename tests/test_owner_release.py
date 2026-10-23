"""Owner signatures bind version, assets and source; no real private key is used."""
import base64
import hashlib
import json
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature
from cursiv_engine.core import release_identity as identity


@pytest.fixture
def signed(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    public = dict(algorithm='Ed25519', public_key=base64.b64encode(raw).decode(), key_id=hashlib.sha256(raw).hexdigest())
    path = tmp_path / 'public.json'; path.write_text(json.dumps(public))
    monkeypatch.setattr(identity, 'KEY_FILE', path)
    installer = tmp_path / 'Cursiv-Setup-3.14-U88.exe'; installer.write_bytes(b'MZ fixture installer')
    payload = dict(format='cursiv-owner-release-1', version='3.14-U88', source_commit='a'*40,
                   assets={installer.name:dict(size=installer.stat().st_size,sha256=hashlib.sha256(installer.read_bytes()).hexdigest())})
    envelope = dict(key_id=public['key_id'], signed=payload,
                    signature=base64.b64encode(key.sign(identity.canonical(payload))).decode())
    return installer, envelope


def test_valid_owner_signature_authenticates_actual_file(signed):
    path, envelope = signed
    assert identity.verify_file(path, envelope, '3.14-U88')['status'] == 'OwnerSignatureValid'


@pytest.mark.parametrize('change', ['bytes', 'version', 'hash', 'key', 'signature', 'source'])
def test_github_asset_or_metadata_replacement_fails(signed, change):
    path, envelope = signed
    if change == 'bytes': path.write_bytes(b'changed installer')
    elif change == 'version': envelope['signed']['version'] = '3.14-U89'
    elif change == 'hash': envelope['signed']['assets'][path.name]['sha256'] = '0'*64
    elif change == 'key': envelope['key_id'] = 'b'*64
    elif change == 'signature': envelope['signature'] = base64.b64encode(bytes(64)).decode()
    else: envelope['signed']['source_commit'] = 'b'*40
    with pytest.raises((ValueError, InvalidSignature)):
        identity.verify_file(path, envelope, '3.14-U88')


def test_owner_verified_installer_is_rechecked_before_launch(signed):
    import update_security
    path, envelope = signed
    (path.parent / 'owner-release.json').write_text(json.dumps(envelope))
    assert update_security.verify_installer(path)['status'] == 'OwnerSignatureValid'
    path.write_bytes(b'malicious changed file')
    with pytest.raises(ValueError):
        update_security.verify_installer(path)


def test_password_encrypted_backup_and_matching_restore(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from scripts import owner_release
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    keyfile = tmp_path / 'public.json'
    keyfile.write_text(json.dumps(dict(algorithm='Ed25519', public_key=base64.b64encode(public).decode(),
                                     key_id=hashlib.sha256(public).hexdigest())))
    monkeypatch.setattr(identity, 'KEY_FILE', keyfile)
    monkeypatch.setattr(owner_release, 'load_key', lambda: key)
    monkeypatch.setattr(owner_release.getpass, 'getpass', lambda _: 'test-only-password-20261023')
    backup = tmp_path / 'recovery.pem'
    owner_release.backup(backup)
    assert b'ENCRYPTED PRIVATE KEY' in backup.read_bytes()
    with pytest.raises(ValueError):
        serialization.load_pem_private_key(backup.read_bytes(), password=b'wrong')
    target = tmp_path / 'protected-key.dpapi'
    monkeypatch.setattr(owner_release, 'private_path', lambda: target)
    monkeypatch.setitem(sys.modules, 'win32crypt', SimpleNamespace(CryptProtectData=lambda raw, *a: b'fixture-protected:' + raw))
    owner_release.restore(backup)
    assert target.read_bytes().startswith(b'fixture-protected:')
    with pytest.raises(FileExistsError):
        owner_release.restore(backup)

"""Owner-only release signing. Private seed stays DPAPI-protected outside the repo.

init generates once; sign authenticates named assets; backup prompts locally for
an encrypted PKCS8 recovery backup. Never pass a recovery password on a command line.
"""
import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cursiv_engine.core import release_identity as identity
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def private_path():
    if os.name != 'nt':
        raise OSError('Owner signing is configured on the owner’s Windows account only')
    folder = Path(os.environ['LOCALAPPDATA']) / 'CursivReleaseSigning'
    for protected in (ROOT, Path(os.environ.get('OneDrive', ROOT))):
        if folder.resolve().is_relative_to(protected.resolve()):
            raise OSError('Signing key must remain outside the repository and OneDrive')
    return folder / 'owner-release-key.dpapi'


def load_key():
    import win32crypt
    raw = win32crypt.CryptUnprotectData(private_path().read_bytes(), None, None, None, 0)[1]
    return Ed25519PrivateKey.from_private_bytes(raw)


def initialize():
    import win32crypt
    path = private_path()
    if path.exists():
        raise FileExistsError('Owner key already exists; refusing to replace it')
    if identity.KEY_FILE.exists():
        raise FileExistsError('Pinned owner identity already exists; recover its key instead of replacing it')
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(win32crypt.CryptProtectData(raw, 'Cursiv owner release signing', None, None, None, 0))
    record = dict(algorithm='Ed25519', publisher='Joshua Winkler / Cursiv',
                  public_key=base64.b64encode(public).decode('ascii'), key_id=hashlib.sha256(public).hexdigest())
    identity.KEY_FILE.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print('Public owner fingerprint:', record['key_id'])
    print('Private key:', path, '(Windows-user protected; never upload)')


def sign(version, commit, paths, output):
    key = load_key()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    record = identity.public_identity()
    if hashlib.sha256(public).hexdigest() != record['key_id']:
        raise ValueError('Local private key does not match the pinned release identity')
    assets = {}
    for name in paths:
        path = Path(name)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if path.name in assets:
            raise ValueError('Duplicate asset name')
        assets[path.name] = dict(size=path.stat().st_size, sha256=digest)
    payload = dict(format='cursiv-owner-release-1', version=version, source_commit=commit, assets=assets)
    envelope = dict(key_id=record['key_id'], signed=payload,
                    signature=base64.b64encode(key.sign(identity.canonical(payload))).decode('ascii'))
    for name in paths:
        identity.verify_file(name, envelope, version)
    Path(output).write_text(json.dumps(envelope, indent=2) + '\n', encoding='utf-8')
    print('Signed and independently verified', len(assets), 'assets; key', record['key_id'])


def backup(output):
    destination = Path(output).resolve()
    if destination.is_relative_to(ROOT) or destination.is_relative_to(Path(os.environ.get('OneDrive', ROOT)).resolve()):
        raise ValueError('Keep recovery backups outside the repository and OneDrive')
    password = getpass.getpass('New recovery backup password (not stored): ')
    if len(password) < 16 or password != getpass.getpass('Confirm password: '):
        raise ValueError('Use a matching password of at least 16 characters')
    data = load_key().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.BestAvailableEncryption(password.encode('utf-8')))
    with Path(output).open('xb') as stream:
        stream.write(data)
    print('Encrypted recovery backup written. Store it offline, separately from the password.')


def restore(source):
    import win32crypt
    path = private_path()
    if path.exists():
        raise FileExistsError('An owner key already exists; refusing to overwrite it')
    password = getpass.getpass('Recovery backup password: ')
    key = serialization.load_pem_private_key(Path(source).read_bytes(), password=password.encode('utf-8'))
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if hashlib.sha256(public).hexdigest() != identity.public_identity()['key_id']:
        raise ValueError('Recovery key does not match the pinned owner identity')
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(win32crypt.CryptProtectData(raw, 'Cursiv owner release signing', None, None, None, 0))
    print('Matching owner key restored for this Windows account.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    signer = sub.add_parser('sign')
    signer.add_argument('--version', required=True); signer.add_argument('--commit', required=True)
    signer.add_argument('--output', required=True); signer.add_argument('assets', nargs='+')
    recovery = sub.add_parser('backup'); recovery.add_argument('output')
    restore_parser = sub.add_parser('restore'); restore_parser.add_argument('source')
    verifier = sub.add_parser('verify')
    verifier.add_argument('--manifest', required=True); verifier.add_argument('--version', required=True)
    verifier.add_argument('assets', nargs='+')
    args = parser.parse_args()
    if args.command == 'init': initialize()
    elif args.command == 'backup': backup(args.output)
    elif args.command == 'restore': restore(args.source)
    elif args.command == 'verify':
        envelope = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
        for name in args.assets:
            print(Path(name).name, identity.verify_file(name, envelope, args.version))
    else: sign(args.version, args.commit, args.assets, args.output)

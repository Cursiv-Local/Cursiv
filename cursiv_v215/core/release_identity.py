"""Owner release authentication. The public key ships with the application."""
import base64
import hashlib
import json
from pathlib import Path
import re

KEY_FILE = Path(__file__).with_name('release_public_key.json')


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def public_identity():
    data = json.loads(KEY_FILE.read_text(encoding='utf-8'))
    raw = base64.b64decode(data['public_key'], validate=True)
    if data.get('algorithm') != 'Ed25519' or len(raw) != 32 or hashlib.sha256(raw).hexdigest() != data.get('key_id'):
        raise ValueError('Invalid pinned owner identity')
    return data


def verify_manifest(envelope, version, filename):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    identity = public_identity()
    if not isinstance(envelope, dict) or envelope.get('key_id') != identity['key_id']:
        raise ValueError('Release owner identity does not match the installed trusted key')
    payload = envelope.get('signed')
    if not isinstance(payload, dict) or payload.get('format') != 'cursiv-owner-release-1' or payload.get('version') != version:
        raise ValueError('Release version or signed manifest format does not match')
    if not re.fullmatch(r'[0-9a-f]{40}', str(payload.get('source_commit', ''))):
        raise ValueError('Signed source commit is invalid')
    Ed25519PublicKey.from_public_bytes(base64.b64decode(identity['public_key'], validate=True)).verify(
        base64.b64decode(envelope['signature'], validate=True), canonical(payload))
    item = payload.get('assets', {}).get(filename)
    if (not isinstance(item, dict) or type(item.get('size')) is not int or not 0 < item['size'] <= 1_000_000_000
            or not re.fullmatch(r'[a-f0-9]{64}', str(item.get('sha256', '')))):
        raise ValueError('Installer is not covered by the signed owner manifest')
    return item


def verify_file(path, envelope, version):
    path = Path(path)
    item = verify_manifest(envelope, version, path.name)
    if path.stat().st_size != item['size']:
        raise ValueError('Installer size differs from owner-signed metadata')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != item['sha256']:
        raise ValueError('Installer hash differs from owner-signed metadata')
    return dict(status='OwnerSignatureValid', key_id=public_identity()['key_id'], sha256=digest)

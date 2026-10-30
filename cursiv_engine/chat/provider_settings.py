"""Non-secret provider preferences plus device-bound credentials.

The credential file is outside portable workspaces. DPAPI/Keychain failure is
session-only, never plaintext-on-disk. This module does not migrate owner keys.
"""
import base64
import json
import os
from pathlib import Path
import sys
import threading

from cursiv_engine.core import atomic, keystore
from cursiv_engine.core.paths import APP_DATA
from .provider_registry import get

FILE = APP_DATA / 'provider_manager.json'
CREDENTIALS = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'Cursiv' / 'provider-credentials.json'
_lock = threading.RLock()
_session: dict[str, str] = {}


def _read(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def load():
    data = _read(FILE)
    # An upgrade cannot opt a user into cloud routing.
    return {'mode': 'local_auto', 'provider': 'ollama', 'model': 'qwen3:4b-instruct', **data}


def update(**values):
    allowed = {'mode', 'provider', 'model', 'endpoints', 'models', 'statuses', 'cloud_authorized', 'local_only_projects'}
    if set(values) - allowed:
        raise ValueError('Unknown provider setting')
    with _lock:
        data = load()
        data.update(values)
        FILE.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_text(FILE, json.dumps(data, ensure_ascii=False, indent=2))


def select(mode, provider='ollama', model=''):
    if mode not in ('local_auto', 'cloud_auto', 'manual'):
        raise ValueError('Unknown routing mode')
    get(provider)
    update(mode=mode, provider=provider, model=model)


def save_key(provider, value):
    get(provider)
    if not isinstance(value, str) or any(c in value for c in '\r\n\x00'):
        raise ValueError('Invalid credential')
    with _lock:
        data = _read(CREDENTIALS)
        if provider == 'custom':
            data['custom_origin'] = endpoint(provider).get('url', '')
        if not value:
            data[provider] = ''  # tombstone suppresses an older legacy config key
            _session.pop(provider, None)
        else:
            protected = None
            try:
                if sys.platform == 'win32':  # also on portable: key stays on this device
                    protected = 'dpapi:' + base64.b64encode(keystore._crypt(value.encode('utf-8'), True)).decode('ascii')
                elif sys.platform == 'darwin':
                    item = keystore._keychain_put(value)
                    if item:
                        protected = 'keychain:' + item
            except Exception:
                protected = None
            if protected is None:
                _session[provider] = value
                data[provider] = ''
            else:
                data[provider] = protected
                _session.pop(provider, None)
        CREDENTIALS.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_text(CREDENTIALS, json.dumps(data))
        legacy_file=APP_DATA/'config.json'
        legacy=_read(legacy_file)
        field=get(provider).credential
        if field and field in legacy:
            legacy.pop(field)
            atomic.write_text(legacy_file,json.dumps(legacy,indent=2))
        statuses = load().get('statuses', {})
        statuses.pop(provider, None)
        update(statuses=statuses)
        return 'Saved for this session only; secure OS storage unavailable.' if provider in _session else 'Saved in device credential storage.'


def key(provider):
    data = _read(CREDENTIALS)
    if provider == 'custom' and provider in data and data.get('custom_origin') != endpoint(provider).get('url', ''):
        return ''
    if provider in _session:
        return _session[provider]
    if provider in data:
        return keystore.reveal(data[provider])
    # Read-only compatibility with encrypted legacy credentials. Do not import
    # chat.keys here: its historical import-time migration writes config.json.
    field = get(provider).credential
    return keystore.reveal(_read(APP_DATA / 'config.json').get(field, '')) if field else ''


def has_override(provider):
    return provider in _session or provider in _read(CREDENTIALS)


def endpoint(provider):
    return load().get('endpoints', {}).get(provider, {})


def configure_endpoint(provider, *, url, model='', name='', timeout=60):
    with _lock:
        if provider not in ('ollama', 'lmstudio', 'custom'):
            raise ValueError('This provider has a fixed API origin')
        from .provider_http import validate_endpoint
        url, local = validate_endpoint(provider, url)
        settings = load().get('endpoints', {})
        # Replacing an origin invalidates the custom credential before transmission.
        if provider == 'custom' and endpoint(provider).get('url') != url:
            save_key(provider, '')
        settings[provider] = dict(url=url, model=model, name=name[:80], timeout=max(2, min(float(timeout), 300)), local=local)
        update(endpoints=settings)


def authorize_cloud(provider, enabled):
    if get(provider).local:
        raise ValueError('Local provider cannot be a cloud automatic candidate')
    values = set(load().get('cloud_authorized', []))
    values.add(provider) if enabled else values.discard(provider)
    update(cloud_authorized=sorted(values))


def project_local_only(workspace, enabled=None):
    import hashlib
    if not workspace:
        return False
    identity = hashlib.sha256(os.path.normcase(str(Path(workspace).resolve())).encode('utf-8')).hexdigest()
    values = set(load().get('local_only_projects', []))
    if enabled is not None:
        values.add(identity) if enabled else values.discard(identity)
        update(local_only_projects=sorted(values))
    return identity in values

"""Explicit workspace selection, persisted separately from credentials/settings."""
from __future__ import annotations

import json
import hashlib
import socket
import threading
from pathlib import Path

from . import atomic, file_access, paths

_lock = threading.RLock()


def config_file() -> Path:
    return paths.APP_DATA / 'workspace_access.json'


def _read() -> dict:
    try:
        value = json.loads(config_file().read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {'version': 1, 'users': {}}
    if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('users'), dict):
        raise ValueError('Invalid workspace configuration; select a workspace explicitly')
    return value


def _host() -> str:
    return hashlib.sha256(socket.gethostname().encode('utf-8')).hexdigest()


def load(person: str) -> tuple[str, bool, str]:
    try:
        with _lock:
            settings = _read()['users'].get(person, {})
            if not isinstance(settings, dict):
                raise ValueError('Invalid workspace grant')
            if settings.get('workspace'):
                if paths.portable_root() and not settings['workspace'].startswith('portable://') and settings.get('host') != _host():
                    raise PermissionError('This external workspace was authorized on another computer; select it explicitly here')
                root = file_access.workspace_root(paths.resolve_reference(settings['workspace']))
                return str(root), settings.get('enabled') is True, ''
            portable = paths.portable_root()
            if portable:
                return str(file_access.workspace_root(portable / 'Workspace')), True, ''
            return '', False, ''
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return '', False, f'{type(exc).__name__}: {exc}'


def save(person: str, root: str, enabled: bool) -> str:
    resolved = file_access.workspace_root(root)
    with _lock:
        settings = _read()
        settings['users'][person] = dict(workspace=paths.save_reference(resolved), enabled=bool(enabled), host=_host())
        payload = json.dumps(settings, ensure_ascii=False, indent=2)
        atomic.write_text(config_file(), payload)
        if config_file().read_text(encoding='utf-8') != payload:
            raise OSError('Workspace configuration could not be verified')
    return str(resolved)

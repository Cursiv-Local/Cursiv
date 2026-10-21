"""Stable identity configuration and observed operational context, without inference."""
from datetime import datetime
import json
from pathlib import Path
import re
from . import state_store

DEFAULTS = dict(version=1, name='Cursiv', adapt_style=True, context=True,
                principles=['Be clear and accurate', 'Distinguish evidence from inference',
                            'Respect permissions and privacy', 'Do not invent experiences or recollections'])


def path(person: str) -> Path:
    return Path.home() / '.cursiv' / 'presence' / (re.sub(r'[^a-z0-9_-]', '_', person.lower()) + '.json')


def settings(person: str) -> dict:
    data = state_store.load(path(person), {})
    if not isinstance(data, dict) or any(k in data and not isinstance(data[k], bool)
                                           for k in ('adapt_style', 'context')):
        raise ValueError('Invalid presence preferences')
    return dict(DEFAULTS, **data)


def configure(person: str, **changes) -> None:
    if set(changes) - {'adapt_style', 'context'} or any(type(v) is not bool for v in changes.values()):
        raise ValueError('Unknown presence setting')
    with state_store.LOCK:
        state_store.save(path(person), dict(settings(person), **changes))


def snapshot(workspace: str = '', file_access: bool = False) -> dict:
    from .paths import portable_root
    from . import netgate
    root = portable_root()
    return dict(observed_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                offline=netgate.is_offline(), portable=bool(root),
                storage_available=root.exists() if root else None,
                authorized_workspace=workspace if file_access else None,
                file_access=bool(file_access), field_retrieval='application-controlled',
                limitations=['No observation while closed', 'Model output is not verified evidence',
                             'A configured path alone does not prove data is readable'])


def prompt(person: str, workspace: str = '', file_access: bool = False) -> str:
    cfg = settings(person)
    if not cfg['context']:
        return ''
    return ('\nOperational observations (not personal experiences):\n' +
            json.dumps(snapshot(workspace, file_access), ensure_ascii=False) +
            '\nPresentation preferences never override evidence, permissions or safety. '
            'A failed lookup is unknown, not a remembered event. Do not claim continuous activity.\n')

"""Atomic deferred read-only tasks with explicit, recoverable execution outcomes.

Enqueuing text grants no tools/network. A deliberate flush is local-only.
Legacy records and task history are preserved; damage fails closed.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import threading
import time
import uuid
from cursiv_engine.core import atomic, private_store, state_store
from cursiv_engine.core.paths import APP_DATA

_QUEUE_FILE = APP_DATA / 'offline_queue.jsonl'
_LOCK = threading.RLock()
STATES = {'pending', 'running', 'succeeded', 'failed', 'blocked', 'cancelled'}
LEASE_SECONDS = 480

@dataclass(frozen=True)
class Outcome:
    status: str
    response: str = ''
    error: str = ''
    uncertain: bool = False

def _now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def _locked():
    """OS releases the byte lock after process death; never held during inference."""
    with _LOCK:
        state_store.checked(_QUEUE_FILE)
        lock_path = state_store.checked(_QUEUE_FILE.with_suffix('.lock'))
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('a+b') as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)

def _read():
    try:
        if _QUEUE_FILE.stat().st_size > state_store.MAX_BYTES * 2:
            raise ValueError('Queue exceeds safe read limit; existing data preserved.')
        text = private_store.read_text(_QUEUE_FILE)
    except FileNotFoundError:
        return []
    rows, ids = [], set()
    for line in text.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in ids or not isinstance(row.get('prompt'), str):
            raise ValueError('Damaged or duplicate queue entry; no tasks dispatched or rewritten.')
        ids.add(row['id'])
        old = row.get('status')
        if old in ('queued', 'fired', 'error'):
            row['legacy_status'] = old
            row['status'] = 'blocked'
            row['error'] = 'Legacy task needs explicit review/retry; old fired text is not proof of execution.'
            row['uncertain'] = old == 'fired'
        if row.get('status') not in STATES or not isinstance(row.get('history', []), list):
            raise ValueError('Unsupported queue state; no tasks dispatched or rewritten.')
        rows.append(row)
    return rows

def _save(rows):
    text = ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in rows)
    if len(text.encode()) > state_store.MAX_BYTES:
        raise ValueError('Queue exceeds safe storage budget; archive history before continuing.')
    atomic.write_text(_QUEUE_FILE, text)

def _set(row, status, **detail):
    row.setdefault('history', []).append(dict(at=_now(), previous=row['status'], status=status, error=detail.get('error', '')))
    row.update(status=status, updated=_now(), **detail)

def enqueue(prompt, tags=None, note=''):
    from .workflow import identity
    prompt = prompt.strip()
    if not prompt or len(prompt) > 4000:
        raise ValueError('Queue tasks need a non-empty prompt of at most 4000 characters.')
    entry = dict(id=uuid.uuid4().hex, timestamp=_now(), prompt=prompt, tags=tags or [], note=note,
                 status='pending', owner=list(identity()), authorization='local-read-only-v1', history=[])
    with _locked():
        rows = _read()
        rows.append(entry)
        _save(rows)
    return entry

def history():
    with _locked():
        return _read()

def list_queued():
    return [r for r in history() if r['status'] == 'pending']

def count():
    return len(list_queued())

def cancel(task_id):
    with _locked():
        rows = _read()
        row = next(r for r in rows if r['id'] == task_id)
        if row['status'] in ('pending', 'running', 'blocked', 'failed'):
            _set(row, 'cancelled', uncertain=row['status'] == 'running' or row.get('uncertain', False),
                 error='Cancelled explicitly; no completion is claimed.')
            _save(rows)
        return row

def retry(task_id, *, reconciled=False):
    from .workflow import identity
    with _locked():
        rows = _read()
        row = next(r for r in rows if r['id'] == task_id)
        if row['status'] in ('running', 'pending', 'succeeded'):
            raise ValueError('Task is already active or completed; retry refused.')
        if row.get('uncertain') and not reconciled:
            raise ValueError('Outcome is uncertain. Reconcile previous effects before retrying with --reconciled.')
        _set(row, 'pending', owner=list(identity()), authorization='local-read-only-v1', uncertain=False, error='')
        _save(rows)
        return row

def active(task_id, execution):
    with _locked():
        row = next((r for r in _read() if r['id'] == task_id), {})
        return row.get('status') == 'running' and row.get('execution') == execution

def flush(executor, *, cancel_event=None, limit=5):
    """Durably claim bounded tasks, execute outside lock, persist explicit outcomes.

    Expired running leases are uncertain and require reconciliation, never silently
    redispatched. Strings/empty/error-shaped responses cannot establish success.
    """
    from .workflow import identity
    results = []
    with _locked():
        rows = _read()
        changed = False
        for row in rows:
            if row['status'] == 'running' and row.get('lease_until', 0) < time.time():
                _set(row, 'blocked', uncertain=True, error='Interrupted execution; reconcile before retry.')
                changed = True
        if changed:
            _save(rows)
        ids = [r['id'] for r in rows if r['status'] == 'pending'][:max(0, min(limit, 5))]
    for task_id in ids:
        if cancel_event and cancel_event.is_set():
            break
        with _locked():
            rows = _read()
            row = next(r for r in rows if r['id'] == task_id)
            if row['status'] != 'pending':
                continue
            if row.get('authorization') != 'local-read-only-v1' or row.get('owner') != list(identity()):
                _set(row, 'blocked', error='Person/workspace or permission changed; review and retry explicitly.')
                _save(rows)
                results.append(dict(row))
                continue
            execution = uuid.uuid4().hex
            _set(row, 'running', execution=execution, lease_until=time.time() + LEASE_SECONDS, error='')
            _save(rows)
            claimed = dict(row)
        try:
            outcome = executor(claimed)
            if not isinstance(outcome, Outcome) or outcome.status not in ('succeeded', 'failed', 'blocked', 'cancelled'):
                outcome = Outcome('failed', error='Executor returned no explicit execution outcome.')
            if outcome.status == 'succeeded' and (not outcome.response.strip() or outcome.error or outcome.response.lstrip().lower().startswith(('error:', '[error', '[flush requires', '[ollama unavailable'))):
                outcome = Outcome('failed', error='Executor returned an empty or error-shaped result.')
        except Exception as exc:
            outcome = Outcome('blocked', error=f'{type(exc).__name__}: {exc}; reconcile before retry.', uncertain=True)
        with _locked():
            rows = _read()
            row = next(r for r in rows if r['id'] == task_id)
            if row['status'] == 'running' and row.get('execution') == execution:
                if cancel_event and cancel_event.is_set():
                    outcome = Outcome('cancelled', error='Cancelled before completion could be accepted.')
                if row.get('owner') != list(identity()):
                    outcome = Outcome('blocked', error='Person/workspace changed; old result rejected.')
                _set(row, outcome.status, response=outcome.response, error=outcome.error, uncertain=outcome.uncertain)
                _save(rows)
            results.append(dict(row))
    return results

def clear_fired():
    """Compatibility: hide successful history, retaining records and all failures."""
    with _locked():
        rows = _read()
        done = [r for r in rows if r['status'] == 'succeeded' and not r.get('archived')]
        for row in done:
            row['archived'] = True
        if done:
            _save(rows)
        return len(done)

def format_queue():
    rows = [r for r in history() if not r.get('archived')]
    return ('[Deferred tasks] ' + str(len(rows)) + ' task(s). Local read-only execution; no unattended network/tools.\n'
            + '\n'.join(f"{r['id']} [{r['status']}] {r['prompt'][:80]}" + (' — ' + r['error'] if r.get('error') else '') for r in rows))

"""Serialize legacy turn state and model requests across application surfaces."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import threading

_SLOT = threading.RLock()
_GUARD = ContextVar('cursiv_active_turn_guard', default=lambda: True)


def check_guard():
    if not _GUARD.get()():
        from .request_budget import Stopped
        raise Stopped('Turn cancelled or conversation/person/workspace changed.')


@contextmanager
def guard(valid):
    token = _GUARD.set(valid)
    try:
        yield
    finally:
        _GUARD.reset(token)


def guarded(generator, valid):
    with guard(valid):
        try:
            check_guard()
            for piece in generator:
                check_guard()
                yield piece
        finally:
            close = getattr(generator, 'close', None)
            if close:
                close()


@contextmanager
def exclusive(check=lambda: None):
    while not _SLOT.acquire(timeout=.1):
        check()
        check_guard()
    try:
        check()
        check_guard()
        yield
    finally:
        _SLOT.release()


def serialized_turn(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        from cursiv_engine.agents.workflow import identity
        from cursiv_engine.memory import semantic
        owner, generation = identity(), semantic._person_revision
        def check():
            if identity() != owner or semantic._person_revision != generation:
                from .request_budget import Stopped
                raise Stopped('Person/workspace changed while this turn was waiting or running.')
        def stream():
            with exclusive(check):
                # Rebuild the legacy verifier's ledger from this supplied conversation only.
                # No previous chat/person's assumption or failed-review state is inherited.
                from cursiv_engine.core import verify
                verify.reset_session()
                history = kwargs.get('history', args[2] if len(args) > 2 else [])
                previous = ''
                for row in history[-8:]:
                    if row.get('role') == 'user':
                        previous = str(row.get('content', ''))
                    elif row.get('role') == 'assistant' and previous:
                        verify.store_ledger_from(previous, str(row.get('content', '')))
                for piece in fn(*args, **kwargs):
                    check()
                    yield piece
        return stream()
    return call


def serialized_work(fn):
    """One-shot command cascades share the turn slot without resetting its verifier."""
    @wraps(fn)
    def call(*args, **kwargs):
        from cursiv_engine.agents.workflow import identity
        from cursiv_engine.memory import semantic
        owner, generation = identity(), semantic._person_revision
        def check():
            from .request_budget import current, Stopped
            budget = current()
            if budget:
                budget.check()
            if identity() != owner or semantic._person_revision != generation:
                raise Stopped('Person/workspace changed; command output rejected.')
        def stream():
            with exclusive(check):
                for chunk in fn(*args, **kwargs):
                    check()
                    yield chunk
        return stream()
    return call

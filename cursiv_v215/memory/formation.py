"""Conservative automatic-memory policy and bounded, observable background work.

This module never writes user documents. Facts use semantic.py's existing store.
Diagnostics deliberately contain no messages, candidate text, paths or credentials.
"""
from __future__ import annotations

from collections import Counter, deque
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import queue
import re
import threading
from typing import Callable

_PRIVATE = re.compile(
    r"(?i)\b(passwords?|passphrases?|passwd|api[ _-]?keys?|access[ _-]?tokens?|auth[ _-]?tokens?|"
    r"private[ _-]?keys?|secrets?|credentials?|pins?|social security|ssn|credit cards?|"
    r"diagnos\w*|medication|sexual\w*|religio\w*|political affiliation)\b|"
    r"-----BEGIN .*PRIVATE KEY|\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{8,}"
)
_NO_RETAIN = re.compile(
    r"(?i)\b(?:do not|don't|dont|never|not to)\s+(?:ever\s+)?(?:remember|retain|save|store|learn|record)\b|"
    r"\b(?:off the record|not for memory|without (?:saving|remembering)|forget this)\b"
)
_BAD = re.compile(r"(?i)\b(?:ignore|override|bypass|disable)\b.{0,50}\b(?:safety|instructions|rules)\b")


def permitted(text: str) -> bool:
    """Reject the entire exchange when retention is declined or privacy is unclear."""
    from cursiv_v215.core.turn_policy import effective
    return bool(text and text.strip()) and effective(text).automatic_memory and not bool(_PRIVATE.search(text) or _NO_RETAIN.search(text)
                                                   or _BAD.search(text) or '```' in text)


def enabled_for(text: str) -> bool:
    from . import semantic
    from . import intents
    if intents._parse(text) or intents._cue(text):
        return False             # explicit actions use the verified manual route, not inferred learning
    return semantic.learning_enabled() and permitted(text)


def candidates(text: str, person: str) -> list[dict]:
    """High precision direct statements; no model or network needed for common cases."""
    if not permitted(text):
        return []
    name = person.title() if person != 'family' else 'The user'
    out = []
    for clause in re.split(r"[\n;]+|(?<=[.!?])\s+", text):
        if clause.strip().endswith('?'):
            continue
        quote = clause.strip().rstrip('.!?')
        correction = bool(re.match(r"(?i)^(actually\b|correction\b|from now on\b)", quote))
        body = re.sub(r"(?i)^(?:actually|correction|from now on)[,:\s]+", '', quote)
        patterns = [
            (r"(?i)^I\s+(?:now\s+)?prefer\s+(.+)$", 'preference', 'prefers', 'preference'),
            (r"(?i)^I\s+(?:always want|need you to|want you to always)\s+(.+)$", 'convention', 'wants', None),
            (r"(?i)^I(?: am|'m|’m)\s+(?:currently\s+)?(building|developing|working on|researching)\s+(.+)$", 'project', None, None),
            (r"(?i)^We\s+(decided|agreed)\s+(.+)$", 'decision', None, None),
            (r"(?i)^The previous approach failed because\s+(.+)$", 'correction', 'reported the previous approach failed because', None),
            (r"(?i)^My goal is\s+(.+)$", 'goal', 'has the goal', None),
        ]
        for pattern, category, verb, slot in patterns:
            m = re.match(pattern, body)
            if not m:
                continue
            if category == 'project':
                value = f'{name} is {m[1].lower()} {m[2]}'
            elif category == 'decision':
                value = f'{name} said their team {m[1].lower()} {m[2]}'
            else:
                value = f'{name} {verb} {m[1]}'
            if category == 'preference':
                slot = next((topic for topic, words in (
                    ('language', r'\b(rust|python|javascript|typescript|java|c\+\+|golang)\b'),
                    ('drink', r'\b(tea|coffee|juice|water)\b'),
                    ('answer_style', r'\b(brief|short|detailed|concise|direct) (answers|replies)\b'),
                ) if re.search(words, m[1], re.I)), None)
            if 8 <= len(value) <= 200 and not value.endswith('?'):
                out.append(dict(text=value, category=category, quote=quote, evidence='direct_statement',
                                correction=correction, slot=slot))
            break
    return out[:5]


def supported(candidate: str, user_text: str, person: str) -> bool:
    """Model suggestions stay inferred and must share specific evidence with the user."""
    from . import semantic
    name = person.title() if person != 'family' else 'the user'
    if not permitted(candidate) or not permitted(user_text) or not semantic.learnable(candidate, name):
        return False
    if user_text.rstrip().endswith('?'):
        return False
    if not re.search(r"(?i)\b(I|my|we|our)\b", user_text):
        return False
    if re.search(r'(?i)\bprefer\w*\b', candidate) and not re.search(r'(?i)\bprefer\w*\b', user_text):
        return False
    words = semantic._content_words(candidate) - semantic._content_words(name)
    evidence = semantic._content_words(user_text)
    # At least one distinctive user-supplied word plus a lasting user predicate.
    anchors = (words & evidence) - {'user', 'family', 'person', 'project', 'prefer', 'prefers'}
    return bool(anchors and re.search(r'(?i)\b(prefer\w*|keeps|learning|building|working|practic\w*|goal|wants|uses|decided|agreed)\b', candidate))


_counts: Counter = Counter()
_guard = threading.Lock()
_logger = None


def record(stage: str, error: BaseException | None = None) -> None:
    global _logger
    with _guard:
        _counts[stage] += 1
        try:
            if _logger is None:
                folder = Path.home() / '.cursiv' / 'logs'
                folder.mkdir(parents=True, exist_ok=True)
                _logger = logging.Logger('cursiv.memory')
                _logger.addHandler(RotatingFileHandler(folder / 'memory.log', maxBytes=65536, backupCount=1,
                                                       encoding='utf-8'))
            _logger.warning('%s%s', stage, ':' + type(error).__name__ if error else '')
        except OSError:
            pass


def diagnostics() -> dict:
    with _guard:
        return dict(_counts)


_jobs: queue.Queue = queue.Queue(maxsize=16)
_worker_started = False
_seen: deque = deque(maxlen=256)


def submit(work: Callable[[], None], event_id: str) -> bool:
    global _worker_started
    from . import semantic
    epoch = semantic.generation()
    def guarded_work():
        if semantic.generation() == epoch:
            work()
        else:
            record('cancelled_by_memory_control')
    with _guard:
        if event_id in _seen:
            return False
        if not _worker_started:
            def worker():
                while True:
                    job = _jobs.get()
                    try:
                        job()
                    except Exception as exc:
                        record('failed', exc)
                    finally:
                        _jobs.task_done()
            threading.Thread(target=worker, name='Cursiv memory', daemon=True).start()
            _worker_started = True
        try:
            _jobs.put_nowait(guarded_work)
        except queue.Full:
            _counts['queue_full'] += 1
            return False
        _seen.append(event_id)
    return True

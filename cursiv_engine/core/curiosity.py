"""Inspectable, per-person investigation journal. Never edits evidence sources."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
from . import state_store

STATUSES = ('Proposed', 'Open', 'Investigating', 'Awaiting evidence', 'Resolved', 'Dismissed', 'Superseded')
ACTIVE = STATUSES[:4]
DEFAULTS = dict(automatic=False, suggestions=False, frequency=5, max_active=5)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def path(person: str) -> Path:
    from . import demo
    root = demo.root() if demo.active() else Path.home() / '.cursiv'
    return root / 'curiosity' / (re.sub(r'[^a-z0-9_-]', '_', person.lower()) + '.json')


def load(person: str) -> dict:
    data = state_store.load(path(person), dict(version=1, settings=dict(DEFAULTS), records=[], events=0))
    if (not isinstance(data, dict) or data.get('version') != 1 or
            not isinstance(data.get('records'), list) or not isinstance(data.get('settings'), dict)):
        raise ValueError('Invalid curiosity journal; data preserved')
    cfg = dict(DEFAULTS, **data['settings'])
    if (type(cfg['automatic']) is not bool or type(cfg['suggestions']) is not bool or
            type(cfg['frequency']) is not int or not 1 <= cfg['frequency'] <= 100 or
            type(cfg['max_active']) is not int or not 1 <= cfg['max_active'] <= 20):
        raise ValueError('Invalid curiosity settings')
    for record in data['records']:
        if (not isinstance(record, dict) or not isinstance(record.get('id'), str) or
                record.get('status') not in STATUSES or not isinstance(record.get('history'), list)):
            raise ValueError('Invalid curiosity record')
        for key in ('project', 'question', 'why', 'investigation', 'classification', 'created', 'reviewed'):
            if not isinstance(record.get(key), str):
                raise ValueError(f'Invalid curiosity record field: {key}')
        if type(record.get('score')) is not int:
            raise ValueError('Invalid curiosity priority')
        for key in ('evidence', 'missing_variables', 'hypotheses', 'resolution'):
            if not isinstance(record.get(key), list):
                raise ValueError(f'Invalid curiosity record field: {key}')
        for ref in record['evidence'] + record['resolution']:
            if not isinstance(ref, dict) or any(not isinstance(ref.get(k), str) for k in
                    ('source', 'id', 'quote', 'digest', 'classification')):
                raise ValueError('Invalid saved evidence reference')
    data['settings'] = cfg
    return data


def configure(person: str, **changes) -> None:
    if set(changes) - set(DEFAULTS):
        raise ValueError('Unknown curiosity setting')
    for key, value in changes.items():
        if key in ('automatic', 'suggestions') and type(value) is not bool:
            raise ValueError('Setting requires true/false')
        if key in ('frequency', 'max_active') and (type(value) is not int or not 1 <= value <= (100 if key == 'frequency' else 20)):
            raise ValueError('Setting out of range')
    with state_store.LOCK:
        data = load(person)
        data['settings'].update(changes)
        data['control_epoch'] = data.get('control_epoch', 0) + 1
        state_store.save(path(person), data)


def reference(source: str, ident: str, text: str, classification: str) -> dict:
    return dict(source=source, id=ident, quote=text[:3000],
                digest=hashlib.sha256(text.encode('utf-8')).hexdigest(), classification=classification)


def normalize(text: str) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', text.lower()))


def add(person: str, project: str, candidate: dict, evidence: list[dict], *, manual: bool = False) -> dict | None:
    """Candidates can reference only records retrieved and validated by the caller."""
    question = str(candidate.get('question', '')).strip()
    if not 8 <= len(question) <= 400:
        raise ValueError('Question must be 8–400 characters')
    for key in ('missing_variables', 'hypotheses'):
        values = candidate.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or len(v) > 500 for v in values):
            raise ValueError('Candidate lists require bounded text values')
    refs = candidate.get('refs', [])
    allowed = {(e['source'], e['id']): e for e in evidence}
    if not isinstance(refs, list) or any(not isinstance(r, dict) or (r.get('source'), r.get('id')) not in allowed for r in refs):
        raise ValueError('Unsupported evidence reference')
    if not refs and not manual:
        raise ValueError('Automatic questions require retrieved evidence')
    chosen = [allowed[(r['source'], r['id'])] for r in refs]
    # The score describes selection criteria, never statistical confidence.
    factors = dict(evidence=2 if chosen else 0, testability=int(bool(candidate.get('investigation'))),
                   relevance=1, novelty=1, speculation_penalty=int(bool(candidate.get('hypotheses'))))
    key = normalize(question)
    with state_store.LOCK:
        data = load(person)
        for existing in data['records']:
            if existing['project'] != project:
                continue
            old = set(normalize(existing['question']).split())
            new = set(key.split())
            if normalize(existing['question']) == key or (old and len(old & new) / len(old | new) >= .8):
                return None  # includes dismissed and resolved questions
        if sum(r['project'] == project and r['status'] in ACTIVE for r in data['records']) >= data['settings']['max_active']:
            return None
        if len(data['records']) >= 1000:
            raise ValueError('Journal contains 1000 investigations; export and clear before adding more')
        timestamp = now()
        record = dict(id='CUR-' + uuid.uuid4().hex[:12], project=project, question=question,
            why=str(candidate.get('why', 'Additional evidence is needed.'))[:800],
            evidence=chosen, missing_variables=list(candidate.get('missing_variables', []))[:10],
            hypotheses=list(candidate.get('hypotheses', []))[:5],
            investigation=str(candidate.get('investigation', 'Collect supporting evidence.'))[:1000],
            score=sum(factors.values()) - 2 * factors['speculation_penalty'], score_factors=factors,
            classification='Unknown' if not chosen else 'Inference', created=timestamp,
            reviewed=timestamp, status='Proposed', resolution=[], surfaced=None,
            history=[dict(at=timestamp, status='Proposed', note='Manually created' if manual else 'Validated evidence-based proposal')])
        data['records'].append(record)
        state_store.save(path(person), data)
        return record


def transition(person: str, ident: str, status: str, evidence: list[dict] | None = None) -> None:
    ident = 'CUR-' + ident[4:].lower() if ident.lower().startswith('cur-') else ident
    if status not in STATUSES:
        raise ValueError('Unknown investigation status')
    if status == 'Resolved' and not evidence:
        raise ValueError('Resolution requires supporting evidence; hypotheses alone cannot resolve a question')
    with state_store.LOCK:
        data = load(person)
        record = next((r for r in data['records'] if r['id'] == ident), None)
        if record is None:
            raise ValueError('No such curiosity entry')
        if status in ACTIVE and record['status'] not in ACTIVE and sum(
                r['project'] == record['project'] and r['status'] in ACTIVE for r in data['records']) >= data['settings']['max_active']:
            raise ValueError('Active investigation budget reached')
        record.update(status=status, reviewed=now())
        if status == 'Resolved':
            record['resolution'] = evidence
        record['history'].append(dict(at=now(), status=status, evidence=evidence or []))
        state_store.save(path(person), data)


def _quote(e: dict) -> str:
    """A field record is saved as its JSON snapshot; show it as one notebook line."""
    try:
        row = json.loads(e['quote'])
        if isinstance(row, dict) and 'measurements' in row:
            from .fieldlog import summary
            return summary(row)
    except (ValueError, TypeError, KeyError):
        pass
    return str(e['quote'])


def _listed(items) -> str:
    return '; '.join(str(x) for x in items) if items else 'none'


def render(records: list[dict]) -> str:
    if not records:
        return 'No matching curiosity entries. No journal contents were invented.'
    def one(r):
        last = r['history'][-1] if r['history'] else {}
        return (f"[{r['id']}] {r['status']} · priority {r['score']} (selection score, not probability)\n"
                f"{r['question']}\nWhy: {r['why']}\nNext: {r['investigation']}\n"
                + ''.join(f"- Evidence [{e['source']}:{e['id']}] ({e['classification']}): {_quote(e)}\n" for e in r['evidence'])
                + 'Hypotheses (unverified): ' + _listed(r['hypotheses'])
                + '\nMissing/unknown: ' + _listed(r['missing_variables'])
                + (f"\nLast update: {str(last.get('at', ''))[:16].replace('T', ' ')} · {last.get('note') or last.get('status', '')}"
                   f" ({len(r['history'])} in history)" if last else ''))
    return ('Evidence below is a saved snapshot; use curiosity review <CUR-id> to check current availability.\n\n'
            + '\n\n'.join(one(r) for r in records[:50]))

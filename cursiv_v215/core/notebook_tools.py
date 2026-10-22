"""Application-owned Field Notebook commands. Model prose is never dispatched.

Only user messages supply observation details. The allowlisted interface delegates
to fieldlog, reads the record back, and checks the existing SHA-256 chain before
issuing a receipt. No workspace paths, shell operations or model calls are used.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import re
import threading

from . import fieldlog

CREATE = 'notebook_create_observation'
READ = 'notebook_read_entries'
VERIFY = 'notebook_verify_chain'
TOOLS = frozenset((CREATE, READ, VERIFY))
_lock = threading.RLock()
_FIELDS = {'observer', 'site', 'lat', 'lon', 'location_source', 'location_accuracy_m',
           'location_fix_utc', 'measurements', 'note', 'sample_id'}
_TARGET = r'(?:field\s+(?:notebook(?:\s+section)?|log)|notebook\s+section)'
_REF = re.compile(r'(?i)^(?:it|this|that|this observation|that observation|the observation|the above|those details)$')


@dataclass
class Result:
    tool: str
    status: str
    records: list[dict] = field(default_factory=list)
    error: str = ''
    problems: list[str] = field(default_factory=list)
    count: int = 0

    @property
    def ok(self) -> bool:
        return self.status in ('saved', 'already_recorded', 'read', 'verified')

    def receipt(self) -> dict:
        return dict(asdict(self), ok=self.ok)

    def render(self) -> str:
        if not self.ok:
            return 'Field Notebook — ' + ('details needed: ' if self.status == 'clarification' else 'not confirmed: ') + \
                self.error + (('\n' + '\n'.join(self.problems)) if self.problems else '')
        if self.status in ('saved', 'already_recorded'):
            row = self.records[0]
            lead = 'Saved to the field log:' if self.status == 'saved' else 'Already recorded in the Field Notebook; no duplicate added:'
            return (f"{lead} {fieldlog.summary(row)}\nRecord ID: {row['id']} · "
                    f"fingerprint {row['hash'][:12]} · read-back matched · chain intact.")
        if self.status == 'verified':
            return f'Field Notebook: all {self.count} entries are intact and in order (SHA-256 chain verified).'
        return ('Field Notebook: ' + str(self.count) + ' matching record(s).\n' +
                ('\n'.join('[' + row['id'] + '] ' + fieldlog.summary(row) for row in self.records)
                 if self.records else 'No matching entries were found.'))


def execute(tool: str, args: dict, *, observer: str = '') -> Result:
    """Trusted application interface, not a parser for LLM function-call text."""
    try:
        if tool not in TOOLS:
            raise ValueError('unsupported notebook operation')
        if not isinstance(args, dict):
            raise ValueError('notebook arguments must be an object')
        allowed = {CREATE: {'fields', 'request_id'}, READ: {'words', 'entry', 'sample', 'limit', 'offset', 'start', 'end'}, VERIFY: set()}[tool]
        if args.keys() - allowed:
            raise ValueError('unsupported notebook arguments (file paths and permissions are not notebook tools)')
        with _lock:
            problems = fieldlog.verify()
            if problems:
                return Result(tool, 'failed', error='The notebook chain has integrity problems. No append was attempted.', problems=problems)
            if tool == VERIFY:
                problems = fieldlog.photo_problems()
                if problems:
                    return Result(tool, 'failed', error='Notebook photo verification found problems.', problems=problems)
                return Result(tool, 'verified', count=len(fieldlog.entries()))
            if tool == READ:
                from . import field_recall
                result = field_recall.query(**args)
                if result['warnings']:
                    return Result(tool, 'failed', error='Some notebook records could not be validated.', problems=result['warnings'])
                return Result(tool, 'read', records=result['records'], count=result['total'])
            fields = args.get('fields')
            if not isinstance(fields, dict) or fields.keys() - _FIELDS:
                raise ValueError('unsupported observation fields; photos and record corrections use the notebook window')
            fields = dict(fields)
            for key in ('observer', 'site', 'note', 'sample_id', 'location_source', 'location_fix_utc'):
                if key in fields and not isinstance(fields[key], str):
                    raise ValueError(key + ' must be text')
            if not isinstance(fields.get('measurements', []), list) or any(
                    not isinstance(m, dict) or not {'name', 'value'} <= m.keys() or
                    not m.get('name') or m.keys() - {'name', 'value', 'unit'} or
                    not all(isinstance(v, str) for v in m.values()) for m in fields.get('measurements', [])):
                raise ValueError('measurements must contain names, exact text values and units')
            fields['observer'] = fields.get('observer') or observer
            request_id = args.get('request_id', '')
            if not isinstance(request_id, str) or not re.fullmatch(r'[0-9a-f]{64}', request_id):
                raise ValueError('a notebook request identifier is required')
            before = fieldlog.entries()
            old = next((r for r in before if r.get('chat_request_id') == request_id), None)
            if fields.get('sample_id', '').lower() in ('auto', 'new', 'next'):
                fields['sample_id'] = old['sample_id'] if old else fieldlog.new_sample_id(fields.get('site', ''))
            # Compare with the requested fields as well as the backend's receipt:
            # a consistent return value cannot excuse writing different details.
            expected = {k: fields.get(k, '').strip() for k in ('observer', 'site', 'note', 'sample_id')}
            expected.update(lat=fieldlog._coord(fields.get('lat'), -90, 90),
                            lon=fieldlog._coord(fields.get('lon'), -180, 180),
                            measurements=fieldlog._clean_measurements(fields.get('measurements')))
            located = expected['lat'] is not None
            accuracy = fields.get('location_accuracy_m')
            expected.update(location_source=fields.get('location_source', '') if located else '',
                            location_fix_utc=fields.get('location_fix_utc', '') if located else '',
                            location_accuracy_m=round(float(accuracy), 1) if located and accuracy not in (None, '') else None)
            row = fieldlog.add(**fields, request_id=request_id)
            # The returned dict alone is not proof. Read the actual notebook again.
            actual = next((r for r in fieldlog.entries() if r.get('id') == row.get('id')), None)
            problems = fieldlog.verify()
            if (actual != row or actual is None or actual.get('chat_request_id') != request_id
                    or any(actual.get(k) != v for k, v in expected.items())
                    or fieldlog.record_problems(actual) or problems):
                return Result(tool, 'failed', error='Append/read-back verification failed. A record may exist; do not assume it was saved correctly.', problems=problems)
            return Result(tool, 'already_recorded' if old else 'saved', records=[actual], count=1)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return Result(tool, 'failed', error=f'{type(exc).__name__}: {exc}. No successful save is confirmed; a failed append may have left data on disk.')


@dataclass
class _Intent:
    kind: str
    payload: str = ''
    reference: bool = False


def _intent(text: str) -> _Intent | None:
    text = text.strip()
    if re.match(r"(?i)^(?:please\s+)?(?:do not|don't|never)\b", text):
        return None
    text = re.sub(r'(?i)^(?:(?:no|actually|instead|i meant)[,:]?\s+)*(?:please\s+)?', '', text)
    text = re.sub(r'(?i)^(?:(?:can|could|would) you\s+|i (?:want|need) you to\s+)(?:please\s+)?', '', text)
    # Existing exports/imports/reports retain their separate, explicit commands.
    if re.match(r'(?i)^field\s*(?:log|notebook)\s+(?:export|import|share|report|verify\s+\S)', text):
        return None
    if re.fullmatch(r'(?i)(?:field\s*log check|check field log)', text) or re.search(
            rf'(?i)^(?:verify|check|validate)\b.*\b{_TARGET}\b', text):
        return _Intent('verify')
    if re.fullmatch(rf'(?i)(?:show |read |list )?(?:the |my )?{_TARGET}[.?]?', text) or re.search(
            rf'(?i)^(?:show|read|list|retrieve|find|search|what did i record|what is in|what\x27s in)\b.*\b{_TARGET}\b', text):
        return _Intent('read', text)
    if re.search(rf'(?i)^(?:correct|amend|edit|delete|remove|overwrite)\b.*\b(?:{_TARGET}|field observation)\b', text):
        return _Intent('unsupported')
    m = re.match(r'(?i)^(?:record|log|save|add)\s+(?:(?:a|an|this|that|the|my|new)\s+)?field observation\b\s*[:,-]?\s*(.*)$', text)
    if m:
        payload = m[1].strip()
        # An explicit destination suffix is not part of the observation itself.
        payload = re.sub(rf'(?i)\s+(?:to|in|into) (?:the |my )?{_TARGET}[.!]?$', '', payload)
        payload = re.sub(rf'(?i)^(?:to|in|into) (?:the |my )?{_TARGET}\s*[:,-]?\s*', '', payload)
        return _Intent('create', payload)
    m = re.match(rf'(?is)^(?:add|record|save|put|log|write|move|remember)\s*(.*?)\s+(?:to|in|into)\s+(?:the |my )?{_TARGET}\b(.*)$', text)
    if m:
        after = m[2].strip().lstrip(':;,- ').strip()
        # "not a file" corrects the destination; it isn't observation content.
        if re.match(r'(?i)^(?:not\b|instead of\b)', after):
            after = ''
        payload = after or m[1].strip().rstrip('.!?')
        return _Intent('create', payload, not payload or bool(_REF.fullmatch(payload)))
    if re.fullmatch(rf'(?i)(?:in|to|into) (?:the |my )?{_TARGET}(?:,? not .+)?[.!]?', text):
        return _Intent('create', reference=True)
    if text.lower().startswith('log ') and not re.fullmatch(r'(?i)log (?:in|out|off|on|into|me (?:in|out))\b[^;\d]*', text):
        return _Intent('create', text[4:].strip())
    return None


def _detail(text: str) -> str:
    text = re.sub(r'(?i)^(?:actually[, :]+|correction[: ]+|no,\s*)', '', text.strip())
    return re.sub(r'(?i)^(?:field\s+)?observation\s*:\s*', '', text)


def _structured(text: str) -> bool:
    return bool(re.search(r'(?im)(?:^|[;\n])\s*(?:site|observer|note|notes|lat|lon|latitude|longitude|sample(?: id)?)\s*[:=]', text)
                or re.search(r'(?i)\b(?:observed|observation|water temp|pH|dissolved oxygen|transect)\b', text))


def _positive_target(text: str) -> bool:
    for match in re.finditer(rf'(?i)\b{_TARGET}\b|\bfield observation\b', text):
        if not re.search(r'(?i)\b(?:not|instead of|rather than)\s+(?:the |my )?$', text[:match.start()]):
            return True
    return False


def _source(history: list[dict]) -> list[tuple[int, str]]:
    """Resolve references from user-authored observation details, never assistant prose."""
    parts = []
    users = [(i, m['content']) for i, m in enumerate(history) if m.get('role') == 'user' and isinstance(m.get('content'), str)]
    for index, text in reversed(users[-6:]):
        intent = _intent(text)
        if intent:
            if intent.kind != 'create':
                break                    # a different action makes "it" ambiguous
            if intent.kind == 'create' and intent.payload and not intent.reference:
                parts.append((index, _detail(intent.payload)))
                break
            continue
        # Preserve explicitly supplied contents from an earlier misdirected file request.
        m = re.match(r'(?is)^(?:file (?:create|replace)\s+.+?\s+::\s+|(?:write|save|create)\b.+?\b(?:containing|content)\s*:\s*)(.+)$', text)
        if m:
            parts.append((index, _detail(m[1])))
            break
        if not _structured(text):
            break
        parts.append((index, _detail(text)))
    return list(reversed(parts))


def _request(text: str, history: list[dict]) -> _Intent | None:
    intent = _intent(text)
    users = [m for m in history if m.get('role') == 'user' and isinstance(m.get('content'), str)]
    previous = _intent(users[-1]['content']) if users else None
    if intent is None and previous and previous.kind == 'create':
        if not previous.payload and not previous.reference and _structured(text):
            intent = _Intent('create', text)
        elif re.fullmatch(r'(?i)(?:read it back|did you (?:save|record) it\??|where did you save it\??)', text.strip()):
            intent = _Intent('read', reference=True)
    if intent is None:
        # Mentioning the notebook inside explicit file/memory content does not
        # change the destination selected by the person.
        if re.match(r'(?i)^(?:file\s+|remember\s+|save (?:this )?(?:record|memory)\s*:)', text.strip()):
            return None
        if (_positive_target(text)
                and re.search(r'(?i)\b(?:record|add|save|write|put|move|remember)\b', text)):
            return _Intent('clarification')
    return intent


def is_request(text: str, history: list[dict]) -> bool:
    return _request(text, history) is not None


def command(text: str, history: list[dict], *, observer: str = '', scope: str = '') -> Result | None:
    """Route before models. Callers supply a stable conversation ID for retry scope."""
    intent = _request(text, history)
    if intent is None:
        return None
    from .turn_policy import effective, DENIED
    operation = {'read': READ, 'verify': VERIFY}.get(intent.kind, CREATE)
    if effective(text).blocks(operation):
        return Result(operation, 'failed', error=DENIED)
    if intent.kind == 'clarification':
        return Result(CREATE, 'clarification', error='State the observation and native notebook destination explicitly. '
                      'No notebook operation was executed; model text, filesystem paths and memory claims cannot confirm a save.')
    if intent.kind == 'unsupported':
        return Result(CREATE, 'failed', error='Chat cannot edit or delete existing notebook entries. '
                      'Use Field Notebook → Correct selected to append a correction with a reason; the original stays intact.')
    if intent.kind == 'verify':
        return execute(VERIFY, {}, observer=observer)
    if intent.kind == 'read' and not intent.reference:
        entry = re.search(r'(?i)\bentry\s+([0-9a-f]{12}|#?\d+)\b', intent.payload)
        sample = re.search(r'(?i)\bsample\s+([\w.-]+)', intent.payload)
        words = re.search(r'(?i)\bfor\s+(.+?)[.?]?$', intent.payload)
        args = {'entry': entry[1]} if entry else {'sample': sample[1].rstrip('.?')} if sample else {'words': words[1]} if words else {}
        if re.search(r'(?i)\bentry\s+\S+', intent.payload) and not entry:
            return Result(READ, 'failed', error='Supply an actual notebook record identifier or entry number.')
        return execute(READ, args, observer=observer)
    parts = _source(history) if intent.reference else [(len(history), _detail(intent.payload))] if intent.payload else []
    if not parts:
        return Result(CREATE if intent.kind == 'create' else READ, 'clarification',
                      error='Supply the observation details, for example: site: Pond; pH 7.20; note: clear water. No notebook save has been confirmed.')
    try:
        fields = {}
        measurements = {}
        notes = []
        for _, body in parts:
            if len(body) > 16000:
                raise ValueError('observation text exceeds the chat limit')
            parsed = fieldlog.parse(body)
            for key, value in parsed.items():
                if key == 'measurements':
                    for measurement in value:
                        measurements[measurement['name'].casefold()] = measurement
                elif key == 'note':
                    if value:
                        notes.append(value)
                elif value not in ('', None):
                    fields[key] = value
        fields.update(measurements=list(measurements.values()), note='; '.join(notes))
        if fields.get('lat') is not None:
            fields['location_source'] = 'typed'
        prefix = [m['content'] for m in history[:parts[0][0]] if m.get('role') == 'user' and isinstance(m.get('content'), str)]
        request_id = hashlib.sha256(json.dumps([scope, observer, prefix, [p[1] for p in parts]], ensure_ascii=False).encode('utf-8')).hexdigest()
        if intent.kind == 'read':
            rows = fieldlog.entries()
            row = next((r for r in rows if r.get('chat_request_id') == request_id), None)
            if row is None:
                return Result(READ, 'failed', error='No matching native notebook record was found. Earlier model save claims are not evidence.')
            return execute(READ, {'entry': row['id']}, observer=observer)
        return execute(CREATE, dict(fields=fields, request_id=request_id), observer=observer)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return Result(CREATE, 'failed', error=f'{type(exc).__name__}: {exc}. No successful notebook save is confirmed.')

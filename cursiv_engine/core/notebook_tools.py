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
           'location_fix_utc', 'measurements', 'note', 'sample_id', 'project'}
_TARGET = r'(?:field\s+(?:notebook(?:\s+section)?|log)|notebook(?:\s+section)?)'
_REF = re.compile(r'(?i)^(?:it|this|that|this observation|that observation|the observation|the above|those details)$')


@dataclass
class Result:
    tool: str
    status: str
    records: list[dict] = field(default_factory=list)
    error: str = ''
    problems: list[str] = field(default_factory=list)
    count: int = 0
    scope: dict = field(default_factory=dict)      # verify: {code: [records that mention it]}
    filters: dict = field(default_factory=dict)    # read: the actual date/site/sample filters searched

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
            from .feedback import logged_receipt
            return logged_receipt(self.records[0], duplicate=self.status == 'already_recorded')
        if self.status == 'verified':
            if not self.count:
                return 'Field Notebook: no entries were found in this notebook. No saved chain was verified.'
            lines = [f'Field Notebook: all {self.count} entries are intact and in order (SHA-256 chain verified). '
                     + fieldlog.CHECK_MEANS]
            # A scoped check says which records it found; none found is never "verified" (U100 audit).
            for code, rows in self.scope.items():
                if rows:
                    lines.append(f'Records for {code}: {len(rows)}, all inside that verified chain:')
                    lines += ['[' + row['id'] + '] ' + fieldlog.summary(row) for row in rows]
                else:
                    lines.append(f'No records mention {code}, so nothing was checked for it.')
            return '\n'.join(lines)
        # One wording for every notebook lookup (U103): field_recall.render.
        from . import field_recall
        sample, mentions = next(iter(self.scope.items()), ("", []))
        return field_recall.render(dict(records=self.records, total=self.count, warnings=[], more=False, offset=0,
                                        mentions=mentions, sample=sample, filters=self.filters))


def execute(tool: str, args: dict, *, observer: str = '') -> Result:
    """Trusted application interface, not a parser for LLM function-call text."""
    try:
        if tool not in TOOLS:
            raise ValueError('unsupported notebook operation')
        if not isinstance(args, dict):
            raise ValueError('notebook arguments must be an object')
        allowed = {CREATE: {'fields', 'request_id'}, READ: {'words', 'entry', 'sample', 'project', 'corrections', 'limit', 'offset', 'start', 'end', 'site', 'measure'}, VERIFY: set()}[tool]
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
                return Result(tool, 'read', records=result['records'], count=result['total'],
                              scope={result['sample']: result['mentions']} if result.get('mentions') else {},
                              filters=result.get('filters', {}))
            fields = args.get('fields')
            if not isinstance(fields, dict) or fields.keys() - _FIELDS:
                raise ValueError('unsupported observation fields; photos and record corrections use the notebook window')
            fields = dict(fields)
            for key in ('observer', 'site', 'note', 'sample_id', 'project', 'location_source', 'location_fix_utc'):
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
            if fields.get('project', '').strip():
                expected['project'] = fields['project'].strip()
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
    from . import file_requests
    if file_requests.recognizes(text):
        return None  # explicit workspace source/file intent precedes notebook keywords
    if discussion(text):
        return None
    if re.match(r'(?i)^(?:prepare|draft)\s+(?:(?:a|an)\s+)?field observation\b', text):
        return _Intent('card', text)
    if re.match(r"(?i)^(?:please\s+)?(?:do not|don't|never)\b", text):
        return None
    text = re.sub(r'(?i)^(?:(?:no|actually|instead|i meant)[,:]?\s+)*(?:please\s+)?', '', text)
    text = re.sub(r'(?i)^(?:(?:can|could|would) you\s+|i (?:want|need) you to\s+)(?:please\s+)?', '', text)
    if re.match(r'(?i)^(?:find|show|list|retrieve|search|look up)\b', text) and re.search(
            r'(?i)\b(?:my notebook|the notebook|field notebook|field log)\b', text):
        return _Intent('read', text)
    # A labelled sample or project is a notebook lookup, even without the word
    # "notebook". Do not ask a model to guess whether a just-saved record exists.
    if re.match(r'(?i)^(?:find|show|list|retrieve|search|look up|what did i record)\b', text):
        from . import field_recall
        if field_recall.identity_filters(text) and not re.search(r'(?i)\bhistory\b', text):
            return _Intent('read', text)
    if re.match(r'(?i)^(?:what about|where (?:is|are)|do you have|have you recorded|did you save|is there)\b', text):
        from . import field_recall
        if field_recall.identity_filters(text):
            return _Intent('read', text)
    # Existing exports/imports/reports retain their separate, explicit commands.
    if re.match(r'(?i)^field\s*(?:log|notebook)\s+(?:export|import|share|report|correct|verify\s+\S)', text):
        return None
    if re.match(r'(?i)^export\s+(?:the |my )?(?:field\s+)?notebook\b', text):
        return _Intent('export', text)
    if re.fullmatch(r'(?i)(?:field\s*log check|check field log)', text) or re.search(
            rf'(?i)^(?:verify|check|validate)\b.*\b{_TARGET}\b', text) or re.search(
            r'(?i)^(?:verify|check|validate|confirm)\b.*\b(?:integrity|(?:field\s+)?observations?|field records?|'
            r'notebook (?:entries|records))\b', text):
        return _Intent('verify', text)
    # "Show the full correction history for W-001": every entry for that sample, corrections included.
    m = re.search(r'(?i)^(?:show|list|what is|what\'s)\b.*\b(?:correction\s+)?history\b.*?\b(?:for|of)\s+(?:sample\s+)?'
                  r'(' + fieldlog.ID.pattern + r')\b', text)
    if m:
        return _Intent('read', 'sample ' + m[1])
    if re.fullmatch(rf'(?i)(?:show |read |list |see )?(?:the |my )?{_TARGET}[.?]?', text) or re.search(
            rf'(?i)^(?:show|read|list|retrieve|find|search|what did i record|what is in|what\x27s in)\b.*\b{_TARGET}\b', text):
        return _Intent('read', text)
    if re.search(rf'(?i)^(?:correct|amend|edit|delete|remove|overwrite)\b.*\b(?:{_TARGET}|field observation)\b', text):
        return _Intent('unsupported')
    if re.match(r'(?i)^(?:correct|amend|edit|delete|remove|overwrite)\s+(?:the\s+)?'
                r'(?:last|previous|selected)\s+(?:entry|observation)\b', text):
        return _Intent('unsupported')
    m = re.match(r'(?i)^(?:record|log|save|add)\s+(?:(?:a|an|this|that|the|my|new)\s+)?field observation\b\s*[:,-]?\s*(.*)$', text)
    if m:
        payload = m[1].strip()
        # An explicit destination suffix is not part of the observation itself.
        payload = re.sub(rf'(?i)\s+(?:to|in|into) (?:the |my )?{_TARGET}[.!]?$', '', payload)
        payload = re.sub(rf'(?i)^(?:to|in|into) (?:the |my )?{_TARGET}\s*[:,-]?\s*', '', payload)
        if payload and not _explicit(payload):
            return _Intent('card', payload)   # plain words: a confirm card shows how Cursiv read it first (U100 audit)
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


def _explicit(payload: str) -> bool:
    """Written the notebook's own way ("site: …; temp 14.2 C"), so it can be saved as typed.
    Plain sentences go to a confirm card instead (W-001 was saved as "ORION = -742")."""
    return bool(';' in payload or re.search(
        r'(?i)(?:^|[;,]\s*)(?:site|sample(?: id)?|project|note|observation)\s*:', payload))


def discussion(text: str) -> bool:
    """Talking about notebook mechanics never requests a notebook operation."""
    return bool(re.match(r'(?i)^\s*(?:explain|describe|compare|how (?:do|does)|what is the difference)\b', text)
                and re.search(r'(?i)\b(?:notebook|memory|implementation|retrieval)\b', text))


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
    if text.lstrip().startswith(('@', '/')) or re.match(r'(?i)^agents?\s+', text.strip()):
        return None  # explicit profile/agent commands own their notebook scope and evidence budget
    intent = _intent(text)
    users = [m for m in history if m.get('role') == 'user' and isinstance(m.get('content'), str)]
    previous = _intent(users[-1]['content']) if users else None
    if intent is None and previous and previous.kind == 'create':
        if not previous.payload and not previous.reference and _structured(text):
            intent = _Intent('create', text)
        elif re.fullmatch(r'(?i)(?:read it back|did you (?:save|record) it\??|where did you save it\??)', text.strip()):
            intent = _Intent('read', reference=True)
    if intent is None:
        if discussion(text):
            return None
        # Mentioning the notebook inside explicit file/memory content does not
        # change the destination selected by the person.
        if re.match(r'(?i)^(?:file\s+|remember\s+|save (?:this )?(?:record|memory)\s*:)', text.strip()):
            return None
        # "Write a poem about a field notebook left in the rain" is writing, not a save.
        if re.search(r'(?i)\b(?:poem|story|song|haiku|limerick|essay|joke|riddle|rhyme|verse|lyrics|tale|sonnet)s?\b|'
                     rf'\babout (?:a|an|the|my|this) {_TARGET}\b', text):
            return None
        # A plain-words record gets a confirm card from core/notebook_proposals.py instead.
        if re.match(r'(?i)^(?:please\s+)?(?:record|log|save|add)\s+(?:(?:a|an|this|that|the|my|new)\s+)?'
                    r'field observation\b\s*[:,-]?\s*\S', text):
            return _Intent('card', text)
        if (_positive_target(text)
                and re.search(r'(?i)\b(?:record|add|save|write|put|move|remember)\b', text)):
            return _Intent('clarification')
    return intent


def is_request(text: str, history: list[dict]) -> bool:
    return _request(text, history) is not None


def blocked_message(text: str, history: list[dict]) -> str | None:
    """Pure policy refusal: classify user text without calling any notebook API."""
    from .turn_policy import effective, task_text
    intent = _request(task_text(text), history)
    if intent is None:
        return None
    operation = {'read': READ, 'verify': VERIFY}.get(intent.kind, CREATE)
    if effective(text).blocks(operation):
        return ('Corrections are blocked this turn. No action was executed.' if intent.kind == 'unsupported' else
                'This notebook operation is blocked this turn. No action was executed.')
    return None


def command(text: str, history: list[dict], *, observer: str = '', scope: str = '') -> Result | None:
    """Route before models. Callers supply a stable conversation ID for retry scope."""
    from .turn_policy import task_text
    intent = _request(task_text(text), history)
    if intent is None:
        return None
    from .turn_policy import effective, DENIED
    operation = {'read': READ, 'verify': VERIFY}.get(intent.kind, CREATE)
    if effective(text).blocks(operation):
        return Result(operation, 'failed', error=blocked_message(text, history) or DENIED)
    from . import notebook_proposals
    if intent.kind == 'export':
        preview = notebook_proposals.export_request(intent.payload)
        return Result(CREATE, 'preview', error='Export preview only; no files were written.\n' +
            '\n'.join(preview.card_lines()) + ('\n' + '\n'.join(preview.problems) if preview.problems else
                '\nAfter reviewing, approve by sending: ' + preview.command))
    preview = notebook_proposals.confirmation(text) if intent.kind in ('create', 'card', 'clarification') else None
    if preview is not None:
        details = '\n'.join(preview.card_lines())
        return Result(CREATE, 'preview', error='Preview only; nothing has been saved.\n' + details +
                      ('\n' + '\n'.join(preview.problems) if preview.problems else
                       '\nAfter reviewing, approve by sending: ' + preview.command))
    if intent.kind == 'card':
        return None          # allowed: the chat shows a confirm card (core/notebook_proposals.py)
    if intent.kind == 'clarification':
        return Result(CREATE, 'clarification', error='State the observation and native notebook destination explicitly. '
                      'No notebook operation was executed; model text, filesystem paths and memory claims cannot confirm a save.')
    if intent.kind == 'unsupported':
        return Result(CREATE, 'failed', error='Chat cannot edit or delete existing notebook entries. '
                      'Use Field Notebook → Correct selected to append a correction with a reason; the original stays intact.')
    if intent.kind == 'verify':
        result = execute(VERIFY, {}, observer=observer)
        codes = list(dict.fromkeys(m.group(0) for m in fieldlog.ID.finditer(intent.payload or '')))
        if result.ok and codes:
            from . import field_recall
            identities = field_recall.identity_filters(intent.payload)
            for code in codes[:5]:
                result.scope[code] = field_recall.query(**(identities or {'words': code}), limit=50)['records']
        return result
    if intent.kind == 'read' and not intent.reference:
        from . import field_recall
        entry = re.search(r'(?i)\b(?:entry|record(?: id)?)\s+([0-9a-f]{12}|#?\d+)\b', intent.payload)
        words = re.search(r'(?i)\bfor\s+(.+?)[.?]?$', intent.payload)
        args = field_recall.filters_for_request(intent.payload)
        if 'clarification' in args:
            return Result(READ, 'clarification', error=args['clarification'])
        if entry:
            args['entry'] = entry[1]
        elif words and not any(k in args for k in ('words', 'sample', 'project')):
            args['words'] = words[1]
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
        if not (fields['measurements'] or fields['note'] or fields.get('sample_id')):
            return Result(CREATE, 'clarification', error='Missing observation content: supply a measurement, '
                          'note: or observation:. Example: log site: North Creek; temp 14.2 C; observation: clear water. '
                          'No notebook append was attempted.')
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

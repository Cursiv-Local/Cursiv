"""Explicit memory intents and verified backend outcomes; no model acknowledgements.

The deterministic path never calls an LLM or embeddings. A local classifier may
propose a bounded user-text span for an otherwise unresolved explicit request.
Application validation and backend read-back remain mandatory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
import threading

SAVE = 'SAVE_MEMORY'
RECALL = 'RECALL_MEMORY'
UPDATE = 'UPDATE_MEMORY'
FORGET = 'FORGET_MEMORY'
LIST = 'LIST_MEMORIES'
OFF = 'DISABLE_AUTO_MEMORY'
ON = 'ENABLE_AUTO_MEMORY'
STATUS = 'MEMORY_STATUS'
OPERATIONS = frozenset((SAVE, RECALL, UPDATE, FORGET, LIST, OFF, ON, STATUS))
_lock = threading.RLock()
_pending: dict[tuple, tuple] = {}


@dataclass
class Action:
    operation: str
    content: str = ''
    query: str = ''
    reference: bool = False
    form: str = 'remember'
    period: str = ''


@dataclass
class Outcome:
    operation: str
    ok: bool
    message: str
    records: list[dict] = field(default_factory=list)
    status: str = ''


@dataclass
class Result:
    outcomes: list[Outcome] = field(default_factory=list)
    clarification: str = ''

    @property
    def ok(self):
        return bool(self.outcomes) and all(o.ok for o in self.outcomes) and not self.clarification

    def render(self):
        return '\n\n'.join([o.message for o in self.outcomes] + ([self.clarification] if self.clarification else []))

    def receipt(self):
        return dict(asdict(self), domain='memory', ok=self.ok)


_REF = re.compile(r'(?i)^(?:this|that|it|these|this information|that information|this record|these details|'
                  r'what I (?:just )?told you|what I said|what I told you|that last decision|the last decision|'
                  r'the measurement we discussed|the last measurement|that measurement)$')
_DISCUSSION = re.compile(r'(?i)^(?:["\x27`>]|how (?:does|do)|why (?:did|do|would)|what (?:if|would)|'
                         r'imagine|suppose|for example|example:|explain|tell me how|if I|someone (?:says|said))\b')


def _clean(body: str) -> str:
    from . import semantic
    body = re.sub(r'(?i)^(?:(?:permanently|manually|durably|for next time)\b\s*[:,]?\s*)+', '', body.strip())
    body = re.sub(r'(?i)^that\s+', '', body)
    return semantic._record_text(body)


def _parse(text: str) -> list[Action] | None:
    t = text.strip()
    if not t or _DISCUSSION.search(t):
        return None
    t = re.sub(r'(?i)^(?:please\s+|(?:can|could|would) you\s+)', '', t)
    # Split only when a second explicit operation follows; content containing
    # "then" or "and" is otherwise retained as content.
    parts = re.split(r'(?i)(?:,?\s+(?:and )?then\s+|,\s*(?:and\s+)?)(?=(?:remember|save|store|disable|enable|turn|stop)\b)', t)
    if len(parts) > 1:
        parsed = [_parse(p) for p in parts]
        return [a for group in parsed for a in group] if all(parsed) and len(parts) <= 4 else None
    low = t.lower().rstrip('.!?')
    if low == 'save this':
        return None              # existing Saved Notes action: anchor the previous exchange
    if low == 'memory status':
        return [Action(STATUS)]
    m = re.fullmatch(r'(?is)what (?:do|can) you remember(?:\s+(?:from|over|during))?\s+(.+?)[.!?]?$', t)
    if m and re.match(r'(?i)(?:the )?(?:past|passed|last|today|yesterday|between|\d{4}-\d{2}-\d{2})\b', m[1]):
        return [Action(RECALL, period=m[1].strip())]
    m = re.fullmatch(r'(?is)what (?:do|can) you remember about (.+?)[.!?]?$', t)
    if m and m[1].lower() != 'me':
        return [Action(RECALL, query=m[1])]
    if low in ('memory learn off', 'disable auto memory', 'disable automatic memory', 'turn off automatic memory',
               'stop learning from our conversations', 'stop learning from conversations'):
        return [Action(OFF)]
    if low in ('memory learn on', 'enable auto memory', 'enable automatic memory', 'turn on automatic memory',
               'start learning from our conversations', 'start learning from conversations'):
        return [Action(ON)]
    if low in ('memory', 'memories', 'list memories', 'list my memories', 'show my memories',
               'what do you remember', 'what do you remember about me', 'show saved memories'):
        return [Action(LIST)]
    m = re.fullmatch(r'(?is)(?:actually[, ]+)?(my\s+.+?)\s*,?\s+not\s+(.+?)[.!]?$', t)
    if m:
        return [Action(UPDATE, content=m[1].strip().rstrip(','), query=m[2].strip().rstrip('.!'))]
    m = re.fullmatch(r'(?is)(?:update|correct|change)\s+(?:the |my )?(?:saved )?memory\s+(.+?)\s+(?:to|with|:)\s*(.+)', t)
    if m:
        return [Action(UPDATE, content=_clean(m[2]), query=m[1].strip())]
    m = re.fullmatch(r'(?is)(?:forget|remove from memory|delete (?:the )?(?:saved )?memory)\s+(.+)', t)
    if m:
        query = m[1].strip().rstrip('.!?')
        return [Action(FORGET, query=query, reference=bool(_REF.fullmatch(query)))]
    m = re.fullmatch(r'(?is)(recall|retrieve|look up|fetch|pull up)\s+(.+)', t)
    if m and (m[1].lower() == 'recall' or re.search(r'(?i)\b(memory|memories|saved|stored|record)\b', m[2])):
        return [Action(RECALL, query=m[2].strip())]
    m = None
    if not m:
        m = re.fullmatch(r'(?is)find\s+(.+\b(?:memory|memories|saved|stored|record)\b.*)', t)
    if m:
        return [Action(RECALL, query=m[1].strip())]
    m = re.fullmatch(r"(?is)(?:remember|don['’]?t forget|do not forget)\s+(.+)", t)
    if m:
        content = _clean(m[1])
        return [Action(SAVE, content=content, reference=bool(_REF.fullmatch(content.rstrip('.!?'))))]
    m = re.fullmatch(r'(?is)(?:save|store|keep|record)\s+((?:this|that|the following|these)'
                     r'(?:\s+(?:record|details|data|information|note|measurement|entry|reading|last decision))?)'
                     r'(?:\s+(?:to|in|into)\s+(?:your |the )?(?:persistent |long[- ]term |saved )?memory)?'
                     r'(?:\s+for (?:next time|future conversations))?\s*[:\-–]\s*(.+)', t)
    if m:
        return [Action(SAVE, content=_clean(m[2]), form='record')]
    m = re.fullmatch(r'(?is)(?:save|store|keep)\s+(.+?)(?:\s+(?:to|in|into)\s+(?:your |the )?memory|\s+for next time)?[.!]?$', t)
    if m:
        body = m[1].strip().rstrip('.!?')
        if _REF.fullmatch(body):
            return [Action(SAVE, content=body, reference=True, form='record')]
    m = re.fullmatch(r'(?is)keep in mind(?: that)?\s+(.+)', t)
    if m:
        return [Action(SAVE, content=_clean(m[1]))]
    return None


def _cue(text: str) -> bool:
    if _DISCUSSION.search(text.strip()):
        return False
    return bool(re.search(r'(?i)^(?:please\s+)?(?:(?:can|could|would) you\s+)?'
        r'(?:remember|recall|forget|don[\x27’]?t forget|do not forget|keep in mind|make a mental note|'
        r'(?:save|store|keep)\b.*\b(?:memory|next time|future conversation|last decision|measurement)|'
        r'(?:disable|enable|turn|stop|start)\b.*\b(?:memory|learning)|'
        r'(?:update|correct|change)\b.*\bmemory)', text.strip()))


def _key(person, scope):
    from . import semantic
    return str(semantic.FACTS_FILE), person, scope


def is_request(text: str, history: list[dict] | None = None, *, person: str = '', scope: str = '') -> bool:
    return bool(_parse(text) or _cue(text) or _key(person, scope) in _pending)


def clear_pending(person: str, scope: str = '') -> None:
    with _lock:
        _pending.pop(_key(person, scope), None)


def _context_candidates(history: list[dict], reference: str) -> list[str]:
    candidates = []
    for row in reversed(history[-12:]):
        if row.get('role') != 'user' or not isinstance(row.get('content'), str):
            continue
        text = row['content'].strip()
        if re.fullmatch(r'(?i)(?:ok(?:ay)?|yes|no|thanks|thank you|sounds good|do it)[.!]?', text):
            continue
        parsed = _parse(text)
        if parsed:
            candidates = [a.content for a in parsed if a.operation == SAVE and a.content and not a.reference]
            if candidates:
                return candidates
            continue
        if text.endswith('?') or _DISCUSSION.search(text) or _cue(text):
            continue
        from cursiv_v215.core import file_access, notebook_tools
        if file_access.is_request(text):
            file_request = file_access._parse(text, [])
            if not file_request or not file_request[2]:
                continue
            text = file_request[2]
        notebook_request = notebook_tools._intent(text)
        if notebook_request:
            if notebook_request.kind != 'create' or not notebook_request.payload or notebook_request.reference:
                continue
            text = notebook_request.payload
        pieces = [p.strip() for p in re.split(r'(?<=[.!?])\s+', text) if p.strip()]
        if re.search(r'(?i)decision', reference):
            pieces = [p for p in pieces if re.search(r'(?i)\b(?:decided|decision|we will|I will|we chose|I chose)\b', p)]
        elif re.search(r'(?i)measurement', reference):
            pieces = [p for p in pieces if re.search(r'\d', p)]
        if pieces:
            return list(dict.fromkeys(pieces))
        if candidates:
            break
    return candidates


def _targets(query: str, person: str) -> list[dict]:
    from . import semantic
    query = query.strip().lower().rstrip('.!?')
    visible = semantic.list_facts(person)
    by_id = [f for f in visible if f.get('id') == query]
    return by_id or [f for f in visible if query and query in f['text'].lower()]


def execute(action: Action, *, person: str) -> Outcome:
    from . import semantic as sem
    try:
        if not isinstance(action, Action) or action.operation not in OPERATIONS:
            raise ValueError('unsupported memory operation')
        op = action.operation
        from cursiv_v215.core import turn_policy
        if turn_policy.current().blocks(op):
            return Outcome(op, False, turn_policy.DENIED, status='denied')
        if op == STATUS:
            from cursiv_v215.core import presence
            state = presence.memory_state(person)
            import json
            return Outcome(op, not state['errors'], 'Persistent local memory status:\n' +
                           json.dumps(state, indent=2) + '\nSelected saved facts can survive restarts. '
                           'This does not retrain the model or establish complete recall.', status='read')
        if op in (OFF, ON):
            enabled = op == ON
            sem.set_learning(enabled)
            if sem.learning_enabled() is not enabled or sem._settings().get('learn') is not enabled:
                raise OSError('automatic-memory setting did not match the requested value')
            message = ("I'll keep learning lasting facts from our conversations." if enabled else
                       "I'll stop learning from conversations. Saved memories stay until you forget them.")
            return Outcome(op, True, message + '\nSetting saved and verified. Manual memory saves remain available.', status='verified')
        if op == LIST:
            records = sem.list_facts(person, repair=False)
            message = ('What I remember (' + str(len(records)) + '):\n' + '\n'.join(
                '- [' + str(f.get('id', 'legacy')) + '] ' + f['text'] + '  (' + sem.fact_subtitle(f) + ')' for f in records[-40:])) if records else \
                "No readable active saved facts are available to this user. To save one: remember <something about you>"
            message += '\nSaved facts only; showing up to 40 active records, not a complete conversation history.'
            unreadable = sem.memory_status()['unreadable']
            if unreadable:
                message += f'\n{unreadable} store line(s) are unreadable; missing facts may still exist.'
            return Outcome(op, True, message, records, 'read')
        if op == RECALL:
            if action.period:
                from . import recall
                try:
                    recall.window(action.period)
                except ValueError as exc:
                    return Outcome(op, False, 'Memory date range needs clarification: ' + str(exc), status='clarification')
                message, records = recall.retrieve(action.period, person)
                return Outcome(op, True, message, records, 'read')
            message = sem._recall_reply(action.query, person, repair=False)
            status = sem.memory_status()
            if status['error']:
                return Outcome(op, False, message, status='failed')
            return Outcome(op, True, message, sem.find(action.query, person, repair=False), 'read')
        if op in (SAVE, UPDATE):
            content = re.sub(r'\s+', ' ', action.content.strip())
            if not 4 <= len(content) <= sem.MAX_FACT:
                raise ValueError(f"it's {len(content)} characters; one saved memory needs 4..{sem.MAX_FACT} characters; save longer information in shorter parts")
            if op == UPDATE:
                targets = _targets(action.query, person)
                if len(targets) != 1:
                    raise ValueError('choose one actual saved memory to correct')
                saved = sem.update_fact(targets[0]['id'], content, person=person)
                duplicate = False
            else:
                saved = sem.add_fact(content, person=person, source='manual', exact=True)
                duplicate = saved is None
                if duplicate:
                    saved = next((f for f in sem.list_facts(person) if f.get('person') == person
                                  and f['text'].casefold() == content.casefold()), None)
            back = next((f for f in sem.list_facts(person) if saved and f.get('id') == saved.get('id')), None)
            if not back or back['text'].casefold() != content.casefold():
                raise OSError('memory read-back did not find the requested contents at the returned record ID')
            if duplicate:
                message = 'Already saved: an identical memory is there (nothing new was written).'
            elif op == UPDATE:
                message = 'Memory corrected and verified: ' + back['text'] + '\nThe previous record is retained as superseded history.'
            elif action.form == 'remember':
                message = "Got it — I'll remember: " + back['text']
            else:
                message = f"Saved to Cursiv's memory on this computer ({back['created']}), exactly as:\n{back['text']}"
            separator = ' ' if action.form == 'remember' and op == SAVE and not duplicate else '\n'
            return Outcome(op, True, message + separator + 'Memory ID: ' + back['id'] + '; saved and verified.',
                           [back], 'already_saved' if duplicate else 'updated' if op == UPDATE else 'saved')
        targets = _targets(action.query, person)
        if not targets:
            return Outcome(op, True, "I couldn't find a memory matching that. Nothing was removed.", status='not_found')
        if len(targets) != 1:
            raise ValueError('choose one actual saved memory to forget')
        gone = sem.forget_selected([targets[0]['id']], person=person)
        remaining = {f['id'] for f in sem.list_facts(person, include_superseded=True)}
        if any(f['id'] in remaining for f in gone):
            raise OSError('memory deletion could not be verified')
        return Outcome(op, True, 'Forgotten:\n' + '\n'.join('- ' + f['text'] for f in gone) +
                       '\nRemoval verified in the memory store.', gone, 'forgotten')
    except OSError as exc:
        if getattr(action, 'operation', '') in (RECALL, LIST, STATUS):
            return Outcome(action.operation, False, 'Saved memory unavailable: ' + type(exc).__name__ +
                           '. This is a storage error, not evidence of no memories.', status='failed')
        return Outcome(getattr(action, 'operation', ''), False, sem._save_error(exc), status='failed')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        if getattr(action, 'operation', '') in (RECALL, LIST, STATUS):
            return Outcome(action.operation, False, 'Saved memory could not be read reliably: ' +
                           type(exc).__name__ + '. The records may still exist.', status='failed')
        return Outcome(getattr(action, 'operation', ''), False, f'Not saved: memory operation not confirmed: {exc}.', status='failed')


def command(text: str, history: list[dict], *, person: str, scope: str = '', classifier=None) -> Result | None:
    try:
        return _command(text, history, person=person, scope=scope, classifier=classifier)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return Result([Outcome('', False, f'Memory operation not confirmed: {type(exc).__name__}: {exc}', status='failed')])


def _command(text: str, history: list[dict], *, person: str, scope: str = '', classifier=None) -> Result | None:
    from . import semantic as sem
    key = _key(person, scope)
    with _lock:
        pending = _pending.get(key)
        if pending and text.strip().lower() in ('cancel', 'never mind', 'nevermind'):
            _pending.pop(key, None)
            return Result(clarification='Memory operation cancelled. No additional change was made.')
        actions = _parse(text)
        if pending and actions:
            _pending.pop(key, None)
        if pending and not actions:
            action, choices = pending
            answer = text.strip().lower().rstrip('.!?')
            pick = {'first': 0, 'the first one': 0, 'second': 1, 'the second one': 1}.get(answer)
            if answer.isdigit():
                pick = int(answer) - 1
            if pick is None:
                pick = next((i for i, v in enumerate(choices) if answer == v.lower()), None)
            if pick is None or not 0 <= pick < len(choices):
                _pending.pop(key, None)
                pending = None
            else:
                action = Action(**asdict(action))
                action.reference = False
                if action.operation == SAVE:
                    action.content = choices[pick]
                else:
                    action.query = choices[pick]
                actions = [action]
                _pending.pop(key, None)
        if actions is None:
            if not _cue(text):
                return None
            from cursiv_v215.core import local_intent
            users = [r['content'] for r in history[-8:] if r.get('role') == 'user' and isinstance(r.get('content'), str)]
            proposal = (classifier or local_intent.classify)(text, users)
            # A classifier can select data, never invent it or authorize deletion,
            # correction, or changing retention from an ambiguous request.
            if (isinstance(proposal, dict) and set(proposal) == {'operation', 'content', 'source'}
                    and proposal.get('operation') in (SAVE, RECALL)
                    and isinstance(proposal.get('content'), str) and proposal.get('source') in users + [text]
                    and proposal['content'] in proposal['source']
                    and not _DISCUSSION.search(proposal['source'])
                    and (proposal['source'] == text or proposal['content'] in _context_candidates(history, 'this'))
                    and not re.search(r'(?i)^(?:please|remember|permanently|manually|make a mental note|keep in mind|save|store|this|that)\b', proposal['content'].strip())):
                actions = [Action(proposal['operation'], content=_clean(proposal['content']), query=proposal['content'])]
            else:
                return Result(clarification='Memory details needed: specify what to remember or recall. No successful memory action is confirmed.')
        result = Result()
        for action in actions:
            from cursiv_v215.core.turn_policy import effective, DENIED
            if effective(text).blocks(action.operation):
                result.outcomes.append(Outcome(action.operation, False, DENIED, status='denied'))
                continue
            if action.reference:
                choices = _context_candidates(history, action.content or action.query)
                if action.operation == FORGET:
                    matched = [r['id'] for content in choices for r in _targets(content, person)]
                    choices = list(dict.fromkeys(matched))
                if len(choices) == 1:
                    action.reference = False
                    if action.operation == SAVE:
                        action.content = choices[0]
                    else:
                        action.query = choices[0]
                else:
                    if choices:
                        _pending[key] = (action, choices)
                        result.clarification = 'Which detail should I ' + ('remember' if action.operation == SAVE else 'forget') + '?\n' + \
                            '\n'.join(f'{i + 1}. {v}' for i, v in enumerate(choices))
                    else:
                        result.clarification = 'Quote the exact detail to remember or forget. Assistant prose and save claims are not user memory evidence.'
                    break
            if action.operation in (UPDATE, FORGET):
                targets = _targets(action.query, person)
                if len(targets) > 1:
                    choices = [r['id'] for r in targets]
                    _pending[key] = (action, choices)
                    result.clarification = 'Choose one saved memory by number or ID:\n' + '\n'.join(
                        f"{i + 1}. {r['id']}: {r['text']}" for i, r in enumerate(targets))
                    break
            result.outcomes.append(execute(action, person=person))
        while len(_pending) > 128:
            _pending.pop(next(iter(_pending)))
        return result

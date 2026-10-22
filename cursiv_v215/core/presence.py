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


def memory_state(person: str) -> dict:
    """Read status without legacy repair, embeddings, writes, or model inference."""
    from cursiv_v215.memory import semantic as sem
    out = dict(supported=True, automatic_learning=None, active_records=None,
               unreadable_records=0, errors=[])
    try:
        cfg = sem._settings()
        learn = cfg.get('learn', True)
        if type(learn) is not bool:
            raise ValueError('Invalid automatic-memory setting')
        out['automatic_learning'] = learn
    except (OSError, ValueError) as exc:
        out['errors'].append('Memory settings unavailable: ' + type(exc).__name__)
    try:
        facts, bad = sem._read_facts()
        out['active_records'] = sum(f.get('person') in (person, sem.SHARED) and
                                    f.get('status', 'active') == 'active' for f in facts)
        out['unreadable_records'] = len(bad)
    except (OSError, ValueError) as exc:
        out['errors'].append('Memory records unavailable: ' + type(exc).__name__)
    return out


def snapshot(workspace: str | None = None, file_access: bool | None = None, *,
             person: str | None = None) -> dict:
    from .paths import portable_root
    from . import netgate, turn_policy
    root = portable_root()
    out = dict(observed_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                offline=netgate.is_offline(), portable=bool(root),
                storage_available=root.exists() if root and turn_policy.current().inspect else None,
                authorized_workspace=workspace if file_access else None,
                file_access=file_access, field_retrieval='application-controlled',
                limitations=['No observation while closed', 'Model output is not verified evidence',
                             'A configured path alone does not prove data is readable'])
    if person is not None and turn_policy.current().inspect:
        out['memory'] = memory_state(person)
    return out


CAPABILITIES = (
    'Cursiv supports persistent local semantic memory and saved conversations across restarts. '
    'Automatic learning, when enabled, stores selected facts; it does not retrain model weights '
    'or remember everything. Manual saves are separate and require a verified backend result. '
    'Memory retrieval is bounded and may miss records. No work or observation occurs while the app is closed. '
    'Local inference can work offline with an installed compatible model; optional online providers exist. '
    'Authorized workspace access permits supported file tools, not unrestricted execution or self-modification. '
    'Code analysis requires actual file reads; a folder listing is not source evidence. '
    'Never claim no persistent memory, perfect recall, exclusive capabilities, or verified actions from prose. '
    'Philosophical claims about awareness are speculation, not operational observations.'
)


def prompt(person: str, workspace: str = '', file_access: bool = False, *, observed=None) -> str:
    from . import turn_policy
    if not turn_policy.current().inspect:
        return '\nCapabilities (no saved preferences or records inspected): ' + CAPABILITIES
    cfg = settings(person)
    if not cfg['context']:
        return ''
    return ('\nOperational observations (not personal experiences):\n' +
            json.dumps(observed if observed is not None else snapshot(workspace, file_access, person=person), ensure_ascii=False) +
            '\nCapabilities: ' + CAPABILITIES +
            '\nPresentation preferences never override evidence, permissions or safety. '
            'A failed lookup is unknown, not a remembered event. Do not claim continuous activity.\n')


def answers_state_question(text: str) -> bool:
    """Only direct operational questions; leave hypotheticals and philosophy conversational."""
    t = text.lower().replace('’', "'")
    if re.search(r'\b(?:if|imagine|suppose|thought experiment|philosoph|conscious|self.aware)\b', t):
        return False
    return bool(re.search(
        r'\b(?:current operational state|am i offline|are you offline|is file access (?:on|off|enabled)|'
        r'what (?:can you do right now|is your current model)|'
        r'what(?:\x27s| is) your current workspace|describe your memory capabilities|'
        r'can you (?:read or write|read and write|observe anything while|keep working.*closed)|'
        r'do you (?:have|support) (?:persistent|semantic|long.term) memory|'
        r'can you analy[sz]e your (?:own )?codebase|'
        r'(?:do|can) you (?:remember|learn) (?:from |across |between )?(?:past |previous )?sessions)\b', t))


def state_answer(observed: dict) -> str:
    offline = observed.get('offline')
    network = ('Offline mode is on; external connections are blocked.' if offline is True else
               'Offline mode is off; that does not establish internet connectivity.' if offline is False else
               'The offline setting is unknown.')
    access, workspace = observed.get('file_access'), observed.get('authorized_workspace')
    files = (f'File access is on for {workspace}. Supported reads and writes are authorized there; '
             'a particular operation still has to succeed.' if access is True and workspace else
             'File access is off.' if access is False else 'Workspace file access is unknown or no destination was supplied.')
    mem = observed.get('memory', {})
    auto = {True: 'on', False: 'off', None: 'unknown'}.get(mem.get('automatic_learning'), 'unknown')
    count = mem.get('active_records')
    memory = ('Cursiv supports persistent local memory across restarts. Automatic learning is ' + auto + '. ' +
              (f'The readable store has {count} active record(s) visible to this user. ' if count is not None else
               'Saved-record availability is unknown. ') +
              'This is saved-fact memory, not complete recall or model retraining.')
    warnings = (' Some memory records/settings are unavailable; no completeness claim is possible.'
                if mem.get('errors') or mem.get('unreadable_records') else '')
    return ('Current application state:\n- ' + network + '\n- ' + files + '\n- ' + memory + warnings +
            '\n- Cursiv cannot observe or keep working while closed.\n'
            'These are application settings and stored-record observations, not evidence that I inspected your documents.')


def contradiction(answer: str, observed: dict) -> str:
    """Correct specific false capability claims, not philosophical positions."""
    fence = re.escape(chr(96) * 3)
    prose = re.sub(fence + r'.*?(?:' + fence + r'|$)', '', answer, flags=re.S)
    prose = re.sub(r'(?m)^\s*>.*$', '', prose).replace('’', "'")
    prose = re.sub(r'[*_]', '', prose)
    sentences = re.split(r'(?<=[.!?])\s+|\n+', prose)
    memory_denials = (
        r"I (?:don't|do not) (?:store|save|retain) anything\b",
        r"I (?:don't|do not|can't|cannot) (?:remember|retain) (?:past|previous) sessions\b",
        r"I (?:have no|don't have|do not have) (?:any )?(?:persistent|semantic|long.term) memory\b",
        r"I (?:don't|do not) (?:remember|store|save) .{0,90}\b(?:after you close|after I close|between sessions|past sessions)\b",
        r"I (?:work|run) .{0,90}\bwithout (?:internet or )?memory\b",
    )
    for sentence in sentences:
        sentence = sentence.lstrip('-• ')
        if re.search(r'(?i)\b(?:unless|without (?:your|user|explicit)|automatically|(?:in|as) (?:my |model )?weights)\b', sentence):
            continue
        if any(re.match(pattern, sentence, re.I) for pattern in memory_denials):
            return 'The model misstated Cursiv’s memory capabilities.\n\n' + state_answer(observed)
        opposite = 'off' if observed.get('file_access') is True else 'on' if observed.get('file_access') is False else ''
        if opposite and re.fullmatch(r'(?:File access is |Reason: File access is )' + opposite +
                                      r'(?: (?:right now|currently))?[.!]?', sentence.strip(), re.I):
            return 'The model contradicted this turn’s file-access setting.\n\n' + state_answer(observed)
    return ''

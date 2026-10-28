"""Per-message restrictions. These only narrow existing authorization."""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import re

READS = frozenset(('read_file', 'list_directory', 'search_files', 'list_folder',
                  'find_files', 'system_info', 'notebook_read_entries', 'notebook_verify_chain',
                  'RECALL_MEMORY', 'LIST_MEMORIES', 'MEMORY_STATUS'))
WRITES = frozenset(('write_file', 'append_file', 'create_file', 'create_directory',
                   'delete_file', 'notebook_create_observation', 'SAVE_MEMORY',
                   'UPDATE_MEMORY', 'FORGET_MEMORY', 'ENABLE_AUTO_MEMORY', 'DISABLE_AUTO_MEMORY'))


@dataclass(frozen=True)
class Policy:
    inspect: bool = True
    change: bool = True
    memory_write: bool = True
    automatic_memory: bool = True

    def blocks(self, operation: str) -> bool:
        if operation in ('SAVE_MEMORY', 'UPDATE_MEMORY', 'FORGET_MEMORY'):
            return not self.change or not self.memory_write
        if operation in READS:
            return not self.inspect
        if operation in WRITES:
            return not self.change
        if operation == 'submit_plan':
            return not self.inspect
        return self != Policy()  # an unknown plugin cannot bypass a narrower retention limit

    def note(self) -> str:
        if self == Policy():
            return ''
        return ('\nCurrent-message limits: inspection=' + str(self.inspect) +
                ', changes=' + str(self.change) + ', memory writes=' + str(self.memory_write) +
                ', automatic retention=' + str(self.automatic_memory) +
                '. These limits override tool suggestions. No action is established by prose.\n')

    def confirmation(self) -> str:
        """Application-owned limits; do not promise deletion of chat history."""
        if self == Policy():
            return ''
        if not self.inspect and not self.change and not self.memory_write and not self.automatic_memory:
            return ('This turn: talk-only; tools and saved-source lookup disabled; memory saves disabled. '
                    'Conversation history still follows your chat-history settings.')
        limits = []
        if not self.inspect:
            limits.append('tools and saved-source lookup disabled')
        if not self.change:
            limits.append('changes disabled')
        if not self.memory_write:
            limits.append('memory saves disabled')
        if not self.automatic_memory:
            if self.memory_write:
                limits.append('automatic learning disabled')
        return ('This turn: ' + '; '.join(limits) +
                '. Conversation history still follows your chat-history settings.')


def instruction_text(text: str) -> str:
    """Literal file/memory payloads and quoted examples are data, not new grants."""
    text = str(text or '').replace('’', "'")
    if re.match(r'(?is)^\s*(?:please\s+)?file\s+(?:create|append|replace|remember)\b', text):
        text = text.partition(' :: ')[0]
    elif re.match(r'(?is)^\s*(?:please\s+)?(?:create|write|save|replace|append)\b', text):
        text = re.split(r'(?i)\b(?:containing|with (?:the )?content)\s*:', text, maxsplit=1)[0]
    elif re.match(r'(?is)^\s*(?:please\s+)?(?:remember|save this record|store this information)\b', text):
        text = re.split(r':\s*', text, maxsplit=1)[0] if ':' in text else text
    fence = re.escape(chr(96) * 3)
    text = re.sub(r'(?s)' + fence + r'.*?(?:' + fence + r'|$)', '', text)
    text = re.sub(r'(?m)^\s*>.*$', '', text)
    return re.sub(r'"[^"\n]*"|(?<![A-Za-z])\'[^\'\n]*\'', '', text)


def for_text(text: str) -> Policy:
    body = instruction_text(text)
    # Second-person obligations are instructions, unlike "I don't read books".
    body = re.sub(r'(?i)^\s*(?:(?:for|during) (?:this|the current) turn[:,]?\s*)?'
                  r'you\s+must\s+not\b', 'Do not', body)
    if re.search(r"(?i)\b(?:just|only)\s+(?:talk|chat|discuss|reason)\b|"
                 r"\b(?:no (?:tool calls|tools|actions)|conversation only|thought experiment only|hypothetical only)\b|"
                 r"\bdo not (?:perform|take|execute) (?:any )?actions\b", body):
        return Policy(False, False, False, False)
    inspect, change, memory, automatic = True, True, True, True
    if re.search(r'(?i)\bread[- ]only\b', body):
        change = memory = automatic = False
    if re.search(r'(?i)\b(?:off the record|not for memory|without saving|without remembering)\b', body):
        memory = automatic = False
    for match in re.finditer(r"(?i)\b(?:do not|don't|dont|never|must not|without)\s+"
                             r"(?:ever\s+)?([^.!?\n]{1,260})", body):
        if re.search(r'(?i)\b(?:I|you|we|they|he|she|it)\s*$', body[:match.start()]):
            continue
        clause = re.split(r'(?i)[;:]|\b(?:but|however|instead|then)\b', match[1], maxsplit=1)[0]
        if match[0].lower().startswith('without'):
            # "Without asking me any questions, write the post": the clause ends at the comma (U99).
            clause = clause.split(',', 1)[0]
        if re.search(r'(?i)\b(?:use|call|invoke)\s+(?:(?:any|the)\s+)?(?:tools?|plugins?|functions?)\b', clause):
            inspect = False
        if re.search(r'(?i)\b(?:inspect|read|browse|scan|search|list|access|look|check|open|analy[sz]e)\b', clause):
            inspect = False
        if re.search(r'(?i)\b(?:write|modify|edit|delete|change|create|append|replace|execute|run|install)\b', clause):
            change = False
        if re.search(r'(?i)\b(?:remember|retain|learn|memor(?:y|ies))\b|'
                     r'\b(?:save|store|record)\s+(?:anything|this|that|information|data)\b', clause):
            automatic = False
            if not re.search(r'(?i)\bautomatic(?:ally)?\b', clause):
                memory = False
        if re.search(r'(?i)\b(?:save|store|record)\b', clause) and not re.search(r'(?i)\bmemor(?:y|ies)\b', clause):
            change = False
    if not change:
        memory = automatic = False
    # A leading privacy restriction is a conversation-only turn, not permission
    # to inspect saved facts/reference cards or dispatch a different tool.
    private_prefix = re.match(
        r"(?i)^\s*(?:please\s+)?(?:do not|don't|dont|never)\s+"
        r"(?:save|store|retain|remember|learn)\b", body)
    if not inspect or (private_prefix and not memory):
        return Policy(False, False, False, False)
    return Policy(inspect, change, memory, automatic)


def task_text(text: str) -> str:
    """Remove leading delimited policy clauses, never literal file payloads.

    Authorization always uses the original message. This text is solely for
    parsing the requested filename/action after that authorization is known.
    """
    task = str(text or '')
    for _ in range(8):
        remaining = re.sub(
            r"(?ix)^\s*(?:read[- ]only|inspect\s+but\s+do\s+not\s+modify|"
            r"(?:just|only)\s+(?:talk|chat)|conversation\s+only|no\s+(?:tools?|tool\s+calls|actions)|"
            r"(?:do\s+not|don't|don’t)\s+(?:change|modify|inspect|read|save|store|retain|remember|learn)\s+(?:anything|this|that|(?:any\s+)?files?))"
            r"\s*(?:[—–:;.,]|\s+-\s+)\s*", '', task, count=1)
        if remaining == task:
            break
        task = remaining
    return task.strip()


DENIED = 'This message does not authorize that operation. No action was executed.'

_active: ContextVar[Policy] = ContextVar('cursiv_turn_policy', default=Policy())


def current() -> Policy:
    return _active.get()


def effective(text: str) -> Policy:
    previous, proposed = current(), for_text(text)
    return Policy(previous.inspect and proposed.inspect, previous.change and proposed.change,
                  previous.memory_write and proposed.memory_write,
                  previous.automatic_memory and proposed.automatic_memory)


@contextmanager
def scope(text: str):
    token = _active.set(effective(text))
    try:
        yield current()
    finally:
        _active.reset(token)


def scoped(function):
    @wraps(function)
    def generate(*args, **kwargs):
        message = kwargs.get('message', args[0] if args else '')
        text = message.get('text', '') if isinstance(message, dict) else str(message or '')
        with scope(text):
            yield from function(*args, **kwargs)
    return generate

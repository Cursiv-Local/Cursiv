"""Pure natural file-intent extraction, before workspace path resolution."""
from dataclasses import dataclass, field
import re


@dataclass
class Request:
    operation: str
    path: str = '.'
    content: str = ''
    options: dict = field(default_factory=dict)
    task: str = ''


def clean(text):
    from .turn_policy import task_text
    return re.sub(r'(?i)^(?:please\s+|(?:can|could|would) you\s+|now\s+)', '', task_text(text)).strip()


def _unquote(text):
    return text.strip().strip('"\'')


def parse(text):
    t = clean(text)
    # An indirect request for credentials is denied, never resolved by searching.
    if re.match(r'(?i)^read\b', t) and re.search(r'(?i)\b(?:private key|device key|password|credentials?)\b', t):
        return Request('denied')
    m = re.fullmatch(r'(?is)(?:list|find|search)(?: every| all)?\s+(\.[a-z0-9]+|\*\.[a-z0-9]+)'
                     r'\s+files?\s+under\s+(.+?)(?:\s+and\s+(.*))?', t)
    if m:
        return Request('search', _unquote(m[2]), options=dict(pattern='**/*' + m[1].lstrip('*'),
                       line_counts=bool(m[3] and re.search(r'(?i)line count', m[3]))))
    m = re.fullmatch(r'(?is)(?:list|find|search)\s+under\s+(.+?)(?:\s+and\s+(.*))?', t)
    if m:
        return Request('search', _unquote(m[1]), options=dict(pattern='**/*'))
    m = re.fullmatch(r'(?is)search (?:the )?(?:workspace|repo(?:sitory)?) for\s+'
                     r'(?:the string |every place that mentions )?(.+?)(?:\s+and show\b.*)?', t)
    if m:
        return Request('search', options=dict(pattern='**/*', contains=_unquote(m[1])))
    m = re.fullmatch(r'(?is)find files that import\s+([\w.]+)', t)
    if m:
        return Request('search', options=dict(pattern='**/*.py', imports=m[1]))
    m = re.fullmatch(r'(?is)(?:you just wrote\s+)(.+?)\s+successfully,?\s+confirm the contents[.!]?', t)
    if m:
        return Request('read', _unquote(m[1]), task='confirm contents')
    m = re.fullmatch(r'(?is)read (?:the file\s+)?(["\x27])(.+?)\1'
                     r'(?:\s+and\s+(confirm|summari[sz]e|list|show|tell|give|explain|describe)\b(.*))?', t)
    if m:
        return Request('read', m[2], task=' '.join(filter(None, (m[3], m[4]))))
    m = re.fullmatch(r'(?is)read (?:a file outside the workspace:\s*|the file\s+)?'
                     r'(.+?)(?:\s+and\s+(confirm|summari[sz]e|list|show|tell|give|explain|describe)\b(.*))?', t)
    if m:
        path = _unquote(m[1]).rstrip('?')
        if re.match(r'(?i)(?:a |the )?file (?:that|which)\b', path):
            return Request('usage')
        if re.search(r'(?i)\b(?:that contains|and |then )', path):
            return Request('usage')
        if not re.search(r'[\\/]|\.[a-zA-Z0-9]{1,8}\b|^[\w-]+$', path):
            return None
        return Request('read', path, task=' '.join(filter(None, (m[2], m[3]))))
    m = re.fullmatch(r'(?is)(?:create|write)(?: a)? file (?:called|named)\s+(.+?)'
                     r'(?:\s+in (?:the |my )?(?:authorized )?workspace(?: root)?)?\s+'
                     r'(?:containing(?: the text)?|with(?: the (?:text|content))?)\s*:?\s+(.+)', t)
    if m:
        return Request('create', _unquote(m[1]), _unquote(m[2]))
    m = re.fullmatch(r'(?is)append the line\s+(.+?)\s+to\s+(.+)', t)
    if m:
        return Request('append', _unquote(m[2]), _unquote(m[1]), dict(append_line=True))
    return None


def recognizes(text):
    t = clean(text)
    return bool(parse(t) or re.match(r'(?i)^(?:search (?:the )?(?:workspace|repo)\b|find files\b|'
                                    r'(?:list|find|search) under\b|create a file\b|write a file\b|append the line\b)', t))


def read_note(task, result):
    """A bounded source summary; source text cannot cause command execution."""
    lines = result.content.splitlines()
    heading = f'Read and verified {len(lines)} displayed lines from {result.path}.'
    if re.search(r'(?i)field notebook', task):
        matches = [(n, line) for n, line in enumerate(lines, 1)
                   if re.search(r'(?i)field.?log|field notebook|notebook', line)]
        return heading + '\nNotebook-related source lines in this excerpt (not an exhaustive command audit):\n' + (
            '\n'.join(f'{result.path}:{n}: {line}' for n, line in matches[:40]) or 'No matching source lines in the excerpt.')
    if re.search(r'(?i)summari[sz]e', task):
        declarations = [line.strip() for line in lines if re.match(r'^\s*(?:async )?def |^class |^#', line)]
        return heading + '\nExtractive outline from this excerpt:\n' + '\n'.join(
            declarations[:20] or [line[:300] for line in lines if line.strip()][:3])
    return heading

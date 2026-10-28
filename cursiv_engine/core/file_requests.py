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
    content_ref: str = ''
    error: str = ''


def clean(text):
    from .turn_policy import task_text
    return re.sub(r'(?i)^(?:please\s+|(?:can|could|would) you\s+|now\s+)', '', task_text(text)).strip()


def _unquote(text):
    text = text.strip()
    if len(text) >= 2 and (text[0], text[-1]) in (('"', '"'), ("'", "'"), ('“', '”'), ('‘', '’')):
        return text[1:-1]
    return text


def reference(text):
    return bool(re.fullmatch(r'(?i)(?:(?:that|this|the) file|(?:(?:the|my) )?(?:field[- ]?)?notes?(?: file)?'
                             r'(?: we just (?:made|created|opened))?)', text.strip().rstrip('?.')))


def _write(text):
    """Extract literal user text or an explicit reference; never generate payloads."""
    short = re.fullmatch(r'(?is)append to\s+(.+)', text)
    if short and (reference(short[1]) or re.search(r'[\\/]|\.[a-z0-9]{1,8}$', _unquote(short[1]), re.I)):
        return Request('append', _unquote(short[1]), options=dict(append_line=True), content_ref='the new measurement')
    # "Add a second line to notes.txt saying Site B, 13.8 C"
    m = re.fullmatch(r'(?is)(?:append|add|write)\s+(?:(?:a|an|another|one more)\s+)?(?:(?:second|third|new|next|last|final)\s+)?'
                     r'line\s+(?:to|at the end of|onto)\s+(.+?)\s+(?:saying|that says|which says|reading|with(?: the text)?)\s*:?\s+(.+)', text)
    if m:
        m = (None, m[2], m[1])
    else:
        m = re.fullmatch(r'(?is)(?:append|add)\s+(?:the line\s+)?(.+?)\s+to\s+(.+)', text)
    if m:
        payload, target = m[1].strip(), m[2].strip().rstrip('?')
        if not (reference(target) or re.search(r'[\\/]|\.[a-z0-9]{1,8}$', _unquote(target), re.I)):
            return None  # notebook/memory actions and "add 1 to 2" have their own routes
        op, options = 'append', dict(append_line=True)
    else:
        m = re.fullmatch(r'(?is)(create|make|write|overwrite)\s+(.+)', text)
        if not m:
            return None
        op, options = ('replace', dict(overwrite=True)) if m[1].lower() == 'overwrite' else ('create', {})
        body = re.sub(r'(?i)^(?:a |an |the )?(?:new )?(?:text )?file (?:called|named)\s+', '', m[2])
        # "a notes file" is an explicit, conventional filename choice.
        body = re.sub(r'(?i)^(?:a |the )?notes file\b', 'notes.txt', body)
        split = re.fullmatch(r'(?is)(.+?)\s+and\s+(?:write|put)\s+(.*?)\s+in(?:to)? it[.!]?', body)
        if not split:
            split = re.fullmatch(r'(?is)(.+?)\s+(?:containing(?: the text)?|with(?: the (?:text|content))?)\s*:?\s*(.*)', body)
        if split:
            target, payload = split[1].strip(), split[2].strip()
        else:
            target, payload = body.strip(), ''
            options['empty_file'] = op == 'create'
        target = re.sub(r'(?i)\s+in (?:the |my )?(?:authorized )?workspace(?: root)?[.!]?$', '', target)
        if not (re.search(r'[\\/]|\.[a-z0-9]{1,8}$', _unquote(target), re.I) or reference(target)):
            # Let older explicit command forms retain their existing parsing.
            if ' :: ' in text or re.search(r'(?i)\bwith (?:that|the same) content', text):
                return None
            if not re.search(r'(?i)\bfile\b', m[2]):
                return None  # e.g. "write a poem with heart" is ordinary conversation
            return Request('usage', error='What should I name the file? For example: Create field-notes.txt with the text: Site A, 14.2 C.')
    if not target:
        return Request('usage', error='Which file should I add this to? Name it or say “that file” after opening it.')
    if not payload and not options.get('empty_file'):
        return Request('usage', error='What text should I write? Include it in the request; no file was changed.')
    literal = _unquote(payload)
    contextual = payload == literal and re.fullmatch(
        r'(?i)(?:the )?(?:new measurement|(?:today[’\x27]s )?(?:site [\w-]+ )?measurement|that content|the same content)', payload)
    return Request(op, _unquote(target), '' if contextual else literal, options,
                   content_ref=payload if contextual else '')


def parse(text):
    t = clean(text)
    # An indirect request for credentials is denied, never resolved by searching.
    if re.match(r'(?i)^read\b', t) and re.search(r'(?i)\b(?:private key|device key|password|credentials?)\b', t):
        return Request('denied')
    # Cursiv never deletes files; say so instead of letting the model pretend it did.
    m = re.fullmatch(r'(?is)(?:delete|remove|erase|trash)\s+(?:the\s+)?(?:file\s+)?(.+?)[.!?]?', t)
    if m:
        target = _unquote(m[1].strip())
        target = re.sub(r'(?i)\s+(?:from|in) (?:the |my )?(?:authorized )?workspace$', '', target)
        if re.search(r'[\\/]|\.[a-z0-9]{1,8}$', target, re.I) or re.fullmatch(r'(?i)(?:that|this|the) file', target):
            return Request('delete', target)
    write = _write(t)
    if write:
        return write
    if re.fullmatch(r'(?i)search (?:(?:the|my) )?(?:workspace|repo(?:sitory)?)(?: for)?[.?]?', t):
        return Request('usage', error='What words should I search for? For example: Search my workspace for temperature or sample.')
    m = re.fullmatch(r'(?is)(?:list|find|search)(?: every| all)?\s+(\.[a-z0-9]+|\*\.[a-z0-9]+)'
                     r'\s+files?\s+under\s+(.+?)(?:\s+and\s+(.*))?', t)
    if m:
        return Request('search', _unquote(m[2]), options=dict(pattern='**/*' + m[1].lstrip('*'),
                       line_counts=bool(m[3] and re.search(r'(?i)line count', m[3]))))
    m = re.fullmatch(r'(?is)(?:list|find|search)\s+under\s+(.+?)(?:\s+and\s+(.*))?', t)
    if m:
        return Request('search', _unquote(m[1]), options=dict(pattern='**/*'))
    m = re.fullmatch(r'(?is)search (?:(?:the|my) )?(?:workspace|repo(?:sitory)?) for\s+'
                     r'(?:the string |every place that mentions )?(.+?)(?:\s+and show\b.*)?', t)
    if m:
        query = m[1].strip()
        terms = re.split(r'\s+or\s+', query, flags=re.I) if _unquote(query) == query else [query]
        options = dict(pattern='**/*')
        options['terms'] = [_unquote(term) for term in terms]
        return Request('search', options=options)
    m = re.fullmatch(r'(?is)find files that import\s+([\w.]+)', t)
    if m:
        return Request('search', options=dict(pattern='**/*.py', imports=m[1]))
    m = re.fullmatch(r'(?is)(?:you just wrote\s+)(.+?)\s+successfully,?\s+confirm the contents[.!]?', t)
    if m:
        return Request('read', _unquote(m[1]), task='confirm contents')
    m = re.fullmatch(r'(?is)(?:show(?: me)? (?:the )?contents of|show(?: me)? what(?:[’\x27]s| is) in|open|what(?:[’\x27]s| is) in)\s+(.+?)[?]?', t)
    if m and m[1].casefold().rstrip('.?!') in ('notes', 'my notes', 'the notes'):
        return None  # the existing saved-notes viewer owns these unqualified requests
    if m and (reference(m[1]) or re.search(r'[\\/]|\.[a-z0-9]{1,8}$', _unquote(m[1]), re.I)):
        return Request('read', _unquote(m[1]))
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
        if not (reference(path) or re.search(r'[\\/]|\.[a-zA-Z0-9]{1,8}\b|^[\w-]+$', path)):
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
    from . import source_inspection
    return bool(source_inspection.is_request(t) or parse(t) or re.match(r'(?i)^(?:search (?:(?:the|my) )?(?:workspace|repo)\b|find files\b|'
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

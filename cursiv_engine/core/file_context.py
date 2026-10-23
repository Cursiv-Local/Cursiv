"""Short-term file references from application receipts and user text, never model prose.

No global or persistent state: the caller supplies this conversation and the current
authorized root. Every candidate still passes the native filesystem boundary.
"""
from pathlib import Path
import re


class Clarify(ValueError):
    pass


def _words(value):
    return re.findall(r'[a-z0-9]+', value.casefold())


def _recent(history, root):
    from . import file_access as fs
    seen = set()
    for row in reversed(history[-30:]):
        if row.get('role') != 'assistant':
            continue
        receipts = row.get('file_receipts', [])
        if not receipts and fs.unverified_claim(str(row.get('content', ''))):
            return
        if not isinstance(receipts, list):
            continue
        for receipt in reversed(receipts):
            if not isinstance(receipt, dict) or receipt.get('domain') != 'filesystem':
                continue
            if receipt.get('verified') is not True or receipt.get('ok') is not True:
                return  # a failed action must not silently point "that file" at an older success
            if receipt.get('operation') not in ('read_file', 'create_file', 'write_file', 'append_file'):
                continue
            try:
                raw = receipt.get('path')
                if not isinstance(raw, str) or not Path(raw).is_absolute():
                    continue
                path = fs.resolve(raw, root)
                if path.is_file() and path not in seen:
                    seen.add(path)
                    yield path
            except (OSError, ValueError):
                continue


def resolve(target, operation, history, root):
    from . import file_access as fs, file_requests
    target = target.strip().rstrip('?')
    # Paths are not prose. Never repair traversal, absolute or protected paths by
    # dropping prefixes or searching for a harmless-looking basename elsewhere.
    if re.search(r'[\\/:]', target) or '..' in Path(target).parts or fs.DENY.search(target):
        return fs.resolve(target, root)
    reference = file_requests.reference(target)
    if operation in ('create', 'replace', 'remember', 'save conversation') and not reference:
        return fs.resolve(target, root)
    direct = fs.resolve(target, root)
    if not reference and direct.is_file():
        return direct
    bare = re.sub(r'(?i)^(?:the|my)\s+', '', target)
    if bare.casefold() == 'file' or re.fullmatch(r'(?i)(?:that|this) file', bare):
        recent = next(_recent(history, root), None)
        if recent:
            return recent
        raise Clarify('Which file do you mean? Name it once, for example: Open field-notes.txt.')
    bare = re.sub(r'(?i)\s+we just (?:made|created|opened)$', '', bare)
    bare = re.sub(r'(?i)\s+file$', '', bare)
    words = _words(Path(bare).stem)
    if not words:
        raise Clarify('Which file do you mean? Give its name.')
    def matches(path):
        name = _words(path.stem)
        return all(word in name for word in words) and (not Path(bare).suffix or path.suffix.casefold() == Path(bare).suffix.casefold())
    # A named reference such as "the notes file" prefers a matching confirmed
    # recent file. Explicit names without an extension must still be unambiguous.
    if reference:
        recent = next((p for p in _recent(history, root) if matches(p)), None)
        if recent:
            return recent
    elif Path(bare).suffix:
        recent = next((p for p in _recent(history, root) if p.name.casefold() == bare.casefold()), None)
        return recent if recent else direct
    result = fs.perform('search_files', dict(directory='.', pattern='**/*', name_terms=words), root)
    if not result.ok:
        raise Clarify(result.render())
    candidates = [fs.resolve(name, root) for name in result.entries]
    candidates = [p for p in candidates if p.is_file() and matches(p)]
    if len(candidates) == 1 and not result.truncated:
        return candidates[0]
    if result.truncated:
        raise Clarify('Filename search reached its limit. Give the filename and subfolder so I can identify the right file.')
    if candidates:
        names = ', '.join(str(p.relative_to(root)) for p in candidates[:5])
        raise Clarify(f'Which file do you mean? Matches: {names}. Give one exact filename.')
    raise Clarify(f'No matching file for “{target}” in this workspace. Give its filename or create it first.')


def content(reference, history):
    """Use an exact user-authored measurement, not a fabricated or tool-read value."""
    from . import file_requests
    rows = history[-30:]
    if re.search(r'(?i)new measurement', reference):
        last = next((i for i in range(len(rows) - 1, -1, -1) if rows[i].get('file_receipts')), -1)
        rows = rows[last + 1:]
    site = re.search(r'(?i)\bsite\s+([\w-]+)', reference)
    for row in reversed(rows):
        if row.get('role') != 'user' or not isinstance(row.get('content'), str):
            continue
        text = row['content'][:8000]
        parsed = file_requests.parse(text)
        if parsed:
            # Only already literal user payloads; commands and references are not measurements.
            text = parsed.content if parsed.operation in ('create', 'append') else ''
            if text and re.fullmatch(r'(?i)(?:that|the same) content', reference):
                return text
        for line in reversed(text.splitlines()):
            if site and not re.search(r'(?i)\bsite\s+' + re.escape(site[1]) + r'\b', line):
                continue
            if re.search(r'(?i)\d+(?:\.\d+)?\s*(?:°?\s*[CF]|m[lL]|liters?|[lL]|cm|mm|kg|ppm|pH)\b', line):
                return line.strip()
    raise Clarify('What measurement should I write? Paste the text here; no file was changed.')

"""Bounded read-only source investigation using the shared workspace boundary.

No code execution or model output participates in discovery, citations or evidence.
Static call references are possibilities, never proof of runtime execution.
"""
from dataclasses import dataclass
import ast
import os
from pathlib import Path
import re
import time

SUFFIXES = frozenset(('.py', '.js', '.mjs', '.ts', '.tsx', '.jsx', '.html', '.css', '.md', '.toml', '.json'))
SKIP = frozenset(('node_modules', '__pycache__', 'venv', '.venv', 'build', 'dist', 'reports',
                  'private', 'test_internals', 'station', 'bench', 'icons', 'installer'))


@dataclass(frozen=True)
class Limits:
    files: int = 24
    depth: int = 4
    calls: int = 48
    characters: int = 120000
    entries: int = 3000
    seconds: float = 15.0

    def __post_init__(self):
        for key, maximum in (('files', 40), ('depth', 8), ('calls', 80), ('characters', 240000), ('entries', 6000)):
            if type(getattr(self, key)) is not int or not 1 <= getattr(self, key) <= maximum:
                raise ValueError('Invalid source inspection limit: ' + key)
        if not 0 < self.seconds <= 30:
            raise ValueError('Invalid source inspection time limit')


def is_request(text: str) -> bool:
    """An investigative action plus code subject, not a bare feature mention."""
    from .turn_policy import task_text
    q = re.sub(r'(?i)^\s*(?:please\s+|(?:can|could|would) you\s+)', '', task_text(text))
    action = re.match(r'(?i)^(?:examine|inspect|analy[sz]e|investigate|trace|find|locate|explain|describe|'
                      r'look (?:at|through)|read)\b', q)
    subject = re.search(r'(?i)\b(?:repo(?:sitory)?|codebase|source(?: code)?|implementation|'
                        r'retrieval code|message[- ]processing pipeline|function calls?|'
                        r'(?:a )?user sends (?:a )?message)\b', q)
    # Explicit simple file reads keep their existing literal-content interface.
    if re.match(r'(?i)^read\s+(?:the file\s+)?[\w./\\-]+\.[a-z0-9]+[.!?]?$', q):
        return False
    return bool(action and subject)


def _terms(question):
    words = set(re.findall(r'[a-z_][a-z0-9_]{2,}', question.lower()))
    words -= {'the', 'and', 'its', 'this', 'that', 'what', 'happens', 'when', 'user', 'sends',
              'examine', 'inspect', 'find', 'trace', 'identify', 'implementation', 'repository', 'source', 'code'}
    if words & {'message', 'processing', 'pipeline'}:
        words.update(('chat', 'send', 'process_message', '_run_turn', 'completion', 'conversation', 'routing',
                      'streaming', 'dispatch', 'local_provider'))
    if words & {'notebook', 'retrieval'}:
        words.update(('notebook', 'fieldlog', 'field_recall', 'retrieve'))
    if 'architecture' in words:
        words.update(('main', 'app', 'architecture', 'chat', 'worker'))
    return words


def investigate(question, root, *, limits=None):
    from . import file_access as fs, turn_policy, evidence_log
    limits = limits or Limits()
    if turn_policy.effective(question).blocks('read_file'):
        return fs.Reply(turn_policy.DENIED)
    if root is None:
        return fs.Reply('File access is off. Choose workspace <folder>, then files on. No source was inspected.')
    try:
        base = fs.workspace_root(root)
    except (OSError, ValueError) as exc:
        return fs.Reply('Source inspection unavailable: ' + str(exc))
    start = time.monotonic()
    terms, paths, scanned, limited = _terms(question), [], 0, False
    # Each discovered directory and file is validated, including linked parents.
    for current, dirs, files in os.walk(base, followlinks=False):
        safe = []
        for name in sorted(dirs):
            if name.startswith('.') or name in SKIP:
                continue
            try:
                fs.resolve(str(Path(current)/name), base)
                safe.append(name)
            except (OSError, ValueError):
                continue
        dirs[:] = safe
        for name in sorted(files):
            scanned += 1
            if scanned > limits.entries or time.monotonic()-start > limits.seconds:
                limited = True
                break
            if name.startswith('.') or name in ('field-notes.txt', 'CURSIV-LEGAL-HANDOFF.md') or Path(name).suffix.lower() not in SUFFIXES:
                continue
            try:
                paths.append(fs.resolve(str(Path(current)/name), base))
            except (OSError, ValueError):
                continue
        if limited:
            break
    hints = set()
    def score(path):
        rel = path.relative_to(base).as_posix().lower()
        value = sum(5 for word in terms if word in path.stem.lower()) + sum(word in rel for word in terms)
        if path.name in ('ARCHITECTURE.md', 'CODE-MAP.md', 'README.md'):
            value += 8
        if path.name in ('ARCHITECTURE.md', 'CODE-MAP.md'):
            value += 30
        if path in hints:
            value += 25
        if path.suffix == '.py':
            value += 2
        if rel.startswith(('tests/', 'docs/')) and path.name not in ('ARCHITECTURE.md', 'CODE-MAP.md'):
            value -= 10
        return (-value, rel)
    pending = [(p, 0) for p in sorted(paths, key=score)]
    candidates = {p.relative_to(base).as_posix(): p for p in paths}
    reads, documents, seen, used, calls = [], [], set(), 0, 0
    failures, edges, targets = [], [], {}
    while pending and len(reads) < limits.files and calls < limits.calls:
        path, depth = pending.pop(0)
        if path in seen:
            continue
        seen.add(path)
        if time.monotonic()-start > limits.seconds:
            limited = True
            break
        calls += 1
        result = fs.perform('read_file', {'path': str(path)}, base)
        reads.append(result)
        if not result.ok:
            failures.append((path.relative_to(base).as_posix(), result.error))
            continue
        if used+len(result.content) > limits.characters:
            limited = True
            break
        used += len(result.content)
        rel = path.relative_to(base).as_posix()
        if path.name in ('ARCHITECTURE.md', 'CODE-MAP.md'):
            # Documentation is a discovery hint, not proof of implementation.
            # Only already-discovered, authorized paths can be promoted.
            for hint in re.findall(r'[\w/.-]+\.(?:py|mjs|js|ts)\b', result.content[:2200]):
                choices = [p for name, p in candidates.items() if name == hint or name.endswith('/'+hint)]
                if len(choices) == 1:
                    hints.add(choices[0])
            pending.sort(key=lambda item: score(item[0]))
        if result.truncated and calls+2 <= limits.calls and len(reads)+1 < limits.files:
            # Search the actual file for task-relevant declarations beyond its head,
            # then read a bounded window with application-owned source offsets.
            needles = ['def '+t for t in sorted(terms) if '_' in t]
            if terms & {'chat', 'pipeline'}:
                needles += ['def chat(', 'def _chat_inner(', 'def _run_turn(', 'def _chat_stream(']
            if terms & {'notebook', 'retrieval'}:
                needles += ['def query(', 'def command(', 'def _request(', 'def execute(']
            if needles:
                calls += 1
                matches = fs.perform('search_files', dict(directory=str(path.parent), pattern=path.name,
                                     terms=needles[:5]), base)
                if matches.ok and matches.entries:
                    found = re.search(r':(\d+):', matches.entries[0])
                    if found and int(found[1]) > len(result.content.splitlines()):
                        calls += 1
                        window = fs.perform('read_file', dict(path=str(path), start_line=int(found[1]), max_lines=200), base)
                        if window.ok and used+len(window.content) <= limits.characters:
                            used += len(window.content)
                            reads.append(window)
                            result = window
        lines = result.content.splitlines()
        declarations, references, imports, bindings = [], [], [], {}
        if path.suffix == '.py':
            try:
                tree = ast.parse(result.content)
                declarations = [(n.lineno, n.name) for n in ast.walk(tree)
                                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                module_name = '.'.join(path.relative_to(base).with_suffix('').parts)
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        targets[module_name+'.'+node.name] = (rel, node.lineno+result.start_line-1)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        name = ast.unparse(node.func)
                        if re.fullmatch(r'[A-Za-z_][\w.]*', name):
                            references.append((node.lineno, name))
                    elif isinstance(node, ast.Import):
                        imports.extend(a.name for a in node.names)
                        for alias in node.names:
                            bindings[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                    elif isinstance(node, ast.ImportFrom):
                        package = list(path.relative_to(base).with_suffix('').parts[:-1])
                        prefix = package[:len(package)-node.level+1] if node.level else []
                        module = prefix + (node.module or '').split('.') if node.module else prefix
                        imports.append('.'.join(module))
                        imports.extend('.'.join(module+[alias.name]) for alias in node.names)
                        for alias in node.names:
                            bindings[alias.asname or alias.name] = '.'.join(module+[alias.name])
            except (SyntaxError, ValueError, RecursionError):
                # A partial large file or unsupported syntax remains text evidence.
                declarations = [(n, m[1]) for n, line in enumerate(lines, 1)
                                if (m := re.match(r'\s*(?:async )?(?:def|class)\s+([\w]+)', line))]
        elif path.suffix in ('.js', '.mjs', '.ts', '.tsx', '.jsx'):
            declarations = [(n, m[1]) for n, line in enumerate(lines, 1)
                            if (m := re.match(r'\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function|class)\s+([\w$]+)', line))]
        declarations = [(n+result.start_line-1, name) for n, name in declarations]
        references = [(n+result.start_line-1, name) for n, name in references]
        for n, name in references:
            head, _, tail = name.partition('.')
            if head in bindings:
                target = bindings[head] + ('.'+tail if tail else '')
                edges.append((rel, n, name, target))
        hits = [(n+result.start_line-1, line.strip()) for n, line in enumerate(lines, 1) if any(t in line.lower() for t in terms)]
        documents.append((rel, result.truncated, declarations, hits, references))
        evidence_log.record(evidence_log.SOURCE_READ, 'authorized workspace source', path=rel,
                            lines=f'{result.start_line}-{result.start_line+len(lines)-1}', operation='bounded source inspection',
                            scope='displayed excerpt only' if result.truncated else 'read text')
        if depth < limits.depth:
            follow = []
            for module in imports:
                for name in (module.replace('.', '/')+'.py', module.replace('.', '/')+'/__init__.py'):
                    if name in candidates:
                        follow.append((candidates[name], depth+1))
            # Keep task relevance ahead of incidental imports of storage/helpers.
            pending = sorted(set(follow+pending), key=lambda item: score(item[0]))
    limited |= bool(pending)
    out = ['Source inspection — read-only static evidence from the authorized workspace.',
           f'Read attempts: {len(reads)}/{limits.files}; tool calls: {calls}/{limits.calls}; '
           f'text supplied: {used}/{limits.characters} characters; import depth: at most {limits.depth}.',
           'Direct evidence (relative paths and line numbers):']
    for rel, truncated, declarations, hits, references in documents:
        out.append(f'\n{rel}' + (' (partial excerpt)' if truncated else ''))
        ranked = sorted(declarations, key=lambda d: (-sum(t in d[1].lower() for t in terms), d[0]))
        for n, name in ranked[:4]:
            label = 'declaration candidate' if truncated else 'declaration'
            out.append(f'- {rel}:{n} — {label} `{name}`.')
        for n, line in hits[:3]:
            out.append(f'- {rel}:{n} — {line[:180]}')
        if not declarations and not hits:
            out.append('No matching declaration or line in the inspected text.')
    links = []
    for rel, n, name, target in edges:
        match = targets.get(target)
        if match is not None and match[0] != rel:
            dest, line = match
            links.append(f'- {rel}:{n} calls `{name}`; imported declaration at `{dest}:{line}`. '
                         'Possible static link; runtime target not verified.')
    if links:
        out += ['\nInferences from inspected call expressions (not an execution trace):'] + list(dict.fromkeys(links))[:16]
    if failures:
        out.append(f'\n{len(failures)} read(s) unavailable; failed reads were not used as evidence.')
        out.extend(f'- {name}: {error}' for name, error in failures[:8])
    out += ['\nNot verified: runtime dispatch, dynamic calls, behavior of code not read, or completeness of this architecture.',
            'Inspection limits reached; narrow the question or choose a smaller workspace.' if limited else
            'Discovery completed within these limits; matching text does not prove runtime behavior.',
            '\n*[Sources: authorized workspace text and static parser (no AI model; no code executed)]*']
    return fs.Reply('\n'.join(out), receipts=[r for r in reads if r.ok])

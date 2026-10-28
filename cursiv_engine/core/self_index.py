"""Versioned inventory of public application source; never a user-workspace index.

Build-time Git inventory excludes untracked/private files. Runtime reads only the
inventory's exact paths and verifies bytes before supplying an excerpt. No code
is imported or executed by indexing. Static calls are possible targets, not traces.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import threading

NAME = 'cursiv_engine/core/own_source_index.json'
TOP = {'cursiv_engine', 'launcher', 'docs', 'README.md', 'TECH.md', 'ARCHITECTURE.md',
       'CHANGELOG.md', 'MODELS.md', 'PRIVACY.md', 'OFFLINE-DEMO.md'}
SUFFIXES = {'.py', '.md', '.json', '.txt', '.spec', '.iss', '.toml', '.js', '.mjs', '.ts', '.css', '.html'}
DENIED = {'station', '.cursiv', '.git', '.ssh', '__pycache__', 'private', 'test_internals',
          'licenses', 'family', 'tests', 'CURSIV-LEGAL-HANDOFF.md', 'field-notes.txt'}
ADDITIONS = ('cursiv_engine/core/self_index.py', 'cursiv_engine/core/self_inspection.py',
             'cursiv_engine/core/source_inspection.py', 'cursiv_engine/core/self_contracts.py')
MAX_FILE = 600000
_lock = threading.RLock()
_cache = {}


def fingerprint(raw):
    """Git checkouts may translate CRLF; normalize only that text representation."""
    return hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()


def public_path(rel):
    if not isinstance(rel, str) or '\\' in rel or ':' in rel:
        return False
    p = PurePosixPath(rel)
    return bool(p.parts and not p.is_absolute() and p.parts[0] in TOP and '..' not in p.parts
                and not DENIED.intersection(p.parts) and not any(part.startswith('.') for part in p.parts)
                and p.suffix in SUFFIXES and rel != NAME
                and (p.suffix=='.py' or not re.search(r'(?i)(?:secret|credential|password|\.env|\.(?:key|pem|pfx|p12)$)', rel)))


def checked(base, rel):
    if not public_path(rel):
        raise ValueError('Not public application source')
    base = Path(base).absolute()
    path = base / rel
    for probe in (path, *path.parents):
        if probe.is_symlink() or (hasattr(probe, 'is_junction') and probe.is_junction()):
            raise ValueError('Linked application source is not permitted')
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(base.resolve()) or not resolved.is_file() or resolved.stat().st_nlink > 1:
        raise ValueError('Application source must be an ordinary file inside its bundle')
    if resolved.stat().st_size > MAX_FILE:
        raise ValueError('Application source exceeds the text limit')
    return resolved


def public_files(base):
    """Build-only inventory. Untracked owner documents are never enumerated/read."""
    found = subprocess.check_output(['git', 'ls-files', '-z'], cwd=base).decode('utf-8').split('\0')
    found += [name for name in ADDITIONS if (Path(base)/name).is_file()]
    return sorted({name for name in found if public_path(name)})


def _module(rel):
    parts = list(PurePosixPath(rel).with_suffix('').parts)
    if parts[-1] == '__init__':
        parts.pop()
    # Launcher modules are imported by their bare names in the desktop.
    return '.'.join(parts[1:] if parts[0] == 'launcher' else parts)


def _parse(rel, text):
    module, bindings, symbols = _module(rel), {}, []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return module, symbols
    package = module.split('.')[:-1]
    def bind(node, values):
        if isinstance(node, ast.Import):
            for alias in node.names:
                values[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            prefix = package[:len(package)-node.level+1] if node.level else []
            origin = prefix + (node.module.split('.') if node.module else [])
            for alias in node.names:
                values[alias.asname or alias.name] = '.'.join(origin+[alias.name])
    for node in tree.body:
        bind(node,bindings)
    def visit(nodes, parents=()):
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = '.'.join((*parents,node.name))
                calls = []
                if not isinstance(node, ast.ClassDef):
                    local = dict(bindings)
                    # Function-local imports may differ even when their bare names match.
                    body_nodes, pending = [], list(node.body)
                    while pending:
                        item = pending.pop()
                        if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                            continue
                        body_nodes.append(item)
                        pending.extend(ast.iter_child_nodes(item))
                    shadowed = {arg.arg for arg in (*node.args.posonlyargs,*node.args.args,*node.args.kwonlyargs)}
                    if node.args.vararg: shadowed.add(node.args.vararg.arg)
                    if node.args.kwarg: shadowed.add(node.args.kwarg.arg)
                    shadowed.update(item.id for item in body_nodes if isinstance(item,ast.Name) and isinstance(item.ctx,ast.Store))
                    for shadow_name in shadowed:
                        local.pop(shadow_name,None)
                    for item in body_nodes:
                        bind(item,local)
                    # Walk this function's statements; nested defs are separate symbols.
                    stack = list(node.body)
                    while stack:
                        item = stack.pop()
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            continue
                        if isinstance(item, ast.Call):
                            called = ast.unparse(item.func)
                            if re.fullmatch(r'[A-Za-z_][\w.]*', called):
                                head, _, tail = called.partition('.')
                                target = local[head]+('.'+tail if tail else '') if head in local else ''
                                if head == 'self' and parents:
                                    target = module+'.'+parents[0]+'.'+tail
                                elif not tail and head not in local and head not in shadowed:
                                    target = module+'.'+head
                                calls.append(dict(name=called, line=item.lineno, target=target))
                        stack.extend(ast.iter_child_nodes(item))
                doc = (ast.get_docstring(node) or '').splitlines()
                symbols.append(dict(name=name, line=node.lineno, end=node.end_lineno,
                                    doc=doc[0][:140] if doc else '', calls=sorted(calls,key=lambda c:c['line'])[:100]))
                visit(node.body, (*parents,node.name))
            elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(list(ast.iter_child_nodes(node)), parents)
    visit(tree.body)
    return module, symbols


def build(base, version, paths=None):
    rows = {}
    for rel in (public_files(base) if paths is None else sorted(set(paths))):
        if not public_path(rel):
            continue
        try:
            raw = checked(base, rel).read_bytes()
            text = raw.decode('utf-8-sig')
        except (OSError, ValueError, UnicodeError):
            continue
        module, symbols = _parse(rel, text) if rel.endswith('.py') else ('', [])
        rows[rel] = dict(sha256=fingerprint(raw), bytes=len(raw.replace(b'\r\n',b'\n')), module=module, symbols=symbols)
    digest = hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(schema=1, version=version, snapshot=digest, files=rows)


def load(base, version):
    path = Path(base)/NAME
    for probe in (path,*path.absolute().parents):
        if probe.is_symlink() or (hasattr(probe, 'is_junction') and probe.is_junction()):
            raise ValueError('Linked source index is not permitted')
    if not path.resolve().is_relative_to(Path(base).resolve()) or not path.is_file() or path.stat().st_nlink>1:
        raise ValueError('Source index must be an ordinary bundle file')
    if path.stat().st_size > 12000000:
        raise ValueError('Source index exceeds its safe limit')
    raw = path.read_bytes()
    key = (str(Path(base).resolve()), hashlib.sha256(raw).hexdigest(), version)
    with _lock:
        if key in _cache:
            return _cache[key]
    value = json.loads(raw)
    if not isinstance(value,dict) or value.get('schema') != 1 or value.get('version') != version or not isinstance(value.get('files'),dict):
        raise ValueError('Source index version does not match this application')
    if len(value['files']) > 2000 or any(not public_path(name) for name in value['files']):
        raise ValueError('Source index contains an unsupported path')
    for row in value['files'].values():
        if (not isinstance(row,dict) or not re.fullmatch(r'[0-9a-f]{64}',str(row.get('sha256','')))
                or type(row.get('bytes')) is not int or not 0<=row['bytes']<=MAX_FILE
                or not isinstance(row.get('symbols'),list) or len(row['symbols'])>5000):
            raise ValueError('Source index contains invalid file metadata')
        for symbol in row['symbols']:
            if (not isinstance(symbol,dict) or not re.fullmatch(r'[A-Za-z_][\w.]*',str(symbol.get('name','')))
                    or type(symbol.get('line')) is not int or type(symbol.get('end')) is not int
                    or not 1<=symbol['line']<=symbol['end']<=100000 or not isinstance(symbol.get('calls'),list)):
                raise ValueError('Source index contains invalid symbol metadata')
    digest = hashlib.sha256(json.dumps(value['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest != value.get('snapshot'):
        raise ValueError('Source index fingerprint does not match')
    with _lock:
        _cache.clear()
        _cache[key] = value
    return value


def text(base, index, rel):
    if rel not in index['files']:
        raise ValueError('File is not in the installed source inventory')
    raw = checked(base, rel).read_bytes()
    if fingerprint(raw) != index['files'][rel]['sha256']:
        raise ValueError('Source changed since indexing; rebuild the development index or repair this installation')
    return raw.decode('utf-8-sig')

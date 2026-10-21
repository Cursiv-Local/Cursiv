"""Shared workspace validation for existing file tools and explicit local commands.

No shell, model-native tools, network, or automatic-memory callbacks are involved.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import tempfile
import threading
import time

DENY = re.compile(
    r'(?i)(^|[\\/])(?:\.cursiv|\.git|\.ssh|\.gnupg|\.aws|\.azure|\.kube|\.docker)(?:[\\/]|$)|'
    r'(^|[\\/])(?:id_rsa|id_ed25519|[^\\/]*\.(?:pem|key|pfx|p12)|\.env(?:\.[^\\/]*)?|[^\\/]*secrets?[^\\/]*|[^\\/]*password[^\\/]*|[^\\/]*credential[^\\/]*)$|'
    r'Login Data|Cookies|Web Data|Local State|Microsoft[\\/]Credentials|Microsoft[\\/]Protect'
)
MAX_BYTES = 2_000_000
_CREDENTIAL = re.compile(r'(?i)-----BEGIN .*PRIVATE KEY|\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{8,}|'
                         r'\b(?:password|passphrase|api[_ -]?key|access[_ -]?token|client_secret)[\"\x27]?'
                         r'\s*[:=]\s*(?:[\"\x27][^\"\x27\n]+[\"\x27]|[A-Za-z0-9_+/.-]{8,})')
_lock = threading.RLock()


def resolve(raw: str, root: Path | None) -> Path:
    if root is None:
        raise PermissionError('File access is off. Choose workspace <folder>, then files on.')
    if not isinstance(raw, str) or not raw.strip() or '\x00' in raw:
        raise ValueError('A nonempty file path is required')
    raw = raw.strip().strip('"').strip("'")
    base = root.expanduser().resolve(strict=True)
    if not base.is_dir():
        raise ValueError('The authorized workspace must be a directory')
    p = Path(raw).expanduser()
    path = p if p.is_absolute() else base / p
    # Deny lexical traversal and NTFS alternate streams before normalization.
    if '..' in p.parts or any(':' in part for part in (p.parts[1:] if p.anchor else p.parts) if part):
        raise PermissionError('Path traversal or alternate streams are not allowed')
    resolved = path.resolve()
    if not resolved.is_relative_to(base):
        raise PermissionError('Path is outside the authorized workspace; select that folder explicitly first')
    if DENY.search(str(path)) or DENY.search(str(resolved)):
        raise PermissionError('Protected credential, private data or repository metadata path')
    probe = path
    while probe != base and probe != probe.parent:
        if probe.is_symlink() or (hasattr(probe, 'is_junction') and probe.is_junction()):
            raise PermissionError('Symbolic links and directory junctions are not allowed')
        probe = probe.parent
    if resolved.is_file() and resolved.stat().st_nlink > 1:
        raise PermissionError('Hard-linked files are not allowed')
    return resolved


def _text(path: Path) -> str:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('File exceeds the 2 MB text limit')
    raw = path.read_bytes()
    if b'\x00' in raw:
        raise ValueError('Only UTF-8 text files are supported')
    text = raw.decode('utf-8-sig')
    if _CREDENTIAL.search(text):
        raise PermissionError('File contains credentials or private keys')
    return text


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'missing'


def pending(name: str, args: dict, root: Path) -> dict:
    if name not in ('write_file', 'append_file') or not isinstance(args.get('content', ''), str):
        raise ValueError('Invalid pending file operation')
    p = resolve(args.get('path', ''), root)
    if p.exists() and (not p.is_file() or p.stat().st_size > MAX_BYTES):
        raise ValueError('Existing target must be a text file under 2 MB')
    return dict(operation=name, path=str(p), content=args.get('content', ''), expected_sha256=digest(p),
                remember=bool(args.get('remember', False)))


def execute(name: str, args: dict, root: Path | None, *, confirmed: bool = False) -> str:
    """Schema-validated dispatch. Existing contents are never overwritten without confirmation."""
    if not isinstance(args, dict):
        raise ValueError('File arguments must be an object')
    allowed = {'read_file', 'list_directory', 'search_files', 'create_directory',
               'write_file', 'create_file', 'append_file', 'delete_file'}
    if name not in allowed:
        raise ValueError('Unsupported file operation')
    with _lock:
        p = resolve(args.get('directory', '.') if name == 'search_files' else args.get('path', '.'), root)
        if name == 'read_file':
            return f'File: {p}\n' + _text(p)[:12000]
        if name == 'list_directory':
            rows = []
            for child in sorted(p.iterdir(), key=lambda x: x.name.lower()):
                try:
                    safe = resolve(str(child), root)
                except PermissionError:
                    continue
                rows.append(('[folder] ' if safe.is_dir() else '') + safe.name)
                if len(rows) == 150:
                    break
            return f'Directory: {p}\n' + '\n'.join(rows)
        if name == 'search_files':
            pattern = args.get('pattern', '*')
            if not isinstance(pattern, str) or '..' in Path(pattern).parts or Path(pattern).is_absolute():
                raise ValueError('Search pattern must stay inside the workspace')
            rows = []
            started = time.monotonic()
            for current, dirs, files in os.walk(p, followlinks=False):
                safe_dirs = []
                for directory in dirs:
                    try:
                        resolve(str(Path(current) / directory), root)
                        safe_dirs.append(directory)
                    except (OSError, ValueError):
                        pass
                dirs[:] = safe_dirs
                for item in files + dirs:
                    child = Path(current) / item
                    relative = child.relative_to(p)
                    if not (relative.match(pattern) or (pattern.startswith('**/') and relative.match(pattern[3:]))):
                        continue
                    try:
                        rows.append(str(resolve(str(child), root)))
                    except (OSError, ValueError):
                        continue
                    if len(rows) == 80:
                        break
                if len(rows) == 80 or time.monotonic() - started > 3:
                    break
                if '**' not in pattern:
                    dirs[:] = []
            return 'Found:\n' + '\n'.join(rows)
        if name == 'create_directory':
            p.mkdir(parents=True, exist_ok=True)
            resolve(str(p), root)
            return f'Created directory: {p}'
        if p.exists() and not confirmed:
            raise PermissionError('Confirmation required before modifying an existing file')
        if args.get('expected_sha256') is not None and digest(p) != args['expected_sha256']:
            raise PermissionError('File changed after the request; read it again and request confirmation')
        if name == 'delete_file':
            raise PermissionError('Deletion is disabled in this first version; use your file manager')
        content = args.get('content')
        if not isinstance(content, str) or len(content.encode('utf-8')) > MAX_BYTES:
            raise ValueError('Content must be UTF-8 text under 2 MB')
        if _CREDENTIAL.search(content):
            raise PermissionError('Credential and private-key content cannot be written through file tools')
        if name == 'create_file' and p.exists():
            raise FileExistsError('Create never overwrites an existing file')
        existed = p.exists()
        if existed:
            _text(p)
        before = p.read_bytes() if existed else b''
        if name == 'append_file':
            _text(p)                       # validate text; preserve every existing byte
            data = before + content.encode('utf-8')
        else:
            data = content.encode('utf-8')
        if len(data) > MAX_BYTES:
            raise ValueError('Result would exceed the 2 MB text limit')
        p.parent.mkdir(parents=True, exist_ok=True)
        resolve(str(p), root)               # recheck after directory creation
        fd, temporary = tempfile.mkstemp(prefix='.cursiv-write-', dir=p.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            resolve(str(p), root)
            if p.exists() != existed or (existed and p.read_bytes() != before):
                raise PermissionError('File changed during the write; existing contents were preserved')
            if not existed:
                # Windows rename refuses an existing destination, so a race cannot overwrite it.
                if os.name == 'nt':
                    os.rename(temporary, p)
                else:
                    os.link(temporary, p)
                    os.unlink(temporary)
            else:
                os.replace(temporary, p)
            resolve(str(p), root)
            if p.read_bytes() != data:
                raise OSError('Write verification failed')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return f'Saved and verified: {p} ({len(data)} bytes)'


_REQUEST = re.compile(r'(?i)^file\s+(?:read|list|create|append|replace|remember|save conversation|help)\b|'
                      r'^(?:read|list|create|append|replace)\s+["\x27]|'
                      r'^(?:read|list|create|append|modify|save|remember)\b.{0,240}\b(?:file|folder|desktop|project notes)\b')


def is_request(text: str) -> bool:
    return bool(_REQUEST.search((text or '').strip()))


@dataclass
class Reply:
    text: str = ''
    pending: dict | None = None


def command(text: str, history: list[dict], root: Path | None) -> Reply | None:
    if not is_request(text):
        return None
    m = re.fullmatch(r'(?is)file\s+(read|list|create|append|replace|remember|save conversation)\s+(.+)', text.strip())
    if not m:
        # Conservative natural-language aliases with an explicit, quoted filename.
        m = re.fullmatch(r'(?is)(read|list|create|append|replace)\s+(?:the (?:file|folder)\s+)?["\']([^"\']+)["\'](?:\s*:\s*(.*))?', text.strip())
        if m:
            text = 'file ' + m[1] + ' ' + m[2] + ((' :: ' + m[3]) if m[3] is not None else '')
            return command(text, history, root)
        return Reply('Choose an exact filename inside your authorized workspace. Commands: file read <path>; '
                     'file list <folder>; file create|append|replace|remember <path> :: <text>; '
                     'file save conversation <path>. Set workspace <folder>, then files on first.')
    op, body = m[1].lower(), m[2]
    if root is None:
        return Reply('File access is off. Choose workspace <folder>, then files on. No file was accessed.')
    path, separator, content = body.partition(' :: ')
    if op in ('create', 'append', 'replace', 'remember') and not separator:
        return Reply('Supply the exact content after " :: ". No file was written.')
    if op == 'save conversation':
        content = '\n\n'.join(str(x.get('role', 'message')) + ': ' + str(x.get('content', '')) for x in history)
        if not content:
            return Reply('No conversation text is available to save.')
    name = {'read': 'read_file', 'list': 'list_directory', 'create': 'create_file',
            'append': 'append_file', 'replace': 'write_file', 'remember': 'write_file',
            'save conversation': 'write_file'}[op]
    args = dict(path=path.strip(), content=content, remember=op == 'remember')
    try:
        p = resolve(args['path'], root)
        if name in ('write_file', 'append_file') and p.exists():
            return Reply(pending=pending(name, args, root))
        result = execute(name, args, root)
        if op == 'remember':
            result += '\nConversational memory: ' + save_memory(content)
        return Reply(result)
    except (OSError, ValueError) as exc:
        result = f'File operation not confirmed: {type(exc).__name__}: {exc}'
        if op == 'remember':
            result += '\nConversational memory: ' + save_memory(content)
        return Reply(result)


def save_memory(content: str) -> str:
    from cursiv_v215.memory import semantic
    try:
        fact = semantic.add_fact(content, source='manual')
        return 'saved and verified.' if fact else 'already present.'
    except (OSError, ValueError) as exc:
        return f'not confirmed ({type(exc).__name__}: {exc}).'

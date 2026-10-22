"""Shared workspace validation for existing file tools and explicit local commands.

No shell, model-native tools, network, or automatic-memory callbacks are involved.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
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


class VerifiedText(str):
    """Application-produced action output; providers only produce ordinary str."""

    def __new__(cls, text, result=None):
        value = super().__new__(cls, text)
        value.result = result
        return value


@dataclass
class FileResult:
    operation: str
    path: str = ''
    ok: bool = True
    content: str = ''
    entries: list[str] = field(default_factory=list)
    byte_count: int = 0
    sha256: str = ''
    error: str = ''
    truncated: bool = False

    def receipt(self) -> dict:
        data = asdict(self)
        if self.operation != 'read_file':
            data.pop('content')        # verified bytes/hash suffice; don't duplicate large writes in model/history
        return dict(data, domain='filesystem', verified=self.ok)

    def model_output(self) -> str:
        return json.dumps(self.receipt(), ensure_ascii=False)

    def render(self) -> str:
        if not self.ok:
            return f'Error: {self.error}. File operation not confirmed.'
        if self.operation == 'read_file':
            return f'File: {self.path}\n{self.content}'
        if self.operation == 'list_directory':
            return f'Directory: {self.path}\n' + '\n'.join(self.entries)
        if self.operation == 'search_files':
            return 'Found:\n' + '\n'.join(self.entries)
        if self.operation == 'create_directory':
            return f'Created and verified directory: {self.path}'
        return f'Saved and verified: {self.path} ({self.byte_count} bytes)\nSHA-256: {self.sha256}'

    def status_line(self) -> str:
        if not self.ok or self.operation not in ('read_file', 'list_directory', 'search_files'):
            return self.render()
        count = len(self.content.splitlines()) if self.operation == 'read_file' else len(self.entries)
        unit = 'lines' if self.operation == 'read_file' else 'entries'
        return f'Verified {self.operation}: {self.path} ({count} {unit})'


def workspace_root(root: Path | str | None) -> Path:
    if root is None or not str(root).strip():
        raise PermissionError('File access is off. Choose workspace <folder>, then files on.')
    candidate = Path(root).expanduser().absolute()
    for probe in (candidate, *candidate.parents):
        if probe.is_symlink() or (hasattr(probe, 'is_junction') and probe.is_junction()):
            raise PermissionError('Workspace symbolic links and directory junctions are not allowed')
    base = candidate.resolve(strict=True)
    if not base.is_dir():
        raise ValueError('The authorized workspace must be a directory')
    return base


def resolve(raw: str, root: Path | None) -> Path:
    base = workspace_root(root)
    if not isinstance(raw, str) or not raw.strip() or '\x00' in raw:
        raise ValueError('A nonempty file path is required')
    raw = raw.strip().strip('"').strip("'")
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
    return _decode_text(path.read_bytes())


def _decode_text(raw: bytes) -> str:
    if len(raw) > MAX_BYTES:
        raise ValueError('File exceeds the 2 MB text limit')
    if b'\x00' in raw:
        raise ValueError('Only UTF-8 text files are supported')
    text = raw.decode('utf-8-sig')
    if _CREDENTIAL.search(text):
        raise PermissionError('File contains credentials or private keys')
    return text


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'missing'


def _check_mutation(path: Path) -> None:
    """Shared with confirmation preparation; no adapter can grant an exception."""
    from cursiv_v215.guardian.protected import is_protected_path
    if is_protected_path(str(path)) or is_protected_path(str(path) + '/'):
        raise PermissionError('Protected login, key or guardian file cannot be changed')


def pending(name: str, args: dict, root: Path) -> dict:
    if name not in ('write_file', 'append_file') or not isinstance(args.get('content', ''), str):
        raise ValueError('Invalid pending file operation')
    p = resolve(args.get('path', ''), root)
    _check_mutation(p)
    if p.exists() and (not p.is_file() or p.stat().st_size > MAX_BYTES):
        raise ValueError('Existing target must be a text file under 2 MB')
    return dict(operation=name, path=str(p), content=args.get('content', ''), expected_sha256=digest(p),
                remember=bool(args.get('remember', False)))


def execute_result(name: str, args: dict, root: Path | None, *, confirmed: bool = False) -> FileResult:
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
            raw = p.read_bytes()
            content = _decode_text(raw)
            return FileResult(name, str(p), content=content[:12000], byte_count=len(raw),
                              sha256=hashlib.sha256(raw).hexdigest(), truncated=len(content) > 12000)
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
            return FileResult(name, str(p), entries=rows)
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
            return FileResult(name, str(p), entries=rows)
        # Every mutation route (native, generic and provider) reaches this layer.
        # The provider's additional guard is not an authorization boundary.
        _check_mutation(p)
        if name == 'create_directory':
            p.mkdir(parents=True, exist_ok=True)
            resolve(str(p), root)
            if not p.is_dir():
                raise OSError('Directory creation verification failed')
            return FileResult(name, str(p))
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
            back = p.read_bytes()
            if back != data:
                raise OSError('Write verification failed')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return FileResult(name, str(p), content=data.decode('utf-8'), byte_count=len(back),
                          sha256=hashlib.sha256(back).hexdigest())


def execute(name: str, args: dict, root: Path | None, *, confirmed: bool = False) -> str:
    """Compatibility API. Exceptions still propagate; receipts come from the backend."""
    return execute_result(name, args, root, confirmed=confirmed).render()


def perform(name: str, args: dict, root: Path | str | None, *, confirmed: bool = False) -> FileResult:
    try:
        return execute_result(name, args, workspace_root(root), confirmed=confirmed)
    except (OSError, ValueError, TypeError) as exc:
        return FileResult(name, ok=False, error=f'{type(exc).__name__}: {exc}')


_REQUEST = re.compile(r'(?i)^(?:please\s+)?file\s+(?:read|list|create|append|replace|remember|save conversation|help)\b|'
                      r'^(?:read|list|create|append|replace)\s+["\x27]|'
                      r'^(?:please\s+)?(?:read|list|create|append|modify|save|write|replace)\b.{0,240}'
                      r'(?:\b(?:file|folder|desktop|workspace|project notes)\b|\.[a-z0-9]{1,8}\b)')


def is_request(text: str, history: list[dict] | None = None) -> bool:
    from .turn_policy import task_text
    t = re.sub(r'(?i)^(?:(?:can|could|would) you\s+|now\s+)', '', task_text(text))
    return bool(_REQUEST.search(t) or _workspace_listing(t) or (_location_request(t) and _previous(history or [])))


def _workspace_listing(text: str) -> bool:
    return bool(re.fullmatch(r"(?is)(?:look at|list|show(?: me)?)(?:\s+the)?\s+"
                             r"(?:files in (?:the )?)?(?:current |authorized )?workspace"
                             r"(?:\s+and (?:tell|show|give)\b.*)?[.?]?", text))


def _location_request(text: str) -> bool:
    return bool(re.search(r'(?i)^(?:give me |tell me |show me )?(?:the )?(?:exact )?(?:location|destination|path)\b|'
                         r'^(?:where (?:did you|was it|is (?:it|the file))|give me the exact location)', text))


def _parse(text: str, history: list[dict]) -> tuple[str, str, str] | None:
    from .turn_policy import task_text
    t = re.sub(r'(?i)^(?:please\s+|(?:can|could|would) you\s+|now\s+)', '', task_text(text))
    if _workspace_listing(t):
        return 'list', '.', ''
    m = re.fullmatch(r'(?is)file\s+(read|list|create|append|replace|remember|save conversation)\s+(.+)', t)
    if m:
        path, separator, content = m[2].partition(' :: ')
        return m[1].lower(), path.strip(), content if separator else ''
    m = re.fullmatch(r'(?is)(read|list)\s+(?:the (?:file|folder)\s+)?["\']([^"\']+)["\']'
                     r'\s+and (?:tell|show|give|summari[sz]e|explain|describe)\b.*', t)
    if m:
        return m[1].lower(), m[2], ''
    m = re.fullmatch(r'(?is)(read|list|create|append|replace)\s+(?:the (?:file|folder)\s+)?["\']([^"\']+)["\'](?:\s*:\s*(.*))?', t)
    if m:
        return m[1].lower(), m[2], m[3] or ''
    m = re.fullmatch(r'(?is)(create|write|save|replace|append)(?:\s+(?:a|the))?(?:\s+file(?:\s+(?:named|called))?)?\s+'
                     r'(.+?)\s+(?:in (?:my|the) (?:authorized )?workspace\s+)?'
                     r'(?:containing|with (?:the )?content|with the following content)\s*:\s?(.*)', t)
    if m:
        return ('create' if m[1].lower() in ('create', 'write', 'save') else m[1].lower(), m[2].strip(), m[3])
    m = re.fullmatch(r'(?is)(?:create|write|save)\s+(.+?)\s+with (?:that|the same) content[.!]?', t.strip())
    if m:
        prior = _previous(history, require_content=True)
        return ('create', m[1].strip(), prior[2]) if prior and prior[2] else None
    m = re.fullmatch(r'(?is)(read|list)\s+(?:(?:the|my)\s+)?(?:files?\s+)?(.+?)(?:\s+and (?:tell|show|give|summari[sz]e|explain|describe)\b.*)?', t.strip())
    if m:
        path = m[2].strip().rstrip('?.').strip('"\'')
        if re.fullmatch(r'(?i)(?:in )?(?:(?:my|the) )?(?:(?:current|authorized) )?workspace', path):
            path = '.'
        # Do not turn an unrecognized prose instruction into a literal path.
        if re.search(r'(?i)\b(?:and|then|please)\s+(?:tell|show|give|summari[sz]e|explain|describe|read|write)\b', path):
            return None
        return m[1].lower(), path, ''
    if _location_request(t):
        prior = _previous(history)
        if prior:
            return 'verify', prior[1], prior[2]
    return None


def _previous(history: list[dict], *, require_content=False) -> tuple[str, str, str] | None:
    # User-authored filenames/content only. Assistant save/path claims are ignored.
    for i in range(len(history) - 1, max(-1, len(history) - 14), -1):
        row = history[i]
        if row.get('role') != 'user' or not isinstance(row.get('content'), str):
            continue
        t = row['content']
        if _location_request(t):
            continue
        parsed = _parse(t, []) if _REQUEST.search(t.strip()) else None
        if parsed and (not require_content or parsed[2]):
            return parsed
    return None


def unverified_claim(text: str) -> bool:
    """Conservative guard for action acknowledgements emitted as model prose."""
    text = re.sub(r'(?ms)^\s*```[^\n]*\n.*?^\s*```\s*$', '', text)
    text = re.sub(r'(?ms)^\s*~~~[^\n]*\n.*?^\s*~~~\s*$', '', text)
    text = re.sub(r'(?m)^\s*(?:[-+•]\s+|\d+[.)]\s+)', '', text)
    return bool(re.search(r'(?im)^\s*[*_`]*(?:→\s*)?(?:file_create|create_file|write_file|append_file|read_file)\s*[:(]|'
        r'^\s*[*_`]*(?:got it\s*[,—–:-]\s*)?I(?:[\x27’]ll| will)\s+remember\b|'
        r'^\s*[*_`]*(?:I|we|Cursiv|the file|your file|it)\s+(?:(?:have|has|just|successfully|now|been|was|is|already)\s+)*'
        r'(?:saved|stored|remembered)\b|'
        r'^\s*[*_`]*(?:I|we|Cursiv|the file|your file|it)\s+(?:(?:have|has|just|successfully|now|been|was|is|already)\s+)*'
        r'(?:created|wrote|written|appended|deleted|updated)\b[^.\n]{0,80}\b(?:file|folder|directory|memory|letter|record)\b|'
        r'^\s*[*_`]*(?:created|saved|wrote|written|appended|deleted|updated)\s+(?:(?:the|your|a|new)\s+)?'
        r'(?:file|folder|directory|memory|letter|record)\b', text))


def model_prose(text: str) -> str:
    if unverified_claim(text):
        return VerifiedText('Action not confirmed: the model described a save or file operation without a matching verified execution result. '
                            'No successful action is confirmed by that description.')
    return text


@dataclass
class Reply:
    text: str = ''
    pending: dict | None = None
    receipts: list[FileResult] = field(default_factory=list)


def command(text: str, history: list[dict], root: Path | None) -> Reply | None:
    if not is_request(text, history):
        return None
    parsed = _parse(text, history)
    if not parsed:
        return Reply('Choose an exact filename inside your authorized workspace. Commands: file read <path>; '
                     'file list <folder>; file create|append|replace|remember <path> :: <text>; '
                     'file save conversation <path>. Set workspace <folder>, then files on first.')
    op, path, content = parsed
    from .turn_policy import effective, DENIED
    policy = effective(text)
    action = {'read': 'read_file', 'verify': 'read_file', 'list': 'list_directory'}.get(op, 'write_file')
    if policy.blocks(action):
        return Reply(DENIED)
    if root is None:
        return Reply('File access is off. Choose workspace <folder>, then files on. No file was accessed.')
    if op in ('create', 'append', 'replace', 'remember') and not content:
        return Reply('Supply the exact content after " :: ". No file was written.')
    if op == 'save conversation':
        content = '\n\n'.join(str(x.get('role', 'message')) + ': ' + str(x.get('content', '')) for x in history)
        if not content:
            return Reply('No conversation text is available to save.')
    name = {'read': 'read_file', 'verify': 'read_file', 'list': 'list_directory', 'create': 'create_file',
            'append': 'append_file', 'replace': 'write_file', 'remember': 'write_file',
            'save conversation': 'write_file'}[op]
    args = dict(path=path.strip(), content=content, remember=op == 'remember')
    try:
        p = resolve(args['path'], root)
        if name in ('write_file', 'append_file') and p.exists():
            return Reply(pending=pending(name, args, root))
        receipt = perform(name, args, root)
        if op == 'verify' and receipt.ok and content and receipt.content != content:
            receipt = FileResult(name, receipt.path, ok=False, error='Current file contents do not match the requested contents')
        result = receipt.render()
        if op == 'remember':
            result += ('\nConversational memory: ' + save_memory(content) if receipt.ok else
                       '\nConversational memory: not attempted because the file operation failed.')
        return Reply(result, receipts=[receipt])
    except (OSError, ValueError) as exc:
        result = f'File operation not confirmed: {type(exc).__name__}: {exc}'
        if op == 'remember':
            result += '\nConversational memory: not attempted because the file operation failed.'
        return Reply(result)


def save_memory(content: str) -> str:
    from cursiv_v215.memory import semantic
    from cursiv_v215.memory import intents
    result = intents.execute(intents.Action(intents.SAVE, content=content), person=semantic.current_person())
    if result.ok:
        return ('already present.' if result.status == 'already_saved' else 'saved and verified.') + \
            ' Memory ID: ' + result.records[0]['id']
    return 'not confirmed: ' + result.message

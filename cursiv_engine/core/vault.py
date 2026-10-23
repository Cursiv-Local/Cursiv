"""Opt-in, portable data encryption. No password or derived key is persisted.

The envelope retains the existing JSON/JSONL bytes. A path binding prevents
swapping two records within a vault; roots can move with a portable drive.
Activation is deliberately separate from normal readers and writers.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import threading

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MARKER = 'data-vault.json'
MAGIC = b'CURSIV-VAULT-1\n'
MAX_BYTES = 64 * 1024 * 1024
LOCK = threading.RLock()
_keys: dict[Path, Fernet] = {}
FOLDERS = frozenset(('conversations', 'sessions', 'projects', 'style', 'curiosity', 'presence'))
NAMES = frozenset(('memory.json', 'embeddings_cache.json', 'strands.jsonl', 'territories.json',
                   'coding_profile.json', 'coding_lessons.jsonl', 'council_memory.json',
                   'rated_exchanges.jsonl'))


class VaultError(OSError):
    """Never treat an encrypted store as missing, empty, or recoverable plaintext."""


def roots() -> list[Path]:
    from .paths import APP_DATA
    import sys
    paths = [APP_DATA, Path.home() / '.cursiv']
    if getattr(sys, 'frozen', False):
        paths.append(Path(sys.executable).parent / '.cursiv')
    return list(dict.fromkeys(p.absolute() for p in paths))


def checked(path: Path) -> Path:
    path = Path(path).absolute()
    for p in (path, *path.parents):
        if p.is_symlink() or p.is_junction():
            raise VaultError('Linked private storage refused; existing data preserved')
    if path.is_file() and path.stat().st_nlink > 1:
        raise VaultError('Hard-linked private storage refused; existing data preserved')
    return path


def covered(relative: Path) -> bool:
    """Known conversation/memory stores and their in-place backups, never notebook data."""
    if not relative.parts or relative.parts[0].startswith('.vault-'):
        return False
    if relative.parts[0] in FOLDERS:
        return True
    if len(relative.parts) > 1 and relative.parts[0] not in ('backups', 'archives'):
        return False  # a similarly named attachment/document is not a memory store
    name = relative.name.lstrip('.')  # include leftovers from older interrupted atomic writes
    return (name in NAMES or
            name.startswith('memory_') or
            any(name.startswith(base + ending) for base in NAMES for ending in ('.', '-')))


def owner(path: Path) -> Path | None:
    path = Path(path).absolute()
    for parent in path.parents:
        if parent in _keys and not (parent / MARKER).exists() and covered(path.relative_to(parent)):
            raise VaultError('Encryption configuration disappeared; existing data preserved')
        if (parent / MARKER).exists():
            return parent if covered(path.relative_to(parent)) else None
    return None


def metadata(root: Path) -> dict:
    path = checked(root / MARKER)
    try:
        if path.stat().st_size > 4096:
            raise ValueError('metadata too large')
        data = json.loads(path.read_text(encoding='utf-8'))
        salt = base64.b64decode(data['salt'], validate=True)
        if (data['version'] != 1 or data['kdf'] != 'scrypt-131072-8-1' or
                len(salt) != 16 or data['state'] not in ('migrating', 'ready') or
                not isinstance(data['check'], str) or len(data['check']) > 256):
            raise ValueError('unknown configuration')
        return data
    except (ValueError, KeyError, TypeError) as exc:
        raise VaultError('Invalid encryption configuration; existing data preserved') from exc


def derive(passphrase: str, salt: bytes) -> Fernet:
    key = Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(passphrase.encode('utf-8'))
    return Fernet(base64.urlsafe_b64encode(key))


def new_metadata(passphrase: str) -> tuple[dict, Fernet]:
    if len(passphrase) < 16:
        raise VaultError('Use an encryption passphrase of at least 16 characters')
    salt = os.urandom(16)
    cipher = derive(passphrase, salt)
    return dict(version=1, kdf='scrypt-131072-8-1', salt=base64.b64encode(salt).decode('ascii'),
                check=cipher.encrypt(b'Cursiv data vault v1').decode('ascii'), state='migrating'), cipher


def authenticate(root: Path, passphrase: str) -> tuple[dict, Fernet]:
    data = metadata(root)
    cipher = derive(passphrase, base64.b64decode(data['salt']))
    try:
        if cipher.decrypt(data['check'].encode('ascii')) != b'Cursiv data vault v1':
            raise InvalidToken
    except (InvalidToken, ValueError, TypeError) as exc:
        raise VaultError('Incorrect encryption passphrase or damaged vault configuration') from exc
    return data, cipher


def unlock(passphrase: str, directories=None) -> None:
    """Authenticate every root before making any of them available."""
    pending = {}
    for root in directories if directories is not None else roots():
        root = Path(root).absolute()
        if not (root / MARKER).exists():
            continue
        data, cipher = authenticate(root, passphrase)
        if data['state'] != 'ready':
            raise VaultError('Encryption migration is unfinished; resume it before opening Cursiv')
        pending[root] = cipher
    with LOCK:
        _keys.update(pending)


def lock() -> None:
    """Drop key references; application exit is required to discard decrypted caches."""
    with LOCK:
        _keys.clear()


def _cipher(root: Path) -> Fernet:
    if metadata(root)['state'] != 'ready':
        raise VaultError('Encryption migration is unfinished; no storage changes allowed')
    try:
        return _keys[root]
    except KeyError as exc:
        raise VaultError('Conversations and memories are locked; unlock at startup') from exc


def ensure_access(path: Path) -> None:
    root = owner(path)
    if root is not None:
        checked(path)
        _cipher(root)


def pack(cipher: Fernet, relative: Path, data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise VaultError('Private store exceeds the 64 MB encryption limit; existing data preserved')
    return MAGIC + cipher.encrypt(relative.as_posix().encode('utf-8') + b'\0' + data)


def unpack(cipher: Fernet, relative: Path, data: bytes) -> bytes:
    try:
        value = cipher.decrypt(data[len(MAGIC):])
        name, content = value.split(b'\0', 1)
        if not data.startswith(MAGIC) or name != relative.as_posix().encode('utf-8'):
            raise InvalidToken
        return content
    except (InvalidToken, ValueError) as exc:
        raise VaultError('Encrypted data authentication failed; existing data preserved') from exc


def protect(path: Path, content: bytes) -> bytes:
    root = owner(path)
    if root is None:
        if Path(path).is_file():
            with Path(path).open('rb') as stream:
                if stream.read(len(MAGIC)) == MAGIC:
                    raise VaultError('Encrypted store configuration is missing; refusing overwrite')
        return content
    checked(path)
    cipher = _cipher(root)
    relative = Path(path).absolute().relative_to(root)
    if Path(path).exists():
        current = Path(path).read_bytes()
        if not current.startswith(MAGIC):
            raise VaultError('Unexpected plaintext in encrypted storage; existing data preserved')
        unpack(cipher, relative, current)  # never overwrite an unauthenticated existing record
    return pack(cipher, relative, content)


def reveal(path: Path, content: bytes) -> bytes:
    root = owner(path)
    if root is None:
        if content.startswith(MAGIC):
            raise VaultError('Encrypted store configuration is missing; unlock cannot be bypassed')
        return content
    checked(path)
    cipher = _cipher(root)
    if not content.startswith(MAGIC):
        raise VaultError('Unexpected plaintext in encrypted storage; resume migration before use')
    return unpack(cipher, Path(path).absolute().relative_to(root), content)

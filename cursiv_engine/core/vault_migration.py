"""Explicit offline migration with encrypted recovery copies and resumable state.

Call only with the application closed and DataLease held. Original bytes are
backed up and authenticated before replacement. No plaintext temporary files.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from . import atomic, vault

JOURNAL = Path('.vault-recovery/manifest.enc')


def require_closed() -> None:
    """Older releases predate the OS lease; refuse migration while they run too."""
    import psutil
    # Migration now runs at a normal start (U97), so this process's own launchers
    # (a venv python.exe redirector, a PyInstaller bootloader) are never "another Cursiv".
    own_launchers = {parent.pid for parent in psutil.Process().parents()}
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            info = process.info
            if info['pid'] == os.getpid() or info['pid'] in own_launchers:
                continue
            name = (info.get('name') or '').lower()
            command = info.get('cmdline') or []
            source = any(str(arg).replace('\\', '/').lower().endswith('/launcher/main.py') or
                         str(arg).replace('\\', '/').lower() == 'launcher/main.py' for arg in command)
            module = any(command[i:i + 2] == ['-m', 'launcher'] for i in range(len(command)))
            if name in ('cursiv.exe', 'cursiv') or source or module:
                raise vault.VaultError('Close every other Cursiv process, including older versions, before migration')
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            raise vault.VaultError('Could not establish whether Cursiv data is in use; migration refused') from exc


def adopt_new_stores(directories=None) -> int:
    """After unlock: stores a later release began encrypting (the field notebook, U98) are
    still readable in an existing vault. Each gets an encrypted recovery copy, verified,
    then is encrypted in place and read back. Run at startup with the lease held."""
    import time
    done = 0
    for root in (directories if directories is not None else vault.roots()):
        root = Path(root).absolute()
        if not (root / vault.MARKER).exists() or vault.metadata(root)['state'] != 'ready':
            continue
        cipher = vault._cipher(root)
        stamp = time.strftime('%Y%m%d-%H%M%S')
        for index, path in enumerate(inventory(root)):
            raw = path.read_bytes()
            if raw.startswith(vault.MAGIC):
                continue
            relative = path.relative_to(root)
            backup = Path('.vault-recovery') / f'adopt-{stamp}-{index:06d}.enc'
            atomic.write_bytes(root / backup, vault.pack(cipher, backup, relative.as_posix().encode('utf-8')
                                                         + b'\0' + raw), protect=False)
            if vault.unpack(cipher, backup, (root / backup).read_bytes()).split(b'\0', 1)[1] != raw:
                raise vault.VaultError('Encrypted recovery copy verification failed; nothing was changed')
            if path.read_bytes() != raw:
                raise vault.VaultError('A store changed while it was being encrypted; existing data preserved')
            atomic.write_bytes(path, vault.pack(cipher, relative, raw), protect=False)
            if vault.unpack(cipher, relative, path.read_bytes()) != raw:
                raise vault.VaultError('Encryption read-back verification failed; the recovery copy is kept')
            done += 1
    return done


def inventory(root: Path) -> list[Path]:
    if not root.exists():
        return []
    result = []
    for directory, dirs, files in os.walk(vault.checked(root), followlinks=False):
        for name in dirs:
            vault.checked(Path(directory) / name)
        dirs[:] = [d for d in dirs if not d.startswith('.vault-')]
        for name in files:
            path = Path(directory) / name
            if vault.covered(path.relative_to(root)):
                vault.checked(path)
                with path.open('rb') as stream:
                    encrypted = stream.read(len(vault.MAGIC)) == vault.MAGIC
                if path.stat().st_size > vault.MAX_BYTES * (2 if encrypted else 1):
                    raise vault.VaultError('A private store exceeds 64 MB; archive it before enabling encryption')
                result.append(path)
    return sorted(result)


def _write_metadata(root: Path, data: dict) -> None:
    atomic.write_text(root / vault.MARKER, json.dumps(data, indent=2))


def migrate(passphrase: str, directories=None) -> dict[str, int]:
    roots = list(dict.fromkeys(Path(p).absolute() for p in
                              (directories if directories is not None else vault.roots())))
    prepared = []
    # Preflight every root before changing any record. Existing vaults must use
    # the supplied passphrase; no partial unlock or implicit password rotation.
    for root in roots:
        vault.checked(root)
        files = inventory(root)
        if (root / vault.MARKER).exists():
            meta, cipher = vault.authenticate(root, passphrase)
        else:
            meta, cipher = vault.new_metadata(passphrase)
        prepared.append((root, files, meta, cipher))
    for root, _files, meta, _cipher in prepared:
        if not (root / vault.MARKER).exists():
            root.mkdir(parents=True, exist_ok=True)
            _write_metadata(root, meta)
    counts = {}
    for root, files, meta, cipher in prepared:
        if meta['state'] == 'ready':
            # A new plaintext copy may have appeared in an enabled root. Never
            # silently use it or leave it outside the migration's protection.
            for path in files:
                vault.unpack(cipher, path.relative_to(root), path.read_bytes())
            counts[str(root)] = 0
            continue
        journal_path = root / JOURNAL
        if journal_path.exists():
            records = json.loads(vault.unpack(cipher, JOURNAL, journal_path.read_bytes()))
        else:
            records = []
            for index, path in enumerate(files):
                relative = path.relative_to(root)
                raw = path.read_bytes()
                if raw.startswith(vault.MAGIC):
                    raise vault.VaultError('Encrypted file without a migration journal; manual recovery required')
                backup = Path('.vault-recovery') / f'{index:08d}.enc'
                atomic.write_bytes(root / backup, vault.pack(cipher, backup, raw), protect=False)
                if vault.unpack(cipher, backup, (root / backup).read_bytes()) != raw:
                    raise vault.VaultError('Encrypted recovery backup verification failed')
                records.append(dict(path=relative.as_posix(), sha256=hashlib.sha256(raw).hexdigest(),
                                    backup=backup.as_posix()))
            # This encrypted snapshot is the byte-for-byte pre-migration backup.
            # It also authenticates filenames/hashes; no plaintext hash manifest.
            atomic.write_bytes(journal_path, vault.pack(cipher, JOURNAL,
                               json.dumps(records, ensure_ascii=False).encode('utf-8')), protect=False)
            if json.loads(vault.unpack(cipher, JOURNAL, journal_path.read_bytes())) != records:
                raise vault.VaultError('Encrypted recovery backup verification failed')
        expected = {r['path'] for r in records}
        if {p.relative_to(root).as_posix() for p in files} != expected:
            raise vault.VaultError('Private store inventory changed during migration; existing data preserved')
        for record in records:
            relative = Path(record['path'])
            if relative.is_absolute() or '..' in relative.parts or not vault.covered(relative):
                raise vault.VaultError('Invalid migration record')
            path = vault.checked(root / relative)
            backup = Path(record['backup'])
            if backup.parent != Path('.vault-recovery') or not backup.name.endswith('.enc'):
                raise vault.VaultError('Invalid recovery file reference')
            original = vault.unpack(cipher, backup, vault.checked(root / backup).read_bytes())
            if hashlib.sha256(original).hexdigest() != record['sha256']:
                raise vault.VaultError('Recovery backup checksum mismatch')
            current = path.read_bytes()
            if current.startswith(vault.MAGIC):
                if vault.unpack(cipher, relative, current) != original:
                    raise vault.VaultError('Migrated file differs from its recovery copy')
            else:
                if current != original:
                    raise vault.VaultError('Private file changed during migration; refusing replacement')
                atomic.write_bytes(path, vault.pack(cipher, relative, original), protect=False)
            if vault.unpack(cipher, relative, path.read_bytes()) != original:
                raise vault.VaultError('Encrypted file read-back verification failed')
        _write_metadata(root, dict(meta, state='ready'))
        counts[str(root)] = len(records)
    vault.unlock(passphrase, roots)
    return counts

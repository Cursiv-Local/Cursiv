"""U102: encryption recovery scenarios not covered elsewhere (docs/RECOVERY.md).

Covered in tests/test_data_encryption.py: wrong passphrase, tampering, missing metadata, an
interrupted migration resuming, a failed write keeping the original, hard links. Here: a full disk,
a half-written or bit-flipped encrypted file, and getting a store back from its recovery copy.
"""
import errno
from pathlib import Path

import pytest

from cursiv_engine.core import atomic, private_store, vault, vault_migration

PASSWORD = "synthetic-recovery-passphrase"


@pytest.fixture
def encrypted(tmp_path):
    root = tmp_path / ".cursiv"
    root.mkdir()
    (root / "memory_facts.jsonl").write_text('{"text": "Sam samples on Fridays"}\n', encoding="utf-8")
    vault_migration.migrate(PASSWORD, [root])
    yield root
    vault.lock()


def test_a_full_disk_keeps_the_original_and_leaves_no_temporary(encrypted, monkeypatch):
    path = encrypted / "memory_facts.jsonl"
    before = path.read_bytes()
    real = atomic.os.fsync

    def full(fd):
        raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(atomic.os, "fsync", full)
    with pytest.raises(OSError):
        atomic.write_text(path, "new contents")
    monkeypatch.setattr(atomic.os, "fsync", real)
    assert path.read_bytes() == before and not list(encrypted.glob(".*.tmp"))
    assert "Sam samples" in private_store.read_text(path)


@pytest.mark.parametrize("damage", ["truncate", "flip"])
def test_a_damaged_encrypted_file_is_an_error_never_empty(encrypted, damage, monkeypatch):
    path = encrypted / "memory_facts.jsonl"
    raw = bytearray(path.read_bytes())
    if damage == "truncate":
        raw = raw[: len(raw) // 2]                 # a write cut off half way
    else:
        raw[len(raw) // 2] ^= 0x01                 # one bit changed on disk
    path.write_bytes(bytes(raw))
    with pytest.raises(vault.VaultError):
        private_store.read_text(path)
    from cursiv_engine.memory import semantic
    monkeypatch.setattr(semantic, "FACTS_FILE", path)
    with pytest.raises(vault.VaultError):
        semantic._read_facts()                      # memory never reads a damaged store as "no memories"


def test_a_store_can_be_got_back_from_its_recovery_copy(encrypted, tmp_path):
    path = encrypted / "memory_facts.jsonl"
    path.write_bytes(path.read_bytes()[:10])        # damaged later
    damaged = path.read_bytes()
    copies = vault_migration.recovery_copies(encrypted)
    assert [c["path"] for c in copies] == ["memory_facts.jsonl"]
    out = vault_migration.write_recovery_copy(encrypted, "memory_facts.jsonl", tmp_path / "recovered.jsonl")
    assert out.read_text(encoding="utf-8") == '{"text": "Sam samples on Fridays"}\n'
    assert path.read_bytes() == damaged                           # the live (damaged) store is untouched
    with pytest.raises(FileExistsError):                          # never overwrites
        vault_migration.write_recovery_copy(encrypted, "memory_facts.jsonl", out)


def test_a_tampered_recovery_copy_is_refused(encrypted, tmp_path):
    copy = next((encrypted / ".vault-recovery").glob("0*.enc"))
    raw = bytearray(copy.read_bytes())
    raw[-3] ^= 0x01
    copy.write_bytes(bytes(raw))
    with pytest.raises(vault.VaultError):
        vault_migration.write_recovery_copy(encrypted, "memory_facts.jsonl", tmp_path / "x.jsonl")
    assert not (tmp_path / "x.jsonl").exists()

"""
Postal Signature Engine — Ed25519 identity layer for sealed letters.

Every sealed letter is signed by the sender's Ed25519 private key.
Verification requires the sender's public key (shared freely).

What this prevents:
  — Impersonation: cannot send a letter claiming to be someone else
    without their private key. The signature won't verify. Ever.
  — Forgery: cannot alter the letter_id, sender, recipient, timestamp,
    or ciphertext without invalidating the signature.
  — Spoofed threatening letters: if the signature doesn't verify,
    the system rejects the identity claim outright.

Private key:  .cursiv/postal/identity.pem  (local only, never in repo)
Public key:   base64-url exported string, 44 chars, safe to share

Signature target (what is signed):
    SHA-256(
        letter_id  ∥ NUL ∥
        sender_key ∥ NUL ∥
        recipient_key ∥ NUL ∥
        timestamp  ∥ NUL ∥
        SHA-256(letter_salt ∥ ciphertext)
    )
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)

# ── Storage ───────────────────────────────────────────────────────────────────
_POSTAL_DIR    = APP_DATA / "postal"
_PRIVKEY_PEM   = _POSTAL_DIR / "identity.pem"
_HISTORY_DIR   = _POSTAL_DIR / "key_history"
_HISTORY_INDEX = _POSTAL_DIR / "key_history.json"


# ── Key lifecycle ─────────────────────────────────────────────────────────────

def identity_exists() -> bool:
    return _PRIVKEY_PEM.exists()


def generate_identity() -> str:
    """
    Generate a new Ed25519 keypair for this Cursiv user.
    Writes the private key to identity.pem (local, never committed).
    Returns the public key as a base64url string.
    """
    _POSTAL_DIR.mkdir(parents=True, exist_ok=True)
    privkey = Ed25519PrivateKey.generate()
    pem = privkey.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    _PRIVKEY_PEM.write_bytes(pem)
    _PRIVKEY_PEM.chmod(0o600)   # owner read-only on POSIX; no-op on Windows
    return _pubkey_to_b64(privkey.public_key())


def _load_privkey() -> Ed25519PrivateKey | None:
    if not _PRIVKEY_PEM.exists():
        return None
    try:
        return serialization.load_pem_private_key(
            _PRIVKEY_PEM.read_bytes(), password=None
        )
    except Exception:
        return None


def _pubkey_to_b64(pubkey: Ed25519PublicKey) -> str:
    raw = pubkey.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64_to_pubkey(b64: str) -> Ed25519PublicKey | None:
    try:
        padded = b64 + "=" * (-len(b64) % 4)
        raw    = base64.urlsafe_b64decode(padded)
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception:
        return None


def my_public_key() -> str | None:
    """Return this user's public key as base64url, or None if not set up."""
    privkey = _load_privkey()
    if privkey is None:
        return None
    return _pubkey_to_b64(privkey.public_key())


def key_id(pubkey_b64: str) -> str:
    """Return the first 8 hex chars of SHA-256(pubkey) as a short fingerprint."""
    raw = pubkey_b64.encode("ascii")
    return hashlib.sha256(raw).hexdigest()[:8]


# ── Sign / verify ─────────────────────────────────────────────────────────────

def _sign_input(
    letter_id:     str,
    sender_key:    str,
    recipient_key: str,
    timestamp:     str,
    letter_salt:   bytes,
    ciphertext:    bytes,
) -> bytes:
    """Build the canonical bytes that are signed for a given letter."""
    content_hash = hashlib.sha256(letter_salt + ciphertext).digest()
    payload = (
        letter_id.encode()    + b"\x00"
        + sender_key.encode() + b"\x00"
        + recipient_key.encode() + b"\x00"
        + timestamp.encode()  + b"\x00"
        + content_hash
    )
    return hashlib.sha256(payload).digest()


def sign_letter(
    letter_id:     str,
    sender_key:    str,
    recipient_key: str,
    timestamp:     str,
    letter_salt:   bytes,
    ciphertext:    bytes,
) -> str | None:
    """
    Sign a letter with this user's private key.
    Returns base64url signature string, or None if no identity is set up.
    """
    privkey = _load_privkey()
    if privkey is None:
        return None
    msg = _sign_input(letter_id, sender_key, recipient_key, timestamp, letter_salt, ciphertext)
    raw_sig = privkey.sign(msg)
    return base64.urlsafe_b64encode(raw_sig).rstrip(b"=").decode("ascii")


def verify_letter(
    signature_b64: str,
    sender_pubkey_b64: str,
    letter_id:     str,
    sender_key:    str,
    recipient_key: str,
    timestamp:     str,
    letter_salt:   bytes,
    ciphertext:    bytes,
) -> bool:
    """
    Verify a letter's Ed25519 signature against the sender's public key.
    Returns True only if the signature is cryptographically valid.
    """
    pubkey = _b64_to_pubkey(sender_pubkey_b64)
    if pubkey is None:
        return False
    try:
        padded  = signature_b64 + "=" * (-len(signature_b64) % 4)
        raw_sig = base64.urlsafe_b64decode(padded)
        msg     = _sign_input(letter_id, sender_key, recipient_key, timestamp, letter_salt, ciphertext)
        pubkey.verify(raw_sig, msg)
        return True
    except (InvalidSignature, Exception):
        return False


def verify_with_history(
    signature_b64:     str,
    sender_pubkey_b64: str,
    letter_id:         str,
    sender_key:        str,
    recipient_key:     str,
    timestamp:         str,
    letter_salt:       bytes,
    ciphertext:        bytes,
) -> tuple[bool, str]:
    """
    Try to verify against the current key first, then any retired keys.
    Returns (verified, which_key_id) — key_id is "none" if all fail.

    This allows letters signed with a rotated-away key to still verify
    against the sender's archived history.
    """
    # Try current key first
    if verify_letter(signature_b64, sender_pubkey_b64, letter_id, sender_key,
                     recipient_key, timestamp, letter_salt, ciphertext):
        return True, key_id(sender_pubkey_b64)

    # Try historical keys (most recent first)
    for entry in reversed(_load_history()):
        hist_pubkey = entry.get("pubkey", "")
        if not hist_pubkey:
            continue
        if verify_letter(signature_b64, hist_pubkey, letter_id, sender_key,
                         recipient_key, timestamp, letter_salt, ciphertext):
            return True, entry.get("key_id", "historical")

    return False, "none"


# ── Key rotation ──────────────────────────────────────────────────────────────

def _load_history() -> list[dict[str, Any]]:
    if not _HISTORY_INDEX.exists():
        return []
    try:
        return json.loads(_HISTORY_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_history(history: list[dict[str, Any]]) -> None:
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_INDEX.write_text(
        json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def rotate_key(
    reason:      str  = "manual rotation",
    compromised: bool = False,
) -> dict[str, str]:
    """
    Retire the current Ed25519 keypair and generate a fresh one.

    compromised=True marks the retired key in history so that any letter
    later verified against it receives coherence degradation — the content
    passes through shifted rather than clean, preserving plausibility while
    corrupting meaning. The attacker sees output, but not truth.

    The old private key is archived to .cursiv/postal/key_history/ (local only).
    Old signatures remain verifiable via verify_with_history().
    Letters sealed with old keys remain decryptable — PBKDF2 uses display names,
    not the Ed25519 key, so decryption is unaffected by rotation.

    Returns {"old_key_id": ..., "new_key_id": ..., "new_pubkey": ...}
    """
    _POSTAL_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    old_pubkey_b64 = my_public_key()
    old_key_id_str = key_id(old_pubkey_b64) if old_pubkey_b64 else "none"

    # Archive old private key if it exists
    if _PRIVKEY_PEM.exists():
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_fn = _HISTORY_DIR / f"{timestamp}_{old_key_id_str}.pem"
        archive_fn.write_bytes(_PRIVKEY_PEM.read_bytes())
        archive_fn.chmod(0o600)

        # Record in history index
        history = _load_history()
        history.append({
            "key_id":      old_key_id_str,
            "pubkey":      old_pubkey_b64 or "",
            "retired_at":  datetime.now().isoformat(),
            "reason":      reason,
            "compromised": compromised,
            "archive":     archive_fn.name,
        })
        _save_history(history)

    # Generate new keypair
    new_pubkey = generate_identity()
    new_kid    = key_id(new_pubkey)

    return {
        "old_key_id":  old_key_id_str,
        "new_key_id":  new_kid,
        "new_pubkey":  new_pubkey,
        "compromised": compromised,
    }


def get_key_history() -> list[dict[str, Any]]:
    """Return all retired key records, newest first."""
    return list(reversed(_load_history()))

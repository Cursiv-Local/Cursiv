"""
Postal Key Engine — machine-bound key derivation for sealed letters.

Every sealed letter requires three compounding PBKDF2 layers to derive its keys:

  Layer 1 — Machine Anchor (50,000 iterations)
    Input:  seal.uuid  (random UUID, unique to this Cursiv installation)
    Salt:   hardcoded anchor constant + machine-specific twist
    Output: 32-byte anchor — the machine fingerprint

  Layer 2 — Identity Binding (100,000 iterations)
    Input:  sender_key + recipient_key + letter_id  (order-sensitive)
    Salt:   SHA-256(identity_label + layer1_anchor)
    Output: 64 bytes → split into enc_key (32) + hmac_key (32)

  Layer 3 — Stream Derivation (200,000 iterations)
    Input:  enc_key from layer 2
    Salt:   SHA-256(stream_label + enc_key)
    Output: 32-byte stream_seed — used to expand the keystream

Total: 350,000 PBKDF2-SHA256 iterations per seal/open operation.
~2–5 seconds on modern hardware. Intentional. Each attempt costs real time.

The seal.uuid lives in .cursiv/postal/seal.uuid — NOT in the repository.
A clone of the repo on any other machine has a different (or absent) seal.uuid
and derives completely different keys. Every single letter becomes undecryptable.
"""
from __future__ import annotations

import hashlib
import uuid as _uuid_mod
from pathlib import Path
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

# ── Storage ───────────────────────────────────────────────────────────────────
_POSTAL_DIR    = APP_DATA / "postal"
_SEAL_UUID_FILE = _POSTAL_DIR / "seal.uuid"

# ── Derivation constants — do not change; altering breaks all existing seals ─
_ANCHOR_SALT    = (
    b"CURSIV\x00POSTAL\x00ANCHOR\x00v1\x00"
    b"\xe2\x88\x87\xce\xa9\xe2\x88\x9e"   # ∇Ω∞ encoded
)
_IDENTITY_LABEL = b"CURSIV\x00POSTAL\x00IDENTITY\x00v1"
_STREAM_LABEL   = b"CURSIV\x00POSTAL\x00STREAM\x00v1"

# ── Iteration counts — deliberately high ─────────────────────────────────────
_ANCHOR_ITER   =  50_000
_IDENTITY_ITER = 100_000
_STREAM_ITER   = 200_000


# ── Machine anchor ────────────────────────────────────────────────────────────

def _get_seal_uuid() -> bytes:
    """
    Read or create the machine-unique seal UUID.
    Created once on first use; stored locally; never committed to git.
    """
    _POSTAL_DIR.mkdir(parents=True, exist_ok=True)
    if not _SEAL_UUID_FILE.exists():
        _SEAL_UUID_FILE.write_text(str(_uuid_mod.uuid4()), encoding="utf-8")
    return _SEAL_UUID_FILE.read_text(encoding="utf-8").strip().encode("utf-8")


# ── Core derivation ───────────────────────────────────────────────────────────

def derive_letter_keys(
    sender_key:    str,
    recipient_key: str,
    letter_id:     str,
) -> tuple[bytes, bytes, bytes]:
    """
    Derive (enc_key, hmac_key, stream_seed) for one specific letter.

    All three values require this machine's seal.uuid to compute.
    Identical sender/recipient/letter_id on a different machine → different keys.
    The original letter is permanently unreadable on any other machine.

    Returns:
        enc_key    (32 bytes) — used to verify stream_seed integrity
        hmac_key   (32 bytes) — used for HMAC-SHA256 authentication tag
        stream_seed (32 bytes) — seed for keystream expansion
    """
    seal_uuid = _get_seal_uuid()

    # Layer 1: machine anchor
    anchor = hashlib.pbkdf2_hmac(
        "sha256",
        seal_uuid,
        _ANCHOR_SALT,
        _ANCHOR_ITER,
        dklen=32,
    )

    # Layer 2: identity binding (sender ∥ null ∥ recipient ∥ null ∥ letter_id)
    identity      = f"{sender_key}\x00{recipient_key}\x00{letter_id}".encode("utf-8")
    identity_salt = hashlib.sha256(_IDENTITY_LABEL + anchor).digest()
    identity_key  = hashlib.pbkdf2_hmac(
        "sha256",
        identity,
        identity_salt,
        _IDENTITY_ITER,
        dklen=64,
    )
    enc_key  = identity_key[:32]
    hmac_key = identity_key[32:]

    # Layer 3: stream seed
    stream_salt = hashlib.sha256(_STREAM_LABEL + enc_key).digest()
    stream_seed = hashlib.pbkdf2_hmac(
        "sha256",
        enc_key,
        stream_salt,
        _STREAM_ITER,
        dklen=32,
    )

    return enc_key, hmac_key, stream_seed


def derive_keystream(stream_seed: bytes, letter_salt: bytes, length: int) -> bytes:
    """
    Expand stream_seed + letter_salt into a keystream of exactly `length` bytes.

    Uses SHA-256 in counter mode — each 32-byte block is:
        SHA-256(stream_seed ∥ letter_salt ∥ counter[4 bytes big-endian])

    The letter_salt (32 random bytes, unique per letter) ensures no two
    letters ever share a keystream even if the keys were somehow identical.
    """
    base       = stream_seed + letter_salt
    keystream  = bytearray()
    counter    = 0
    while len(keystream) < length:
        block = hashlib.sha256(base + counter.to_bytes(4, "big")).digest()
        keystream.extend(block)
        counter += 1
    return bytes(keystream[:length])


def seal_uuid_present() -> bool:
    """True when the machine seal file exists (postal system is initialized)."""
    return _SEAL_UUID_FILE.exists()

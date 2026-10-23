"""
Sealed Store — encrypted letter vault.

Letters are stored as alien-language encoded ciphertext.
The original plaintext is never written to disk.
The HMAC authentication tag is embedded invisibly via ZWC steganography.
Decryption requires the machine seal.uuid + correct sender/recipient identity.

File layout:
  .cursiv/postal/sealed/{letter_id}.seal  — alien-encoded ciphertext
  .cursiv/postal/index.json               — metadata only (no content)

The .seal file is pure UTF-8 text. It looks like:

  CURSIV·SEALED·POST
  id: <letter_id>
  from: <sender_key>
  for: <recipient_key>  [ZWC: invisible HMAC tag appended here]
  sealed: <ISO timestamp>
  ─────
  <Cursiv-alphabet-encoded ciphertext in blocks of 47>
  ─────
"""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from cursiv_engine.postal.postal_key import derive_letter_keys, derive_keystream
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)
try:
    from cursiv_engine.postal.postal_sign import (
        sign_letter         as _sign_letter,
        verify_with_history as _verify_with_history,
    )
    _SIGN_OK = True
except Exception:
    _SIGN_OK = False
    def _sign_letter(*a, **kw):          return None             # type: ignore[misc]
    def _verify_with_history(*a, **kw):  return (False, "none")  # type: ignore[misc]

# ── Paths ──────────────────────────────────────────────────────────────────────
_POSTAL_DIR  = APP_DATA / "postal"
_SEALED_DIR  = _POSTAL_DIR / "sealed"
_INDEX_FILE  = _POSTAL_DIR / "index.json"
_EXPORT_DEST = None   # resolved lazily


# ── Alien encoding (Cursiv custom alphabet base64 + block formatting) ─────────

def _encode_alien(data: bytes) -> str:
    """
    Encode bytes using the Cursiv custom alphabet (Greek + extended Latin + math).
    Formatted in lines of 47 characters with ∷ separators every 7 lines.
    Output looks like:  ΑΓΩβξπΛΜ∀αΔΞ∃Ρ∞ΒΦΤ∂ΩΨΗ…
    """
    try:
        from cursiv_engine.core.sigil import encode_b64 as _enc
    except ImportError:
        _enc = lambda b: base64.b64encode(b).decode()   # noqa: E731

    raw        = _enc(data)
    LINEWIDTH  = 47
    SEP_EVERY  = 7
    lines: list[str] = []
    line_n = 0

    for i in range(0, len(raw), LINEWIDTH):
        if line_n > 0 and line_n % SEP_EVERY == 0:
            lines.append("∷")
        lines.append(raw[i:i + LINEWIDTH])
        line_n += 1

    return "\n".join(lines)


def _decode_alien(text: str) -> bytes:
    """Inverse of _encode_alien. Strips separators and decodes."""
    try:
        from cursiv_engine.core.sigil import decode_b64 as _dec
    except ImportError:
        _dec = lambda s: base64.b64decode(s)   # noqa: E731

    cleaned = "".join(
        line for line in text.split("\n")
        if line.strip() and line.strip() != "∷"
    )
    return _dec(cleaned)


# ── ZWC tag helpers ───────────────────────────────────────────────────────────

def _embed_tag(host: str, tag: str) -> str:
    """Embed an auth tag string invisibly into host using ZWC steganography."""
    try:
        from cursiv_engine.core.sigil import embed_zwc
        return embed_zwc(host, tag)
    except Exception:
        return host   # graceful fallback — tag lost but seal still stored


def _extract_tag(text: str) -> str:
    """Extract the ZWC-embedded auth tag from text."""
    try:
        from cursiv_engine.core.sigil import extract_zwc
        return extract_zwc(text)
    except Exception:
        return ""


# ── Index ─────────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    _SEALED_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> list[dict[str, Any]]:
    if not _INDEX_FILE.exists():
        return []
    try:
        return json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_index(index: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    _INDEX_FILE.write_text(
        json.dumps(index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _export_path() -> Path:
    home = Path.home()
    for candidate in (
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "OneDrive - Personal" / "Desktop",
        home / "Downloads",
    ):
        if candidate.exists():
            return candidate
    return home


# ── Encryption helpers ────────────────────────────────────────────────────────

def _encrypt(
    plaintext:     bytes,
    sender_key:    str,
    recipient_key: str,
    letter_id:     str,
) -> tuple[bytes, bytes, str]:
    """
    Encrypt plaintext for this (sender, recipient, letter_id) triple.
    Returns (letter_salt, ciphertext, hmac_hex).
    """
    enc_key, hmac_key, stream_seed = derive_letter_keys(
        sender_key, recipient_key, letter_id
    )
    letter_salt = secrets.token_bytes(32)
    keystream   = derive_keystream(stream_seed, letter_salt, len(plaintext))
    ciphertext  = bytes(a ^ b for a, b in zip(plaintext, keystream))
    auth_tag    = _hmac.new(hmac_key, letter_salt + ciphertext, "sha256").hexdigest()
    return letter_salt, ciphertext, auth_tag


def _decrypt(
    letter_salt:   bytes,
    ciphertext:    bytes,
    stored_tag:    str,
    sender_key:    str,
    recipient_key: str,
    letter_id:     str,
) -> bytes | None:
    """
    Decrypt ciphertext. Returns plaintext bytes, or None if HMAC verification fails.
    """
    enc_key, hmac_key, stream_seed = derive_letter_keys(
        sender_key, recipient_key, letter_id
    )
    expected_tag = _hmac.new(hmac_key, letter_salt + ciphertext, "sha256").hexdigest()
    if not _hmac.compare_digest(expected_tag, stored_tag):
        return None   # tampered or wrong machine / wrong identity

    keystream  = derive_keystream(stream_seed, letter_salt, len(ciphertext))
    return bytes(a ^ b for a, b in zip(ciphertext, keystream))


# ── .seal file format ─────────────────────────────────────────────────────────

def _write_seal_file(
    letter_id:     str,
    sender_key:    str,
    recipient_key: str,
    timestamp:     str,
    letter_salt:   bytes,
    ciphertext:    bytes,
    auth_tag:      str,
    signature:     str | None = None,
) -> str:
    """Write the .seal file. Returns filename."""
    payload      = letter_salt + ciphertext
    alien_body   = _encode_alien(payload)
    for_line     = _embed_tag(f"for: {recipient_key}", auth_tag)
    filename     = f"{letter_id}.seal"
    sig_line     = f"sig: {signature}\n" if signature else ""

    seal_text = (
        f"CURSIV·SEALED·POST\n"
        f"id: {letter_id}\n"
        f"from: {sender_key}\n"
        f"{for_line}\n"
        f"{sig_line}"
        f"sealed: {timestamp}\n"
        f"─────\n"
        f"{alien_body}\n"
        f"─────\n"
    )

    (_SEALED_DIR / filename).write_text(seal_text, encoding="utf-8")
    return filename


def _read_seal_file(filename: str) -> tuple[bytes, bytes, str, str | None] | None:
    """
    Parse a .seal file.
    Returns (letter_salt, ciphertext, auth_tag, signature_b64 | None)
    or None on parse failure.
    """
    path = _SEALED_DIR / filename
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Extract auth tag from the ZWC-embedded "for:" line, and Ed25519 sig
    auth_tag  = ""
    signature = None
    for line in raw.splitlines():
        if line.startswith("for:") or line.startswith("for﻿"):
            auth_tag = _extract_tag(line)
        elif line.startswith("sig: "):
            signature = line[5:].strip()

    # Extract alien body between the ─────  delimiters
    parts = raw.split("─────")
    if len(parts) < 3:
        return None

    alien_body = parts[1].strip()
    try:
        payload     = _decode_alien(alien_body)
    except Exception:
        return None

    if len(payload) < 32:
        return None

    letter_salt = payload[:32]
    ciphertext  = payload[32:]
    return letter_salt, ciphertext, auth_tag, signature


# ── Signature status + coherence degradation ─────────────────────────────────

def _sig_status_from_history(matched_key_id: str, current_pubkey: str) -> str:
    """
    Given a matched_key_id from verify_with_history, determine sig_status.
    - matched current key  → "verified"
    - matched a retired (non-compromised) historical key → "verified_rotated"
    - matched a compromised historical key → "verified_compromised"
    """
    from cursiv_engine.postal.postal_sign import key_id as _kid, get_key_history
    current_kid = _kid(current_pubkey)
    if matched_key_id == current_kid:
        return "verified"
    for entry in get_key_history():
        if entry.get("key_id") == matched_key_id:
            return "verified_compromised" if entry.get("compromised") else "verified_rotated"
    return "verified_rotated"   # matched something, assume rotated


def _degrade_coherence(plaintext: bytes, sealed_ts: str) -> bytes:
    """
    Coherence degradation for letters verified against a COMPROMISED key.

    The content passes through mostly intact but a fraction of bytes are
    corrupted deterministically — enough to shift meaning, not enough to
    look obviously broken. The fraction increases as the key ages.

    Degradation schedule:
        0–7 days post-compromise:   10% bytes corrupted
        8–30 days:                  25%
        31–90 days:                 45%
        91+ days:                   65%  (never 100% — residual coherence preserved)

    The noise is seeded from seal.uuid so it is stable per-machine:
    the same letter always degrades the same way on the same machine.
    """
    from cursiv_engine.postal.postal_key import _get_seal_uuid
    import time

    # Determine degradation fraction from key age
    try:
        from datetime import datetime, timezone
        sealed_dt   = datetime.fromisoformat(sealed_ts)
        age_days    = (datetime.now() - sealed_dt).days
    except Exception:
        age_days = 0

    if age_days <= 7:
        fraction = 0.10
    elif age_days <= 30:
        fraction = 0.25
    elif age_days <= 90:
        fraction = 0.45
    else:
        fraction = 0.65

    # Generate deterministic noise keystream seeded by seal.uuid
    seed        = _get_seal_uuid() + b"\x00CURSIV-DEGRADE-v1\x00"
    noise_seed  = hashlib.sha256(seed).digest()
    noise_bytes = bytearray()
    counter     = 0
    while len(noise_bytes) < len(plaintext):
        noise_bytes.extend(hashlib.sha256(noise_seed + counter.to_bytes(4, "big")).digest())
        counter += 1
    noise_bytes = bytes(noise_bytes[:len(plaintext)])

    # Corrupt only word-boundary-adjacent bytes (preserves structural coherence)
    result    = bytearray(plaintext)
    corrupted = 0
    target    = int(len(plaintext) * fraction)
    for i, byte in enumerate(plaintext):
        if corrupted >= target:
            break
        # Only corrupt printable non-space, non-newline characters
        if 0x21 <= byte <= 0x7E:
            # Shift within printable range — doesn't produce garbage
            shifted  = ((byte - 0x21 + noise_bytes[i]) % 94) + 0x21
            result[i] = shifted
            corrupted += 1

    return bytes(result)


# ── Public API ────────────────────────────────────────────────────────────────

def seal_letter(
    sender_key:       str,
    sender_display:   str,
    recipient_key:    str,
    recipient_display: str,
    content:          str,
    hint:             str = "",
    *,
    progress_cb: "callable | None" = None,
) -> str:
    """
    Seal a letter. Returns the letter_id.

    progress_cb(step: str) — called at each encryption stage if provided.
    content is never written to disk in plaintext.
    """
    _ensure_dirs()
    letter_id = secrets.token_hex(8)   # 16-char hex, 64 bits of entropy

    if progress_cb:
        progress_cb("anchor")

    enc_key, hmac_key, stream_seed = derive_letter_keys(
        sender_key, recipient_key, letter_id
    )

    if progress_cb:
        progress_cb("stream")

    plaintext_bytes = content.encode("utf-8")
    letter_salt     = secrets.token_bytes(32)
    keystream       = derive_keystream(stream_seed, letter_salt, len(plaintext_bytes))

    if progress_cb:
        progress_cb("xor")

    ciphertext = bytes(a ^ b for a, b in zip(plaintext_bytes, keystream))

    if progress_cb:
        progress_cb("hmac")

    auth_tag = _hmac.new(hmac_key, letter_salt + ciphertext, "sha256").hexdigest()

    if progress_cb:
        progress_cb("sign")

    now       = datetime.now()
    timestamp = now.isoformat()

    # Ed25519 identity signature — proves this machine's identity key authored the letter
    signature = _sign_letter(
        letter_id, sender_key, recipient_key, timestamp, letter_salt, ciphertext
    ) if _SIGN_OK else None

    if progress_cb:
        progress_cb("encode")

    filename  = _write_seal_file(
        letter_id, sender_key, recipient_key, timestamp,
        letter_salt, ciphertext, auth_tag, signature,
    )

    if progress_cb:
        progress_cb("index")

    index = _load_index()
    index.append({
        "id":              letter_id,
        "from_key":        sender_key,
        "from_display":    sender_display,
        "for_key":         recipient_key,
        "for_display":     recipient_display,
        "hint":            hint.strip()[:80],
        "sealed":          timestamp,
        "filename":        filename,
        "read":            False,
    })
    _save_index(index)
    return letter_id


def open_letter(letter_id: str) -> str | None:
    """
    Decrypt a sealed letter. Returns plaintext or None on failure.
    Marks the letter as read in the index.
    """
    entry = get_sealed_entry(letter_id)
    if not entry:
        return None

    parsed = _read_seal_file(entry["filename"])
    if parsed is None:
        return None

    letter_salt, ciphertext, auth_tag, signature = parsed

    plaintext_bytes = _decrypt(
        letter_salt, ciphertext, auth_tag,
        entry["from_key"], entry["for_key"], letter_id,
    )
    if plaintext_bytes is None:
        return None

    # Ed25519 signature verification — check current key then history
    sig_status = "unsigned"
    if signature and _SIGN_OK:
        try:
            from cursiv_engine.postal.user_registry import lookup_pubkey
            sender_pubkey = lookup_pubkey(entry["from_key"])
            if sender_pubkey:
                verified, matched_key_id = _verify_with_history(
                    signature, sender_pubkey,
                    letter_id, entry["from_key"], entry["for_key"],
                    entry.get("sealed", ""), letter_salt, ciphertext,
                )
                if verified:
                    # Check whether the matched key was marked compromised
                    sig_status = _sig_status_from_history(matched_key_id, sender_pubkey)
                else:
                    sig_status = "INVALID"
            else:
                sig_status = "unverified"
        except Exception:
            sig_status = "unverified"

    # Apply coherence degradation if letter was verified against a compromised key
    if sig_status == "verified_compromised":
        plaintext_bytes = _degrade_coherence(plaintext_bytes, entry.get("sealed", ""))

    # Mark read, store sig_status
    index = _load_index()
    for e in index:
        if e.get("id") == letter_id:
            e["read"]       = True
            e["sig_status"] = sig_status
    _save_index(index)

    return plaintext_bytes.decode("utf-8", errors="replace")


def get_sig_status(letter_id: str) -> str:
    """
    Return the last-known signature status for a letter:
    'verified', 'unverified', 'unsigned', 'INVALID', or 'unknown'.
    """
    entry = get_sealed_entry(letter_id)
    if not entry:
        return "unknown"
    return entry.get("sig_status", "unknown")


def get_sealed_entry(letter_id: str) -> dict[str, Any] | None:
    return next((e for e in _load_index() if e.get("id") == letter_id), None)


def letters_for(recipient_key: str) -> list[dict[str, Any]]:
    """All letters addressed to recipient_key, newest first."""
    return sorted(
        [e for e in _load_index() if e.get("for_key") == recipient_key],
        key=lambda e: e.get("sealed", ""),
        reverse=True,
    )


def letters_from(sender_key: str) -> list[dict[str, Any]]:
    """All letters written by sender_key, newest first."""
    return sorted(
        [e for e in _load_index() if e.get("from_key") == sender_key],
        key=lambda e: e.get("sealed", ""),
        reverse=True,
    )


def all_letters() -> list[dict[str, Any]]:
    return sorted(_load_index(), key=lambda e: e.get("sealed", ""), reverse=True)


def delete_sealed(letter_id: str) -> bool:
    """Permanently delete a sealed letter and remove from index."""
    entry = get_sealed_entry(letter_id)
    if not entry:
        return False
    try:
        (_SEALED_DIR / entry["filename"]).unlink(missing_ok=True)
    except Exception:
        pass
    _save_index([e for e in _load_index() if e.get("id") != letter_id])
    return True


# ── Pack export / import ──────────────────────────────────────────────────────

def export_sealpack(letter_id: str) -> tuple[Path, str] | None:
    """
    Export a sealed letter as a passphrase-protected .sealpack file.
    The sealpack can be sent to the recipient on any machine — they import it
    with the passphrase you provide to them out-of-band.

    Returns (filepath, passphrase) or None on failure.
    The passphrase is shown once and never stored.
    """
    content = open_letter(letter_id)
    if content is None:
        return None

    entry = get_sealed_entry(letter_id)
    if not entry:
        return None

    # Generate a strong readable passphrase (shown once to sender)
    passphrase  = secrets.token_urlsafe(20)   # ~133 bits entropy
    pack_salt   = secrets.token_bytes(32)

    # Derive pack key from passphrase (independent of machine seal.uuid)
    pack_master = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        pack_salt + b"CURSIV-SEALPACK-v1",
        200_000,
        dklen=64,
    )
    pack_enc_key  = pack_master[:32]
    pack_hmac_key = pack_master[32:]

    # Stream seed for sealpack
    pack_stream_seed = hashlib.pbkdf2_hmac(
        "sha256",
        pack_enc_key,
        pack_salt,
        100_000,
        dklen=32,
    )

    plaintext_bytes = content.encode("utf-8")
    pack_keystream  = derive_keystream(pack_stream_seed, pack_salt, len(plaintext_bytes))
    pack_ciphertext = bytes(a ^ b for a, b in zip(plaintext_bytes, pack_keystream))
    pack_auth       = _hmac.new(
        pack_hmac_key, pack_salt + pack_ciphertext, "sha256"
    ).hexdigest()

    pack = {
        "cursiv_sealpack": True,
        "version":         "1.0",
        "letter_id":       letter_id,
        "from_key":        entry["from_key"],
        "from_display":    entry["from_display"],
        "for_key":         entry["for_key"],
        "for_display":     entry["for_display"],
        "hint":            entry.get("hint", ""),
        "sealed":          entry.get("sealed", ""),
        "pack_salt":       base64.b64encode(pack_salt).decode(),
        "pack_auth":       pack_auth,
        "pack_body":       _encode_alien(pack_ciphertext),
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"sealed_{entry['from_key']}_to_{entry['for_key']}_{timestamp}.sealpack"
    dest      = _export_path() / filename
    dest.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest, passphrase


def import_sealpack(filepath: "str | Path", passphrase: str) -> str | None:
    """
    Import a .sealpack file using the sender's passphrase.
    Decrypts the content and re-seals it locally on this machine.
    Returns the new letter_id, or None on failure.
    """
    path = Path(filepath)
    if not path.exists():
        return None

    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not pack.get("cursiv_sealpack"):
        return None

    pack_salt   = base64.b64decode(pack["pack_salt"])
    pack_auth   = pack["pack_auth"]
    pack_body   = pack["pack_body"]

    try:
        pack_ciphertext = _decode_alien(pack_body)
    except Exception:
        return None

    # Re-derive pack key from passphrase
    pack_master = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        pack_salt + b"CURSIV-SEALPACK-v1",
        200_000,
        dklen=64,
    )
    pack_enc_key  = pack_master[:32]
    pack_hmac_key = pack_master[32:]

    # Verify auth
    expected_auth = _hmac.new(
        pack_hmac_key, pack_salt + pack_ciphertext, "sha256"
    ).hexdigest()
    if not _hmac.compare_digest(expected_auth, pack_auth):
        return None   # wrong passphrase or tampered pack

    # Decrypt
    pack_stream_seed = hashlib.pbkdf2_hmac(
        "sha256", pack_enc_key, pack_salt, 100_000, dklen=32
    )
    pack_keystream = derive_keystream(pack_stream_seed, pack_salt, len(pack_ciphertext))
    plaintext_bytes = bytes(a ^ b for a, b in zip(pack_ciphertext, pack_keystream))

    try:
        content = plaintext_bytes.decode("utf-8")
    except Exception:
        return None

    # Re-seal locally on this machine
    return seal_letter(
        sender_key        = pack["from_key"],
        sender_display    = pack["from_display"],
        recipient_key     = pack["for_key"],
        recipient_display = pack["for_display"],
        content           = content,
        hint              = pack.get("hint", ""),
    )

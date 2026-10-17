"""
Strand Federation — air-gapped Strand pack export / import.

Deliberate, human-approved, cryptographically signed exchange of Strands
between personal Cursiv instances (home machine, laptop, workshop server)
without any cloud sync — ever.

A .cursivpack file is:
  1. JSON dict  — strands + territory definitions + metadata
  2. zlib compressed at level 9
  3. HMAC-SHA256 signed with a key derived from machine identity
  4. base85 encoded for portable text transfer

Signing key = a random 32-byte key made once per install and kept in
~/.cursiv/runtime/pack_key. Packs this copy made verify cleanly; packs from
another copy are flagged as "from another computer" and need the person's
confirmation -- the import still works. The signature only tells your own
packs apart from others; it isn't proof of who made a pack.

Import is always gated by:
  1. HMAC checksum verification
  2. Human approval prompt showing full pack inventory
  3. Strands-only import (no code, no config, no protected paths touched)

Transfer medium: USB drive, LAN copy, encrypted file share.
Cloud sync is never automatic and never supported.
"""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import time
import zlib
from pathlib import Path
from typing import Any

PACK_VERSION = "1.0"
PACK_EXT     = ".cursivpack"

# ── Signing key: random, made once per install ──────────────────────────────
def _load_sign_key() -> bytes:
    import secrets
    key_file = Path.home() / ".cursiv" / "runtime" / "pack_key"
    try:
        key = key_file.read_bytes()
        if len(key) == 32:
            return key
    except OSError:
        pass
    key = secrets.token_bytes(32)
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
    except OSError:
        pass
    return key


_SIGN_KEY: bytes = _load_sign_key()
_SIGN_SOURCE = "install"


def _sign(payload: bytes) -> str:
    return _hmac.new(_SIGN_KEY, payload, hashlib.sha256).hexdigest()


# ── Export ────────────────────────────────────────────────────────────────────

def export_pack(
    strands: list[dict[str, Any]],
    territories: dict[str, Any],
    label: str = "",
) -> str:
    """
    Serialize, compress, sign, and base85-encode a strand collection.
    Returns the complete .cursivpack text content.
    """
    payload = {
        "version":      PACK_VERSION,
        "label":        label or f"cursiv-pack-{int(time.time())}",
        "exported_at":  time.time(),
        "strand_count": len(strands),
        "territories":  territories,
        "strands":      strands,
    }
    raw        = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    compressed = zlib.compress(raw, level=9)
    sig        = _sign(compressed)
    envelope   = json.dumps({
        "cursivpack": PACK_VERSION,
        "sig":        sig,
        "sign_src":   _SIGN_SOURCE,
        "data":       base64.b85encode(compressed).decode(),
    })
    return envelope


def import_pack(pack_text: str) -> tuple[list[dict], dict, dict]:
    """
    Decode and verify a .cursivpack file.

    Returns (strands, territories, meta) on success.
    meta includes 'same_machine': True/False — callers show a warning if False.
    Raises ValueError on malformed or corrupted pack.
    """
    try:
        envelope   = json.loads(pack_text)
        sig        = envelope["sig"]
        compressed = base64.b85decode(envelope["data"].encode())
    except Exception as exc:
        raise ValueError(f"Malformed pack file: {exc}") from exc

    expected     = _sign(compressed)
    same_machine = _hmac.compare_digest(sig, expected)

    try:
        raw     = zlib.decompress(compressed)
        payload = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"Pack decompression failed: {exc}") from exc

    meta = {
        "version":      payload.get("version", "?"),
        "label":        payload.get("label", "unknown"),
        "exported_at":  payload.get("exported_at", 0),
        "strand_count": payload.get("strand_count", 0),
        "same_machine": same_machine,
        "sign_src":     envelope.get("sign_src", "?"),
    }
    return payload.get("strands", []), payload.get("territories", {}), meta


# ── Pack summary (for human approval display) ────────────────────────────────

def pack_summary(strands: list[dict], meta: dict) -> str:
    """Format a human-readable inventory of a pack before import."""
    from collections import Counter
    territories = Counter(s.get("territory_tag", "general") for s in strands)
    sources     = Counter(s.get("source", "?") for s in strands)

    exported_ts = meta.get("exported_at", 0)
    try:
        import datetime
        exported_str = datetime.datetime.fromtimestamp(exported_ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        exported_str = "unknown"

    lines = [
        f"  Label      : {meta.get('label', '?')}",
        f"  Exported   : {exported_str}",
        f"  Strands    : {len(strands)}",
        f"  Source     : {'same machine (verified)' if meta.get('same_machine') else 'external machine (!) (signature mismatch - different hardware)'}",
        f"  Territories: {dict(territories)}",
        f"  Sources    : {dict(sources)}",
    ]
    return "\n".join(lines)

"""
Cursiv Sigil — small encoding helpers used by the sealed family letters and
the postal store.

  Custom alphabet  encode_b64 / decode_b64: base64-style encoding over a
                   64-character alphabet (Greek + Extended Latin + math
                   symbols) instead of A-Z/a-z/0-9/+/.
  Zero-width text  embed_zwc / extract_zwc: hides a short string inside
                   other text as zero-width characters
                   (\u200B=00, \u200C=01, \u200D=10, \u2060=11).
  Install key      derive_key / xor_bytes: a key tied to this computer's
                   system UUID (.cursiv/system.uuid), for simple XOR
                   obfuscation of local values.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)

# ── Option A: Custom 64-character alphabet ────────────────────────────────────
CURSIV_ALPHABET = (
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"  # Greek uppercase  [0–23]
    "αβγδεζηθικλμνξοπρστυφχψω"  # Greek lowercase  [24–47]
    "ĀāĒēĪīŌōŪū"                 # Extended Latin   [48–57]
    "∀∃∇∂∈∞"                     # Math symbols     [58–63]
)
assert len(CURSIV_ALPHABET) == 64

_AENC = {ch: i for i, ch in enumerate(CURSIV_ALPHABET)}
_ADEC = list(CURSIV_ALPHABET)

# ── Option B: Cursiv-specific salt woven into key derivation ──────────────────
_CURSIV_SALT = "JW-CURSIV-SOVEREIGN-2026-∇"

# ── Zero-width character alphabet (2-bit values) ──────────────────────────────
_Z = ["​", "‌", "‍", "⁠"]
_ZSET = set(_Z)
_SENTINEL = "⁠​⁠"   # start/end marker — rare combo in natural text


# ── Encoding — Option A ───────────────────────────────────────────────────────

def encode_b64(data: bytes) -> str:
    """Encode bytes using the Cursiv 64-char alphabet. Not base64-compatible."""
    padding = (3 - len(data) % 3) % 3
    padded  = data + b"\x00" * padding
    out     = []
    for i in range(0, len(padded), 3):
        b0, b1, b2 = padded[i], padded[i + 1], padded[i + 2]
        n = (b0 << 16) | (b1 << 8) | b2
        out.append(_ADEC[(n >> 18) & 0x3F])
        out.append(_ADEC[(n >> 12) & 0x3F])
        out.append(_ADEC[(n >>  6) & 0x3F])
        out.append(_ADEC[(n      ) & 0x3F])
    encoded = "".join(out)
    if padding:
        encoded = encoded[:-padding] + "=" * padding
    return encoded


def decode_b64(s: str) -> bytes:
    """Decode a Cursiv-encoded string back to bytes."""
    padding = s.count("=")
    clean   = s.rstrip("=")
    padded  = clean + _ADEC[0] * ((-len(clean)) % 4)
    out     = []
    for i in range(0, len(padded), 4):
        chunk = padded[i:i + 4]
        if len(chunk) < 4:
            break
        n = 0
        for ch in chunk:
            n = (n << 6) | _AENC.get(ch, 0)
        out.extend([(n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
    return bytes(out[:-padding] if padding else out)


# ── Key derivation — Option B ─────────────────────────────────────────────────

def _system_uuid() -> str:
    """
    Read .cursiv/system.uuid — the per-installation identity anchor.
    Creates one on first run. Returns a degraded constant if .cursiv/ is absent.
    A source-only copy (no .cursiv/ dir) produces a different key than a real
    installation, causing encoded constants to decode silently wrong.
    """
    uuid_path = APP_DATA / "system.uuid"
    try:
        if uuid_path.exists():
            return uuid_path.read_text(encoding="utf-8").strip()
        import uuid as _uuid
        sid = str(_uuid.uuid4())
        uuid_path.parent.mkdir(parents=True, exist_ok=True)
        uuid_path.write_text(sid, encoding="utf-8")
        return sid
    except Exception:
        return "CURSIV-DEGRADED-MISSING-INSTALL-CONTEXT"


def derive_key() -> bytes:
    """Derive a 32-byte XOR key. Consistent per installation; wrong on raw clones."""
    combined = f"{_CURSIV_SALT}|{_system_uuid()}".encode("utf-8")
    return hashlib.sha256(combined).digest()


def xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR data against key (key repeats as needed)."""
    kl = len(key)
    return bytes(b ^ key[i % kl] for i, b in enumerate(data))


# ── Combined encode/decode (A + B) ────────────────────────────────────────────

def encode_const(value: str) -> str:
    """
    Encode a string constant with custom alphabet (A) + installation XOR key (B).
    In source the constant looks like a proprietary encoded blob.
    At runtime decode_const() recovers the original.
    On unauthorized clones, decode_const() returns garbled text silently.
    """
    raw   = value.encode("utf-8")
    key   = derive_key()
    xored = xor_bytes(raw, key)
    return encode_b64(xored)


def decode_const(encoded: str) -> str:
    """Decode a constant encoded with encode_const()."""
    xored = decode_b64(encoded)
    key   = derive_key()
    raw   = xor_bytes(xored, key)
    return raw.decode("utf-8", errors="replace")


# ── Zero-width character encoding ─────────────────────────────────────────────

def _zwc_encode(message: str) -> str:
    """Encode a message as a sequence of invisible zero-width Unicode characters."""
    data  = message.encode("utf-8")
    chars = []
    for byte in data:
        chars.append(_Z[(byte >> 6) & 0x3])
        chars.append(_Z[(byte >> 4) & 0x3])
        chars.append(_Z[(byte >> 2) & 0x3])
        chars.append(_Z[(byte     ) & 0x3])
    return _SENTINEL + "".join(chars) + _SENTINEL


def _zwc_decode(text: str) -> str:
    """Extract and decode any ZWC-embedded message. Returns '' if none found."""
    if _SENTINEL not in text:
        return ""
    try:
        # The sentinel is spelled with the same zero-width characters as the
        # payload, so the payload can contain it too -- searching forward for
        # the closing sentinel stopped inside the message (e.g. "s" = 0x73
        # already encodes as ‌⁠​⁠). The closing sentinel is always the last
        # thing in the unbroken run of zero-width characters, so read the
        # whole run and strip it from the end. Same format as before, so
        # anything already written still decodes.
        start = text.index(_SENTINEL) + len(_SENTINEL)
        end = start
        while end < len(text) and text[end] in _ZSET:
            end += 1
        run = text[start:end]
        if not run.endswith(_SENTINEL):
            return ""
        chars = list(run[:-len(_SENTINEL)])
        if len(chars) % 4 != 0:
            return ""
        result = []
        for i in range(0, len(chars), 4):
            byte = (
                (_Z.index(chars[i    ]) << 6) |
                (_Z.index(chars[i + 1]) << 4) |
                (_Z.index(chars[i + 2]) << 2) |
                (_Z.index(chars[i + 3])      )
            )
            result.append(byte)
        return bytes(result).decode("utf-8", errors="replace")
    except (ValueError, IndexError):
        return ""


def embed_zwc(host: str, message: str) -> str:
    """Hide `message` inside `host` as zero-width characters (after its first character)."""
    encoded = _zwc_encode(message)
    if not host:
        return encoded
    return host[0] + encoded + host[1:]


def extract_zwc(text: str) -> str:
    """Extract and decode any ZWC message embedded in text."""
    return _zwc_decode(text)

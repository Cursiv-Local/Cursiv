"""
Cursiv — family letter sealing (shared by the runtime and scripts/seal_family_letters.py).

Each family member's letter, context and profile are stored only in encrypted
form, in sealed_letters.json next to this file. One copy is sealed per name
token that may open it (every word of the member's full name, plus aliases),
under a key derived from  "<name token>|<YYYY-MM-DD birth date>".

Standard library only (scrypt + HMAC-SHA256 keystream + HMAC tag), so the
frozen build needs no extra packages.

Honest limit: the birth date is the real secret. Someone who already knows a
member's name and birth date can open their letter -- the same thing the
babel activation itself has always required.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

SEALED_FILE = Path(__file__).parent / "sealed_letters.json"

# scrypt cost: ~0.1-0.3 s per attempt on a normal PC, so unlocking stays quick
# but guessing birth dates is slow.
_N, _R, _P = 2 ** 15, 8, 1
_MAXMEM = 128 * 1024 * 1024
_VERIFY_LABEL = b"cursiv-family-v1:verify"


def name_tokens(name: str) -> list[str]:
    return [t for t in (w.strip(".,;:!?").lower() for w in name.split()) if t]


def derive(token: str, dob_iso: str, salt: bytes) -> tuple[bytes, bytes, str]:
    """Returns (enc_key, mac_key, verifier) for one name token + birth date."""
    km = hashlib.scrypt(f"{token}|{dob_iso}".encode("utf-8"), salt=salt,
                        n=_N, r=_R, p=_P, maxmem=_MAXMEM, dklen=64)
    enc_key, mac_key = km[:32], km[32:]
    verifier = hmac.new(mac_key, _VERIFY_LABEL, "sha256").hexdigest()
    return enc_key, mac_key, verifier


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(enc_key + nonce + counter.to_bytes(4, "big")).digest()
        counter += 1
    return bytes(out[:length])


def seal(payload: dict, enc_key: bytes, mac_key: bytes) -> dict:
    nonce = os.urandom(16)
    plain = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ct = bytes(a ^ b for a, b in zip(plain, _keystream(enc_key, nonce, len(plain))))
    tag = hmac.new(mac_key, nonce + ct, "sha256").hexdigest()
    return {"n": base64.b64encode(nonce).decode(), "c": base64.b64encode(ct).decode(), "t": tag}


def open_sealed(entry: dict, enc_key: bytes, mac_key: bytes) -> dict | None:
    nonce, ct = base64.b64decode(entry["n"]), base64.b64decode(entry["c"])
    if not hmac.compare_digest(hmac.new(mac_key, nonce + ct, "sha256").hexdigest(), entry["t"]):
        return None
    plain = bytes(a ^ b for a, b in zip(ct, _keystream(enc_key, nonce, len(ct))))
    try:
        return json.loads(plain.decode("utf-8"))
    except Exception:
        return None


def build_sealed(source: dict) -> dict:
    """Seal a plaintext source dict (see scripts/seal_family_letters.py) into the shipped format."""
    salt = os.urandom(16)
    entries: dict[str, dict] = {}
    for m in source["members"]:
        tokens = set(name_tokens(m["stored_name"])) | {a.lower() for a in source.get("aliases", {}).get(m["key"], [])}
        payload = {
            "member": {k: m[k] for k in ("key", "display", "relation", "dob", "stored_name", "letter", "context")},
            "allowed_tokens": sorted(tokens),
            "jw_header": source["jw_header"],
            "system_template": source["system_template"],
        }
        for token in sorted(tokens):
            enc_key, mac_key, verifier = derive(token, m["dob"], salt)
            entries[verifier] = seal(payload, enc_key, mac_key)
    return {"version": 1, "salt": base64.b64encode(salt).decode(), "entries": entries}

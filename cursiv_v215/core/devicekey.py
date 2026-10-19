"""
This installation's signing key (field network Phase 0, docs/FIELD-NETWORK.md; R4).

Each Cursiv installation has an Ed25519 key pair, made on first use. It signs the
**head** of the field log (the latest entry's number and fingerprint, which through the
chain covers every entry before it) whenever the log is shared or exported, so anyone
can check that records came from this installation and weren't changed, added or removed.

The private key never leaves this computer on purpose: it is stored protected
(Windows: encrypted for this Windows user; macOS: the login Keychain), in
~/.cursiv/device_key.json. On a Cursiv USB it is stored readable on the drive (it has
to work on any PC). If the key can't be read back (another Windows user, a copied
file), a new key is made and the old public key is kept in the file's history, so a
reader can see the key changed and when.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

HEAD_FORMAT = "cursiv-head-1"
_cache: dict = {}


def key_file() -> Path:
    return Path.home() / ".cursiv" / "device_key.json"


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def key_id(public_b64: str) -> str:
    """A short, stable name for a public key: the first 16 hex characters of its SHA-256."""
    return hashlib.sha256(base64.b64decode(public_b64)).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new(history: list) -> tuple[Ed25519PrivateKey, dict]:
    from cursiv_v215.core import atomic, keystore
    priv = Ed25519PrivateKey.generate()
    raw = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                             serialization.NoEncryption())
    pub = _b64(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    data = {"public_key": pub, "key_id": key_id(pub), "created_utc": _now(),
            "private_key": keystore.protect(_b64(raw)), "history": history}
    key_file().parent.mkdir(parents=True, exist_ok=True)
    atomic.write_text(key_file(), json.dumps(data, indent=2))
    return priv, data


def load() -> tuple[Ed25519PrivateKey, dict]:
    """This installation's key pair (made on first use)."""
    path = key_file()
    if _cache.get("path") == path and "priv" in _cache:
        return _cache["priv"], _cache["data"]
    from cursiv_v215.core import keystore
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    priv = None
    if data:
        try:
            raw = base64.b64decode(keystore.reveal(data.get("private_key", "")))
            priv = Ed25519PrivateKey.from_private_bytes(raw)
            mine = _b64(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
            if mine != data.get("public_key"):
                priv = None
        except Exception:
            priv = None
    if priv is None:
        history = list((data or {}).get("history", []))
        if data and data.get("public_key"):
            history.append({"public_key": data["public_key"], "key_id": data.get("key_id"),
                            "created_utc": data.get("created_utc"), "replaced_utc": _now(),
                            "why": "the saved key couldn't be read on this computer or account"})
        priv, data = _new(history)
    _cache.update(path=path, priv=priv, data=data)
    return priv, data


def public_key() -> str:
    return load()[1]["public_key"]


def _canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sign(obj: dict) -> dict:
    """{"signed": obj, "public_key", "key_id", "signature"} over the canonical JSON of obj."""
    priv, data = load()
    return {"signed": obj, "public_key": data["public_key"], "key_id": data["key_id"],
            "signature": _b64(priv.sign(_canonical(obj)))}


def verify(envelope: dict) -> bool:
    """True if the signature matches the signed object and the public key in the envelope."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(envelope["public_key"]))
        pub.verify(base64.b64decode(envelope["signature"]), _canonical(envelope["signed"]))
        return key_id(envelope["public_key"]) == envelope.get("key_id", key_id(envelope["public_key"]))
    except (InvalidSignature, KeyError, ValueError, TypeError):
        return False


def head(rows: list[dict], device: str) -> dict:
    """The head of a chain: its device label, entry count and latest fingerprint."""
    last = rows[-1] if rows else {}
    return {"format": HEAD_FORMAT, "device": device, "entries": len(rows),
            "seq": last.get("seq", 0), "hash": last.get("hash", ""), "signed_utc": _now()}


def signed_head(rows: list[dict], device: str) -> dict:
    return sign(head(rows, device))

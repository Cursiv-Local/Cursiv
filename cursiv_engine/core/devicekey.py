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

A key can also be protected with a passphrase (U105, for drives, where it is otherwise readable by
anyone holding the drive): protect(passphrase) re-stores the same key encrypted (scrypt + Fernet, as the
vault does), so its id and every pin of it stay the same. While it's locked nothing is signed: load()
raises KeyLocked instead of making a new key, which would give the drive a new identity that main
computers refuse. unlock(passphrase) opens it for this run of Cursiv.
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
PASSPHRASE_PREFIX = "pp1:"           # "pp1:" + base64(salt) + ":" + Fernet token of the raw key, base64
MIN_PASSPHRASE = 10
_cache: dict = {}


class KeyLocked(ValueError):
    """The signing key is passphrase-protected and hasn't been unlocked in this run of Cursiv."""

    def __init__(self):
        super().__init__("the signing key is protected by a passphrase and is locked; unlock it to sign "
                         "(Field Notebook: Signing key…)")


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
    from cursiv_engine.core import atomic, keystore
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
    from cursiv_engine.core import keystore
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    priv = None
    if data and str(data.get("private_key", "")).startswith(PASSPHRASE_PREFIX):
        raise KeyLocked()                                   # never replaced while locked
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


def _read() -> dict | None:
    try:
        return json.loads(key_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def protected() -> bool:
    """Is this installation's key stored under a passphrase?"""
    return str((_read() or {}).get("private_key", "")).startswith(PASSPHRASE_PREFIX)


def unlocked() -> bool:
    return _cache.get("path") == key_file() and "priv" in _cache


def protect(passphrase: str) -> dict:
    """Store this installation's key under a passphrase (the same key: its id and pins don't change).
    The key must be readable or unlocked now. Returns the key's public data."""
    from cursiv_engine.core import atomic, vault
    import os
    if len(passphrase or "") < MIN_PASSPHRASE:
        raise ValueError(f"use a passphrase of at least {MIN_PASSPHRASE} characters")
    priv, data = load()
    raw = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                             serialization.NoEncryption())
    salt = os.urandom(16)
    token = vault.derive(passphrase, salt).encrypt(raw).decode("ascii")
    data = dict(data, private_key=PASSPHRASE_PREFIX + _b64(salt) + ":" + token, protected_utc=_now())
    atomic.write_text(key_file(), json.dumps(data, indent=2))
    if unlock(passphrase)[1]["key_id"] != data["key_id"]:       # read back: the stored key opens
        raise OSError("the protected key didn't read back the same; nothing else was changed")
    return {k: data[k] for k in ("public_key", "key_id")}


def unlock(passphrase: str) -> tuple[Ed25519PrivateKey, dict]:
    """Open a passphrase-protected key for this run of Cursiv. ValueError if the passphrase is wrong."""
    from cryptography.fernet import InvalidToken
    from cursiv_engine.core import vault
    data = _read()
    stored = str((data or {}).get("private_key", ""))
    if not stored.startswith(PASSPHRASE_PREFIX):
        return load()
    try:
        salt_b64, token = stored[len(PASSPHRASE_PREFIX):].split(":", 1)
        raw = vault.derive(passphrase or "", base64.b64decode(salt_b64)).decrypt(token.encode("ascii"))
        priv = Ed25519PrivateKey.from_private_bytes(raw)
    except (InvalidToken, ValueError, TypeError):
        raise ValueError("that passphrase doesn't open the signing key") from None
    mine = _b64(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    if mine != data.get("public_key"):
        raise ValueError("the stored key doesn't match its public key; it wasn't used")
    _cache.update(path=key_file(), priv=priv, data=data)
    return priv, data


def lock() -> None:
    _cache.clear()


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

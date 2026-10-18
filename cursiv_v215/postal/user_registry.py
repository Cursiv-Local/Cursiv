# ┌─────────────────────────────────────────────────────────────────────────────┐
# │  CURSIV POSTAL — USER REGISTRY                                              │
# │  Local address book: display names → Ed25519 public keys.                  │
# │  No server. No central authority. Works offline.                            │
# │  Public keys are not secrets — they are meant to be shared.                 │
# └─────────────────────────────────────────────────────────────────────────────┘
"""
User Registry — local contacts and identity management for Cursiv postal.

Each Cursiv installation has one identity (name + Ed25519 keypair).
Contacts are stored locally: .cursiv/postal/contacts.json

To write to someone you need their public key (44-char base64url string).
They share it with you once. You store it. Letters between you are signed
and verified forever after — no server, no lookup, no dependency.

Identity setup (one-time):
    postal setup <your_name>
    → generates Ed25519 keypair
    → saves display name
    → prints your public key to share

Adding a contact:
    postal add user <name> <pubkey>

Writing to a contact by name:
    postal write to <name>
    → system looks up their key automatically

Key ID = first 8 chars of SHA-256(pubkey) — short fingerprint for display.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

from cursiv_v215.postal.postal_sign import (
    identity_exists,
    generate_identity,
    my_public_key,
    key_id    as _key_id,
    rotate_key,
    get_key_history,
)

# ── Storage ───────────────────────────────────────────────────────────────────
_POSTAL_DIR    = APP_DATA / "postal"
_CONTACTS_FILE = _POSTAL_DIR / "contacts.json"
_IDENTITY_FILE = _POSTAL_DIR / "identity_meta.json"


# ── Identity ──────────────────────────────────────────────────────────────────

def setup_identity(display_name: str) -> dict[str, str]:
    """
    One-time setup: generate Ed25519 keypair and save display name.
    If an identity already exists, this regenerates the keypair — use carefully.
    Returns {"name": ..., "key_id": ..., "pubkey": ...}
    """
    _POSTAL_DIR.mkdir(parents=True, exist_ok=True)
    pubkey = generate_identity()
    kid    = _key_id(pubkey)
    meta   = {
        "name":     display_name.strip(),
        "key_id":   kid,
        "pubkey":   pubkey,
        "created":  datetime.now().isoformat(),
    }
    _IDENTITY_FILE.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return meta


def load_identity() -> dict[str, str] | None:
    """Return this user's identity metadata, or None if not set up."""
    if not _IDENTITY_FILE.exists():
        return None
    try:
        return json.loads(_IDENTITY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def my_identity() -> dict[str, str] | None:
    """
    Return the current user's full identity dict, refreshing pubkey from
    the live keypair in case the metadata file got stale.
    Returns None if identity has never been set up.
    """
    if not identity_exists():
        return None
    meta = load_identity()
    # Refresh pubkey from live keypair
    live_pubkey = my_public_key()
    if live_pubkey is None:
        return meta  # shouldn't happen but degrade gracefully
    if meta is None:
        meta = {
            "name":    "unknown",
            "key_id":  _key_id(live_pubkey),
            "pubkey":  live_pubkey,
            "created": datetime.now().isoformat(),
        }
    else:
        meta["pubkey"] = live_pubkey
        meta["key_id"] = _key_id(live_pubkey)
    return meta


# ── Contacts ──────────────────────────────────────────────────────────────────

def _load_contacts() -> dict[str, Any]:
    if not _CONTACTS_FILE.exists():
        return {}
    try:
        return json.loads(_CONTACTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_contacts(contacts: dict[str, Any]) -> None:
    _POSTAL_DIR.mkdir(parents=True, exist_ok=True)
    _CONTACTS_FILE.write_text(
        json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def add_contact(display_name: str, pubkey_b64: str) -> dict[str, str]:
    """
    Register a contact by name and public key.
    Returns the contact dict.
    Raises ValueError if the public key is invalid.
    """
    from cursiv_v215.postal.postal_sign import _b64_to_pubkey
    if _b64_to_pubkey(pubkey_b64) is None:
        raise ValueError(f"Invalid Ed25519 public key: {pubkey_b64!r}")

    contacts = _load_contacts()
    name     = display_name.strip()
    entry    = {
        "name":    name,
        "pubkey":  pubkey_b64,
        "key_id":  _key_id(pubkey_b64),
        "added":   datetime.now().isoformat(),
    }
    contacts[name.lower()] = entry
    _save_contacts(contacts)
    return entry


def remove_contact(display_name: str) -> bool:
    contacts = _load_contacts()
    key      = display_name.strip().lower()
    if key not in contacts:
        return False
    del contacts[key]
    _save_contacts(contacts)
    return True


def lookup_contact(name_or_key: str) -> dict[str, str] | None:
    """
    Look up a contact by display name (case-insensitive) or key_id prefix.
    Returns contact dict or None.
    """
    contacts = _load_contacts()
    query    = name_or_key.strip().lower()
    # Exact name match
    if query in contacts:
        return contacts[query]
    # Partial key_id match
    for entry in contacts.values():
        if entry.get("key_id", "").startswith(query):
            return entry
    return None


def list_contacts() -> list[dict[str, str]]:
    """All contacts sorted alphabetically by name."""
    contacts = _load_contacts()
    return sorted(contacts.values(), key=lambda c: c.get("name", "").lower())


def lookup_pubkey(name_or_key: str) -> str | None:
    """Return a contact's public key string, or None."""
    contact = lookup_contact(name_or_key)
    return contact["pubkey"] if contact else None


def resolve_recipient(name_or_key: str) -> tuple[str, str] | None:
    """
    Resolve a recipient name/key to (display_name, pubkey_b64).
    Returns None if the contact is not found.
    """
    contact = lookup_contact(name_or_key)
    if contact is None:
        return None
    return contact["name"], contact["pubkey"]


# ── Key rotation ──────────────────────────────────────────────────────────────

def rotate_identity(
    reason:      str  = "manual rotation",
    compromised: bool = False,
) -> dict[str, str]:
    """
    Retire the current Ed25519 keypair, generate a fresh one, and update
    the identity metadata file.

    compromised=True activates coherence degradation: any letter later
    verified against the retired key returns shifted content — plausible
    but wrong. The fraction of corruption grows with key age (10% → 65%).
    The attacker sees output. They never see truth.

    The old key is archived locally. PBKDF2 encryption uses display names
    (not keys), so all existing letters remain fully decryptable.

    Returns {"old_key_id": ..., "new_key_id": ..., "new_pubkey": ...}
    """
    result  = rotate_key(reason=reason, compromised=compromised)
    # Refresh identity_meta with new pubkey
    meta    = load_identity() or {}
    meta["pubkey"]     = result["new_pubkey"]
    meta["key_id"]     = result["new_key_id"]
    meta["rotated_at"] = __import__("datetime").datetime.now().isoformat()
    _POSTAL_DIR.mkdir(parents=True, exist_ok=True)
    _IDENTITY_FILE.write_text(
        __import__("json").dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return result


def key_rotation_history() -> list[dict]:
    """Return all retired key records for this identity, newest first."""
    return get_key_history()

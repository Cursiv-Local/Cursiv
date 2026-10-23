"""
Cursiv Postal — sealed encrypted letters between any two principals.

Letters are encrypted to a specific sender + recipient pair on a specific
machine. The seal.uuid (unique to this Cursiv installation) is required
to derive decryption keys. A clone of the repository without this file
cannot decrypt a single letter.

Contents are never written to disk in plaintext. Ever.
"""
from __future__ import annotations

from cursiv_engine.postal.sealed_store import (
    seal_letter,
    open_letter,
    get_sealed_entry,
    get_sig_status,
    letters_for,
    letters_from,
    all_letters,
    delete_sealed,
    export_sealpack,
    import_sealpack,
)
from cursiv_engine.postal.council_reader import council_walkthrough
from cursiv_engine.postal.user_registry import (
    setup_identity,
    my_identity,
    add_contact,
    remove_contact,
    lookup_contact,
    list_contacts,
    resolve_recipient,
    rotate_identity,
    key_rotation_history,
)

__all__ = [
    "seal_letter",
    "open_letter",
    "get_sealed_entry",
    "get_sig_status",
    "letters_for",
    "letters_from",
    "all_letters",
    "delete_sealed",
    "export_sealpack",
    "import_sealpack",
    "council_walkthrough",
    "setup_identity",
    "my_identity",
    "add_contact",
    "remove_contact",
    "lookup_contact",
    "list_contacts",
    "resolve_recipient",
    "rotate_identity",
    "key_rotation_history",
]

"""
Which features Cursiv shows: the research profile (the default) or everything.

The research profile keeps the window focused on field work: the field notebook,
documents, calculations, the offline reference and privacy. Personal features
(the phone app, coding help, agents and builder tools) are hidden from Tools, help
and the title bar until Settings → Appearance → "Show personal features".

Family letters, the legacy vault and personal letters were removed from the public
app in U97. Their old commands get REMOVED_NOTE; letters and data already saved on a
computer are left where they are.
"""
from __future__ import annotations

PROFILE_KEY = "profile"          # "personal" shows everything; anything else is the research profile
REMOVED_NOTE = ('Family letters, the legacy vault and personal letters were removed from Cursiv. '
                'Letters and data already saved on this computer were not deleted.')


def letters_command(text: str) -> bool:
    """The removed letter/vault commands, not ordinary discussion or file intent."""
    cmd = text.strip().lower()
    return (cmd in ('letters', 'letters for me', 'letters from me', 'legacy', 'write to') or
            cmd.startswith(('open letter ', 'letter ', 'council letter ', 'seal export ', 'seal import ',
                            'postal ', 'legacy ', 'write to ', 'babel i am ', 'babel: i am ')))


def personal() -> bool:
    try:
        from cursiv_engine.chat import keys
        return keys.saved_key(PROFILE_KEY) == "personal"
    except Exception:
        return False


def research() -> bool:
    return not personal()


def set_personal(on: bool) -> None:
    from cursiv_engine.chat import keys
    keys.store_key(PROFILE_KEY, "personal" if on else "")

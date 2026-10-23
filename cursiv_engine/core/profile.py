"""
Which features Cursiv shows: the research profile (the default) or everything.

The research profile keeps the window focused on field work: the field notebook,
documents, calculations, the offline reference and privacy. Personal features
(family letters, the legacy vault, the phone app, coding help, the council,
agents and builder tools) are hidden from Tools, help and the title bar.
Nothing is removed. Letter/vault commands also require Settings → Appearance →
"Show personal features"; they no longer bypass the hidden UI.
"""
from __future__ import annotations

PROFILE_KEY = "profile"          # "personal" shows everything; anything else is the research profile
PERSONAL_NOTE = 'Personal letters and the legacy vault are hidden. Enable Settings → Appearance → Show personal features to use them.'


def personal_command(text: str) -> bool:
    """Only established letter/vault commands, not ordinary discussion or file intent."""
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

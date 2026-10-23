"""
Which features Cursiv shows: the research profile (the default) or everything.

The research profile keeps the window focused on field work: the field notebook,
documents, calculations, the offline reference and privacy. Personal features
(family letters, the legacy vault, the phone app, coding help, the council,
agents and builder tools) are hidden from Tools, help and the title bar.
Nothing is removed: typed commands still work, and Settings → Appearance →
"Show personal features" brings them all back.
"""
from __future__ import annotations

PROFILE_KEY = "profile"          # "personal" shows everything; anything else is the research profile


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

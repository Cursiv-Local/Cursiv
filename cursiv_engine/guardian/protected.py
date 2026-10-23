"""Files the AI's write tool may never change, even with file access on and
the person approving: saved keys, logins, and Cursiv's own security code."""
from __future__ import annotations

PROTECTED_PATHS: tuple[str, ...] = (
    ".cursiv/config.json",          # saved AI keys and settings
    ".cursiv/runtime/",             # login hashes, owner code
    ".cursiv/strands.jsonl",        # saved notes
    "cursiv_engine/guardian/",        # login and this list
    "secrets.bat",
)


def is_protected_path(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    return any(item in p for item in PROTECTED_PATHS)

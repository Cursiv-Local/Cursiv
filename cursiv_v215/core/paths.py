"""
Where Cursiv keeps the data that belongs with the program: settings and saved keys
(config.json), memories, conversations' strands, the search cache, letters, ...

- Run from source, or the Windows app: the .cursiv folder next to the program, as
  always (the Windows installer never removes it, so updates keep the data).
- The macOS app: ~/Library/Application Support/Cursiv. A Mac app is replaced as a
  whole when it's updated, so nothing can be kept inside it.
- CURSIV_APP_DATA, if set, wins (tests, special setups).

Personal data in the home folder (~/.cursiv: field log, documents, demo) is separate
and unchanged.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROGRAM_ROOT = Path(__file__).resolve().parent.parent.parent


def app_data_dir() -> Path:
    env = os.environ.get("CURSIV_APP_DATA")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cursiv"
    return PROGRAM_ROOT / ".cursiv"


APP_DATA = app_data_dir()


def portable_root() -> Path | None:
    value = os.environ.get('CURSIV_USB_ROOT')
    return Path(value).resolve() if os.environ.get('CURSIV_PORTABLE') == '1' and value else None


def save_reference(path: Path | str) -> str:
    """Portable references move with the drive; external references stay explicit."""
    path = Path(path).resolve()
    root = portable_root()
    if root and path.is_relative_to(root):
        return 'portable://' + path.relative_to(root).as_posix()
    return str(path)


def resolve_reference(value: str) -> Path:
    if not value.startswith('portable://'):
        return Path(value)
    root = portable_root()
    rel = Path(value[len('portable://'):])
    if root is None or rel.is_absolute() or rel.drive or '..' in rel.parts:
        raise ValueError('Portable reference unavailable or invalid')
    result = (root / rel).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Portable reference escapes the drive')
    return result

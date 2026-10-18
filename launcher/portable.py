"""
Portable (USB) mode -- Cursiv running straight off a drive made by
usb_maker.py, with nothing installed on the computer it's plugged into.

Layout of a Cursiv USB:
    <drive>\\Start Cursiv.bat      one click
    <drive>\\Cursiv\\               the program (Cursiv.exe + portable.cursiv marker)
    <drive>\\Ollama\\               the local AI engine (ollama.exe + lib)
    <drive>\\Models\\               AI models (Ollama's manifests + blobs)
    <drive>\\Home\\                 stands in for the user's home folder

activate() must run first thing in main.py, before any module computes
Path.home(): about twenty modules keep data under Path.home()/.cursiv, so
pointing USERPROFILE at <drive>\\Home keeps every memory, key and log on the
drive and nothing on the host PC. The real home is kept in CURSIV_REAL_HOME
for the read-only tools that look at the person's Downloads/Desktop.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "portable.cursiv"
FIELD_MARKER = "field.cursiv"          # a field copy: see apply_field_defaults()


def usb_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    app_dir = Path(sys.executable).resolve().parent
    return app_dir.parent if (app_dir / MARKER).exists() else None


def is_portable() -> bool:
    return os.environ.get("CURSIV_PORTABLE") == "1"


def activate() -> bool:
    root = usb_root()
    if root is None:
        return False
    home = root / "Home"
    try:
        home.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    if not os.environ.get("CURSIV_REAL_HOME"):      # kept on a second activate(); empty counts as unset
        os.environ["CURSIV_REAL_HOME"] = os.environ.get("USERPROFILE") or str(Path.home())
    os.environ["USERPROFILE"] = str(home)
    os.environ["HOME"] = str(home)
    os.environ["CURSIV_PORTABLE"] = "1"
    os.environ["CURSIV_USB_ROOT"] = str(root)
    os.environ["OLLAMA_MODELS"] = str(root / "Models")
    ollama_dir = root / "Ollama"
    if (ollama_dir / "ollama.exe").exists():
        os.environ["PATH"] = str(ollama_dir) + os.pathsep + os.environ.get("PATH", "")
    if (root / "Cursiv" / FIELD_MARKER).exists():
        apply_field_defaults(home)
    return True


def apply_field_defaults(home: Path) -> None:
    """The first time a field copy starts: offline mode on, no break notes, no learned
    guesses about the person (only what they save with "remember"). All three can be
    changed in Settings afterwards; this runs once."""
    done = home / ".cursiv" / "field_defaults_applied"
    if done.exists():
        return
    try:
        from cursiv_v215.core import netgate
        from cursiv_v215.chat import keys
        from cursiv_v215.memory import semantic
        netgate.set_offline(True)
        keys.store_key("break_notes", "off")
        semantic.set_learning(False)
        done.parent.mkdir(parents=True, exist_ok=True)
        done.write_text("Field defaults set on first start: offline on, break notes off, learning off.\n",
                        encoding="utf-8")
    except Exception:
        pass


def real_home() -> Path:
    return Path(os.environ.get("CURSIV_REAL_HOME") or Path.home())

"""
Undo U35's directory junctions for Cursiv's data folders (installed app only).

U35 replaced the program-folder data folders ({app}\\_internal\\.cursiv and
{app}\\.cursiv) with junctions to %USERPROFILE%\\.cursiv. Some Windows 11
setups refuse to let an app traverse such links ("WinError 448: untrusted
mount point"), which broke reading and writing data there.

settle_data_folders() runs at startup of the frozen app: any of those folders
that is a junction is removed (only the link -- the data lives in the home
folder) and replaced by a real folder filled with a copy of the home folder's
files. Real folders are left alone. The installer never deletes these folders
(it only replaces its own program files), so updates keep the data safe.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

HOME_DATA = Path(os.environ.get("CURSIV_DATA_DIR") or (Path.home() / ".cursiv"))


def _is_link(p: Path) -> bool:
    try:
        return p.is_junction() or p.is_symlink()
    except Exception:
        return False


def copy_all(src: Path, dest: Path) -> int:
    copied = 0
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        target = dest / f.relative_to(src)
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        copied += 1
    return copied


def unlink_one(folder: Path, log: list[str]) -> None:
    if not _is_link(folder):
        return
    os.rmdir(folder)          # removes the junction itself, never what it points to
    folder.mkdir(parents=True, exist_ok=True)
    n = copy_all(HOME_DATA, folder) if HOME_DATA.is_dir() else 0
    log.append(f"replaced junction {folder} with a real folder ({n} file(s) copied from {HOME_DATA})")


def settle_data_folders() -> list[str]:
    """Frozen (installed) app only. Safe to call on every startup."""
    log: list[str] = []
    if os.environ.get('CURSIV_PORTABLE') == '1' or not getattr(sys, "frozen", False) or sys.platform != "win32":
        return log
    app_dir = Path(sys.executable).resolve().parent
    internal = Path(getattr(sys, "_MEIPASS", app_dir / "_internal"))
    for folder in (internal / ".cursiv", app_dir / ".cursiv"):
        try:
            unlink_one(folder, log)
        except Exception as exc:
            log.append(f"error for {folder}: {exc}")
    if log:
        try:
            (HOME_DATA / "logs").mkdir(parents=True, exist_ok=True)
            with open(HOME_DATA / "logs" / "data_home.log", "a", encoding="utf-8") as fh:
                for line in log:
                    fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")
        except Exception:
            pass
    return log


# Kept for any caller still using the U35 name.
link_data_folders = settle_data_folders

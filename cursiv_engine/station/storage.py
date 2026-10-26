"""
Which drives the Field Station can see (docs/FIELD-STATION-PLAN.md, phases 2 and 9). Read-only: this
module never mounts, formats or writes to a drive; that comes in phase 9, with explicit user steps.

On Linux a drive is identified by its filesystem UUID (`lsblk`), never by /dev/sda-style names, which can
change between boots or plugs. Elsewhere (Windows during development) psutil's partition list is used and
the identifier is marked as not stable.

A drive is recognised as a Cursiv workspace when it has a named field notebook (Home/.cursiv/fieldlog/
notebook.json, U103) or a team share (cursiv-field-share/ at its top).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def workspace_info(mount: Path) -> dict | None:
    """The Cursiv workspace on a mounted drive, or None. Never raises for an unreadable drive."""
    from cursiv_engine.core import fieldlog
    notebook = mount / "Home" / ".cursiv" / "fieldlog"
    share = mount / "cursiv-field-share"
    info = {}
    try:
        ident = fieldlog.read_identity(notebook) if notebook.is_dir() else {}
    except (OSError, fieldlog.IdentityDamaged) as exc:
        ident = {"error": str(exc)}
    if ident:
        info["notebook"] = {k: ident[k] for k in ("id", "name", "error") if k in ident}
    try:
        if share.is_dir():
            info["share_logs"] = sorted(p.stem for p in share.glob("*.jsonl"))
    except OSError:
        info["share_logs"] = []
    return info or None


def _flatten(devices: list[dict]) -> list[dict]:
    out = []
    for d in devices:
        out.append(d)
        out.extend(_flatten(d.get("children") or []))
    return out


def parse_lsblk(text: str) -> list[dict]:
    """lsblk -J -b -o NAME,UUID,LABEL,FSTYPE,SIZE,MOUNTPOINT,RM,TRAN -> mounted filesystems with a UUID."""
    rows = []
    for d in _flatten(json.loads(text).get("blockdevices", [])):
        if not d.get("uuid") or not d.get("mountpoint") or d.get("mountpoint") in ("[SWAP]",):
            continue
        rows.append({"id": d["uuid"], "id_stable": True, "label": d.get("label") or "", "fstype": d.get("fstype") or "",
                     "size": int(d.get("size") or 0), "mount": d["mountpoint"],
                     "removable": str(d.get("rm")).lower() in ("1", "true"), "transport": d.get("tran") or ""})
    return rows


def _linux_drives(run=subprocess.run) -> list[dict] | None:
    exe = shutil.which("lsblk")
    if not exe:
        return None
    try:
        out = run([exe, "-J", "-b", "-o", "NAME,UUID,LABEL,FSTYPE,SIZE,MOUNTPOINT,RM,TRAN"],
                  capture_output=True, text=True, timeout=5, check=True).stdout
        return parse_lsblk(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _psutil_drives() -> list[dict]:
    try:
        import psutil
        parts = psutil.disk_partitions(all=False)
    except Exception:  # psutil missing or refused: no drives listed rather than a guess
        return []
    return [{"id": p.device, "id_stable": False, "label": "", "fstype": p.fstype, "size": 0, "mount": p.mountpoint,
             "removable": "removable" in (p.opts or ""), "transport": ""} for p in parts]


def discover(run=subprocess.run) -> list[dict]:
    """Mounted drives with their space and any Cursiv workspace on them. Real readings only."""
    drives = _linux_drives(run)
    if drives is None:
        drives = _psutil_drives()
    for d in drives:
        try:
            u = shutil.disk_usage(d["mount"])
            d["space"] = {"total": u.total, "used": u.used, "free": u.free}
        except OSError as exc:
            d["space"] = {"error": exc.strerror or type(exc).__name__}
        d["workspace"] = workspace_info(Path(d["mount"]))
    return drives

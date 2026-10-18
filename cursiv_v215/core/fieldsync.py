"""
Team sync without internet (research roadmap R6): field logs move between
laptops on a USB drive or a shared folder on the local network.

Each laptop's log stays its own chain. "Share" copies this laptop's log, with a
manifest (entry count and last fingerprint), into a folder. "Import" reads every
shared log in a folder, checks its chain and manifest, and keeps a copy per
laptop in ~/.cursiv/fieldlog/team/. Nothing from another laptop is ever written
into this laptop's own log, so its fingerprints stay intact.

Nothing is resolved silently:
- a log that only grew since the last import replaces the older copy;
- a log whose history differs from the copy already here (an entry changed,
  removed or reordered) is kept beside it and reported, and neither is chosen;
- the same sample ID recorded on two laptops is reported.

Only the field log moves. Personal memory, documents and settings never do.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from cursiv_v215.core import fieldlog

SHARE_DIR = "cursiv-field-share"          # the folder made on the USB drive / shared folder


def team_dir() -> Path:
    return fieldlog.log_dir() / "team"


def _read_lines(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def chain_problems(rows: list[dict]) -> list[str]:
    """The same checks as fieldlog.verify(), for a log read from somewhere else."""
    problems, prev, seq = [], fieldlog.GENESIS, 0
    for e in rows:
        if e.get("prev") != prev:
            problems.append(f"entry {e.get('seq')} doesn't follow the entry before it")
        if fieldlog._fingerprint(e) != e.get("hash"):
            problems.append(f"entry {e.get('seq')} was changed after it was recorded")
        if e.get("seq") != seq + 1:
            problems.append(f"entry numbers jump from {seq} to {e.get('seq')}")
        prev, seq = e.get("hash"), e.get("seq", seq)
    return problems


def share(folder: Path, observer: str = "") -> Path:
    """Copy this laptop's field log and a manifest into <folder>/cursiv-field-share/."""
    rows = fieldlog.entries()
    if not rows:
        raise ValueError("the field log is empty; there's nothing to share")
    problems = fieldlog.verify()
    if problems:
        raise ValueError("this laptop's field log has problems (" + problems[0] + "); "
                         "run 'field log check' before sharing")
    out = Path(folder) / SHARE_DIR
    out.mkdir(parents=True, exist_ok=True)
    device = fieldlog._device()
    shutil.copyfile(fieldlog.log_file(), out / f"{device}.jsonl")
    (out / f"{device}.manifest.json").write_text(json.dumps({
        "device": device, "observer": observer, "entries": len(rows), "last_hash": rows[-1]["hash"],
        "shared_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2), encoding="utf-8")
    return out


def _check_shared(log: Path) -> tuple[list[dict], list[str]]:
    try:
        rows = _read_lines(log)
    except ValueError:
        return [], ["a line isn't a complete entry (the copy may have been cut off)"]
    problems = chain_problems(rows)
    if {e.get("device") for e in rows} - {log.stem}:
        problems.append("it contains entries from a different laptop than its name says")
    man = log.with_name(log.stem + ".manifest.json")
    if not man.exists():
        problems.append("its manifest is missing")
    else:
        m = json.loads(man.read_text(encoding="utf-8"))
        if m.get("entries") != len(rows) or (rows and m.get("last_hash") != rows[-1]["hash"]):
            problems.append(f"the manifest says {m.get('entries')} entries but the copy has {len(rows)}: "
                            "it was cut off or changed after it was shared")
    return rows, problems


def import_folder(folder: Path) -> dict:
    """Import every shared log in folder (or folder/cursiv-field-share). Returns a report:
    {"added": {device: new entries}, "unchanged": [...], "conflicts": [...], "rejected": [...], "own": bool}."""
    folder = Path(folder)
    src = folder / SHARE_DIR if (folder / SHARE_DIR).is_dir() else folder
    logs = sorted(src.glob("*.jsonl"))
    if not logs:
        raise ValueError(f"no shared field logs in {src}")
    report = {"added": {}, "unchanged": [], "conflicts": [], "rejected": [], "own": False}
    me = fieldlog._device()
    team_dir().mkdir(parents=True, exist_ok=True)
    for log in logs:
        device = log.stem
        if device == me:
            report["own"] = True          # this laptop's own share: its log is already here
            continue
        rows, problems = _check_shared(log)
        if problems:
            report["rejected"].append(f"{device}: " + "; ".join(problems))
            continue
        mine = team_dir() / f"{device}.jsonl"
        if not mine.exists():
            shutil.copyfile(log, mine)
            report["added"][device] = len(rows)
            continue
        have = _read_lines(mine)
        hashes_have, hashes_new = [e["hash"] for e in have], [e["hash"] for e in rows]
        if hashes_new[:len(hashes_have)] == hashes_have:
            if len(rows) > len(have):
                shutil.copyfile(log, mine)                     # it only grew
                report["added"][device] = len(rows) - len(have)
            else:
                report["unchanged"].append(device)
        elif hashes_have[:len(hashes_new)] == hashes_new:
            report["unchanged"].append(device)                 # an older share than the copy here
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            keep = team_dir() / f"{device}.conflict-{stamp}.jsonl"
            shutil.copyfile(log, keep)
            first = next(i for i, (a, b) in enumerate(zip(hashes_have, hashes_new)) if a != b)
            report["conflicts"].append(
                f"{device}: its history differs from the copy imported earlier, from entry {first + 1} on. "
                f"Both are kept ({mine.name} and {keep.name}); neither was chosen.")
    return report


def team_entries() -> list[dict]:
    """Every entry from this laptop and every imported laptop (not conflict copies)."""
    rows = list(fieldlog.entries())
    seen = {e["hash"] for e in rows}
    for f in sorted(team_dir().glob("*.jsonl")) if team_dir().is_dir() else []:
        if ".conflict-" in f.name:
            continue
        for e in _read_lines(f):
            if e["hash"] not in seen:
                seen.add(e["hash"])
                rows.append(e)
    return sorted(rows, key=lambda e: (e["recorded_utc"], e["device"], e["seq"]))


def team_current() -> list[dict]:
    rows = team_entries()
    replaced = {e["corrects"] for e in rows if e.get("corrects")}
    return [e for e in rows if e["id"] not in replaced]


def sample_clashes(rows: list[dict] | None = None) -> list[str]:
    """Sample IDs recorded on more than one laptop (likely two different samples given one ID)."""
    by_id: dict[str, set] = {}
    for e in rows if rows is not None else team_current():
        if e.get("sample_id"):
            by_id.setdefault(e["sample_id"], set()).add(e["device"])
    return [f"sample {sid} was recorded on {len(devs)} laptops ({', '.join(sorted(devs))})"
            for sid, devs in sorted(by_id.items()) if len(devs) > 1]


def team_export(folder: Path | None = None) -> dict[str, Path]:
    """CSV, JSON and GeoJSON of the whole team, the same formats as a single laptop's export."""
    folder = folder or (fieldlog.log_dir() / "exports" / ("team_" + datetime.now().strftime("%Y-%m-%d_%H%M%S")))
    return fieldlog.export(folder, rows=team_current(), everything=team_entries())


def report_text(r: dict) -> str:
    lines = []
    for device, n in r["added"].items():
        lines.append(f"- {device}: {n} new entr{'y' if n == 1 else 'ies'}")
    for device in r["unchanged"]:
        lines.append(f"- {device}: nothing new")
    for c in r["conflicts"]:
        lines.append(f"- CONFLICT {c}")
    for x in r["rejected"]:
        lines.append(f"- NOT IMPORTED {x}")
    for c in sample_clashes():
        lines.append(f"- CHECK {c}")
    if r["own"] and len(lines) == 0:
        lines.append("- only this laptop's own share was there")
    return "Imported field logs:\n" + "\n".join(lines)


def command(text: str, observer: str = "") -> str | None:
    """field log share <folder>, field log import <folder>, team log, team log export."""
    t = (text or "").strip()
    m = re.match(r"(?i)^field ?log (share|import)\s+(.+)$", t)
    if m:
        folder = Path(m.group(2).strip().strip('"'))
        try:
            if m.group(1).lower() == "share":
                out = share(folder, observer)
                return (f"Shared this laptop's field log to {out}. On the other laptops: "
                        f"field log import {folder}. Only the field log is shared; memories and documents stay here.")
            return report_text(import_folder(folder))
        except (OSError, ValueError) as exc:
            return f"Not done: {exc}."
    low = t.lower()
    if low in ("team log", "team field log", "field log team"):
        rows = team_current()
        if not rows:
            return "No field entries yet, from this laptop or any imported one."
        devices = sorted({e["device"] for e in rows})
        head = f"Team field log: {len(rows)} entries from {len(devices)} laptop{'s' if len(devices) != 1 else ''}"
        clash = sample_clashes(rows)
        body = "\n".join(f"[{e['device'][:6]}] {fieldlog.summary(e)}" for e in rows[-15:])
        return head + " (latest 15):\n" + body + ("\nCheck:\n" + "\n".join(f"- {c}" for c in clash) if clash else "")
    if low in ("team log export", "export team log", "field log team export"):
        paths = team_export()
        return "Exported the team log:\n" + "\n".join(f"- {k.upper()}: {p}" for k, p in paths.items())
    return None

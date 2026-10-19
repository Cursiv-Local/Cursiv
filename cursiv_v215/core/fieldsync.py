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

Signed (field network Phase 0): a share's manifest carries the laptop's signed head
(core/devicekey.py). Import checks the signature against the copy, and remembers the
first key seen for each laptop (team/<laptop>.key.json). After that, a share signed by
a different key, or an unsigned share, is refused: someone copying the laptop's name
can't add records in its place. Shares from Cursiv before U73 have no signature; they
are imported and reported as unsigned until that laptop signs once.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from cursiv_v215.core import devicekey, fieldlog

SHARE_DIR = "cursiv-field-share"          # the folder made on the USB drive / shared folder


def team_dir() -> Path:
    return fieldlog.log_dir() / "team"


def _read_lines(path: Path) -> list[dict]:
    """Every entry in a log file; ValueError if any line isn't one (cut off, or not an entry)."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if not isinstance(e, dict):
                raise ValueError("a line isn't an entry")
            out.append(e)
    return out


def _copy_atomic(src: Path, dest: Path) -> None:
    """Copy so a power cut or a pulled drive leaves either the old file or the new one, never half."""
    import os
    tmp = dest.with_name(dest.name + ".tmp")
    shutil.copyfile(src, tmp)
    with tmp.open("rb+") as f:
        os.fsync(f.fileno())
    os.replace(tmp, dest)


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
        n = e.get("seq")
        prev, seq = e.get("hash"), n if isinstance(n, int) and not isinstance(n, bool) else seq + 1
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
    for e in rows:                                   # photos travel with the log, named by their SHA-256
        for rel in e.get("photos") or []:
            src = fieldlog.photo_path(rel)
            if fieldlog._is_stored(rel) and src.exists() and not (out / rel).exists():
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, out / rel)
    (out / f"{device}.manifest.json").write_text(json.dumps({
        "device": device, "observer": observer, "entries": len(rows), "last_hash": rows[-1]["hash"],
        "shared_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "head": devicekey.signed_head(rows, device),
    }, indent=2), encoding="utf-8")
    return out


def _key_file(device: str) -> Path:
    return team_dir() / f"{device}.key.json"


# ── Revoked keys: the team lead marks a lost, stolen or retired device ─────────
# New files signed by a revoked key are refused. What was imported before stays, and the
# team view says which entries came from a key revoked later. Nothing is deleted.

def _revoked_file() -> Path:
    return team_dir() / "revoked.json"


def revoked() -> dict:
    """{key_id: {"device", "reason", "revoked_utc", "by"}}"""
    try:
        return json.loads(_revoked_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def revoke(device: str, reason: str, by: str = "") -> dict:
    """Revoke the key remembered for a device. Raises ValueError if there's none or no reason."""
    if not reason.strip():
        raise ValueError("give a reason (lost, stolen, retired...): it's kept with the revocation")
    pin = pinned_key(device)
    if not pin:
        raise ValueError(f"no signing key is remembered for {device} (it was never imported signed)")
    data = revoked()
    data[pin["key_id"]] = {"device": device, "reason": reason.strip(), "by": by.strip(),
                           "revoked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    team_dir().mkdir(parents=True, exist_ok=True)
    from cursiv_v215.core import atomic
    atomic.write_text(_revoked_file(), json.dumps(data, indent=2))
    return data[pin["key_id"]]


def pinned_key(device: str) -> dict | None:
    try:
        return json.loads(_key_file(device).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _check_signature(m: dict, device: str, rows: list[dict]) -> tuple[dict | None, list[str]]:
    """(the verified signature envelope or None if unsigned, problems)."""
    env = m.get("head")
    if not env:
        return None, []
    gone = revoked().get(env.get("key_id", ""))
    if gone:
        return None, [f"it's signed by a key the team lead revoked on {gone['revoked_utc'][:10]} "
                      f"({gone['reason']}). Not imported; what came from it earlier stays, marked."]
    if not devicekey.verify(env):
        return None, ["its signature doesn't match: the copy or its manifest was changed after it was signed"]
    h = env["signed"]
    if not isinstance(h, dict):
        return None, ["its signature isn't over a log head"]
    if device.startswith("phone-") and env["key_id"][:12] != device[6:]:
        # a phone's name is "phone-" + the first 12 of its key id (website/notebook/core.js deviceLabel)
        return None, [f"it's signed by key {env['key_id']}, which isn't the key that phone's name comes from: "
                      "another device is using that phone's name. Not imported"]
    if h.get("format") != devicekey.HEAD_FORMAT or h.get("device") != device or h.get("entries") != len(rows) \
            or (rows and h.get("hash") != rows[-1]["hash"]):
        return None, ["its signature is for a different log or length than this copy"]
    pin = pinned_key(device)
    if pin and pin.get("public_key") != env["public_key"]:
        return None, [f"it's signed by a different key ({env['key_id']}) than this laptop's earlier shares "
                      f"({pin.get('key_id')}). Not imported. If that laptop really has a new key (a new "
                      f"Windows account or a reinstall), delete {_key_file(device).name} in the team folder "
                      f"to accept it."]
    return env, []


def _check_shared(log: Path) -> tuple[list[dict], list[str]]:
    rows, problems, _env = _check_shared_signed(log)
    return rows, problems


def _check_shared_signed(log: Path) -> tuple[list[dict], list[str], dict | None]:
    try:
        rows = _read_lines(log)
    except (OSError, ValueError):
        return [], ["a line isn't a complete entry (the copy may have been cut off)"], None
    problems = chain_problems(rows)
    bad = [(i, p) for i, e in enumerate(rows, 1) for p in fieldlog.record_problems(e)]   # i: its place in the file
    if bad:
        seq, first = bad[0]
        problems.append(f"entry {seq} has a value Cursiv can't accept ({first})"
                        + (f", and {len(bad) - 1} more problem(s)" if len(bad) > 1 else "")
                        + ". The whole log was refused, so nothing from it is half-imported")
    newer = max((e.get("schema", 0) for e in rows if isinstance(e.get("schema", 0), int)), default=0)
    if newer > fieldlog.SCHEMA:
        problems.append(f"it was made by a newer Cursiv (record schema {newer}; this one reads up to "
                        f"{fieldlog.SCHEMA}). Update Cursiv, then import it again")
    other = next((e for e in rows if e.get("device") != log.stem), None)
    if other is not None:
        problems.append(f"entry {other.get('seq')} says it's from {str(other.get('device'))[:30]}, not {log.stem}: "
                        "it contains entries from a different laptop than its name says")
    man = log.with_name(log.stem + ".manifest.json")
    if not man.exists():
        problems.append("its manifest is missing")
    else:
        try:
            m = json.loads(man.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            m = None
        if not isinstance(m, dict):
            problems.append("its manifest can't be read (cut off or damaged)")
            return rows, problems, None
        if m.get("entries") != len(rows) or (rows and m.get("last_hash") != rows[-1]["hash"]):
            problems.append(f"the manifest says {m.get('entries')} entries but the copy has {len(rows)}: "
                            "it was cut off or changed after it was shared")
        env, sig_problems = _check_signature(m, log.stem, rows)
        problems += sig_problems
        if env is None and not sig_problems and pinned_key(log.stem):
            problems.append("it isn't signed, but this laptop's earlier shares were: not imported")
        return rows, problems, env
    return rows, problems, None


def _import_photos(src: Path, rows: list[dict]) -> int:
    """Copy the photos these entries name into the photo store, each checked against its
    SHA-256 name. Returns how many are missing or don't match (the entries still import)."""
    import hashlib
    missing = 0
    for e in rows:
        for rel in e.get("photos") or []:
            if not fieldlog._is_stored(rel):
                continue
            dest = fieldlog.photo_path(rel)
            if dest.exists():
                continue
            f = src / rel
            if not f.exists() or f.stat().st_size > fieldlog.PHOTO_MAX_MB * 2**20 \
                    or hashlib.sha256(f.read_bytes()).hexdigest() != Path(rel).stem:
                missing += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            _copy_atomic(f, dest)
    return missing


def _clock_ahead_minutes(rows: list[dict]) -> int:
    """Minutes the device's clock looks ahead of this computer's (entries recorded "in the
    future"), or 0. Times are kept as recorded; this only flags them."""
    now = datetime.now(timezone.utc)
    worst = 0.0
    for e in rows:
        try:
            t = datetime.strptime(e.get("recorded_utc", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        worst = max(worst, (t - now).total_seconds() / 60)
    return int(round(worst)) if worst > 5 else 0


def import_folder(folder: Path) -> dict:
    """Import every shared log in folder (or folder/cursiv-field-share). Returns a report:
    {"added": {device: new entries}, "unchanged": [...], "conflicts": [...], "rejected": [...], "own": bool}."""
    folder = Path(folder)
    src = folder / SHARE_DIR if (folder / SHARE_DIR).is_dir() else folder
    logs = sorted(src.glob("*.jsonl"))
    if not logs:
        raise ValueError(f"no shared field logs in {src}")
    report = {"added": {}, "unchanged": [], "conflicts": [], "rejected": [], "own": False,
              "signed": {}, "unsigned": [], "photos_missing": {}}
    me = fieldlog._device()
    team_dir().mkdir(parents=True, exist_ok=True)
    for log in logs:
        device = log.stem
        if device == me:
            report["own"] = True          # this laptop's own share: its log is already here
            continue
        try:
            rows, problems, env = _check_shared_signed(log)
        except Exception as exc:                       # one damaged log never stops the others
            rows, problems, env = [], [f"it couldn't be read ({type(exc).__name__})"], None
        if problems:
            report["rejected"].append(f"{device}: " + "; ".join(problems))
            continue
        missing = _import_photos(src, rows)
        if missing:
            report["photos_missing"][device] = missing
        ahead = _clock_ahead_minutes(rows)
        if ahead:
            report.setdefault("clock", {})[device] = ahead
        if env:
            report["signed"][device] = env["key_id"]
            if not pinned_key(device):
                from cursiv_v215.core import atomic
                atomic.write_text(_key_file(device), json.dumps({
                    "device": device, "public_key": env["public_key"], "key_id": env["key_id"],
                    "first_seen_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, indent=2))
        else:
            report["unsigned"].append(device)
        mine = team_dir() / f"{device}.jsonl"
        if not mine.exists():
            _copy_atomic(log, mine)
            report["added"][device] = len(rows)
            continue
        try:
            have = _read_lines(mine)
        except (OSError, ValueError):
            report["rejected"].append(f"{device}: the copy imported earlier ({mine.name}) can't be read; "
                                      "nothing was changed. Run 'team log' for details")
            continue
        hashes_have, hashes_new = [e["hash"] for e in have], [e["hash"] for e in rows]
        if hashes_new[:len(hashes_have)] == hashes_have:
            if len(rows) > len(have):
                _copy_atomic(log, mine)                        # it only grew
                report["added"][device] = len(rows) - len(have)
            else:
                report["unchanged"].append(device)
        elif hashes_have[:len(hashes_new)] == hashes_new:
            report["unchanged"].append(device)                 # an older share than the copy here
        else:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            keep = team_dir() / f"{device}.conflict-{stamp}.jsonl"
            _copy_atomic(log, keep)
            first = next(i for i, (a, b) in enumerate(zip(hashes_have, hashes_new)) if a != b)
            report["conflicts"].append(
                f"{device}: its history differs from the copy imported earlier, from entry {first + 1} on. "
                f"Both are kept ({mine.name} and {keep.name}); neither was chosen.")
    return report


# ── The phone notebook (website/notebook): one .cursivsync file per send ────────
# The phone keeps a log in exactly the laptop's format and signs its head with its own
# Ed25519 key. Its file is unpacked into a share folder and imported like a laptop's
# USB share, through every check above.

PHONE_FORMAT = "cursiv-phone-bundle-1"
_PHONE_DEVICE = re.compile(r"^phone-[0-9a-f]{12}$")


PHONE_ZIP_FORMAT = "cursiv-phone-bundle-2"
_ZIP_LIMIT = 4 << 30                       # the whole file, unpacked (a zip's sizes can lie: counted as read)
_LOG_LIMIT = 200 << 20                     # bundle.json, the log and its manifest, each


def _unzip_phone_bundle(path: Path, into: Path) -> None:
    """Unpack a format-2 send file into `into`, letting through only the names a phone writes:
    bundle.json, cursiv-field-share/<phone>.jsonl, <phone>.manifest.json and photos/<sha256>.<ext>.
    Anything else (another folder, an absolute path, "..", a second log) refuses the whole file."""
    import zipfile
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"{path.name} isn't a phone notebook file ({exc})") from exc
    with z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError(f"{path.name} names a file twice")
        try:
            head = json.loads(z.read("bundle.json")) if "bundle.json" in names else {}
        except ValueError:
            head = {}
        if not isinstance(head, dict) or head.get("format") != PHONE_ZIP_FORMAT:
            raise ValueError(f"{path.name} isn't a phone notebook file")
        device = str(head.get("device", ""))
        if not _PHONE_DEVICE.match(device):
            raise ValueError("the file doesn't name a phone (its device label is wrong)")
        allowed = {"bundle.json", f"{SHARE_DIR}/{device}.jsonl", f"{SHARE_DIR}/{device}.manifest.json"}
        photo_max = fieldlog.PHOTO_MAX_MB << 20
        total = 0
        for info in z.infolist():
            name = info.filename
            rel = name[len(SHARE_DIR) + 1:] if name.startswith(SHARE_DIR + "/") else ""
            if info.is_dir() or not (name in allowed or fieldlog._is_stored(rel)):
                raise ValueError(f"{path.name} holds something a phone doesn't send ({name[:80]}): not imported")
            limit = photo_max if fieldlog._is_stored(rel) else _LOG_LIMIT
            if name == "bundle.json":
                continue
            dest = into / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            got = 0
            with z.open(info) as src, dest.open("wb") as out:
                while chunk := src.read(1 << 20):
                    got += len(chunk)
                    total += len(chunk)
                    if got > limit + (1 << 20) or total > _ZIP_LIMIT:
                        raise ValueError(f"{path.name} is too big to be a phone's send file ({name[:80]})")
                    out.write(chunk)
        if f"{SHARE_DIR}/{device}.jsonl" not in names:
            raise ValueError(f"{path.name} has no log in it")


def import_phone_bundle(path: Path) -> dict:
    """Import a .cursivsync file from the phone notebook: format 2 (a zip, what the phone makes now)
    or format 1 (one JSON file with photos inside, from earlier versions). Same report as import_folder()."""
    import base64
    import tempfile
    path = Path(path)
    try:
        with path.open("rb") as f:
            is_zip = f.read(2) == b"PK"
    except OSError as exc:
        raise ValueError(f"can't read {path.name} ({exc})") from exc
    if is_zip:
        with tempfile.TemporaryDirectory() as tmp:
            _unzip_phone_bundle(path, Path(tmp))
            return import_folder(Path(tmp))
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path.name} isn't a phone notebook file ({exc})") from exc
    if not isinstance(bundle, dict) or bundle.get("format") != PHONE_FORMAT:
        raise ValueError(f"{path.name} isn't a phone notebook file")
    device = str(bundle.get("device", ""))
    if not _PHONE_DEVICE.match(device):
        raise ValueError("the file doesn't name a phone (its device label is wrong)")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / SHARE_DIR
        out.mkdir()
        with (out / f"{device}.jsonl").open("w", encoding="utf-8") as f:
            for e in bundle.get("entries") or []:
                f.write(json.dumps(e, ensure_ascii=False, separators=(",", ":")) + "\n")
        (out / f"{device}.manifest.json").write_text(json.dumps(bundle.get("manifest") or {}), encoding="utf-8")
        for rel, data in (bundle.get("photos") or {}).items():
            if fieldlog._is_stored(rel):
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                (out / rel).write_bytes(base64.b64decode(data))
        return import_folder(Path(tmp))


def _team_files() -> list[Path]:
    return [f for f in (sorted(team_dir().glob("*.jsonl")) if team_dir().is_dir() else [])
            if ".conflict-" not in f.name]


def team_problems() -> list[str]:
    """Imported copies here that no longer check out (damaged on this disk after import)."""
    out = []
    for f in _team_files():
        try:
            rows = _read_lines(f)
        except (OSError, ValueError):
            out.append(f"{f.name} can't be read: import that device's share again")
            continue
        p = chain_problems(rows) + [f"entry {e.get('seq')}: {x}" for e in rows for x in fieldlog.record_problems(e)]
        if p:
            out.append(f"{f.name}: {p[0]}")
    return out


def team_entries() -> list[dict]:
    """Every entry from this laptop and every imported laptop (not conflict copies).
    A copy damaged after import is left out (team_problems() names it), not half-read."""
    rows = list(fieldlog.entries())
    seen = {e.get("hash") for e in rows}
    for f in _team_files():
        try:
            theirs = _read_lines(f)
        except (OSError, ValueError):
            continue
        if chain_problems(theirs) or any(fieldlog.record_problems(e) for e in theirs):
            continue
        for e in theirs:
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
    for device, kid in r.get("signed", {}).items():
        lines.append(f"- {device}: signature checked (key {kid})")
    for device, n in r.get("photos_missing", {}).items():
        lines.append(f"- {device}: {n} photo(s) missing, over {fieldlog.PHOTO_MAX_MB} MB, or not matching their "
                     f"fingerprint (the entries are in)")
    for device, mins in r.get("clock", {}).items():
        lines.append(f"- CHECK {device}: its clock looks about {mins} minutes ahead of this computer's. Its times are "
                     f"kept as recorded; check that device's date and time")
    for device in r.get("unsigned", []):
        lines.append(f"- {device}: not signed (shared by Cursiv before U73); its chain was checked")
    for c in sample_clashes():
        lines.append(f"- CHECK {c}")
    if r["own"] and len(lines) == 0:
        lines.append("- only this laptop's own share was there")
    return "Imported field logs:\n" + "\n".join(lines)


def command(text: str, observer: str = "") -> str | None:
    """field log share <folder>, field log import <folder>, team log, team log export,
    field log revoke <device> <reason>."""
    t = (text or "").strip()
    m = re.match(r"(?i)^field ?log revoke\s+(\S+)\s*(.*)$", t)
    if m:
        try:
            r = revoke(m.group(1), m.group(2), by=observer)
        except ValueError as exc:
            return f"Not revoked: {exc}."
        return (f"Revoked {m.group(1)}'s key ({r['reason']}). New files signed by it will be refused; "
                f"entries imported before stay in the team log, marked as from a revoked key.")
    m = re.match(r"(?i)^field ?log (share|import)\s+(.+)$", t)
    if m:
        folder = Path(m.group(2).strip().strip('"'))
        try:
            if m.group(1).lower() == "import" and folder.suffix.lower() == ".cursivsync":
                return report_text(import_phone_bundle(folder))
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
        head = f"Team field log: {len(rows)} entries from {len(devices)} device{'s' if len(devices) != 1 else ''}"
        damaged = team_problems()
        if damaged:
            head = ("WARNING, left out because they no longer check out:\n" + "\n".join(f"- {d}" for d in damaged)
                    + "\n" + head)
        clash = sample_clashes(rows)
        gone = {v["device"]: v for v in revoked().values()}
        body = "\n".join(f"[{e['device'] if e['device'].startswith('phone-') else e['device'][:6]}] "
                         f"{fieldlog.summary(e)}"
                         + (f"  (key revoked {gone[e['device']]['revoked_utc'][:10]})" if e["device"] in gone else "")
                         for e in rows[-15:])
        return head + " (latest 15):\n" + body + ("\nCheck:\n" + "\n".join(f"- {c}" for c in clash) if clash else "")
    if low in ("team log export", "export team log", "field log team export"):
        paths = team_export()
        return "Exported the team log:\n" + "\n".join(f"- {k.upper()}: {p}" for k, p in paths.items())
    return None

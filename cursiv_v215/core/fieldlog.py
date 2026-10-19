"""
Field notebook (research roadmap R1): structured observations recorded by a
person, kept apart from anything the AI says or infers.

Every entry is a line in an append-only file (~/.cursiv/fieldlog/observations.jsonl;
on a Cursiv drive that's on the drive). Nothing is ever edited or deleted: a
correction is a new entry that points at the one it corrects, with a reason, and
both stay in the file. Each entry carries the fingerprint (SHA-256) of the entry
before it, so changing, removing or reordering any past line is detectable
(verify()). The AI never writes here; only the person does, through `log ...`
or the Field Notebook window.

Exports: CSV (one row per measurement), JSON (everything, including corrected
entries) and GeoJSON (entries with coordinates).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "genesis"
# Record schema. 1 (U75): "schema", and optional "location_accuracy_m" / "location_fix_utc".
# Entries without "schema" are 0 and still valid. A newer schema is refused on import (fieldsync).
SCHEMA = 1
_lock = threading.Lock()


def log_dir() -> Path:
    from cursiv_v215.core import demo
    if demo.active():                     # the field demo's sample data, apart from real records
        return demo.root() / "fieldlog"
    return Path.home() / ".cursiv" / "fieldlog"


def log_file() -> Path:
    return log_dir() / "observations.jsonl"


def _device() -> str:
    """A short, stable label for this computer (a hash, not its name)."""
    return hashlib.sha256(socket.gethostname().encode("utf-8", "replace")).hexdigest()[:12]


# ── Photos: stored once, named by their SHA-256 ───────────────────────────
# An entry lists "photos/<sha256>.<ext>"; the name is part of the entry's
# fingerprint, so a photo can't be swapped without breaking the record. The time
# and GPS position a camera wrote into the photo (EXIF) are kept in photo_info.

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff", ".gif", ".bmp"}
PHOTO_WARN_MB = 15        # a warning when attaching (phone photos are usually 2-6 MB)
PHOTO_MAX_MB = 50         # refused above this, here, on the phone and on import (docs/MOBILE-PLAN.md)


def photo_dir() -> Path:
    return log_dir() / "photos"


def photo_path(stored: str) -> Path:
    """Where a stored photo ("photos/<sha256>.jpg") is on this computer."""
    return log_dir() / stored


def _exif_rational(v) -> float:
    try:
        return float(v)
    except TypeError:
        return v[0] / v[1]


def photo_info(path: Path) -> dict:
    """{"taken": "2026:10:18 14:31:05" or "", "lat": float|None, "lon": float|None} from EXIF."""
    info = {"taken": "", "lat": None, "lon": None}
    try:
        from PIL import Image
        with Image.open(path) as img:
            exif = img.getexif()
            sub = exif.get_ifd(0x8769)                       # Exif sub-IFD
            info["taken"] = str(sub.get(36867) or exif.get(306) or "")
            gps = exif.get_ifd(0x8825)
            if gps and 2 in gps and 4 in gps:
                def deg(dms):
                    d, m, s = (_exif_rational(x) for x in dms)
                    return d + m / 60 + s / 3600
                lat, lon = deg(gps[2]), deg(gps[4])
                if str(gps.get(1, "N")).upper().startswith("S"):
                    lat = -lat
                if str(gps.get(3, "E")).upper().startswith("W"):
                    lon = -lon
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    info["lat"], info["lon"] = round(lat, 7), round(lon, 7)
    except Exception:
        pass
    return info


def store_photo(path) -> str:
    """Copy a photo into the notebook's photo store; returns "photos/<sha256><ext>"."""
    src = Path(path)
    if not src.is_file():
        raise ValueError(f"no photo at {src}")
    ext = src.suffix.lower()
    if ext not in PHOTO_EXTS:
        raise ValueError(f"{src.name} isn't a photo Cursiv recognises ({', '.join(sorted(PHOTO_EXTS))})")
    size_mb = src.stat().st_size / 2**20
    if size_mb > PHOTO_MAX_MB:
        raise ValueError(f"{src.name} is {size_mb:.0f} MB; photos over {PHOTO_MAX_MB} MB aren't stored")
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    rel = f"photos/{digest}{'.jpg' if ext == '.jpeg' else ext}"
    dest = log_dir() / rel
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    return rel


def _is_stored(p: str) -> bool:
    return isinstance(p, str) and re.fullmatch(r"photos/[0-9a-f]{64}\.[a-z]+", p) is not None


def _fingerprint(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _read() -> tuple[list[dict], list[str]]:
    """Entries in file order, and lines that couldn't be read (e.g. a write cut off by power loss)."""
    entries, bad = [], []
    try:
        lines = log_file().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [], []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            e = None
        if isinstance(e, dict):
            entries.append(e)
        else:
            bad.append(f"line {n} isn't a complete entry")
    return entries, bad


def entries() -> list[dict]:
    """Every entry ever written, including ones later corrected."""
    return _read()[0]


def _clean_measurements(measurements) -> list[dict]:
    out = []
    for m in measurements or []:
        name = str(m.get("name", "")).strip()
        if not name:
            continue
        # The value is kept exactly as typed ("12.40" stays "12.40": trailing zeros can be
        # meaningful precision); "number" is the same value for calculations, or None.
        value = str(m.get("value", "")).strip()
        number = float(value) if re.fullmatch(r"-?\d+(?:\.\d+)?", value) else None
        out.append({"name": name, "value": value, "number": number, "unit": str(m.get("unit", "") or "").strip()})
    return out


def _coord(value, low: float, high: float):
    if value in (None, ""):
        return None
    v = float(value)
    if not low <= v <= high:
        raise ValueError(f"coordinate {v} is outside {low}..{high}")
    return round(v, 7)


def add(*, observer: str = "", site: str = "", lat=None, lon=None, location_source: str = "",
        location_accuracy_m=None, location_fix_utc: str = "",
        measurements=None, note: str = "", photos=None, corrects: str = "", reason: str = "",
        app_version: str = "", sample_id: str = "") -> dict:
    """Append one entry and return it. Coordinates are decimal degrees (WGS84)."""
    if corrects and not reason.strip():
        raise ValueError("a correction needs a reason")
    lat_v, lon_v = _coord(lat, -90, 90), _coord(lon, -180, 180)
    if (lat_v is None) != (lon_v is None):
        raise ValueError("give both latitude and longitude, or neither")
    meas = _clean_measurements(measurements)
    sample_id = (sample_id or "").strip()
    if sample_id and not _SAMPLE_OK.fullmatch(sample_id):
        raise ValueError("a sample ID can use letters, numbers, '-', '_' and '.' (up to 40)")
    if not (meas or note.strip() or photos or sample_id):
        raise ValueError("an entry needs at least a measurement, a note or a photo")
    stored, infos = [], []
    for p in photos or []:
        if _is_stored(str(p)):
            stored.append(str(p))
            continue
        rel = store_photo(p)
        stored.append(rel)
        infos.append({"file": rel, "name": Path(p).name, **photo_info(Path(p))})
    with _lock:
        existing, _bad = _read()
        if corrects and corrects not in {e["id"] for e in existing}:
            raise ValueError(f"no entry {corrects} to correct")
        now = time.time()
        accuracy = None
        if lat_v is not None and location_accuracy_m not in (None, ""):
            accuracy = round(float(location_accuracy_m), 1)
            if not math.isfinite(accuracy) or accuracy < 0:
                raise ValueError("location accuracy must be a number of metres, 0 or more")
        entry = {
            "schema": SCHEMA,
            "id": uuid.uuid4().hex[:12],
            "seq": (existing[-1]["seq"] + 1) if existing else 1,
            "recorded_utc": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "recorded_local": datetime.fromtimestamp(now).astimezone().isoformat(timespec="seconds"),
            "observer": observer.strip(),
            "sample_id": sample_id,
            "site": site.strip(),
            "lat": lat_v, "lon": lon_v,
            "location_source": location_source if lat_v is not None else "",
            "location_accuracy_m": accuracy,
            "location_fix_utc": (location_fix_utc or "") if lat_v is not None else "",
            "measurements": meas,
            "note": note.strip(),
            "photos": stored,
            "corrects": corrects or None,
            "reason": reason.strip(),
            "device": _device(),
            "app_version": app_version,
            "prev": existing[-1]["hash"] if existing else GENESIS,
        }
        if infos:
            entry["photo_info"] = infos
        entry["hash"] = _fingerprint(entry)
        log_dir().mkdir(parents=True, exist_ok=True)
        # One line per entry, flushed to disk before returning, so a power cut can
        # at worst leave one incomplete last line (verify() reports it). If the last
        # write was cut off, this entry starts on a new line instead of being glued
        # onto the broken one (which would make both unreadable).
        line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        if not _ends_with_newline(log_file()):
            line = "\n" + line
        with log_file().open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return entry


def _ends_with_newline(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() == 0:
                return True
            f.seek(-1, os.SEEK_END)
            return f.read(1) == b"\n"
    except FileNotFoundError:
        return True


def correct(entry_id: str, reason: str, **fields) -> dict:
    """A new entry replacing entry_id in the current view. Fields not given are copied from it."""
    old = next((e for e in entries() if e["id"] == entry_id), None)
    if old is None:
        raise ValueError(f"no entry {entry_id} to correct")
    base = {k: old.get(k) for k in ("observer", "site", "lat", "lon", "location_source", "measurements",
                                    "note", "photos", "sample_id", "location_accuracy_m", "location_fix_utc")}
    base["location_fix_utc"] = base.get("location_fix_utc") or ""
    base["photos"] = base.get("photos") or []
    base["sample_id"] = base.get("sample_id") or ""
    base.update(fields)
    return add(**base, corrects=entry_id, reason=reason)


def current() -> list[dict]:
    """The entries as they stand: an entry that was corrected is replaced by its correction."""
    all_entries = entries()
    replaced = {e["corrects"] for e in all_entries if e.get("corrects")}
    return [e for e in all_entries if e["id"] not in replaced]


def verify() -> list[str]:
    """Problems with the log, or [] when every entry is intact and in order."""
    all_entries, problems = _read()
    prev, seq = GENESIS, 0
    for e in all_entries:
        if e.get("prev") != prev:
            problems.append(f"entry {e.get('seq')} ({e.get('id')}) doesn't follow the entry before it: "
                            "something was removed, inserted or reordered")
        if _fingerprint(e) != e.get("hash"):
            problems.append(f"entry {e.get('seq')} ({e.get('id')}) was changed after it was recorded")
        if e.get("seq") != seq + 1:
            problems.append(f"entry numbers jump from {seq} to {e.get('seq')}")
        n = e.get("seq")
        prev, seq = e.get("hash"), n if isinstance(n, int) and not isinstance(n, bool) else seq + 1
    return problems


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _utc_ok(v) -> bool:
    try:
        datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except (TypeError, ValueError):
        return False


def _local_ok(v) -> bool:
    try:
        datetime.fromisoformat(v)
        return isinstance(v, str)
    except (TypeError, ValueError):
        return False


def record_problems(e) -> list[str]:
    """What's wrong with one entry's values, or []. A fingerprint only proves an entry
    wasn't changed after it was made; this catches entries made wrong (by a bug, an old
    or foreign program, or on purpose) before they're trusted. Entries from before the
    schema field, sample IDs or photos (older Cursiv) still pass."""
    if not isinstance(e, dict):
        return ["isn't an entry"]
    p = []
    for k in ("id", "recorded_utc", "recorded_local", "observer", "site", "note", "reason", "device", "prev", "hash"):
        if not isinstance(e.get(k), str):
            p.append(f"{k} is missing or not text")
    for k in ("location_source", "app_version", "sample_id", "location_fix_utc"):
        if k in e and not isinstance(e[k], str):
            p.append(f"{k} is not text")
    if not (isinstance(e.get("seq"), int) and not isinstance(e.get("seq"), bool) and e["seq"] >= 1):
        p.append("its number (seq) isn't a whole number from 1")
    if "schema" in e and not (isinstance(e["schema"], int) and not isinstance(e["schema"], bool)):
        p.append("schema isn't a whole number")
    if isinstance(e.get("recorded_utc"), str) and not _utc_ok(e["recorded_utc"]):
        p.append(f"recorded_utc {e['recorded_utc'][:30]!r} isn't a time (YYYY-MM-DDTHH:MM:SSZ)")
    if not _local_ok(e.get("recorded_local")):
        p.append("recorded_local isn't a time")
    lat, lon = e.get("lat"), e.get("lon")
    if (lat is None) != (lon is None):
        p.append("it has a latitude or a longitude but not both")
    elif lat is not None:
        if not (_num(lat) and -90 <= lat <= 90):
            p.append(f"latitude {lat!r} isn't a number from -90 to 90")
        if not (_num(lon) and -180 <= lon <= 180):
            p.append(f"longitude {lon!r} isn't a number from -180 to 180")
    acc = e.get("location_accuracy_m")
    if acc is not None and not (_num(acc) and acc >= 0):
        p.append(f"location accuracy {acc!r} isn't a number of metres")
    meas = e.get("measurements")
    if not isinstance(meas, list):
        p.append("measurements isn't a list")
    else:
        for m in meas:
            if not (isinstance(m, dict) and isinstance(m.get("name"), str) and m["name"].strip()
                    and isinstance(m.get("value"), str) and isinstance(m.get("unit", ""), str)
                    and (m.get("number") is None or _num(m.get("number")))):
                p.append(f"a measurement isn't a name, a value as text, a unit and a number or nothing ({str(m)[:60]})")
                break
    photos = e.get("photos", [])
    if not isinstance(photos, list) or not all(_is_stored(x) for x in photos):
        p.append("photos isn't a list of stored photo names (photos/<sha256>.<ext>)")
    if e.get("corrects") is not None and not isinstance(e.get("corrects"), str):
        p.append("corrects isn't an entry id")
    if e.get("corrects") and not str(e.get("reason", "")).strip():
        p.append("it corrects an entry but gives no reason")
    sid = e.get("sample_id", "")
    if isinstance(sid, str) and sid and not _SAMPLE_OK.fullmatch(sid):
        p.append(f"sample ID {sid[:40]!r} isn't valid")
    return p


def photo_problems(rows: list[dict] | None = None) -> list[str]:
    """Photos these entries name that are missing from this computer or whose bytes no longer
    match the SHA-256 in their name (changed or damaged after they were stored)."""
    out = []
    for e in rows if rows is not None else entries():
        for rel in e.get("photos") or []:
            where = f"entry {e.get('seq')} ({e.get('device', '')})"
            if not _is_stored(rel):
                out.append(f"{where}: {str(rel)[:60]!r} isn't a stored photo name")
                continue
            f = photo_path(rel)
            if not f.is_file():
                out.append(f"{where}: photo {rel} is missing")
            elif _file_sha256(f) != Path(rel).stem:
                out.append(f"{where}: photo {rel} doesn't match its fingerprint (changed or damaged after it was stored)")
    return out


# ── Sample IDs (research roadmap R4) ───────────────────────────────────────

_SAMPLE_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}")


def new_sample_id(site: str = "") -> str:
    """Site initials, today's date, and the next free number: 'NT-20261018-001'."""
    words = re.findall(r"[A-Za-z0-9]+", site or "")
    prefix = ("".join(w[0] for w in words[:3]).upper() or "S")
    day = datetime.now().strftime("%Y%m%d")
    taken = {e.get("sample_id") for e in entries()}
    n = 1
    while f"{prefix}-{day}-{n:03d}" in taken:
        n += 1
    return f"{prefix}-{day}-{n:03d}"


def sample_history(sample_id: str) -> list[dict]:
    """Every entry recorded for a sample, oldest first, including corrected ones."""
    return [e for e in entries() if e.get("sample_id") == sample_id]


def labels_html(rows: list[dict]) -> str:
    """A printable sheet of sample labels (ID, site, time, observer, coordinates, fingerprint)."""
    import html
    cells = []
    for e in rows:
        if not e.get("sample_id"):
            continue
        where = f"{e['lat']}, {e['lon']}" if e.get("lat") is not None else ""
        cells.append(
            '<div class="label"><div class="id">' + html.escape(e["sample_id"]) + "</div>"
            f'<div>{html.escape(e.get("site", ""))}</div>'
            f'<div>{html.escape(e["recorded_local"][:16].replace("T", " "))} · {html.escape(e.get("observer", ""))}</div>'
            f'<div>{html.escape(where)}</div>'
            f'<div class="fp">#{e["seq"]} · {e["hash"][:12]}</div></div>')
    return ("<!doctype html><meta charset='utf-8'><title>Sample labels</title><style>"
            "body{font-family:Arial,sans-serif;margin:10mm}"
            ".sheet{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}"
            ".label{border:1px dashed #999;padding:3mm;font-size:9pt;line-height:1.3;break-inside:avoid}"
            ".id{font-size:13pt;font-weight:bold;font-family:Consolas,monospace}"
            ".fp{color:#555;font-family:Consolas,monospace;font-size:8pt}"
            "@media print{.label{border-color:#bbb}}</style>"
            "<div class='sheet'>" + "".join(cells) + "</div>")


# ── Export ─────────────────────────────────────────────────────────────────

CSV_FIELDS = ("entry_id", "seq", "recorded_utc", "recorded_local", "observer", "sample_id", "site", "lat", "lon",
              "location_source", "measurement", "value", "unit", "note", "photos", "corrects", "reason",
              "fingerprint", "device", "location_accuracy_m")


def export(folder: Path | None = None, include_corrected: bool = False, *,
           rows: list[dict] | None = None, everything: list[dict] | None = None) -> dict[str, Path]:
    """Write CSV, JSON and GeoJSON; returns their paths. JSON always has every entry.
    rows / everything: other entries to export (the team log, fieldsync.team_export)."""
    folder = folder or (log_dir() / "exports" / datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    folder.mkdir(parents=True, exist_ok=True)
    if rows is None:
        rows = entries() if include_corrected else current()
    every = entries() if everything is None else everything
    problems = verify() + photo_problems(every)

    csv_path = folder / "observations.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_FIELDS)
        for e in rows:
            common = [e["id"], e["seq"], e["recorded_utc"], e["recorded_local"], e["observer"],
                      e.get("sample_id", ""), e["site"],
                      "" if e["lat"] is None else e["lat"], "" if e["lon"] is None else e["lon"],
                      e["location_source"]]
            acc = e.get("location_accuracy_m")
            tail = [e["note"], ";".join(e["photos"]), e["corrects"] or "", e["reason"], e["hash"],
                    e.get("device", ""), "" if acc is None else acc]
            for m in e["measurements"] or [{"name": "", "value": "", "unit": ""}]:
                w.writerow(common + [m["name"], m["value"], m["unit"]] + tail)

    json_path = folder / "observations.json"
    json_path.write_text(json.dumps({
        "exported_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "integrity": "intact" if not problems else problems,
        "entries": entries() if everything is None else everything,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    geo_path = folder / "observations.geojson"
    features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
                 "properties": {**{k: e[k] for k in ("id", "seq", "recorded_utc", "observer", "site",
                                                     "measurements", "note", "hash")},
                                "sample_id": e.get("sample_id", ""),
                                "location_accuracy_m": e.get("location_accuracy_m")}}
                for e in rows if e["lat"] is not None]
    geo_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2,
                                   ensure_ascii=False), encoding="utf-8")
    paths = {"csv": csv_path, "json": json_path, "geojson": geo_path}
    report = folder / "field-report.html"
    report.write_text(report_html(rows, all_entries=entries() if everything is None else everything),
                      encoding="utf-8")
    paths["report"] = report
    if any(e.get("sample_id") for e in rows):
        labels = folder / "sample-labels.html"
        labels.write_text(labels_html(rows), encoding="utf-8")
        paths["labels"] = labels
    for e in every:
        for rel in e.get("photos") or []:
            src = photo_path(rel)
            # only a photo that still matches its fingerprint is copied, so the signature never
            # vouches for a changed one (photo_problems() lists it in the export's integrity)
            if _is_stored(rel) and src.is_file() and not (folder / rel).exists() \
                    and _file_sha256(src) == Path(rel).stem:
                (folder / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, folder / rel)
    if (folder / "photos").is_dir():
        paths["photos"] = folder / "photos"
    paths["signature"] = sign_export(folder, paths, every, problems)
    return paths


# ── Signed exports (R4; field network Phase 0) ─────────────────────────────

SIGNATURE_FILE = "signature.json"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sign_export(folder: Path, paths: dict, rows: list[dict], problems: list[str] | None = None) -> Path:
    """signature.json: this installation's signature over the log's head (every entry, through
    the chain) and the SHA-256 of every exported file. verify_export() checks it."""
    from cursiv_v215.core import devicekey
    own = entries()
    files = {f.relative_to(folder).as_posix(): _file_sha256(f) for f in sorted(Path(folder).rglob("*"))
             if f.is_file() and f.name != SIGNATURE_FILE}
    devices = sorted({e.get("device", "") for e in rows})
    env = devicekey.sign({
        "format": "cursiv-export-1",
        "exported_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exported_by_device": _device(),
        "log_head": devicekey.head(own, _device()),
        "entries_exported": len(rows),
        "devices": devices,
        "integrity": "intact" if not (verify() if problems is None else problems) else "problems",
        "files": files,
    })
    out = folder / SIGNATURE_FILE
    out.write_text(json.dumps(env, indent=2), encoding="utf-8")
    return out


def verify_export(folder: Path) -> list[str]:
    """Problems with an export folder's signature and files, or [] when it checks out."""
    from cursiv_v215.core import devicekey
    folder = Path(folder)
    sig = folder / SIGNATURE_FILE
    if not sig.exists():
        return [f"no {SIGNATURE_FILE} in {folder}: this export isn't signed (made before U73?)"]
    try:
        env = json.loads(sig.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [f"{SIGNATURE_FILE} can't be read (cut off or damaged)"]
    if not isinstance(env, dict) or not devicekey.verify(env):
        return ["the signature doesn't match: signature.json was changed, or wasn't made by the key it names"]
    s = env.get("signed")
    files = s.get("files") if isinstance(s, dict) else None
    if not isinstance(files, dict) or s.get("format") != "cursiv-export-1":
        return [f"{SIGNATURE_FILE} isn't a Cursiv export signature"]
    problems = []
    root = folder.resolve()
    for name, digest in files.items():
        f = folder / name
        if not f.resolve().is_relative_to(root):
            problems.append(f"the signature names a file outside the export ({name[:60]})")
        elif not f.is_file():
            problems.append(f"{name} is missing")
        elif _file_sha256(f) != digest:
            problems.append(f"{name} was changed after the export was signed")
    for f in sorted(folder.rglob("*")):
        rel = f.relative_to(folder).as_posix()
        if f.is_file() and rel != SIGNATURE_FILE and rel not in files:
            problems.append(f"{rel} isn't covered by the signature (added after the export was made)")
    return problems


def _signer(key_id: str) -> str:
    """Whose key signed: this installation's, a team device Cursiv has imported signed, or unknown.
    Reads the saved keys only; never makes a key."""
    try:
        from cursiv_v215.core import devicekey
        mine = json.loads(devicekey.key_file().read_text(encoding="utf-8"))
        if mine.get("key_id") == key_id:
            return "this installation's key"
    except (OSError, ValueError):
        pass
    team = log_dir() / "team"
    for f in sorted(team.glob("*.key.json")) if team.is_dir() else []:
        try:
            k = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if k.get("key_id") == key_id:
            return f"not this installation's key; it's the key of {k.get('device')}, imported before"
    return ("not this installation's key, and not a key Cursiv has seen from a team device: "
            "check the key id with whoever sent it")


def verify_export_text(folder: Path) -> str:
    problems = verify_export(folder)
    if problems:
        return "This export does NOT check out:\n" + "\n".join(f"- {p}" for p in problems)
    env = json.loads((Path(folder) / SIGNATURE_FILE).read_text(encoding="utf-8"))
    s = env["signed"]
    head = s.get("log_head") if isinstance(s.get("log_head"), dict) else {}
    text = (f"This export checks out: signed by key {env['key_id']} ({_signer(env['key_id'])}; "
            f"made on laptop {s.get('exported_by_device')}) on "
            f"{s.get('exported_utc')}; {len(s['files'])} files unchanged; {s.get('entries_exported')} entries; the log's "
            f"head was entry {head.get('seq')} ({str(head.get('hash', ''))[:12]}).")
    if s.get("integrity") != "intact":
        text += ("\nBUT when it was made, the log had problems (a changed entry or a damaged photo): "
                 "observations.json lists them under \"integrity\".")
    return text


# ── Field report: a printable summary of what was recorded ────────────────

def select(rows: list[dict], site: str = "", day: str = "") -> list[dict]:
    """Entries for one site (case-insensitive, part of the name is enough) and/or one
    local day ("2026-10-18" or "today")."""
    if day == "today":
        day = datetime.now().strftime("%Y-%m-%d")
    out = rows
    if site:
        out = [e for e in out if site.lower() in (e.get("site") or "").lower()]
    if day:
        out = [e for e in out if (e.get("recorded_local") or "").startswith(day)]
    return out


def site_summary(rows: list[dict]) -> list[dict]:
    """Per site and measurement: count, mean, min, max (numeric values only), unit."""
    import statistics
    groups: dict[tuple, dict] = {}
    for e in rows:
        for m in e.get("measurements") or []:
            if m.get("number") is None:
                continue
            key = (e.get("site") or "(no site)", m["name"].lower(), m.get("unit", ""))
            g = groups.setdefault(key, {"site": key[0], "measurement": m["name"], "unit": key[2], "values": []})
            g["values"].append(m["number"])
    out = []
    for g in groups.values():
        v = g.pop("values")
        out.append({**g, "n": len(v), "mean": statistics.fmean(v), "min": min(v), "max": max(v)})
    return sorted(out, key=lambda g: (g["site"], g["measurement"].lower()))


def report_html(rows: list[dict], title: str = "Field report", all_entries: list[dict] | None = None,
                app_version: str = "") -> str:
    """A printable report of these entries (the current view: corrections applied).
    all_entries: the full log, to list the corrections that apply to these entries."""
    import html
    esc = html.escape
    everything = all_entries if all_entries is not None else entries()
    problems = verify()
    times = sorted(e["recorded_local"] for e in rows)
    span = (f"{times[0][:16].replace('T', ' ')} to {times[-1][:16].replace('T', ' ')}" if times else "no entries")
    ids = {e["id"] for e in rows}
    replaced = {e["corrects"]: e for e in everything if e.get("corrects")}
    corrections = [(c, next((o for o in everything if o["id"] == old), None))
                   for old, c in replaced.items() if c["id"] in ids]

    def num(v: float) -> str:
        return f"{v:.4g}"

    summary = "".join(
        f"<tr><td>{esc(g['site'])}</td><td>{esc(g['measurement'])}</td><td>{esc(g['unit'])}</td>"
        f"<td class=r>{g['n']}</td><td class=r>{num(g['mean'])}</td><td class=r>{num(g['min'])}</td>"
        f"<td class=r>{num(g['max'])}</td></tr>" for g in site_summary(rows))
    body = []
    for e in rows:
        meas = "<br>".join(esc(f"{m['name']} {m['value']}{(' ' + m['unit']) if m['unit'] else ''}")
                           for m in e["measurements"])
        where = f"{e['lat']}, {e['lon']}" if e.get("lat") is not None else ""
        body.append(
            f"<tr><td>{e['seq']}</td><td>{esc(e['recorded_local'][:16].replace('T', ' '))}</td>"
            f"<td>{esc(e.get('sample_id', ''))}</td><td>{esc(e.get('site', ''))}</td><td>{esc(where)}</td>"
            f"<td>{meas}</td><td>{esc(e.get('note', ''))}</td><td>{esc(e.get('observer', ''))}</td>"
            f"<td class=fp>{e['hash'][:12]}</td></tr>")
    fixes = "".join(
        f"<li>Entry {c['seq']} corrects entry {o['seq'] if o else '?'}: {esc(c['reason'])}</li>"
        for c, o in corrections)
    integrity = ("Every entry in the log is intact and in order (fingerprints checked when this report was made)."
                 if not problems else "THE LOG HAS PROBLEMS: " + esc("; ".join(problems)))
    return (
        "<!doctype html><meta charset='utf-8'><title>" + esc(title) + "</title><style>"
        "body{font-family:Arial,sans-serif;margin:14mm;color:#111;font-size:10pt}"
        "h1{font-size:17pt;margin:0 0 2mm}h2{font-size:12pt;margin:7mm 0 2mm}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:1.2mm 2mm;"
        "vertical-align:top;text-align:left}th{background:#eee}.r{text-align:right}"
        ".fp{font-family:Consolas,monospace;font-size:8.5pt;color:#444}.meta{color:#333}"
        ".bad{color:#b00;font-weight:bold}.foot{margin-top:6mm;color:#555;font-size:9pt}"
        "@media print{tr{break-inside:avoid}}</style>"
        f"<h1>{esc(title)}</h1>"
        f"<p class=meta>{len(rows)} entries · {esc(span)} · made "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}{(' · Cursiv ' + esc(app_version)) if app_version else ''}</p>"
        f"<p class='{'meta' if not problems else 'bad'}'>{integrity}</p>"
        + (f"<h2>Summary by site</h2><table><tr><th>Site</th><th>Measurement</th><th>Unit</th><th>n</th>"
           f"<th>Mean</th><th>Min</th><th>Max</th></tr>{summary}</table>" if summary else "")
        + "<h2>Entries</h2><table><tr><th>#</th><th>Recorded</th><th>Sample</th><th>Site</th><th>Location</th>"
          "<th>Measurements</th><th>Note</th><th>Observer</th><th>Fingerprint</th></tr>" + "".join(body) + "</table>"
        + (f"<h2>Corrections</h2><ul>{fixes}</ul><p>The corrected entries stay in the log and in the JSON export.</p>"
           if fixes else "")
        + "<p class=foot>Observations as recorded by people in Cursiv's field notebook. Nothing in this report was "
          "written or changed by the AI. Values are shown exactly as typed; the summary uses numeric values only.</p>")


# ── Typed entries: "log ..." ───────────────────────────────────────────────

_FIELD = re.compile(r"(?i)^\s*(site|observer|note|notes|lat|lon|latitude|longitude|sample|sample id)\s*[:=]\s*(.+)$")
_PAIR = re.compile(r"^\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$")
_MEASURE = re.compile(r"^\s*([A-Za-z][\w ./()%-]*?)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*([^\d\s][^;]*)?\s*$")


def parse(text: str) -> dict:
    """'site: North transect; water temp 12.4 C; pH 7.2; 44.1234, -71.5678; note: turbid'
    -> fields for add(). Parts are split on ';' or new lines. Anything that isn't a
    field, a coordinate pair or 'name number unit' goes into the note, word for word."""
    out = {"site": "", "observer": "", "lat": None, "lon": None, "measurements": [], "note": "", "sample_id": ""}
    notes = []
    for part in re.split(r"[;\n]", text or ""):
        part = part.strip()
        if not part:
            continue
        m = _FIELD.match(part)
        if m:
            key, value = m.group(1).lower(), m.group(2).strip()
            if key in ("note", "notes"):
                notes.append(value)
            elif key in ("lat", "latitude"):
                out["lat"] = float(value)
            elif key in ("lon", "longitude"):
                out["lon"] = float(value)
            elif key in ("sample", "sample id"):
                out["sample_id"] = value
            else:
                out[key] = value
            continue
        m = _PAIR.match(part)
        if m:
            out["lat"], out["lon"] = float(m.group(1)), float(m.group(2))
            continue
        m = _MEASURE.match(part)
        if m:
            out["measurements"].append({"name": m.group(1).strip(), "value": m.group(2),
                                        "unit": (m.group(3) or "").strip()})
            continue
        notes.append(part)
    out["note"] = "; ".join(notes)
    return out


def summary(e: dict) -> str:
    bits = [f"#{e['seq']}", e["recorded_local"].replace("T", " ")]
    if e.get("sample_id"):
        bits.append(f"sample {e['sample_id']}")
    if e["site"]:
        bits.append(e["site"])
    if e["lat"] is not None:
        bits.append(f"{e['lat']}, {e['lon']}")
    meas = ", ".join(f"{m['name']} {m['value']}{(' ' + m['unit']) if m['unit'] else ''}" for m in e["measurements"])
    line = " · ".join(bits) + (f" — {meas}" if meas else "") + (f" — {e['note']}" if e["note"] else "")
    if e.get("corrects"):
        line += f"  (corrects {e['corrects']}: {e['reason']})"
    return line


def command(text: str, observer: str = "") -> str | None:
    """Chat commands: log ..., field log, field log check, field log export. None if not one."""
    t = (text or "").strip()
    low = t.lower()
    if low.startswith("log ") and len(t) > 4:
        # "log out", "log in", "log into my account" aren't field entries
        if re.fullmatch(r"(?i)(in|out|off|on|into|me (in|out))\b[^;\d]*", t[4:].strip()):
            return None
        try:
            fields = parse(t[4:])
            if fields["lat"] is not None:
                fields["location_source"] = "typed"
            fields["observer"] = fields["observer"] or observer
            if fields["sample_id"].lower() in ("auto", "new", "next"):
                fields["sample_id"] = new_sample_id(fields["site"])
            e = add(**fields)
        except ValueError as exc:
            return f"Not saved: {exc}."
        return (f"Saved to the field log: {summary(e)}\nFingerprint {e['hash'][:12]}. "
                "Corrections are added as new entries; nothing is overwritten.")
    if low in ("field log", "fieldlog", "field notes", "show field log"):
        rows = current()
        if not rows:
            return "The field log is empty. Add an entry with: log site: …; water temp 12.4 C; note: …"
        return "Field log (latest 15):\n" + "\n".join(summary(e) for e in rows[-15:])
    m = re.match(r"(?i)^field ?log sample\s+(\S+)$", t)
    if m:
        hist = sample_history(m.group(1))
        if not hist:
            return f"No entries for sample {m.group(1)}."
        return f"Sample {m.group(1)}:\n" + "\n".join(summary(e) for e in hist)
    m = re.match(r"(?i)^field ?(?:log )?report(?:\s+site\s+(.+?))?(?:\s+(today))?\s*$", t)
    if m:
        site, day = (m.group(1) or "").strip(), (m.group(2) or "").lower()
        rows = select(current(), site, day)
        if not rows:
            return "No field entries match" + (f" site '{site}'" if site else "") + (" today" if day else "") + "."
        folder = log_dir() / "reports"
        folder.mkdir(parents=True, exist_ok=True)
        name = "field-report" + (f"-{re.sub(r'[^A-Za-z0-9]+', '-', site).strip('-')}" if site else "") + \
               (f"-{datetime.now():%Y-%m-%d}" if day else "") + f"-{datetime.now():%H%M%S}.html"
        title = "Field report" + (f": {site}" if site else "") + (" (today)" if day else "")
        path = folder / name
        path.write_text(report_html(rows, title), encoding="utf-8")
        return f"Field report saved ({len(rows)} entr{'y' if len(rows) == 1 else 'ies'}): {path}\nOpen it in a browser to read or print it."
    if low in ("field log check", "fieldlog check", "check field log"):
        problems = verify() + photo_problems()
        n = len(entries())
        return (f"All {n} entries are intact and in order." if not problems else
                "The field log has problems:\n" + "\n".join(f"- {p}" for p in problems))
    if low in ("field log export", "fieldlog export", "export field log"):
        paths = export()
        return ("Exported (signed: check it any time with  field log verify <folder>):\n"
                + "\n".join(f"- {k.upper()}: {p}" for k, p in paths.items()))
    m = re.match(r"(?i)^field ?log verify\s+(.+)$", t)
    if m:
        return verify_export_text(Path(m.group(1).strip().strip('"')))
    return None

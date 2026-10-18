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
import os
import re
import socket
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "genesis"
_lock = threading.Lock()


def log_dir() -> Path:
    return Path.home() / ".cursiv" / "fieldlog"


def log_file() -> Path:
    return log_dir() / "observations.jsonl"


def _device() -> str:
    """A short, stable label for this computer (a hash, not its name)."""
    return hashlib.sha256(socket.gethostname().encode("utf-8", "replace")).hexdigest()[:12]


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
            entries.append(json.loads(line))
        except ValueError:
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
    with _lock:
        existing, _bad = _read()
        if corrects and corrects not in {e["id"] for e in existing}:
            raise ValueError(f"no entry {corrects} to correct")
        now = time.time()
        entry = {
            "id": uuid.uuid4().hex[:12],
            "seq": (existing[-1]["seq"] + 1) if existing else 1,
            "recorded_utc": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "recorded_local": datetime.fromtimestamp(now).astimezone().isoformat(timespec="seconds"),
            "observer": observer.strip(),
            "sample_id": sample_id,
            "site": site.strip(),
            "lat": lat_v, "lon": lon_v,
            "location_source": location_source if lat_v is not None else "",
            "measurements": meas,
            "note": note.strip(),
            "photos": [str(p) for p in (photos or [])],
            "corrects": corrects or None,
            "reason": reason.strip(),
            "device": _device(),
            "app_version": app_version,
            "prev": existing[-1]["hash"] if existing else GENESIS,
        }
        entry["hash"] = _fingerprint(entry)
        log_dir().mkdir(parents=True, exist_ok=True)
        # One line per entry, flushed to disk before returning, so a power cut can
        # at worst leave one incomplete last line (verify() reports it).
        with log_file().open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return entry


def correct(entry_id: str, reason: str, **fields) -> dict:
    """A new entry replacing entry_id in the current view. Fields not given are copied from it."""
    old = next((e for e in entries() if e["id"] == entry_id), None)
    if old is None:
        raise ValueError(f"no entry {entry_id} to correct")
    base = {k: old.get(k) for k in ("observer", "site", "lat", "lon", "location_source", "measurements",
                                    "note", "photos", "sample_id")}
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
        prev, seq = e.get("hash"), e.get("seq", seq)
    return problems


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
              "fingerprint")


def export(folder: Path | None = None, include_corrected: bool = False) -> dict[str, Path]:
    """Write CSV, JSON and GeoJSON; returns their paths. JSON always has every entry."""
    folder = folder or (log_dir() / "exports" / datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    folder.mkdir(parents=True, exist_ok=True)
    rows = entries() if include_corrected else current()
    problems = verify()

    csv_path = folder / "observations.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_FIELDS)
        for e in rows:
            common = [e["id"], e["seq"], e["recorded_utc"], e["recorded_local"], e["observer"],
                      e.get("sample_id", ""), e["site"],
                      "" if e["lat"] is None else e["lat"], "" if e["lon"] is None else e["lon"],
                      e["location_source"]]
            tail = [e["note"], ";".join(e["photos"]), e["corrects"] or "", e["reason"], e["hash"]]
            for m in e["measurements"] or [{"name": "", "value": "", "unit": ""}]:
                w.writerow(common + [m["name"], m["value"], m["unit"]] + tail)

    json_path = folder / "observations.json"
    json_path.write_text(json.dumps({
        "exported_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "integrity": "intact" if not problems else problems,
        "entries": entries(),
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    geo_path = folder / "observations.geojson"
    features = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]},
                 "properties": {**{k: e[k] for k in ("id", "seq", "recorded_utc", "observer", "site",
                                                     "measurements", "note", "hash")},
                                "sample_id": e.get("sample_id", "")}}
                for e in rows if e["lat"] is not None]
    geo_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2,
                                   ensure_ascii=False), encoding="utf-8")
    paths = {"csv": csv_path, "json": json_path, "geojson": geo_path}
    if any(e.get("sample_id") for e in rows):
        labels = folder / "sample-labels.html"
        labels.write_text(labels_html(rows), encoding="utf-8")
        paths["labels"] = labels
    return paths


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
    if low in ("field log check", "fieldlog check", "check field log"):
        problems = verify()
        n = len(entries())
        return (f"All {n} entries are intact and in order." if not problems else
                "The field log has problems:\n" + "\n".join(f"- {p}" for p in problems))
    if low in ("field log export", "fieldlog export", "export field log"):
        paths = export()
        return "Exported:\n" + "\n".join(f"- {k.upper()}: {p}" for k, p in paths.items())
    return None

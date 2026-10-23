"""The whole field-record workflow, end to end, with the production code on both sides:

phone: website/notebook/core.js (run under Node) makes entries with photos, coordinates,
       sample IDs, measurements and a correction, signs them, and builds the real send file
       (format 2 zip) twice: after 3 entries, and again after 6.
laptop: fieldsync.import_phone_bundle (the Import menu, the chat command and the Wi-Fi
        receiver all call it) imports it; then a signed team export.

Node runs the phone's JavaScript, not a phone's browser: IndexedDB, the camera, the share
sheet and real Safari/Chrome crypto are not exercised here (docs/EVIDENCE.md).
"""
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from cursiv_engine.core import devicekey, fieldlog, fieldsync

REPO = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="needs Node.js to run the phone's code")

PHONE = r"""
import * as core from "./core.mjs";
import { readFileSync, writeFileSync } from "node:fs";
const [outDir, photoA, photoB] = process.argv.slice(2);
const keyPair = await core.newKeyPair();
const device = await core.deviceLabel(await core.publicKeyB64(keyPair.publicKey));
const store = {};                                      // what the phone keeps in IndexedDB "photos"
async function keep(path, name) {
  const bytes = new Uint8Array(readFileSync(path));
  const rel = `photos/${await core.sha256Hex(bytes)}.jpg`;
  store[rel] = new Blob([bytes], { type: "image/jpeg" });
  return { rel, name };
}
const pa = await keep(photoA, "IMG_0001.jpg"), pb = await keep(photoB, "IMG_0002.jpg");
const rows = [], typed = [];
let t = Date.parse("2026-10-17T13:00:00Z");
async function add(f) {
  typed.push(f);
  t += 7 * 60 * 1000;
  rows.push(await core.makeEntry(rows, device, f, new Date(t)));
}
async function send(name) {
  const used = {};
  for (const e of rows) for (const rel of e.photos) used[rel] = store[rel];
  const zip = await core.makeZipBundle(rows, device, keyPair, used, "Ana Ruíz", new Date(t + 60000));
  writeFileSync(`${outDir}/${name}`, new Uint8Array(await zip.arrayBuffer()));
}
await add({ observer: "Ana Ruíz", site: "Upper Brook (site A)", sample_id: "UBA-20261017-001",
            lat: "44.1234567", lon: "-71.5678901", location_source: "phone GPS", location_accuracy_m: "4.6",
            location_fix_utc: "2026-10-17T13:06:58Z",
            measurements: [{ name: "water temp", value: "12.40", unit: "°C" }, { name: "pH", value: "7.2" }],
            note: "riffle, clear", photos: [pa] });
await add({ observer: "Ana Ruíz", site: "Upper Brook (site A)", sample_id: "UBA-20261017-002",
            lat: "44.1239", lon: "-71.5671", location_source: "typed",
            measurements: [{ name: "conductivity", value: "118", unit: "µS/cm" }], note: "", photos: [] });
await add({ observer: "Ana Ruíz", site: "Lower Brook (site B)", sample_id: "LBB-20261017-001",
            lat: "-33.8688", lon: "151.2093", location_source: "typed",
            measurements: [{ name: "turbidity", value: "0.0", unit: "NTU" }], note: "zero is a real reading",
            photos: [pb] });
await send("send-1.cursivsync");
// later: a correction of entry 2 (meter recalibrated) and three more entries
await add({ observer: "Ana Ruíz", site: "Upper Brook (site A)", sample_id: "UBA-20261017-002",
            lat: "44.1239", lon: "-71.5671", location_source: "typed",
            measurements: [{ name: "conductivity", value: "121", unit: "µS/cm" }], note: "",
            corrects: rows[1].id, reason: "meter recalibrated", photos: [] });
await add({ observer: "Ben Okafor", site: "Lower Brook (site B)", sample_id: "LBB-20261017-002",
            measurements: [{ name: "count", value: "12" }], note: "mayfly nymphs", photos: [pa, pb] });
await add({ observer: "Ben Okafor", site: "Ridge", note: "storm cell to the west, left the ridge", photos: [] });
await send("send-2.cursivsync");
writeFileSync(`${outDir}/phone.json`, JSON.stringify({ device, key_id: await core.keyId(await core.publicKeyB64(keyPair.publicKey)),
                                                        typed, rows }));
"""


def _jpeg(path: Path, colour, gps=None) -> Path:
    from PIL import Image
    img = Image.new("RGB", (64, 48), colour)
    img.save(path, "JPEG", quality=80)
    return path


@pytest.fixture
def laptop(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "laptop" / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptopA")
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / "laptop" / "device_key.json")
    devicekey._cache.clear()
    return tmp_path


@pytest.fixture
def phone(laptop):
    work = laptop / "phone"
    work.mkdir()
    shutil.copyfile(REPO / "website" / "notebook" / "core.js", work / "core.mjs")
    (work / "phone.mjs").write_text(PHONE, encoding="utf-8")
    a = _jpeg(work / "a.jpg", (30, 120, 60))
    b = _jpeg(work / "b.jpg", (200, 40, 40))
    r = subprocess.run([NODE, "phone.mjs", str(work), str(a), str(b)], cwd=work,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    info = json.loads((work / "phone.json").read_text(encoding="utf-8"))
    info.update(send1=work / "send-1.cursivsync", send2=work / "send-2.cursivsync",
                photos={"a": a.read_bytes(), "b": b.read_bytes()})
    return info


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _mine(device):
    return [e for e in fieldsync.team_entries() if e["device"] == device]


def test_phone_to_laptop_every_record_photo_fingerprint_and_signature(phone, laptop):
    device = phone["device"]
    own = fieldlog.add(observer="Lab", site="Base", note="laptop's own entry")       # the laptop has its own log

    # ── first send: 3 entries ──
    r = fieldsync.import_phone_bundle(phone["send1"])
    assert r["added"] == {device: 3} and r["signed"] == {device: phone["key_id"]}
    assert not r["rejected"] and not r["conflicts"] and not r["photos_missing"]
    assert fieldsync.pinned_key(device)["key_id"] == phone["key_id"]

    # ── second send: 6 entries; only the 3 new ones are added ──
    r = fieldsync.import_phone_bundle(phone["send2"])
    assert r["added"] == {device: 3} and not r["rejected"] and not r["photos_missing"]
    rows = _mine(device)
    assert len(rows) == 6 and [e["seq"] for e in rows] == [1, 2, 3, 4, 5, 6]

    # every entry: Python recomputes the phone's fingerprints and checks every value
    assert fieldsync.chain_problems(rows) == []
    assert all(fieldlog.record_problems(e) == [] for e in rows)
    assert [e["hash"] for e in rows] == [e["hash"] for e in phone["rows"]]
    for e, typed in zip(rows, phone["typed"]):
        assert e["observer"] == typed["observer"] and e["site"] == typed["site"]
        assert e["sample_id"] == typed.get("sample_id", "")
        assert [(m["name"], m["value"], m["unit"]) for m in e["measurements"]] == \
               [(m["name"], m["value"], m.get("unit", "")) for m in typed.get("measurements", [])]
        assert e["note"] == typed["note"]
        if typed.get("lat"):
            assert e["lat"] == round(float(typed["lat"]), 7) and e["lon"] == round(float(typed["lon"]), 7)
        else:
            assert e["lat"] is None and e["lon"] is None
    first = rows[0]
    assert first["measurements"][0]["value"] == "12.40" and first["measurements"][0]["number"] == 12.4
    assert first["location_accuracy_m"] == 4.6 and first["location_fix_utc"] == "2026-10-17T13:06:58Z"
    assert rows[2]["lat"] == -33.8688 and rows[2]["measurements"][0]["value"] == "0.0"

    # every photo arrived byte for byte, under its fingerprint
    assert fieldlog.photo_problems(rows) == []
    assert fieldlog.photo_path(rows[0]["photos"][0]).read_bytes() == phone["photos"]["a"]
    assert fieldlog.photo_path(rows[2]["photos"][0]).read_bytes() == phone["photos"]["b"]
    assert rows[4]["photos"] == [rows[0]["photos"][0], rows[2]["photos"][0]]

    # corrections keep history: entry 2 is replaced in the current view, and still in the log
    current = [e for e in fieldsync.team_current() if e["device"] == device]
    assert len(current) == 5
    assert rows[1]["id"] not in {e["id"] for e in current}
    fix = next(e for e in current if e.get("corrects") == rows[1]["id"])
    assert fix["reason"] == "meter recalibrated" and fix["measurements"][0]["value"] == "121"
    assert rows[1]["measurements"][0]["value"] == "118"

    # the laptop's own log is untouched by any of it
    assert fieldlog.entries() == [own] and fieldlog.verify() == []

    # ── importing either file again adds nothing; replaying the older one changes nothing ──
    before = _snapshot(fieldlog.log_dir())
    assert fieldsync.import_phone_bundle(phone["send2"])["unchanged"] == [device]
    assert fieldsync.import_phone_bundle(phone["send1"])["unchanged"] == [device]
    assert _snapshot(fieldlog.log_dir()) == before and len(_mine(device)) == 6

    # ── a signed team export of all of it checks out, photos included ──
    paths = fieldsync.team_export(laptop / "export")
    assert fieldlog.verify_export(laptop / "export") == []
    exported = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert exported["integrity"] == "intact" and len(exported["entries"]) == 7
    for rel in {p for e in rows for p in e["photos"]}:
        assert (laptop / "export" / rel).read_bytes() == fieldlog.photo_path(rel).read_bytes()
    assert "(this installation's key;" in fieldlog.verify_export_text(laptop / "export")


def _rezip(src: Path, dest: Path, change) -> Path:
    with zipfile.ZipFile(src) as z:
        files = {n: z.read(n) for n in z.namelist()}
    change(files)
    with zipfile.ZipFile(dest, "w") as z:
        for n, data in files.items():
            z.writestr(n, data)
    return dest


def _flip(b: bytes, at: int) -> bytes:
    return b[:at] + bytes([b[at] ^ 1]) + b[at + 1:]


@pytest.mark.parametrize("damage,expect", [
    ("log byte", "refused"),
    ("log line removed", "refused"),
    ("manifest removed", "refused"),
    ("signature changed", "refused"),
    ("photo byte", "photo"),
    ("truncated file", "error"),
    ("not a zip", "error"),
])
def test_a_damaged_send_file_is_caught_and_the_laptop_keeps_what_it_had(phone, laptop, damage, expect):
    device = phone["device"]
    fieldsync.import_phone_bundle(phone["send1"])
    before = _snapshot(fieldlog.log_dir())
    log = f"{fieldsync.SHARE_DIR}/{device}.jsonl"
    man = f"{fieldsync.SHARE_DIR}/{device}.manifest.json"
    bad = laptop / "bad.cursivsync"
    src = phone["send2"]
    if damage == "log byte":
        def change(f):
            f[log] = f[log].replace(b'"mayfly nymphs"', b'"mayfly nymphz"')
        _rezip(src, bad, change)
    elif damage == "log line removed":
        def change(f):
            lines = f[log].splitlines(keepends=True)
            f[log] = b"".join(lines[:3] + lines[4:])
        _rezip(src, bad, change)
    elif damage == "manifest removed":
        _rezip(src, bad, lambda f: f.pop(man))
    elif damage == "signature changed":
        def change(f):
            m = json.loads(f[man])
            m["head"]["signed"]["entries"] = 5
            f[man] = json.dumps(m).encode()
        _rezip(src, bad, change)
    elif damage == "photo byte":
        def change(f):
            name = next(n for n in f if "/photos/" in n)
            f[name] = _flip(f[name], len(f[name]) // 2)
        _rezip(src, bad, change)
    elif damage == "truncated file":
        data = src.read_bytes()
        bad.write_bytes(data[: len(data) * 2 // 3])
    else:
        bad.write_bytes(b"PK\x03\x04 this is not really a zip")

    if expect == "error":
        with pytest.raises(ValueError):
            fieldsync.import_phone_bundle(bad)
    else:
        r = fieldsync.import_phone_bundle(bad)
        if expect == "refused":
            assert not r["added"] and r["rejected"], r
        else:   # entries signed and intact; the laptop already has a verified copy of that photo and keeps it
            assert r["added"] == {device: 3} and not r["photos_missing"]
    after = _snapshot(fieldlog.log_dir())
    if expect == "photo":
        # the 3 new entries went in (they check out); the team copy only grew, nothing else changed
        team = f"team/{device}.jsonl"
        assert after[team].startswith(before[team])
        assert {k: v for k, v in after.items() if k in before and k != team} == \
               {k: v for k, v in before.items() if k != team}
        assert fieldlog.photo_problems(_mine(device)) == []
    else:
        assert after == before
    assert len(_mine(device)) == (6 if expect == "photo" else 3)
    assert fieldsync.chain_problems(_mine(device)) == []
    # and the good file still imports afterwards
    assert fieldsync.import_phone_bundle(phone["send2"])["added"] in ({device: 3}, {})
    assert fieldlog.photo_problems(_mine(device)) == []


def test_a_damaged_photo_on_a_first_import_is_left_out_and_named(phone, laptop):
    device = phone["device"]
    bad = _rezip(phone["send2"], laptop / "bad.cursivsync", lambda f: f.update(
        {n: _flip(f[n], len(f[n]) // 2) for n in f if "/photos/" in n and n == sorted(x for x in f if "/photos/" in x)[0]}))
    r = fieldsync.import_phone_bundle(bad)
    assert r["added"] == {device: 6} and r["photos_missing"] == {device: 1}
    assert "1 photo(s) missing" in fieldsync.report_text(r)
    problems = fieldlog.photo_problems(_mine(device))
    assert problems and all(p.endswith("is missing") for p in problems)
    # the good file later supplies the photo, checked against its fingerprint
    fieldsync.import_phone_bundle(phone["send2"])
    assert fieldlog.photo_problems(_mine(device)) == []


# ── the same workflow with offline mode on, every connection attempt recorded ──

_attempts: list | None = None


def _watch(event, args):
    if _attempts is None:
        return
    from cursiv_engine.core import netgate
    if event in ("socket.connect", "socket.sendto"):
        host = args[1][0] if len(args) > 1 and isinstance(args[1], tuple) else None
    elif event in ("socket.getaddrinfo", "socket.gethostbyname"):
        host = args[0]
    else:
        return
    if not netgate.is_local(host):
        _attempts.append((event, host))


import sys as _sys                                      # noqa: E402
_sys.addaudithook(_watch)


def test_receive_import_and_export_work_offline_without_reaching_anything(phone, laptop, monkeypatch):
    global _attempts
    import http.client
    from cursiv_engine.core import netgate, phone_receive
    monkeypatch.setattr(netgate, "CONFIG_FILE", laptop / "app" / "config.json")
    netgate.set_offline(True)
    assert not netgate.allowed()
    _attempts = []
    try:
        r = phone_receive.Receiver(port=0)
        r.start()
        try:
            c = http.client.HTTPConnection("127.0.0.1", r.port, timeout=30)
            c.request("PUT", "/upload", body=phone["send2"].read_bytes(),
                      headers={"X-Cursiv-Code": r.code, "X-File-Name": "send-2.cursivsync"})
            j = json.loads(c.getresponse().read())
        finally:
            r.stop()
        assert f"{phone['device']}: 6 new entries" in j["message"], j
        paths = fieldsync.team_export(laptop / "export")
        assert fieldlog.verify_export(laptop / "export") == [] and "photos" in paths
        assert fieldlog.photo_problems(_mine(phone["device"])) == []
    finally:
        seen, _attempts = _attempts, None
    assert seen == [], seen

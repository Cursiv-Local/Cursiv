"""The phone notebook (website/notebook): its log, built by the phone's own core.js under Node,
must import into Cursiv through the team-sync checks with every fingerprint and the signature
verified by Python. Skipped where Node isn't installed."""
import json
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

from cursiv_v215.core import devicekey, fieldlog, fieldsync

REPO = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="needs Node.js to run the phone's code")

SCRIPT = r"""
import * as core from "./core.mjs";
import { writeFileSync } from "node:fs";
const out = process.argv[2], extra = process.argv[3] === "extra";
const keyPair = await core.newKeyPair();
const pub = await core.publicKeyB64(keyPair.publicKey);
const device = await core.deviceLabel(pub);
const photoBytes = new TextEncoder().encode("pretend these are JPEG bytes");
const rel = `photos/${await core.sha256Hex(photoBytes)}.jpg`;
const rows = [];
const add = async f => rows.push(await core.makeEntry(rows, device, f, new Date("2026-10-19T14:31:05Z")));
await add({ observer: "Ana Ruíz", site: "Upper Brook (site A)", lat: "44.1234567", lon: "-71.5678",
            location_source: "phone GPS ±6 m", sample_id: "UBA-20261019-001",
            measurements: [{ name: "water temp", value: "12.40", unit: "°C" }, { name: "count", value: "12" },
                           { name: "pH", value: "7.2" }, { name: "tiny", value: "0.0000001" }],
            note: "café ☂ — riffle, \"clear\" water\nsecond line", photos: [{ rel, name: "IMG_1.jpg" }] });
await add({ observer: "Ana Ruíz", site: "Upper Brook (site A)", measurements: [{ name: "pH", value: "7.30" }],
            corrects: rows[0].id, reason: "meter recalibrated", photos: [{ rel }] });
if (extra) await add({ observer: "Ana Ruíz", note: "third entry" });
const photos = { [rel]: core.b64(photoBytes) };
const bundle = await core.makeBundle(rows, device, keyPair, photos, "Ana Ruíz");
writeFileSync(out, JSON.stringify(bundle));
console.log(device);
"""


@pytest.fixture
def laptop(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "laptop" / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptopA")
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / "laptop" / "device_key.json")
    devicekey._cache.clear()
    return tmp_path


def _phone(tmp_path, name="send.cursivsync", extra=False, workdir=None):
    work = workdir or (tmp_path / "phone")
    work.mkdir(exist_ok=True)
    shutil.copyfile(REPO / "website" / "notebook" / "core.js", work / "core.mjs")
    (work / "make.mjs").write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / name
    r = subprocess.run([NODE, "make.mjs", str(out), "extra" if extra else ""], cwd=work,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return out, r.stdout.strip()


def test_a_phone_log_imports_with_every_fingerprint_and_the_signature_checked(laptop):
    out, device = _phone(laptop)
    r = fieldsync.import_phone_bundle(out)
    assert r["added"] == {device: 2} and device in r["signed"] and not r["rejected"]
    assert not r["photos_missing"]
    rows = [e for e in fieldsync.team_entries() if e["device"] == device]
    assert fieldsync.chain_problems(rows) == []                     # Python re-derives every JS fingerprint
    first = rows[0]
    assert first["measurements"][0]["value"] == "12.40" and first["location_source"] == "phone GPS ±6 m"
    assert first["note"].startswith("café ☂") and fieldlog.photo_path(first["photos"][0]).exists()
    current = [e for e in fieldsync.team_current() if e["device"] == device]
    assert len(current) == 1 and current[0]["reason"] == "meter recalibrated"
    paths = fieldsync.team_export(laptop / "export")
    assert fieldlog.verify_export(laptop / "export") == [] and "photos" in paths


def test_sending_the_same_file_again_adds_nothing_and_the_key_is_remembered(laptop):
    phone_dir = laptop / "phone"
    out, device = _phone(laptop, "one.cursivsync", workdir=phone_dir)
    fieldsync.import_phone_bundle(out)
    # a later send from the same phone: same key, so the chain must continue (the key is pinned)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert fieldsync.import_phone_bundle(out)["unchanged"] == [device]
    assert data["manifest"]["head"]["key_id"] == fieldsync.pinned_key(device)["key_id"]


def test_a_changed_phone_file_is_refused(laptop):
    out, device = _phone(laptop)
    data = json.loads(out.read_text(encoding="utf-8"))
    data["entries"][0]["measurements"][0]["value"] = "19.90"
    out.write_text(json.dumps(data), encoding="utf-8")
    r = fieldsync.import_phone_bundle(out)
    assert not r["added"] and "changed after it was recorded" in r["rejected"][0]


def test_not_a_phone_file(laptop):
    bad = laptop / "x.cursivsync"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        fieldsync.import_phone_bundle(bad)
    bad.write_text(json.dumps({"format": "cursiv-phone-bundle-1", "device": "laptopB"}), encoding="utf-8")
    with pytest.raises(ValueError):
        fieldsync.import_phone_bundle(bad)


def test_the_chat_command_imports_a_phone_file(laptop):
    out, device = _phone(laptop)
    text = fieldsync.command(f'field log import "{out}"')
    assert f"{device}: 2 new entries" in text and "signature checked" in text

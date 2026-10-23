"""Field-record integrity under attack and accident: every way a record, a share, a photo, a
signature or an export can be wrong, and what Cursiv actually does about it.

The rule throughout: invalid data never becomes trusted data, and a failed import leaves the
records already on this laptop exactly as they were (byte for byte).
A shared log is accepted or refused whole: its entries are one chain, so a partial import
would mean trusting a chain that doesn't check out. Separate laptops' logs in one folder are
judged separately, and the report says which went in and which didn't.
"""
import base64
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from cursiv_engine.core import devicekey, fieldlog, fieldsync


@pytest.fixture
def team(tmp_path, monkeypatch):
    """laptop("A") switches which laptop's log and signing key the calls use."""
    state = {}
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / state["name"] / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptop" + state["name"])
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / state["name"] / "device_key.json")

    @contextmanager
    def laptop(name):
        state["name"] = name
        devicekey._cache.clear()
        yield

    return laptop, tmp_path / "usb"


def _log(laptop, name, n, **extra):
    with laptop(name):
        for i in range(n):
            fieldlog.add(observer=name, site=f"Site {i}", measurements=[{"name": "pH", "value": f"7.{i}"}],
                         sample_id=f"{name}-{i:03d}", **extra)


def _snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _share_paths(usb: Path, device: str):
    d = usb / fieldsync.SHARE_DIR
    return d / f"{device}.jsonl", d / f"{device}.manifest.json"


def _rows(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in rows), encoding="utf-8")


def _rechain(rows: list[dict], keep_seq: bool = False) -> list[dict]:
    """What a careful forger does: recompute every prev/hash so the chain itself checks out."""
    prev = fieldlog.GENESIS
    for i, e in enumerate(rows, 1):
        if not keep_seq:
            e["seq"] = i
        e["prev"] = prev
        e["hash"] = fieldlog._fingerprint(e)
        prev = e["hash"]
    return rows


def _forge_share(usb: Path, device: str, rows: list[dict], key_name: str, laptop) -> None:
    """Write a share for `device` with a correct chain, manifest and a valid signature, from another key."""
    log, man = _share_paths(usb, device)
    _write_rows(log, rows)
    with laptop(key_name):
        head = devicekey.signed_head(rows, device)
    man.write_text(json.dumps({"device": device, "entries": len(rows), "last_hash": rows[-1]["hash"],
                               "head": head}), encoding="utf-8")


@pytest.fixture
def imported_once(team):
    """B shared 3 entries; A imported them. Returns (laptop, usb, A's state before any attack)."""
    laptop, usb = team
    _log(laptop, "A", 2)
    _log(laptop, "B", 3)
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 3} and r["signed"]
        before = _snapshot(fieldlog.log_dir())
    return laptop, usb, before


def _import_refused(laptop, usb, before, *, phrase=""):
    """Import as A; the log must be refused with a reason and A's records left untouched."""
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"], r
        assert r["rejected"] or r["conflicts"], r
        if phrase:
            assert phrase in " ".join(r["rejected"] + r["conflicts"]), r
        after = _snapshot(fieldlog.log_dir())
        # nothing that was there changed; at most a conflict copy was added beside it
        assert {k: v for k, v in after.items() if k in before} == before
        assert all(".conflict-" in k for k in set(after) - set(before)), set(after) - set(before)
        assert len([e for e in fieldsync.team_entries() if e["device"] == "laptopB"]) == 3
        assert fieldlog.verify() == []
    return r


# ── 1-3: a record changed, removed, reordered or duplicated ─────────────────────

def _grow_and_share(laptop, usb, n=2):
    _log(laptop, "B", n)
    with laptop("B"):
        fieldsync.share(usb)


def test_a_record_changed_after_it_was_recorded_is_refused(imported_once):
    laptop, usb, before = imported_once
    _grow_and_share(laptop, usb)
    log, _ = _share_paths(usb, "laptopB")
    rows = _rows(log)
    rows[1]["measurements"][0]["value"] = "9.9"
    _write_rows(log, rows)
    _import_refused(laptop, usb, before, phrase="changed after it was recorded")


def test_a_record_removed_from_the_middle_is_refused(imported_once):
    laptop, usb, before = imported_once
    _grow_and_share(laptop, usb)
    log, _ = _share_paths(usb, "laptopB")
    rows = _rows(log)
    del rows[2]
    _write_rows(log, rows)
    _import_refused(laptop, usb, before, phrase="doesn't follow the entry before it")


@pytest.mark.parametrize("how", ["swap", "duplicate"])
def test_records_reordered_or_duplicated_are_refused(imported_once, how):
    laptop, usb, before = imported_once
    _grow_and_share(laptop, usb)
    log, _ = _share_paths(usb, "laptopB")
    rows = _rows(log)
    if how == "swap":
        rows[3], rows[4] = rows[4], rows[3]
    else:
        rows.insert(3, dict(rows[2]))
    _write_rows(log, rows)
    _import_refused(laptop, usb, before)


def test_a_forger_who_rechains_and_resigns_with_another_key_is_refused(imported_once):
    laptop, usb, before = imported_once
    log, _ = _share_paths(usb, "laptopB")
    rows = _rows(log)
    rows[0]["measurements"][0]["value"] = "4.0"
    _forge_share(usb, "laptopB", _rechain(rows), "Mallory", laptop)
    _import_refused(laptop, usb, before, phrase="different key")


# ── 4-5: photos missing, corrupted or changed ─────────────────────────────────

def _photo(tmp: Path, name="p.jpg", data=b"\xff\xd8\xff pretend jpeg") -> Path:
    p = tmp / name
    p.write_bytes(data)
    return p


def test_a_missing_or_corrupted_photo_is_reported_and_never_stored(team, tmp_path):
    laptop, usb = team
    with laptop("B"):
        e1 = fieldlog.add(note="one", photos=[_photo(tmp_path, "a.jpg", b"AAAA")])
        e2 = fieldlog.add(note="two", photos=[_photo(tmp_path, "b.jpg", b"BBBB")])
        out = fieldsync.share(usb)
    (out / e1["photos"][0]).unlink()                              # missing
    (out / e2["photos"][0]).write_bytes(b"BBBX")                  # corrupted in transit
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 2} and r["photos_missing"] == {"laptopB": 2}
        assert "2 photo(s) missing" in fieldsync.report_text(r)
        assert not fieldlog.photo_path(e1["photos"][0]).exists()
        assert not fieldlog.photo_path(e2["photos"][0]).exists()      # the bad copy wasn't kept
        assert fieldlog.photo_problems(fieldsync.team_entries()) == [
            f"entry 1 (laptopB): photo {e1['photos'][0]} is missing",
            f"entry 2 (laptopB): photo {e2['photos'][0]} is missing"]


def test_a_stored_photo_changed_on_disk_is_detected_and_not_exported_as_authentic(team, tmp_path):
    laptop, _ = team
    with laptop("A"):
        e = fieldlog.add(note="riffle", photos=[_photo(tmp_path)])
        assert fieldlog.photo_problems() == []
        fieldlog.photo_path(e["photos"][0]).write_bytes(b"edited later")
        problems = fieldlog.photo_problems()
        assert problems and "doesn't match its fingerprint" in problems[0]
        assert "doesn't match its fingerprint" in fieldlog.command("field log check")
        paths = fieldlog.export(tmp_path / "export")
        assert not (tmp_path / "export" / e["photos"][0]).exists()     # not copied, so not signed as genuine
        data = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert data["integrity"] != "intact" and "fingerprint" in " ".join(data["integrity"])
        sig = json.loads(paths["signature"].read_text(encoding="utf-8"))
        assert sig["signed"]["integrity"] == "problems"


def test_a_share_cannot_overwrite_a_photo_already_here(team, tmp_path):
    laptop, usb = team
    with laptop("A"):
        e = fieldlog.add(note="mine", photos=[_photo(tmp_path, data=b"original")])
        original = fieldlog.photo_path(e["photos"][0]).read_bytes()
    with laptop("B"):
        fieldlog.add(note="theirs", photos=[_photo(tmp_path, data=b"original")])
        out = fieldsync.share(usb)
    (out / e["photos"][0]).write_bytes(b"swapped")
    with laptop("A"):
        fieldsync.import_folder(usb)
        assert fieldlog.photo_path(e["photos"][0]).read_bytes() == original


# ── 6-7: signatures missing, malformed, invalid; a key that isn't the device's ──

def test_a_signature_removed_after_signed_shares_is_refused(imported_once):
    laptop, usb, before = imported_once
    _grow_and_share(laptop, usb)
    _, man = _share_paths(usb, "laptopB")
    m = json.loads(man.read_text(encoding="utf-8"))
    del m["head"]
    man.write_text(json.dumps(m), encoding="utf-8")
    _import_refused(laptop, usb, before, phrase="isn't signed")


@pytest.mark.parametrize("damage", [
    lambda h: h.update(signature="not base64 !!"),
    lambda h: h.update(signature=base64.b64encode(b"x" * 64).decode()),
    lambda h: h.update(public_key="AAAA"),
    lambda h: h.update(signed="a string, not a head"),
    lambda h: h.pop("public_key"),
    lambda h: h["signed"].update(entries=99),
])
def test_a_malformed_or_invalid_signature_is_refused_without_crashing(imported_once, damage):
    laptop, usb, before = imported_once
    _grow_and_share(laptop, usb)
    _, man = _share_paths(usb, "laptopB")
    m = json.loads(man.read_text(encoding="utf-8"))
    damage(m["head"])
    man.write_text(json.dumps(m), encoding="utf-8")
    _import_refused(laptop, usb, before)


def test_a_manifest_that_isnt_json_refuses_that_log_only(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    _log(laptop, "C", 2)
    for name in ("B", "C"):
        with laptop(name):
            fieldsync.share(usb)
    _, man = _share_paths(usb, "laptopB")
    man.write_text('{"device": "laptopB", "entr', encoding="utf-8")
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopC": 2}
        assert any(x.startswith("laptopB:") and "manifest" in x for x in r["rejected"]), r


def _phone_rows(device: str, n: int = 2) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append({"schema": 1, "id": f"{i:012x}", "seq": i + 1, "recorded_utc": "2026-10-18T10:00:00Z",
                     "recorded_local": "2026-10-18T06:00:00-04:00", "observer": "P", "sample_id": "",
                     "site": "S", "lat": None, "lon": None, "location_source": "", "location_accuracy_m": None,
                     "location_fix_utc": "", "measurements": [], "note": f"n{i}", "photos": [], "corrects": None,
                     "reason": "", "device": device, "app_version": "phone-notebook-1"})
    return _rechain(rows)


def test_a_phone_whose_key_doesnt_match_its_name_is_refused_even_the_first_time(team):
    """A phone's name is made from its public key ("phone-" + key id), so a file signed by any
    other key can't claim that phone's name, even before Cursiv has seen the phone."""
    laptop, usb = team
    (usb / fieldsync.SHARE_DIR).mkdir(parents=True)
    with laptop("Mallory"):
        real_label = "phone-" + devicekey.load()[1]["key_id"][:12]
    victim = "phone-" + "ab" * 6
    _forge_share(usb, victim, _phone_rows(victim), "Mallory", laptop)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "isn't the key that phone's name comes from" in r["rejected"][0]
        assert not fieldsync.pinned_key(victim)
    # the same file under the label its key really gives is accepted
    for p in (usb / fieldsync.SHARE_DIR).iterdir():
        p.unlink()
    _forge_share(usb, real_label, _phone_rows(real_label), "Mallory", laptop)
    with laptop("A"):
        assert fieldsync.import_folder(usb)["added"] == {real_label: 2}


# ── 9: invalid values inside an otherwise well-formed, correctly chained share ──

@pytest.mark.parametrize("field,value", [
    ("lat", 999.0), ("lon", -181.0), ("lat", "44.1"),
    ("recorded_utc", "yesterday"), ("recorded_local", 5),
    ("seq", "1"), ("measurements", "pH 7"), ("measurements", [{"name": "pH"}]),
    ("measurements", [{"name": "pH", "value": "7", "number": "seven", "unit": ""}]),
    ("sample_id", "../../etc"), ("photos", ["../../secret.txt"]), ("photos", "photos/x.jpg"),
    ("location_accuracy_m", -3), ("note", None), ("corrects", 7), ("device", "laptopZ"),
])
def test_a_correctly_chained_and_signed_share_with_an_invalid_value_is_refused(team, field, value):
    """Fingerprints only prove a record wasn't changed after it was made. A record made wrong
    (by a bug, an old version, or on purpose) must still not be accepted."""
    laptop, usb = team
    _log(laptop, "B", 3)
    with laptop("B"):
        fieldsync.share(usb)
    log, _ = _share_paths(usb, "laptopB")
    rows = _rows(log)
    rows[1][field] = value
    if field == "lat":
        rows[1]["lon"] = 10.0
    _forge_share(usb, "laptopB", _rechain(rows, keep_seq=True), "B", laptop)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and r["rejected"], r
        assert "entry 2" in r["rejected"][0], r["rejected"]
        assert fieldsync.team_entries() == fieldlog.entries() == []
        fieldsync.team_current(), fieldsync.sample_clashes()          # and nothing downstream breaks


def test_a_line_that_isnt_an_entry_is_refused_without_crashing(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    with laptop("B"):
        fieldsync.share(usb)
    log, _ = _share_paths(usb, "laptopB")
    log.write_text(log.read_text(encoding="utf-8") + "[1, 2, 3]\n", encoding="utf-8")
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "isn't a complete entry" in r["rejected"][0]


# ── 10-12: repeated, mixed and replayed imports ───────────────────────────────

def test_a_repeated_import_adds_nothing(imported_once):
    laptop, usb, before = imported_once
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["unchanged"] == ["laptopB"] and not r["added"]
        assert _snapshot(fieldlog.log_dir()) == before


def test_a_folder_with_good_and_bad_logs_imports_the_good_and_names_the_bad(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    _log(laptop, "C", 3)
    for name in ("B", "C"):
        with laptop(name):
            fieldsync.share(usb)
    log, _ = _share_paths(usb, "laptopC")
    rows = _rows(log)
    rows[2]["note"] = "tampered"
    _write_rows(log, rows)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 2}
        assert len(r["rejected"]) == 1 and r["rejected"][0].startswith("laptopC:")
        text = fieldsync.report_text(r)
        assert "laptopB: 2 new entries" in text and "NOT IMPORTED laptopC" in text
        assert not [e for e in fieldsync.team_entries() if e["device"] == "laptopC"]   # none of C's 3, not 2 of them


def test_an_older_share_replayed_after_newer_records_changes_nothing(team, tmp_path):
    laptop, usb = team
    _log(laptop, "B", 2)
    with laptop("B"):
        fieldsync.share(usb)
    old = tmp_path / "old-usb"
    import shutil
    shutil.copytree(usb, old)
    _log(laptop, "B", 3)
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        assert fieldsync.import_folder(usb)["added"] == {"laptopB": 5}
        before = _snapshot(fieldlog.log_dir())
        r = fieldsync.import_folder(old)
        assert r["unchanged"] == ["laptopB"] and not r["added"] and not r["conflicts"]
        assert _snapshot(fieldlog.log_dir()) == before
        assert len(fieldsync.team_entries()) == 5


# ── 8: exports truncated, malformed, added to, or signed by an unknown key ────────

@pytest.fixture
def export_folder(team, tmp_path):
    laptop, _ = team
    _log(laptop, "A", 3)
    with laptop("A"):
        fieldlog.export(tmp_path / "exp")
        assert fieldlog.verify_export(tmp_path / "exp") == []
    return laptop, tmp_path / "exp"


def test_a_truncated_export_file_is_detected(export_folder):
    laptop, folder = export_folder
    data = (folder / "observations.json").read_bytes()
    (folder / "observations.json").write_bytes(data[: len(data) // 2])
    with laptop("A"):
        assert "observations.json was changed after the export was signed" in fieldlog.verify_export(folder)


def test_a_truncated_or_malformed_signature_is_detected_without_crashing(export_folder):
    laptop, folder = export_folder
    sig = folder / fieldlog.SIGNATURE_FILE
    text = sig.read_text(encoding="utf-8")
    with laptop("A"):
        sig.write_text(text[:40], encoding="utf-8")
        assert "can't be read" in fieldlog.verify_export(folder)[0]
        for bad in ("[]", '{"signed": [1], "public_key": "AAAA", "signature": "AAAA"}', "null"):
            sig.write_text(bad, encoding="utf-8")
            assert fieldlog.verify_export(folder), bad
            assert "does NOT check out" in fieldlog.verify_export_text(folder)


def test_a_file_added_to_a_signed_export_is_reported(export_folder):
    laptop, folder = export_folder
    (folder / "photos").mkdir(exist_ok=True)
    (folder / "photos" / ("0" * 64 + ".jpg")).write_bytes(b"slipped in")
    with laptop("A"):
        problems = fieldlog.verify_export(folder)
        assert problems and "isn't covered by the signature" in problems[0]


def test_an_export_resigned_by_an_unknown_key_says_whose_key_it_is(export_folder):
    laptop, folder = export_folder
    data = json.loads((folder / "observations.json").read_text(encoding="utf-8"))
    data["entries"][0]["note"] = "forged"
    (folder / "observations.json").write_text(json.dumps(data), encoding="utf-8")
    with laptop("Mallory"):
        env = json.loads((folder / fieldlog.SIGNATURE_FILE).read_text(encoding="utf-8"))
        signed = env["signed"]
        signed["files"]["observations.json"] = hashlib.sha256((folder / "observations.json").read_bytes()).hexdigest()
        (folder / fieldlog.SIGNATURE_FILE).write_text(json.dumps(devicekey.sign(signed)), encoding="utf-8")
    with laptop("A"):
        text = fieldlog.verify_export_text(folder)
        # the files match what was signed, but by a key this laptop has never seen
        assert "not this installation's key" in text and "not a key Cursiv has seen" in text
    with laptop("A"):
        fieldlog.export(folder.parent / "mine")
        assert "(this installation's key;" in fieldlog.verify_export_text(folder.parent / "mine")


# ── the laptop's own log: a power cut, then the next entry ──────────────────────

def test_an_entry_after_a_cut_off_last_line_is_kept_readable(team):
    laptop, _ = team
    _log(laptop, "A", 2)
    with laptop("A"):
        with fieldlog.log_file().open("a", encoding="utf-8") as f:
            f.write('{"schema":1,"id":"half')                   # the power went mid-write
        e = fieldlog.add(note="after the power came back")
        assert e["hash"] in {x["hash"] for x in fieldlog.entries()}   # not glued onto the broken line
        problems = fieldlog.verify()
        assert len(problems) == 1 and "line 3 isn't a complete entry" in problems[0]


@pytest.mark.parametrize("acc", ["nan", "inf", "-inf"])
def test_location_accuracy_must_be_a_real_number(team, acc):
    laptop, _ = team
    with laptop("A"), pytest.raises(ValueError):
        fieldlog.add(note="x", lat=44.0, lon=-71.0, location_accuracy_m=acc)

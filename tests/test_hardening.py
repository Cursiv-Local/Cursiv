"""Record format hardening: schema version, optional GPS accuracy, key revocation by the
team lead, photo limits, a flag for a clock that runs ahead."""
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

from cursiv_engine.core import devicekey, fieldlog, fieldsync


@pytest.fixture
def team(tmp_path, monkeypatch):
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


def test_new_entries_carry_the_schema_and_optional_accuracy(team):
    laptop, _ = team
    with laptop("A"):
        e = fieldlog.add(observer="A", site="S", note="pool", lat=44.1, lon=-71.5, location_source="phone GPS",
                         location_accuracy_m=6.43, location_fix_utc="2026-10-19T14:00:00Z")
        assert e["schema"] == fieldlog.SCHEMA == 1 and e["location_accuracy_m"] == 6.4
        plain = fieldlog.add(observer="A", note="no location", location_accuracy_m=5)
        assert plain["location_accuracy_m"] is None and plain["location_fix_utc"] == ""   # only with coordinates
        assert fieldlog.verify() == []
        assert fieldlog.correct(e["id"], "typo", site="S2")["location_accuracy_m"] == 6.4


def test_a_log_from_a_newer_cursiv_is_refused_with_a_reason(team):
    laptop, usb = team
    with laptop("B"):
        fieldlog.add(observer="B", note="x")
        out = fieldsync.share(usb)
    log = out / "laptopB.jsonl"
    e = json.loads(log.read_text().splitlines()[0])
    e["schema"] = 99
    e["hash"] = fieldlog._fingerprint(e)
    log.write_text(json.dumps(e) + "\n")
    m = json.loads((out / "laptopB.manifest.json").read_text())
    m["last_hash"] = e["hash"]
    m.pop("head")
    (out / "laptopB.manifest.json").write_text(json.dumps(m))
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "newer Cursiv" in r["rejected"][0]


def test_the_lead_revokes_a_lost_phones_key(team):
    laptop, usb = team
    with laptop("B"):
        fieldlog.add(observer="B", note="before it was lost")
        fieldsync.share(usb)
    with laptop("A"):
        assert fieldsync.import_folder(usb)["added"] == {"laptopB": 1}
        with pytest.raises(ValueError):
            fieldsync.revoke("laptopB", "")                          # a reason is required
        assert "Revoked laptopB" in fieldsync.command("field log revoke laptopB lost on the ridge", observer="Lead")
        assert fieldsync.revoked()[fieldsync.pinned_key("laptopB")["key_id"]]["by"] == "Lead"
    with laptop("B"):
        fieldlog.add(observer="someone", note="after it was lost")
        fieldsync.share(usb)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert "laptopB" not in r["added"] and "revoked" in r["rejected"][0]
        assert len(fieldsync.team_entries()) == 1                       # what came before stays
        assert "key revoked" in fieldsync.command("team log")
        assert "Not revoked" in fieldsync.command("field log revoke nobody lost")


def test_photos_over_the_limit_aren_t_stored(team, tmp_path, monkeypatch):
    laptop, _ = team
    monkeypatch.setattr(fieldlog, "PHOTO_MAX_MB", 0.001)               # about 1 KB, for the test
    big = tmp_path / "big.jpg"
    big.write_bytes(b"\xff\xd8" + b"0" * 5000)
    with laptop("A"):
        with pytest.raises(ValueError, match="aren't stored"):
            fieldlog.add(observer="A", photos=[big])


def test_a_clock_running_ahead_is_flagged_not_changed(team):
    laptop, usb = team
    with laptop("B"):
        e = fieldlog.add(observer="B", note="from the future")
        fieldsync.share(usb)
    ahead = datetime.now(timezone.utc) + timedelta(minutes=45)
    rows = [dict(e, recorded_utc=ahead.strftime("%Y-%m-%dT%H:%M:%SZ"))]
    assert 40 <= fieldsync._clock_ahead_minutes(rows) <= 46
    assert fieldsync._clock_ahead_minutes([e]) == 0
    text = fieldsync.report_text({"added": {"laptopB": 1}, "unchanged": [], "conflicts": [], "rejected": [],
                                  "own": False, "clock": {"laptopB": 45}})
    assert "clock looks about 45 minutes ahead" in text and "kept as recorded" in text

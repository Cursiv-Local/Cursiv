"""Signed field records (field network Phase 0): device keys, signed USB shares, signed exports."""
import json
from contextlib import contextmanager

import pytest

from cursiv_engine.core import devicekey, fieldlog, fieldsync


# ── the key itself ────────────────────────────────────────────────────────────

def test_key_is_made_once_kept_and_stored_protected(monkeypatch):
    a = devicekey.public_key()
    devicekey._cache.clear()
    assert devicekey.public_key() == a                      # read back, not remade
    data = json.loads(devicekey.key_file().read_text())
    assert data["key_id"] == devicekey.key_id(a)
    import sys
    if sys.platform == "win32":
        assert data["private_key"].startswith("dpapi:")     # encrypted for this Windows user


def test_an_unreadable_key_is_replaced_and_the_old_one_kept_in_history():
    old = devicekey.public_key()
    data = json.loads(devicekey.key_file().read_text())
    data["private_key"] = "dpapi:" + "A" * 40                # e.g. copied from another account
    devicekey.key_file().write_text(json.dumps(data))
    devicekey._cache.clear()
    new = devicekey.public_key()
    hist = json.loads(devicekey.key_file().read_text())["history"]
    assert new != old and hist[-1]["public_key"] == old and "couldn't be read" in hist[-1]["why"]


def test_signatures_catch_any_change():
    env = devicekey.sign({"a": 1, "b": "x"})
    assert devicekey.verify(env)
    assert not devicekey.verify({**env, "signed": {"a": 2, "b": "x"}})
    other = devicekey.sign({"a": 1, "b": "x"})
    assert devicekey.verify(other)
    forged = {**env, "public_key": devicekey.public_key(), "signature": env["signature"][:-4] + "AAAA"}
    assert not devicekey.verify(forged)


# ── USB sync, signed ─────────────────────────────────────────────────────────

@pytest.fixture
def team(tmp_path, monkeypatch):
    """laptop("A") switches the log, device name AND signing key."""
    state = {}
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / state["name"] / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptop" + state.get("as", state["name"]))
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / state["name"] / "device_key.json")

    @contextmanager
    def laptop(name, posing_as=None):
        state["name"], state["as"] = name, posing_as or name
        devicekey._cache.clear()
        yield

    return laptop, tmp_path / "usb"


def _log(laptop, name, n, posing_as=None):
    with laptop(name, posing_as):
        for i in range(n):
            fieldlog.add(observer=name, site="S", measurements=[{"name": "pH", "value": f"7.{i}"}])


def test_a_signed_share_is_checked_and_its_key_remembered(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 2} and "laptopB" in r["signed"]
        assert fieldsync.pinned_key("laptopB")["key_id"] == r["signed"]["laptopB"]
        assert "signature checked" in fieldsync.report_text(r)


def test_another_laptop_using_the_same_name_is_refused(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        fieldsync.import_folder(usb)
    # laptop M (a different machine, a different key) shares under B's name, extending B's chain
    import shutil
    m_dir = usb.parent / "M" / "fieldlog"
    m_dir.mkdir(parents=True)
    shutil.copyfile(usb / fieldsync.SHARE_DIR / "laptopB.jsonl", m_dir / "observations.jsonl")
    _log(laptop, "M", 1, posing_as="B")
    with laptop("M", posing_as="B"):
        fieldsync.share(usb)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "different key" in r["rejected"][0]
        assert len(fieldsync.team_entries()) == 2


def test_an_unsigned_share_after_signed_ones_is_refused_but_old_unsigned_ones_still_import(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    with laptop("B"):
        out = fieldsync.share(usb)
    man = out / "laptopB.manifest.json"
    m = json.loads(man.read_text())
    unsigned = {k: v for k, v in m.items() if k != "head"}
    man.write_text(json.dumps(unsigned))                        # as Cursiv before U73 wrote it
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 2} and r["unsigned"] == ["laptopB"]
        assert "not signed" in fieldsync.report_text(r)
    _log(laptop, "B", 1)
    with laptop("B"):
        fieldsync.share(usb)                                    # now signed: key pinned
    with laptop("A"):
        assert fieldsync.import_folder(usb)["added"] == {"laptopB": 1}
    _log(laptop, "B", 1)
    with laptop("B"):
        fieldsync.share(usb)                                    # a new entry to import...
    m = json.loads(man.read_text())
    m.pop("head")
    man.write_text(json.dumps(m))                               # ...with its signature stripped
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert "laptopB" not in r["added"] and "isn't signed, but this laptop's earlier shares were" in r["rejected"][0]


def test_entries_added_to_a_share_after_signing_are_caught(team):
    laptop, usb = team
    _log(laptop, "B", 2)
    with laptop("B"):
        out = fieldsync.share(usb)
        extra = fieldlog.add(observer="B", note="added after sharing")    # valid chain entry...
    log = out / "laptopB.jsonl"
    log.write_text(log.read_text() + json.dumps(extra) + "\n")
    man = out / "laptopB.manifest.json"
    m = json.loads(man.read_text())
    m["entries"], m["last_hash"] = 3, extra["hash"]                      # ...and a consistent manifest
    man.write_text(json.dumps(m))
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "signature is for a different log" in r["rejected"][0]


# ── signed exports ───────────────────────────────────────────────────────────

def test_an_export_is_signed_and_any_change_is_detected(team, tmp_path):
    laptop, _usb = team
    _log(laptop, "A", 3)
    with laptop("A"):
        paths = fieldlog.export(tmp_path / "exp")
        assert paths["signature"].name == "signature.json"
        assert fieldlog.verify_export(tmp_path / "exp") == []
        assert "checks out" in fieldlog.command(f"field log verify {tmp_path / 'exp'}")
        csv = paths["csv"]
        csv.write_text(csv.read_text().replace("7.1", "7.9"))
        assert "observations.csv was changed" in fieldlog.verify_export(tmp_path / "exp")[0]
        sig = json.loads(paths["signature"].read_text())
        sig["signed"]["files"]["observations.csv"] = "0" * 64
        paths["signature"].write_text(json.dumps(sig))
        assert "signature doesn't match" in fieldlog.verify_export(tmp_path / "exp")[0]
        (tmp_path / "exp" / "signature.json").unlink()
        assert "isn't signed" in fieldlog.verify_export(tmp_path / "exp")[0]

"""U105 (outside review): a drive's signing key can be protected with a passphrase
(cursiv_engine/core/devicekey.py). The same key is kept, so its id and every main computer's pin of it stay
valid; while locked nothing is signed and no new key is made."""
import json

import pytest

from cursiv_engine.core import devicekey, fieldlog, fieldsync


@pytest.fixture
def key(tmp_path, monkeypatch):
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / "device_key.json")
    from cursiv_engine.core import keystore
    monkeypatch.setattr(keystore, "_dpapi_available", lambda: False)     # stored readable, as on a drive
    devicekey.lock()
    yield tmp_path / "device_key.json"
    devicekey.lock()


def test_protecting_keeps_the_same_key_and_hides_it(key):
    _, before = devicekey.load()
    raw_before = json.loads(key.read_text())["private_key"]
    info = devicekey.protect("a long key passphrase")
    assert info["key_id"] == before["key_id"]
    stored = json.loads(key.read_text())
    assert stored["private_key"].startswith(devicekey.PASSPHRASE_PREFIX) and raw_before not in key.read_text()
    assert devicekey.protected() and devicekey.unlocked()


def test_locked_means_nothing_is_signed_and_no_new_key_is_made(key):
    _, before = devicekey.load()
    devicekey.protect("a long key passphrase")
    devicekey.lock()                                         # what a restart leaves
    file_before = key.read_bytes()
    with pytest.raises(devicekey.KeyLocked):
        devicekey.sign({"x": 1})
    with pytest.raises(devicekey.KeyLocked):
        devicekey.load()
    assert key.read_bytes() == file_before                   # the drive kept its identity
    with pytest.raises(ValueError, match="doesn't open"):
        devicekey.unlock("the wrong passphrase")
    devicekey.unlock("a long key passphrase")
    env = devicekey.sign({"x": 1})
    assert devicekey.verify(env) and env["key_id"] == before["key_id"]


def test_a_short_passphrase_is_refused(key):
    devicekey.load()
    with pytest.raises(ValueError, match="at least"):
        devicekey.protect("short")
    assert not devicekey.protected()


def test_a_main_computer_keeps_accepting_a_protected_drives_shares(tmp_path, monkeypatch, key):
    drive, main = tmp_path / "drive", tmp_path / "main"
    place = {"dir": drive}
    monkeypatch.setattr(fieldlog, "log_dir", lambda: place["dir"] / "fieldlog")
    fieldlog.name_new_notebook(drive / "fieldlog", "Ana Ruiz")
    fieldlog.add(observer="Ana", note="before the passphrase")
    usb = tmp_path / "usb"
    fieldsync.share(usb)
    place["dir"] = main
    assert not fieldsync.import_folder(usb)["rejected"]                # pins Ana's key
    place["dir"] = drive
    devicekey.protect("a long key passphrase")
    devicekey.lock()
    fieldlog.add(observer="Ana", note="after; the key is locked")       # recording still works
    with pytest.raises(devicekey.KeyLocked):
        fieldsync.share(usb)                                            # signing doesn't
    devicekey.unlock("a long key passphrase")
    fieldsync.share(usb)
    place["dir"] = main
    r = fieldsync.import_folder(usb)
    assert not r["rejected"] and sum(r["added"].values()) == 1         # same key: still accepted


def test_a_locked_key_is_reported_by_auto_share_not_raised(tmp_path, monkeypatch, key):
    from cursiv_engine.core import paths
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "drive" / "Home" / ".cursiv" / "fieldlog")
    monkeypatch.setattr(paths, "portable_root", lambda: tmp_path / "drive")
    monkeypatch.setattr(fieldlog, "_last_share", -fieldlog.SHARE_EVERY_S)
    devicekey.load()
    devicekey.protect("a long key passphrase")
    devicekey.lock()
    fieldlog.add(observer="Ana", note="saved even though the key is locked")
    assert "locked" in fieldlog.share_problem and len(fieldlog.entries()) == 1

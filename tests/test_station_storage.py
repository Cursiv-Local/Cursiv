"""Field Station drive discovery (cursiv_engine/station/storage.py) and the headless promise: the
station runs without the desktop's Qt toolkit. Real drives and mounting on a Pi are not tested here."""
import json
import subprocess
import sys
from pathlib import Path

from cursiv_engine.station import storage

LSBLK = {"blockdevices": [
    {"name": "mmcblk0", "uuid": None, "label": None, "fstype": None, "size": 63864569856, "mountpoint": None, "rm": False,
     "tran": None, "children": [
        {"name": "mmcblk0p1", "uuid": "1E3B-8A14", "label": "bootfs", "fstype": "vfat", "size": 536870912,
         "mountpoint": "/boot/firmware", "rm": False, "tran": None},
        {"name": "mmcblk0p2", "uuid": "b1c9f2d4-1111-2222-3333-444455556666", "label": "rootfs", "fstype": "ext4",
         "size": 63322128384, "mountpoint": "/", "rm": False, "tran": None}]},
    {"name": "sda", "uuid": None, "label": None, "fstype": None, "size": 512110190592, "mountpoint": None, "rm": False,
     "tran": "usb", "children": [
        {"name": "sda1", "uuid": "9f1e7a2c-aaaa-bbbb-cccc-ddddeeeeffff", "label": "CURSIV-SSD", "fstype": "ext4",
         "size": 512109142016, "mountpoint": "/media/cursiv/CURSIV-SSD", "rm": False, "tran": None}]},
    {"name": "sdb", "uuid": "4A2B-11CC", "label": "ANA-FIELD", "fstype": "exfat", "size": 256060514304,
     "mountpoint": "/media/cursiv/ANA-FIELD", "rm": "1", "tran": "usb"},
    {"name": "sdc", "uuid": "77AA-0001", "label": "UNPLUGGED", "fstype": "exfat", "size": 1, "mountpoint": None, "rm": True},
    {"name": "zram0", "uuid": None, "label": None, "fstype": "swap", "size": 1, "mountpoint": "[SWAP]", "rm": False},
]}


def test_drives_are_identified_by_filesystem_uuid_never_by_device_name():
    rows = storage.parse_lsblk(json.dumps(LSBLK))
    assert [r["id"] for r in rows] == ["1E3B-8A14", "b1c9f2d4-1111-2222-3333-444455556666",
                                      "9f1e7a2c-aaaa-bbbb-cccc-ddddeeeeffff", "4A2B-11CC"]
    assert all(r["id_stable"] and not r["id"].startswith("/dev/") for r in rows)
    ssd = rows[2]
    assert ssd["label"] == "CURSIV-SSD" and ssd["mount"] == "/media/cursiv/CURSIV-SSD" and not ssd["removable"]
    assert rows[3]["removable"] is True                         # "1" from older lsblk counts too
    # unmounted (sdc) and swap aren't listed: nothing to read on them


def test_a_cursiv_workspace_is_recognised_and_nothing_is_written(tmp_path):
    from cursiv_engine.core import fieldlog
    fieldlog.name_new_notebook(tmp_path / "Home" / ".cursiv" / "fieldlog", "Ana Ruiz")
    (tmp_path / "cursiv-field-share").mkdir()
    (tmp_path / "cursiv-field-share" / "2d7401b2034c.jsonl").write_text("", encoding="utf-8")
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    info = storage.workspace_info(tmp_path)
    assert info["notebook"]["name"] == "Ana Ruiz" and info["share_logs"] == ["2d7401b2034c"]
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == before
    assert storage.workspace_info(tmp_path / "empty-drive") is None


def test_discover_uses_lsblk_when_present(monkeypatch, tmp_path):
    rows = {"blockdevices": [{"name": "sdb", "uuid": "4A2B-11CC", "label": "ANA", "fstype": "exfat", "size": 5,
                              "mountpoint": str(tmp_path), "rm": True, "tran": "usb"}]}
    monkeypatch.setattr(storage.shutil, "which", lambda name: "/usr/bin/lsblk")

    class Done:
        stdout = json.dumps(rows)
    drives = storage.discover(run=lambda *a, **k: Done())
    assert drives[0]["id"] == "4A2B-11CC" and drives[0]["space"]["total"] > 0 and drives[0]["workspace"] is None


def test_without_lsblk_the_identifier_is_marked_not_stable(monkeypatch):
    monkeypatch.setattr(storage.shutil, "which", lambda name: None)
    drives = storage.discover()
    assert drives and all(d["id_stable"] is False for d in drives)


def test_the_station_starts_without_the_desktop_toolkit():
    # A Raspberry Pi station has no Qt: importing the station and everything it uses must not pull it in.
    code = ("import sys; sys.modules['PyQt6'] = None\n"
            "import cursiv_engine.station.server, cursiv_engine.station.storage, cursiv_engine.station.__main__\n"
            "from cursiv_engine.core import fieldlog, fieldsync, vault, vault_migration, data_lease, netgate\n"
            "from cursiv_engine.guardian import access_gate\n"
            "print('ok')")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       cwd=Path(__file__).resolve().parents[1], timeout=120)
    assert r.returncode == 0 and r.stdout.strip() == "ok", r.stderr[-2000:]

"""Photos in the field notebook: stored by SHA-256, EXIF time and GPS kept, exported (signed)
and carried by team sharing, each checked against its fingerprint."""
import hashlib
import json
from contextlib import contextmanager

import pytest
from PIL import Image

from cursiv_engine.core import devicekey, fieldlog, fieldsync
from test_netgate import fresh  # noqa: F401  (fixture)


def _photo(path, color=(10, 120, 200), gps=True):
    img = Image.new("RGB", (40, 30), color)
    ex = Image.Exif()
    if gps:
        ex[0x8825] = {1: "N", 2: (44.0, 7.0, 24.4), 3: "W", 4: (71.0, 34.0, 4.1)}
        ex[0x8769] = {36867: "2026:10:18 14:31:05"}
    img.save(path, exif=ex)
    return path


@pytest.fixture
def log(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "fieldlog")
    return fieldlog


def test_a_photo_is_stored_by_fingerprint_with_its_time_and_place(log, tmp_path):
    p = _photo(tmp_path / "IMG_0042.jpg")
    e = log.add(observer="A", site="Upper Brook", photos=[p], note="riffle")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert e["photos"] == [f"photos/{digest}.jpg"] and log.photo_path(e["photos"][0]).exists()
    info = e["photo_info"][0]
    assert info["name"] == "IMG_0042.jpg" and info["taken"] == "2026:10:18 14:31:05"
    assert (info["lat"], info["lon"]) == (44.1234444, -71.5678056)
    assert log.verify() == []
    p.unlink()                                                    # the original can go; the notebook has a copy
    assert log.photo_path(e["photos"][0]).exists()
    c = log.correct(e["id"], "site name", site="Upper Brook (site A)")
    assert c["photos"] == e["photos"]                             # a correction keeps the photo


def test_only_real_photo_files(log, tmp_path):
    with pytest.raises(ValueError):
        log.add(observer="A", photos=[tmp_path / "missing.jpg"])
    (tmp_path / "notes.txt").write_text("x")
    with pytest.raises(ValueError):
        log.add(observer="A", photos=[tmp_path / "notes.txt"])
    assert log.add(observer="A", photos=[_photo(tmp_path / "a.png", gps=False)])["photos"][0].endswith(".png")


def test_exports_include_the_photos_and_sign_them(log, tmp_path):
    e = log.add(observer="A", photos=[_photo(tmp_path / "a.jpg")])
    paths = log.export(tmp_path / "exp")
    assert (tmp_path / "exp" / e["photos"][0]).exists() and "photos" in paths
    assert log.verify_export(tmp_path / "exp") == []
    (tmp_path / "exp" / e["photos"][0]).write_bytes(b"not the photo")
    assert "was changed after the export was signed" in log.verify_export(tmp_path / "exp")[0]


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


def test_team_sharing_carries_photos_and_checks_them(team, tmp_path):
    laptop, usb = team
    with laptop("B"):
        e = fieldlog.add(observer="B", photos=[_photo(tmp_path / "b.jpg", color=(200, 40, 40))])
        out = fieldsync.share(usb)
    assert (out / e["photos"][0]).exists()
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 1} and not r["photos_missing"]
        assert fieldlog.photo_path(e["photos"][0]).exists()
    # a second laptop's share whose photo was swapped for another file
    with laptop("C"):
        e2 = fieldlog.add(observer="C", photos=[_photo(tmp_path / "c.jpg", color=(0, 200, 0))])
        out = fieldsync.share(usb)
    (out / e2["photos"][0]).write_bytes(b"something else")
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopC": 1} and r["photos_missing"] == {"laptopC": 1}
        assert not fieldlog.photo_path(e2["photos"][0]).exists()
        assert "photo(s) missing, over 50 MB, or not matching" in fieldsync.report_text(r)


# ── the paperclip: asking the image model about a photo ─────────────────────

def test_photo_is_read_locally_and_never_sent_online_when_blocked(tmp_path, monkeypatch, fresh):
    import chat_commands as cc
    from cursiv_engine.core import netgate
    p = _photo(tmp_path / "plot 4.jpg")
    asked = []

    class _Resp:
        def __init__(self, text): self._t = text
        def read(self): return json.dumps({"response": self._t}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=0):
        asked.append(getattr(req, "full_url", req))
        return _Resp("Green moss on wet rocks beside shallow water.")
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(cc, "_ollama_vision_model", lambda: "gemma3:4b")
    netgate.set_offline(True)
    r = cc.handle_command(f'photo "{p}" what is growing here?', {"gemini_key": "AIza-test"}, [])
    assert "Green moss" in r.text and "read by gemma3:4b on this computer" in r.text
    assert all("127.0.0.1" in u for u in asked)                     # only the local engine

    monkeypatch.setattr(cc, "_ollama_vision_model", lambda: "")      # no local image model
    asked.clear()
    r = cc.handle_command(f'photo "{p}"', {"gemini_key": "AIza-test", "openai_key": "sk-test"}, [])
    assert "won't send the photo anywhere" in r.text and asked == []


def test_photo_command_needs_a_photo_file(tmp_path):
    import chat_commands as cc
    assert "No photo at" in cc.handle_command(f'photo "{tmp_path / "nope.jpg"}"', {}, []).text
    assert cc.handle_command("photo of my dog is cute", {}, []) is None        # ordinary chat

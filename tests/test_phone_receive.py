"""Receiving a phone's file over the local Wi-Fi (core/phone_receive.py): the code, who may send,
size limits, the lockout, and that what arrives goes through the same import checks."""
import http.client
import json
import time

import pytest

from cursiv_v215.core import devicekey, fieldlog, fieldsync, phone_receive


@pytest.fixture
def laptop(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "laptop" / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptopA")
    monkeypatch.setattr(devicekey, "key_file", lambda: tmp_path / "laptop" / "device_key.json")
    devicekey._cache.clear()
    return tmp_path


@pytest.fixture
def receiver(laptop):
    events = []
    r = phone_receive.Receiver(report=events.append, port=0)
    r.start()
    r.events = events
    yield r
    r.stop()


def _put(r, body: bytes, code: str, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", r.port, timeout=10)
    h = {"X-Cursiv-Code": code, "X-File-Name": "send.cursivsync", "Content-Length": str(len(body))}
    h.update(headers or {})
    c.request("PUT", "/upload", body=body, headers=h)
    resp = c.getresponse()
    return resp.status, json.loads(resp.read())


def test_the_page_is_served_and_says_nothing_goes_online(receiver):
    c = http.client.HTTPConnection("127.0.0.1", receiver.port, timeout=10)
    c.request("GET", "/")
    resp = c.getresponse()
    page = resp.read().decode()
    assert resp.status == 200 and "Nothing goes to the internet" in page
    assert f"const MAX_BYTES = {phone_receive.MAX_BYTES};" in page and "__MAX_BYTES__" not in page
    assert "default-src 'none'" in resp.getheader("Content-Security-Policy")


def test_a_wrong_code_is_refused_and_five_stop_it(receiver):
    wrong = "000000" if receiver.code != "000000" else "111111"
    for _ in range(phone_receive.WRONG_CODES - 1):
        assert _put(receiver, b"x", wrong)[0] == 403
    assert receiver.running
    _put(receiver, b"x", wrong)
    assert not receiver.running and "wrong codes" in receiver.events[-1]


def test_a_phone_file_sent_with_the_code_is_imported_with_the_usual_checks(receiver, laptop, monkeypatch):
    seen = {}

    def fake_import(path):
        seen["data"] = path.read_bytes()
        return {"added": {"phone-abcdefabcdef": 3}, "unchanged": [], "conflicts": [], "rejected": [],
                "signed": ["phone-abcdefabcdef"], "photos_missing": [], "photos_added": 0}
    monkeypatch.setattr(fieldsync, "import_phone_bundle", fake_import)
    monkeypatch.setattr(fieldsync, "report_text", lambda r: "- phone-abcdefabcdef: 3 new entries")
    status, j = _put(receiver, b"PK pretend zip", receiver.code)
    assert status == 200 and j["ok"] and "3 new entries" in j["message"]
    assert seen["data"] == b"PK pretend zip"
    assert list(phone_receive.received_dir().iterdir())          # a copy of what arrived is kept
    assert receiver.events[-1].startswith("Received send.cursivsync")


def test_something_that_isnt_a_phone_file_is_reported_not_imported(receiver):
    status, j = _put(receiver, b"{}", receiver.code)
    assert status == 200 and not j["ok"] and "NOT IMPORTED" in j["message"]


def test_too_big_or_empty_is_refused_before_reading(receiver, monkeypatch):
    monkeypatch.setattr(phone_receive, "MAX_BYTES", 10)
    assert _put(receiver, b"x" * 11, receiver.code)[0] == 413
    assert _put(receiver, b"", receiver.code)[0] == 413


def test_only_private_network_addresses_may_send():
    for ip in ("192.168.1.20", "10.0.0.5", "172.20.10.2", "127.0.0.1", "::1", "::ffff:192.168.0.9"):
        assert phone_receive._private(ip), ip
    for ip in ("8.8.8.8", "1.1.1.1", "2001:4860:4860::8888", "not an ip"):
        assert not phone_receive._private(ip), ip


def test_it_stops_by_itself_when_nothing_arrives(laptop):
    r = phone_receive.Receiver(port=0, idle_minutes=1 / 60)
    r.start()
    time.sleep(2.5)
    assert not r.running and "nothing received" in r.stopped_because

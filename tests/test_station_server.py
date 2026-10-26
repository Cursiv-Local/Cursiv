"""The Field Station server and API (cursiv_engine/station/server.py), run for real on this computer's
loopback with real accounts, real encryption and a real field notebook in temporary folders. Phones on a
real Pi's Wi-Fi are not tested here (docs/FIELD-STATION-PLAN.md: awaiting hardware validation)."""
import http.client
import json
import threading

import pytest

from cursiv_engine.station import server as srv, simulation


class Client:
    def __init__(self, port: int):
        self.port, self.cookie, self.csrf = port, "", ""

    def call(self, method, path, body=None, *, host=None, origin=None, csrf=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        headers = {"Host": host or f"127.0.0.1:{self.port}"}
        if self.cookie:
            headers["Cookie"] = self.cookie
        if csrf and self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        if origin:
            headers["Origin"] = origin
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=headers)
        r = c.getresponse()
        raw = r.read()
        set_cookie = r.getheader("Set-Cookie") or ""
        if set_cookie.startswith(srv.COOKIE + "="):
            self.cookie = set_cookie.split(";")[0]
        c.close()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = raw.decode("utf-8", "replace")
        if isinstance(payload, dict) and payload.get("csrf"):
            self.csrf = payload["csrf"]
        return r.status, payload, r


@pytest.fixture
def station(tmp_path, monkeypatch):
    from cursiv_engine.core import fieldlog, vault
    from cursiv_engine.guardian import access_gate as ag
    rt = tmp_path / "runtime"
    monkeypatch.setattr(ag, "_RUNTIME", rt)
    for name in ("_HASH_FILE", "_META_FILE", "_FLAG_FILE", "_ACCOUNTS_FILE"):
        monkeypatch.setattr(ag, name, rt / getattr(ag, name).name)
    data = (tmp_path / "home" / ".cursiv").absolute()
    data.mkdir(parents=True)
    monkeypatch.setattr(vault, "roots", lambda: [data])
    monkeypatch.setattr(fieldlog, "log_dir", lambda: data / "fieldlog")
    monkeypatch.setattr(srv, "_model_status", lambda: {"running": False, "models": []})
    vault.lock()
    simulation.activate(None)
    st = srv.Station(data_paths={"internal": data}, exports=data / "exports")
    httpd = srv.serve(st, "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield st, Client(httpd.server_address[1]), data
    httpd.shutdown()
    httpd.server_close()
    vault.lock()
    simulation.activate(None)


def _setup_and_sign_in(st, c):
    assert c.call("POST", "/api/setup", {"code": st.gate.setup_code, "username": "lead", "password": "password1",
                                         "passphrase": "a long passphrase"})[0] == 200
    status, body, _ = c.call("POST", "/api/login", {"username": "lead", "password": "password1"})
    assert status == 200 and body["signed_in"] and body["csrf"]


def test_only_loopback_and_private_networks_are_answered():
    for ip in ("127.0.0.1", "192.168.4.20", "10.42.0.7", "172.16.5.5", "::1", "fd00::5", "::ffff:192.168.1.9"):
        assert srv.local_client(ip), ip
    for ip in ("8.8.8.8", "169.254.10.10", "2001:4860::8888", "::ffff:8.8.8.8", "0.0.0.0", "not an ip"):
        assert not srv.local_client(ip), ip


def test_a_foreign_host_name_is_refused(station):
    _, c, _ = station
    status, body, _ = c.call("GET", "/api/session", host="evil.example")
    assert status == 421


def test_nothing_without_signing_in(station):
    _, c, _ = station
    assert c.call("GET", "/healthz")[1] == {"ok": True, "state": "running"}       # no data in it
    for path in ("/api/health", "/api/status", "/api/notebook", "/api/workspaces"):
        assert c.call("GET", path)[0] == 401, path
    assert c.call("POST", "/api/notebook", {"note": "x"})[0] == 401
    status, body, _ = c.call("GET", "/api/session")
    assert body["signed_in"] is False and body["needs_setup"] is True and "not encrypted" in body["transport"]


def test_security_headers_and_cookie_flags(station):
    st, c, _ = station
    assert c.call("POST", "/api/setup", {"code": st.gate.setup_code, "username": "lead", "password": "password1",
                                         "passphrase": "a long passphrase"})[0] == 200
    status, _, r = c.call("POST", "/api/login", {"username": "lead", "password": "password1"})
    cookie = r.getheader("Set-Cookie")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert r.getheader("X-Frame-Options") == "DENY" and "frame-ancestors 'none'" in r.getheader("Content-Security-Policy")
    assert r.getheader("Cache-Control") == "no-store"


def test_record_list_correct_and_verify_through_the_api(station):
    st, c, _ = station
    _setup_and_sign_in(st, c)
    status, body, _ = c.call("POST", "/api/notebook", {"site": "Willow Creek WC-1", "sample_id": "WC-01",
                                                       "measurements": [{"name": "pH", "value": "7.2"}], "note": "riffle"})
    assert status == 200 and body["entry"]["observer"] == "lead" and body["entry"]["seq"] == 1
    first = body["entry"]["id"]
    status, body, _ = c.call("POST", "/api/notebook/correct", {"entry_id": first, "reason": "meter recalibrated",
                                                               "measurements": [{"name": "pH", "value": "7.4"}]})
    assert status == 200 and body["entry"]["corrects"] == first
    status, body, _ = c.call("GET", "/api/notebook?q=willow")
    assert body["total"] == 2 and [e["seq"] for e in body["entries"]] == [2, 1]   # the original is still there
    status, body, _ = c.call("GET", "/api/notebook/verify")
    assert body["intact"] and body["entries"] == 2 and "doesn't show who" in body["check_means"]


def test_changes_need_the_csrf_token_and_a_matching_origin(station):
    st, c, _ = station
    _setup_and_sign_in(st, c)
    assert c.call("POST", "/api/notebook", {"note": "x"}, csrf=False)[0] == 403
    assert c.call("POST", "/api/notebook", {"note": "x"}, origin="http://evil.example")[0] == 403
    assert c.call("POST", "/api/notebook", {"note": "x"}, origin=f"http://127.0.0.1:{c.port}")[0] == 200


def test_after_a_reboot_only_telemetry_until_the_passphrase(station):
    from cursiv_engine.core import vault
    st, c, _ = station
    _setup_and_sign_in(st, c)
    c.call("POST", "/api/notebook", {"note": "before the reboot"})
    vault.lock()
    assert c.call("GET", "/api/notebook")[0] == 423
    assert c.call("POST", "/api/notebook", {"note": "x"})[0] == 423
    assert c.call("GET", "/api/health")[0] == 200                                   # telemetry still works
    assert c.call("POST", "/api/unlock", {"passphrase": "wrong one"})[0] == 403
    status, body, _ = c.call("POST", "/api/unlock", {"passphrase": "a long passphrase"})
    assert status == 200 and body["unlocked"]
    assert c.call("GET", "/api/notebook")[1]["total"] == 1


def test_concurrent_writes_stay_one_unbroken_chain(station):
    st, c, _ = station
    _setup_and_sign_in(st, c)
    results = []

    def write(i):
        results.append(c.call("POST", "/api/notebook", {"note": f"concurrent {i}", "sample_id": f"S-{i:03d}"})[0])
    threads = [threading.Thread(target=write, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(200) == 20
    body = c.call("GET", "/api/notebook/verify")[1]
    assert body["entries"] == 20 and body["intact"]
    seqs = [e["seq"] for e in c.call("GET", "/api/notebook?limit=50")[1]["entries"]]
    assert sorted(seqs) == list(range(1, 21))


def test_safe_shutdown_stops_writes_and_never_powers_off_unless_configured(station):
    st, c, _ = station
    _setup_and_sign_in(st, c)
    assert c.call("POST", "/api/shutdown", {})[0] == 400                            # needs confirm
    status, body, _ = c.call("POST", "/api/shutdown", {"confirm": True})
    assert status == 200 and body == {"state": "stopped", "writes_unfinished": 0, "os_shutdown": "not configured"}
    assert c.call("GET", "/healthz")[1]["ok"] is False
    assert c.call("POST", "/api/login", {"username": "lead", "password": "password1"})[0] == 503


def test_shutdown_waits_for_a_write_then_runs_the_configured_command():
    calls = []
    st = srv.Station(shutdown_command=["sudo", "-n", "/usr/bin/systemctl", "poweroff"])
    assert st.begin_write()
    done = {}
    t = threading.Thread(target=lambda: done.update(st.shut_down(run=lambda cmd, check: calls.append(cmd))))
    t.start()
    t.join(0.5)
    assert t.is_alive() and st.state == "draining" and not st.begin_write()      # waiting; no new writes
    st.end_write()
    t.join(5)
    assert done["os_shutdown"] == "requested" and calls == [["sudo", "-n", "/usr/bin/systemctl", "poweroff"]]


def test_storage_gone_mid_operation_is_a_clear_error_and_nothing_half_written(station, monkeypatch, tmp_path):
    from cursiv_engine.core import fieldlog
    st, c, data = station
    _setup_and_sign_in(st, c)
    assert c.call("POST", "/api/notebook", {"note": "before"})[0] == 200
    real_append = fieldlog._append

    def pulled(**fields):
        raise OSError(5, "Input/output error")                                     # the SSD went away
    monkeypatch.setattr(fieldlog, "_append", pulled)
    status, body, _ = c.call("POST", "/api/notebook", {"note": "during"})
    assert status == 503 and "storage isn't available" in body["error"]
    monkeypatch.setattr(fieldlog, "_append", real_append)
    body = c.call("GET", "/api/notebook/verify")[1]
    assert body["intact"] and body["entries"] == 1


def test_health_says_when_it_is_simulated(station):
    st, c, _ = station
    _setup_and_sign_in(st, c)
    assert c.call("GET", "/api/health")[1]["simulated"] is False
    simulation.activate("B")
    body = c.call("GET", "/api/health")[1]
    assert body["simulated"] is True and body["thermal_status"] == "critical"
    assert c.call("GET", "/api/session")[1]["simulated"] == "B"


def test_workspaces_lists_notebooks_and_drives(station):
    st, c, _ = station
    _setup_and_sign_in(st, c)
    c.call("POST", "/api/notebook", {"note": "x"})
    body = c.call("GET", "/api/workspaces")[1]
    assert body["notebooks"][0]["own"] is True and isinstance(body["drives"], list)


def test_setup_names_the_stations_notebook_and_head_healthz_works(station):
    from cursiv_engine.core import fieldlog
    st, c, _ = station
    assert c.call("POST", "/api/setup", {"code": st.gate.setup_code, "username": "lead", "password": "password1",
                                         "passphrase": "a long passphrase", "station_name": "Base camp"})[0] == 200
    assert fieldlog.identity()["name"] == "Base camp"
    assert c.call("HEAD", "/healthz")[0] == 200 and c.call("HEAD", "/api/session")[0] == 405


def test_the_interface_is_served_safely(station):
    _, c, _ = station
    status, page, r = c.call("GET", "/")
    assert status == 200 and "Cursiv Field Station" in page and "script-src 'self'" in r.getheader("Content-Security-Policy")
    assert c.call("GET", "/static/app.js")[0] == 200 and c.call("GET", "/static/app.css")[0] == 200
    for path in ("/static/../server.py", "/static/..%2Fserver.py", "/static/server.py", "/static/APP.JS", "/etc/passwd"):
        assert c.call("GET", path)[0] == 404, path
    js = (srv.WEB / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "eval(" not in js                     # station data is only ever text
    html = (srv.WEB / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in html and " style=" not in html and " on" + "click=" not in html   # the CSP allows no inline code

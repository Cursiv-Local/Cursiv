"""
The Field Station's local web server and API (docs/FIELD-STATION-PLAN.md, phase 3). Standard library only,
following core/phone_receive.py: one process, threads per request, the field notebook's own lock
serializing writes.

Who gets an answer at all
- Only clients on this computer (loopback) or a private network (the station's own Wi-Fi). Anything else
  gets nothing. This is the inbound rule; netgate still blocks every outgoing connection while offline.
- The Host header must name this station (localhost, cursiv.local, one of its addresses), which stops a
  web page elsewhere from reaching it through a renamed DNS entry.
- Every request that changes something needs the session's CSRF token, and its Origin (if sent) must be
  this station.

Plain HTTP: traffic on the station's Wi-Fi isn't encrypted by HTTP itself; the Wi-Fi's WPA password is what
protects it (owner's choice for the preview, said in the interface).
"""
from __future__ import annotations

import ipaddress
import json
import mimetypes
import re
import threading
import time
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cursiv_engine.station import sessions as ss, telemetry

WEB = Path(__file__).with_name("web")
COOKIE = "cursiv_station"
MAX_BODY = 1 << 20
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                                "connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"),
}


def local_client(ip: str) -> bool:
    """Loopback or a private network (RFC 1918, IPv6 unique-local). The inbound rule."""
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return a.is_loopback or (a.is_private and not a.is_link_local and not a.is_unspecified)


class Station:
    """State shared by every request: sessions, the sign-in gate, the shutdown state, settings."""

    def __init__(self, *, hosts: set[str] | None = None, data_paths: dict | None = None,
                 shutdown_command: list[str] | None = None, exports: Path | None = None):
        self.sessions = ss.Sessions()
        self.gate = ss.Gate()
        self.hosts = {h.lower() for h in (hosts or set())} | {"localhost", "127.0.0.1", "[::1]", "cursiv.local"}
        self.data_paths = data_paths or {}
        self.shutdown_command = shutdown_command          # None in development: never shuts the computer down
        self.exports = exports
        self.state = "running"                             # running -> draining -> stopped
        self._writes = 0
        self._cv = threading.Condition()

    # writes and safe shutdown
    def begin_write(self) -> bool:
        with self._cv:
            if self.state != "running":
                return False
            self._writes += 1
            return True

    def end_write(self) -> None:
        with self._cv:
            self._writes -= 1
            self._cv.notify_all()

    def shut_down(self, run=None, wait_s: float = 30.0) -> dict:
        """1 stop new writes, 2 let running ones finish, 3 flush (notebook writes are already synced to disk
        before they return), 4 end sessions and lock the encrypted data, 5 ask the OS to shut down, if
        configured. A sudden power cut can still lose the entry being written; this avoids causing one."""
        import subprocess
        from cursiv_engine.core import fieldlog, vault
        with self._cv:
            if self.state == "running":
                self.state = "draining"
            deadline = time.monotonic() + wait_s
            while self._writes and time.monotonic() < deadline:
                self._cv.wait(timeout=0.2)
            unfinished = self._writes
        with fieldlog._lock:                                # no notebook write is half-way through
            pass
        self.sessions.end_all()
        vault.lock()
        self.state = "stopped"
        result = {"state": self.state, "writes_unfinished": unfinished, "os_shutdown": "not configured"}
        if self.shutdown_command:
            (run or subprocess.run)(self.shutdown_command, check=False)
            result["os_shutdown"] = "requested"
        return result


# ── helpers ──────────────────────────────────────────────────────────────────

def _entry_view(e: dict, names: dict) -> dict:
    from cursiv_engine.core import fieldlog
    return {"id": e["id"], "seq": e["seq"], "recorded_local": e["recorded_local"], "observer": e["observer"],
            "site": e["site"], "sample_id": e.get("sample_id", ""), "project": e.get("project", ""),
            "measurements": e["measurements"], "note": e["note"], "photos": len(e.get("photos") or []),
            "lat": e["lat"], "lon": e["lon"], "corrects": e.get("corrects"), "reason": e.get("reason", ""),
            "hash": e["hash"][:12], "notebook": fieldlog.who(e.get("device", ""), names)}


def _model_status() -> dict:
    """Is the local AI engine running, and which models does it have? Loopback only, short timeout."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.5) as r:
            models = [m.get("name", "") for m in json.loads(r.read().decode("utf-8")).get("models", [])]
        return {"running": True, "models": models}
    except Exception as exc:  # not installed or not running: research tools still work
        return {"running": False, "models": [], "note": f"local AI engine not reachable ({type(exc).__name__})"}


def notebook_summary() -> dict:
    from cursiv_engine.core import fieldlog
    rows = fieldlog.entries()
    problems = fieldlog.verify()
    return {"entries": len(rows), "last": rows[-1]["recorded_local"] if rows else None,
            "intact": not problems, "problems": problems[:5], "check_means": fieldlog.CHECK_MEANS,
            "name": fieldlog.identity().get("name", "")}


# ── the request handler ──────────────────────────────────────────────────────

def make_handler(station: Station):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CursivFieldStation"
        sys_version = ""

        def log_message(self, fmt, *args):            # structured, no request bodies or cookies
            print(json.dumps({"t": round(time.time(), 1), "client": self.client_address[0],
                              "request": (fmt % args)[:200]}), flush=True)

        # gatekeeping
        def _allowed(self) -> bool:
            if not local_client(self.client_address[0]):
                self.close_connection = True
                return False
            host = (self.headers.get("Host") or "").lower()
            name = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
            if name not in station.hosts:
                self._json(421, {"error": "this address isn't the Field Station's"})
                return False
            return True

        def _session(self) -> dict | None:
            c = SimpleCookie(self.headers.get("Cookie") or "")
            return station.sessions.get(c[COOKIE].value if COOKIE in c else None)

        def _origin_ok(self) -> bool:
            origin = self.headers.get("Origin")
            return origin is None or origin.lower() == f"http://{(self.headers.get('Host') or '').lower()}"

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("request too large")
            data = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
            self.send_response(code)
            for k, v in {**SECURITY_HEADERS, **(extra or {})}.items():
                self.send_header(k, v)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj, extra: dict | None = None) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8",
                       {"Cache-Control": "no-store", **(extra or {})})

        # GET
        def do_GET(self):
            if not self._allowed():
                return
            url = urlparse(self.path)
            if url.path == "/healthz":                      # for systemd and monitors: no data
                return self._json(200, {"ok": station.state == "running", "state": station.state})
            if url.path in ("/", "/index.html") or url.path.startswith("/static/"):
                return self._static(url.path)
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "not found"})
            s = self._session()
            if url.path == "/api/session":
                return self._json(200, self._session_view(s))
            if s is None:
                return self._json(401, {"error": "sign in first"})
            if url.path == "/api/health":
                return self._json(200, telemetry.snapshot(station.data_paths))
            if url.path == "/api/status":
                return self._json(200, self._status())
            if not self._unlocked():
                return self._json(423, {"error": "the notebook is locked; enter the encryption passphrase"})
            from cursiv_engine.core import fieldlog
            if url.path == "/api/notebook":
                q = parse_qs(url.query)
                words = (q.get("q", [""])[0]).casefold().split()
                limit = max(1, min(int(q.get("limit", ["50"])[0] or 50), 500))
                rows = list(reversed(fieldlog.entries()))
                if words:
                    rows = [e for e in rows if all(w in fieldlog.summary(e).casefold() for w in words)]
                names = fieldlog.notebook_names()
                return self._json(200, {"total": len(rows), "entries": [_entry_view(e, names) for e in rows[:limit]]})
            if url.path == "/api/notebook/verify":
                return self._json(200, notebook_summary())
            if url.path == "/api/workspaces":
                from cursiv_engine.core import fieldsync
                from cursiv_engine.station import storage
                return self._json(200, {"notebooks": fieldsync.notebooks_here(), "drives": storage.discover()})
            return self._json(404, {"error": "not found"})

        # POST
        def do_POST(self):
            if not self._allowed():
                return
            url = urlparse(self.path)
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "not found"})
            if not self._origin_ok():
                return self._json(403, {"error": "request from another site refused"})
            try:
                body = self._body()
            except (ValueError, json.JSONDecodeError) as exc:
                return self._json(400, {"error": str(exc)})
            client = self.client_address[0]
            try:
                if url.path == "/api/setup":
                    station.gate.first_setup(body.get("code", ""), body.get("username", ""), body.get("password", ""),
                                             body.get("passphrase", ""), client)
                    return self._json(200, {"ok": True})
                if url.path == "/api/login":
                    if station.state != "running":
                        return self._json(503, {"error": "the station is shutting down"})
                    if not station.gate.sign_in(body.get("username", ""), body.get("password", ""), client):
                        return self._json(401, {"error": "that username or password isn't right"})
                    s = station.sessions.new(body["username"], client)
                    cookie = f"{COOKIE}={s['token']}; HttpOnly; SameSite=Strict; Path=/; Max-Age={ss.ABSOLUTE_S}"
                    return self._json(200, self._session_view(s), {"Set-Cookie": cookie})
            except ss.TooMany as exc:
                return self._json(429, {"error": str(exc), "wait": exc.wait}, {"Retry-After": str(exc.wait)})
            except PermissionError as exc:
                return self._json(403, {"error": str(exc)})
            except ValueError as exc:
                return self._json(400, {"error": str(exc)})
            s = self._session()
            if s is None:
                return self._json(401, {"error": "sign in first"})
            if not station.sessions.csrf_ok(s, self.headers.get("X-CSRF-Token")):
                return self._json(403, {"error": "missing or wrong CSRF token"})
            if url.path == "/api/logout":
                station.sessions.end(s["token"])
                return self._json(200, {"ok": True}, {"Set-Cookie": f"{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"})
            if url.path == "/api/unlock":
                from cursiv_engine.core import vault
                try:
                    adopted = station.gate.unlock(body.get("passphrase", ""), s["user"], client)
                except ss.TooMany as exc:
                    return self._json(429, {"error": str(exc), "wait": exc.wait})
                except vault.VaultError:
                    return self._json(403, {"error": "that passphrase didn't unlock the data"})
                return self._json(200, {"ok": True, "adopted": adopted, **station.gate.encryption()})
            if url.path == "/api/shutdown":
                if body.get("confirm") is not True:
                    return self._json(400, {"error": "send confirm: true to shut down"})
                return self._json(200, station.shut_down())
            if not self._unlocked():
                return self._json(423, {"error": "the notebook is locked; enter the encryption passphrase"})
            if url.path in ("/api/notebook", "/api/notebook/correct", "/api/export"):
                if not station.begin_write():
                    return self._json(503, {"error": "the station is shutting down; nothing was saved"})
                try:
                    return self._write(url.path, body, s)
                finally:
                    station.end_write()
            return self._json(404, {"error": "not found"})

        def _write(self, path: str, body: dict, s: dict):
            from cursiv_engine.core import fieldlog
            fields = {k: body[k] for k in ("observer", "site", "sample_id", "project", "note", "measurements",
                                           "lat", "lon", "location_source") if k in body and body[k] not in ("", None)}
            fields.setdefault("observer", s["user"])
            try:
                if path == "/api/notebook":
                    e = fieldlog.add(**fields)
                elif path == "/api/notebook/correct":
                    e = fieldlog.correct(str(body.get("entry_id", "")), str(body.get("reason", "")),
                                         **{k: v for k, v in fields.items() if k != "observer"})
                else:
                    from cursiv_engine.core import fieldsync
                    out = fieldsync.team_export((station.exports / time.strftime("team_%Y-%m-%d_%H%M%S"))
                                                if station.exports else None)
                    return self._json(200, {"files": {k: Path(v).name for k, v in out.items()}})
            except (ValueError, TypeError) as exc:
                return self._json(400, {"error": f"not saved: {exc}"})
            except OSError as exc:                          # storage gone (scenario D) or full: say so, nothing half-written
                return self._json(503, {"error": f"not saved: the notebook's storage isn't available ({exc.strerror or exc})"})
            return self._json(200, {"entry": _entry_view(e, fieldlog.notebook_names())})

        # views
        def _unlocked(self) -> bool:
            enc = station.gate.encryption()
            return enc["unlocked"] or not enc["encrypted"]

        def _session_view(self, s) -> dict:
            from cursiv_engine.core import selfknow
            from cursiv_engine.station import simulation
            return {"signed_in": s is not None, "user": s["user"] if s else None, "csrf": s["csrf"] if s else None,
                    "needs_setup": station.gate.needs_setup(), "encryption": station.gate.encryption(),
                    "simulated": simulation.active(), "version": selfknow.VERSION, "state": station.state,
                    "transport": "HTTP on the station's Wi-Fi: protected by the Wi-Fi password, not encrypted by the web page itself"}

        def _status(self) -> dict:
            from cursiv_engine.core import netgate
            out = {"encryption": station.gate.encryption(), "model": _model_status(),
                   "offline": netgate.is_offline(), "state": station.state}
            if self._unlocked():
                try:
                    out["notebook"] = notebook_summary()
                except OSError as exc:
                    out["notebook"] = {"error": f"the notebook's storage isn't available ({exc.strerror or exc})"}
            return out

        def _static(self, path: str):
            name = "index.html" if path in ("/", "/index.html") else path[len("/static/"):]
            if not re.fullmatch(r"[a-z0-9_-]+\.(html|css|js|svg|png|webmanifest)", name):
                return self._json(404, {"error": "not found"})
            f = WEB / name
            if not f.is_file():
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
            self._send(200, f.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""),
                       {"Cache-Control": "no-cache"})

    return Handler


def serve(station: Station, host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), make_handler(station))
    httpd.daemon_threads = True
    return httpd

"""
Receive a phone notebook file over the local Wi-Fi, with no internet and no cable.

The laptop opens a small web page on the local network only while the "Receive from a phone"
window is open. The phone saves its .cursivsync file as usual, opens the address the window
shows (http://192.168.x.x:8765) in its browser, types the 6-digit code, and picks the file.
Cursiv imports it with the same checks as a file from a USB stick (fieldsync.import_phone_bundle).

Who can send: only devices on a private network (192.168.x.x, 10.x.x.x, 172.16-31.x.x, or this
laptop), and only with the code. Five wrong codes stop it. It stops by itself after 15 minutes
with nothing received, and when the window closes. Nothing is ever sent out: it only answers.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import re
import secrets
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cursiv_v215.core import fieldlog, fieldsync

PORT = 8765
MAX_BYTES = 2 << 30            # one send file
IDLE_MINUTES = 15
WRONG_CODES = 5


def lan_addresses() -> list[str]:
    """This laptop's private IPv4 addresses (Wi-Fi, Ethernet, a phone's hotspot)."""
    found = []
    try:
        import psutil
        for addrs in psutil.net_if_addrs().values():
            for a in addrs:
                if (getattr(a.family, "name", "") == "AF_INET" and _private(a.address)
                        and not a.address.startswith(("127.", "169.254."))):   # not loopback or link-local
                    found.append(a.address)
    except Exception:
        pass
    # Wi-Fi and Ethernet first (192.168 / 10.), virtual adapters (172.x for WSL, Docker, Hyper-V) last
    return sorted(set(found), key=lambda ip: (ip.startswith("172."), ip))


def _private(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
        a = a.ipv4_mapped
    return a.is_private or a.is_loopback


def received_dir() -> Path:
    return fieldlog.log_dir() / "received"


class Receiver:
    """Start with .start(); report(text) is called (from a background thread) for each event."""

    def __init__(self, report=None, port: int = PORT, idle_minutes: float = IDLE_MINUTES):
        self.code = f"{secrets.randbelow(10**6):06d}"
        self.report = report or (lambda text: None)
        self.idle_seconds = idle_minutes * 60
        self.wrong = 0
        self.received = 0
        self.imported = 0  # entries confirmed by the importer; uploads counted separately
        self.last_activity = time.monotonic()
        self._lock = threading.Lock()                # one import at a time
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self.stopped_because = ""

    # ── lifecycle ──
    def start(self) -> int:
        handler = type("Handler", (_Handler,), {"receiver": self})
        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", self._port), handler)
        except OSError:
            self._server = ThreadingHTTPServer(("0.0.0.0", 0), handler)      # 8765 taken: any free port
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        threading.Thread(target=self._watch_idle, daemon=True).start()
        return self.port

    @property
    def port(self) -> int:
        return self._server.server_address[1] if self._server else 0

    @property
    def running(self) -> bool:
        return self._server is not None

    def stop(self, why: str = "") -> None:
        server, self._server = self._server, None
        if server:
            self.stopped_because = why
            threading.Thread(target=lambda: (server.shutdown(), server.server_close()), daemon=True).start()
            if why:
                self.report(f"Stopped: {why}")

    def _watch_idle(self) -> None:
        while self._server:
            time.sleep(1)
            if time.monotonic() - self.last_activity > self.idle_seconds:
                self.stop(f"nothing received for {int(self.idle_seconds // 60)} minutes")

    # ── what the handler calls ──
    def check_code(self, given: str) -> bool:
        if hmac.compare_digest(given.encode(), self.code.encode()):
            return True
        self.wrong += 1
        if self.wrong >= WRONG_CODES:
            self.stop(f"{WRONG_CODES} wrong codes were tried")
        return False

    def receive(self, name: str, read, length: int) -> str:
        """Save the upload into the field log's received folder, then import it. Returns the report."""
        self.last_activity = time.monotonic()
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)[:80] or "phone.cursivsync"
        folder = received_dir()
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe}"
        with self._lock:
            got = 0
            with dest.open("wb") as out:
                while got < length:
                    chunk = read(min(1 << 20, length - got))
                    if not chunk:
                        break
                    out.write(chunk)
                    got += len(chunk)
            if got != length:
                dest.unlink(missing_ok=True)
                raise ValueError("the file didn't arrive whole (the connection dropped): send it again")
            try:
                result = fieldsync.import_phone_bundle(dest)
                text = fieldsync.report_text(result)
                self.imported += sum(result['added'].values())
            except (OSError, ValueError) as exc:
                text = f"NOT IMPORTED: {exc}"
        self.received += 1
        self.last_activity = time.monotonic()
        self.report(f"Received {safe} ({got / 1e6:.1f} MB):\n{text}")
        return text


class _Handler(BaseHTTPRequestHandler):
    receiver: Receiver
    server_version = "Cursiv"
    sys_version = ""

    def log_message(self, *args):                    # no console noise
        pass

    def _send(self, status: int, body: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, **fields) -> None:
        self._send(status, json.dumps(fields).encode(), "application/json")

    def _allowed(self) -> bool:
        if _private(self.client_address[0]) and self.receiver.running:
            return True
        self._json(403, ok=False, message="Only phones on the same local network can send here.")
        return False

    def _drain(self) -> None:
        """Read a small refused body, so the phone gets the answer instead of a dropped connection."""
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if 0 < n <= 1 << 20:
                self.rfile.read(n)
        except (OSError, ValueError):
            pass

    def do_GET(self):
        if not self._allowed():
            return
        if self.path.split("?")[0] in ("/", "/index.html"):
            self._send(200, PAGE.replace("__MAX_BYTES__", str(MAX_BYTES)).encode(), "text/html; charset=utf-8")
        else:
            self._json(404, ok=False, message="Not here.")

    def do_PUT(self):
        if not self._allowed():
            return
        if self.path.split("?")[0] != "/upload":
            self._json(404, ok=False, message="Not here.")
            return
        if not self.receiver.check_code(self.headers.get("X-Cursiv-Code", "").strip()):
            self._drain()
            self.close_connection = True
            self._json(403, ok=False, message="That code isn't the one on the laptop's screen.")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._json(411, ok=False, message="The file's size wasn't given: try again.")
            return
        if length <= 0 or length > MAX_BYTES:
            self._drain()                  # small: read it so the phone gets this answer (the page checks size first)
            self.close_connection = True
            self._json(413, ok=False, message="That file is empty or too big for one send.")
            return
        try:
            text = self.receiver.receive(self.headers.get("X-File-Name", "phone.cursivsync"), self.rfile.read, length)
        except (OSError, ValueError) as exc:
            self._json(400, ok=False, message=str(exc))
            return
        problem = any(w in text for w in ("CONFLICT", "NOT IMPORTED", "CHECK"))
        self._json(200, ok=not problem, message=text)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Send to Cursiv</title>
<style>
  :root { color-scheme: light dark; --bg:#f6f7f8; --fg:#16181b; --muted:#5d646d; --card:#fff; --line:#d5d9de; --accent:#1f6feb; --ok:#1a7f37; --bad:#c62828; }
  @media (prefers-color-scheme: dark) { :root { --bg:#121417; --fg:#e8eaed; --muted:#9aa2ab; --card:#1b1e22; --line:#30353b; --accent:#58a6ff; --ok:#3fb950; --bad:#ff7b72; } }
  body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width:520px; margin:0 auto; padding:20px 16px 40px; }
  h1 { font-size:1.4rem; margin:0 0 4px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; margin-top:16px; }
  label { display:block; font-weight:600; margin:12px 0 6px; }
  input { box-sizing:border-box; width:100%; font-size:1.1rem; padding:10px; border:1px solid var(--line); border-radius:8px; background:var(--bg); color:var(--fg); }
  #code { letter-spacing:.3em; font-variant-numeric:tabular-nums; }
  button { margin-top:16px; width:100%; font-size:1.1rem; padding:12px; border:0; border-radius:8px; background:var(--accent); color:#fff; }
  button:disabled { opacity:.5; }
  .muted { color:var(--muted); font-size:.92rem; }
  pre { white-space:pre-wrap; word-break:break-word; font:inherit; margin:12px 0 0; }
  .ok { color:var(--ok); } .bad { color:var(--bad); }
</style></head><body><main>
<h1>Send to Cursiv</h1>
<p class="muted">This page is on the laptop, over your local Wi-Fi. Nothing goes to the internet.</p>
<div class="card">
  <p class="muted">First, in the phone notebook, tap <b>Send to laptop</b> and save the file (on iPhone: Save to Files).</p>
  <label for="code">Code shown on the laptop</label>
  <input id="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]*">
  <label for="file">The .cursivsync file</label>
  <input id="file" type="file">
  <button id="go">Send</button>
  <pre id="out" class="muted"></pre>
</div>
</main>
<script>
const $ = id => document.getElementById(id);
const MAX_BYTES = __MAX_BYTES__;
$("go").onclick = async () => {
  const f = $("file").files[0], code = $("code").value.trim(), out = $("out");
  if (!/^[0-9]{6}$/.test(code)) { out.className = "bad"; out.textContent = "Type the 6-digit code from the laptop."; return; }
  if (!f) { out.className = "bad"; out.textContent = "Pick the .cursivsync file first."; return; }
  if (f.size > MAX_BYTES) { out.className = "bad"; out.textContent = `That file is ${(f.size / 1e9).toFixed(1)} GB, ` +
    "more than one send can take. Send to the laptop more often, or use a USB cable."; return; }
  $("go").disabled = true; out.className = "muted";
  out.textContent = `Sending ${f.name} (${(f.size / 1e6).toFixed(1)} MB)… keep this page open.`;
  try {
    const r = await fetch("/upload", { method: "PUT", body: f,
      headers: { "X-Cursiv-Code": code, "X-File-Name": f.name.replace(/[^A-Za-z0-9._-]/g, "_") } });
    const j = await r.json();
    out.className = j.ok ? "ok" : "bad";
    out.textContent = (j.ok ? "Imported.\\n" : "") + j.message;
  } catch (err) {
    out.className = "bad";
    out.textContent = "Couldn't reach the laptop: is its Receive window still open, and are you on the same Wi-Fi?";
  }
  $("go").disabled = false;
};
</script></body></html>
"""

"""
Real screenshots of the Field Station interface for the website (cursiv.us/field-station). Runs the station
with scripts/station_dev.py against a throwaway folder, sets it up and records sample entries through its own
API, then captures pages with headless Edge or Chrome (scripts/cdp_shots.mjs). Hardware readings are the
simulation scenarios, shown under the SIMULATED banner exactly as the interface shows them.

    python scripts/station_shots.py <out folder> [--browser path\\to\\msedge.exe]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PORT = 8095
BASE = f"http://127.0.0.1:{PORT}"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/usr/bin/chromium", "/usr/bin/google-chrome"]

ENTRIES = [
    dict(site="Willow Creek WC-1", sample_id="WC-1026-01", project="FALL-2026", note="riffle below the footbridge",
         measurements=[{"name": "water temp", "value": "12.4", "unit": "°C"}, {"name": "pH", "value": "7.2"},
                       {"name": "dissolved oxygen", "value": "8.6", "unit": "mg/L"}]),
    dict(site="Willow Creek WC-2", sample_id="WC-1026-02", project="FALL-2026", note="slight turbidity after rain",
         measurements=[{"name": "water temp", "value": "13.1", "unit": "°C"}, {"name": "turbidity", "value": "6.5", "unit": "NTU"}]),
    dict(site="Willow Creek WC-3", sample_id="WC-1026-03", project="FALL-2026", note="caddisfly cases on the cobbles",
         measurements=[{"name": "conductivity", "value": "312", "unit": "µS/cm"}, {"name": "pH", "value": "7.4"}]),
]


def call(method, path, body=None, cookie="", csrf=""):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "Cookie": cookie, "X-CSRF-Token": csrf})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}"), r.headers.get("Set-Cookie") or ""


def start(folder: Path, scenario: str):
    p = subprocess.Popen([sys.executable, str(REPO / "scripts" / "station_dev.py"), str(folder), "--port", str(PORT),
                          "--simulate", scenario], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=REPO)
    lines: list[str] = []
    import threading
    threading.Thread(target=lambda: [lines.append(ln) for ln in p.stdout], daemon=True).start()
    deadline = time.time() + 60
    while time.time() < deadline and not any("Cursiv Field Station on" in ln for ln in lines):
        time.sleep(0.2)
    time.sleep(1.5)                                   # the setup code, if any, is printed just after
    code = next((ln.split("setup code:")[1].split()[0] for ln in lines if "setup code:" in ln), None)
    return p, code


def sign_in():
    _, set_cookie = call("POST", "/api/login", {"username": "lead", "password": "station-shots-1"})
    cookie = set_cookie.split(";")[0]
    session, _ = call("GET", "/api/session", cookie=cookie)
    return cookie, session["csrf"]


def shoot(browser: str, cookie: str, shots: list, out: Path):
    name, value = cookie.split("=", 1)
    plan = out / "_plan.json"
    plan.write_text(json.dumps({"cookie": {"name": name, "value": value, "url": BASE}, "shots": shots}), encoding="utf-8")
    subprocess.run(["node", str(REPO / "scripts" / "cdp_shots.mjs"), browser, str(plan)], check=True, timeout=300)
    plan.unlink()


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    browser = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else next(b for b in BROWSERS if Path(b).exists())
    folder = Path(tempfile.mkdtemp(prefix="cursiv-station-shots-"))
    desk, phone = dict(width=1280, height=860), dict(width=390, height=844, mobile=True, scale=2)
    try:
        p, code = start(folder, "A")
        try:
            call("POST", "/api/setup", {"code": code, "username": "lead", "password": "station-shots-1",
                                        "passphrase": "station shots passphrase", "station_name": "Base camp"})
            cookie, csrf = sign_in()
            first = None
            for e in ENTRIES:
                body, _ = call("POST", "/api/notebook", {**e, "observer": "Ana Ruiz"}, cookie, csrf)
                first = first or body["entry"]["id"]
            call("POST", "/api/notebook/correct", {"entry_id": first, "reason": "pH meter recalibrated",
                                                   "observer": "Ana Ruiz", "measurements": [
                                                       {"name": "water temp", "value": "12.4", "unit": "°C"},
                                                       {"name": "pH", "value": "7.4"},
                                                       {"name": "dissolved oxygen", "value": "8.6", "unit": "mg/L"}]},
                 cookie, csrf)
            shoot(browser, cookie, [
                {"url": BASE + "/#dashboard", **desk, "out": str(out / "station-dashboard.png")},
                {"url": BASE + "/#notebook", **{**desk, "height": 1560}, "out": str(out / "station-notebook.png")},
                {"url": BASE + "/#health", **desk, "out": str(out / "station-health.png")},
                {"url": BASE + "/#dashboard", **phone, "out": str(out / "station-phone-dashboard.png")},
                {"url": BASE + "/#notebook", **phone, "out": str(out / "station-phone-notebook.png"), "wait": 3000},
            ], out)
        finally:
            p.terminate(); p.wait(30)
        # A restart with a plain USB-C power bank (scenario E): locked until the passphrase, no battery numbers.
        p, _ = start(folder, "E")
        try:
            cookie, csrf = sign_in()
            shoot(browser, cookie, [{"url": BASE + "/#dashboard", **phone, "out": str(out / "station-phone-unlock.png")}], out)
            call("POST", "/api/unlock", {"passphrase": "station shots passphrase"}, cookie, csrf)
            shoot(browser, cookie, [{"url": BASE + "/#health", **{**phone, "height": 2350},
                                     "out": str(out / "station-phone-health-powerbank.png"), "wait": 3000}], out)
        finally:
            p.terminate(); p.wait(30)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    print("saved in", out)


if __name__ == "__main__":
    main()

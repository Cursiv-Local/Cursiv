"""Offline, observed from outside: the real program (launcher/main.py --selftest, which loads the
chat engine, the commands, the window code, the reference, the calculator, the field notebook
with a signed export, and document search) run as its own process with a fresh, empty data
folder, while two independent observers watch:

1. attempts: a Python audit hook installed before Cursiv's own code, so it sees every
   connect / DNS lookup Python makes, including ones Cursiv's gate then refuses;
2. connections: the operating system's own table of this process's sockets (psutil),
   polled from this test process, so it sees anything that actually opened, even from
   native code that never goes through Python's socket module.

What this proves and doesn't: one build (this source tree, this Python) on the computer the
tests run on (Windows in CI and here; also macOS in CI), with offline mode on and with the
fresh-install default (offline mode off, automatic web search and update checks off). It is
not a guarantee for every platform, dependency or code path; the chat turn itself is checked
in test_netgate.py, and real cloud calls are never made in tests.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

psutil = pytest.importorskip("psutil")
REPO = Path(__file__).resolve().parent.parent

WRAPPER = r"""
import ipaddress, json, os, runpy, sys
attempts = open(sys.argv[1], "a", encoding="utf-8")
def local(h):
    if h is None: return True
    h = (h.decode() if isinstance(h, bytes) else str(h)).strip("[]").lower()
    if h in ("", "localhost", "localhost.") or h.endswith(".localhost"): return True
    try: return ipaddress.ip_address(h.split("%")[0]).is_loopback
    except ValueError: return False
def hook(ev, args):
    if ev in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        h = args[1][0] if len(args) > 1 and isinstance(args[1], tuple) and args[1] else None
    elif ev in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex", "socket.gethostbyaddr"):
        h = args[0] if args else None
    else:
        return
    if not local(h):
        attempts.write(json.dumps([ev, str(h)]) + "\n"); attempts.flush()
sys.addaudithook(hook)
root = sys.argv[2]
sys.path[:0] = [root, os.path.join(root, "launcher")]
sys.argv = ["main.py", "--selftest", sys.argv[3]]
runpy.run_path(os.path.join(root, "launcher", "main.py"), run_name="__main__")
"""


def _remote(conns) -> list[str]:
    out = []
    for c in conns:
        if c.raddr and not (c.raddr.ip.startswith("127.") or c.raddr.ip in ("::1", "0.0.0.0", "::")):
            out.append(f"{c.raddr.ip}:{c.raddr.port} {c.status}")
    return out


def _connections(proc):
    """Windows venv redirectors can run Python in a child; watch that tree too."""
    processes = [proc]
    try:
        processes += proc.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    rows = []
    for process in processes:
        try:
            rows.extend(process.net_connections(kind='inet'))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return rows


@pytest.mark.parametrize("offline", [True, False], ids=["offline mode on", "fresh-install default"])
def test_the_program_starts_and_works_with_no_connection_off_this_computer(tmp_path, offline):
    app, home = tmp_path / "app", tmp_path / "home"
    app.mkdir()
    home.mkdir()
    (app / "config.json").write_text(json.dumps({"offline_mode": offline}), encoding="utf-8")
    (tmp_path / "wrap.py").write_text(WRAPPER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}     # no cloud keys at all
    env.update(CURSIV_APP_DATA=str(app), HOME=str(home), USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
               CURSIV_NO_ENGINE_START="1", PYTHONIOENCODING="utf-8")
    attempts, report = tmp_path / "attempts.jsonl", tmp_path / "report.txt"
    p = subprocess.Popen([sys.executable, "-I", str(tmp_path / "wrap.py"), str(attempts), str(REPO), str(report)],
                         env=env, cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    seen, polls = set(), 0
    try:
        proc = psutil.Process(p.pid)
        while p.poll() is None:
            try:
                seen.update(_remote(_connections(proc)))
                polls += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            time.sleep(0.02)
        out = p.stdout.read().decode("utf-8", "replace")
    finally:
        if p.poll() is None:
            p.kill()
    assert p.returncode == 0 and report.exists(), out[-3000:]
    text = report.read_text(encoding="utf-8")
    assert "ALL PASSED" in text, text
    assert "full launcher, title bar, tray and chat window build" in text, text
    for part in ("imports", "offline reference", "calculations", "field notebook", "documents", "window"):
        assert f"PASS  {part}" in text, text
    tried = attempts.read_text(encoding="utf-8").splitlines() if attempts.exists() else []
    assert tried == [], f"connection attempts off this computer: {tried}"
    assert seen == set(), f"sockets the OS saw open to other computers: {seen}"
    assert polls > 5                                    # the OS observer really watched it run
    # nothing was written outside the temporary data folders
    assert not (REPO / ".cursiv" / "selftest.tmp").exists()


def test_the_observers_do_see_a_connection_when_there_is_one(tmp_path):
    """Observe an external attempt and a held OS socket independently.

    A rejected external TCP connection can vanish before an OS poll. Hold a
    loopback connection for the OS positive control; test remote classification
    separately. Neither observer can silently pass without seeing its control.
    """
    (tmp_path / "wrap.py").write_text(WRAPPER.split("root = sys.argv[2]")[0] + (
        "import socket, time\n"
        "s = socket.socket(); s.settimeout(1.5)\n"
        "try: s.connect(('192.0.2.1', 9))\n"
        "except OSError: pass\n"
        "s.close()\n"
        "server=socket.socket(); server.bind(('127.0.0.1',0)); server.listen(1)\n"
        "client=socket.socket(); client.connect(server.getsockname()); accepted,_=server.accept()\n"
        "open('control-port.txt','w').write(str(server.getsockname()[1]))\n"
        "time.sleep(1.5)\n"
        "accepted.close(); client.close(); server.close()\n"), encoding="utf-8")
    attempts = tmp_path / "attempts.jsonl"
    p = subprocess.Popen([sys.executable, "-I", str(tmp_path / "wrap.py"), str(attempts)], cwd=tmp_path)
    seen = set()
    proc = psutil.Process(p.pid)
    while p.poll() is None:
        try:
            seen.update((c.raddr.ip, c.raddr.port) for c in _connections(proc) if c.raddr)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        time.sleep(0.02)
    assert json.loads(attempts.read_text(encoding="utf-8").splitlines()[0]) == ["socket.connect", "192.0.2.1"]
    port = int((tmp_path / 'control-port.txt').read_text())
    assert ('127.0.0.1', port) in seen, seen
    from types import SimpleNamespace
    assert _remote([SimpleNamespace(raddr=SimpleNamespace(ip='192.0.2.1', port=9), status='SYN_SENT')]) == ['192.0.2.1:9 SYN_SENT']

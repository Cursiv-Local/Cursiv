"""
The network gate: one switch for every connection Cursiv makes off this computer.

`offline on` closes it (saved in .cursiv/config.json, so it holds after a
restart). While it's closed:

- `allowed()` is False. Cloud calls, web search, the connectivity probe, the
  update check and model downloads ask it first and stop with a plain message.
- An audit hook refuses any socket connection or DNS lookup to anything but
  this computer (127.0.0.1, ::1, localhost). That covers code that forgot to
  ask, third-party SDKs and background threads. Ollama is on loopback, so the
  local model keeps working.

The other two switches here are for automatic traffic while the gate is open.
Both are off until the person turns them on:

- `web_search_auto`: search the web when a question sounds current ("today",
  "right now"). Off means only an explicit "search: ..." searches.
- `update_check_auto`: look for a new release on GitHub after login. The
  "Check for Updates" button works either way.
"""
from __future__ import annotations

import ipaddress
import json
import os
import sys
import threading
from pathlib import Path
from cursiv_v215.core import atomic as _atomic
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

CONFIG_FILE = APP_DATA / "config.json"

DEFAULTS = {
    "offline_mode":      False,
    "web_search_auto":   False,
    "update_check_auto": False,
}

OFFLINE_MESSAGE = "Offline mode is on, so Cursiv won't connect to the internet. Type 'offline off' to allow it."


class NetworkBlocked(ConnectionRefusedError):
    """Raised when the gate is closed. An OSError, so callers that already
    handle 'no internet' handle this the same way."""


_lock = threading.Lock()
_cache: dict = {"mtime": None, "data": {}}


def _read() -> dict:
    """config.json, re-read only when it changes on disk."""
    try:
        mtime = (str(CONFIG_FILE), os.stat(CONFIG_FILE).st_mtime_ns)
    except OSError:
        mtime = (str(CONFIG_FILE), -1)
    if mtime != _cache["mtime"]:
        data = {}
        if mtime[1] != -1:
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        _cache["mtime"], _cache["data"] = mtime, data if isinstance(data, dict) else {}
    return _cache["data"]


def setting(name: str) -> bool:
    return bool(_read().get(name, DEFAULTS.get(name, False)))


def set_setting(name: str, on: bool) -> None:
    with _lock:
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
        data[name] = bool(on)
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _atomic.write_text(CONFIG_FILE, json.dumps(data, indent=2))
        _cache["mtime"] = None


def is_offline() -> bool:
    return setting("offline_mode")


def set_offline(on: bool) -> None:
    set_setting("offline_mode", on)


def allowed() -> bool:
    """May Cursiv talk to anything outside this computer right now?"""
    return not is_offline()


def require(what: str = "This") -> None:
    """Raise NetworkBlocked when the gate is closed."""
    if not allowed():
        raise NetworkBlocked(f"{what} needs the internet. {OFFLINE_MESSAGE}")


def web_search_auto() -> bool:
    return allowed() and setting("web_search_auto")


def update_check_auto() -> bool:
    return allowed() and setting("update_check_auto")


# ── The socket-level backstop ───────────────────────────────────────────────

_LOCAL_NAMES = {"localhost", "localhost.", "ip6-localhost", ""}


def is_local(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host).strip("[]").lower()
    if host in _LOCAL_NAMES or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


def _address_host(address):
    """The host part of a socket address; None for AF_UNIX paths (always local)."""
    if isinstance(address, tuple) and address:
        return address[0]
    return None


def _hook(event: str, args: tuple) -> None:
    if not event.startswith("socket."):
        return
    if event in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        host = _address_host(args[1]) if len(args) > 1 else None
    elif event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex",
                   "socket.gethostbyaddr", "socket.getnameinfo"):
        host = args[0] if args else None
        if event == "socket.getnameinfo" and isinstance(host, tuple):
            host = host[0]
    else:
        return
    if is_local(host) or allowed():
        return
    raise NetworkBlocked(f"Blocked a connection to {host}. {OFFLINE_MESSAGE}")


_installed = False


def install() -> None:
    """Add the audit hook once per process (audit hooks can't be removed;
    the hook checks the gate on every call, so it's a no-op while open)."""
    global _installed
    if _installed:
        return
    _installed = True
    sys.addaudithook(_hook)


install()

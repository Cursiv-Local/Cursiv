"""
Where Ollama (the local AI engine) lives on this computer, and how to start,
restart and install it, on Windows and macOS.

Windows: %LOCALAPPDATA%\\Programs\\Ollama\\ollama.exe, installed by OllamaSetup.exe.
macOS:   Ollama.app in /Applications or ~/Applications (the command-line tool is
         inside it, Contents/Resources/ollama), or `ollama` on the PATH (Homebrew).
         Installed by unzipping Ollama-darwin.zip into ~/Applications: no
         administrator password needed. Ollama.app is signed and notarized by Ollama.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:11434"
MAC = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

INSTALLER_URL = ("https://ollama.com/download/Ollama-darwin.zip" if MAC
                 else "https://ollama.com/download/OllamaSetup.exe")


def _mac_apps() -> list[Path]:
    return [Path("/Applications/Ollama.app"), Path.home() / "Applications" / "Ollama.app"]


def mac_app() -> Path | None:
    return next((a for a in _mac_apps() if a.exists()), None)


def exe() -> str | None:
    """The ollama command-line program, or None if Ollama isn't installed."""
    found = shutil.which("ollama")
    if found:
        return found
    if WINDOWS:
        p = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        return str(p) if p.exists() else None
    if MAC:
        app = mac_app()
        if app and (app / "Contents" / "Resources" / "ollama").exists():
            return str(app / "Contents" / "Resources" / "ollama")
        for p in (Path("/opt/homebrew/bin/ollama"), Path("/usr/local/bin/ollama")):
            if p.exists():
                return str(p)
    return None


def installed() -> bool:
    return exe() is not None


def running(timeout: float = 2) -> bool:
    try:
        urllib.request.urlopen(f"{API}/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


def _wait(seconds: int) -> bool:
    for _ in range(seconds):
        time.sleep(1)
        if running():
            return True
    return False


def start(env: dict | None = None, wait: int = 30) -> bool:
    """Start the engine in the background if it isn't running."""
    if running():
        return True
    cmd = exe()
    if not cmd:
        return False
    try:
        subprocess.Popen([cmd, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=_NO_WINDOW, env=env)
    except Exception:
        return False
    return _wait(wait)


def restart(env: dict | None = None) -> bool:
    """Quit and restart Ollama (fixes it not seeing downloaded models)."""
    if WINDOWS:
        for name in ("ollama app.exe", "ollama.exe"):
            subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True, creationflags=_NO_WINDOW)
        time.sleep(2)
        app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama app.exe"
        if app.exists():
            try:
                subprocess.Popen([str(app)], creationflags=_NO_WINDOW)
            except Exception:
                return False
            return _wait(30)
        return start(env)
    if MAC:
        subprocess.run(["pkill", "-x", "Ollama"], capture_output=True)
        subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
        time.sleep(2)
        app = mac_app()
        if app:
            subprocess.run(["open", "-g", str(app)], capture_output=True)   # -g: don't bring it to the front
            return _wait(30)
        return start(env)
    subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
    time.sleep(2)
    return start(env)


def install(download_to: Path, progress=None) -> None:
    """Download and install Ollama. progress(fraction or -1, text). Raises RuntimeError on failure."""
    def say(pct, text):
        if progress:
            progress(pct, text)
    name = "Ollama-darwin.zip" if MAC else "OllamaSetup.exe"
    dest = Path(download_to) / name
    req = urllib.request.Request(INSTALLER_URL, headers={"User-Agent": "Cursiv-Setup"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while chunk := r.read(1 << 20):
            out.write(chunk)
            got += len(chunk)
            say(int(got * 100 / total) if total else -1,
                f"Downloading Ollama… {got >> 20} MB" + (f" of {total >> 20} MB" if total else ""))
    if MAC:
        say(-1, "Installing Ollama into your Applications folder…")
        apps = Path.home() / "Applications"
        apps.mkdir(exist_ok=True)
        # ditto keeps the app's signature and permissions intact, unlike Python's zipfile
        rc = subprocess.run(["ditto", "-x", "-k", str(dest), str(apps)], capture_output=True).returncode
        if rc != 0 or not (apps / "Ollama.app").exists():
            raise RuntimeError(f"unpacking Ollama failed (code {rc})")
        subprocess.run(["open", "-g", str(apps / "Ollama.app")], capture_output=True)
        if not installed():
            raise RuntimeError("Ollama was unpacked but can't be found")
        return
    say(-1, "Installing Ollama (a small progress window may appear)…")
    rc = subprocess.run([str(dest), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]).returncode
    if rc != 0 or not installed():
        raise RuntimeError(f"the Ollama installer stopped (code {rc})")

"""
Cursiv Setup -- one window that gets a computer ready to talk to Cursiv.

  1. Local AI engine (Ollama): install it quietly with a progress bar, start it.
  2. AI model: download one through Ollama's API with real progress (MB, %),
     cancellable.
  3. While you wait: Cursiv Cloud on/off, and an optional free Gemini/Groq key
     (tested before it's saved).

Replaces the old flow of separate PowerShell console windows. Opened
automatically on first run when Ollama or a model is missing, and any time
from the launcher's Setup button or the tray menu.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLayout, QLineEdit,
    QProgressBar, QPushButton, QVBoxLayout,
)

BG, BG2, BORDER = "#0b0b12", "#13131e", "#2a2a3f"
GOLD, SILVER, SILV2 = "#FFD700", "#C8C8D4", "#666680"
GREEN, RED, AMBER = "#3ecf6e", "#FF4455", "#e8a020"

OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
OLLAMA_API = "http://127.0.0.1:11434"

# Coding models for Cursiv's offline code council: (label, tag)
CODE_MODELS = [
    ("qwen2.5-coder 3B — fast on 4–6 GB graphics cards (1.9 GB)", "qwen2.5-coder:3b"),
    ("qwen2.5-coder 7B — for 8 GB+ graphics cards (4.7 GB)", "qwen2.5-coder:7b"),
    ("qwen2.5-coder 14B — smartest, needs 12 GB+ (9 GB)", "qwen2.5-coder:14b"),
]

# Lets Cursiv read pasted images offline (chat_commands._vision_describe).
VISION_MODEL = ("gemma3 4B — reads and describes images offline (3.3 GB)", "gemma3:4b")
VISION_FAMILIES = ("gemma3", "qwen2.5vl", "llama3.2-vision", "minicpm-v", "llava", "moondream")

# (label, model tag, approximate download size)
MODELS = [
    ("llama3.1 — best answers, for 8 GB+ graphics cards (4.9 GB)", "llama3.1", "4.9 GB"),
    ("qwen3 4B — good answers on 4–6 GB graphics cards (2.5 GB)", "qwen3:4b-instruct", "2.5 GB"),
    ("qwen2.5 1.5B — smallest and fastest (1 GB)", "qwen2.5:1.5b", "1 GB"),
]


def recommended_index(options: list, small: bool) -> int:
    """Which entry to preselect for this PC's graphics card."""
    want = ":4b-instruct" if small else None
    for i, opt in enumerate(options):
        if want and opt[1].endswith(want):
            return i
    return 0 if not small else min(1, len(options) - 1)
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ── Checks (plain functions, safe to call from any thread) ───────────────────

def ollama_installed() -> bool:
    return bool(shutil.which("ollama")) or OLLAMA_EXE.exists()


def ollama_running() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def installed_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=4) as r:
            names = [m.get("name", "") for m in json.loads(r.read().decode()).get("models", [])]
        return [n for n in names if n and "embed" not in n.lower()]
    except Exception:
        return []


def start_ollama() -> bool:
    """Start the Ollama server in the background if it isn't running."""
    if ollama_running():
        return True
    exe = shutil.which("ollama") or (str(OLLAMA_EXE) if OLLAMA_EXE.exists() else None)
    if not exe:
        return False
    try:
        try:
            from cursiv_v215.core import speed
            env = speed.ollama_env()          # flash attention + compact cache for this server
        except Exception:
            env = None
        subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=_NO_WINDOW, env=env)
    except Exception:
        return False
    for _ in range(30):
        time.sleep(1)
        if ollama_running():
            return True
    return False


def restart_ollama() -> bool:
    """Quit and restart Ollama (fixes it not seeing downloaded models)."""
    for name in ("ollama app.exe", "ollama.exe"):
        subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True, creationflags=_NO_WINDOW)
    time.sleep(2)
    app = OLLAMA_EXE.with_name("ollama app.exe")
    try:
        if app.exists():
            subprocess.Popen([str(app)], creationflags=_NO_WINDOW)
        else:
            return start_ollama()
    except Exception:
        return False
    for _ in range(30):
        time.sleep(1)
        if ollama_running():
            return True
    return False


def needs_setup() -> bool:
    """True when this computer can't run Cursiv locally yet (no Ollama, or no model)."""
    if not ollama_installed():
        return True
    if not ollama_running() and not start_ollama():
        return True
    return not installed_models()


# ── Background work → UI, through Qt signals ────────────────────────────────

class _Signals(QObject):
    progress = pyqtSignal(str, int, str)   # step, percent (-1 = busy), text
    done     = pyqtSignal(str, bool, str)  # step, ok, message


class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Setup")
        self.setMinimumWidth(620)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel {{ color: {SILVER}; background: transparent; }}
            QFrame#card {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px; }}
            QPushButton {{ background: #2255DD; color: #fff; border: none; border-radius: 4px;
                           padding: 6px 14px; font-weight: 600; }}
            QPushButton:disabled {{ background: #2a2a3f; color: #777; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
            QProgressBar {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 3px; color: {SILVER};
                            text-align: center; height: 16px; }}
            QProgressBar::chunk {{ background: #2255DD; }}
            QComboBox, QLineEdit {{ background: {BG}; color: {SILVER}; border: 1px solid {BORDER};
                                    border-radius: 4px; padding: 4px 6px; }}
            QCheckBox {{ color: {SILVER}; }}
        """)
        self._sig = _Signals()
        self._sig.progress.connect(self._on_progress)
        self._sig.done.connect(self._on_done)
        self._cancel_pull = threading.Event()
        self._busy = False

        lay = QVBoxLayout(self)
        lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)   # grow, never clip
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        title = QLabel("Get Cursiv ready on this computer")
        title.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: 700;")
        lay.addWidget(title)
        sub = QLabel("Cursiv runs on your own computer through Ollama, a free local AI engine. "
                     "Nothing you type leaves this computer unless you choose a cloud option below.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        lay.addWidget(sub)

        # Step 1 — Ollama
        self._s1 = self._card(lay, "1  ·  Local AI engine (Ollama)")
        self._s1_btn = QPushButton("Install Ollama")
        self._s1_btn.clicked.connect(self._install_ollama)
        self._s1["row"].addWidget(self._s1_btn)
        self._s1_restart = QPushButton("Restart Ollama")
        self._s1_restart.setObjectName("ghost")
        self._s1_restart.setToolTip("Fixes Ollama not seeing models you've already downloaded")
        self._s1_restart.clicked.connect(self._restart_ollama)
        self._s1["row"].addWidget(self._s1_restart)

        # Step 2 — model
        self._s2 = self._card(lay, "2  ·  AI model")
        self._model_box = QComboBox()
        for label, tag, _size in MODELS:
            self._model_box.addItem(label, tag)
        try:
            from cursiv_v215.core import speed
            _small = speed.small_gpu()
        except Exception:
            _small = False
        self._model_box.setCurrentIndex(recommended_index(MODELS, _small))
        self._s2["row"].addWidget(self._model_box, 1)
        self._s2_btn = QPushButton("Download")
        self._s2_btn.clicked.connect(self._pull_model)
        self._s2["row"].addWidget(self._s2_btn)
        self._s2_cancel = QPushButton("Cancel")
        self._s2_cancel.setObjectName("ghost")
        self._s2_cancel.clicked.connect(self._cancel_pull.set)
        self._s2_cancel.setVisible(False)
        self._s2["row"].addWidget(self._s2_cancel)

        # Step 3 — coding model (optional)
        self._s4 = self._card(lay, "3  ·  Coding model (optional)")
        self._s4["detail"].setText("A model trained for programming makes Cursiv much better at writing and fixing code offline.")
        self._code_box = QComboBox()
        for label, tag in CODE_MODELS:
            self._code_box.addItem(label, tag)
        self._code_box.setCurrentIndex(recommended_index(CODE_MODELS, _small))
        self._s4["row"].addWidget(self._code_box, 1)
        self._s4_btn = QPushButton("Download")
        self._s4_btn.clicked.connect(self._pull_code_model)
        self._s4["row"].addWidget(self._s4_btn)

        # Step 4 — image reading model (optional)
        self._s5 = self._card(lay, "4  ·  Image reading model (optional)")
        self._s5_btn = QPushButton("Download")
        self._s5_btn.clicked.connect(self._pull_vision_model)
        self._s5["row"].addStretch(1)
        self._s5["row"].addWidget(self._s5_btn)

        # Step 5 — cloud + free keys
        self._s3 = self._card(lay, "5  ·  While you wait (optional)")
        self._s3_intro = ("Downloading a model can take a while. Until it's done, Cursiv can answer through "
                          "Cursiv Cloud (free, sent to cursiv.winklers-llc.com) or your own free AI key.")
        self._s3["detail"].setText(self._s3_intro)
        self._cloud_box = QCheckBox("Use Cursiv Cloud when no local model is ready")
        self._cloud_box.toggled.connect(self._toggle_cloud)
        self._s3["extra"].addWidget(self._cloud_box)
        key_row = QHBoxLayout()
        self._key_kind = QComboBox()
        self._key_kind.addItem("Gemini key", "gemini")
        self._key_kind.addItem("Groq key", "groq")
        key_row.addWidget(self._key_kind)
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("paste a free key (optional)")
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_row.addWidget(self._key_edit, 1)
        self._key_btn = QPushButton("Test && save")
        self._key_btn.clicked.connect(self._save_key)
        key_row.addWidget(self._key_btn)
        get_btn = QPushButton("Get a free key")
        get_btn.setObjectName("ghost")
        get_btn.clicked.connect(lambda: webbrowser.open(
            "https://aistudio.google.com/apikey" if self._key_kind.currentData() == "gemini"
            else "https://console.groq.com/keys"))
        key_row.addWidget(get_btn)
        self._s3["extra"].addLayout(key_row)

        bottom = QHBoxLayout()
        self._footer = QLabel("")
        self._footer.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        bottom.addWidget(self._footer, 1)
        self._close_btn = QPushButton("Done")
        self._close_btn.clicked.connect(self.accept)
        bottom.addWidget(self._close_btn)
        lay.addLayout(bottom)

        try:
            from cursiv_v215.ui.chat_app import cloud_enabled
            self._cloud_box.setChecked(cloud_enabled())
        except Exception:
            self._cloud_box.setEnabled(False)
        self.refresh()

    # ── Layout helper ────────────────────────────────────────────────────
    def _card(self, parent_lay, title: str) -> dict:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(6)
        head = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-weight: 700; font-size: 13px;")
        head.addWidget(t, 1)
        status = QLabel("")
        head.addWidget(status)
        v.addLayout(head)
        detail = QLabel("")
        detail.setWordWrap(True)
        detail.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        v.addWidget(detail)
        bar = QProgressBar()
        bar.setVisible(False)
        v.addWidget(bar)
        row = QHBoxLayout()
        v.addLayout(row)
        extra = QVBoxLayout()
        v.addLayout(extra)
        parent_lay.addWidget(card)
        return {"status": status, "detail": detail, "bar": bar, "row": row, "extra": extra}

    def _set_status(self, step: dict, ok: bool | None, text: str):
        color, mark = (GREEN, "✓ Ready") if ok else ((AMBER, "Needed") if ok is False else (SILV2, "…"))
        step["status"].setText(mark)
        step["status"].setStyleSheet(f"color: {color}; font-weight: 700;")
        step["detail"].setText(text)

    # ── State ────────────────────────────────────────────────────────────
    def refresh(self):
        installed = ollama_installed()
        running = installed and ollama_running()   # check only -- never block the window
        models = installed_models() if running else []
        if not installed:
            self._set_status(self._s1, False, "Not installed yet. Install is free (about 1 GB) and needs no admin rights.")
        elif not running:
            self._set_status(self._s1, False, "Installed, but it isn't running. Click Start.")
        else:
            self._set_status(self._s1, True, "Installed and running.")
        self._s1_btn.setText("Install Ollama" if not installed else "Start Ollama")
        self._s1_btn.setVisible(not running)
        self._s1_btn.setEnabled(not self._busy)
        self._s1_restart.setVisible(running)
        self._s1_restart.setEnabled(not self._busy)

        if models:
            self._set_status(self._s2, True, "Installed: " + ", ".join(models))
            self._s2_btn.setText("Download another")
        else:
            self._set_status(self._s2, False if running else None,
                             "No model yet. Pick one and click Download." if running
                             else "Waiting for step 1.")
            self._s2_btn.setText("Download")
        self._s2_btn.setEnabled(running and not self._busy)
        self._model_box.setEnabled(running and not self._busy)

        coders = [m for m in models if "coder" in m]
        if coders:
            self._set_status(self._s4, True, "Installed: " + ", ".join(coders))
            self._s4_btn.setText("Download another")
        else:
            self._set_status(self._s4, None, "Optional. " + ("Pick one and click Download." if running else "Waiting for step 1."))
            self._s4_btn.setText("Download")
        self._s4_btn.setEnabled(running and not self._busy)
        self._code_box.setEnabled(running and not self._busy)

        vision = [m for m in models if m.split(":")[0] in VISION_FAMILIES]
        if vision:
            self._set_status(self._s5, True, "Installed: " + ", ".join(vision) + " — paste an image into chat to use it.")
            self._s5_btn.setVisible(False)
        else:
            self._set_status(self._s5, None, "Optional. Lets Cursiv read and describe images you paste in, "
                             "with no internet. " + VISION_MODEL[0] + "." if running else "Optional. Waiting for step 1.")
            self._s5_btn.setVisible(True)
        self._s5_btn.setEnabled(running and not self._busy)

        ready = running and bool(models)
        self._set_status(self._s3, True if ready else None,
                         "All set — Cursiv runs fully on this computer." if ready else self._s3_intro)
        self._footer.setText("Everything is ready." if ready else "You can close this and come back any time "
                                                                  "(launcher → Setup, or the tray menu).")

    # ── Step 1 ───────────────────────────────────────────────────────────
    def _install_ollama(self):
        self._busy = True
        self._s1_btn.setEnabled(False)
        self._s1["bar"].setVisible(True)
        threading.Thread(target=self._do_install, daemon=True).start()

    def _do_install(self):
        try:
            if not ollama_installed():
                dest = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
                req = urllib.request.Request(OLLAMA_INSTALLER_URL, headers={"User-Agent": "Cursiv-Setup"})
                with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as out:
                    total = int(r.headers.get("Content-Length") or 0)
                    got = 0
                    while chunk := r.read(1 << 20):
                        out.write(chunk)
                        got += len(chunk)
                        pct = int(got * 100 / total) if total else -1
                        self._sig.progress.emit("s1", pct, f"Downloading Ollama… {got >> 20} MB"
                                                + (f" of {total >> 20} MB" if total else ""))
                self._sig.progress.emit("s1", -1, "Installing Ollama (a small progress window may appear)…")
                rc = subprocess.run([str(dest), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]).returncode
                if rc != 0 or not ollama_installed():
                    raise RuntimeError(f"the Ollama installer stopped (code {rc})")
            self._sig.progress.emit("s1", -1, "Starting Ollama…")
            if not start_ollama():
                raise RuntimeError("Ollama is installed but didn't start. Try restarting the computer.")
            self._sig.done.emit("s1", True, "Ollama is installed and running.")
        except Exception as exc:
            self._sig.done.emit("s1", False, f"Couldn't install Ollama: {exc}")

    def _restart_ollama(self):
        self._busy = True
        self._s1_restart.setEnabled(False)
        self._sig.progress.emit("s1", -1, "Restarting Ollama…")
        def work():
            ok = restart_ollama()
            self._sig.done.emit("s1", ok, "Ollama restarted." if ok else "Ollama didn't come back -- try restarting the computer.")
        threading.Thread(target=work, daemon=True).start()

    # ── Step 2 ───────────────────────────────────────────────────────────
    def _pull_model(self):
        self._busy = True
        self._cancel_pull.clear()
        self._s2_btn.setEnabled(False)
        self._model_box.setEnabled(False)
        self._s2_cancel.setVisible(True)
        self._s2["bar"].setVisible(True)
        tag = self._model_box.currentData()
        threading.Thread(target=self._do_pull, args=(tag, "s2"), daemon=True).start()

    def _pull_code_model(self):
        self._busy = True
        self._cancel_pull.clear()
        self._s4_btn.setEnabled(False)
        self._code_box.setEnabled(False)
        self._s4["bar"].setVisible(True)
        tag = self._code_box.currentData()
        threading.Thread(target=self._do_pull, args=(tag, "s4"), daemon=True).start()

    def _pull_vision_model(self):
        self._busy = True
        self._cancel_pull.clear()
        self._s5_btn.setEnabled(False)
        self._s5["bar"].setVisible(True)
        threading.Thread(target=self._do_pull, args=(VISION_MODEL[1], "s5"), daemon=True).start()

    def _do_pull(self, tag: str, step: str = "s2"):
        try:
            from cursiv_v215.core import netgate
            if not netgate.allowed():
                self._sig.done.emit(step, False, f"Can't download {tag}. {netgate.OFFLINE_MESSAGE}")
                return
        except ImportError:
            pass
        try:
            req =urllib.request.Request(f"{OLLAMA_API}/api/pull", data=json.dumps({"name": tag, "stream": True}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3600) as r:
                for line in r:
                    if self._cancel_pull.is_set():
                        self._sig.done.emit(step, False, "Download paused. Click Download to continue where it left off.")
                        return
                    try:
                        st = json.loads(line.decode())
                    except Exception:
                        continue
                    if st.get("error"):
                        raise RuntimeError(st["error"])
                    total, done = st.get("total") or 0, st.get("completed") or 0
                    if total and done:
                        self._sig.progress.emit(step, int(done * 100 / total),
                                                f"Downloading {tag}… {done / 1e9:.2f} of {total / 1e9:.2f} GB")
                    elif st.get("status"):
                        self._sig.progress.emit(step, -1, f"{tag}: {st['status']}")
                    if st.get("status") == "success":
                        self._sig.done.emit(step, True, f"{tag} is ready.")
                        return
            raise RuntimeError("the download ended early — click Download to resume")
        except Exception as exc:
            self._sig.done.emit(step, False, f"Model download stopped: {exc}")

    # ── Step 3 ───────────────────────────────────────────────────────────
    def _toggle_cloud(self, on: bool):
        try:
            from cursiv_v215.ui.chat_app import set_cloud_enabled
            set_cloud_enabled(on)
        except Exception:
            pass

    def _save_key(self):
        key = self._key_edit.text().strip()
        if not key:
            return
        kind = self._key_kind.currentData()
        self._key_btn.setEnabled(False)
        self._sig.progress.emit("s3", -1, f"Testing your {kind.title()} key…")

        def work():
            try:
                from cursiv_v215.ui.chat_app import free_key_command
                reply = free_key_command(f"{kind} {key}") or ""
                self._sig.done.emit("s3", "saved and working" in reply, reply.split("\n")[0])
            except Exception as exc:
                self._sig.done.emit("s3", False, f"Couldn't test the key: {exc}")
        threading.Thread(target=work, daemon=True).start()

    # ── Signal handlers (main thread) ────────────────────────────────────
    def _step(self, name: str) -> dict:
        return {"s1": self._s1, "s2": self._s2, "s3": self._s3, "s4": self._s4, "s5": self._s5}[name]

    def _on_progress(self, name: str, pct: int, text: str):
        step = self._step(name)
        bar = step["bar"]
        if name != "s3":
            bar.setVisible(True)
            if pct < 0:
                bar.setRange(0, 0)
            else:
                bar.setRange(0, 100)
                bar.setValue(pct)
        step["detail"].setText(text)

    def _on_done(self, name: str, ok: bool, message: str):
        step = self._step(name)
        step["bar"].setVisible(False)
        if name == "s3":
            self._key_btn.setEnabled(True)
            if ok:
                self._key_edit.clear()
            step["detail"].setText(message)
            return
        self._busy = False
        self._s2_cancel.setVisible(False)
        self.refresh()
        if not ok:
            step["detail"].setText(message)
            step["detail"].setStyleSheet(f"color: {RED}; font-size: 12px;")
        else:
            step["detail"].setStyleSheet(f"color: {SILV2}; font-size: 12px;")

    def closeEvent(self, e):
        self._cancel_pull.set()      # a model download resumes next time
        super().closeEvent(e)

    def accept(self):
        self._cancel_pull.set()
        super().accept()

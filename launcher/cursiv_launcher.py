"""
Cursiv Desktop — the main window (chat panel), tray menu, login gate,
and updater. One copy runs at a time (local socket lock), released by
aboutToQuit cleanup on every quit path.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QColor, QFont, QFontDatabase, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QProgressDialog, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget,
)

from chat_panel import ChatPanel
from shell_dialogs import (
    _is_owner_machine, _UnlockDialog, CommandAccessDialog, _fleet_age_label,
    _fleet_dot, FleetDialog, TitleBar, _ResizeRoot,
)
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2, RED  # one palette for every window (theme.py)

if getattr(sys, "frozen", False):
    _HERE = Path(sys.executable).parent
    _ROOT = _HERE
    # PyInstaller's COLLECT layout puts bundled Python source/data (services/,
    # cursiv_v215/, etc.) under _internal/, not directly beside Cursiv.exe.
    # Anything launched as "python <relative path>" needs THIS as its cwd,
    # not _ROOT — using _ROOT there silently fails (file/module not found),
    # even though the spawned cmd window still opens with the right title.
    _DATA_ROOT = _HERE / "_internal"
else:
    _HERE = Path(__file__).parent
    _ROOT = _HERE.parent
    _DATA_ROOT = _ROOT

# Frozen: the bundle's data folder (_internal on Windows, Contents/Resources in the Mac
# app), where build.spec puts launcher/resources/icons -- not next to the executable.
_ICONS = (
    Path(getattr(sys, "_MEIPASS", _HERE)) / "launcher" / "resources" / "icons"
    if getattr(sys, "frozen", False)
    else _HERE / "resources" / "icons"
)

_LOCK_PORT       = 17_860        # local socket port for single-instance lock

# ── Update checker ─────────────────────────────────────────────────────────────
_CURRENT_VERSION   = "3.14-U88"
_GITHUB_API        = "https://api.github.com/repos/Cursiv-Local/Cursiv/releases/latest"
_GITHUB_RELEASES   = "https://github.com/Cursiv-Local/Cursiv/releases"


def _auto_update_check_on() -> bool:
    """Automatic update check after login: off unless turned on, never offline."""
    try:
        from cursiv_v215.core import netgate
        return netgate.update_check_auto()
    except Exception:
        return False


def _net_allowed() -> bool:
    try:
        from cursiv_v215.core import netgate
        return netgate.allowed()
    except Exception:
        return True

# ── Fleet dashboard ────────────────────────────────────────────────────────────
from relay_settings import RELAY_URL as _RELAY_URL, FLEET_TOKEN as _FLEET_TOKEN
_MACHINE_NAME = platform.node()
_MACHINE_ID   = hashlib.sha256(
    f"cursiv.local.{_MACHINE_NAME}.{os.environ.get('USERNAME', '')}".encode()
).hexdigest()[:24]

# ── Ollama (core/ollama_host.py: Windows and macOS) ──────────────────────────
def _is_ollama_installed() -> bool:
    from cursiv_v215.core import ollama_host
    return ollama_host.installed()


# Windows' default UI font (Segoe UI) has no Egyptian Hieroglyphs glyphs, and
# Qt's automatic font fallback does NOT pick up "Segoe UI Historic" (the
# system font that covers that block) on its own. Every hieroglyph in this UI
# (Anubis, the Eye of Horus) rendered as a tofu box until it was registered
# explicitly. Call once, before building any widget that uses one.
_HIEROGLYPH_FONT_LOADED = False


def _ensure_hieroglyph_font() -> None:
    global _HIEROGLYPH_FONT_LOADED
    if _HIEROGLYPH_FONT_LOADED:
        return
    try:
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/seguihis.ttf")
    except Exception:
        pass
    _HIEROGLYPH_FONT_LOADED = True


def _hieroglyph_font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """A font usable for mixed hieroglyph+Latin text in one widget -- Qt
    tries 'Segoe UI' first (covers the Latin text) and falls back to
    'Segoe UI Historic' per-glyph for anything Segoe UI doesn't cover
    (the hieroglyph), rather than needing two separate widgets."""
    _ensure_hieroglyph_font()
    font = QFont()
    font.setFamilies(["Segoe UI", "Segoe UI Historic"])
    font.setPointSize(size)
    font.setWeight(weight)
    return font


# Path.home(), not __file__-relative -- see cursiv_v215/guardian/access_gate.py
# for why: this needs to survive reinstalls/upgrades at a fixed install path,
# same as every other piece of persistent state in this app.
_GETTING_STARTED_FLAG = Path.home() / ".cursiv" / "runtime" / "getting_started_shown.flag"


def _is_ollama_installed_quick() -> bool:
    return _is_ollama_installed()


def _getting_started_seen() -> bool:
    return _GETTING_STARTED_FLAG.exists()


def _mark_getting_started_seen() -> None:
    try:
        _GETTING_STARTED_FLAG.parent.mkdir(parents=True, exist_ok=True)
        _GETTING_STARTED_FLAG.touch()
    except OSError:
        pass


# ── Palette ───────────────────────────────────────────────────────────────────

import theme
QSS = theme.APP_QSS

# ── Single-instance lock ──────────────────────────────────────────────────────

_lock_socket: Optional[socket.socket] = None


def _acquire_instance_lock() -> bool:
    """
    Bind a local TCP socket as a single-instance lock.
    Returns True if this is the first instance, False if another is running.
    """
    global _lock_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", _LOCK_PORT))
        s.listen(1)
        _lock_socket = s
        return True
    except OSError:
        return False


def _release_instance_lock() -> None:
    global _lock_socket
    if _lock_socket:
        try:
            _lock_socket.close()
        except Exception:
            pass
        _lock_socket = None


# ── Update checker ────────────────────────────────────────────────────────────

def _version_key(v: str) -> Optional[tuple[int, ...]]:
    """'3.14-U32' / 'v3.14-U32' / '3.14' -> (3, 14, 32) / (3, 14, 0). None if unparseable."""
    import re as _re
    m = _re.fullmatch(r"v?(\d+)\.(\d+)(?:-U(\d+))?", v.strip(), _re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def _version_is_newer(remote: str, current: str) -> bool:
    """True if the remote release is newer than this build."""
    r, c = _version_key(remote), _version_key(current)
    if r is None or c is None:
        return remote.lstrip("v").strip().lower() != current.strip().lower()
    return r > c


class _UpdateSignals(QObject):
    result = pyqtSignal(dict)   # emitted on the main thread when check completes


class UpdateChecker:
    """Fetches the latest GitHub release in a background thread; emits result on main thread."""

    def __init__(self, on_result):
        self._signals = _UpdateSignals()
        self._signals.result.connect(on_result)

    def check(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            from cursiv_v215.core import netgate
            from update_security import asset
            if not netgate.allowed():
                raise netgate.NetworkBlocked(netgate.OFFLINE_MESSAGE)
            req = urllib.request.Request(
                _GITHUB_API,
                headers={"Accept": "application/vnd.github+json", "User-Agent": "Cursiv-Launcher"},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            tag, asset = asset(data)
            body = data.get("body", "")
            self._signals.result.emit({
                "ok":       True,
                "tag":      tag,
                "body":     body,
                "exe_url":  asset["browser_download_url"] if asset else None,
                "exe_size": asset.get("size", 0) if asset else 0,
            })
        except Exception as exc:
            self._signals.result.emit({"ok": False, "error": str(exc)})


class _DownloadSignals(QObject):
    progress = pyqtSignal(int, str)    # percent (-1 = unknown), status text
    done     = pyqtSignal(bool, str)   # ok, installer path or error message


def _run_installer_and_quit(installer: str) -> None:
    """
    Run the downloaded installer in update mode, then quit so it can replace
    our files. /SILENT shows only a small progress window -- no wizard, and the
    12-step first-time setup is skipped (its [Run] entry is skipifsilent).
    /UPDATE=1 makes the installer reopen Cursiv when it finishes.
    """
    from update_security import verify_installer
    verify_installer(installer)  # repeat identity verification immediately before execution
    subprocess.Popen(
        [installer, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/UPDATE=1"],
        close_fds=True,
    )
    # Give the installer a moment to start, then shut down cleanly (aboutToQuit
    # -> _cleanup stops our process, services, and the instance lock).
    QTimer.singleShot(1500, QApplication.quit)


class UpdateDialog(QDialog):
    """Shows release notes, downloads the new installer, and installs it."""

    def __init__(self, tag: str, body: str, exe_url: Optional[str], parent=None, exe_size: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Update Available")
        self.setFixedWidth(500)
        self.setStyleSheet(f"background: {BG}; color: {SILVER};")
        self._tag = tag
        self._expected_size = exe_size
        self._signals = _DownloadSignals()
        self._signals.progress.connect(self._on_progress)
        self._signals.done.connect(self._on_done)

        vlay = QVBoxLayout(self)
        vlay.setSpacing(12)
        vlay.setContentsMargins(20, 20, 20, 20)

        header = QLabel(f"<b>Version {tag} is available</b>  (you have {_CURRENT_VERSION})")
        header.setStyleSheet(f"color: {GOLD}; font-size: 14px;")
        vlay.addWidget(header)

        notes_lbl = QLabel("What's new:")
        notes_lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        vlay.addWidget(notes_lbl)

        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(body or "(no release notes)")
        notes.setFixedHeight(180)
        notes.setStyleSheet(
            f"background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};"
            " font-family: 'Segoe UI', Arial; font-size: 12px;"
        )
        vlay.addWidget(notes)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(
            f"QProgressBar {{ background: {BG2}; border: 1px solid {BORDER}; color: {SILVER}; }}"
            f"QProgressBar::chunk {{ background: #d4b04c; }}"
        )
        vlay.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        self._status.setVisible(False)
        vlay.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        if exe_url:
            self._dl_btn = QPushButton("Update Now")
            self._dl_btn.setStyleSheet(
                f"background: #d4b04c; color: #17120a; border-radius: 4px;"
                " font-weight: 600; padding: 6px 16px;"
            )
            self._dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._dl_btn.clicked.connect(lambda: self._download(exe_url))
            btn_row.addWidget(self._dl_btn)

        open_btn = QPushButton("Open Releases Page")
        open_btn.setStyleSheet(
            f"background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};"
            " border-radius: 4px; padding: 6px 16px;"
        )
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(lambda: webbrowser.open(_GITHUB_RELEASES))
        btn_row.addWidget(open_btn)

        btn_row.addStretch()
        self._later_btn = QPushButton("Not Now")
        self._later_btn.setStyleSheet(
            f"background: transparent; color: {SILV2}; border: none; padding: 6px 8px;"
        )
        self._later_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._later_btn)

        vlay.addLayout(btn_row)

    def _download(self, url: str):
        self._dl_btn.setEnabled(False)
        self._later_btn.setEnabled(False)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._status.setText("Downloading the update…")
        self._status.setVisible(True)
        threading.Thread(target=self._do_download, args=(url,), daemon=True).start()

    def _do_download(self, url: str):
        """Background thread -- talks to the UI only through self._signals."""
        try:
            from update_security import download
            dest = download(url, self._tag, self._expected_size, self._signals.progress.emit)
            self._signals.done.emit(True, str(dest))
        except Exception as exc:
            self._signals.done.emit(False, str(exc))

    def _on_progress(self, pct: int, text: str):
        if pct < 0:
            self._progress.setRange(0, 0)       # size unknown: busy indicator
        else:
            self._progress.setRange(0, 100)
            self._progress.setValue(pct)
        self._status.setText(text)

    def _on_done(self, ok: bool, info: str):
        if not ok:
            self._progress.setVisible(False)
            self._status.setText(f"Download failed: {info}  —  try again, or use 'Open Releases Page'.")
            self._dl_btn.setEnabled(True)
            self._later_btn.setEnabled(True)
            return
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        parent = self.parent()
        if parent is not None and hasattr(parent, "_confirm_leave") and not parent._confirm_leave():
            self._status.setText("Update downloaded. Click Update Now again when you're ready.")
            self._dl_btn.setEnabled(True)
            self._later_btn.setEnabled(True)
            return
        self._status.setText("Installing… Cursiv will close and reopen on its own in a minute.")
        try:
            _run_installer_and_quit(info)
        except Exception as exc:
            self._status.setText(f"Couldn't start the installer: {exc}")
            self._dl_btn.setEnabled(True)
            self._later_btn.setEnabled(True)


# ── Command-access management ─────────────────────────────────────────────────







# ── Fleet dashboard ───────────────────────────────────────────────────────────







# ── Title bar ─────────────────────────────────────────────────────────────────





class CursivLauncher(QMainWindow):
    def __init__(self, username: str = "Joshua"):
        super().__init__()
        try:   # memory is kept per person: whoever logged in
            from cursiv_v215.memory import semantic as _sem
            _sem.set_person(username)
        except Exception:
            pass
        self._username   = username

        self.setWindowTitle("Cursiv")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        # Sized for the chat panel, which is now the entire window (the
        # control sidebar is built but hidden -- see _build_ui). Frameless
        # windows don't get free edge-resize handling from Qt, so this is
        # a fixed size rather than a minimum; true drag-to-resize is a
        # follow-up, not part of this pass.
        self.resize(1120, 740)
        self.setMinimumSize(780, 520)
        self.setStyleSheet(QSS)

        self._build_ui()
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, activated=lambda: self.showNormal() if self.isFullScreen() else None)
        self._build_tray()

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        # Cleanup hook — fires on every quit path (TitleBar X, tray Quit, etc.)
        QApplication.instance().aboutToQuit.connect(self._cleanup)
        # Look for a newer release shortly after startup, only if the person turned
        # that on ('autoupdate on' / Settings) and offline mode is off. Silent
        # unless one exists. The Check for Updates button works either way.
        if _auto_update_check_on():
            QTimer.singleShot(10_000, lambda: self._check_updates(automatic=True))
        # Phone app <-> this person's memory: learn from phone chats, share a summary back.
        self._phone_sync_timer = QTimer(self)
        self._phone_sync_timer.timeout.connect(self._phone_sync)
        self._phone_sync_timer.start(5 * 60_000)
        QTimer.singleShot(30_000, self._phone_sync)
        QTimer.singleShot(12_000, self._warm_local_model)

        QTimer.singleShot(200, lambda: self._set_status("Ready"))

        # First run only: show Getting Started automatically once the
        # window has had a moment to finish rendering.
        if not _getting_started_seen():
            QTimer.singleShot(1800, self._show_getting_started)
        # Setup window if Ollama or a model is missing (replaces the old
        # installer-time PowerShell setup windows).
        QTimer.singleShot(2500, self._maybe_open_setup)

        # Fleet heartbeat — fires if relay URL + token are configured
        if _RELAY_URL and _FLEET_TOKEN:
            QTimer.singleShot(3000, self._start_fleet_heartbeat)

    # ── Cleanup (connected to aboutToQuit) ────────────────────────────────

    def _cleanup(self):
        _release_instance_lock()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = _ResizeRoot()
        self.setCentralWidget(root)
        root.setObjectName("root")
        root.setStyleSheet(f"#root {{ background: {BG}; border: 1px solid {BORDER}; }}")

        vlay = QVBoxLayout(root)
        vlay.setContentsMargins(_ResizeRoot._M, 0, _ResizeRoot._M, _ResizeRoot._M)   # edge strips for resizing
        vlay.setSpacing(0)

        _title = TitleBar(self, self._username)
        _title.setCursor(Qt.CursorShape.ArrowCursor)    # don't inherit the edge-resize cursor
        vlay.addWidget(_title)

        # ── Sidebar: no longer shown -- "Getting Started" moved into the
        # tray menu instead. Still built (not
        # skipped) and kept alive off-screen because _check_updates(),
        # _download_codex_models(), _install_ollama(), and the fleet
        # heartbeat all update self._upd_btn/_codex_dl_btn/_ollama_btn/
        # _fleet_lbl by reference -- those methods are reachable from the
        # tray menu regardless of whether this rail is visible, and would
        # crash on a missing attribute if the widgets were never built.
        self._sidebar = QWidget()
        side_lay = QVBoxLayout(self._sidebar)
        side_lay.setContentsMargins(24, 20, 24, 20)
        side_lay.setSpacing(16)
        side_lay.addLayout(self._build_center())
        side_lay.addStretch(1)
        self._sidebar.hide()

        # ── Chat panel: the only view now
        chat_wrap = QWidget()
        chat_wrap.setStyleSheet(f"background: {BG};")
        body = QHBoxLayout(chat_wrap)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        chat_col = QWidget()
        chat_lay = QVBoxLayout(chat_col)
        chat_lay.setContentsMargins(16, 16, 16, 16)
        self._chat_panel = ChatPanel()
        chat_lay.addWidget(self._chat_panel)
        from conversation_sidebar import ConversationSidebar
        self._conv_sidebar = ConversationSidebar(self._chat_panel)
        body.addWidget(self._conv_sidebar)
        body.addWidget(chat_col, 1)

        # The window's edge strips show resize arrows; everything inside gets the
        # normal cursor explicitly -- otherwise it inherits the root's last arrow.
        chat_wrap.setCursor(Qt.CursorShape.ArrowCursor)
        vlay.addWidget(chat_wrap, 1)
        _footer = self._build_footer()
        _footer.setCursor(Qt.CursorShape.ArrowCursor)
        vlay.addWidget(_footer)

    def _build_center(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setContentsMargins(40, 0, 40, 0)
        col.setSpacing(20)

        glyph = QLabel("\U00013062")   # Anubis (Gardiner C6, jackal-headed god)
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Segoe UI (the app's base font) has no Egyptian Hieroglyphs glyphs,
        # and Qt doesn't auto-fall back to Segoe UI Historic (which does) --
        # confirmed by rendering it and getting a tofu box. See
        # _ensure_hieroglyph_font()/_hieroglyph_font() for the full story.
        _ensure_hieroglyph_font()
        glyph.setStyleSheet(
            f'color: {GOLD}; font-size: 48px; font-family: "Segoe UI Historic";'
        )
        col.addWidget(glyph)

        greet = QLabel(f"Welcome back, {self._username}.")
        greet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        greet.setStyleSheet(f"color: {SILVER}; font-size: 15px; font-weight: 600;")
        col.addWidget(greet)

        self._getting_started_btn = QPushButton("Getting Started")
        self._getting_started_btn.setFixedHeight(52)
        self._getting_started_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._getting_started_btn.setStyleSheet(f"""
            QPushButton {{
                background: #d4b04c; color: #17120a;
                font-size: 15px; font-weight: 600;
                border-radius: 8px; border: none;
            }}
            QPushButton:hover   {{ background: #e2c062; }}
            QPushButton:pressed {{ background: #b8963a; }}
            QPushButton:disabled {{ background: #1a1a2e; color: {SILV2}; }}
        """)
        self._getting_started_btn.clicked.connect(self._show_getting_started)
        col.addWidget(self._getting_started_btn)

        # ── Ollama banner (only when Ollama not detected) ──────────────────
        if not _is_ollama_installed():
            ollama_box = QWidget()
            ollama_box.setStyleSheet(
                "background: #1a1200; border: 1px solid #7a4d00; border-radius: 6px;"
            )
            ob_lay = QHBoxLayout(ollama_box)
            ob_lay.setContentsMargins(12, 8, 12, 8)
            ob_lay.setSpacing(10)

            warn_lbl = QLabel("⚠  Ollama not found — required for local AI")
            warn_lbl.setStyleSheet(
                "color: #e8a020; font-size: 11px; background: transparent; border: none;"
            )
            warn_lbl.setWordWrap(True)
            ob_lay.addWidget(warn_lbl, 1)

            self._ollama_btn = QPushButton("Set Up")
            self._ollama_btn.setFixedHeight(26)
            self._ollama_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._ollama_btn.setToolTip(
                "Download and run the official Ollama installer for Windows"
            )
            self._ollama_btn.setStyleSheet("""
                QPushButton {
                    background: #7a4d00; color: #ffe0a0;
                    font-size: 11px; font-weight: 600;
                    border: 1px solid #b07000; border-radius: 4px;
                    padding: 2px 10px;
                }
                QPushButton:hover   { background: #a06500; }
                QPushButton:pressed { background: #5a3a00; }
                QPushButton:disabled { color: #666; border-color: #444; }
            """)
            self._ollama_btn.clicked.connect(self._install_ollama)
            ob_lay.addWidget(self._ollama_btn)

            col.addWidget(ollama_box)

        _util_style = f"""
            QPushButton {{
                background: transparent; color: {SILV2};
                font-size: 11px; border: 1px solid {BORDER}; border-radius: 4px;
                padding: 2px 6px;
            }}
            QPushButton:hover {{ color: {GOLD}; border-color: {LGOLD}; }}
        """

        util_row = QHBoxLayout()
        util_row.setSpacing(8)

        sq_btn = QPushButton("Security Questions")
        sq_btn.setFixedHeight(28)
        sq_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sq_btn.setToolTip("Set up or update your password-recovery security questions")
        sq_btn.setStyleSheet(_util_style)
        sq_btn.clicked.connect(self._setup_sq)
        util_row.addWidget(sq_btn)

        self._upd_btn = QPushButton("Check for Updates")
        self._upd_btn.setFixedHeight(28)
        self._upd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upd_btn.setToolTip("Query GitHub for the latest Cursiv release")
        self._upd_btn.setStyleSheet(_util_style)
        self._upd_btn.clicked.connect(lambda: self._check_updates())
        util_row.addWidget(self._upd_btn)

        rep_btn = QPushButton("Report a Problem")
        rep_btn.setFixedHeight(28)
        rep_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rep_btn.setToolTip("Send Cursiv's error logs to Joshua (never chats, letters or keys)")
        rep_btn.setStyleSheet(_util_style)
        rep_btn.clicked.connect(lambda: self._send_problem_report())
        util_row.addWidget(rep_btn)

        col.addLayout(util_row)

        _codex_style = f"""
            QPushButton {{
                background: transparent; color: {GOLD};
                font-size: 11px; font-weight: 600;
                border: 1px solid {LGOLD}; border-radius: 4px;
                padding: 2px 6px;
            }}
            QPushButton:hover   {{ background: rgba(212,175,55,0.08); border-color: {GOLD}; }}
            QPushButton:pressed {{ background: rgba(212,175,55,0.15); }}
            QPushButton:disabled {{ color: {SILV2}; border-color: {BORDER}; }}
        """
        self._codex_dl_btn = QPushButton("Winkler-Codex Download")
        self._codex_dl_btn.setFixedHeight(28)
        self._codex_dl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._codex_dl_btn.setToolTip(
            "Download the offline Code Council models (qwen2.5-coder:14b + deepseek-coder-v2:16b)"
        )
        self._codex_dl_btn.setStyleSheet(_codex_style)
        self._codex_dl_btn.clicked.connect(self._download_codex_models)
        col.addWidget(self._codex_dl_btn)

        # ── Fleet strip (only when relay is configured) ───────────────────
        if _RELAY_URL and _FLEET_TOKEN:
            fleet_box = QWidget()
            fleet_box.setStyleSheet(
                "background: #0a0a1a; border: 1px solid #1a1a3a; border-radius: 6px;"
            )
            fleet_lay = QHBoxLayout(fleet_box)
            fleet_lay.setContentsMargins(12, 7, 12, 7)
            fleet_lay.setSpacing(10)

            self._fleet_lbl = QLabel("⬢  Fleet — connecting…")
            self._fleet_lbl.setStyleSheet(
                "color: #9a9586; font-size: 11px; background: transparent; border: none;"
            )
            fleet_lay.addWidget(self._fleet_lbl, 1)

            fleet_btn = QPushButton("View Fleet")
            fleet_btn.setFixedHeight(24)
            fleet_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            fleet_btn.setToolTip("Open the Fleet Dashboard — see all your machines")
            fleet_btn.setStyleSheet("""
                QPushButton {
                    background: #151821; color: #e6e2d8;
                    font-size: 10px; font-weight: 600;
                    border: 1px solid #262b38; border-radius: 4px;
                    padding: 1px 8px;
                }
                QPushButton:hover   { background: #1b1f2a; }
                QPushButton:pressed { background: #0a0a1a; }
            """)
            fleet_btn.clicked.connect(self._show_fleet)
            fleet_lay.addWidget(fleet_btn)
            col.addWidget(fleet_box)

        return col

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setFixedHeight(32)
        footer.setObjectName("footer")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer.setStyleSheet(f"#footer {{ background: {BG}; border-top: 1px solid {BORDER}; }}")
        row = QHBoxLayout(footer)
        row.setContentsMargins(16, 0, 16, 0)

        self._status_lbl = QLabel("Starting…")
        self._status_lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        row.addWidget(self._status_lbl)
        row.addStretch()

        ver = QLabel(f"Cursiv v{_CURRENT_VERSION}")
        ver.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        row.addWidget(ver)
        return footer

    # ── Getting Started ──────────────────────────────────────────────────

    def _show_getting_started(self):
        # Fired via QTimer.singleShot(1800, ...) on first run only; runs after
        # main.py's try/except has returned, so it must never raise.
        try:
            from nav_windows import WelcomeDialog
            dlg = WelcomeDialog(self, setup_needed=not _is_ollama_installed_quick())
            dlg.exec()
            if dlg.dont_show_again():
                _mark_getting_started_seen()
        except Exception as e:
            self._set_status(f"Getting Started dialog failed to open: {e}")

    def _set_status(self, msg: str):
        self._status_lbl.setText(msg)

    # ── Security questions setup ──────────────────────────────────────────

    def _setup_sq(self):
        try:
            from launcher.login_dialog import SecurityQSetupDialog
        except Exception:
            try:
                from login_dialog import SecurityQSetupDialog
            except Exception as exc:
                self._set_status(f"Cannot open security questions: {exc}")
                return
        dlg = SecurityQSetupDialog(self, username=self._username)      # the signed-in person's own
        dlg.exec()
        try:
            from cursiv_v215.guardian.security_questions import is_setup_complete
            if is_setup_complete(self._username):
                self._set_status("Security questions saved.")
            else:
                self._set_status("Security questions skipped.")
        except Exception:
            pass

    # ── Update checker ────────────────────────────────────────────────────

    def _check_updates(self, automatic: bool = False):
        """Manual (button/tray) or automatic (shortly after startup) update check.
        The automatic one stays silent unless a newer version actually exists."""
        self._update_check_auto = automatic
        if automatic and not _auto_update_check_on():
            return
        if not _net_allowed():
            if not automatic:
                self._set_status("Offline mode is on, so Cursiv won't contact GitHub. Type 'offline off' to check for updates.")
            return
        if not automatic:
            self._upd_btn.setEnabled(False)
            self._upd_btn.setText("Checking…")
            self._set_status("Querying GitHub for updates…")
        # Keep a reference -- the checker's signal object must outlive this call.
        self._update_checker = UpdateChecker(self._on_update_result)
        self._update_checker.check()

    def _on_update_result(self, result: dict):
        automatic = getattr(self, "_update_check_auto", False)
        self._upd_btn.setEnabled(True)
        self._upd_btn.setText("Check for Updates")
        if not result.get("ok"):
            if not automatic:
                self._set_status(f"Update check failed — {result.get('error', 'no internet?')}")
            return
        tag = result["tag"]
        if not _version_is_newer(tag, _CURRENT_VERSION):
            if not automatic:
                self._set_status(f"You're up to date  ({_CURRENT_VERSION})")
            return
        if os.environ.get("CURSIV_PORTABLE") == "1":
            # The installer would install onto this PC, not the USB.
            self._set_status(f"v{tag} is available — to update this USB, update Cursiv on your "
                             "computer, then use \"Make a Cursiv USB…\" again.")
            return
        self._set_status(f"Update available: v{tag}")
        if automatic and self.isHidden():
            self.showNormal()
        dlg = UpdateDialog(tag, result["body"], result["exe_url"], self, exe_size=result.get("exe_size", 0))
        dlg.exec()

    # ── llama3.1 model download ───────────────────────────────────────────

    def _download_llama_model(self, on_done: "Callable[[], None] | None" = None):
        """Model downloads happen in the Setup window (real progress, no console)."""
        self._open_setup()
        if on_done is not None:
            on_done()

    # ── Winkler-Codex model download ─────────────────────────────────────

    def _download_codex_models(self):
        """Coding models download in the Setup window (progress bar, no console)."""
        self._open_setup()

    # ── Ollama installer ──────────────────────────────────────────────────

    def _install_ollama(self):
        """Installing Ollama happens in the Setup window (real progress, no console)."""
        self._open_setup()

    def _toggle_sidebar(self):
        self._conv_sidebar.setVisible(not self._conv_sidebar.isVisible())

    def _toggle_maximized(self):
        if self.isFullScreen():
            self.showNormal()
        elif self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _confirm_leave(self) -> bool:
        """Ask to save an unsaved conversation. False = the user cancelled."""
        try:
            from conversation_sidebar import confirm_leave
            return confirm_leave(self, getattr(self, "_chat_panel", None))
        except Exception:
            return True

    def _request_quit(self):
        if self._confirm_leave():
            QApplication.quit()

    def _warm_local_model(self):
        """Load the local model before the first message (a cold load took ~100 s on
        small GPUs) -- only when it'll answer, i.e. no online AI keys are saved."""
        def work():
            try:
                from cursiv_v215.ui import chat_app as ca
                if any(ca._saved_key(f) for f in ("groq_key", "gemini_key", "anthropic_key", "api_key", "openai_key")):
                    return
                ca.warm_up_local()
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _phone_sync(self):
        def work():
            try:
                import phone_sync
                phone_sync.sync_once()
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _open_phone(self):
        try:
            from phone_link import PhoneDialog
            PhoneDialog(self).exec()
        except Exception as e:
            self._set_status(f"Phone window failed to open: {e}")

    def _open_memory(self):
        try:
            from memory_dialog import MemoryDialog
            MemoryDialog(self).exec()
        except Exception as e:
            self._set_status(f"Memory window failed to open: {e}")

    def _open_knowledge(self):
        try:
            from nav_windows import KnowledgeDialog
            KnowledgeDialog(self).exec()
        except Exception as e:
            self._set_status(f"Memory & Knowledge failed to open: {e}")

    def _open_field_notebook(self, photos=None):
        try:
            from field_notebook import FieldNotebookDialog
            from cursiv_v215.memory.semantic import current_person
            dlg = FieldNotebookDialog(self, observer=current_person().title())
            if photos:
                dlg.add_photos(photos)
            dlg.exec()
        except Exception as e:
            self._set_status(f"Field Notebook failed to open: {e}")

    def _open_tools(self):
        try:
            from nav_windows import ToolsDialog
            ToolsDialog(self).exec()
        except Exception as e:
            self._set_status(f"Tools failed to open: {e}")

    def _open_help(self):
        try:
            from nav_windows import HelpDialog
            HelpDialog(self).exec()
        except Exception as e:
            self._set_status(f"Help failed to open: {e}")

    # Tools buttons reach the chat panel's dialogs through the main window.
    def _open_postal_compose(self, hint: str = ""):
        self._chat_panel._open_postal_compose(hint)

    def _open_legacy_vault(self):
        self._chat_panel._open_legacy_vault()

    def _open_training_data(self):
        self._chat_panel._open_training_data()

    def _open_settings(self, section: str = ""):
        try:
            from settings_dialog import SettingsDialog
            dlg = SettingsDialog(self, section)
            panel = getattr(self, "_chat_panel", None)
            if panel is not None and hasattr(panel, "reload_keys"):
                dlg.keys_changed.connect(panel.reload_keys)
            dlg.exec()
        except Exception as e:
            self._set_status(f"Settings failed to open: {e}")

    def _send_problem_report(self, context: str = ""):
        from problem_report import open_report
        open_report(self, context)

    def _open_usb_maker(self):
        if sys.platform != "win32":
            QMessageBox.information(self, "Cursiv USB", "The Cursiv USB drive is Windows-only for now. "
                                    "On a Mac, install Cursiv from the .dmg on the download page.")
            return
        try:
            from usb_maker import UsbMakerDialog
            UsbMakerDialog(self).exec()
        except Exception as e:
            self._set_status(f"USB maker failed to open: {e}")

    def _open_setup(self):
        try:
            from setup_dialog import SetupDialog
            SetupDialog(self).exec()
        except Exception as e:
            self._set_status(f"Setup window failed to open: {e}")

    def _maybe_open_setup(self):
        """First launch / after install: if this computer can't run Cursiv
        locally yet, open Setup. The check can take a few seconds (it may start
        Ollama), so it runs off the UI thread."""
        if not hasattr(self, "_setup_signal"):
            from PyQt6.QtCore import QObject, pyqtSignal

            class _SetupSignal(QObject):
                needed = pyqtSignal()
            self._setup_signal = _SetupSignal()
            self._setup_signal.needed.connect(self._open_setup)

        def check():
            try:
                from setup_dialog import needs_setup
                if needs_setup():
                    self._setup_signal.needed.emit()
            except Exception:
                pass
        threading.Thread(target=check, daemon=True).start()

    # ── Fleet heartbeat + dashboard ───────────────────────────────────────

    def _start_fleet_heartbeat(self):
        self._send_heartbeat()          # immediate first ping
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _heartbeat_loop(self):
        while True:
            time.sleep(60)
            self._send_heartbeat()

    def _send_heartbeat(self):
        if not _RELAY_URL or not _FLEET_TOKEN:
            return
        status = "active"
        payload = json.dumps({
            "machine_id":   _MACHINE_ID,
            "machine_name": _MACHINE_NAME,
            "username":     self._username,
            "version":      _CURRENT_VERSION,
            "status":       status,
        }).encode()
        try:
            req = urllib.request.Request(
                f"{_RELAY_URL}/remote/heartbeat",
                data=payload,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Fleet-Token": _FLEET_TOKEN,
                },
            )
            urllib.request.urlopen(req, timeout=8)
            QTimer.singleShot(0, self._fleet_ping_ok)
        except Exception:
            pass

    def _fleet_ping_ok(self):
        if hasattr(self, "_fleet_lbl"):
            self._fleet_lbl.setText("⬢  Fleet — this machine online")
            self._fleet_lbl.setStyleSheet(
                "color: #44cc66; font-size: 11px; background: transparent; border: none;"
            )

    def _show_fleet(self):
        dlg = FleetDialog(self)
        dlg.exec()

    # ── Tray ──────────────────────────────────────────────────────────────

    def _build_tray(self):
        self._tray = QSystemTrayIcon(self._make_icon(), self)
        self._tray.setToolTip("Cursiv")
        self._tray.activated.connect(
            lambda r: self._show()
            if r == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )

        menu = QMenu()
        menu.setStyleSheet(QSS)

        open_act = QAction("Open Cursiv", self)
        open_act.triggered.connect(self._show)
        menu.addAction(open_act)

        menu.addSeparator()
        gs_act = QAction("Getting Started", self)
        gs_act.triggered.connect(self._show_getting_started)
        menu.addAction(gs_act)

        memory_act = QAction("What I remember…", self)
        memory_act.triggered.connect(lambda: self._open_memory())
        menu.addAction(memory_act)

        phone_act = QAction("Phone…", self)
        phone_act.triggered.connect(lambda: self._open_phone())
        menu.addAction(phone_act)

        setup_act = QAction("Setup…", self)
        setup_act.triggered.connect(self._open_setup)
        menu.addAction(setup_act)

        if sys.platform == "win32":              # the USB edition is Windows-only for now
            usb_act = QAction("Make a Cursiv USB…", self)
            usb_act.triggered.connect(lambda: self._open_usb_maker())
            menu.addAction(usb_act)

        report_act = QAction("Send problem report…", self)
        report_act.triggered.connect(lambda: self._send_problem_report())
        menu.addAction(report_act)

        menu.addSeparator()
        sq_act = QAction("Security Questions", self)
        sq_act.triggered.connect(self._setup_sq)
        menu.addAction(sq_act)

        upd_act = QAction("Check for Updates", self)
        upd_act.triggered.connect(lambda: self._check_updates())
        menu.addAction(upd_act)

        if _RELAY_URL and _FLEET_TOKEN:
            fleet_act = QAction("⬢  Fleet Dashboard", self)
            fleet_act.triggered.connect(self._show_fleet)
            menu.addAction(fleet_act)

        menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(lambda: self._request_quit())
        menu.addAction(quit_act)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def _make_icon(self) -> QIcon:
        for name in ("cursiv.ico", "tray.ico", "cursiv.png"):
            p = _ICONS / name
            if p.exists():
                return QIcon(str(p))
        pix = QPixmap(32, 32)
        pix.fill(QColor(BG2))
        painter = QPainter(pix)
        painter.setPen(QColor(GOLD))
        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "✦")
        painter.end()
        return QIcon(pix)

    def _show(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        self._tray.showMessage(
            "Cursiv",
            "Running in the tray. Right-click to open.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

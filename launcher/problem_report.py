"""
"Send problem report" -- lets a user send Cursiv's error logs to the owner.

Collects version/system info and the tail of Cursiv's own log files, scrubs
anything that looks like a key, token, email address or the Windows user name,
shows the user exactly what will be sent, and posts it to the owner's
Cloudflare site (POST /api/report). Never sends chats, letters, memory or keys.
The user gets a short report ID to pass on.
"""
from __future__ import annotations

import json
import os
import platform
import re
import sys
import threading
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextEdit, QVBoxLayout,
)
from theme import BG, BG2, BORDER, GOLD, SILVER, SILV2, RED, GREEN  # one palette for every window (theme.py)

REPORT_URL = os.environ.get("CURSIV_REPORT_URL", "https://cursiv.us/api/report")
HOME_DATA = Path.home() / ".cursiv"


_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\bxai-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\bAIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bAQ\.?[A-Za-z0-9_\-]{20,}"),          # newer Gemini keys
    re.compile(r"\bgsk_[A-Za-z0-9]{12,}"),
    re.compile(r"\b(?:rk|sk|pk)_(?:live|test)_[A-Za-z0-9]{12,}"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}"),   # JWTs
    re.compile(r"(?i)\b(bearer|token|api[_-]?key|password|secret)(\s*[:=]\s*|\s+)\S{6,}"),
]
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def scrub(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[removed]", text)
    text = _EMAIL.sub("[email]", text)
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if len(user) >= 2:
        text = re.sub(re.escape(user), "<user>", text, flags=re.IGNORECASE)
    return text


def _tail(path: Path, lines: int) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(data[-lines:])
    except Exception as exc:
        return f"(could not read: {exc})"


def _version() -> str:
    try:
        from cursiv_launcher import _CURRENT_VERSION
        return _CURRENT_VERSION
    except Exception:
        return "unknown"


def _install_id() -> str:
    try:
        return json.loads((HOME_DATA / "cursiv_cloud.json").read_text(encoding="utf-8")).get("install_id", "")
    except Exception:
        return ""


def collect(context: str = "") -> dict:
    """Everything a report would contain, already scrubbed."""
    info = [
        f"Cursiv version:   {_version()}",
        f"Installed app:    {bool(getattr(sys, 'frozen', False))}",
        f"Windows:          {platform.platform()}",
        f"Python:           {platform.python_version()}",
    ]
    try:
        import setup_dialog as sd
        running = sd.ollama_running()
        info += [f"Ollama installed: {sd.ollama_installed()}",
                 f"Ollama running:   {running}",
                 f"Models:           {', '.join(sd.installed_models()) if running else '-'}"]
    except Exception as exc:
        info.append(f"Ollama check failed: {exc}")
    try:
        from cursiv_engine.ui import chat_app as ca
        cfg = {}
        try:
            from cursiv_engine.chat.keys import KEYS_FILE
            cfg = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        have = [name for name, field in (("xAI", "api_key"), ("OpenAI", "openai_key"), ("Claude", "anthropic_key"),
                                         ("Gemini", "gemini_key"), ("Groq", "groq_key")) if cfg.get(field)]
        info.append(f"Providers set up: {', '.join(have) or 'none'}   (keys are never sent)")
        info.append(f"Cursiv Cloud on:  {ca.cloud_enabled()}")
    except Exception as exc:
        info.append(f"Chat core check failed: {exc}")
    try:
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in HOME_DATA.iterdir())
        info.append(f"Data folder:      {', '.join(names)}")
    except Exception:
        pass

    logs = []
    crash = HOME_DATA / "crash.log"
    if crash.exists():
        logs.append(f"===== crash.log (last 300 lines) =====\n{_tail(crash, 300)}")
    for log in sorted((HOME_DATA / "logs").glob("*.log")) if (HOME_DATA / "logs").exists() else []:
        logs.append(f"===== logs/{log.name} (last 150 lines) =====\n{_tail(log, 150)}")
    if not logs:
        logs.append("(no log files found)")

    body = "\n".join(info) + ("\n\nWhat was on screen:\n" + context if context else "") + "\n\n" + "\n\n".join(logs)
    return {"install_id": _install_id(), "version": _version(), "os": platform.platform(),
            "logs": scrub(body)[-190000:]}


def send(report: dict, note: str) -> str:
    """Posts the report; returns its ID. Raises on failure."""
    payload = dict(report, note=scrub(note.strip())[:4000])
    req = urllib.request.Request(REPORT_URL, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "User-Agent": "Cursiv-Desktop"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))["id"]
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            detail = ""
        raise RuntimeError(detail or f"the server answered {e.code}") from None


class _Signals(QObject):
    done = pyqtSignal(bool, str)


class ProblemReportDialog(QDialog):
    def __init__(self, parent=None, context: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Send Problem Report")
        self.setMinimumWidth(640)
        self.resize(720, 640)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel {{ color: {SILVER}; background: transparent; }}
            QPlainTextEdit, QTextEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};
                                         border-radius: 4px; font-family: Consolas, monospace; font-size: 11px; }}
            QPushButton {{ background: #d4b04c; color: #17120a; border: none; border-radius: 4px; padding: 6px 16px; font-weight: 600; }}
            QPushButton:disabled {{ background: #2a2a3f; color: #777; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
        """)
        self._report = collect(context)
        self._sig = _Signals()
        self._sig.done.connect(self._on_done)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)
        t = QLabel("Send a problem report to Joshua")
        t.setStyleSheet(f"color: {GOLD}; font-size: 15px; font-weight: 700;")
        lay.addWidget(t)
        sub = QLabel("This sends Cursiv's version, basic system info and its error logs so the problem can be "
                     "fixed. It never sends your chats, letters, memory or keys. Here is exactly what will be sent:")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        lay.addWidget(sub)
        preview = QPlainTextEdit(self._report["logs"])
        preview.setReadOnly(True)
        preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        preview.setMinimumHeight(220)
        lay.addWidget(preview, 1)
        lay.addWidget(QLabel("What happened? (optional)"))
        self._note = QTextEdit()
        self._note.setPlaceholderText("e.g. a box about the guardian popped up when I clicked Create Account")
        self._note.setFixedHeight(70)
        self._note.setStyleSheet(self._note.styleSheet() + "font-family: 'Segoe UI'; font-size: 12px;")
        lay.addWidget(self._note)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self._status)
        row = QHBoxLayout()
        row.addStretch()
        self._copy = QPushButton("Copy ID")
        self._copy.setObjectName("ghost")
        self._copy.setVisible(False)
        row.addWidget(self._copy)
        self._cancel = QPushButton("Cancel")
        self._cancel.setObjectName("ghost")
        self._cancel.clicked.connect(self.reject)
        row.addWidget(self._cancel)
        self._send = QPushButton("Send report")
        self._send.clicked.connect(self._do_send)
        row.addWidget(self._send)
        lay.addLayout(row)

    def _do_send(self):
        self._send.setEnabled(False)
        self._status.setStyleSheet(f"color: {SILV2};")
        self._status.setText("Sending…")
        note = self._note.toPlainText()

        def work():
            try:
                self._sig.done.emit(True, send(self._report, note))
            except Exception as exc:
                self._sig.done.emit(False, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def _on_done(self, ok: bool, info: str):
        if not ok:
            self._status.setStyleSheet(f"color: {RED};")
            self._status.setText(f"Couldn't send the report: {info}. Check the internet connection and try again.")
            self._send.setEnabled(True)
            return
        self._status.setStyleSheet(f"color: {GREEN}; font-size: 13px; font-weight: 700;")
        self._status.setText(f"Sent. Report ID: {info}  — tell Joshua this code.")
        self._copy.setVisible(True)
        self._copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(info))
        self._send.setVisible(False)
        self._cancel.setText("Close")


def open_report(parent=None, context: str = "") -> None:
    try:
        ProblemReportDialog(parent, context).exec()
    except Exception:
        pass

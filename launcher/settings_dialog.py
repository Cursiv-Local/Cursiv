"""
Cursiv Settings -- every AI key in one place, plus Cursiv Cloud and the data folder.

Each key row: masked field with Show, Save (tests the key first; only a key
that works is saved), Remove, and a status line. Keys live in the same
config.json the rest of Cursiv reads. Opened from the gear in the title bar.
"""
from __future__ import annotations

import json
import os
import threading
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

BG, BG2, BORDER = "#0b0b12", "#13131e", "#2a2a3f"
GOLD, SILVER, SILV2, GREEN, RED, AMBER = "#FFD700", "#C8C8D4", "#666680", "#3ecf6e", "#FF4455", "#e8a020"

# (label, config field, free?, where to get a key)
PROVIDERS = [
    ("xAI Grok",        "api_key",       False, "https://console.x.ai"),
    ("OpenAI",          "openai_key",    False, "https://platform.openai.com/api-keys"),
    ("Claude",          "anthropic_key", False, "https://console.anthropic.com/settings/keys"),
    ("Google Gemini",   "gemini_key",    True,  "https://aistudio.google.com/apikey"),
    ("Groq",            "groq_key",      True,  "https://console.groq.com/keys"),
]


def _keys_file() -> Path:
    from cursiv_v215.chat import keys
    return keys.KEYS_FILE


def load_keys() -> dict:
    try:
        from cursiv_v215.core import keystore
        return keystore.reveal_all(json.loads(_keys_file().read_text(encoding="utf-8")))
    except Exception:
        return {}


def test_key(field: str, key: str) -> tuple[bool, str]:
    """Live test call. Returns (works, message)."""
    try:
        if field in ("gemini_key", "groq_key"):
            from cursiv_v215.ui import chat_app as ca
            return ca.check_free_key(field, key)
        from cursiv_v215.chat import keys
        probe = {"api_key": keys.probe_xai, "openai_key": keys.probe_openai, "anthropic_key": keys.probe_claude}[field]
        ok = bool(probe(key))
        return ok, "Working." if ok else "The provider rejected this key, or couldn't be reached."
    except Exception as exc:
        return False, f"Test failed: {exc}"


class _Signals(QObject):
    tested = pyqtSignal(str, bool, str, str)   # field, ok, message, key


class SettingsDialog(QDialog):
    keys_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Settings")
        self.setMinimumWidth(760)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel {{ color: {SILVER}; background: transparent; }}
            QFrame#card {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px; }}
            QLineEdit {{ background: {BG}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 4px;
                         padding: 5px 7px; font-family: Consolas, monospace; }}
            QPushButton {{ background: #2255DD; color: #fff; border: none; border-radius: 4px; padding: 5px 12px; font-weight: 600; }}
            QPushButton:disabled {{ background: #2a2a3f; color: #777; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
            QPushButton#link {{ background: transparent; color: #6f9bff; border: none; font-weight: 400; padding: 2px 4px; }}
            QCheckBox {{ color: {SILVER}; }}
        """)
        self._sig = _Signals()
        self._sig.tested.connect(self._on_tested)
        self._rows: dict[str, dict] = {}
        keys = load_keys()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        title = QLabel("Settings")
        title.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: 700;")
        lay.addWidget(title)

        # ── Keys ──
        card = QFrame(); card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        head = QLabel("AI keys  —  optional. Cursiv runs on your own computer without any of these. "
                      "Keys are saved only on this computer.")
        head.setWordWrap(True)
        head.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        grid.addWidget(head, 0, 0, 1, 6)
        r = 1
        for label, field, free, url in PROVIDERS:
            name = QLabel(label + ("  ·  free" if free else ""))
            name.setStyleSheet("font-weight: 600;" + (f" color: {GREEN};" if free else ""))
            name.setMinimumWidth(130)
            edit = QLineEdit(keys.get(field, ""))
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setPlaceholderText("not set")
            show = QPushButton("Show"); show.setObjectName("ghost"); show.setFixedWidth(58)
            save = QPushButton("Save"); save.setFixedWidth(64)
            remove = QPushButton("Remove"); remove.setObjectName("ghost"); remove.setFixedWidth(70)
            get = QPushButton("Get a key ↗"); get.setObjectName("link")
            status = QLabel("")
            status.setWordWrap(True)
            status.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
            grid.addWidget(name, r, 0)
            grid.addWidget(edit, r, 1)
            grid.addWidget(show, r, 2)
            grid.addWidget(save, r, 3)
            grid.addWidget(remove, r, 4)
            grid.addWidget(get, r, 5)
            grid.addWidget(status, r + 1, 1, 1, 5)
            grid.setColumnStretch(1, 1)
            row = {"edit": edit, "show": show, "save": save, "remove": remove, "status": status, "label": label}
            self._rows[field] = row
            show.clicked.connect(lambda _=False, rw=row: self._toggle_show(rw))
            save.clicked.connect(lambda _=False, f=field: self._save(f))
            remove.clicked.connect(lambda _=False, f=field: self._remove(f))
            get.clicked.connect(lambda _=False, u=url: webbrowser.open(u))
            self._set_status(field, None, "Saved." if keys.get(field) else "")
            r += 2
        lay.addWidget(card)

        # ── Cursiv Cloud ──
        cloud_card = QFrame(); cloud_card.setObjectName("card")
        cv = QVBoxLayout(cloud_card)
        cv.setContentsMargins(14, 10, 14, 10)
        self._cloud = QCheckBox("Cursiv Cloud — free backup AI, used only when no local model is ready")
        cv.addWidget(self._cloud)
        note = QLabel("When it's used, your message is sent to cursiv.winklers-llc.com. Turn it off to keep "
                      "everything on this computer.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        cv.addWidget(note)
        try:
            from cursiv_v215.ui.chat_app import cloud_enabled, set_cloud_enabled
            self._cloud.setChecked(cloud_enabled())
            self._cloud.toggled.connect(set_cloud_enabled)
        except Exception:
            self._cloud.setEnabled(False)
        lay.addWidget(cloud_card)

        # ── Internet (core/netgate.py) ──
        net_card = QFrame(); net_card.setObjectName("card")
        nv = QVBoxLayout(net_card)
        nv.setContentsMargins(14, 10, 14, 10)
        net_rows = (
            ("offline_mode", "Offline mode — nothing leaves this computer (cloud AI, web search, updates, downloads)"),
            ("web_search_auto", "Search the web automatically when a question sounds current (\"today\", \"right now\")"),
            ("update_check_auto", "Check for updates automatically after login"),
        )
        try:
            from cursiv_v215.core import netgate
            for name, label in net_rows:
                box = QCheckBox(label)
                box.setChecked(netgate.setting(name))
                box.toggled.connect(lambda on, n=name: netgate.set_setting(n, on))
                nv.addWidget(box)
        except Exception:
            nv.addWidget(QLabel("Internet settings are unavailable."))
        net_note = QLabel("Web search and update checks are off unless you turn them on. A message that starts "
                          "with \"search:\" always searches (unless offline mode is on). The Check for Updates "
                          "button works either way.")
        net_note.setWordWrap(True)
        net_note.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        nv.addWidget(net_note)
        lay.addWidget(net_card)

        # ── Data folder ──
        data_row = QHBoxLayout()
        data_dir = Path.home() / ".cursiv"
        dl = QLabel(f"Your data (memory, chats, settings): {data_dir}")
        dl.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        data_row.addWidget(dl, 1)
        mem_btn = QPushButton("What I remember…"); mem_btn.setObjectName("ghost")
        mem_btn.clicked.connect(self._open_memory)
        data_row.addWidget(mem_btn)
        open_btn = QPushButton("Open folder"); open_btn.setObjectName("ghost")
        open_btn.clicked.connect(lambda: os.startfile(str(data_dir)) if data_dir.exists() else None)
        data_row.addWidget(open_btn)
        done = QPushButton("Done")
        done.clicked.connect(self.accept)
        data_row.addWidget(done)
        lay.addLayout(data_row)

    def _open_memory(self):
        try:
            from memory_dialog import MemoryDialog
            MemoryDialog(self).exec()
        except Exception:
            pass

    # ── Actions ──
    def _set_status(self, field: str, ok: bool | None, text: str):
        st = self._rows[field]["status"]
        color = GREEN if ok else (RED if ok is False else SILV2)
        st.setStyleSheet(f"color: {color}; font-size: 11px;")
        st.setText(text)

    def _toggle_show(self, row: dict):
        hidden = row["edit"].echoMode() == QLineEdit.EchoMode.Password
        row["edit"].setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
        row["show"].setText("Hide" if hidden else "Show")

    def _save(self, field: str):
        row = self._rows[field]
        key = row["edit"].text().strip()
        if not key:
            self._set_status(field, False, "Paste a key first.")
            return
        row["save"].setEnabled(False)
        self._set_status(field, None, "Testing…")

        def work():
            ok, msg = test_key(field, key)
            self._sig.tested.emit(field, ok, msg, key)
        threading.Thread(target=work, daemon=True).start()

    def _on_tested(self, field: str, ok: bool, msg: str, key: str):
        row = self._rows[field]
        row["save"].setEnabled(True)
        if not ok:
            self._set_status(field, False, f"Not saved — {msg}")
            return
        from cursiv_v215.ui.chat_app import _store_key
        _store_key(field, key)
        self._set_status(field, True, "Saved and working.")
        self.keys_changed.emit()

    def _remove(self, field: str):
        from cursiv_v215.ui.chat_app import _store_key
        _store_key(field, "")
        self._rows[field]["edit"].clear()
        self._set_status(field, None, "Removed.")
        self.keys_changed.emit()

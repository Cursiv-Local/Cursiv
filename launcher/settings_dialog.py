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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)
import theme
from theme import BG, BG2, BORDER, GOLD, SILVER, SILV2, RED, GREEN, AMBER  # one palette for every window (theme.py)


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
    """One Settings window. Sections on the left; every control says in one
    plain sentence what it does. Only controls the app actually enforces."""
    keys_changed = pyqtSignal()

    SECTIONS = ("Privacy & internet", "AI model", "Online AI (optional)", "How Cursiv answers",
                "Updates", "Your data & account", "Help & diagnostics")

    def __init__(self, parent=None, section: str = ""):
        super().__init__(parent)
        self._win = parent
        self.setWindowTitle("Cursiv — Settings")
        self.resize(900, 600)
        self.setMinimumSize(760, 520)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel {{ color: {SILVER}; background: transparent; }}
            QLabel#title {{ font-size: 18px; font-weight: 650; }}
            QLabel#explain {{ color: {theme.MUTED}; font-size: 13px; }}
            QLabel#small {{ color: {SILV2}; font-size: 12px; }}
            QFrame#card {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 10px; }}
            QLineEdit {{ background: {BG}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 6px;
                         padding: 5px 7px; font-family: Consolas, monospace; }}
            QPushButton {{ background: {theme.ACCENT}; color: {theme.ACCENT_TEXT}; border: none; border-radius: 6px;
                           padding: 6px 14px; font-weight: 600; }}
            QPushButton:hover {{ background: {theme.ACCENT_HOVER}; }}
            QPushButton:disabled {{ background: {theme.SURFACE2}; color: {theme.FAINT}; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
            QPushButton#ghost:hover {{ background: {theme.SURFACE2}; }}
            QPushButton#link {{ background: transparent; color: {theme.LINK}; text-decoration: underline; border: none;
                                font-weight: 400; padding: 2px 4px; }}
            QCheckBox {{ color: {SILVER}; font-size: 14px; font-weight: 600; background: transparent; }}
            QListWidget#nav {{ background: {BG2}; border: none; border-right: 1px solid {BORDER}; padding: 8px; font-size: 14px; }}
            QListWidget#nav::item {{ padding: 9px 12px; border-radius: 6px; color: {theme.MUTED}; }}
            QListWidget#nav::item:selected {{ background: {theme.SURFACE2}; color: {theme.TEXT}; }}
            QListWidget#nav::item:hover {{ color: {theme.TEXT}; }}
        """)
        self._sig = _Signals()
        self._sig.tested.connect(self._on_tested)
        self._rows: dict[str, dict] = {}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._nav = QListWidget(); self._nav.setObjectName("nav"); self._nav.setFixedWidth(210)
        self._pages = QStackedWidget()
        outer.addWidget(self._nav)
        right = QVBoxLayout(); right.setContentsMargins(26, 22, 26, 18); right.setSpacing(14)
        right.addWidget(self._pages, 1)
        foot = QHBoxLayout(); foot.addStretch(1)
        done = QPushButton("Done"); done.clicked.connect(self.accept); foot.addWidget(done)
        right.addLayout(foot)
        outer.addLayout(right, 1)

        builders = (self._page_privacy, self._page_model, self._page_keys, self._page_answers,
                    self._page_updates, self._page_data, self._page_help)
        for name, build in zip(self.SECTIONS, builders):
            self._nav.addItem(name)
            page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(12)
            title = QLabel(name); title.setObjectName("title"); lay.addWidget(title)
            try:
                build(lay)
            except Exception as exc:
                lay.addWidget(self._explain(f"This section couldn't load: {exc}"))
            lay.addStretch(1)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(page)
            self._pages.addWidget(scroll)
        self._nav.currentRowChanged.connect(self._pages.setCurrentIndex)
        self._nav.setCurrentRow(self.SECTIONS.index(section) if section in self.SECTIONS else 0)

    # ── small helpers ──
    def _explain(self, text: str, name: str = "explain") -> QLabel:
        lbl = QLabel(text); lbl.setObjectName(name); lbl.setWordWrap(True)
        return lbl

    def _card(self, lay) -> QVBoxLayout:
        card = QFrame(); card.setObjectName("card")
        v = QVBoxLayout(card); v.setContentsMargins(16, 14, 16, 14); v.setSpacing(6)
        lay.addWidget(card)
        return v

    def _switch(self, lay, label: str, explain: str, value: bool, on_change) -> QCheckBox:
        v = self._card(lay)
        box = QCheckBox(label); box.setChecked(value); box.toggled.connect(on_change)
        v.addWidget(box)
        v.addWidget(self._explain(explain))
        return box

    def _action(self, lay, label: str, explain: str, handler, primary: bool = False) -> QPushButton:
        v = self._card(lay)
        row = QHBoxLayout()
        text = QVBoxLayout(); text.setSpacing(2)
        t = QLabel(label); t.setStyleSheet("font-size: 14px; font-weight: 600;"); text.addWidget(t)
        text.addWidget(self._explain(explain))
        row.addLayout(text, 1)
        btn = QPushButton("Open" if not primary else label.split(" ")[0])
        if not primary:
            btn.setObjectName("ghost")
        btn.clicked.connect(handler)
        row.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        v.addLayout(row)
        return btn

    def _call_window(self, name: str, *args):
        fn = getattr(self._win, name, None)
        if fn:
            fn(*args)

    # ── pages ──
    def _page_privacy(self, lay):
        from cursiv_v215.chat import status
        from cursiv_v215.core import netgate
        self._status_lbl = self._explain("")
        self._status_lbl.setStyleSheet("font-size: 14px;")
        lay.addWidget(self._status_lbl)
        self._refresh_status()

        def setting(name):
            def apply(on):
                netgate.set_setting(name, on)
                self._refresh_status()
            return apply
        self._switch(lay, "Offline mode",
                     "Nothing leaves this computer: no online AI, web search, updates or downloads. "
                     "Your local model, memory and reference keep working, and it stays on after a restart.",
                     netgate.setting("offline_mode"), setting("offline_mode"))
        self._switch(lay, "Search the web automatically",
                     "When a question sounds current (\"today\", \"right now\"), Cursiv sends it to DuckDuckGo. "
                     "Off means only messages you start with search: go online.",
                     netgate.setting("web_search_auto"), setting("web_search_auto"))
        try:
            from cursiv_v215.ui.chat_app import cloud_enabled, set_cloud_enabled

            def cloud(on):
                set_cloud_enabled(on)
                self._refresh_status()
            self._switch(lay, "Cursiv Cloud backup",
                         "Only when no local model is ready, your message goes to cursiv.winklers-llc.com for an answer. "
                         "Off keeps everything on this computer.",
                         cloud_enabled(), cloud)
        except Exception:
            pass

    def _refresh_status(self):
        try:
            from cursiv_v215.chat import status
            st = status.network_status()
            col = theme.GREEN if st["level"] in ("local", "offline") else theme.AMBER
            self._status_lbl.setText(f'<span style="color:{col}; font-weight:600;">● {st["label"]}</span>'
                                     f'<br><span style="color:{theme.MUTED};">{" ".join(st["details"])}</span>')
        except Exception:
            pass

    def _page_model(self, lay):
        from cursiv_v215.chat import status
        lay.addWidget(self._explain("Cursiv answers with an AI model that runs on this computer through Ollama. "
                                    "Automatic picks the best one your graphics card can run."))
        v = self._card(lay)
        v.addWidget(QLabel("Model"))
        self._model = QComboBox()
        models = status.local_models() or []
        if models:
            self._model.addItem(f"Automatic  ·  {status.automatic_model(models)}", "")
            for m in models:
                self._model.addItem(m, m)
            chosen = status.preferred_model()
            if chosen in models:
                self._model.setCurrentIndex(self._model.findData(chosen))
            self._model.activated.connect(lambda i: status.set_preferred_model(self._model.itemData(i) or ""))
        else:
            self._model.addItem("No local model found — Ollama may not be running", "")
            self._model.setEnabled(False)
        v.addWidget(self._model)
        v.addWidget(self._explain("Bigger models answer better but more slowly. The choice also shows above the chat."))
        self._action(lay, "Download or change models",
                     "Opens Setup, which installs Ollama and downloads models sized for your computer.",
                     lambda: self._call_window("_open_setup"))

    def _page_keys(self, lay):
        lay.addWidget(self._explain("Not needed: Cursiv works on this computer without any of these. A key is used only "
                                    "when the local model can't answer, or to read images, and then that message goes "
                                    "to that company. Keys are encrypted for your Windows account."))
        keys = load_keys()
        card = QFrame(); card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(14, 12, 14, 12)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        r = 0
        for label, field, free, url in PROVIDERS:
            name = QLabel(label + ("  ·  free" if free else ""))
            name.setStyleSheet("font-weight: 600;")
            name.setMinimumWidth(130)
            edit = QLineEdit(keys.get(field, ""))
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setPlaceholderText("not set")
            show = QPushButton("Show"); show.setObjectName("ghost"); show.setFixedWidth(58)
            save = QPushButton("Save"); save.setFixedWidth(64)
            remove = QPushButton("Remove"); remove.setObjectName("ghost"); remove.setFixedWidth(74)
            get = QPushButton("Get a key ↗"); get.setObjectName("link")
            st = QLabel(""); st.setWordWrap(True); st.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
            grid.addWidget(name, r, 0); grid.addWidget(edit, r, 1); grid.addWidget(show, r, 2)
            grid.addWidget(save, r, 3); grid.addWidget(remove, r, 4); grid.addWidget(get, r, 5)
            grid.addWidget(st, r + 1, 1, 1, 5)
            grid.setColumnStretch(1, 1)
            row = {"edit": edit, "show": show, "save": save, "remove": remove, "status": st, "label": label}
            self._rows[field] = row
            show.clicked.connect(lambda _=False, rw=row: self._toggle_show(rw))
            save.clicked.connect(lambda _=False, f=field: self._save(f))
            remove.clicked.connect(lambda _=False, f=field: self._remove(f))
            get.clicked.connect(lambda _=False, u=url: webbrowser.open(u))
            self._set_status(field, None, "Saved." if keys.get(field) else "")
            r += 2
        lay.addWidget(card)
        lay.addWidget(self._explain("Gemini and Groq have free keys that take about two minutes to get.", "small"))

    def _page_answers(self, lay):
        from cursiv_v215.core import style
        from cursiv_v215.memory import semantic
        person = semantic.current_person()
        v = self._card(lay)
        t = QLabel("Tone"); t.setStyleSheet("font-size: 14px; font-weight: 600;"); v.addWidget(t)
        self._tone = QComboBox()
        names = {"normal": "Normal", "warm": "Warm", "brief": "Brief", "blunt": "Blunt", "teacher": "Teacher",
                 "playful": "Playful", "legacy": "Family and legacy"}
        current = (style.load(person) or {}).get("tone", "normal") or "normal"
        for key in style.TONES:
            self._tone.addItem(names.get(key, key.title()), key)
        self._tone.setCurrentIndex(max(0, self._tone.findData(current)))
        self._tone.activated.connect(lambda i: style.set_tone(person, self._tone.itemData(i)))
        v.addWidget(self._tone)
        v.addWidget(self._explain("How Cursiv talks to you. Brief keeps answers short; Teacher explains step by step."))
        self._switch(lay, "Learn from our conversations",
                     "Cursiv picks out lasting facts about you (marked \"inferred\") so it can help better. "
                     "Off means it only remembers what you tell it with \"remember …\".",
                     semantic.learning_enabled(), semantic.set_learning)
        v = self._card(lay)
        t = QLabel("Answer checking"); t.setStyleSheet("font-size: 14px; font-weight: 600;"); v.addWidget(t)
        v.addWidget(self._explain("Always on. After an answer with numbers, advice or technical claims, Cursiv checks "
                                  "the numbers, named sources and assumptions, fixes the answer once if needed, and "
                                  "otherwise adds a short note. Small local models still make mistakes."))

    def _page_updates(self, lay):
        from cursiv_v215.core import netgate
        try:
            import cursiv_launcher
            version = cursiv_launcher._CURRENT_VERSION
        except Exception:
            version = "?"
        lay.addWidget(self._explain(f"This is Cursiv {version}."))
        self._action(lay, "Check for updates now",
                     "Asks GitHub whether a newer version exists. If it does, you'll see what's new and can install it.",
                     lambda: self._call_window("_check_updates"), primary=False)
        self._switch(lay, "Check automatically after login",
                     "Cursiv asks GitHub for a new version each time you log in. Nothing about you is sent.",
                     netgate.setting("update_check_auto"), lambda on: netgate.set_setting("update_check_auto", on))

    def _page_data(self, lay):
        data_dir = Path.home() / ".cursiv"
        self._action(lay, "What Cursiv remembers",
                     "See every saved memory, where it came from and when, and remove any of them.",
                     self._open_memory)
        self._action(lay, "Your data folder",
                     f"Memories, conversations and settings are ordinary files in {data_dir}. "
                     "Saved keys are encrypted; the rest isn't encrypted on disk.",
                     lambda: os.startfile(str(data_dir)) if data_dir.exists() else None)
        self._action(lay, "Security questions",
                     "Set the questions that let you reset a forgotten password.",
                     lambda: self._call_window("_setup_sq"))

    def _page_help(self, lay):
        self._action(lay, "Setup and engine",
                     "Check that Ollama and a model are installed, restart Ollama, or add optional models.",
                     lambda: self._call_window("_open_setup"))
        self._action(lay, "Send a problem report",
                     "Shows you exactly what will be sent (version and error logs, never chats or keys) before sending.",
                     lambda: self._call_window("_send_problem_report"))
        self._action(lay, "Commands and guides",
                     "Everything Cursiv can do, in plain language.",
                     lambda: self._call_window("_open_help"))

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

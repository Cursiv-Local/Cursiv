"""ChatControlsMixin: focused ChatPanel view methods.

Only the GUI thread calls these methods; background results arrive through
the panel signals. The host supplies transcript/widgets/config and callbacks.
No model, filesystem authorization or conversation-storage policy lives here.
"""
from __future__ import annotations
import threading
from pathlib import Path
import re as _re
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QTextBlockFormat, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPlainTextEdit,
    QPushButton, QLabel, QSizePolicy,
)
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2
import theme
from chat_rendering import MarkdownStream


class _ChatInput(QPlainTextEdit):
    """Enter sends, Shift+Enter inserts a newline -- standard chat-app behavior."""

    def __init__(self, on_send, on_paste_image, parent=None):
        super().__init__(parent)
        self._on_send = on_send
        self._on_paste_image = on_paste_image
        self.setFixedHeight(64)
        self.setPlaceholderText("Message Cursiv…   (Enter to send · Shift+Enter for a new line · help for commands)")
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid {theme.BORDER}; border-radius: 10px;
                padding: 9px 12px; font-size: 14px;
            }}
            QPlainTextEdit:focus {{ border-color: {theme.BORDER2}; }}
        """)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._on_send()
            return
        super().keyPressEvent(e)

    def insertFromMimeData(self, source) -> None:
        if source.hasImage() and self._on_paste_image(source.imageData()):
            return
        super().insertFromMimeData(source)


class ChatControlsMixin:
    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        # Model picker: which local model answers (Automatic = Cursiv picks for this computer).
        self._model_box = QComboBox()
        self._model_box.setToolTip("Standard for everyday questions; Deep Think takes longer and reasons first")
        self._model_box.setMinimumWidth(320)
        self._model_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._model_box.addItem("Looking for local models…", "")
        self._model_box.setEnabled(False)
        self._model_box.activated.connect(self._on_model_chosen)
        header_row.addWidget(self._model_box)
        header_row.addStretch(1)
        # Status pill: what can go online right now (core/netgate.py + keys + Cloud).
        self._net_pill = QPushButton("")
        self._net_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self._net_pill.clicked.connect(self._open_settings_from_pill)
        # While the field demo is on: the notebook and documents hold sample data (core/demo.py).
        self._demo_pill = QPushButton("SAMPLE DATA · demo on")
        self._demo_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self._demo_pill.setToolTip("The field notebook and documents hold the demo's sample data.\n"
                                   "Your real records are set aside. Click to see what to try; "
                                   "type 'demo off' to end it.")
        self._demo_pill.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {theme.AMBER}; border: 1px dashed {theme.AMBER};"
            f" border-radius: 13px; padding: 4px 12px; font-size: 12px; font-weight: 700; }}")
        self._demo_pill.clicked.connect(lambda: self._quick_send("demo questions"))
        self._demo_pill.setVisible(False)
        header_row.addWidget(self._demo_pill)
        header_row.addWidget(self._net_pill)
        # More: things that used to sit in the header (still reachable).
        more = QPushButton("⋯")
        more.setToolTip("More")
        more.setFixedSize(34, 30)
        more.setStyleSheet(theme.icon_button(30) + "QPushButton { font-size: 18px; }")
        more.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(more)
        try:
            from cursiv_v215.core import profile as _profile
            if _profile.personal():
                menu.addAction("Training data…", lambda: self._open_training_data())
        except Exception:
            pass
        menu.addAction("Settings…", self._open_settings_from_pill)
        menu.addAction("Help (commands)", lambda: self._quick_send("help"))
        menu.addAction("Field demo (sample data)", lambda: self._quick_send("demo"))
        menu.addAction("End the field demo", lambda: self._quick_send("demo off"))
        more.setMenu(menu)
        more.setStyleSheet(more.styleSheet() + "QPushButton::menu-indicator { image: none; width: 0; }")
        header_row.addWidget(more)
        lay.addLayout(header_row)
        self._signals.models.connect(self._on_models)
        self._signals.crosscheck.connect(self._on_cross_check)
        self._refresh_status_pill()
        self._load_models()
        self._pill_timer = QTimer(self)
        self._pill_timer.timeout.connect(self._refresh_status_pill)
        self._pill_timer.start(15_000)

        self._transcript = QTextBrowser()
        self._transcript.setOpenLinks(False)
        self._transcript.anchorClicked.connect(self._on_link)
        self._transcript.setStyleSheet(f"""
            QTextBrowser {{
                background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid {theme.BORDER}; border-radius: 12px;
                padding: 14px 18px; font-size: 14px;
            }}
        """)
        self._transcript.document().setDocumentMargin(6)
        self._transcript.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lay.addWidget(self._transcript, 1)

        row = QHBoxLayout()
        row.setSpacing(8)

        # Paperclip: add photos to a field entry, or ask the image model about a photo.
        self._clip_btn = QPushButton("📎")
        self._clip_btn.setFixedSize(44, 64)
        self._clip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clip_btn.setToolTip("Add photos to a field entry, or ask Cursiv about a photo")
        self._clip_btn.setStyleSheet(self._icon_btn_style() + "QPushButton { font-size: 20px; }"
                                     "QPushButton::menu-indicator { image: none; width: 0; }")
        clip_menu = QMenu(self._clip_btn)
        clip_menu.addAction("Add photos to a field entry…", self._clip_to_notebook)
        clip_menu.addAction("Ask Cursiv about a photo…", self._clip_ask)
        clip_menu.addSeparator()
        note = clip_menu.addAction("Making new images needs an online service (a paid OpenAI key or a free "
                                   "Cloudflare account); offline, Cursiv can only read photos.")
        note.setEnabled(False)
        self._clip_btn.setMenu(clip_menu)
        row.addWidget(self._clip_btn)

        self._input = _ChatInput(self._send, self._handle_pasted_image)
        row.addWidget(self._input, 1)

        self._voice_btn = QPushButton("Voice")
        self._voice_btn.setFixedSize(64, 64)
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_btn.setToolTip("Record 5s of audio and transcribe it into the input box")
        self._voice_btn.setStyleSheet(self._icon_btn_style())
        # clicked emits clicked(bool) -- a bare connect would bind that bool
        # to raw_text (same trap as the Getting Started download buttons),
        # so wrap it to call with no arguments and let the defaults apply.
        self._voice_btn.clicked.connect(lambda: self._start_voice())
        row.addWidget(self._voice_btn)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedSize(76, 64)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(theme.primary_button(10) + "QPushButton { font-size: 14px; }")
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._send_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedSize(56, 64)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setToolTip("Stop the current response and return to standby")
        self._stop_btn.setStyleSheet(theme.ghost_button(10) + f"QPushButton:enabled {{ color: {theme.RED}; }}")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        row.addWidget(self._stop_btn)

        # Cross-check (core/crosscheck.py): only on request, only after confirming what goes where
        self._cc_btn = QPushButton("Cross-\ncheck")
        self._cc_btn.setFixedSize(64, 64)
        self._cc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cc_btn.setToolTip("Ask another AI (with your own key) to review the last answer. You see exactly "
                                "what would be sent, and to whom, before anything leaves this computer.")
        self._cc_btn.setStyleSheet(self._icon_btn_style() + "QPushButton { font-size: 12px; }")
        self._cc_btn.setEnabled(False)
        self._cc_btn.clicked.connect(self._cross_check)
        row.addWidget(self._cc_btn)

        lay.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {theme.FAINT}; font-size: 12px;")
        lay.addWidget(self._status)

    def _icon_btn_style(self) -> str:
        return theme.ghost_button(10) + "QPushButton { font-size: 13px; padding: 0; }"

    _PILL = {"offline": (theme.GREEN, "rgba(111,211,155,0.10)"), "local": (theme.GREEN, "rgba(111,211,155,0.10)"),
             "online": (theme.AMBER, "rgba(232,180,90,0.10)")}

    def _refresh_status_pill(self) -> None:
        try:
            from cursiv_v215.chat import status as _st
            st = _st.network_status()
        except Exception:
            st = {"level": "online", "label": "Status unknown", "details": ["Couldn't read the network settings."]}
        fg, bg = self._PILL.get(st["level"], self._PILL["online"])
        self._net_pill.setText(f"●  {st['label']}")
        self._net_pill.setToolTip("\n".join(st["details"]) + "\n\nClick to change in Settings.")
        self._net_pill.setStyleSheet(
            f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {fg}55; border-radius: 13px;"
            f" padding: 4px 12px; font-size: 12px; font-weight: 600; }}"
            f"QPushButton:hover {{ border-color: {fg}; }}")
        self._net_status = st
        try:
            from cursiv_v215.core import demo as _demo
            self._demo_pill.setVisible(_demo.active())
        except Exception:
            self._demo_pill.setVisible(False)

    _PHOTO_FILTER = "Photos (*.jpg *.jpeg *.png *.heic *.heif *.webp *.tif *.tiff *.gif *.bmp)"

    def _clip_to_notebook(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(self, "Photos for a field entry", "", self._PHOTO_FILTER)
        if not files:
            return
        win = self.window()
        if hasattr(win, "_open_field_notebook"):
            win._open_field_notebook(photos=files)

    def _clip_ask(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        f, _ = QFileDialog.getOpenFileName(self, "A photo to ask about", "", self._PHOTO_FILTER)
        if f:
            self.prefill(f'photo "{f}" What does this photo show?')

    def _open_settings_from_pill(self) -> None:
        win = self.window()
        if hasattr(win, "_open_settings"):
            win._open_settings()
        self._refresh_status_pill()

    def _load_models(self) -> None:
        # The AI engine is started here, in the background, if it's installed but not running:
        # from a Cursiv USB it can take a minute or two (measured 46 s on a fast laptop), and
        # until then the menu says so instead of "Ollama isn't running".
        import os as _os
        portable = _os.environ.get("CURSIV_PORTABLE") == "1"
        self._model_box.clear()
        self._model_box.addItem("Starting the AI engine… (from a USB drive this can take a minute or two)"
                                if portable else "Looking for local models…", "")
        self._model_box.setEnabled(False)

        def work():
            try:
                from cursiv_v215.chat import status as _st
                models = _st.local_models()
                if models is None and _os.environ.get("CURSIV_NO_ENGINE_START") != "1":   # self-test, tests
                    from cursiv_v215.core import ollama_host, speed
                    if ollama_host.installed() and ollama_host.start(speed.ollama_env()):
                        models = _st.local_models()
                self._signals.models.emit(models)
            except Exception:
                self._signals.models.emit(None)
        threading.Thread(target=work, daemon=True).start()

    def _on_models(self, models) -> None:
        from cursiv_v215.chat import status as _st
        box = self._model_box
        box.clear()
        if not models:
            box.addItem("No local model yet — open Setup" if models == [] else
                        "The AI engine didn't start: type status for the reason", "")
            box.setEnabled(False)
            return
        for label, choice, enabled in _st.menu_choices(models):
            box.addItem(label, choice)
            box.model().item(box.count() - 1).setEnabled(enabled)
        box.setCurrentIndex(max(0, box.findData(_st.current_choice())))
        box.setEnabled(True)

    def _on_model_chosen(self, index: int) -> None:
        from cursiv_v215.chat import status as _st
        _st.choose(self._model_box.itemData(index) or "standard")

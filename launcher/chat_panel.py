"""
Cursiv — in-app chat panel.

Replaces the old terminal-spawned CLI with a real chat view living inside
the main Cursiv window. Plain messages go through the exact same core
chat() call the terminal CLI and web demo already use
(cursiv_v215/ui/chat_app.py); the terminal CLI's ~40 built-in commands
(key management, council, Babel, Codex, strand memory, blast, postal
letters, voice, etc.) are routed through chat_commands.py, which calls the
same underlying functions the CLI does. No subprocess, no console window
-- everything streams on a background thread and reaches the UI through
Qt signals, the only thread-safe way to touch widgets from another thread.

A handful of commands need a real dialog rather than a single line of text
(composing a sealed letter, the family Legacy Vault, board login/register,
voice recording, pasting a clipboard image) -- those are intercepted here,
on the main thread, before anything reaches the command router.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QTextBlockFormat, QTextCharFormat, QTextCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox, QMenu,
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPlainTextEdit,
    QPushButton, QLabel, QSizePolicy, QInputDialog, QLineEdit, QMessageBox,
)
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2  # one palette for every window (theme.py)
import theme
import re as _re


_HERE = Path(__file__).parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# chat_commands.py pulls in roughly a dozen cursiv_v215 subsystems (postal,
# family, voice, babel, council, strand memory, board client, obsidian,
# substrate...) that, before this chat panel existed, were only ever loaded
# by the terminal CLI running as its own separate process -- never by the
# main GUI's startup path. Importing it eagerly here would make the main
# window's very first paint depend on all of that succeeding (and being
# fast) every single time, with no way to show anything -- not even the
# window itself -- if one of them is slow or broken. It's loaded on a
# background thread instead (see ChatPanel._load_backend), so the window
# always appears immediately; chat is simply not sendable until it's ready.
cc = None            # type: ignore  -- set once the background load finishes
_CHAT_OK = False
_CHAT_IMPORT_ERROR = ""
_cursiv_chat = None
_CHAT_ROOT = _ROOT
_RATE_SENTINEL = object()

# ── Palette (matches cursiv_launcher.py exactly) ────────────────────────────


def _load_saved_keys() -> dict:
    import json
    try:
        from cursiv_v215.chat.keys import KEYS_FILE as keys_file     # the one settings file
        from cursiv_v215.core import keystore
        data = keystore.reveal_all(json.loads(keys_file.read_text(encoding="utf-8")))
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except Exception:
        return {}


def autosave_enabled() -> bool:
    """Conversations save themselves unless turned off in Settings → Your data & account."""
    try:
        from cursiv_v215.chat import keys
        return keys.saved_key("autosave_chats") != "off"
    except Exception:
        return True


def _iter_cancellable(gen, cancel_event: threading.Event):
    """Wraps a generator so the consuming loop can notice a Stop click
    between chunks. gen.close() (not just letting it fall out of scope)
    raises GeneratorExit inside the generator at its current yield point
    right away, so a well-structured provider call's `with` block around
    its HTTP connection unwinds and closes it promptly instead of on
    whenever GC gets to it."""
    while True:
        if cancel_event.is_set():
            gen.close()
            return
        try:
            chunk = next(gen)
        except StopIteration:
            return
        yield chunk


def _is_ollama_installed() -> bool:
    import os
    import shutil
    exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return bool(shutil.which("ollama")) or exe.exists()


class _ChatSignals(QObject):
    chunk = pyqtSignal(str)             # one streamed text fragment
    replace = pyqtSignal(str)           # the whole reply so far is replaced (a revised draft)
    done  = pyqtSignal()                # generation finished cleanly
    error = pyqtSignal(str)             # generation raised an exception
    cancelled = pyqtSignal()            # user hit Stop mid-generation
    image = pyqtSignal(str)             # a local image path to render inline
    voice_result = pyqtSignal(str, bool)   # transcribed text, auto_send
    pending_write = pyqtSignal(str)     # raw WRITE_SENTINEL JSON payload, needs approval
    write_complete = pyqtSignal(str)    # result text once an approved write finishes (or fails)
    backend_ready = pyqtSignal(bool, str)  # chat_commands finished loading: ok, error message
    models = pyqtSignal(object)         # installed Ollama chat models (list), or None if Ollama is down


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


class ChatPanel(QWidget):
    conversation_changed = pyqtSignal()     # saved / opened / new / renamed -> sidebar refresh
    """
    Self-contained chat view: transcript + input box, wired to the real
    chat() streaming core and the full command router. cfg/history persist
    for the life of the window (not saved across restarts in this pass).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = []          # [{"role": "user"|"assistant", "content": str}]
        self._conv_id: Optional[str] = None     # set once the user saves this conversation
        self._dirty = False                     # messages since the last save
        self._streaming = False
        self._backend_ready = False
        self._reply_text = ""
        self._pending_history_append: Optional[list[tuple[str, str]]] = None
        self._cancel_event: Optional[threading.Event] = None
        self._signals = _ChatSignals()
        self._signals.chunk.connect(self._on_chunk)
        self._signals.replace.connect(self._on_replace)
        self._signals.done.connect(self._on_done)
        self._signals.error.connect(self._on_error)
        self._signals.cancelled.connect(self._on_cancelled)
        self._signals.image.connect(self._on_image)
        self._signals.voice_result.connect(self._on_voice_result)
        self._signals.pending_write.connect(self._on_pending_write)
        self._signals.write_complete.connect(self._finish_pending_write)
        self._signals.backend_ready.connect(self._on_backend_ready)
        self._pending_write_context: dict = {}
        self._cfg: dict = {}

        self._build_ui()
        self._send_btn.setEnabled(False)
        self._voice_btn.setEnabled(False)
        self._append_system("Getting Cursiv ready…")

        # Deferred to the next event-loop tick (still the *main* thread) --
        # not a background thread. This was a background thread originally,
        # which fixed the window never appearing at all, but a real packaged
        # build then showed the window correctly and crashed/closed shortly
        # after -- almost certainly PyInstaller's frozen import machinery
        # (a custom importer + a global import lock) not being as
        # thread-safe as CPython's normal filesystem import path, something
        # dev-mode testing from source can't reproduce since it never goes
        # through that loader at all. QTimer.singleShot(0, ...) still lets
        # Qt paint the window before this runs (that's the actual fix for
        # "window never appears"), it just does the ~10s import on the UI
        # thread instead of a background one -- the UI is unresponsive for
        # that stretch instead of silently crashing, which is a straight
        # improvement even though it's not true async loading.
        QTimer.singleShot(0, self._load_backend)

    def _load_backend(self) -> None:
        try:
            import chat_commands as _cc_module  # noqa: F401
            self._on_backend_ready(True, "")
        except Exception as e:
            self._on_backend_ready(False, str(e))

    def _on_backend_ready(self, ok: bool, error: str) -> None:
        global cc, _CHAT_OK, _CHAT_IMPORT_ERROR, _cursiv_chat, _CHAT_ROOT, _RATE_SENTINEL
        if ok:
            import chat_commands as _cc_module   # already loaded -- instant, from sys.modules
            cc = _cc_module
            _CHAT_OK = True
            _cursiv_chat = cc._chat
            _CHAT_ROOT = cc._CHAT_ROOT
            _RATE_SENTINEL = cc.RATE_SENTINEL

            self._cfg = cc._default_cfg()
            keys = _load_saved_keys()
            self._cfg["api_key"] = keys.get("api_key", "")
            self._cfg["openai_key"] = keys.get("openai_key", "")
            self._cfg["anthropic_key"] = keys.get("anthropic_key", "")
            self._cfg["postal_user"] = "joshua"

            self._backend_ready = True
            self._send_btn.setEnabled(True)
            self._voice_btn.setEnabled(True)
            # Replace "Getting Cursiv ready…" with one line -- unless the
            # person already opened a saved conversation while it loaded.
            has_key = any(keys.get(k) for k in
                          ("api_key", "openai_key", "anthropic_key", "gemini_key", "groq_key"))
            if not self._history and not self._conv_id:
                self._show_empty_state(setup_needed=not (has_key or _is_ollama_installed()))
        else:
            _CHAT_IMPORT_ERROR = error
            self._append_system(
                f"Chat core failed to load: {error}\n"
                "This usually means a required package didn't install correctly."
            )

    # ── UI ────────────────────────────────────────────────────────────────

    # ── Saved conversations ──────────────────────────────────────────────
    def _after_turn(self) -> None:
        self._dirty = True
        if self._conv_id or autosave_enabled():    # new chats save themselves; saved ones stay current
            self.save_conversation()

    def has_unsaved(self) -> bool:
        return self._dirty and bool(self._history) and not self._conv_id

    def is_busy(self) -> bool:
        return self._streaming

    def current_conversation_id(self) -> Optional[str]:
        return self._conv_id

    def save_conversation(self, title: Optional[str] = None) -> Optional[str]:
        if not self._history:
            return None
        import conversations
        self._conv_id = conversations.save(self._conv_id, self._history, self._transcript.toHtml(), title,
                                           on_titled=self.conversation_changed.emit)   # AI title -> sidebar
        self._dirty = False
        self.conversation_changed.emit()
        return self._conv_id

    def new_conversation(self) -> None:
        self._transcript.clear()
        self._history = []
        self._conv_id = None
        self._dirty = False
        self._show_empty_state()
        self.conversation_changed.emit()

    # ── Empty state ─────────────────────────────────────────────────────

    # The research profile (core/profile.py, the default); EXAMPLES with personal features shown.
    FIELD_EXAMPLES = ("What is the distance and bearing from 44.1234, -71.5678 to 44.1371, -71.5512?",
                      "log site: North transect; water temp 12.40 C; pH 7.2; note: first visit",
                      "How much 1 M stock do I need to make 500 mL of 0.1 M solution?",
                      ("Try everything with sample data: demo", "demo"))
    EXAMPLES = ("How do I purify creek water so it's safe to drink?",
                "Help me plan meals for a week on a tight budget.",
                "Explain how a well pump works, simply.",
                "What should go in a 72-hour emergency kit for a family of four?")

    def _examples(self) -> tuple:
        try:
            from cursiv_v215.core import profile as _profile
            return self.EXAMPLES if _profile.personal() else self.FIELD_EXAMPLES
        except Exception:
            return self.FIELD_EXAMPLES

    def _show_empty_state(self, setup_needed: bool = False) -> None:
        """What a new chat looks like: a question, how Cursiv works in one line, examples to click."""
        from urllib.parse import quote
        if setup_needed:
            body = (f'<p style="color:{theme.AMBER};">Cursiv needs an AI model before it can answer.</p>'
                    f'<p><a href="cursiv://setup" style="color:{theme.ACCENT};">Open Setup</a>'
                    f'<span style="color:{theme.MUTED};"> to install the free local engine and a model sized for this '
                    f'computer, or add a free Gemini or Groq key in Settings.</span></p>')
        else:
            body = "".join(
                f'<p style="margin:6px 0;"><a href="cursiv://prompt/{quote(text)}" '
                f'style="color:{theme.TEXT}; text-decoration:none;">→&nbsp;&nbsp;{self._escape(label)}</a></p>'
                for label, text in ((e, e) if isinstance(e, str) else e for e in self._examples()))
        self._transcript.setHtml(theme.live(
            f'<div style="margin-top:40px;">'
            f'<p style="font-size:22px; font-weight:600; color:{theme.TEXT};">What can I help with?</p>'
            f'<p style="color:{theme.MUTED}; margin:6px 0 18px 0;">Cursiv answers with an AI model on this computer. '
            f'It can be wrong, so check anything that matters. Type <b>help</b> to see everything it can do.</p>'
            f'{body}</div>'))
        self._empty_shown = True

    def _clear_empty_state(self) -> None:
        if getattr(self, "_empty_shown", False):
            self._transcript.clear()
            self._empty_shown = False

    def _on_link(self, url) -> None:
        from urllib.parse import unquote
        if url.scheme() == "cursiv":
            if url.host() == "prompt":
                self.prefill(unquote(url.path().lstrip("/")))
            elif url.host() == "details":
                from PyQt6.QtWidgets import QMessageBox
                box = QMessageBox(self)
                box.setWindowTitle("Reasoning and checks")
                box.setTextFormat(Qt.TextFormat.MarkdownText)
                box.setText(unquote(url.path().lstrip("/")))
                box.exec()
            elif url.host() == "setup":
                win = self.window()
                if hasattr(win, "_open_setup"):
                    win._open_setup()
            return
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(url)

    def open_conversation(self, conv_id: str) -> bool:
        import conversations
        data = conversations.load(conv_id)
        if not data:
            return False
        self._transcript.setHtml(theme.to_current(data.get("html", "")))
        self._empty_shown = False
        self._history = list(data.get("messages", []))
        self._conv_id = conv_id
        self._dirty = False
        self._transcript.verticalScrollBar().setValue(self._transcript.verticalScrollBar().maximum())
        self.conversation_changed.emit()
        return True

    def reload_keys(self) -> None:
        """Pick up keys changed in Settings without restarting."""
        if not getattr(self, "_cfg", None):
            return
        keys = _load_saved_keys()
        for field in ("api_key", "openai_key", "anthropic_key"):
            self._cfg[field] = keys.get(field, "")

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

        lay.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {theme.FAINT}; font-size: 12px;")
        lay.addWidget(self._status)

    def _icon_btn_style(self) -> str:
        return theme.ghost_button(10) + "QPushButton { font-size: 13px; padding: 0; }"

    # ── Status pill and model picker ─────────────────────────────────────

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
        def work():
            try:
                from cursiv_v215.chat import status as _st
                self._signals.models.emit(_st.local_models())
            except Exception:
                self._signals.models.emit(None)
        threading.Thread(target=work, daemon=True).start()

    def _on_models(self, models) -> None:
        from cursiv_v215.chat import status as _st
        box = self._model_box
        box.clear()
        if not models:
            box.addItem("No local model yet — open Setup" if models == [] else "Ollama isn't running", "")
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

    def prefill(self, text: str) -> None:
        """Put a starting command in the input box (Tools buttons), cursor at the end."""
        self._input.setPlainText(text)
        cur = self._input.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        self._input.setTextCursor(cur)
        self._input.setFocus()

    def _quick_send(self, text: str) -> None:
        if self._streaming:
            return
        self._input.setPlainText(text)
        self._send()

    # ── Rendering a finished answer ─────────────────────────────────────

    _STATUS_LINE = _re.compile(r"^\s*\*([\[(])(.*)[\])]\*\s*$")
    _LEDGER_LINE = _re.compile(r"^[\s>*_-]*(Known|Inferred|Assumed|Unknown)[*_]*\s*:", _re.I)

    @classmethod
    def split_details(cls, body: list[str]) -> tuple[list[str], str]:
        """The answer, and what goes behind "Show reasoning and checks": the
        Known / Inferred / Assumed / Unknown lines and the check's notes. The
        answer and the reference card stay in view."""
        main, details = [], []
        notes_at = next((i for i, ln in enumerate(body)
                         if ln.strip().startswith("**Checked, with notes**")), None)
        if notes_at is not None:
            details.extend(ln for ln in body[notes_at:] if ln.strip())
            body = body[:notes_at]
            while body and body[-1].strip() in ("", "---"):
                body = body[:-1]
        ledger: list[str] = []
        try:
            # The same reader the check uses: "✅ Known:" and items on the lines below count too.
            from cursiv_v215.core import verify
            text = "\n".join(body)
            found = verify._ledger_span(text)
            if found:
                start, end, parts = found
                ledger = [f"{k}: {parts[k] or 'none'}" for k in ("Known", "Inferred", "Assumed", "Unknown")]
                body = (text[:start].rstrip() + "\n" + text[end:]).split("\n")
        except Exception:
            pass
        if not ledger:
            ledger = [ln.replace("**", "").strip().strip("*_-> ") for ln in body if cls._LEDGER_LINE.match(ln)]
            body = [ln for ln in body if not cls._LEDGER_LINE.match(ln)]
        main = list(body)
        while main and main[-1].strip() in ("", "---"):
            main.pop()
        if ledger:
            details = ["**What this answer is based on**", *("- " + ln for ln in ledger)] + (
                [""] + details if details else [])
        return main, "\n".join(details)

    def _chip_html(self, inner: str) -> str:
        """One of Cursiv's own status lines, as a small line under (or above) the answer."""
        esc = self._escape(inner)
        if inner.startswith("Answered by "):
            engine = inner[len("Answered by "):]
            local = engine.startswith(("Ollama", "Code Council", "Cursiv local"))
            col = theme.GREEN if local else theme.AMBER
            label = ("Local · " + self._escape(engine.split("·", 1)[-1].strip())) if local else ("Online · " + self._escape(engine))
            return f'<p style="margin:6px 0 0 0; font-size:12px; color:{col};">● {label}</p>'
        if inner.startswith("Cursiv's check:"):
            return f'<p style="margin:8px 0 0 0; font-size:13px; color:{theme.AMBER};">⚠ {esc}</p>'
        if inner.startswith("From Cursiv's offline reference"):
            urgent = "[medical/" in inner or "[survival/" in inner
            style = (f"font-size:13px; color:{theme.TEXT};" if urgent else f"font-size:12px; color:{theme.MUTED};")
            return (f'<table width="100%" cellpadding="10" cellspacing="0" style="margin:2px 0 10px 0;'
                    f' background-color:{theme.SURFACE2}; border:1px solid {theme.BORDER};"><tr><td>'
                    f'<span style="{style}">{esc}</span></td></tr></table>')
        return f'<p style="margin:4px 0; font-size:12px; color:{theme.MUTED};">{esc}</p>'

    @staticmethod
    def _keep_line_breaks(md: str) -> str:
        """In Markdown a single newline joins lines; the model's single newlines
        (Known: / Inferred: lines, addresses, short steps) are meant as line breaks."""
        out, in_code, under_item = [], False, False
        lines = md.split("\n")
        item = _re.compile(r"\s*([-*+]|\d+[.)])\s")
        for i, line in enumerate(lines):
            if line.lstrip().startswith("```"):
                in_code = not in_code
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if in_code or not line.strip():
                under_item = False if not line.strip() else under_item
                out.append(line)
                continue
            if item.match(line):
                under_item = False
                if nxt.strip() and not _re.match(r"\s*([-*+]|\d+[.)]|#|>|\|)", nxt):
                    # "1. Step\nWhat to do" — Qt numbers a line break inside an item as a new
                    # item (4 steps showed as 7), so the text under it becomes its own
                    # indented paragraph.
                    out += [line, ""]
                    under_item = True
                    continue
                out.append(line)
                continue
            if under_item:
                line = "   " + line.lstrip()
            if nxt.strip() and not line.endswith("  ") and not _re.match(r"\s*([-*+]|\d+[.)]|#|>|\|)", nxt):
                line += "  "
            out.append(line)
        return "\n".join(out)

    def _render_reply(self) -> None:
        """Swap the plain streamed text of a finished chat answer for rendered Markdown,
        with Cursiv's status lines as small chips. Only for chat answers: command output
        (help, status) keeps its plain, aligned text."""
        text = self._reply_text or ""
        start = getattr(self, "_reply_start", None)
        if start is None or not text.strip():
            return
        top, body, bottom = [], [], []
        for line in text.splitlines():
            m = self._STATUS_LINE.match(line)
            if m:
                (top if not body else bottom).append(m.group(2))
            else:
                body.append(line)
        body, details = self.split_details(body)
        md = self._keep_line_breaks("\n".join(body).strip())
        cursor = QTextCursor(self._transcript.document())
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        for inner in top:
            cursor.insertHtml(theme.live(self._chip_html(inner)))
        if md:
            if top:
                cursor.insertBlock()
            cursor.insertMarkdown(md)
        if details:
            from urllib.parse import quote
            self._plain_block(cursor)
            cursor.insertHtml(f'<p style="margin:6px 0 0 0; font-size:12px;"><a href="cursiv://details/'
                              f'{quote(details)}" style="color:{theme.MUTED};">Show reasoning and checks</a></p>')
        for inner in bottom:
            self._plain_block(cursor)
            cursor.insertHtml(theme.live(self._chip_html(inner)))
        self._plain_block(cursor)               # the next turn starts outside any list

    @staticmethod
    def _plain_block(cursor: QTextCursor) -> None:
        """A new block that isn't part of the list an answer may end with. Qt carries the
        list on, so the "Local" line became item 5 and the next "You" was indented."""
        cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())
        lst = cursor.currentList()
        if lst is not None:
            lst.remove(cursor.block())
        fmt = cursor.blockFormat()
        fmt.setIndent(0)
        cursor.setBlockFormat(fmt)

    # ── Transcript rendering ─────────────────────────────────────────────

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    def _force_new_block(self) -> None:
        # A fresh <p>...</p> fragment inserted via insertHtml() doesn't
        # reliably start a new QTextBlock when appended after existing
        # content -- Qt's rich text engine can merge it into the previous
        # block with a   line-separator standing in for the paragraph
        # break, which renders as glued onto the end of the last line
        # instead of a proper new block with its own margin. Every method
        # below that starts a new visual turn (system message, "You", a
        # fresh AI reply) calls this first; Qt's actual document-structure
        # API (insertBlock) doesn't have that ambiguity the way inserted
        # HTML fragments do.
        if self._transcript.document().isEmpty():
            return
        cursor = self._transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertBlock()
        self._transcript.setTextCursor(cursor)

    def _append_html_block(self, html: str) -> None:
        self._transcript.moveCursor(QTextCursor.MoveOperation.End)
        self._transcript.insertHtml(theme.live(html))
        self._transcript.moveCursor(QTextCursor.MoveOperation.End)

    def _append_system(self, text: str) -> None:
        self._force_new_block()
        self._append_html_block(
            f'<p style="color:{SILV2}; font-size:12px; margin:4px 0 12px 0;">{self._escape(text)}</p>'
        )

    def _append_user(self, text: str) -> None:
        self._force_new_block()
        self._append_html_block(
            f'<p style="margin:10px 0 4px 0;">'
            f'<span style="color:{theme.MUTED}; font-weight:600;">You</span><br>'
            f'<span style="color:{SILVER};">{self._keep_shape(text)}</span></p>'
        )

    @classmethod
    def _keep_shape(cls, text: str) -> str:
        """Escaped text that keeps its line breaks, indents and spacing, so a pasted
        list or table doesn't run together into one paragraph."""
        out = cls._escape(text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    "))
        out = out.replace("  ", "&nbsp; ")
        return out.replace("\n", "<br>")

    def _begin_ai_reply(self) -> None:
        # Opens a paragraph the streamed chunks get appended into; closed in _on_done.
        self._force_new_block()
        self._append_html_block(
            f'<p style="margin:4px 0 4px 0;">'
            f'<span style="color:{theme.ACCENT}; font-weight:600;">Cursiv</span><br>'
            f'<span style="color:{theme.TEXT}; white-space:pre-wrap;">'
        )
        cursor = QTextCursor(self._transcript.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._reply_start = cursor.position()

    def _at_bottom(self) -> bool:
        sb = self._transcript.verticalScrollBar()
        return sb.value() >= sb.maximum() - 4

    def _append_reply_chunk(self, chunk: str) -> None:
        # Streamed chunks come from the model, not markup -- insert as plain
        # text so partial HTML never lands mid-tag. Insert through a cursor
        # tied to the document, not the widget's own moveCursor/textCursor,
        # so a user who scrolled up mid-generation to reread earlier text
        # doesn't get yanked back to the bottom on every chunk -- only
        # auto-follow if they were already at the bottom.
        at_bottom = self._at_bottom()
        cursor = QTextCursor(self._transcript.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        if at_bottom:
            self._transcript.verticalScrollBar().setValue(self._transcript.verticalScrollBar().maximum())

    def _end_ai_reply(self) -> None:
        # Just closes the tags _begin_ai_reply opened, in the same block
        # as the streamed content -- the *next* turn's own method
        # (_append_system/_append_user/_begin_ai_reply) is what calls
        # _force_new_block(), so nothing extra is needed here.
        self._append_html_block("</span></p>")

    def _append_image(self, path: str) -> None:
        import base64
        try:
            data = Path(path).read_bytes()
        except Exception:
            return
        b64 = base64.b64encode(data).decode()
        ext = Path(path).suffix.lstrip(".").lower() or "png"
        self._append_html_block(
            f'<p style="margin:4px 0 12px 0;">'
            f'<img src="data:image/{ext};base64,{b64}" style="max-width:480px; border-radius:8px;" />'
            f'</p>'
        )

    # ── Sending ───────────────────────────────────────────────────────────

    def _send(self) -> None:
        if self._streaming:
            return
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._clear_empty_state()
        if not _CHAT_OK:
            self._append_system("Chat core isn't available -- see the message above.")
            return

        # "clear" wipes the on-screen transcript and in-memory history --
        # there's nothing for chat_commands.py (UI-agnostic, no widget
        # access) to do here, so it's handled directly on the main thread.
        if text.strip().lower() == "clear":
            self._input.clear()
            self.new_conversation()
            return

        # A handful of commands need a real dialog, not a single line of
        # text -- intercept them here on the main thread before anything
        # reaches the background-thread command router.
        if self._try_dialog_command(text):
            self._input.clear()
            return

        self._input.clear()
        self._append_user(text)
        self._begin_turn()

        # Snapshot deliberately excludes this turn -- built-in commands
        # (anchor this, etc.) inspect history for the *prior* exchange, and
        # the terminal CLI never adds command text to history at all, only
        # real chat turns. Whether/what to append is decided in _run_turn
        # once we know if this resolved to a command or a plain chat call.
        history_snapshot = list(self._history)
        thread = threading.Thread(
            target=self._run_turn, args=(text, history_snapshot), daemon=True,
        )
        thread.start()

    def _begin_turn(self) -> None:
        self._streaming = True
        self._cancel_event = threading.Event()
        self._send_btn.setEnabled(False)
        self._voice_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status.setText("Cursiv is thinking…")
        self._reply_text = ""
        self._reply_is_chat = False
        self._begin_ai_reply()

    def _stop_generation(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._stop_btn.setEnabled(False)
        self._status.setText("Stopping…")

    def _run_turn(self, text: str, history: list[dict]) -> None:
        try:
            force_provider, stripped = cc.hey_prefix(text)
            result = None
            if not force_provider:
                result = cc.handle_command(text, self._cfg, history)

            if result is not None:
                self._deliver_result(result, history, text)
                return

            # No built-in command matched (or a "hey <provider>" prefix
            # forced routing) -- fall through to the default streaming chat,
            # the same core the terminal CLI's plain-message path uses.
            # `history` here is the snapshot from *before* this turn, so it
            # goes straight to chat() -- which appends the current user
            # turn itself -- with nothing to trim off the end.
            workspace = self._cfg.get("workspace", str(_CHAT_ROOT))
            gen = _cursiv_chat(
                stripped, history,
                api_key=self._cfg.get("api_key", ""), files=None,
                file_access=self._cfg.get("file_access", False),
                root_path=workspace,
                openai_key=self._cfg.get("openai_key", ""),
                confirm_writes=(self._cfg.get("confirm_mode", "confirm") == "confirm"),
                anthropic_key=self._cfg.get("anthropic_key", ""),
                force_provider=force_provider,
                replace_draft=True,
            )
            self._cfg["last_user_msg"] = stripped
            self._reply_is_chat = True          # rendered as Markdown when it finishes
            cancel_event = self._cancel_event
            full = ""
            for chunk in _iter_cancellable(gen, cancel_event):
                if not chunk:
                    continue
                if cc.WRITE_SENTINEL in chunk:
                    # Last chunk chat() will ever yield for this turn (it
                    # returns right after) -- anything before the sentinel
                    # in this same chunk is still real preview text to show.
                    before, raw_json = chunk.split(cc.WRITE_SENTINEL, 1)
                    if before:
                        full += before
                        self._signals.chunk.emit(before)
                    self._pending_write_context = {
                        "full": full, "stripped": stripped, "workspace": workspace,
                    }
                    self._signals.pending_write.emit(raw_json)
                    return   # stays "streaming" (buttons disabled) until the
                             # approval dialog resolves on the main thread
                if chunk.startswith(cc.REPLACE_SENTINEL):
                    full = chunk[len(cc.REPLACE_SENTINEL):]   # history keeps only the final answer
                    self._signals.replace.emit(full)
                    continue
                full += chunk
                self._signals.chunk.emit(chunk)
            if cancel_event.is_set():
                self._pending_history_append = (
                    [("user", stripped), ("assistant", full)] if full else None
                )
                self._signals.cancelled.emit()
                return
            self._signals.done.emit()
            self._pending_history_append = [("user", stripped), ("assistant", full)]
        except Exception as e:
            self._signals.error.emit(str(e))

    def _deliver_result(self, result, history: list[dict], text: str = "") -> None:
        """Runs on the background thread -- streams a command's TextResult/StreamResult."""
        if isinstance(result, cc.TextResult):
            if result.text:
                self._signals.chunk.emit(result.text)
            if result.image_path:
                self._signals.image.emit(result.image_path)
            self._signals.done.emit()
            self._pending_history_append = None   # commands don't pollute chat history
            return

        # StreamResult
        self._signals.chunk.emit(result.intro + "\n\n")
        cancel_event = self._cancel_event
        full = ""
        rate_limited = False
        try:
            for chunk in _iter_cancellable(result.generator, cancel_event):
                if chunk == _RATE_SENTINEL:
                    rate_limited = True
                    continue
                if chunk:
                    full += chunk
                    self._signals.chunk.emit(chunk)
        except Exception as e:
            self._signals.error.emit(str(e))
            return
        if cancel_event.is_set():
            self._pending_history_append = None
            self._signals.cancelled.emit()
            return
        if not full:
            # The generator produced nothing displayable -- e.g. an
            # invalid/rejected API key, a real rate limit, or a network
            # failure that the provider call swallowed into an empty
            # response instead of raising. Previously this looked
            # identical to the intro line just... never getting an
            # answer, with no way to tell a real failure from something
            # being broken in the UI itself.
            self._signals.chunk.emit(
                "[Rate limited or no response — wait a moment and try again, "
                "or check that the API key is valid.]" if rate_limited else
                "[No response received from the provider.]"
            )
        # Streamed command answers (codex, council, search, babel, …) join the
        # conversation, so a follow-up like "done" or "now add a gripper" has context.
        if full.strip() and text:
            self._pending_history_append = [("user", text), ("assistant", full[-6000:])]
        if result.on_complete:
            try:
                result.on_complete(full)
            except Exception:
                pass
        self._signals.done.emit()
        self._pending_history_append = None

    # ── Signal handlers (run on the GUI thread) ─────────────────────────

    def _on_chunk(self, chunk: str) -> None:
        self._reply_text += chunk
        self._append_reply_chunk(chunk)

    def _on_replace(self, text: str) -> None:
        """Swap the streamed draft for the checked answer (same paragraph and style)."""
        start = getattr(self, "_reply_start", None)
        if start is None:
            self._append_reply_chunk("\n\n" + text)
            return
        cursor = QTextCursor(self._transcript.document())
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)            # replaces the selected draft
        self._reply_text = text

    def _on_image(self, path: str) -> None:
        self._append_image(path)

    def _on_done(self) -> None:
        if getattr(self, "_reply_is_chat", False):
            try:
                self._render_reply()
            except Exception:
                pass                     # the plain streamed text stays
        self._end_ai_reply()
        self._refresh_status_pill()      # "offline on", a new key, ... change it
        for role, content in (getattr(self, "_pending_history_append", None) or []):
            self._history.append({"role": role, "content": content})
        self._pending_history_append = None
        self._after_turn()
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.setText("")
        self._input.setFocus()

    def _on_cancelled(self) -> None:
        self._append_html_block(
            f'<span style="color:{SILV2}; font-style:italic;"> [Stopped]</span></p>'
        )
        for role, content in (getattr(self, "_pending_history_append", None) or []):
            self._history.append({"role": role, "content": content})
        self._pending_history_append = None
        self._after_turn()
        self._cancel_event = None
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.setText("")
        self._input.setFocus()

    def _on_error(self, message: str) -> None:
        self._append_html_block(
            f'<span style="color:#ff6666;">[Error: {self._escape(message)}]</span></p>'
        )
        # _pending_history_append is only ever set right before a clean
        # done.emit() (see _run_turn/_deliver_result), so an error here
        # means it's still None -- a failed generation never produced a
        # complete exchange, so nothing gets added to history.
        self._pending_history_append = None
        self._cancel_event = None
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.setText("")

    def _on_pending_write(self, raw_json: str) -> None:
        """
        file_access + "confirm" write mode: Cursiv wants to write a file and
        chat() paused mid-turn waiting for approval -- same gate the
        terminal CLI's _handle_pending_write() enforces, just as a dialog
        instead of a y/n prompt. Still "streaming" (buttons disabled) while
        this is open, matching the terminal blocking on the same decision.
        """
        import json
        try:
            pending = json.loads(raw_json)
        except Exception:
            self._finish_pending_write("[Could not parse pending write]")
            return

        path = pending.get("path", "?")
        content = pending.get("content", "")
        preview = content[:400] + ("..." if len(content) > 400 else "")
        approved = QMessageBox.question(
            self, "Cursiv — Write pending",
            f"Approve write to:\n{path}\n\n{preview}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes

        if not approved:
            self._finish_pending_write("Write cancelled — file not modified.")
            return

        self._status.setText("Writing file...")
        workspace = self._pending_write_context.get("workspace", str(_CHAT_ROOT))
        threading.Thread(
            target=self._run_write_approval, args=(path, content, workspace), daemon=True,
        ).start()

    def _run_write_approval(self, path: str, content: str, workspace: str) -> None:
        try:
            result = cc.approve_write(path, content, workspace)
            self._signals.write_complete.emit(result.text)
        except Exception as e:
            self._signals.write_complete.emit(f"[Write failed: {e}]")

    def _finish_pending_write(self, tail_text: str) -> None:
        full = self._pending_write_context.get("full", "")
        stripped = self._pending_write_context.get("stripped", "")
        if tail_text:
            self._append_reply_chunk(("\n\n" if full else "") + tail_text)
            full += ("\n\n" if full else "") + tail_text
        self._end_ai_reply()
        self._history.append({"role": "user", "content": stripped})
        self._history.append({"role": "assistant", "content": full})
        self._after_turn()
        self._pending_write_context = {}
        self._cancel_event = None
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.setText("")

    # ── Commands that need a real dialog ─────────────────────────────────

    def _try_dialog_command(self, text: str) -> bool:
        """Returns True if `text` was handled here (a dialog was shown)."""
        cmd = text.strip().lower()

        if cmd == "write to" or cmd.startswith("write to "):
            self._open_postal_compose(text[9:].strip())
            return True

        if cmd == "legacy" or cmd.startswith("legacy "):
            # "legacy import <path>" is a plain text command (handled by
            # chat_commands); bare "legacy"/"legacy <anything else>" opens
            # the vault dialog, matching the terminal's natural-language
            # gate but with real structured login fields instead.
            if cmd.startswith("legacy import "):
                return False
            self._open_legacy_vault()
            return True

        if cmd.startswith("babel i am ") or cmd.startswith("babel: i am "):
            # Family letter activation ("babel I am [Name] born [Date][, PIN]")
            # existed in the terminal CLI but was never ported to the GUI --
            # it fell through to plain "translate this to English" instead,
            # which is what a name+DOB *mismatch* is supposed to do (the CLI
            # deliberately doesn't reveal whether a guess was close), so only
            # intercept here once detect_family_member finds a real match.
            # A non-match returns False and falls through to chat_commands'
            # normal babel handler, unchanged -- same as a genuine guess.
            if self._try_family_activation(text):
                return True

        if cmd in ("voice", "listen") or cmd.startswith("voice ") or cmd.startswith("listen "):
            # Typed as a command (matching the terminal CLI exactly) --
            # auto-send the transcription, same as the CLI falling straight
            # through to model routing with no review step.
            self._start_voice(raw_text=text, auto_send=True)
            return True

        if cmd == "paste":
            self._paste_from_clipboard()
            return True

        return False

    def _try_family_activation(self, text: str) -> bool:
        """Ports the terminal CLI's family-letter activation flow: PIN
        setup/verify, a boundary-confirmation gate, then the letter and a
        session-long persona switch. Returns False (unhandled, caller falls
        through to plain babel translation) whenever the parsed name+DOB
        doesn't match a real family member -- a wrong guess must look
        identical to a normal, unrecognized "i am ..." sentence, same as
        the CLI's deliberate vagueness.
        """
        if not cc._LEGACY_OK:
            return False
        # parse_iam_command expects "i am ...", so drop the "babel"/"babel:"
        # prefix first, the way the CLI does -- passing the whole message made
        # every activation look like a non-match and fall through to translation.
        parsed = cc._fam_parse_iam(cc._babel_input(text) or text)
        if parsed is None:
            return False
        name, dob_text, inline_pin = parsed
        profile = cc._fam_detect(name, dob_text)
        if profile is None:
            return False

        key, display = profile["key"], profile["display"]

        if not cc._fam_pin_is_set(key):
            pin1, ok = QInputDialog.getText(
                self, "Cursiv", f"Identity recognized. Welcome, {display}.\n\n"
                f"First-time setup — choose a personal code (2-8 characters from: {cc._FAM_PIN_CHARS}):",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not pin1:
                return True
            if not cc._fam_pin_valid(pin1):
                QMessageBox.warning(self, "Cursiv", f"Code must be 2-8 characters from: {cc._FAM_PIN_CHARS}")
                return True
            pin2, ok = QInputDialog.getText(
                self, "Cursiv", "Confirm your code:", QLineEdit.EchoMode.Password,
            )
            if not ok or pin1 != pin2:
                QMessageBox.warning(self, "Cursiv", "Codes did not match. Try again.")
                return True
            cc._fam_set_pin(key, pin1)
            QMessageBox.information(
                self, "Cursiv",
                f"Code set. Next time include it: babel i am {name} born {dob_text}, {pin1}",
            )
            pin = pin1
        else:
            pin = inline_pin
            if pin is None:
                pin, ok = QInputDialog.getText(
                    self, "Cursiv", "Code:", QLineEdit.EchoMode.Password,
                )
                if not ok:
                    return True
            if not cc._fam_verify_pin(key, pin or ""):
                # Deliberately as non-committal as the "no match" case --
                # a wrong code shouldn't confirm the name+DOB was correct.
                self._append_system("Processing…")
                return True

        proceed = QMessageBox.question(
            self, "Cursiv — Boundary Notice",
            "Please respect that there are boundaries in place for a reason.\n\n"
            "By proceeding, you are deactivating safeguards built into this "
            "system. It may reveal more than you are ready to understand.\n\n"
            "If you are not ready for this, choose No — this will be here "
            "when you are.\n\nAre you ready to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            self._append_system("Understood. Come back when you're ready.")
            return True

        letter = cc._fam_get_letter(key)
        self._history[:] = [
            {"role": "system", "content": cc._fam_build_prompt(profile)},
            {"role": "assistant", "content": letter},
        ]

        self._append_user(f"babel i am {name} born {dob_text}")
        self._begin_ai_reply()
        self._append_reply_chunk(f"✦  Access granted. Welcome, {display}.\n\n")
        self._append_reply_chunk(letter)
        self._append_reply_chunk("\n\nYour personal feed is now active. Ask anything. Take your time. This is yours.")
        mail = cc._legacy_letters_for(key) if cc._LEGACY_OK else []
        if mail:
            self._append_reply_chunk(
                f"\n\nYou've got mail — {len(mail)} letter{'s' if len(mail) != 1 else ''} "
                f"waiting for you. Type \"legacy\" to open the vault."
            )
        self._end_ai_reply()
        return True

    def _open_postal_compose(self, recipient_hint: str) -> None:
        from postal_compose_dialog import PostalComposeDialog
        dlg = PostalComposeDialog(self._cfg.get("postal_user", "joshua"), recipient_hint, self)
        if dlg.exec() and dlg.result_text:
            self._append_user(f"write to {recipient_hint}".strip())
            self._begin_ai_reply()
            self._append_reply_chunk(dlg.result_text)
            self._end_ai_reply()

    def _open_legacy_vault(self) -> None:
        from legacy_vault_dialog import LegacyVaultDialog
        dlg = LegacyVaultDialog(self._cfg, self)
        dlg.exec()

    def _open_training_data(self) -> None:
        if not _CHAT_OK:
            self._append_system("Chat core isn't loaded yet -- try again in a moment.")
            return
        from training_data_dialog import TrainingDataDialog
        dlg = TrainingDataDialog(self._cfg, self)
        dlg.exec()

    # ── Voice ─────────────────────────────────────────────────────────────

    def _start_voice(self, raw_text: str = "", auto_send: bool = False) -> None:
        if self._streaming:
            return
        low = raw_text.strip().lower()
        raw_mode = low in ("listen",) or low.startswith("listen ")
        duration = 5.0
        sub = ""
        if low.startswith("voice "):
            sub = low[6:].strip()
        elif low.startswith("listen "):
            sub = low[7:].strip()
        if sub == "raw":
            raw_mode = True
        elif sub:
            try:
                duration = max(1.0, min(float(sub), 60.0))
            except ValueError:
                pass

        self._voice_btn.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._streaming = True
        self._status.setText(f"Listening for {duration:.0f} seconds… speak now")
        threading.Thread(
            target=self._run_voice, args=(duration, raw_mode, auto_send), daemon=True,
        ).start()

    def _run_voice(self, duration: float, raw_mode: bool, auto_send: bool) -> None:
        try:
            result = cc.voice_turn(self._cfg, duration_s=duration, raw_mode=raw_mode)
            self._signals.voice_result.emit(result.text, auto_send)
        except Exception as e:
            self._signals.error.emit(str(e))

    def _on_voice_result(self, text: str, auto_send: bool) -> None:
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._status.setText("")
        if not text:
            return
        self._input.setPlainText(text)
        if auto_send:
            self._send()
        else:
            cursor = self._input.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._input.setTextCursor(cursor)
            self._input.setFocus()

    # ── Paste image ───────────────────────────────────────────────────────

    def _handle_pasted_image(self, qimage) -> bool:
        if qimage is None or qimage.isNull():
            return False
        self._paste_qimage(qimage)
        return True

    def _paste_from_clipboard(self) -> None:
        qimage = QGuiApplication.clipboard().image()
        if qimage.isNull():
            self._append_system("Clipboard is empty or doesn't contain an image.")
            return
        self._paste_qimage(qimage)

    def _paste_qimage(self, qimage) -> None:
        from PyQt6.QtCore import QBuffer, QByteArray
        buf = QByteArray()
        qbuf = QBuffer(buf)
        qbuf.open(QBuffer.OpenModeFlag.WriteOnly)
        qimage.save(qbuf, "PNG")
        png_bytes = bytes(buf)
        width, height = qimage.width(), qimage.height()

        self._append_user("[pasted image]")
        self._begin_turn()
        threading.Thread(
            target=self._run_paste_analysis, args=(png_bytes, width, height), daemon=True,
        ).start()

    def _run_paste_analysis(self, png_bytes: bytes, width: int, height: int) -> None:
        try:
            result = cc.analyze_pasted_image(png_bytes, self._cfg, width, height)
            self._signals.chunk.emit(result.text)
            if result.image_path:
                self._signals.image.emit(result.image_path)
            self._signals.done.emit()
        except Exception as e:
            self._signals.error.emit(str(e))

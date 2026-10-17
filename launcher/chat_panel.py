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
from PyQt6.QtGui import QKeyEvent, QTextCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPlainTextEdit,
    QPushButton, QLabel, QSizePolicy, QInputDialog, QLineEdit, QMessageBox,
)

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

# Guardian's skull-alert block is real HTML meant to render as a styled card,
# not model-generated prose -- see _on_chunk, which detects it and routes it
# through _append_html_block instead of the plain-text streaming path every
# other chunk takes (deliberately plain-text, so partial HTML from a model's
# own streamed reply never lands mid-tag).
try:
    from cursiv_v215.guardian.temple_guardian import SKULL_HTML as _SKULL_HTML
except Exception:
    _SKULL_HTML = "\x00__skull_html_unavailable__\x00"

# ── Palette (matches cursiv_launcher.py exactly) ────────────────────────────
BG     = "#0b0b12"
BG2    = "#13131e"
BORDER = "#2a2a3f"
GOLD   = "#FFD700"
LGOLD  = "#9B7B20"
SILVER = "#C8C8D4"
SILV2  = "#666680"


def _load_saved_keys() -> dict:
    import json
    keys_file = Path(_CHAT_ROOT) / ".cursiv" / "config.json"
    try:
        data = json.loads(keys_file.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except Exception:
        return {}


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
    done  = pyqtSignal()                # generation finished cleanly
    error = pyqtSignal(str)             # generation raised an exception
    cancelled = pyqtSignal()            # user hit Stop mid-generation
    image = pyqtSignal(str)             # a local image path to render inline
    voice_result = pyqtSignal(str, bool)   # transcribed text, auto_send
    pending_write = pyqtSignal(str)     # raw WRITE_SENTINEL JSON payload, needs approval
    write_complete = pyqtSignal(str)    # result text once an approved write finishes (or fails)
    backend_ready = pyqtSignal(bool, str)  # chat_commands finished loading: ok, error message


class _ChatInput(QPlainTextEdit):
    """Enter sends, Shift+Enter inserts a newline -- standard chat-app behavior."""

    def __init__(self, on_send, on_paste_image, parent=None):
        super().__init__(parent)
        self._on_send = on_send
        self._on_paste_image = on_paste_image
        self.setFixedHeight(64)
        self.setPlaceholderText("Message Cursiv… (try: council, codex, babel, help)")
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {BG2}; color: {SILVER};
                border: 1px solid {BORDER}; border-radius: 8px;
                padding: 8px 10px; font-size: 13px;
            }}
            QPlainTextEdit:focus {{ border-color: {LGOLD}; }}
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
            if not self._history and not self._conv_id:
                self._transcript.clear()
            has_key = any(keys.get(k) for k in
                          ("api_key", "openai_key", "anthropic_key", "gemini_key", "groq_key"))
            if has_key or _is_ollama_installed():
                self._append_system("Ready. Ask me anything — or type help to see what I can do.")
            else:
                self._append_system(
                    "Almost ready — Cursiv needs an AI to talk through. Open Setup "
                    "(tray menu → Setup…) to install the free local engine, or add a "
                    "free Gemini or Groq key in Settings."
                )
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
        if self._conv_id:                       # saved once -> keep it current
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
        self.conversation_changed.emit()

    def open_conversation(self, conv_id: str) -> bool:
        import conversations
        data = conversations.load(conv_id)
        if not data:
            return False
        self._transcript.setHtml(data.get("html", ""))
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
        header = QLabel("Cursiv")
        header.setStyleSheet(
            f'color: {GOLD}; font-size: 15px; font-weight: 700;'
            f' font-family: "Segoe UI", "Segoe UI Historic";'
        )
        header_row.addWidget(header)
        header_row.addStretch(1)

        training_btn = QPushButton("🗂 Training Data")
        training_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        training_btn.setFixedHeight(28)
        training_btn.setStyleSheet(self._icon_btn_style() + "QPushButton { font-size: 11px; padding: 4px 10px; }")
        training_btn.setToolTip(
            "View, add, or delete examples in the training data store -- "
            "upload an image or paste JSON directly."
        )
        training_btn.clicked.connect(lambda: self._open_training_data())
        header_row.addWidget(training_btn)
        lay.addLayout(header_row)

        self._transcript = QTextBrowser()
        self._transcript.setOpenExternalLinks(True)
        self._transcript.setStyleSheet(f"""
            QTextBrowser {{
                background: {BG2}; color: {SILVER};
                border: 1px solid {BORDER}; border-radius: 8px;
                padding: 10px; font-size: 13px;
            }}
        """)
        self._transcript.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lay.addWidget(self._transcript, 1)

        row = QHBoxLayout()
        row.setSpacing(8)

        self._input = _ChatInput(self._send, self._handle_pasted_image)
        row.addWidget(self._input, 1)

        self._voice_btn = QPushButton("🎙")
        self._voice_btn.setFixedSize(40, 64)
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_btn.setToolTip("Record 5s of audio and transcribe it into the input box")
        self._voice_btn.setStyleSheet(self._icon_btn_style())
        # clicked emits clicked(bool) -- a bare connect would bind that bool
        # to raw_text (same trap as the Getting Started download buttons),
        # so wrap it to call with no arguments and let the defaults apply.
        self._voice_btn.clicked.connect(lambda: self._start_voice())
        row.addWidget(self._voice_btn)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedSize(72, 64)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: #2255DD; color: #ffffff;
                font-size: 13px; font-weight: 600;
                border-radius: 8px; border: none;
            }}
            QPushButton:hover    {{ background: #3366EE; }}
            QPushButton:pressed  {{ background: #1144CC; }}
            QPushButton:disabled {{ background: #1a1a2e; color: {SILV2}; }}
        """)
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._send_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedSize(56, 64)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setToolTip("Stop the current response and return to standby")
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #ff6666;
                font-size: 12px; font-weight: 600;
                border: 1px solid #663333; border-radius: 8px;
            }}
            QPushButton:hover    {{ background: rgba(255,102,102,0.10); border-color: #ff6666; }}
            QPushButton:pressed  {{ background: rgba(255,102,102,0.18); }}
            QPushButton:disabled {{ color: {SILV2}; border-color: {BORDER}; }}
        """)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_generation)
        row.addWidget(self._stop_btn)

        lay.addLayout(row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 10px;")
        lay.addWidget(self._status)

    def _icon_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: transparent; color: {GOLD}; font-size: 16px;
                border: 1px solid {BORDER}; border-radius: 8px;
            }}
            QPushButton:hover    {{ background: rgba(212,175,55,0.08); border-color: {LGOLD}; }}
            QPushButton:pressed  {{ background: rgba(212,175,55,0.15); }}
            QPushButton:disabled {{ color: {SILV2}; }}
        """

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
        self._transcript.insertHtml(html)
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
            f'<span style="color:{LGOLD}; font-weight:600;">You</span><br>'
            f'<span style="color:{SILVER};">{self._escape(text)}</span></p>'
        )

    def _begin_ai_reply(self) -> None:
        # Opens a paragraph the streamed chunks get appended into; closed in _on_done.
        self._force_new_block()
        self._append_html_block(
            f'<p style="margin:4px 0 4px 0;">'
            f'<span style="color:{GOLD}; font-weight:700;">✦ Cursiv</span><br>'
            f'<span style="color:#F0E9D8; white-space:pre-wrap;">'
        )

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
        if not _CHAT_OK:
            self._append_system("Chat core isn't available -- see the message above.")
            return

        # "clear" wipes the on-screen transcript and in-memory history --
        # there's nothing for chat_commands.py (UI-agnostic, no widget
        # access) to do here, so it's handled directly on the main thread.
        if text.strip().lower() == "clear":
            self._input.clear()
            self.new_conversation()
            self._append_system("History cleared.")
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
            )
            self._cfg["last_user_msg"] = stripped
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
        if chunk.strip() == _SKULL_HTML.strip():
            # Close the AI-reply paragraph opened by _begin_ai_reply, render
            # the skull card as actual HTML, then reopen a fresh paragraph
            # so anything streamed after it (the decoy response) still has
            # somewhere valid to land -- _end_ai_reply() closes it as usual.
            # Same scroll-preservation as _append_reply_chunk: only follow
            # to the bottom if the user was already there.
            at_bottom = self._at_bottom()
            cursor = QTextCursor(self._transcript.document())
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml("</span></p>")
            cursor.insertHtml(chunk)
            cursor.insertHtml(
                f'<p style="margin:4px 0 4px 0;">'
                f'<span style="color:#F0E9D8; white-space:pre-wrap;">'
            )
            if at_bottom:
                self._transcript.verticalScrollBar().setValue(self._transcript.verticalScrollBar().maximum())
            return
        self._append_reply_chunk(chunk)

    def _on_image(self, path: str) -> None:
        self._append_image(path)

    def _on_done(self) -> None:
        self._end_ai_reply()
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
        self._status.setText(f"🎙 Listening {duration:.0f}s… speak now")
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

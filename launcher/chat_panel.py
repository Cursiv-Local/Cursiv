"""
Cursiv — in-app chat panel.

Replaces the old terminal-spawned CLI with a real chat view living inside
the main Cursiv window. Plain messages go through the exact same core
chat() call the terminal CLI and web demo already use
(cursiv_engine/ui/chat_app.py); the terminal CLI's ~40 built-in commands
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
    QPushButton, QLabel, QSizePolicy, QInputDialog, QLineEdit, QMessageBox, QDialog,
)
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2  # one palette for every window (theme.py)
import theme
import re as _re
from chat_rendering import MarkdownStream, TranscriptCache, style_code
from chat_controls import ChatControlsMixin, _ChatInput
from chat_transcript import ChatTranscriptMixin
from chat_review import ChatReviewMixin
from chat_feedback import ChatFeedbackMixin
from chat_actions import ChatActionsMixin
from provider_controls import ProviderControlsMixin, provider_turn, load_saved_keys as _load_saved_keys


_HERE = Path(__file__).parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# chat_commands.py pulls in roughly a dozen cursiv_engine subsystems (postal,
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


def autosave_enabled() -> bool:
    """Conversations save themselves unless turned off in Settings → Your data & account."""
    try:
        from cursiv_engine.chat import keys
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
        if cancel_event.is_set():
            gen.close()
            return
        yield chunk


def _is_ollama_installed() -> bool:
    import os
    import shutil
    exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return bool(shutil.which("ollama")) or exe.exists()


class _ChatSignals(QObject):
    provider_models = pyqtSignal(str, object, str)
    run_event = pyqtSignal(object, object)  # immutable turn target, application-owned UI event
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
    crosscheck = pyqtSignal(object)     # core.crosscheck.Review, from the background thread
    review_done = pyqtSignal(object, object)
    review_state = pyqtSignal(object, str)
    tool_receipt = pyqtSignal(object)
    state_changed = pyqtSignal()
    notes_view = pyqtSignal(str, str)   # category/query; widgets are opened on the GUI thread
    stage = pyqtSignal(str)            # distinguish answer checks from streaming/rendering
    saved = pyqtSignal(str, str, int)  # conversation id, error, snapshot revision




class ChatPanel(ProviderControlsMixin, ChatControlsMixin, ChatTranscriptMixin, ChatReviewMixin, ChatFeedbackMixin, ChatActionsMixin, QWidget):
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
        self._pending_notebook_receipt: dict | None = None
        self._pending_file_receipts: list[dict] = []
        self._pending_answer_evidence = None
        self._pending_memory_receipt: dict | None = None
        self._cancel_event: Optional[threading.Event] = None
        self._signals = _ChatSignals()
        self._signals.chunk.connect(self._on_chunk)
        self._signals.run_event.connect(self._on_run_event)
        self._signals.replace.connect(self._on_replace)
        self._signals.done.connect(self._on_done)
        self._signals.error.connect(self._on_error)
        self._signals.cancelled.connect(self._on_cancelled)
        self._signals.image.connect(self._on_image)
        self._signals.voice_result.connect(self._on_voice_result)
        self._signals.pending_write.connect(self._on_pending_write)
        self._signals.write_complete.connect(self._finish_pending_write)
        self._signals.notes_view.connect(self._open_saved_notes)
        self._signals.stage.connect(self._status_stage)
        self._signals.saved.connect(self._on_saved)
        self._signals.backend_ready.connect(self._on_backend_ready)
        self._init_review()
        self._pending_write_context: dict = {}
        self._cfg: dict = {}

        self._build_ui()
        self._pending_chunks: list[str] = []
        self._markdown_stream = MarkdownStream()
        self._render_cache = None
        self._transcript_cache = TranscriptCache(self._transcript.document())
        self._save_revision = 0
        self._save_error = False
        self._chunk_timer = QTimer(self)
        self._chunk_timer.setInterval(40)
        self._chunk_timer.timeout.connect(self._flush_reply_chunks)
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

            selection_cfg = {k:v for k,v in self._cfg.items() if k.startswith('selected_')}
            self._cfg = cc._default_cfg()
            self._cfg.update(selection_cfg)
            keys = _load_saved_keys()
            self._cfg["api_key"] = keys.get("api_key", "")
            self._cfg["openai_key"] = keys.get("openai_key", "")
            self._cfg["anthropic_key"] = keys.get("anthropic_key", "")
            self._cfg["postal_user"] = "joshua"

            self._backend_ready = True
            self._refresh_status_pill()
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
            self.save_conversation(background=True)
        self._update_session_note()
        QTimer.singleShot(8000, self._show_suggestions)     # learning finishes in the background

    def _on_saved(self, conv_id: str, error: str, revision: int) -> None:
        if conv_id == self._conv_id and revision == self._save_revision:
            self._dirty = bool(error)
            self._save_error = bool(error)
            if error:
                self._status.setText("Conversation could not be saved. Use Save to retry.")
                self._status.setToolTip(error)
        self.conversation_changed.emit()

    def has_unsaved(self) -> bool:
        if self._conv_id:
            # Called by the existing leave/quit confirmation, not by streaming.
            # A completed-but-failed autosave must still offer Save/Don't Save.
            import conversations
            try:
                conversations.wait_for_save(self._conv_id)
            except Exception:
                self._dirty = self._save_error = True
        return self._dirty and bool(self._history) and (not self._conv_id or self._save_error)

    def is_busy(self) -> bool:
        return self._streaming

    def current_conversation_id(self) -> Optional[str]:
        return self._conv_id

    def save_conversation(self, title: Optional[str] = None, *, background: bool = False) -> Optional[str]:
        if not self._history:
            return None
        import conversations
        if background:
            # Only the new message blocks are exported here. JSON/disk work
            # receives immutable text, never a widget or live QTextDocument.
            self._save_revision += 1
            revision, signals = self._save_revision, self._signals
            self._conv_id = conversations.queue_save(
                self._conv_id, self._history, self._transcript_cache.capture(),
                on_titled=self.conversation_changed.emit,
                on_done=lambda conv_id, error: signals.saved.emit(conv_id, error, revision))
            return self._conv_id
        self._save_revision += 1
        html = self._transcript.toHtml()
        self._conv_id = conversations.save(self._conv_id, self._history, html, title,
                                           on_titled=self.conversation_changed.emit)   # AI title -> sidebar
        self._transcript_cache.reset(html)
        self._dirty = False
        if self._save_error:
            self._status.setText("")
            self._status.setToolTip("")
        self._save_error = False
        self.conversation_changed.emit()
        return self._conv_id

    def new_conversation(self) -> None:
        self._cancel_review()
        self._last_research_run = None
        if self._cancel_event is not None:
            self._cancel_event.set()
        if self._streaming:
            self._pending_history_append = None
            self._on_cancelled()
        self._intents = {}
        self._pending_intent = None
        self._reset_rendering()
        self._transcript.clear()
        self._transcript_cache.reset()
        self._history = []
        self._conv_id = None
        self._dirty = False
        self._save_error = False
        try:
            from cursiv_engine.memory import session_notes
            session_notes.set_active("")             # a new chat starts without an old note
        except Exception:
            pass
        self._show_empty_state()
        self._reset_feedback()
        self.conversation_changed.emit()

    # ── Empty state ─────────────────────────────────────────────────────

    # The research profile (core/profile.py, the default); EXAMPLES with personal features shown.
    FIELD_EXAMPLES = (("New here? What can Cursiv do?", "What can Cursiv do?"),
                      "What is the distance and bearing from 44.1234, -71.5678 to 44.1371, -71.5512?",
                      "log site: North transect; water temp 12.40 C; pH 7.2; note: first visit",
                      "How much 1 M stock do I need to make 500 mL of 0.1 M solution?",
                      ("Try everything with sample data: demo", "demo"))
    EXAMPLES = (("New here? What can Cursiv do?", "What can Cursiv do?"),
                "How do I purify creek water so it's safe to drink?",
                "Help me plan meals for a week on a tight budget.",
                "Explain how a well pump works, simply.",
                "What should go in a 72-hour emergency kit for a family of four?")

    def _examples(self) -> tuple:
        try:
            from cursiv_engine.core import profile as _profile
            return self.EXAMPLES if _profile.personal() else self.FIELD_EXAMPLES
        except Exception:
            return self.FIELD_EXAMPLES

    def _show_empty_state(self, setup_needed: bool = False) -> None:
        """What a new chat looks like: a question, how Cursiv works in one line, examples to click."""
        from urllib.parse import quote
        if setup_needed:
            body = (f'<p style="color:{theme.AMBER};">Local AI chat needs an AI model. Built-in help is available now.</p>'
                    f'<p><a href="cursiv://setup" style="color:{theme.ACCENT};">Open Setup</a>'
                    f'<span style="color:{theme.MUTED};"> to install the free local engine and a model sized for this '
                    f'computer, or add a free Gemini or Groq key in Settings.</span></p>'
                    f'<p><a href="cursiv://prompt/What%20can%20Cursiv%20do%3F" '
                    f'style="color:{theme.ACCENT};">New here? What can Cursiv do?</a></p>')
        else:
            import chat_badges
            prompt = lambda text: f"cursiv://prompt/{quote(text)}"
            extra = [(e, e) if isinstance(e, str) else e for e in self._examples()]
            covered = ("log site", "offline on")       # already a starter card
            extra = [(label, text) for label, text in extra          # not a second "log site: …"
                     if not text.lower().startswith(covered)][:3]
            body = chat_badges.starters(prompt) + "".join(
                f'<p style="margin:4px 0 4px 8px;"><a href="{prompt(text)}" '
                f'style="color:{theme.MUTED}; text-decoration:none; font-size:13px;">→&nbsp;&nbsp;{self._escape(label)}</a></p>'
                for label, text in extra)
        self._transcript.setHtml(theme.live(
            f'<div style="margin-top:36px;">'
            f'<p style="font-size:22px; font-weight:600; color:{theme.TEXT};">What can I help with?</p>'
            f'<p style="color:{theme.MUTED}; margin:6px 0 14px 0;">Cursiv runs on this computer. Calculations, '
            f'notebook entries and saved memories are done by Cursiv itself; other answers come from an AI model '
            f'and can be wrong, so check anything that matters. Pick a card to edit it before sending.</p>'
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
            elif url.host() == "intent":
                what, _, key = url.path().lstrip("/").partition("/")
                self._answer_intent(what, key)
            elif url.host() == "suggest":
                what, _, key = url.path().lstrip("/").partition("/")
                self._answer_suggestion(what, key)
            elif url.host() == "report":
                win = self.window()
                if hasattr(win, "_send_problem_report"):
                    win._send_problem_report(getattr(self, "_last_problem", ""))
            return
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(url)

    def open_conversation(self, conv_id: str) -> bool:
        import conversations
        data = conversations.load(conv_id)
        if not data:
            return False
        self._last_research_run = None
        if self._cancel_event is not None:
            self._cancel_event.set()
        if self._streaming:
            self._pending_history_append = None
            self._on_cancelled()
        self._cancel_review()
        self._intents = {}
        self._pending_intent = None
        self._reset_rendering()
        saved_html = theme.to_current(data.get("html", ""))
        self._transcript.setHtml(saved_html)
        if style_code(self._transcript.document(), 0, self._transcript.document().characterCount() - 1):
            self._transcript_cache.reset()  # export the updated font on the next normal save
        else:
            self._transcript_cache.reset(saved_html)
        self._empty_shown = False
        self._history = list(data.get("messages", []))
        self._conv_id = conv_id
        self._dirty = False
        self._save_error = False
        self._reset_feedback()
        self._show_picking_up(conv_id)
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
        self._refresh_status_pill()



    # ── Status pill and model picker ─────────────────────────────────────










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







    # ── Transcript rendering ─────────────────────────────────────────────














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

        self._provider_turn_authorized = self._authorize_provider_text(text)
        self._input.clear()
        self._append_user(text)
        self._begin_turn(cc.hey_prefix(text)[1])

        # Snapshot deliberately excludes this turn -- built-in commands
        # (anchor this, etc.) inspect history for the *prior* exchange, and
        # the terminal CLI never adds command text to history at all, only
        # real chat turns. Whether/what to append is decided in _run_turn
        # once we know if this resolved to a command or a plain chat call.
        history_snapshot = list(self._history)
        thread = threading.Thread(
            target=self._run_turn, args=(text, history_snapshot),
            kwargs={'turn_target': self._run_target()}, daemon=True,
        )
        thread.start()

    def _begin_turn(self, text: str = '') -> None:
        self._cancel_review()
        self._set_turn_feedback(text)
        self._reset_rendering()
        self._pending_notebook_receipt = None
        self._pending_file_receipts = []
        self._pending_answer_evidence = None
        self._pending_memory_receipt = None
        self._streaming = True
        self._cancel_event = threading.Event()
        self._send_btn.setEnabled(False)
        self._voice_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._provider_box.setEnabled(False)
        self._cloud_model_box.setEnabled(False)
        self._model_box.setEnabled(False)
        self._retry_provider_btn.setVisible(False)
        self._cc_btn.setEnabled(False)
        self._last_exchange = None           # a new turn: nothing finished to cross-check yet
        self._status.setText("Preparing answer…")
        self._reply_text = ""
        self._reply_is_chat = False
        self._begin_ai_reply()

    def _stop_generation(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._stop_btn.setEnabled(False)
        self._status.setText("Stopping…")

    @provider_turn
    def _run_turn(self, text: str, history: list[dict], propose: bool = True, turn_target=None) -> None:
        target = turn_target or self._run_target()
        if not self._current_run_target(target):
            return
        try:
            force_provider, stripped = self._managed_prefix(text)
            selection_error = ''
            if not force_provider and self._cfg.get('selected_provider'):
                selected_model = self._cfg.get('selected_model','')
                if self._cfg['selected_provider'] == 'cloud_auto':
                    force_provider = 'manager:cloud_auto'
                elif not selected_model:
                    selection_error='Choose an exact model ID for the selected provider before requesting a model answer.'
                else:
                    force_provider = 'manager:'+self._cfg['selected_provider']+'::'+selected_model
            # A provider prefix never transfers notebook execution to the model.
            from cursiv_engine.core import notebook_tools, file_requests
            from cursiv_engine.memory import intents, semantic
            from cursiv_engine.core import turn_policy
            unrestricted = turn_policy.effective(stripped) == turn_policy.Policy()
            from cursiv_engine.core import self_inspection
            workspace_request = file_requests.recognizes(stripped) or bool(self_inspection.resolve(stripped,history))
            if propose and unrestricted and not workspace_request:
                from cursiv_engine.core import notebook_proposals
                preview = (notebook_proposals.confirmation(stripped)
                           or notebook_proposals.export_request(stripped)
                           or notebook_proposals.correction(stripped)
                           or self._memory_confirmation(stripped, history)
                           or notebook_proposals.context_correction(stripped, history)
                           or (notebook_proposals.record(stripped) if not intents.requested_operations(stripped) else None))
                if preview is not None:
                    self._pending_intent = preview
                    self._pending_history_append = None
                    self._signals.done.emit()
                    return
            native = unrestricted and not workspace_request and (notebook_tools.is_request(stripped, history) or intents.is_request(
                stripped, history, person=semantic.current_person(), scope=self._conv_id or ''))
            if native and self._conv_id is None:
                import uuid
                self._conv_id = uuid.uuid4().hex[:12]
            result = cc.notebook_command(stripped, history, scope=self._conv_id or '', cfg=self._cfg) if unrestricted and not workspace_request else None
            if result is None and unrestricted and not workspace_request:
                result = cc.memory_command(stripped, history, scope=self._conv_id or '', preview_saves=propose)
                if result is not None and result.update_preview:
                    from cursiv_engine.core.intent import ACTIONS, Proposal
                    slots = result.update_preview
                    action = ACTIONS['memory.correct']
                    self._pending_intent = Proposal(action, slots, action.template.format(**slots), [], edit_text=stripped)
                    self._pending_history_append = None
                    self._signals.done.emit()
                    return
                if result is not None and result.save_preview:
                    from cursiv_engine.core.intent import ACTIONS, Proposal
                    facts = result.save_preview
                    self._pending_intent = Proposal(ACTIONS['memory.save'], {'fact': facts[0]}, 'remember ' + facts[0],
                        [] if len(facts) == 1 else ['Save one memory at a time so you can check its preview.'], edit_text=stripped)
                    self._pending_history_append = None
                    self._signals.done.emit()
                    return
            if result is None and (not force_provider or (force_provider.startswith('manager:') and self._native_image_command(stripped))):
                result = cc.handle_command(text, self._cfg, history)

            if result is not None:
                self._deliver_result(result, history, text, turn_target=target)
                return

            # U99: said in plain words? The local model may turn it into one of
            # Cursiv's own commands. Read-only ones run now; anything that changes
            # something waits on a confirm card. The model never runs anything.
            if propose and not force_provider and not selection_error and unrestricted and not workspace_request:
                proposal = self._propose_action(stripped)
                if proposal is not None:
                    if proposal.ok and not proposal.needs_confirm:
                        self._signals.chunk.emit(f"*[Understood as: {proposal.command}]*\n\n")
                        return self._run_turn(proposal.command, history, propose=False)
                    self._pending_intent = proposal
                    self._pending_history_append = None
                    self._signals.done.emit()
                    return

            # No built-in command matched (or a "hey <provider>" prefix
            # forced routing) -- fall through to the default streaming chat,
            # the same core the terminal CLI's plain-message path uses.
            # `history` here is the snapshot from *before* this turn, so it
            # goes straight to chat() -- which appends the current user
            # turn itself -- with nothing to trim off the end.
            workspace = self._cfg.get("workspace", '')
            if selection_error:
                from cursiv_engine.chat import provider_manager as manager
                from cursiv_engine.chat.provider_types import Request
                list(manager.infer(Request(self._cfg['selected_provider'],'', [{'role':'user','content':stripped}])))
                self._signals.run_event.emit(target,dict(kind='provider_failure',text=selection_error,
                    request=manager.snapshot(),prompt=stripped,provenance=manager.outcome().metadata()))
                return  # native operations above remain independent of model configuration
            review_key, review_cancel = self._review_generation, self._cancel_event
            if not self._current_run_target(target):
                return
            if not force_provider:
                force_provider = 'manager:local_auto'
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
                on_stage=self._signals.stage.emit,
                on_action=self._capture_file_result,
                on_review=lambda job: self._queue_review(review_key, job, review_cancel),
            )
            self._cfg["last_user_msg"] = stripped
            self._reply_is_chat = True          # streamed Markdown; commands stay plain
            cancel_event = self._cancel_event
            full = ""
            from cursiv_engine.chat.activity import guarded
            from cursiv_engine.chat import provider_manager as manager
            def owned_provider_stream(source):
                with manager.turn_options(research_authorized=getattr(self, '_provider_turn_authorized', False),
                        local_only=bool(self._cfg.get('project_local_only')), workspace=workspace, cancel=cancel_event,destination=getattr(self,'_provider_turn_destination',None)):
                    yield from source
            gen = owned_provider_stream(gen)
            gen = guarded(gen, lambda: self._current_run_target(target) and not target[1].is_set())
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
                    self._signals.run_event.emit(target, dict(kind='replace', text=full))
                    continue
                full += chunk
                self._signals.run_event.emit(target, dict(kind='chunk', text=chunk))
            if cancel_event.is_set():
                from cursiv_engine.chat import provider_manager as manager
                result = manager.outcome()
                if result is not None and manager.snapshot() is not None:
                    self._signals.run_event.emit(target, dict(kind='provider_failure', text=result.error_message or 'Request canceled.',
                        request=manager.snapshot(), prompt=stripped, provenance=result.metadata()))
                    return
                self._signals.run_event.emit(target, dict(kind='cancelled', history=
                    [("user", stripped), ("assistant", full)] if full else None))
                return
            result = manager.outcome()
            if result is not None and result.error:
                self._signals.run_event.emit(target, dict(kind='provider_failure', text=result.error_message,
                    request=manager.snapshot(), prompt=stripped, provenance=result.metadata()))
                return
            self._signals.run_event.emit(target, dict(kind='done', history=[('user', stripped), ('assistant', full)],
                    exchange=(stripped, full) if full.strip() else None,
                    provenance=result.metadata() if result else None))
        except Exception as e:
            self._signals.run_event.emit(target, dict(kind='error', text=str(e)))

    # ── Cross-check: a second AI reviews the last answer, only on request (core/crosscheck.py) ──
    def _cross_check(self) -> None:
        from cursiv_engine.core import crosscheck
        exchange = getattr(self, "_last_exchange", None)
        if not exchange or self._streaming:
            return
        providers = crosscheck.available(self._cfg)
        if not providers:
            QMessageBox.information(self, "Cross-check",
                                    "Cross-check sends an answer to another AI service for a second opinion, so it "
                                    "needs your own key for one: Claude, OpenAI, xAI, or a free Gemini or Groq key "
                                    "(Settings → AI keys). Nothing was sent. Cursiv works the same without one.")
            return
        from crosscheck_dialog import CrossCheckDialog
        dlg = CrossCheckDialog(exchange[0], exchange[1], providers, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.payload is None:
            return                                    # cancelled: nothing leaves this computer
        payload = dlg.payload
        self._cc_btn.setEnabled(False)
        self._status.setText(f"Asking {payload.to} for a second opinion…")
        cfg = dict(self._cfg)
        threading.Thread(target=lambda: self._signals.crosscheck.emit(crosscheck.review(payload, cfg)),
                         daemon=True).start()

    def _on_cross_check(self, r) -> None:
        """The review goes below the answer, in its own block; the answer and the history are untouched."""
        # A late automatic review must not replace a block appended by the
        # person's explicit second-opinion request.
        self._cancel_review()
        from cursiv_engine.core import crosscheck
        colour = theme.AMBER if r.ok else theme.RED
        self._force_new_block()
        self._append_html_block(
            f'<div style="margin:8px 0 14px 0; padding:8px 10px; border-left:3px solid {colour};">'
            f'<span style="color:{colour}; font-weight:600;">{self._escape(crosscheck.heading(r))}</span><br>'
            f'<span style="color:{SILVER};">{self._keep_shape(r.text)}</span></div>')
        self._status.setText("")
        self._cc_btn.setEnabled(bool(getattr(self, "_last_exchange", None)) and not self._streaming)

    def _deliver_result(self, result, history: list[dict], text: str = "", turn_target=None) -> None:
        """Runs on the background thread -- streams a command's TextResult/StreamResult."""
        from cursiv_engine.chat import provider_manager as manager
        outcome=manager.outcome()
        if outcome and outcome.error:
            self._signals.run_event.emit(turn_target or self._run_target(),dict(kind='provider_failure',text=outcome.error_message,
                request=manager.snapshot(),prompt=text,provenance=outcome.metadata()))
            return
        if getattr(result, 'run', None) is not None:
            return self._deliver_run(result, text, turn_target or self._run_target())
        self._signals.state_changed.emit()
        if isinstance(result, cc.NotebookResult):
            self._pending_history_append = [("user", cc.hey_prefix(text)[1]), ("assistant", result.text)]
            self._pending_notebook_receipt = result.receipt
            self._signals.tool_receipt.emit(('notebook', result.receipt))
            self._signals.chunk.emit(result.text)
            self._signals.done.emit()
            return
        if isinstance(result, cc.MemoryResult):
            self._pending_history_append = [("user", cc.hey_prefix(text)[1]), ("assistant", result.text)]
            self._pending_memory_receipt = result.receipt
            self._signals.tool_receipt.emit(('memory', result.receipt))
            self._signals.chunk.emit(result.text)
            self._signals.done.emit()
            return
        if isinstance(result, cc.NotesResult):
            self._pending_history_append = None
            self._signals.notes_view.emit(result.category, result.query)
            self._signals.chunk.emit(result.text)
            self._signals.done.emit()
            return
        if isinstance(result, cc.TextResult):
            target = turn_target or self._run_target()
            if result.text:
                self._signals.run_event.emit(target, dict(kind='chunk', text=result.text))
            if result.image_path:
                self._signals.run_event.emit(target, dict(kind='image', text=result.image_path))
            self._signals.run_event.emit(target, dict(kind='done',
                history=[('user',text),('assistant',result.text)] if outcome and text else None,
                provenance=outcome.metadata() if outcome else None))
            return

        return self._deliver_command_stream(result, text, turn_target or self._run_target())

    def _open_saved_notes(self, category: str = '', query: str = '') -> None:
        try:
            from saved_notes_dialog import SavedNotesDialog
            dialog = getattr(self, '_notes_dialog', None)
            if dialog is None:
                dialog = SavedNotesDialog(self, category=category or None, query=query)
                self._notes_dialog = dialog
            else:
                dialog.apply_request(category=category or None, query=query)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        except Exception as exc:
            self._append_system(f'Could not open saved notes: {exc}')

    # ── Signal handlers (run on the GUI thread) ─────────────────────────

    def _on_chunk(self, chunk: str) -> None:
        self._reply_text += chunk
        policy = getattr(self, '_turn_policy', None)
        if policy and chunk == policy.confirmation() + '\n\n' and policy.confirmation():
            return  # quiet badge now; full policy evidence stays in the checks panel/history
        self._pending_chunks.append(chunk)
        if not self._chunk_timer.isActive():
            self._chunk_timer.start()

    def _status_stage(self, text: str) -> None:
        if self._streaming:
            self._status.setText(text)
            # The model has finished; checks can still take seconds. Finish
            # the visible draft now, including a paragraph without a trailing
            # blank line. Later corrections still replace this message in place.
            self._flush_reply_chunks(format_blocks=False)
            if self._reply_is_chat:
                try:
                    self._render_reply()
                except Exception:
                    pass                # preserve the plain draft if Markdown fails
                self._markdown_stream = MarkdownStream()
                self._stream_tail_start = self._transcript.document().characterCount() - 1

    def _on_replace(self, text: str) -> None:
        """Swap the streamed draft for the checked answer (same paragraph and style)."""
        start = getattr(self, "_reply_start", None)
        if start is None:
            self._append_reply_chunk("\n\n" + text)
            return
        if hasattr(self, '_pending_chunks'):
            self._reset_rendering()
        cursor = QTextCursor(self._transcript.document())
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)            # replaces the selected draft
        self._reply_text = text
        if hasattr(self, '_markdown_stream'):
            # Replacement is rare, and is always finalized as one checked message.
            # Do not let a subsequent note append re-render an already displayed draft.
            self._stream_tail_start = cursor.position()

    def _on_image(self, path: str) -> None:
        self._flush_reply_chunks(format_blocks=False)
        self._append_image(path)

    def _on_done(self) -> None:
        self._flush_reply_chunks(format_blocks=False)
        if getattr(self, "_pending_intent", None) is not None:
            self._show_intent_card(self._pending_intent)
            self._pending_intent = None
        elif getattr(self, "_reply_is_chat", False):
            try:
                self._render_reply()
                self._maybe_show_tour()
            except Exception:
                pass                     # the plain streamed text stays
        else:
            try:
                self._render_receipt()   # a notebook save, offline on, … as a card
            except Exception:
                pass
        self._end_ai_reply()
        self._refresh_status_pill()      # "offline on", a new key, ... change it
        for role, content in (getattr(self, "_pending_history_append", None) or []):
            self._history.append({"role": role, "content": content})
        if getattr(self, '_pending_provider_provenance', None) and self._history:
            self._history[-1]['provider_provenance'] = self._pending_provider_provenance
        self._pending_provider_provenance = None
        if self._pending_notebook_receipt is not None and self._history:
            self._history[-1]['notebook_receipt'] = self._pending_notebook_receipt
            self._pending_notebook_receipt = None
        if self._pending_file_receipts and self._history:
            self._history[-1]['file_receipts'] = self._pending_file_receipts
            self._pending_file_receipts = []
        if self._pending_answer_evidence is not None and self._history:
            self._history[-1]['answer_evidence'] = self._pending_answer_evidence
            self._pending_answer_evidence = None
        if self._pending_memory_receipt is not None and self._history:
            self._history[-1]['memory_receipt'] = self._pending_memory_receipt
            self._pending_memory_receipt = None
        self._pending_history_append = None
        self._refresh_context_indicator()
        self._after_turn()
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._retry_provider_btn.setVisible(self._has_current_provider_retry())
        self._provider_box.setEnabled(True)
        self._cloud_model_box.setEnabled(True)
        self._model_box.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._cc_btn.setEnabled(bool(getattr(self, "_last_exchange", None)))
        self._status.setText("")
        self._input.setFocus()
        self._start_review()

    def _on_cancelled(self) -> None:
        self._provider_box.setEnabled(True)
        self._cloud_model_box.setEnabled(True)
        self._model_box.setEnabled(True)
        self._cancel_review()
        self._flush_reply_chunks(format_blocks=False)
        self._chunk_timer.stop()
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
        self._provider_box.setEnabled(True)
        self._cloud_model_box.setEnabled(True)
        self._model_box.setEnabled(True)
        self._cancel_review()
        self._flush_reply_chunks(format_blocks=False)
        self._chunk_timer.stop()
        import chat_badges
        self._force_new_block()
        self._append_html_block(chat_badges.problem(message))
        self._last_problem = message
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
        self._flush_reply_chunks(format_blocks=False)
        import json
        try:
            pending = json.loads(raw_json)
        except Exception:
            self._finish_pending_write("[Could not parse pending write]")
            return

        path = pending.get("path", "?")
        content = pending.get("content", "")
        self._pending_write_context['request'] = pending
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
        workspace = self._pending_write_context.get("workspace", '')
        threading.Thread(
            target=self._run_write_approval, args=(path, content, workspace), daemon=True,
        ).start()

    def _run_write_approval(self, path: str, content: str, workspace: str) -> None:
        try:
            request = self._pending_write_context.get('request', {})
            result = cc.approve_write(path, content, workspace,
                                      operation=request.get('operation', 'write_file'),
                                      expected_sha256=request.get('expected_sha256'),
                                      remember=request.get('remember', False))
            self._pending_file_receipts = getattr(result, 'receipts', [])
            for receipt in self._pending_file_receipts:
                self._signals.tool_receipt.emit(('filesystem', receipt))
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
        if self._pending_file_receipts:
            self._history[-1]['file_receipts'] = self._pending_file_receipts
            self._pending_file_receipts = []
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

        from cursiv_engine.core import profile
        if profile.letters_command(text):
            self._append_user(text)          # show what was typed; the note alone looked like a repeat
            self._append_system(profile.REMOVED_NOTE)
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

        if cmd in ("workspace map", "make a workspace map", "draft cursiv.md"):
            self._append_user(text)
            self._draft_workspace_map()
            return True

        if cmd in ("memory folder", "show my memory folder", "show memory folder", "memory files"):
            self._append_user(text)
            self._show_memory_folder()
            return True

        return False

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

        self._provider_turn_authorized = self._authorize_provider_turn()
        self._append_user("[pasted image]")
        self._begin_turn()
        threading.Thread(
            target=self._run_paste_analysis, args=(png_bytes, width, height), daemon=True,
            kwargs={'turn_target':self._run_target(),'cfg_snapshot':dict(self._cfg)},
        ).start()


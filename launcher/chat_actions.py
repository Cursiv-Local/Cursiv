"""ChatActionsMixin (U99/U100): plain-words actions and memory you can see, in the chat window.

The confirm card for conversational actions (core/intent.py), suggested memories
(memory/suggestions.py), session notes (memory/session_notes.py), the readable memory
folder (memory/markdown.py) and the workspace map (core/guidance.py). Moved out of
chat_panel.py to keep it under the module size budget; runs on the GUI thread except
where it starts its own background thread.
"""
from __future__ import annotations

import threading

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QTextCursor

import theme


class ChatActionsMixin:
    # ── U99: conversational actions waiting for a yes ───────────────────────

    def _show_intent_card(self, proposal) -> None:
        import uuid
        import chat_badges
        key = uuid.uuid4().hex[:10]
        self._intents = getattr(self, "_intents", {})
        self._intents[key] = proposal
        start = getattr(self, "_reply_start", None)
        cursor = QTextCursor(self._transcript.document())
        cursor.beginEditBlock()
        if start is not None:
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(theme.live(chat_badges.intent_card(proposal, key)))
        self._plain_block(cursor)
        cursor.endEditBlock()

    def _answer_intent(self, what: str, key: str) -> None:
        """Save runs exactly the command on the card, through Cursiv's own code (with
        its receipt); Edit puts it in the message box; Cancel changes nothing."""
        proposal = getattr(self, "_intents", {}).get(key)
        if proposal is None:
            self._append_system("That card was already answered.")
            return
        if what == "edit":
            self.prefill(proposal.edit_text or proposal.command)
            return
        if self._streaming:
            return
        self._intents.pop(key, None)
        if what == "cancel":
            self._append_system("Cancelled. Nothing was changed.")
            return
        if what != "save" or not proposal.ok:
            return
        if proposal.action.name == 'notebook.correct':
            from cursiv_engine.core import fieldlog
            if not any(row['id'] == proposal.slots.get('entry') for row in fieldlog.current()):
                self._append_system('This observation has changed since the preview. Review its current entry before correcting it.')
                return
        self._begin_turn(proposal.command)
        history_snapshot = list(self._history)
        threading.Thread(target=self._run_turn, args=(proposal.command, history_snapshot, False),
                         daemon=True).start()

    # ── U100: session notes (memory/session_notes.py) ───────────────────────

    def _draft_workspace_map(self) -> None:
        """U100: draft CURSIV.md from the folders already in the workspace; saved only on Save,
        through the file tool (which never overwrites an existing file without approval)."""
        workspace = self._cfg.get("workspace", "") if self._cfg.get("file_access") else ""
        if not workspace:
            self._append_system("Choose a workspace and turn file access on first (or say: work in my … folder).")
            return
        from PyQt6.QtWidgets import QMessageBox
        from cursiv_engine.core import file_access, guidance
        draft = guidance.draft_map(workspace)
        box = QMessageBox(self)
        box.setWindowTitle("Workspace map (CURSIV.md)")
        box.setText("A first map of this workspace, drafted from its folders. Save it as CURSIV.md? "
                    "It's a readable file in the workspace; you can edit it any time.")
        box.setDetailedText(draft)
        box.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Save:
            self._append_system("Nothing was written.")
            return
        receipt = file_access.perform("create_file", {"path": guidance.MAP, "content": draft}, workspace)
        self._append_system(receipt.render() if hasattr(receipt, "render") else str(receipt))

    def _show_memory_folder(self) -> None:
        """U100: memory as readable .md files. On a USB drive, the drive's folder; on a computer
        (where memory is encrypted) a copy wherever the person chooses, with a warning."""
        from pathlib import Path
        from cursiv_engine.memory import markdown, semantic
        folder = markdown.portable_folder()
        if folder is None:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            QMessageBox.information(self, "Memory as readable files",
                                    "Your memory is encrypted on this computer. Cursiv will write a READABLE copy "
                                    "(one .md file per memory, plus MEMORY.md) to a folder you choose. Anyone who can "
                                    "open that folder can read it. Changing the files doesn't change Cursiv's memory.")
            chosen = QFileDialog.getExistingDirectory(self, "Where should the readable copy go?")
            if not chosen:
                self._append_system("Nothing was written.")
                return
            folder = Path(chosen) / "Cursiv memory"
        try:
            done = markdown.export(semantic.current_person(), folder)
        except Exception as exc:
            self._append_system(f"The memory files weren't written: {exc}")
            return
        self._append_system(f"Wrote {done['memories']} memories as readable files: {folder}")
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _show_suggestions(self) -> None:
        """Guesses from the last exchange, offered as "Remember this?" (memory/suggestions.py)."""
        if self._streaming:
            QTimer.singleShot(4000, self._show_suggestions)
            return
        try:
            from cursiv_engine.memory import semantic, suggestions
            rows = suggestions.unshown(semantic.current_person())
        except Exception:
            return
        if rows:
            import chat_badges
            self._force_new_block()
            self._append_html_block(chat_badges.suggestion_card(rows))

    def _answer_suggestion(self, what: str, sid: str) -> None:
        try:
            from cursiv_engine.memory import semantic, suggestions
            person = semantic.current_person()
            text = suggestions.confirm(person, sid) if what == "save" else suggestions.dismiss(person, sid)
        except Exception as exc:
            text = f"Not saved: {exc}"
        self._append_system(text)

    def _show_picking_up(self, conv_id: str) -> None:
        try:
            from cursiv_engine.memory import session_notes
            note = session_notes.set_active(conv_id)
        except Exception:
            return
        line = session_notes.picking_up(note) if note else ""
        if line:
            self._append_system(line)

    def _update_session_note(self) -> None:
        """In the background after a turn: Done from Cursiv's records each time; the model's
        summary every few exchanges, from the local model only."""
        conv_id, history = self._conv_id, list(self._history)
        if not conv_id or not history:
            return

        def work():
            try:
                from cursiv_engine.memory import session_notes
                from cursiv_engine.ui import chat_app as _ca
                import conversations
                title = next((c["title"] for c in conversations.list_all() if c["id"] == conv_id), "Conversation")
                ask = (lambda m: _ca._local_llm(m, 260)) if _ca._local_model_ready() else None
                note = session_notes.update(conv_id, title, history, ask)
                if session_notes._active.get("conv") == conv_id:
                    session_notes._active["note"] = note
            except Exception:
                pass                                 # a note is a convenience; never break the chat
        threading.Thread(target=work, daemon=True, name="cursiv-session-note").start()

    def _propose_action(self, text: str):
        """U99: plain words that might be an action -> one canonical command, from the
        LOCAL model only (never an online one), checked by core/intent.py."""
        try:
            from cursiv_engine.core import intent, notebook_proposals
            # Notebook corrections never need the model: Cursiv finds the record and checks the old value.
            fixed = notebook_proposals.correction(text)
            if fixed is not None:
                return fixed
            observed = notebook_proposals.observation(text)
            if observed is not None:
                return observed
            if not intent.might_be_action(text):
                return None
            parsed = notebook_proposals.record(text)
            if notebook_proposals.understood(parsed):
                return parsed                      # Cursiv's parser read all of it; no model rewording
            from cursiv_engine.ui import chat_app as _ca
            proposal = None
            if _ca._local_model_ready():
                self._signals.stage.emit("Working out what you asked for…")
                workspace = self._cfg.get("workspace", "") if self._cfg.get("file_access") else ""
                proposal = intent.propose(text, lambda messages: _ca._local_llm(messages, 220), workspace)
            # No model, or it found no action: a plain-words record still gets a card from the parser.
            return proposal or parsed
        except Exception:
            return None

    def _memory_confirmation(self, text: str, history: list[dict]):
        """Preview an explicit memory save before the desktop calls the native writer."""
        from cursiv_engine.memory import intents
        from cursiv_engine.core.intent import ACTIONS, Proposal
        actions = intents._parse(text)
        if not actions or not any(action.operation == intents.SAVE for action in actions):
            return None
        action = ACTIONS['memory.save']
        if len(actions) != 1:
            return Proposal(action, {'fact': text}, '', ['Save one memory at a time so you can check its preview.'])
        requested = actions[0]
        content = requested.content
        if requested.reference:
            candidates = intents._context_candidates(history, content)
            if len(candidates) != 1:
                return Proposal(action, {'fact': content}, '', ['What should I remember? State the fact in your own words.'])
            content = candidates[0]
        return Proposal(action, {'fact': content}, 'remember ' + content, [], edit_text=text)

"""GUI-owned continuity and turn-scoped worker publication, no inference here."""
import copy
import threading
import types
import uuid

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton
from cursiv_engine.chat import continuity


_STATE = ('_pending_history_append', '_pending_intent', '_pending_notebook_receipt',
          '_pending_file_receipts', '_pending_answer_evidence', '_pending_memory_receipt',
          '_pending_write_context', '_reply_is_chat')


class _Signal:
    def __init__(self, view, name):
        self.view, self.name = view, name

    def emit(self, *args):
        view = self.view
        state = {key: copy.deepcopy(getattr(view, key, None)) for key in _STATE}
        if self.name == 'run_event':
            target, event = args
            event = dict(event, worker_state=state)
        else:
            target, event = view._target, dict(kind='worker_signal', signal=self.name,
                                             args=args, worker_state=state)
        if event.get('kind') == 'done' or self.name == 'done':
            # Only application command handlers mutate this snapshot. Apply
            # their configuration changes on the owning GUI turn, never by
            # writing through to a later turn or another person's settings.
            event['config_delta'] = {key: copy.deepcopy(value) for key, value in view._cfg.items()
                                     if key not in view._initial_cfg or view._initial_cfg[key] != value}
        try:
            view._panel._signals.run_event.emit(target, event)
        except RuntimeError:
            pass  # the window may have closed while a transport unwound


class _Signals:
    def __init__(self, view):
        self.view = view

    def __getattr__(self, name):
        return _Signal(self.view, name)


class _WorkerView:
    """Keep an old worker's pending state out of the next turn's GUI state."""
    def __init__(self, panel, target):
        self._panel, self._target = panel, target
        self._signals = _Signals(self)
        for name in (*_STATE, '_cfg', '_conv_id', '_cancel_event', '_review_generation',
                     '_provider_turn_authorized', '_provider_turn_destination', '_continuity_id'):
            value = getattr(panel, name, None)
            setattr(self, name, copy.deepcopy(value) if name in (*_STATE, '_cfg') else value)
        self._initial_cfg = copy.deepcopy(self._cfg)

    def __getattr__(self, name):
        value = getattr(self._panel, name)
        if name in ('_current_run_target', '_queue_review'):
            return value
        if name == '_run_target':
            return lambda: self._target
        if name == '_worker_view':
            return lambda target: self
        if isinstance(value, types.MethodType) and value.__self__ is self._panel:
            return types.MethodType(value.__func__, self)
        return value


class ContinuityMixin:
    def _on_saved(self, conv_id: str, error: str, revision: int) -> None:
        if conv_id == self._conv_id and revision == self._save_revision:
            self._dirty = bool(error)
            self._save_error = bool(error)
            if error:
                self._status.setText("Conversation could not be saved. Use Save to retry.")
                self._status.setToolTip(error)
        self.conversation_changed.emit()

    def _stop_generation(self) -> None:
        if not self._streaming:
            return
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._pause_visible_response()

    def _on_cancelled(self) -> None:
        from theme import SILV2
        if not self._streaming:
            return
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
        self._cancel_event = None
        self._streaming = False
        self._send_btn.setEnabled(True)
        self._voice_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status.setText("")
        self._input.setFocus()
        self._persist_interruption()

    def _worker_view(self, target):
        return _WorkerView(self, target)

    def _ensure_native_scope(self, target):
        if self._conv_id is None:
            self._conv_id = self._continuity_id
            self._signals.run_event.emit(target, dict(kind='native_scope', conversation_id=self._conv_id))

    def _build_continuity(self, layout):
        self._continuity_id = uuid.uuid4().hex[:12]
        row = QHBoxLayout()
        self._paused_label = QLabel('Paused response')
        self._paused_tasks = QComboBox()
        self._resume_btn = QPushButton('Resume')
        self._dismiss_paused_btn = QPushButton('Dismiss')
        self._resume_btn.clicked.connect(lambda: self._resume_checkpoint())
        self._dismiss_paused_btn.clicked.connect(self._dismiss_checkpoint)
        for widget in (self._paused_label, self._paused_tasks, self._resume_btn, self._dismiss_paused_btn):
            row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)
        self._resume_context = None
        self._refresh_paused()

    def _paused(self):
        from cursiv_engine.core import style
        from cursiv_engine.memory import semantic
        try:
            settings = style.presentation(semantic.current_person())
        except (OSError, ValueError):
            settings = dict(checkpoint_limit=8, checkpoint_days=14)
        return continuity.available(self._history, self._conv_id or getattr(self, '_continuity_id', None),
            limit=settings['checkpoint_limit'], days=settings['checkpoint_days'])

    def _refresh_paused(self):
        if not hasattr(self, '_paused_tasks'):
            return
        selected = self._paused_tasks.currentData()
        self._paused_tasks.clear()
        for row in self._paused():
            cp = row['interruption']
            self._paused_tasks.addItem(cp['original_request'][:65], cp['checkpoint_id'])
        index = self._paused_tasks.findData(selected)
        if index >= 0:
            self._paused_tasks.setCurrentIndex(index)
        visible = self._paused_tasks.count() > 0
        for widget in (self._paused_label, self._paused_tasks, self._resume_btn, self._dismiss_paused_btn):
            widget.setVisible(visible)
            widget.setEnabled(not self._streaming)

    def _dismiss_checkpoint(self):
        selected = self._paused_tasks.currentData()
        for row in self._paused():
            if row['interruption']['checkpoint_id'] == selected:
                row.pop('interruption', None)
                self._persist_interruption()
                break
        self._refresh_paused()

    def _persist_interruption(self):
        """Ordered existing writer, no model title, session note or learning."""
        from chat_panel import autosave_enabled
        self._dirty = True
        if self._conversation_saved or autosave_enabled():
            try:
                self.save_conversation(background=True, allow_model_title=False)
            except (OSError, ValueError, RuntimeError):
                self._save_error = True
                self._status.setText('Paused task kept in this window; saving failed. Use Save to retry.')

    def _pause_visible_response(self):
        if not self._streaming:
            return
        self._session_note_model_allowed = False
        self._pending_history_append = None
        if self._pending_write_context.get('request') is not None:
            self._append_system('An already approved write may still finish. Check its result before requesting it again.')
        if self._reply_is_chat and not self._pending_write_context:
            from chat_panel import autosave_enabled
            self._continuity_id = self._conv_id or getattr(self, '_continuity_id', None) or uuid.uuid4().hex[:12]
            if self._conv_id or autosave_enabled():
                self._conv_id = self._continuity_id
            context = getattr(self, '_resume_context', None)
            original = context['data']['original_request'] if context else self._turn_text
            prior = context['data']['previously_displayed_response'] if context else ''
            cp = continuity.checkpoint(original, self._continuity_id, uuid.uuid4().hex,
                self._cfg.get('selected_provider', '') or 'local_auto', self._cfg.get('selected_model', ''),
                prior=prior, parent=context['checkpoint_id'] if context else None)
            if context:
                self._finish_checkpoint('continued')
            provenance = getattr(self, '_stream_provenance', None)
            cp['provenance'] = provenance
            row = dict(role='assistant', content=self._reply_text, interruption=cp)
            if provenance:
                row['provider_provenance'] = provenance
            self._history.extend([dict(role='user', content=original), row])
        self._on_cancelled()
        self._resume_context = None
        self._refresh_paused()

    def _finish_checkpoint(self, status='completed'):
        context = getattr(self, '_resume_context', None)
        if context:
            for row in self._history:
                cp = row.get('interruption') or {}
                if cp.get('checkpoint_id') == context['checkpoint_id']:
                    cp['status'] = status
                    cp['resume_count'] = cp.get('resume_count', 0) + 1
                    cp.pop('prior_response', None)
            if status == 'completed' and self._history and self._history[-1].get('role') == 'assistant':
                self._history[-1]['continuation'] = dict(checkpoint_id=context['checkpoint_id'],
                    exact_repeated_prefix_chars=continuity.exact_overlap(
                        context['data']['previously_displayed_response'], self._history[-1]['content']))

    def _resume_checkpoint(self, checkpoint_id=None):
        if self._streaming:
            return
        selected = checkpoint_id or self._paused_tasks.currentData()
        row = next((r for r in self._paused() if r['interruption']['checkpoint_id'] == selected), None)
        if row is None:
            self._append_system('This paused task has expired or is no longer available.')
            self._refresh_paused()
            return
        try:
            context = continuity.prepare(row)
        except ValueError as exc:
            self._append_system(str(exc))
            return
        # Presentation settings are application preferences, not recovered
        # private memories or new file/tool permissions for the continuation.
        from cursiv_engine.core import style
        from cursiv_engine.memory import semantic
        try:
            history = [{k: v for k, v in r.items() if k != 'interruption'} for r in self._history[-6:]]
            context['presentation'] = style.presentation_prompt(semantic.current_person(), context['data']['original_request'], history)
        except (OSError, ValueError):
            context['presentation'] = ''
        cp = row['interruption']
        provider, model = self._cfg.get('selected_provider', '') or 'local_auto', self._cfg.get('selected_model', '')
        force = self._provider_force()
        # Pin the previous resolved backend when the user has not changed auto selection.
        previous = cp.get('provenance') if isinstance(cp.get('provenance'), dict) else {}
        if provider == cp['provider'] and model == cp['model'] and previous.get('requested_model'):
            actual_provider = previous.get('requested_provider') or previous.get('provider')
            if actual_provider:
                force = 'manager:' + actual_provider + '::' + previous['requested_model']
        from cursiv_engine.chat.model_selection import parse
        try:
            parse(force)
        except ValueError as exc:
            self._append_system('Resume blocked: ' + str(exc) + '. The paused task is still available.')
            return
        destination_provider, destination_model = provider, model
        if '::' in force:
            destination_provider, destination_model = force.removeprefix('manager:').split('::', 1)
            self._provider_turn_authorized = self._authorize_provider_turn(
                provider_override=destination_provider, model_override=destination_model)
        else:
            self._provider_turn_authorized = self._authorize_provider_turn()
        self._append_system('Resuming with ' + destination_provider + (' · ' + destination_model if destination_model else '') +
            '. Original selection: ' + cp['provider'] + (' · ' + cp['model'] if cp['model'] else '') +
            '. Text continuation only; new actions need a new request.')
        self._append_user('Resume: ' + cp['original_request'][:160])
        self._begin_turn(continuity.RESUME_REQUEST)
        self._resume_context = context
        target = self._run_target()
        threading.Thread(target=self._run_resume, args=(context, force), kwargs={'turn_target': target}, daemon=True).start()

    def _run_resume(self, context, force, turn_target=None):
        from provider_controls import provider_turn
        @provider_turn
        def run(view, *, turn_target=None):
            from chat_panel import _cursiv_chat, _iter_cancellable, cc
            from cursiv_engine.chat import provider_manager as manager
            from cursiv_engine.chat.activity import guarded
            target = turn_target
            view._reply_is_chat = True
            full = ''
            try:
                view._signals.run_event.emit(target, dict(kind='generation_started'))
                with continuity.use(context):
                    source = _cursiv_chat(continuity.RESUME_REQUEST, [],
                        api_key=view._cfg.get('api_key', ''), files=None,
                        file_access=False, root_path=view._cfg.get('workspace', ''),
                        openai_key=view._cfg.get('openai_key', ''), anthropic_key=view._cfg.get('anthropic_key', ''),
                        confirm_writes=True, force_provider=force, replace_draft=True, review_mode='off')
                    source = guarded(source, lambda: view._current_run_target(target) and not target[1].is_set())
                    for chunk in _iter_cancellable(source, target[1]):
                        if chunk.startswith(cc.WRITE_SENTINEL):
                            raise ValueError('Resume does not execute actions. Submit a new request for the action.')
                        kind = 'replace' if chunk.startswith(cc.REPLACE_SENTINEL) else 'chunk'
                        text = chunk[len(cc.REPLACE_SENTINEL):] if kind == 'replace' else chunk
                        full = text if kind == 'replace' else full + text
                        result = manager.outcome()
                        view._signals.run_event.emit(target, dict(kind=kind, text=text,
                            provenance=result.metadata() if result else None))
                result = manager.outcome()
                if result and result.error:
                    view._signals.run_event.emit(target, dict(kind='error', text=result.error_message))
                else:
                    view._signals.run_event.emit(target, dict(kind='done', history=[('user', 'Resume: '+context['data']['original_request']),
                        ('assistant', full)], provenance=result.metadata() if result else None))
            except Exception as exc:
                view._signals.run_event.emit(target, dict(kind='error', text=str(exc)))
        run(self, turn_target=turn_target)

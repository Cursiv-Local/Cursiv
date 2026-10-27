"""Owned desktop results and follow-up reviews. Only Qt slots touch widgets/history."""
import threading


class ChatReviewMixin:
    def _run_target(self):
        from cursiv_engine.memory import semantic
        return (self._review_generation, self._cancel_event, self._conv_id,
                self._cfg.get('workspace'), self._cfg.get('file_access'), semantic._person_revision)

    def _current_run_target(self, target):
        return target == self._run_target()

    def _on_run_event(self, target, event):
        # A queued Qt event is checked at acceptance, after any conversation/person switch.
        if not self._current_run_target(target):
            if (target[1] is self._cancel_event and self._streaming
                    and target[0] == self._review_generation):
                self._pending_history_append = None
                self._on_cancelled()
            return
        run = event.get('run')
        if run is not None:
            from cursiv_engine.agents.workflow import identity
            if run.owner != identity():
                if target[1] is not None:
                    target[1].set()
                self._pending_history_append = None
                self._on_cancelled()
                return
        kind = event['kind']
        cancelled = target[1] is not None and target[1].is_set()
        if kind in ('chunk', 'replace'):
            if cancelled:
                return
            if run is not None:
                self._last_research_run = run
                self._reply_is_chat = True  # workflow answers use Markdown, not native-action receipt rendering
            (self._on_chunk if kind == 'chunk' else self._on_replace)(event.get('text', ''))
        elif kind == 'error':
            if cancelled:
                self._on_cancelled()
            else:
                self._on_error(event.get('text', 'Run failed.'))
        elif kind == 'image' and not cancelled:
            self._on_image(event['text'])
        elif kind in ('done', 'cancelled'):
            # Profile runs already own all generation/review work. Their metadata note,
            # and native command receipts, must not start an unbudgeted model summary.
            self._session_note_model_allowed = run is None and bool(event.get('exchange')) and kind == 'done' and not cancelled
            self._pending_history_append = event.get('history')
            if kind == 'cancelled' or cancelled:
                self._on_cancelled()
            else:
                if 'exchange' in event:
                    self._last_exchange = event['exchange']
                self._on_done()

    def _deliver_run(self, result, text, target):
        """Owned workflow publication: acceptance/history updates happen on the GUI thread."""
        from chat_panel import _iter_cancellable
        run = result.run
        cancel_event = target[1] or run.budget.cancelled
        previous_valid = run.budget.valid
        run.budget.cancelled = cancel_event
        run.budget.valid = lambda: previous_valid() and self._current_run_target(target)
        publish = lambda **event: self._signals.run_event.emit(target, dict(event, run=run))
        if not self._current_run_target(target):
            run.cancel()
            return
        publish(kind='chunk', text=result.intro + '\n\n')
        parts = []
        try:
            for chunk in _iter_cancellable(result.generator, cancel_event):
                if chunk:
                    parts.append(chunk)
                    publish(kind='chunk', text=chunk)
            if cancel_event.is_set():
                publish(kind='cancelled')
                return
            full = ''.join(parts)
            publish(kind='done', history=[('user', text), ('assistant', full)] if full and text else None)
        except Exception as exc:
            publish(kind='error', text=str(exc))

    def _deliver_command_stream(self, result, text, target):
        """Babel/coding and other legacy streams use the same owned UI publication."""
        from chat_panel import _iter_cancellable, _RATE_SENTINEL
        from cursiv_engine.chat.activity import guard, exclusive, guarded, check_guard
        cancel = target[1] or threading.Event()
        valid = lambda: self._current_run_target(target) and not cancel.is_set()
        publish = lambda **event: self._signals.run_event.emit(target, event)
        full, rate_limited = '', False
        try:
            with guard(valid), exclusive():
                publish(kind='chunk', text=result.intro + '\n\n')
                for chunk in _iter_cancellable(guarded(result.generator, valid), cancel):
                    if chunk == _RATE_SENTINEL:
                        rate_limited = True
                    elif chunk:
                        full += chunk
                        publish(kind='chunk', text=chunk)
                if cancel.is_set():
                    publish(kind='cancelled')
                    return
                check_guard()
                if not full:
                    publish(kind='chunk', text='[Rate limited or no response received.]' if rate_limited else '[No response received from the provider.]')
                if full and result.on_complete:
                    try:
                        result.on_complete(full)
                    except Exception:
                        pass  # retained compatibility for optional follow-up callbacks
                publish(kind='done', history=[('user', text), ('assistant', full[-6000:])] if full and text else None)
        except Exception as exc:
            publish(kind='cancelled' if cancel.is_set() else 'error', text=str(exc))

    def _init_review(self):
        self._review_generation = 0
        self._pending_review = None
        self._review_cancel = None
        self._signals.review_done.connect(self._on_review_done)
        self._signals.review_state.connect(self._on_review_state)
        self.destroyed.connect(lambda: self._cancel_review())

    def _cancel_review(self):
        self._review_generation = getattr(self, '_review_generation', 0) + 1
        pending = getattr(self, '_pending_review', None)
        if pending:
            pending[1].cancelled.set()
        event = getattr(self, '_review_cancel', None)
        if event:
            event.set()
        self._pending_review = self._review_cancel = None
        if hasattr(self, '_check_progress'):
            self._check_progress.hide()

    def _queue_review(self, key, job, cancel_event):
        # Called by the chat worker; no Qt calls and no model calls here.
        if key != self._review_generation or (cancel_event and cancel_event.is_set()):
            job.cancelled.set()
            return
        self._pending_review = (key, job)

    def _start_review(self):
        pending, self._pending_review = self._pending_review, None
        if not pending or pending[0] != self._review_generation or not self._history:
            return
        key, job = pending
        index, original = len(self._history) - 1, self._history[-1].get('content', '')
        if self._history[index].get('role') != 'assistant' or job.cancelled.is_set():
            return
        self._review_cancel = job.cancelled
        if not getattr(self, '_save_error', False):
            self._status.setText('Draft ready')
        signals = self._signals

        def work():
            from cursiv_engine.core.verify import PassResult
            try:
                result = job.run(on_model_state=lambda stage: signals.review_state.emit((key, index, original), stage))
            except Exception:
                result = PassResult(status='unavailable', skip_learn=True,
                                    append='Model review unavailable; the answer is unverified.')
            if not job.cancelled.is_set():
                try:
                    signals.review_done.emit((key, index, original), result)
                except RuntimeError:
                    pass  # the window was destroyed; never touch a widget from this thread
        threading.Thread(target=work, daemon=True, name='cursiv-answer-review').start()

    def _on_review_state(self, target, stage):
        key, index, original = target
        if (key != self._review_generation or self._streaming or index >= len(self._history)
                or self._history[index].get('content') != original or self._review_cancel is None
                or self._review_cancel.is_set()):
            return
        self._check_progress.setVisible(bool(stage))
        if not getattr(self, '_save_error', False):
            self._status.setText(f'Draft ready · {stage}…' if stage else 'Draft ready')

    def _on_review_done(self, target, result):
        key, index, original = target
        if (key != self._review_generation or self._streaming or index >= len(self._history)
                or self._history[index].get('content') != original
                or (self._review_cancel and self._review_cancel.is_set())):
            return
        self._review_cancel = None
        self._check_progress.hide()
        from cursiv_engine.core.feedback import review_status
        if not getattr(self, '_save_error', False):
            self._status.setText(review_status(result))
        from cursiv_engine.chat.review import followup
        note = followup(result)
        if result is None:
            return
        if note:
            text = original + note
            self._on_replace(text)  # this generation's latest message only; never rebuild history
            self._render_reply()
            self._end_ai_reply()
            self._history[index]['content'] = text
            if self._last_exchange:
                self._last_exchange = (self._last_exchange[0], text)
        self._history[index]['background_review'] = {
            'status': result.status, 'issues': [p.record() for p in result.issues],
            'scope': 'bounded local model review; not a factual guarantee'}
        self._after_turn()

"""Desktop follow-up reviews. Widgets/history are touched only by Qt result slots."""
import threading


class ChatReviewMixin:
    def _init_review(self):
        self._review_generation = 0
        self._pending_review = None
        self._review_cancel = None
        self._signals.review_done.connect(self._on_review_done)
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
        self._status.setText('Answer ready · background check running')
        signals = self._signals

        def work():
            from cursiv_v215.core.verify import PassResult
            try:
                result = job.run()
            except Exception:
                result = PassResult(status='unavailable', skip_learn=True,
                                    append='Model review unavailable; the answer is unverified.')
            if not job.cancelled.is_set():
                try:
                    signals.review_done.emit((key, index, original), result)
                except RuntimeError:
                    pass  # the window was destroyed; never touch a widget from this thread
        threading.Thread(target=work, daemon=True, name='cursiv-answer-review').start()

    def _on_review_done(self, target, result):
        key, index, original = target
        if (key != self._review_generation or self._streaming or index >= len(self._history)
                or self._history[index].get('content') != original
                or (self._review_cancel and self._review_cancel.is_set())):
            return
        self._review_cancel = None
        self._status.setText('')
        from cursiv_v215.chat.review import followup
        note = followup(result)
        if not note:
            return
        text = original + note
        self._on_replace(text)  # this generation's latest message only; never rebuild history
        self._render_reply()
        self._end_ai_reply()
        self._history[index]['content'] = text
        self._history[index]['background_review'] = {
            'status': result.status, 'issues': [p.record() for p in result.issues]}
        if self._last_exchange:
            self._last_exchange = (self._last_exchange[0], text)
        self._after_turn()

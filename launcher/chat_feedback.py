"""Quiet application-owned state and receipts. All methods run on the GUI thread."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QProgressBar, QHBoxLayout

import theme


class ChatFeedbackMixin:
    def _build_feedback(self, layout):
        self._turn_policy = None
        self._context_indicator = QLabel('')
        self._context_indicator.setTextFormat(Qt.TextFormat.PlainText)
        self._context_indicator.setWordWrap(True)
        self._context_indicator.setStyleSheet(f'color: {theme.MUTED}; font-size: 12px;')
        layout.addWidget(self._context_indicator)
        self._receipt_line = QLabel('')
        self._receipt_line.setTextFormat(Qt.TextFormat.PlainText)
        self._receipt_line.setWordWrap(True)
        self._receipt_line.setStyleSheet(f'color: {theme.MUTED}; font-size: 12px;')
        self._receipt_line.hide()
        layout.addWidget(self._receipt_line)
        self._signals.tool_receipt.connect(self._on_tool_receipt)
        self._signals.state_changed.connect(self._refresh_status_pill)

    def _build_check_progress(self, layout):
        row = QHBoxLayout()
        self._check_progress = QProgressBar()
        self._check_progress.setRange(0, 0)
        self._check_progress.setTextVisible(False)
        self._check_progress.setFixedSize(44, 3)
        self._check_progress.setAccessibleName('Local model review running')
        self._check_progress.setStyleSheet(
            f'QProgressBar {{ border: none; background: {theme.BORDER}; }}'
            f'QProgressBar::chunk {{ background: {theme.ACCENT}; }}')
        self._check_progress.hide()
        row.addWidget(self._check_progress)
        row.addWidget(self._status, 1)
        layout.addLayout(row)

    def _set_turn_feedback(self, text=''):
        from cursiv_engine.core.turn_policy import for_text
        self._turn_text = text
        self._turn_policy = for_text(text)
        self._receipt_line.clear()
        self._receipt_line.hide()
        self._refresh_context_indicator()

    def _refresh_context_indicator(self):
        if not hasattr(self, '_context_indicator'):
            return
        cfg = getattr(self, '_cfg', {})
        files = cfg.get('file_access')
        parts = ['Files on' if files is True else 'Files off' if files is False else 'File access unknown']
        workspace = str(cfg.get('workspace') or '')
        if workspace:
            parts.append('Workspace: ' + (Path(workspace).name or workspace))
        policy = self._turn_policy
        if policy is not None:
            if not policy.inspect:
                parts.append('This turn: talk-only')
            elif not policy.change:
                parts.append('This turn: read-only')
            elif not policy.memory_write or not policy.automatic_memory:
                parts.append('This turn: memory restricted')
        # Only backend receipts establish notebook context. Reopening a saved
        # conversation restores the context without inventing an active project.
        import re
        turn = getattr(self, '_turn_text', '')
        relevant = not turn or re.search(r'(?i)\b(?:field|notebook|observations?|samples?|site|log|record|transect)\b', turn)
        for row in reversed(getattr(self, '_history', []) if relevant else []):
            receipt = row.get('notebook_receipt') or {}
            if receipt.get('ok') and receipt.get('status') in ('saved', 'already_recorded'):
                records = receipt.get('records') or []
                if records:
                    record = records[0]
                    parts.append('Last notebook site: ' + str(record.get('site') or 'unnamed'))
                    if record.get('sample_id'):
                        parts.append('Last notebook sample: ' + str(record['sample_id']))
                    break
        self._context_indicator.setText(' · '.join(parts))
        self._context_indicator.setToolTip(
            ('Configured workspace: ' + workspace + '\n' if workspace else '') +
            'Access and availability are checked when an operation runs.\n'
            'Turn limits do not change offline mode or conversation-history settings.')

    def _reset_feedback(self):
        self._turn_text = ''
        self._turn_policy = None
        self._receipt_line.clear()
        self._receipt_line.hide()
        self._status.clear()
        self._refresh_context_indicator()

    def _on_tool_receipt(self, payload):
        from cursiv_engine.core import feedback
        domain, receipt = payload
        formatter = {'filesystem': feedback.file_receipt, 'notebook': feedback.notebook_receipt,
                     'memory': feedback.memory_receipt}.get(domain)
        text = formatter(receipt) if formatter else str(receipt.get('summary') or '')
        self._receipt_line.setText(text)
        self._receipt_line.setVisible(bool(text))
        # Native results own the line, even while model generation is underway.
        self._receipt_line.setToolTip('Application result; model prose cannot set this receipt.')

    def _capture_file_result(self, result):
        """Worker-side adapter. Typed executed results only; never inspect prose."""
        from cursiv_engine.core.file_access import FileResult
        from cursiv_engine.core.tools import ToolOutcome
        from cursiv_engine.core.answer_evidence import AnswerEvidence
        if isinstance(result, AnswerEvidence):
            self._pending_answer_evidence = result.receipt()
            return
        if isinstance(result, FileResult):
            receipt = result.receipt()
            self._pending_file_receipts.append(receipt)
            self._signals.tool_receipt.emit(('filesystem', receipt))
        elif isinstance(result, ToolOutcome):
            summary = ('Checked computer state' if result.ok and result.label == 'system_info' else
                       'Tool action not confirmed · ' + result.label if not result.ok else
                       'Tool result · ' + result.label)
            self._signals.tool_receipt.emit(('tool', {'summary': summary}))

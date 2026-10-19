"""
The Cross-Check confirmation (core/crosscheck.py): which provider, and exactly what will leave this
computer. Nothing is sent unless the person presses Send in this window.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                             QVBoxLayout)

import theme
from cursiv_v215.core import crosscheck


class CrossCheckDialog(QDialog):
    """exec() == Accepted means the person confirmed; .payload is what to send."""

    def __init__(self, question: str, answer: str, providers: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Cross-check this answer")
        self.resize(720, 640)
        self._question, self._answer = question, answer
        self.payload: crosscheck.Payload | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(10)

        title = QLabel("Ask a second AI to review this answer")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        outer.addWidget(title)

        row = QHBoxLayout()
        row.addWidget(QLabel("Send to:"))
        self._provider = QComboBox()
        for pid, who in providers:
            self._provider.addItem(who, pid)
        self._provider.currentIndexChanged.connect(self._refresh)
        row.addWidget(self._provider, 1)
        outer.addLayout(row)

        self._warning = QLabel()
        self._warning.setWordWrap(True)
        self._warning.setStyleSheet(f"color: {theme.AMBER}; font-weight: 600;")
        outer.addWidget(self._warning)

        outer.addWidget(QLabel("Exactly what will be sent:"))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        outer.addWidget(self._preview, 1)

        note = QLabel("Only this question and answer are sent: no memories, documents, field notes, other parts "
                      "of the conversation or files. The review is an opinion to weigh; it won't change Cursiv's "
                      "answer and isn't added to the conversation.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.MUTED};")
        outer.addWidget(note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(theme.ghost_button())
        cancel.clicked.connect(self.reject)
        self._send = QPushButton("Send")
        self._send.setStyleSheet(theme.primary_button())
        self._send.clicked.connect(self._confirm)
        buttons.addWidget(cancel)
        buttons.addWidget(self._send)
        outer.addLayout(buttons)
        self._refresh()

    def _refresh(self) -> None:
        pid = self._provider.currentData()
        try:
            self.payload = crosscheck.build(pid, self._question, self._answer)
        except ValueError as exc:
            self.payload = None
            self._preview.setPlainText(str(exc))
            self._send.setEnabled(False)
            return
        self._warning.setText(f"This text will leave this computer and be sent over the internet to "
                              f"{self.payload.to}, under your own key, and handled by their terms. "
                              + ("It's long, so it was cut to fit; the preview shows exactly what goes."
                                 if self.payload.trimmed else ""))
        self._preview.setPlainText(self.payload.preview())
        self._send.setText(f"Send to {self.payload.to}")
        self._send.setEnabled(True)

    def _confirm(self) -> None:
        if self.payload is not None:
            self.accept()

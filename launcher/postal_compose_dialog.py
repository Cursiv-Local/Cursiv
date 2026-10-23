"""
Cursiv — Postal compose dialog (native GUI edition of the terminal CLI's
"write to <name>" sealed-letter flow).

Recipient + optional hint + multi-line body, then seals via the exact
same cursiv_engine.postal.sealed_store.seal_letter() call the terminal CLI
uses (through chat_commands.postal_compose) -- machine-bound encryption,
Ed25519 signing if an identity is set up. Sealing does real key-derivation
work (tens of thousands of PBKDF2 iterations), so it runs on a background
thread with a small progress indicator rather than freezing the dialog.
"""
from __future__ import annotations

import threading

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QMessageBox,
)

import chat_commands as cc
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2  # one palette for every window (theme.py)

class _SealSignals(QObject):
    done = pyqtSignal(object)   # TextResult
    error = pyqtSignal(str)


class PostalComposeDialog(QDialog):
    def __init__(self, sender_user: str, recipient_hint: str = "", parent=None):
        super().__init__(parent)
        self._sender_user = sender_user
        self.result_text: str = ""
        self._signals = _SealSignals()
        self._signals.done.connect(self._on_sealed)
        self._signals.error.connect(self._on_error)

        self.setWindowTitle("Cursiv — Sealed Letter")
        self.setMinimumSize(480, 420)
        self.setStyleSheet(f"QDialog {{ background: {BG}; }} QLabel {{ color: {SILVER}; }}")

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        header = QLabel("⬡ Sealed Letter")
        header.setStyleSheet(f"color: {GOLD}; font-size: 15px; font-weight: 700;")
        lay.addWidget(header)
        note = QLabel(
            "Machine-bound encryption -- readable only on this machine unless exported "
            "with a passphrase (seal export)."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        lay.addWidget(note)

        lay.addWidget(self._label("To"))
        self._to_field = QLineEdit(recipient_hint)
        self._style_field(self._to_field)
        lay.addWidget(self._to_field)

        lay.addWidget(self._label("Public hint (optional -- shown before opening)"))
        self._hint_field = QLineEdit()
        self._style_field(self._hint_field)
        lay.addWidget(self._hint_field)

        lay.addWidget(self._label("Letter"))
        self._body_field = QPlainTextEdit()
        self._body_field.setStyleSheet(
            f"QPlainTextEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 8px; font-size: 13px; }}"
        )
        lay.addWidget(self._body_field, 1)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        lay.addWidget(self._status)

        row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {SILV2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)

        self._seal_btn = QPushButton("Seal & Send")
        self._seal_btn.setStyleSheet(
            "QPushButton { background: #d4b04c; color: #17120a; font-weight: 600; border: none; border-radius: 6px; padding: 8px; }"
            "QPushButton:disabled { background: #1a1a2e; color: #666; }"
        )
        self._seal_btn.clicked.connect(self._seal)
        row.addWidget(self._seal_btn)
        lay.addLayout(row)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px; font-weight: 600;")
        return lbl

    def _style_field(self, field: QLineEdit) -> None:
        field.setStyleSheet(
            f"QLineEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 8px; font-size: 13px; }}"
        )

    def _seal(self) -> None:
        to = self._to_field.text().strip()
        body = self._body_field.toPlainText().strip()
        if not to or not body:
            QMessageBox.information(self, "Sealed Letter", "Recipient and letter body are required.")
            return
        hint = self._hint_field.text().strip()
        self._seal_btn.setEnabled(False)
        self._status.setText("Sealing -- deriving keys, signing, encrypting...")
        threading.Thread(target=self._run_seal, args=(to, hint, body), daemon=True).start()

    def _run_seal(self, to: str, hint: str, body: str) -> None:
        try:
            result = cc.postal_compose(self._sender_user, to, hint, body)
            self._signals.done.emit(result)
        except Exception as e:
            self._signals.error.emit(str(e))

    def _on_sealed(self, result) -> None:
        self.result_text = result.text
        self.accept()

    def _on_error(self, message: str) -> None:
        self._seal_btn.setEnabled(True)
        self._status.setText("")
        QMessageBox.warning(self, "Sealed Letter", f"Sealing failed: {message}")

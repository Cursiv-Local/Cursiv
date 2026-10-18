"""
Cursiv — Legacy Vault dialog (native GUI edition of the terminal CLI's
"legacy" family-letter vault).

Ports the family letter vault to a dialog: PIN-gated login, read letters
waiting for you (with an ephemeral AI companion chat underneath, never
saved to session/strand -- matches the CLI), write new letters (with an
optional AI-polish pass), export your letters to send to Joshua, and
manage letters you've written (read/edit/delete -- delete keeps the same
four-step confirmation the CLI uses, since this is permanent and personal).

Auth failures (unrecognized name, no PIN set, wrong PIN) all show the same
generic message, matching the terminal CLI's deliberate vagueness -- a
wrong guess should not reveal whether a name is a real family member.
"""
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QLabel, QLineEdit,
    QPushButton, QTextBrowser, QPlainTextEdit, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog, QCheckBox, QStackedWidget, QSizePolicy,
)

import chat_commands as cc
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2  # one palette for every window (theme.py)

_LEGACY_NOTICE = (
    "This is not time-travel in the novelty sense. But it is the closest we "
    "can get. Please take this seriously. The responses may vary, but the "
    "intent is sound. Reason through what you see for yourself. Do not let "
    "the AI tell you what to think."
)

_AUTH_FAIL = "Not recognized, or the code doesn't match. Try again."


class _CompanionSignals(QObject):
    chunk = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)


class LegacyVaultDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._profile: Optional[dict] = None
        self._inbox: list[dict] = []
        self._outbox: list[dict] = []
        self._companion_history: list[dict] = []
        self._companion_signals = _CompanionSignals()
        self._companion_signals.chunk.connect(self._on_companion_chunk)
        self._companion_signals.done.connect(self._on_companion_done)
        self._companion_signals.error.connect(self._on_companion_error)
        self._companion_streaming = False

        self.setWindowTitle("Cursiv — Legacy Vault")
        self.setMinimumSize(640, 560)
        self.setStyleSheet(f"QDialog {{ background: {BG}; }} QLabel {{ color: {SILVER}; }}")

        self._stack = QStackedWidget()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.addWidget(self._stack)

        self._stack.addWidget(self._build_login())
        self._stack.addWidget(QWidget())   # placeholder for vault home, built after login
        self._stack.addWidget(QWidget())   # placeholder for letter viewer

    # ── Login ────────────────────────────────────────────────────────────

    def _build_login(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)

        header = QLabel("𓂀  Winkler Legacy Guardian")
        header.setStyleSheet(f'color: {GOLD}; font-size: 18px; font-weight: 700; font-family: "Segoe UI", "Segoe UI Historic";')
        lay.addWidget(header)

        lay.addWidget(self._note_label(_LEGACY_NOTICE))
        lay.addSpacing(10)

        self._name_field = self._field(lay, "Name")
        self._dob_field = self._field(lay, "Date of birth")
        self._pin_field = self._field(lay, "Code", password=True)
        self._pin_field.returnPressed.connect(self._try_login)

        self._login_error = QLabel("")
        self._login_error.setStyleSheet("color: #ff6666; font-size: 12px;")
        self._login_error.setWordWrap(True)
        lay.addWidget(self._login_error)

        enter_btn = QPushButton("Enter")
        enter_btn.setFixedHeight(40)
        enter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        enter_btn.setStyleSheet(
            "QPushButton { background: #d4b04c; color: #17120a; font-weight: 600; border: none; border-radius: 8px; }"
            "QPushButton:hover { background: #e2c062; }"
        )
        enter_btn.clicked.connect(self._try_login)
        lay.addWidget(enter_btn)
        lay.addStretch(1)
        return w

    def _field(self, lay: QVBoxLayout, label: str, password: bool = False) -> QLineEdit:
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px; font-weight: 600;")
        lay.addWidget(lbl)
        field = QLineEdit()
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setStyleSheet(
            f"QLineEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 8px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border-color: {LGOLD}; }}"
        )
        lay.addWidget(field)
        return field

    def _note_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        return lbl

    def _try_login(self):
        name = self._name_field.text().strip()
        dob = self._dob_field.text().strip()
        pin = self._pin_field.text().strip()
        if not (name and dob and pin):
            self._login_error.setText("Fill in all three fields.")
            return

        profile = cc._fam_detect(name, dob) if cc._LEGACY_OK else None
        if not profile or not cc._fam_pin_is_set(profile["key"]) or not cc._fam_verify_pin(profile["key"], pin):
            self._login_error.setText(_AUTH_FAIL)
            self._pin_field.clear()
            return

        self._profile = profile
        self._login_error.setText("")
        self._enter_vault()

    # ── Vault home ───────────────────────────────────────────────────────

    def _enter_vault(self):
        self._inbox = cc._legacy_letters_for(self._profile["key"])
        self._outbox = cc._legacy_letters_by(self._profile["key"])

        home = QWidget()
        lay = QVBoxLayout(home)
        lay.setSpacing(10)

        header = QLabel(f"Welcome, {self._profile['display']}.")
        header.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: 700;")
        lay.addWidget(header)
        lay.addWidget(self._note_label(_LEGACY_NOTICE))

        lay.addWidget(self._section_label(f"LETTERS WAITING FOR YOU ({len(self._inbox)})"))
        self._inbox_list = QListWidget()
        self._style_list(self._inbox_list)
        for e in self._inbox:
            item = QListWidgetItem(
                f"from {e.get('from_display', '?')}  ·  {e.get('subject', '(no subject)')}  ·  {e.get('written', '')[:10]}"
                + ("  (revised)" if e.get("revised") else "")
            )
            self._inbox_list.addItem(item)
        lay.addWidget(self._inbox_list)

        read_btn = QPushButton("Read Selected Letter")
        read_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        read_btn.setStyleSheet(self._btn_style())
        read_btn.clicked.connect(self._open_inbox_letter)
        lay.addWidget(read_btn)

        lay.addWidget(self._section_label(f"LETTERS YOU'VE WRITTEN ({len(self._outbox)})"))
        self._outbox_list = QListWidget()
        self._style_list(self._outbox_list)
        for e in self._outbox:
            item = QListWidgetItem(
                f"for {e.get('for_display', '?')}  ·  {e.get('subject', '(no subject)')}  ·  {e.get('written', '')[:10]}"
            )
            self._outbox_list.addItem(item)
        lay.addWidget(self._outbox_list)

        row = QHBoxLayout()
        for label, slot in (
            ("Read", self._read_own_letter), ("Edit", self._edit_own_letter), ("Delete", self._delete_own_letter),
        ):
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(self._btn_style())
            b.clicked.connect(slot)
            row.addWidget(b)
        lay.addLayout(row)

        row2 = QHBoxLayout()
        write_btn = QPushButton("Write New Letter")
        write_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        write_btn.setStyleSheet(self._btn_style(primary=True))
        write_btn.clicked.connect(self._write_letter)
        row2.addWidget(write_btn)

        export_btn = QPushButton("Export My Letters")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(self._btn_style())
        export_btn.clicked.connect(self._export_letters)
        row2.addWidget(export_btn)
        lay.addLayout(row2)

        old = self._stack.widget(1)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(1, home)
        self._stack.setCurrentIndex(1)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {LGOLD}; font-size: 10px; font-weight: 700; letter-spacing: 1px; margin-top: 6px;")
        return lbl

    def _style_list(self, lst: QListWidget) -> None:
        lst.setStyleSheet(
            f"QListWidget {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; font-size: 12px; }}"
            f"QListWidget::item {{ padding: 6px; }}"
            f"QListWidget::item:selected {{ background: rgba(212,175,55,0.15); color: {GOLD}; }}"
        )
        lst.setMaximumHeight(110)

    def _btn_style(self, primary: bool = False) -> str:
        if primary:
            return (
                "QPushButton { background: #d4b04c; color: #17120a; font-weight: 600; border: none; border-radius: 6px; padding: 8px; }"
                "QPushButton:hover { background: #e2c062; }"
            )
        return (
            f"QPushButton {{ background: transparent; color: {GOLD}; border: 1px solid {LGOLD}; "
            f"border-radius: 6px; padding: 8px; }}"
            f"QPushButton:hover {{ background: rgba(212,175,55,0.08); }}"
        )

    # ── Reading an inbox letter (+ ephemeral companion chat) ───────────────

    def _open_inbox_letter(self):
        row = self._inbox_list.currentRow()
        if row < 0 or row >= len(self._inbox):
            QMessageBox.information(self, "Legacy Vault", "Select a letter first.")
            return
        entry = self._inbox[row]
        if QMessageBox.question(
            self, "Legacy Vault", f"Open letter from {entry.get('from_display', '?')}?",
        ) != QMessageBox.StandardButton.Yes:
            return
        content = cc._legacy_get_content(entry["id"])
        if not content:
            QMessageBox.warning(self, "Legacy Vault", "Letter file not found.")
            return
        self._show_letter_viewer(entry, content, from_field="from_display", companion=True)

    def _read_own_letter(self):
        row = self._outbox_list.currentRow()
        if row < 0 or row >= len(self._outbox):
            QMessageBox.information(self, "Legacy Vault", "Select a letter first.")
            return
        entry = self._outbox[row]
        if QMessageBox.question(
            self, "Legacy Vault", f"Re-read your letter for {entry.get('for_display', '?')}?",
        ) != QMessageBox.StandardButton.Yes:
            return
        content = cc._legacy_get_content(entry["id"])
        if not content:
            QMessageBox.warning(self, "Legacy Vault", "Letter file not found.")
            return
        self._show_letter_viewer(entry, content, from_field="for_display", companion=False)

    def _show_letter_viewer(self, entry: dict, content: str, from_field: str, companion: bool) -> None:
        view = QWidget()
        lay = QVBoxLayout(view)
        lay.setSpacing(10)

        header = QLabel(f"{'Letter from' if companion else 'Your letter for'} {entry.get(from_field, '?')}  ·  {entry.get('subject', '')}")
        header.setStyleSheet(f"color: {GOLD}; font-size: 14px; font-weight: 700;")
        lay.addWidget(header)

        body = QTextBrowser()
        body.setPlainText(content)
        body.setStyleSheet(f"QTextBrowser {{ background: {BG2}; color: #F0E9D8; border: 1px solid {BORDER}; border-radius: 6px; padding: 10px; font-size: 13px; }}")
        lay.addWidget(body, 1)

        if companion and (self._cfg.get("api_key") or self._cfg.get("openai_key") or self._cfg.get("anthropic_key")):
            lay.addWidget(self._note_label(
                "The council is here with you if you need it. Ask anything -- they will not speak as the "
                "author, only as a companion helping you process what you've read."
            ))
            self._companion_history = [{
                "role": "system",
                "content": (
                    f"{self._profile['display']} has just read a personal legacy letter written for them "
                    f"by {entry.get('from_display', '?')}. The letter:\n\n{content}\n\n"
                    f"Your role: be a warm, honest companion helping them process what they've read. "
                    f"You are NOT {entry.get('from_display', '?')}. Do not speak as them, do not roleplay "
                    f"as them, do not claim to channel them. If asked, decline clearly but gently. "
                    f"Do not tell them what to think or feel. Ask. Listen. Reflect."
                ),
            }]
            self._companion_view = QTextBrowser()
            self._companion_view.setStyleSheet(f"QTextBrowser {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px; font-size: 12px; }}")
            self._companion_view.setMaximumHeight(160)
            lay.addWidget(self._companion_view)

            row = QHBoxLayout()
            self._companion_input = QLineEdit()
            self._companion_input.setPlaceholderText("Ask the companion...")
            self._companion_input.setStyleSheet(f"QLineEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px; }}")
            self._companion_input.returnPressed.connect(self._send_companion)
            row.addWidget(self._companion_input, 1)
            send_btn = QPushButton("Ask")
            send_btn.setStyleSheet(self._btn_style())
            send_btn.clicked.connect(self._send_companion)
            row.addWidget(send_btn)
            lay.addLayout(row)

        back_btn = QPushButton("← Back to Vault")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(self._btn_style())
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        lay.addWidget(back_btn)

        old = self._stack.widget(2)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(2, view)
        self._stack.setCurrentIndex(2)

    def _send_companion(self):
        if self._companion_streaming:
            return
        text = self._companion_input.text().strip()
        if not text:
            return
        self._companion_input.clear()
        self._companion_view.append(f"<b style='color:{LGOLD};'>You:</b> {text}")
        self._companion_history.append({"role": "user", "content": text})
        self._companion_streaming = True
        self._companion_reply = ""
        self._companion_view.append(f"<b style='color:{GOLD};'>Companion:</b> ")
        threading.Thread(target=self._run_companion, args=(list(self._companion_history),), daemon=True).start()

    def _run_companion(self, history: list[dict]) -> None:
        try:
            gen, _label = cc._cascade_gen(self._cfg, history, max_tokens=500)
            for chunk in gen:
                if chunk and chunk != cc.RATE_SENTINEL:
                    self._companion_signals.chunk.emit(chunk)
            self._companion_signals.done.emit()
        except Exception as e:
            self._companion_signals.error.emit(str(e))

    def _on_companion_chunk(self, chunk: str) -> None:
        self._companion_reply += chunk
        cursor = self._companion_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._companion_view.setTextCursor(cursor)
        self._companion_view.insertPlainText(chunk)

    def _on_companion_done(self) -> None:
        self._companion_history.append({"role": "assistant", "content": self._companion_reply})
        self._companion_streaming = False

    def _on_companion_error(self, message: str) -> None:
        self._companion_view.append(f"<span style='color:#ff6666;'>[Error: {message}]</span>")
        self._companion_streaming = False

    # ── Writing a new letter ────────────────────────────────────────────

    def _write_letter(self):
        dlg = _ComposeLegacyLetterDialog(self._profile, self._cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_id:
            QMessageBox.information(self, "Legacy Vault", f"Letter saved.\nID: {dlg.result_id}")
            self._enter_vault()   # refresh outbox list

    # ── Editing / deleting own letters ──────────────────────────────────

    def _edit_own_letter(self):
        row = self._outbox_list.currentRow()
        if row < 0 or row >= len(self._outbox):
            QMessageBox.information(self, "Legacy Vault", "Select a letter first.")
            return
        entry = self._outbox[row]
        if QMessageBox.question(
            self, "Legacy Vault", f"Rewrite letter for {entry.get('for_display', '?')}? Original will be replaced.",
        ) != QMessageBox.StandardButton.Yes:
            return
        if QMessageBox.warning(
            self, "Legacy Vault", "This cannot be undone. Are you certain?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        current = cc._legacy_get_content(entry["id"]) or ""
        text, ok = QInputDialog.getMultiLineText(self, "Legacy Vault — Edit Letter", "Revised letter:", current)
        if not ok or not text.strip():
            return
        if cc._legacy_rewrite(entry["id"], text.strip()):
            QMessageBox.information(self, "Legacy Vault", "Letter updated.")
            self._enter_vault()
        else:
            QMessageBox.warning(self, "Legacy Vault", "Update failed.")

    def _delete_own_letter(self):
        row = self._outbox_list.currentRow()
        if row < 0 or row >= len(self._outbox):
            QMessageBox.information(self, "Legacy Vault", "Select a letter first.")
            return
        entry = self._outbox[row]
        who = entry.get("for_display", "?")

        if QMessageBox.warning(
            self, "Legacy Vault", f"Permanently delete letter for {who}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        if QMessageBox.warning(
            self, "Legacy Vault", "This letter cannot be recovered. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        text, ok = QInputDialog.getText(self, "Legacy Vault", "Type DELETE to confirm:")
        if not ok or text.strip().upper() != "DELETE":
            QMessageBox.information(self, "Legacy Vault", "Deletion cancelled.")
            return
        if QMessageBox.warning(
            self, "Legacy Vault", "Final confirmation -- gone forever. Last chance.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        if cc._legacy_delete(entry["id"]):
            QMessageBox.information(self, "Legacy Vault", "Letter permanently deleted.")
            self._enter_vault()
        else:
            QMessageBox.warning(self, "Legacy Vault", "Deletion failed.")

    def _export_letters(self):
        if not self._outbox:
            QMessageBox.information(self, "Legacy Vault", "You haven't written any letters yet.")
            return
        try:
            exp_path, exp_count = cc._legacy_export_pack(self._profile["key"], self._profile["display"])
        except Exception as e:
            QMessageBox.warning(self, "Legacy Vault", f"Export failed: {e}")
            return
        if exp_count == 0:
            QMessageBox.information(self, "Legacy Vault", "Nothing to export.")
            return
        cc._legacy_open_folder(exp_path)
        QMessageBox.information(
            self, "Legacy Vault",
            f"Export saved — {exp_count} letter(s)\nFile: {exp_path.name}\nLocation: {exp_path.parent}\n\n"
            "Attach it to an email and send to Joshua. He runs the import and your letters are live.",
        )


class _ComposeLegacyLetterDialog(QDialog):
    """Write a new legacy letter -- recipient, subject, body, optional AI polish."""

    def __init__(self, profile: dict, cfg: dict, parent=None):
        super().__init__(parent)
        self._profile = profile
        self._cfg = cfg
        self.result_id: str = ""
        self._polished_text: str = ""

        self.setWindowTitle("Write a Legacy Letter")
        self.setMinimumSize(520, 480)
        self.setStyleSheet(f"QDialog {{ background: {BG}; }} QLabel {{ color: {SILVER}; }}")

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        lay.addWidget(self._label("Who is this letter for?"))
        self._for_field = QLineEdit()
        self._style_field(self._for_field)
        lay.addWidget(self._for_field)

        lay.addWidget(self._label("Subject or occasion (optional)"))
        self._subject_field = QLineEdit()
        self._style_field(self._subject_field)
        lay.addWidget(self._subject_field)

        lay.addWidget(self._label("Your letter"))
        self._body_field = QPlainTextEdit()
        self._body_field.setStyleSheet(
            f"QPlainTextEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 8px; font-size: 13px; }}"
        )
        lay.addWidget(self._body_field, 1)

        self._polish_check = QCheckBox("Ask AI to help polish this (keeps your voice)")
        self._polish_check.setStyleSheet(f"color: {SILV2};")
        lay.addWidget(self._polish_check)

        lay.addWidget(self._label("Custom letter code (optional -- press Enter to use system credentials)"))
        self._code_field = QLineEdit()
        self._style_field(self._code_field)
        lay.addWidget(self._code_field)

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

        self._save_btn = QPushButton("Save Letter")
        self._save_btn.setStyleSheet(
            "QPushButton { background: #d4b04c; color: #17120a; font-weight: 600; border: none; border-radius: 6px; padding: 8px; }"
            "QPushButton:disabled { background: #1a1a2e; color: #666; }"
        )
        self._save_btn.clicked.connect(self._save)
        row.addWidget(self._save_btn)
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

    def _save(self) -> None:
        for_display = self._for_field.text().strip()
        body = self._body_field.toPlainText().strip()
        if not for_display or not body:
            QMessageBox.information(self, "Legacy Vault", "Recipient and letter body are required.")
            return

        final_body = body
        if self._polish_check.isChecked():
            self._save_btn.setEnabled(False)
            self._status.setText("Polishing with AI -- keeping your voice...")
            polished = self._run_polish_blocking(for_display, body)
            self._save_btn.setEnabled(True)
            self._status.setText("")
            if polished and polished.strip():
                choice = QMessageBox.question(
                    self, "Legacy Vault", "AI polish complete. Use the polished version?\n\n"
                    f"{polished[:400]}{'…' if len(polished) > 400 else ''}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if choice == QMessageBox.StandardButton.Yes:
                    final_body = polished.strip()

        code = self._code_field.text().strip()
        if code and _pin_looks_valid(code):
            access_type, access_hash = "letter_pin", _make_pin_hash(code)
        else:
            access_type, access_hash = "babel_pin", ""

        lid = cc._legacy_save(
            from_key=self._profile["key"], from_display=self._profile["display"],
            for_key=cc._legacy_name_to_key(for_display), for_display=for_display,
            subject=self._subject_field.text().strip(), content=final_body,
            access_type=access_type, access_hash=access_hash,
        )
        self.result_id = lid
        self.accept()

    def _run_polish_blocking(self, for_display: str, body: str) -> str:
        messages = [
            {"role": "system", "content": (
                f"You are helping {self._profile['display']} polish a personal letter written for "
                f"{for_display}. Make the words flow better while keeping the author's exact voice, "
                f"style, and meaning. Do not add sentiment that isn't there. Do not change what they "
                f"are saying -- only how smoothly it reads. Return ONLY the polished letter."
            )},
            {"role": "user", "content": body},
        ]
        try:
            gen, _label = cc._cascade_gen(self._cfg, messages, max_tokens=1000)
            return "".join(c for c in gen if c and c != cc.RATE_SENTINEL)
        except Exception:
            return ""


def _pin_looks_valid(pin: str) -> bool:
    try:
        from cursiv_v215.family.family_profiles import is_valid_pin
        return is_valid_pin(pin)
    except Exception:
        return False


def _make_pin_hash(pin: str) -> str:
    try:
        from cursiv_v215.family.legacy_store import make_letter_pin_hash
        return make_letter_pin_hash(pin)
    except Exception:
        return ""

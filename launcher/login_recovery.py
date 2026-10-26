"""Security-question setup and password recovery. Reuses existing guardian APIs and preserves their account checks.

Existing class identities are re-exported by login_dialog for callers.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)
from theme import BG, BG2, GOLD, LGOLD, SILV2, RED, GREEN  # one palette for every window (theme.py)

from login_style import _BaseDialog


def _sq():
    from cursiv_engine.guardian.security_questions import (
        QUESTIONS, setup_security_questions,
        is_setup_complete as sq_ready,
        get_selected_questions, verify_answers,
        clear_security_questions,
    )
    return (QUESTIONS, setup_security_questions, sq_ready,
            get_selected_questions, verify_answers, clear_security_questions)


class SecurityQSetupDialog(_BaseDialog):
    """
    Shown after account creation. User picks 3 questions from a list of 20
    and provides answers that are bcrypt-hashed for later recovery.
    """

    def __init__(self, parent=None, required: bool = False, username: str | None = None):
        super().__init__("Cursiv — Security Questions", parent)
        self.setFixedWidth(500)
        self._required = required     # first account: no skipping (it's how a forgotten password is reset)
        self._username = username     # whose questions these are (each account has its own)
        self._build()

    def _build(self):
        try:
            QUESTIONS = _sq()[0]
        except Exception:
            QUESTIONS = []

        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(32, 28, 32, 24)
        vlay.setSpacing(10)

        vlay.addWidget(self._header("✦  SECURITY QUESTIONS"))
        vlay.addWidget(self._sub(
            "Choose 3 questions for password recovery.\n"
            "Answers are hashed — we cannot see or retrieve them."
        ))
        vlay.addSpacing(8)

        self._combos: list[QComboBox] = []
        self._ans_fields: list[QLineEdit] = []
        if self._required:
            vlay.addWidget(self._sub(
                "Needed: these are the only way to reset a forgotten password."))

        for i in range(3):
            lbl = QLabel(f"Question {i + 1}")
            lbl.setStyleSheet(f"color: {GOLD}; font-weight: 700; font-size: 12px;")
            vlay.addWidget(lbl)

            cb = QComboBox()
            cb.setMaxVisibleItems(10)
            for q in QUESTIONS:
                cb.addItem(q)
            if QUESTIONS:
                cb.setCurrentIndex(min(i * 6, len(QUESTIONS) - 1))
            self._combos.append(cb)
            vlay.addWidget(cb)

            af = self._field("Your answer")
            self._ans_fields.append(af)
            vlay.addWidget(af)

            if i < 2:
                vlay.addSpacing(6)

        self._err = self._err_label()
        vlay.addSpacing(4)
        vlay.addWidget(self._err)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        skip = QPushButton("Skip for now")
        skip.setProperty("class", "secondary")
        skip.setStyleSheet(f"background: {BG2}; color: {SILV2}; border: 1px solid {LGOLD};")
        skip.clicked.connect(self.reject)

        save = QPushButton("Save Security Questions  ✓")
        save.clicked.connect(self._submit)

        if not self._required:
            btn_row.addWidget(skip)
        btn_row.addWidget(save)
        vlay.addLayout(btn_row)

        if self._ans_fields:
            self._ans_fields[0].setFocus()

    def _submit(self):
        indices = [cb.currentIndex() for cb in self._combos]
        if len(set(indices)) < 3:
            self._err.setText("Please choose 3 different questions.")
            return

        answers = [f.text().strip() for f in self._ans_fields]
        if any(not a for a in answers):
            self._err.setText("Please answer all 3 questions.")
            return

        try:
            _, setup_sq, *_ = _sq()
            setup_sq(indices, answers, self._username)
        except Exception as exc:
            self._err.setText(f"Setup error: {exc}")
            return

        self._ok = True
        self.accept()


class ResetPasswordDialog(_BaseDialog):
    """
    Page 0 — enter username (verifies it exists + SQ configured)
    Page 1 — answer 3 security questions (2/3 threshold)
    Page 2 — set new password
    """

    def __init__(self, parent=None):
        super().__init__("Cursiv — Reset Password", parent)
        self.setFixedWidth(460)
        self._nuclear_requested = False
        self._verified_username = ""
        self._build()

    def nuclear_reset_requested(self) -> bool:
        return self._nuclear_requested

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page0())
        self._stack.addWidget(self._page1())
        self._stack.addWidget(self._page2())
        outer.addWidget(self._stack)

    def _vbox(self, margins=(32, 28, 32, 24), spacing=12) -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(*margins)
        v.setSpacing(spacing)
        return w, v

    # ── Page 0: username ───────────────────────────────────────────────────

    def _page0(self) -> QWidget:
        w, v = self._vbox()

        v.addWidget(self._header("✦  RESET PASSWORD"))
        v.addWidget(self._sub(
            "Enter your username to load your security questions."
        ))
        v.addSpacing(6)

        self._p0_user = self._field("Username")
        self._p0_err  = self._err_label()

        v.addWidget(self._p0_user)
        v.addWidget(self._p0_err)

        btn = QPushButton("Continue  →")
        btn.clicked.connect(self._p0_submit)
        self._p0_user.returnPressed.connect(self._p0_submit)
        v.addWidget(btn)

        # Nuclear fallback — visible only if SQ not set up
        self._nuclear_btn = QPushButton("Reset Entire Account  ⚠")
        self._nuclear_btn.setStyleSheet(
            f"background: {BG2}; color: {RED}; border: 1px solid {RED};"
        )
        self._nuclear_btn.setToolTip(
            "Deletes all credentials. Use if no security questions were set up."
        )
        self._nuclear_btn.setVisible(False)
        self._nuclear_btn.clicked.connect(self._request_nuclear)
        v.addWidget(self._nuclear_btn)

        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(f"background: {BG2}; color: {SILV2}; border: 1px solid {LGOLD};")
        cancel.clicked.connect(self.reject)
        v.addWidget(cancel)

        self._p0_user.setFocus()
        return w

    def _p0_submit(self):
        username = self._p0_user.text().strip()
        if not username:
            self._p0_err.setText("Please enter your username.")
            return

        try:
            from cursiv_engine.guardian.access_gate import username_exists
            if not username_exists(username):
                self._p0_err.setText("Username not found.")
                return
        except Exception as exc:
            self._p0_err.setText(f"Error: {exc}")
            return

        try:
            _, _, sq_ready, get_qs, *_ = _sq()
            if not sq_ready(username):
                self._p0_err.setText(
                    "This account has no security questions, so its password can't be reset here.\n"
                    "Ask someone who can sign in to remove it and add it again (Settings → Your data "
                    "& account). As a last resort, 'Reset Entire Account' removes every login."
                )
                self._nuclear_btn.setVisible(True)
                return
            questions = get_qs(username)
        except Exception as exc:
            self._p0_err.setText(f"Security question error: {exc}")
            return

        for lbl, q in zip(self._q_labels, questions):
            lbl.setText(q)

        self._verified_username = username
        self._stack.setCurrentIndex(1)
        self._sq_fields[0].setFocus()

    def _request_nuclear(self):
        self._nuclear_requested = True
        self.reject()

    # ── Page 1: security questions ─────────────────────────────────────────

    def _page1(self) -> QWidget:
        w, v = self._vbox()

        v.addWidget(self._header("✦  SECURITY CHECK"))
        v.addWidget(self._sub("Answer at least 2 of 3 questions to continue."))
        v.addSpacing(4)

        self._q_labels:  list[QLabel]   = []
        self._sq_fields: list[QLineEdit] = []

        for i in range(3):
            lbl = QLabel(f"Question {i + 1}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {GOLD}; font-size: 12px; font-weight: 600;")
            self._q_labels.append(lbl)
            v.addWidget(lbl)

            af = self._field(f"Answer {i + 1}")
            self._sq_fields.append(af)
            v.addWidget(af)

        self._p1_err = self._err_label()
        v.addSpacing(4)
        v.addWidget(self._p1_err)

        btn = QPushButton("Verify  →")
        btn.clicked.connect(self._p1_submit)
        v.addWidget(btn)

        return w

    def _p1_submit(self):
        answers = [f.text().strip() for f in self._sq_fields]
        try:
            _, _, _, _, verify, *_ = _sq()
            if not verify(answers, self._verified_username):
                self._p1_err.setText(
                    "Security answers do not match (need 2 of 3).\n"
                    "Check spelling — minor differences matter."
                )
                return
        except Exception as exc:
            # TooManyAttempts (U103) explains the wait in its message.
            self._p1_err.setText(str(exc) if type(exc).__name__ == "TooManyAttempts" else f"Verification error: {exc}")
            return

        self._stack.setCurrentIndex(2)
        self._new_pw.setFocus()

    # ── Page 2: new password ───────────────────────────────────────────────

    def _page2(self) -> QWidget:
        w, v = self._vbox()

        v.addWidget(self._header("✦  NEW PASSWORD"))
        v.addWidget(self._sub(
            "Security verified. Enter your new password."
        ))
        v.addSpacing(6)

        self._new_pw  = self._field("New password", password=True)
        self._new_pw2 = self._field("Confirm new password", password=True)
        self._p2_err  = self._err_label()

        v.addWidget(self._new_pw)
        v.addWidget(self._new_pw2)
        v.addWidget(self._p2_err)

        btn = QPushButton("Set New Password  ✓")
        btn.clicked.connect(self._p2_submit)
        self._new_pw2.returnPressed.connect(self._p2_submit)
        v.addWidget(btn)

        return w

    def _p2_submit(self):
        pw  = self._new_pw.text()
        pw2 = self._new_pw2.text()

        if len(pw) < 4:
            self._p2_err.setText("Password must be at least 4 characters.")
            return
        if pw != pw2:
            self._p2_err.setText("Passwords do not match.")
            self._new_pw2.clear()
            self._new_pw2.setFocus()
            return

        try:
            from cursiv_engine.guardian.access_gate import reset_password
            reset_password(pw, username=self._verified_username)     # only the account that answered
        except Exception as exc:
            self._p2_err.setText(f"Error saving password: {exc}")
            return

        self._ok = True
        self.accept()

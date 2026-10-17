"""
Cursiv Login / Setup Dialogs — PyQt6.
Integrates with cursiv_v215.guardian.access_gate (bcrypt credential store)
and cursiv_v215.guardian.security_questions (password recovery).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QStackedWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

BG    = "#0b0b12"
BG2   = "#13131e"
GOLD  = "#FFD700"
LGOLD = "#9B7B20"
SILV  = "#C8C8D4"
SILV2 = "#666680"
RED   = "#FF4455"
GREEN = "#44CC88"
BLUE  = "#2255DD"

_QSS = f"""
QDialog, QWidget {{
    background: {BG}; color: {SILV};
    font-family: "Segoe UI", Arial, sans-serif; font-size: 13px;
}}
QLabel {{ background: transparent; }}
QLineEdit {{
    background: {BG2}; color: {SILV};
    border: 1px solid {LGOLD}; border-radius: 5px;
    padding: 6px 10px; font-size: 13px;
}}
QLineEdit:focus {{ border-color: {GOLD}; }}
QPushButton {{
    background: {BLUE}; color: #fff;
    border: none; border-radius: 6px;
    padding: 8px 20px; font-size: 13px; font-weight: 600;
}}
QPushButton:hover   {{ background: #3366EE; }}
QPushButton:pressed {{ background: #1144CC; }}
QPushButton.secondary {{
    background: {BG2}; color: {SILV2};
    border: 1px solid {LGOLD};
}}
QPushButton.secondary:hover {{ background: #1e1e2e; color: {SILV}; }}
QComboBox {{
    background: {BG2}; color: {SILV};
    border: 1px solid {LGOLD}; border-radius: 5px;
    padding: 6px 10px; font-size: 12px;
    min-height: 28px;
}}
QComboBox:focus {{ border-color: {GOLD}; }}
QComboBox::drop-down {{
    border: none; width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {BG2}; color: {SILV};
    border: 1px solid {LGOLD};
    selection-background-color: {BLUE};
    selection-color: #fff;
    padding: 2px;
}}
"""

# ── Lazy import helpers ────────────────────────────────────────────────────────

def _sq():
    from cursiv_v215.guardian.security_questions import (
        QUESTIONS, setup_security_questions,
        is_setup_complete as sq_ready,
        get_selected_questions, verify_answers,
        clear_security_questions,
    )
    return (QUESTIONS, setup_security_questions, sq_ready,
            get_selected_questions, verify_answers, clear_security_questions)


# ── Base dialog ────────────────────────────────────────────────────────────────

class _BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setStyleSheet(_QSS)
        self.setMinimumWidth(380)
        self._ok = False

    def _header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {GOLD}; font-size: 18px; font-weight: 700; letter-spacing: 2px;"
        )
        return lbl

    def _sub(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        return lbl

    def _field(self, placeholder: str, password: bool = False) -> QLineEdit:
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        if password:
            f.setEchoMode(QLineEdit.EchoMode.Password)
        return f

    def _err_label(self) -> QLabel:
        lbl = QLabel("")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {RED}; font-size: 11px;")
        return lbl

    def _ok_label(self) -> QLabel:
        lbl = QLabel("")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
        return lbl

    def accepted_ok(self) -> bool:
        return self._ok


# ── Security questions setup dialog ───────────────────────────────────────────

class SecurityQSetupDialog(_BaseDialog):
    """
    Shown after account creation. User picks 3 questions from a list of 20
    and provides answers that are bcrypt-hashed for later recovery.
    """

    def __init__(self, parent=None, required: bool = False):
        super().__init__("Cursiv — Security Questions", parent)
        self.setFixedWidth(500)
        self._required = required     # first account: no skipping (it's how a forgotten password is reset)
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
            setup_sq(indices, answers)
        except Exception as exc:
            self._err.setText(f"Setup error: {exc}")
            return

        self._ok = True
        self.accept()


# ── Reset password dialog (3-page stacked flow) ────────────────────────────────

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
            from cursiv_v215.guardian.access_gate import username_exists
            if not username_exists(username):
                self._p0_err.setText("Username not found.")
                return
        except Exception as exc:
            self._p0_err.setText(f"Error: {exc}")
            return

        try:
            _, _, sq_ready, get_qs, *_ = _sq()
            if not sq_ready():
                self._p0_err.setText(
                    "No security questions are configured for this account.\n"
                    "Use 'Reset Entire Account' below as a last resort."
                )
                self._nuclear_btn.setVisible(True)
                return
            questions = get_qs()
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
            if not verify(answers):
                self._p1_err.setText(
                    "Security answers do not match (need 2 of 3).\n"
                    "Check spelling — minor differences matter."
                )
                return
        except Exception as exc:
            self._p1_err.setText(f"Verification error: {exc}")
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
            from cursiv_v215.guardian.access_gate import reset_password
            reset_password(pw)
        except Exception as exc:
            self._p2_err.setText(f"Error saving password: {exc}")
            return

        self._ok = True
        self.accept()


# ── Setup dialog (account creation) ───────────────────────────────────────────

def _log_setup_error(where: str, exc: BaseException) -> None:
    """Save the full error so a problem report can include it."""
    try:
        import datetime
        import traceback
        from pathlib import Path
        log = Path.home() / ".cursiv" / "logs" / "login.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n{datetime.datetime.now().isoformat()}  {where}\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
    except Exception:
        pass


class SetupDialog(_BaseDialog):
    """
    Create username + password. First-run mode (is_additional=False, the
    default) creates the primary account and offers security-question
    setup for password recovery. Additional-account mode (is_additional=
    True, opened from the login screen's "Create Account" option) adds
    another login that shares this same install's data -- multiple people
    can each have their own credentials without sharing one password.
    Security questions are primary-account-only for now, so that step is
    skipped for additional accounts.
    """

    def __init__(self, parent=None, is_additional: bool = False):
        title = "Cursiv — Add Account" if is_additional else "Cursiv — Create Account"
        super().__init__(title, parent)
        self.setMinimumWidth(380)
        self._is_additional = is_additional
        self._username_result = ""
        self._build()

    def _build(self):
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(32, 28, 32, 24)
        vlay.setSpacing(14)

        vlay.addWidget(self._header("✦  CURSIV"))
        vlay.addWidget(self._sub(
            "Add another login for this device.\nShares the same Cursiv data as every other account here."
            if self._is_additional else
            "Create your access credentials.\n"
            "Stored securely across multiple locations."
        ))
        vlay.addSpacing(6)

        self._user = self._field("Username")
        self._pw   = self._field("Password", password=True)
        self._pw2  = self._field("Confirm password", password=True)
        self._err  = self._err_label()

        for w in (self._user, self._pw, self._pw2, self._err):
            vlay.addWidget(w)

        # Shown only when creating the account fails: sends the error to Joshua.
        self._report_btn = QPushButton("Send problem report")
        self._report_btn.setVisible(False)
        self._report_btn.clicked.connect(self._send_report)
        vlay.addWidget(self._report_btn)

        btn = QPushButton("Add Account" if self._is_additional else "Create Account")
        btn.clicked.connect(self._submit)
        self._pw2.returnPressed.connect(self._submit)
        vlay.addWidget(btn)

        self._user.setFocus()

    def _send_report(self):
        try:
            from problem_report import open_report
            open_report(self, f"Create Account failed: {self._err.text()}")
        except Exception:
            pass

    def _submit(self):
        username = self._user.text().strip()
        password = self._pw.text()
        confirm  = self._pw2.text()

        if not username:
            self._err.setText("Username cannot be empty.")
            return
        if len(password) < 4:
            self._err.setText("Password must be at least 4 characters.")
            return
        if password != confirm:
            self._err.setText("Passwords do not match.")
            self._pw2.clear()
            self._pw2.setFocus()
            return

        try:
            from cursiv_v215.guardian.access_gate import setup_credentials, add_account, username_exists
            if self._is_additional:
                if username_exists(username):
                    self._err.setText("That username is already taken.")
                    return
                if not add_account(username, password):
                    self._err.setText("That username is already taken.")
                    return
            else:
                setup_credentials(username, password)
        except Exception as exc:
            _log_setup_error("Create Account", exc)
            self._err.setText(f"Setup error: {exc}")
            self._report_btn.setVisible(True)
            return

        self._username_result = username

        if not self._is_additional:
            # Security questions are required for the first account: without
            # them the only way back in was "Reset Entire Account", which let
            # anyone at the keyboard in. Additional accounts don't have their
            # own question-based recovery yet.
            while True:
                sq_dlg = SecurityQSetupDialog(self, required=True)
                if sq_dlg.exec() and sq_dlg.accepted_ok():
                    break

        self._ok = True
        self.accept()

    def get_username(self) -> str:
        return self._username_result


def _clear_saved_keys() -> None:
    """Remove the AI keys from Cursiv's config (part of a full account reset)."""
    import json
    try:
        from cursiv_v215.chat.keys import KEYS_FILE as path
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in ("api_key", "openai_key", "anthropic_key", "gemini_key", "groq_key",
                      "cf_account_id", "cf_api_token"):
            data.pop(field, None)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── Login dialog ───────────────────────────────────────────────────────────────


class LoginDialog(_BaseDialog):
    """Standard login — verifies existing credentials."""

    def __init__(self, parent=None):
        super().__init__("Cursiv — Login", parent)
        self.setMinimumWidth(380)
        self._username_result = ""
        self._build()

    def _build(self):
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(32, 28, 32, 24)
        vlay.setSpacing(14)

        vlay.addWidget(self._header("✦  CURSIV"))
        vlay.addWidget(self._sub("Welcome back. Please authenticate."))
        vlay.addSpacing(6)

        self._user   = self._field("Username")
        self._pw     = self._field("Password", password=True)
        self._status = self._err_label()

        for w in (self._user, self._pw, self._status):
            vlay.addWidget(w)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self._submit)
        self._pw.returnPressed.connect(self._submit)
        vlay.addWidget(login_btn)

        # Reset password + create-account links, side by side
        link_row = QHBoxLayout()
        link_row.setSpacing(4)

        link_style = (
            f"background: transparent; color: {SILV2}; font-size: 12px; "
            f"font-weight: 400; border: none; padding: 2px;"
        )

        reset_btn = QPushButton("Forgot Password?")
        reset_btn.setStyleSheet(link_style)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.clicked.connect(self._reset)
        link_row.addStretch(1)
        link_row.addWidget(reset_btn)

        sep = QLabel("·")
        sep.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        link_row.addWidget(sep)

        create_btn = QPushButton("Create Account")
        create_btn.setStyleSheet(link_style)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setToolTip("Add another login — type an existing username and password first")
        create_btn.clicked.connect(self._create_account)
        link_row.addWidget(create_btn)
        link_row.addStretch(1)

        vlay.addLayout(link_row)

        self._user.setFocus()

    def _create_account(self):
        # A new login sees the same keys, memories and conversations, so only
        # someone who can already log in may add one.
        username, password = self._user.text().strip(), self._pw.text()
        try:
            from cursiv_v215.guardian.access_gate import verify_credentials
            approved = bool(username and password and verify_credentials(username, password))
        except Exception:
            approved = False
        if not approved:
            self._status.setStyleSheet(f"color: {RED}; font-size: 11px;")
            self._status.setText("To add an account, first type an existing username and "
                                 "password above, then click Create Account.")
            return
        dlg = SetupDialog(self, is_additional=True)
        if dlg.exec() and dlg.accepted_ok():
            self._status.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
            self._status.setText(f"Account created for {dlg.get_username()}. You can log in now.")
            self._user.setText(dlg.get_username())
            self._pw.clear()
            self._pw.setFocus()

    def _reset(self):
        dlg = ResetPasswordDialog(self)
        dlg.exec()

        if dlg.accepted_ok():
            # SQ reset succeeded — user can now log in with their new password
            self._status.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
            self._status.setText("Password reset. Log in with your new password.")
            self._pw.clear()
            self._pw.setFocus()
            return

        if dlg.nuclear_reset_requested():
            # User has no SQ and wants the nuclear option
            reply = QMessageBox.question(
                self, "Reset Account",
                "This deletes every login on this computer and the AI keys "
                "saved in Cursiv (you'll need to add them again).\n\n"
                "Memories and conversations stay. Cursiv's login is a lock on the "
                "front door, not encryption — anyone with access to this "
                "computer's files can read them.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                from cursiv_v215.guardian.access_gate import reset_credentials
                from cursiv_v215.guardian.security_questions import clear_security_questions
                reset_credentials()
                clear_security_questions()
                _clear_saved_keys()
            except Exception as exc:
                self._status.setText(f"Reset error: {exc}")
                return
            # Immediately re-run setup
            setup = SetupDialog(self)
            if setup.exec() and setup.accepted_ok():
                self._username_result = setup.get_username()
                self._ok = True
                self.accept()

    def _submit(self):
        username = self._user.text().strip()
        password = self._pw.text()

        if not username or not password:
            self._status.setText("Please enter username and password.")
            return

        self._status.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        self._status.setText("Verifying…")

        try:
            from cursiv_v215.guardian.access_gate import verify_credentials
            verified = verify_credentials(username, password)
        except Exception as exc:
            self._status.setStyleSheet(f"color: {RED}; font-size: 11px;")
            self._status.setText(f"Auth error: {exc}")
            return

        if verified:
            self._username_result = username
            self._ok = True
            self.accept()
        else:
            self._status.setStyleSheet(f"color: {RED}; font-size: 11px;")
            self._status.setText("Invalid credentials. Please try again.")
            self._pw.clear()
            self._pw.setFocus()

    def get_username(self) -> str:
        return self._username_result


# ── Family welcome dialog ──────────────────────────────────────────────────────

class FamilyWelcomeDialog(_BaseDialog):
    """
    Shown to family members after login/setup when their username matches a
    known family member's first name. Points them at the babel activation --
    the letter itself is sealed and only opens with their name + birth date,
    so it is never shown here.
    """

    def __init__(self, first_name: str, parent=None):
        super().__init__(f"Cursiv — Welcome, {first_name}", parent)
        self.setMinimumWidth(560)
        self._build(first_name)

    def _build(self, first_name: str):
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(28, 22, 28, 20)
        vlay.setSpacing(12)

        vlay.addWidget(self._header(f"✦  WELCOME, {first_name.upper()}"))
        vlay.addWidget(self._sub("A message was left for you inside this system."))

        # ── Activation instructions ───────────────────────────────────────
        instr_text = (
            "To open it, type this in the Cursiv chat box:\n\n"
            "  babel I am [your full name] born [your birth date]\n\n"
            "The system will recognize you, let you choose a personal code, and open your letter.\n"
            "After that, add your code at the end after a comma."
        )
        instr_box = QLabel(instr_text)
        instr_box.setWordWrap(True)
        instr_box.setStyleSheet(
            f"background: rgba(201,162,39,0.07);"
            f"color: {GOLD};"
            f"border-left: 3px solid {GOLD};"
            f"font-size: 12px;"
            f"padding: 12px 14px;"
        )
        vlay.addWidget(instr_box)

        btn = QPushButton("Begin  ✦")
        btn.clicked.connect(self.accept)
        vlay.addWidget(btn)

        self._ok = True

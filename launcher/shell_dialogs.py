"""Desktop auxiliary dialogs and window frame.


CommandAccessDialog and FleetDialog retain their existing authentication and
network-gate paths. TitleBar and _ResizeRoot own only Qt window controls.
The launcher re-exports these class identities for existing callers.
"""
from __future__ import annotations
import json
import threading
import urllib.request
import theme
from datetime import datetime, timezone
from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2, RED
from relay_settings import RELAY_URL as _RELAY_URL, FLEET_TOKEN as _FLEET_TOKEN

def _is_owner_machine() -> bool:
    """True when the local access_gate is configured — identifies Joshua's machines."""
    try:
        from cursiv_v215.guardian.access_gate import is_setup_complete
        return is_setup_complete()
    except ImportError:
        return False


class _UnlockDialog(QDialog):
    """Minimal inline password prompt — verifies via local access_gate bcrypt."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Unlock Required")
        self.setFixedWidth(360)
        self.setStyleSheet(f"background: {BG}; color: {SILVER};")
        self._verified = False

        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(24, 24, 24, 24)
        vlay.setSpacing(12)

        lbl = QLabel("Enter your unlock code to manage command access.")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {SILVER}; font-size: 12px;")
        vlay.addWidget(lbl)

        from PyQt6.QtWidgets import QLineEdit
        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw.setPlaceholderText("Password")
        self._pw.setStyleSheet(
            f"background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};"
            " border-radius: 4px; padding: 6px 10px; font-size: 13px;"
        )
        self._pw.returnPressed.connect(self._verify)
        vlay.addWidget(self._pw)

        self._err = QLabel("")
        self._err.setStyleSheet("color: #FF4455; font-size: 11px;")
        self._err.setVisible(False)
        vlay.addWidget(self._err)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("Unlock")
        ok_btn.setFixedHeight(34)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(
            "background: #d4b04c; color: #17120a; border-radius: 4px;"
            " font-weight: 600; font-size: 13px; padding: 4px 20px;"
        )
        ok_btn.clicked.connect(self._verify)
        btn_row.addWidget(ok_btn)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"background: transparent; color: {SILV2}; border: none; font-size: 12px;"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        vlay.addLayout(btn_row)

    def _verify(self):
        pw = self._pw.text()
        try:
            from cursiv_v215.guardian.access_gate import verify_credentials
            import os as _os
            ok = verify_credentials(_os.environ.get("USERNAME", "Joshua"), pw)
        except Exception:
            ok = False
        if ok:
            self._verified = True
            self.accept()
        else:
            self._err.setText("Incorrect password.")
            self._err.setVisible(True)
            self._pw.clear()
            self._pw.setFocus()

    def verified(self) -> bool:
        return self._verified


class CommandAccessDialog(QDialog):
    """Manage who has fleet command access — owner only, gated behind local unlock."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Command Access")
        self.setFixedWidth(500)
        self.setStyleSheet(f"background: {BG}; color: {SILVER};")

        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(20, 20, 20, 20)
        vlay.setSpacing(12)

        header = QLabel("⚙  Command Access")
        header.setStyleSheet(f"color: {GOLD}; font-size: 14px; font-weight: 700;")
        vlay.addWidget(header)

        sub = QLabel(
            "Command users can push heartbeats and view the fleet dashboard.\n"
            "Only you can add or revoke access."
        )
        sub.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        sub.setWordWrap(True)
        vlay.addWidget(sub)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(200)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px; }}"
        )
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f"background: {BG2};")
        self._list_lay = QVBoxLayout(self._list_widget)
        self._list_lay.setContentsMargins(8, 8, 8, 8)
        self._list_lay.setSpacing(6)
        self._scroll.setWidget(self._list_widget)
        vlay.addWidget(self._scroll)

        # New-token row
        from PyQt6.QtWidgets import QLineEdit
        add_box = QWidget()
        add_box.setStyleSheet(
            f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px;"
        )
        add_lay = QHBoxLayout(add_box)
        add_lay.setContentsMargins(10, 8, 10, 8)
        add_lay.setSpacing(8)
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText('Label, e.g. "Work Laptop"')
        self._label_edit.setStyleSheet(
            f"background: {BG}; color: {SILVER}; border: 1px solid {BORDER};"
            " border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._label_edit.returnPressed.connect(self._add_token)
        add_lay.addWidget(self._label_edit, 2)
        add_btn = QPushButton("+ Add User")
        add_btn.setFixedHeight(28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "background: #d4b04c; color: #17120a; border-radius: 4px;"
            " font-size: 11px; font-weight: 600; padding: 2px 14px;"
        )
        add_btn.clicked.connect(self._add_token)
        add_lay.addWidget(add_btn)
        vlay.addWidget(add_box)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        self._status_lbl.setWordWrap(True)
        vlay.addWidget(self._status_lbl)

        close_btn = QPushButton("Done")
        close_btn.setFixedHeight(28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"background: {BG2}; color: {SILV2}; border: 1px solid {BORDER};"
            " border-radius: 4px; font-size: 11px; padding: 2px 16px;"
        )
        close_btn.clicked.connect(self.accept)
        vlay.addWidget(close_btn)

        self._fetch_tokens()

    def _fetch_tokens(self):
        self._status_lbl.setText("Loading…")
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        if not _RELAY_URL or not _FLEET_TOKEN:
            QTimer.singleShot(0, lambda: self._apply_tokens([], "Relay not configured"))
            return
        try:
            req = urllib.request.Request(
                f"{_RELAY_URL}/remote/fleet/tokens",
                headers={"X-Fleet-Token": _FLEET_TOKEN},
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
            QTimer.singleShot(0, lambda d=data.get("tokens", []): self._apply_tokens(d, ""))
        except Exception as exc:
            QTimer.singleShot(0, lambda e=str(exc): self._apply_tokens([], e))

    def _apply_tokens(self, tokens: list, error: str):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if error:
            lbl = QLabel(f"⚠  {error}")
            lbl.setStyleSheet(f"color: #e8a020; font-size: 11px; padding: 4px;")
            self._list_lay.addWidget(lbl)
            self._status_lbl.setText("")
            return

        if not tokens:
            lbl = QLabel("No command users added yet — only you (owner) have access.")
            lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px; padding: 4px;")
            self._list_lay.addWidget(lbl)
        else:
            for tok in tokens:
                self._list_lay.addWidget(self._make_token_row(tok))

        self._list_lay.addStretch()
        self._status_lbl.setText(
            f"{len(tokens)} command user{'s' if len(tokens) != 1 else ''} with access"
        )

    def _make_token_row(self, tok: dict) -> QWidget:
        row_w = QWidget()
        row_w.setStyleSheet(
            f"background: {BG}; border: 1px solid {BORDER}; border-radius: 4px;"
        )
        row = QHBoxLayout(row_w)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(10)

        lbl = QLabel(f"<b>{tok['label']}</b>")
        lbl.setStyleSheet(f"color: {SILVER}; font-size: 12px; background: transparent; border: none;")
        row.addWidget(lbl, 2)

        by_lbl = QLabel(f"added {tok['added_at'][:10]}")
        by_lbl.setStyleSheet(f"color: {SILV2}; font-size: 10px; background: transparent; border: none;")
        row.addWidget(by_lbl, 1)

        revoke_btn = QPushButton("Revoke")
        revoke_btn.setFixedHeight(22)
        revoke_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        revoke_btn.setStyleSheet(
            "background: #3a1010; color: #FF4455; border: 1px solid #6a2020;"
            " border-radius: 3px; font-size: 10px; font-weight: 600; padding: 1px 8px;"
        )
        tid = tok["id"]
        revoke_btn.clicked.connect(lambda _=False, i=tid, b=revoke_btn: self._revoke(i, b))
        row.addWidget(revoke_btn)

        return row_w

    def _revoke(self, token_id: str, btn: QPushButton):
        btn.setEnabled(False)
        btn.setText("Revoking…")
        threading.Thread(target=self._do_revoke, args=(token_id,), daemon=True).start()

    def _do_revoke(self, token_id: str):
        try:
            req = urllib.request.Request(
                f"{_RELAY_URL}/remote/fleet/tokens/{token_id}",
                method="DELETE",
                headers={"X-Fleet-Token": _FLEET_TOKEN},
            )
            urllib.request.urlopen(req, timeout=8)
            QTimer.singleShot(0, self._fetch_tokens)
        except Exception as exc:
            QTimer.singleShot(0, lambda e=str(exc): self._status_lbl.setText(f"Revoke failed: {e}"))

    def _add_token(self):
        label = self._label_edit.text().strip()
        if not label:
            self._status_lbl.setText("Enter a label for the new user.")
            return
        self._label_edit.setEnabled(False)
        self._status_lbl.setText("Creating token…")
        threading.Thread(target=self._do_add, args=(label,), daemon=True).start()

    def _do_add(self, label: str):
        try:
            payload = json.dumps({"label": label}).encode()
            req = urllib.request.Request(
                f"{_RELAY_URL}/remote/fleet/tokens",
                data=payload,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Fleet-Token": _FLEET_TOKEN,
                },
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
            QTimer.singleShot(0, lambda d=data: self._show_new_token(d))
        except Exception as exc:
            QTimer.singleShot(0, lambda e=str(exc): self._add_failed(e))

    def _show_new_token(self, data: dict):
        self._label_edit.setEnabled(True)
        self._label_edit.clear()
        raw_token = data.get("token", "")
        label     = data.get("label", "")

        dlg = QDialog(self)
        dlg.setWindowTitle("New Command Access Token")
        dlg.setFixedWidth(480)
        dlg.setStyleSheet(f"background: {BG}; color: {SILVER};")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(10)

        vl.addWidget(QLabel(f"<b>Token created for: {label}</b>"))
        warn = QLabel("Copy this token and give it to the user.\nIt will NOT be shown again.")
        warn.setStyleSheet("color: #e8a020; font-size: 11px;")
        warn.setWordWrap(True)
        vl.addWidget(warn)

        from PyQt6.QtWidgets import QLineEdit
        token_box = QLineEdit(raw_token)
        token_box.setReadOnly(True)
        token_box.setStyleSheet(
            f"background: {BG2}; color: {GOLD}; border: 1px solid {BORDER};"
            " border-radius: 4px; padding: 6px 10px; font-family: 'Cascadia Code', monospace;"
            " font-size: 12px;"
        )
        token_box.selectAll()
        vl.addWidget(token_box)

        instr = QLabel(
            "They add this to their secrets.bat:\n\n"
            "  set CURSIV_RELAY_URL=<your Railway URL>\n"
            "  set CURSIV_FLEET_TOKEN=<this token>"
        )
        instr.setStyleSheet(
            f"background: {BG2}; color: {SILV2}; font-family: 'Cascadia Code', monospace;"
            f" font-size: 11px; padding: 10px; border: 1px solid {BORDER}; border-radius: 4px;"
        )
        vl.addWidget(instr)

        from PyQt6.QtWidgets import QDialogButtonBox
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(dlg.accept)
        bb.setStyleSheet(
            f"QPushButton {{ background: #d4b04c; color: #17120a; border-radius: 4px;"
            " font-weight: 600; padding: 6px 20px; }}"
        )
        vl.addWidget(bb)
        dlg.exec()
        self._fetch_tokens()

    def _add_failed(self, err: str):
        self._label_edit.setEnabled(True)
        self._status_lbl.setText(f"Failed: {err}")


def _fleet_age_label(last_seen_iso: str) -> str:
    try:
        ts  = datetime.fromisoformat(last_seen_iso)
        age = (datetime.utcnow() - ts).total_seconds()
        if age < 90:
            return "just now"
        if age < 3600:
            return f"{int(age // 60)}m ago"
        return f"{int(age // 3600)}h ago"
    except Exception:
        return last_seen_iso


def _fleet_dot(last_seen_iso: str) -> tuple[str, str]:
    """Returns (dot_char, color) for a status indicator."""
    try:
        ts  = datetime.fromisoformat(last_seen_iso)
        age = (datetime.utcnow() - ts).total_seconds()
        if age < 120:
            return "●", "#44cc66"
        if age < 600:
            return "●", "#e8a020"
        return "●", "#444466"
    except Exception:
        return "●", "#444466"


class FleetDialog(QDialog):
    """Fleet Dashboard — shows all Cursiv instances currently online."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv Fleet Dashboard")
        self.setFixedWidth(560)
        self.setStyleSheet(f"background: {BG}; color: {SILVER};")

        self._nodes: list[dict] = []
        self._error = ""

        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(20, 20, 20, 20)
        vlay.setSpacing(12)

        header = QLabel("⬢  Fleet Dashboard")
        header.setStyleSheet(f"color: {GOLD}; font-size: 14px; font-weight: 700;")
        vlay.addWidget(header)

        self._sub = QLabel("Machines that have checked in recently")
        self._sub.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        vlay.addWidget(self._sub)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(280)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 6px; }}"
        )
        self._cards = QWidget()
        self._cards.setStyleSheet(f"background: {BG2};")
        self._cards_lay = QVBoxLayout(self._cards)
        self._cards_lay.setContentsMargins(8, 8, 8, 8)
        self._cards_lay.setSpacing(6)
        self._scroll.setWidget(self._cards)
        vlay.addWidget(self._scroll)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setFixedHeight(28)
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setStyleSheet(
            f"background: #d4b04c; color: #17120a; border-radius: 4px;"
            " font-size: 11px; font-weight: 600; padding: 2px 16px;"
        )
        self._refresh_btn.clicked.connect(self._fetch)
        btn_row.addWidget(self._refresh_btn)

        if _is_owner_machine():
            mgmt_btn = QPushButton("⚙ Manage Access")
            mgmt_btn.setFixedHeight(28)
            mgmt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            mgmt_btn.setToolTip("Add or revoke command users (requires unlock code)")
            mgmt_btn.setStyleSheet(
                f"background: {BG2}; color: {GOLD}; border: 1px solid {LGOLD};"
                " border-radius: 4px; font-size: 11px; font-weight: 600; padding: 2px 14px;"
            )
            mgmt_btn.clicked.connect(self._open_manage_access)
            btn_row.addWidget(mgmt_btn)

        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"background: {BG2}; color: {SILV2}; border: 1px solid {BORDER};"
            " border-radius: 4px; font-size: 11px; padding: 2px 16px;"
        )
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        vlay.addLayout(btn_row)

        self._fetch()

        # Auto-refresh every 30s while open
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._fetch)
        self._timer.start(30_000)

    def _open_manage_access(self):
        unlock = _UnlockDialog(self)
        if unlock.exec() and unlock.verified():
            dlg = CommandAccessDialog(self)
            dlg.exec()

    def _fetch(self):
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("Refreshing…")
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        if not _RELAY_URL or not _FLEET_TOKEN:
            QTimer.singleShot(0, lambda: self._apply([], "CURSIV_RELAY_URL or CURSIV_FLEET_TOKEN not set in secrets.bat"))
            return
        try:
            req = urllib.request.Request(
                f"{_RELAY_URL}/remote/fleet",
                headers={"X-Fleet-Token": _FLEET_TOKEN},
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode())
            nodes = data.get("nodes", [])
            QTimer.singleShot(0, lambda n=nodes: self._apply(n, ""))
        except Exception as exc:
            QTimer.singleShot(0, lambda e=str(exc): self._apply([], e))

    def _apply(self, nodes: list, error: str):
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("Refresh")
        self._nodes = nodes
        self._error = error

        # Clear cards
        while self._cards_lay.count():
            item = self._cards_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if error:
            lbl = QLabel(f"⚠  {error}")
            lbl.setStyleSheet(f"color: #e8a020; font-size: 11px; padding: 8px;")
            lbl.setWordWrap(True)
            self._cards_lay.addWidget(lbl)
            self._sub.setText("Could not reach relay")
            return

        if not nodes:
            lbl = QLabel("No machines online in the last 10 minutes.")
            lbl.setStyleSheet(f"color: {SILV2}; font-size: 11px; padding: 8px;")
            self._cards_lay.addWidget(lbl)
            self._sub.setText("No machines online")
            return

        online = sum(1 for n in nodes if _fleet_dot(n["last_seen"])[1] == "#44cc66")
        self._sub.setText(f"{len(nodes)} machine{'s' if len(nodes) != 1 else ''} checked in  •  {online} online now")

        for node in nodes:
            dot, col = _fleet_dot(node["last_seen"])
            card = QWidget()
            card.setStyleSheet(
                f"background: {BG}; border: 1px solid {BORDER}; border-radius: 6px;"
            )
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 8, 12, 8)
            row.setSpacing(12)

            dot_lbl = QLabel(dot)
            dot_lbl.setStyleSheet(f"color: {col}; font-size: 10px; background: transparent; border: none;")
            dot_lbl.setFixedWidth(12)
            row.addWidget(dot_lbl)

            name_lbl = QLabel(f"<b>{node['machine_name']}</b>")
            name_lbl.setStyleSheet(f"color: {SILVER}; font-size: 12px; background: transparent; border: none;")
            row.addWidget(name_lbl, 2)

            status_lbl = QLabel(node.get("status", "idle").upper())
            status_lbl.setStyleSheet(
                f"color: {col}; font-size: 9px; font-weight: 600; "
                f"background: transparent; border: none; letter-spacing: 1px;"
            )
            row.addWidget(status_lbl, 1)

            ver_lbl = QLabel(node.get("version", ""))
            ver_lbl.setStyleSheet(f"color: {SILV2}; font-size: 10px; background: transparent; border: none;")
            row.addWidget(ver_lbl, 1)

            age_lbl = QLabel(_fleet_age_label(node["last_seen"]))
            age_lbl.setStyleSheet(f"color: {SILV2}; font-size: 10px; background: transparent; border: none;")
            age_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(age_lbl, 1)

            self._cards_lay.addWidget(card)

        self._cards_lay.addStretch()


class TitleBar(QWidget):
    def __init__(self, parent: QMainWindow, username: str = ""):
        super().__init__(parent)
        self._win    = parent
        self._drag   = False
        self._origin = QPoint()
        self.setFixedHeight(44)
        self.setObjectName("titleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"#titleBar {{ background: {BG}; border-bottom: 1px solid {BORDER}; }}")

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 8, 0)
        row.setSpacing(8)

        brand = QLabel("Cursiv")
        brand.setStyleSheet(f"color: {SILVER}; font-size: 14px; font-weight: 600;")
        row.addWidget(brand)
        row.addStretch()

        if username:
            u = QLabel(username)
            u.setStyleSheet(f"color: {SILV2}; font-size: 12px; padding-right: 6px;")
            row.addWidget(u)

        try:
            from cursiv_v215.core import profile as _profile
            _show_phone = _profile.personal()
        except Exception:
            _show_phone = False
        for symbol, tip, slot, col in [
            *([("☏", "Phone — link the phone app and see the shared conversation",
                lambda: parent._open_phone() if hasattr(parent, "_open_phone") else None, GOLD)] if _show_phone else []),
            ("⚙", "Settings — AI keys, Cursiv Cloud, data folder",
             lambda: parent._open_settings() if hasattr(parent, "_open_settings") else None, GOLD),
            ("☰", "Show or hide saved conversations",
             lambda: parent._toggle_sidebar() if hasattr(parent, "_toggle_sidebar") else None, SILV2),
            ("─", "Minimise", lambda: parent.showMinimized(), SILV2),
            ("□", "Maximise / restore  (F11: full screen)",
             lambda: parent._toggle_maximized() if hasattr(parent, "_toggle_maximized") else None, SILV2),
            ("✕", "Quit",
             lambda: parent._request_quit() if hasattr(parent, "_request_quit") else QApplication.quit(), RED),
        ]:
            btn = QPushButton(symbol)
            btn.setToolTip(tip)
            btn.setFixedSize(34, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            hover = theme.RED if col == RED else theme.TEXT
            btn.setStyleSheet(f"""
                QPushButton {{ background: transparent; color: {theme.MUTED}; font-size: 14px;
                               border-radius: 6px; border: none; }}
                QPushButton:hover {{ background: {theme.SURFACE2}; color: {hover}; }}
            """)
            btn.clicked.connect(slot)
            row.addWidget(btn)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            # Let Windows move the window (supports snapping to screen edges);
            # fall back to manual dragging if that isn't available.
            handle = self._win.windowHandle()
            if handle is not None and handle.startSystemMove():
                return
            self._drag   = True
            self._origin = e.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and hasattr(self._win, "_toggle_maximized"):
            self._win._toggle_maximized()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.MouseButton.LeftButton and not self._win.isMaximized():
            self._win.move(e.globalPosition().toPoint() - self._origin)

    def mouseReleaseEvent(self, e):
        self._drag = False


class _ResizeRoot(QWidget):
    """Root of the frameless main window: dragging within a few pixels of any
    edge or corner resizes the window (handed to Windows via startSystemResize)."""
    _M = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def _edges(self, pos) -> Qt.Edge:
        w, h, m = self.width(), self.height(), self._M
        edges = Qt.Edge(0)
        if pos.x() <= m: edges |= Qt.Edge.LeftEdge
        if pos.x() >= w - m: edges |= Qt.Edge.RightEdge
        if pos.y() <= m: edges |= Qt.Edge.TopEdge
        if pos.y() >= h - m: edges |= Qt.Edge.BottomEdge
        return edges

    def mouseMoveEvent(self, e):
        win = self.window()
        edges = self._edges(e.position().toPoint()) if not (win.isMaximized() or win.isFullScreen()) else Qt.Edge(0)
        diag1 = (Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.Edge.RightEdge | Qt.Edge.BottomEdge)
        diag2 = (Qt.Edge.RightEdge | Qt.Edge.TopEdge, Qt.Edge.LeftEdge | Qt.Edge.BottomEdge)
        if edges in diag1:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in diag2:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        win = self.window()
        if e.button() == Qt.MouseButton.LeftButton and not (win.isMaximized() or win.isFullScreen()):
            edges = self._edges(e.position().toPoint())
            if edges and win.windowHandle() is not None:
                win.windowHandle().startSystemResize(edges)
                return
        super().mousePressEvent(e)

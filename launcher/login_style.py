"""Shared login dialog controls and palette. No credential storage or recovery operations.

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



SILV  = "#C8C8D4"


BLUE  = "#d4b04c"


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
    background: {BLUE}; color: #17120a;
    border: none; border-radius: 6px;
    padding: 8px 20px; font-size: 13px; font-weight: 600;
}}
QPushButton:hover   {{ background: #e2c062; }}
QPushButton:pressed {{ background: #b8963a; }}
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

"""
"Receive from a phone over Wi-Fi": shows the address and code a phone types in its browser,
and what arrived. The laptop answers on the local network only while this window is open.
All the receiving is in cursiv_engine/core/phone_receive.py.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

import theme
from cursiv_engine.core import phone_receive


class _Signals(QObject):
    event = pyqtSignal(str)


class PhoneReceiveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Receive from a phone")
        self.resize(640, 560)
        self._signals = _Signals()
        self._signals.event.connect(self._on_event)
        self.imported = 0
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(10)

        title = QLabel("Receive from a phone over Wi-Fi")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        outer.addWidget(title)

        self._receiver = phone_receive.Receiver(report=self._signals.event.emit)
        try:
            port = self._receiver.start()
        except OSError as exc:
            self._receiver = None
            msg = QLabel(f"Couldn't open the receiving page on this laptop ({exc}). "
                         "Send the file by USB cable, AirDrop or Quick Share instead and use Import.")
            msg.setWordWrap(True)
            outer.addWidget(msg)
            self._add_close(outer)
            return

        addrs = phone_receive.lan_addresses()
        steps = QLabel(
            "1. Put the phone on the <b>same Wi-Fi</b> as this laptop (or this laptop on the phone's hotspot).<br>"
            "2. In the phone notebook, tap <b>Send to laptop</b> and save the file (iPhone: Save to Files).<br>"
            "3. In the phone's browser, open the address below, type the code, and pick the file.")
        steps.setWordWrap(True)
        outer.addWidget(steps)

        if addrs:
            where = "<br>".join(f"http://{ip}:{port}" for ip in addrs[:3])
            more = "" if len(addrs) == 1 else ("<br><span style='font-size:13px; font-weight:400;'>"
                                               "(more than one network: try the first one first)</span>")
        else:
            where, more = "No local network found", ("<br><span style='font-size:13px; font-weight:400;'>"
                                                     "Connect this laptop to Wi-Fi or a phone's hotspot, "
                                                     "then open this window again.</span>")
        addr = QLabel(f"{where}{more}")
        addr.setStyleSheet("font-size: 22px; font-weight: 600; font-family: Consolas, Menlo, monospace;")
        addr.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(addr)
        code = QLabel(f"Code:  {self._receiver.code[:3]} {self._receiver.code[3:]}")
        code.setStyleSheet(f"font-size: 30px; font-weight: 700; color: {theme.ACCENT};")
        outer.addWidget(code)

        note = QLabel("Only devices on this local network, with the code, can send. Nothing goes to the internet. "
                      f"It stops when you close this window, after {phone_receive.IDLE_MINUTES} minutes with nothing "
                      f"received, or after {phone_receive.WRONG_CODES} wrong codes. If Windows asks whether to let "
                      "Cursiv use the network, allow it on <b>private</b> networks only.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.MUTED};")
        outer.addWidget(note)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Waiting for a phone…")
        outer.addWidget(self._log, 1)
        self._add_close(outer)

    def _add_close(self, outer) -> None:
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton("Stop and close")
        close.setStyleSheet(theme.ghost_button())
        close.clicked.connect(self.accept)
        row.addWidget(close)
        outer.addLayout(row)

    def _on_event(self, text: str) -> None:
        self.imported = self._receiver.imported
        self._log.appendPlainText(text + "\n")

    def done(self, result: int) -> None:          # accept, reject, Esc and the window's X all come here
        if self._receiver:
            self._receiver.stop()
        super().done(result)

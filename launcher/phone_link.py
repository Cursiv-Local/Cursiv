"""
Phone ↔ computer link: the desktop side of the phone app (cursiv.us/app).

The phone and computer share one conversation ("space") on the owner's
Cloudflare site. Linking: the phone's Link button shows a 6-digit code; enter
it here. This computer's device token is kept in %USERPROFILE%\\.cursiv\\space.json.
The window shows the shared conversation (photos included), polls for new
messages, and can send questions and photos that also appear on the phone.
"""
from __future__ import annotations

import base64
import html
import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout,
)
from theme import BG, BG2, BORDER, GOLD, SILVER, SILV2, RED, GREEN  # one palette for every window (theme.py)

API = "https://cursiv.us"
SPACE_FILE = Path.home() / ".cursiv" / "space.json"



def load_token() -> str:
    try:
        return json.loads(SPACE_FILE.read_text(encoding="utf-8")).get("token", "")
    except Exception:
        return ""


def save_token(token: str) -> None:
    """Link this computer: keep other settings, remember whose memory the phone feeds."""
    try:
        state = json.loads(SPACE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    try:
        from cursiv_engine.memory import semantic
        state["person"] = semantic.current_person()
    except Exception:
        pass
    state.update({"token": token, "learned_until": "", "digest_hash": ""})
    SPACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SPACE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def api(path: str, payload: dict | None = None, token: str = "", timeout: float = 90) -> dict:
    headers = {"Content-Type": "application/json", "User-Agent": "Cursiv-Desktop"}
    if token:
        headers["Authorization"] = f"Space {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            detail = ""
        raise RuntimeError(detail or f"the server answered {e.code}") from None


def _fmt(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(^|[^*])\*([^*\n]+)\*", r"\1<i>\2</i>", t)
    return t.replace("\n", "<br>")


_IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


def _image_url(mime: str, data: str) -> str:
    """A data URL for a photo from the phone space, or "" when it isn't a plain image (U103: both
    parts go into the window's HTML, so nothing else may get through)."""
    if mime not in _IMAGE_TYPES or not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", data or ""):
        return ""
    return f"data:{mime};base64,{data}"


class _Signals(QObject):
    messages = pyqtSignal(list)
    image = pyqtSignal(str, str)          # message id, data URL
    done = pyqtSignal(str, bool, str)     # action, ok, info


class PhoneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Phone")
        self.resize(640, 720)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel {{ color: {SILVER}; background: transparent; }}
            QTextBrowser {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 6px;
                            font-family: 'Segoe UI'; font-size: 13px; padding: 6px; }}
            QLineEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 4px; padding: 7px; font-size: 13px; }}
            QPushButton {{ background: #d4b04c; color: #17120a; border: none; border-radius: 4px; padding: 7px 14px; font-weight: 600; }}
            QPushButton:disabled {{ background: #2a2a3f; color: #777; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
        """)
        self._token = load_token()
        self._sig = _Signals()
        self._sig.messages.connect(self._on_messages)
        self._sig.image.connect(self._on_image)
        self._sig.done.connect(self._on_done)
        self._msgs: dict[str, dict] = {}
        self._images: dict[str, str] = {}
        self._last = ""
        self._busy = False
        self._photo = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        title = QLabel("Phone")
        title.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: 700;")
        lay.addWidget(title)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        lay.addWidget(self._status)

        # Not linked yet
        self._link_row = QHBoxLayout()
        self._code = QLineEdit()
        self._code.setPlaceholderText("6-digit code from the phone")
        self._code.setMaxLength(6)
        self._link_row.addWidget(self._code, 1)
        self._link_btn = QPushButton("Link")
        self._link_btn.clicked.connect(self._link)
        self._link_row.addWidget(self._link_btn)
        lay.addLayout(self._link_row)

        # Linked: conversation
        self._view = QTextBrowser()
        self._view.setOpenExternalLinks(False)
        lay.addWidget(self._view, 1)
        self._photo_label = QLabel("")
        self._photo_label.setStyleSheet(f"color: {GREEN}; font-size: 12px;")
        lay.addWidget(self._photo_label)
        send_row = QHBoxLayout()
        self._attach = QPushButton("Add photo")
        self._attach.setObjectName("ghost")
        self._attach.clicked.connect(self._pick_photo)
        send_row.addWidget(self._attach)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask about a page, or continue the conversation…")
        self._input.returnPressed.connect(self._send)
        send_row.addWidget(self._input, 1)
        self._send_btn = QPushButton("Send")
        self._send_btn.clicked.connect(self._send)
        send_row.addWidget(self._send_btn)
        lay.addLayout(send_row)
        self._share = QCheckBox("Let the phone app use my memories (a short summary is kept on cursiv.us)")
        self._share.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        try:
            import phone_sync
            self._share.setChecked(phone_sync.share_enabled())
            self._share.toggled.connect(phone_sync.set_share)
        except Exception:
            self._share.setEnabled(False)
        lay.addWidget(self._share)
        tools = QHBoxLayout()
        self._code_btn = QPushButton("Link another device")
        self._code_btn.setObjectName("ghost")
        self._code_btn.clicked.connect(self._show_code)
        tools.addWidget(self._code_btn)
        self._unlink_btn = QPushButton("Unlink this computer")
        self._unlink_btn.setObjectName("ghost")
        self._unlink_btn.clicked.connect(self._unlink)
        tools.addWidget(self._unlink_btn)
        tools.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        tools.addWidget(close)
        lay.addLayout(tools)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(8000)
        self._refresh_mode()

    # ── state ────────────────────────────────────────────────────────────
    def _refresh_mode(self):
        linked = bool(self._token)
        for w in (self._code, self._link_btn):
            w.setVisible(not linked)
        for w in (self._view, self._attach, self._input, self._send_btn, self._code_btn, self._unlink_btn, self._photo_label, self._share):
            w.setVisible(linked)
        if linked:
            self._status.setText("Linked with the phone app. New messages from the phone appear here automatically.")
            self._poll()
        else:
            self._status.setText("On the phone, open Cursiv (cursiv.us/app), tap Link at the top, "
                                 "and type the 6-digit code here. The phone and this computer will then share one conversation.")

    def _run(self, action: str, fn):
        def work():
            try:
                self._sig.done.emit(action, True, fn() or "")
            except Exception as exc:
                self._sig.done.emit(action, False, str(exc))
        threading.Thread(target=work, daemon=True).start()

    # ── linking ──────────────────────────────────────────────────────────
    def _link(self):
        code = re.sub(r"\D", "", self._code.text())
        if len(code) != 6:
            self._status.setText("Enter the 6-digit code shown on the phone.")
            return
        self._link_btn.setEnabled(False)
        self._status.setText("Linking…")
        self._run("link", lambda: api("/api/space/join", {"code": code})["token"])

    def _show_code(self):
        self._status.setText("Getting a code…")
        self._run("code", lambda: api("/api/space/pair-code", {}, self._token)["code"])

    def _unlink(self):
        SPACE_FILE.unlink(missing_ok=True)
        self._token = ""
        self._msgs.clear(); self._images.clear(); self._last = ""
        self._view.clear()
        self._refresh_mode()

    # ── conversation ─────────────────────────────────────────────────────
    def _poll(self):
        if not self._token or self._busy:
            return
        token, since = self._token, self._last

        def work():
            try:
                msgs = api("/api/space/messages?since=" + urllib.request.quote(since), token=token, timeout=20)["messages"]
                self._sig.messages.emit(msgs)
                for m in msgs:
                    if m.get("has_image") and m["id"] not in self._images:
                        r = api(f"/api/space/image/{m['id']}", token=token, timeout=30)
                        url = _image_url(r.get("mime", ""), r.get("image", ""))
                        if url:
                            self._sig.image.emit(m["id"], url)
            except Exception as exc:
                if "isn't paired" in str(exc):
                    self._sig.done.emit("unpaired", False, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def _on_messages(self, msgs: list):
        changed = False
        for m in msgs:
            if m["id"] not in self._msgs:
                self._msgs[m["id"]] = m
                changed = True
            if m["created"] > self._last:
                self._last = m["created"]
        if changed:
            self._render()

    def _on_image(self, mid: str, url: str):
        self._images[mid] = url
        self._render()

    def _render(self):
        parts = []
        for m in sorted(self._msgs.values(), key=lambda x: x["created"]):
            who = "CURSIV" if m["role"] == "assistant" else ("You (phone)" if m.get("source") == "phone" else "You (computer)")
            color = GOLD if m["role"] == "assistant" else SILVER
            img = self._images.get(m["id"])
            img_html = f'<br><img src="{img}" width="320"><br>' if img else ("<br><i>[photo loading…]</i><br>" if m.get("has_image") else "")
            text = "" if m["text"] == "(photo)" else _fmt(m["text"])
            parts.append(f'<p><b style="color:{color}">{who}</b>{img_html}<br>{text}</p>')
        self._view.setHtml("".join(parts) or f'<p style="color:{SILV2}">No messages yet — ask something here or on the phone.</p>')
        self._view.verticalScrollBar().setValue(self._view.verticalScrollBar().maximum())

    def _pick_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a photo", "", "Images (*.jpg *.jpeg *.png *.webp *.heic *.bmp)")
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            self._status.setText("Couldn't open that image.")
            return
        if max(img.width(), img.height()) > 1600:
            img = img.scaled(1600, 1600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        buf = QBuffer(QByteArray())
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "JPEG", 82)
        self._photo = base64.b64encode(bytes(buf.data())).decode("ascii")
        self._photo_label.setText(f"Photo attached: {Path(path).name}")

    def _send(self):
        text = self._input.text().strip()
        if self._busy or (not text and not self._photo):
            return
        self._busy = True
        self._send_btn.setEnabled(False)
        payload = {"text": text, "image": self._photo, "image_mime": "image/jpeg", "source": "desktop"}
        self._input.clear(); self._photo = ""; self._photo_label.setText("")
        self._status.setText("Cursiv is reading…")
        token = self._token
        self._run("send", lambda: json.dumps(api("/api/space/ask", payload, token)))

    def _on_done(self, action: str, ok: bool, info: str):
        if action == "link":
            self._link_btn.setEnabled(True)
            if ok:
                save_token(info)
                self._token = info
                self._refresh_mode()
                try:   # learn from the phone conversation so far + share the memory summary
                    import phone_sync
                    threading.Thread(target=phone_sync.sync_once, daemon=True).start()
                except Exception:
                    pass
            else:
                self._status.setText(f"Couldn't link: {info}")
        elif action == "code":
            self._status.setText(f"Code for another device: {info}  (valid 10 minutes)" if ok else f"Couldn't get a code: {info}")
        elif action == "send":
            self._busy = False
            self._send_btn.setEnabled(True)
            if ok:
                r = json.loads(info)
                self._status.setText("Linked with the phone app. New messages from the phone appear here automatically.")
                self._on_messages([r["user"], r["reply"]])
                self._poll()          # picks up the photo for this message
            else:
                self._status.setText(f"Couldn't send: {info}")
        elif action == "unpaired":
            self._unlink()
            self._status.setText("This computer was unlinked. Get a new code from the phone to link again.")

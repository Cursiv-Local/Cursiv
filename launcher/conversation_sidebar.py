"""
Left sidebar: + New chat, Save, and the person's saved conversations
(newest first). Click to open; right-click to rename or delete. Leaving an
unsaved conversation (new chat, opening another, quitting) asks first.
"""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

import conversations
from theme import BG, BG2, BORDER, GOLD, SILVER, SILV2  # one palette for every window (theme.py)



def confirm_leave(parent, panel) -> bool:
    """If the current conversation has unsaved messages, ask Save / Don't Save / Cancel.
    Returns False only when the user cancels."""
    if panel is None or not panel.has_unsaved():
        return True
    box = QMessageBox(parent)
    box.setWindowTitle("Cursiv")
    box.setIcon(QMessageBox.Icon.Question)
    box.setText("Save this conversation?")
    box.setInformativeText("It isn't saved yet. Saved conversations appear in the sidebar so you can come back to them.")
    save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(save)
    box.exec()
    clicked = box.clickedButton()
    if clicked is cancel:
        return False
    if clicked is save:
        panel.save_conversation()
    return True


def _when(ts: float) -> str:
    d = time.localtime(ts)
    now = time.localtime()
    if d.tm_yday == now.tm_yday and d.tm_year == now.tm_year:
        return time.strftime("%I:%M %p", d).lstrip("0")
    return time.strftime("%b %d", d)


class ConversationSidebar(QWidget):
    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self._panel = panel
        self.setFixedWidth(236)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)   # paint the dark background
        self.setStyleSheet(f"""
            QWidget {{ background: {BG2}; }}
            QLabel {{ color: {SILV2}; font-size: 12px; font-weight: 600; background: transparent; padding-top: 6px; }}
            QPushButton {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 6px;
                           padding: 7px 10px; font-size: 12px; text-align: left; }}
            QPushButton:hover {{ border-color: #343a4a; background: #1b1f2a; }}
            QListWidget {{ background: {BG2}; color: {SILVER}; border: none; font-size: 12px; outline: none; }}
            QListWidget::item {{ padding: 8px 8px; border-radius: 6px; margin: 1px 0; }}
            QListWidget::item:hover {{ background: #1a1b28; }}
            QListWidget::item:selected {{ background: #1b1f2a; color: #e6e2d8; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 12, 10, 10)
        lay.setSpacing(8)
        row = QHBoxLayout()
        self._new = QPushButton("+  New chat")
        self._new.clicked.connect(self._new_chat)
        row.addWidget(self._new, 1)
        self._save = QPushButton("Save")
        self._save.setToolTip("Save this conversation (it then keeps itself up to date)")
        self._save.clicked.connect(self._save_chat)
        row.addWidget(self._save)
        lay.addLayout(row)
        head = QLabel("Conversations")
        lay.addWidget(head)
        self._list = QListWidget()
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)   # long titles end in "…"
        self._list.itemClicked.connect(self._open)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._menu)
        lay.addWidget(self._list, 1)
        self._empty = QLabel("Nothing saved yet.\nClick Save to keep a conversation.")
        self._empty.setWordWrap(True)
        self._empty.setStyleSheet(f"color: {SILV2}; font-size: 12px; letter-spacing: 0; padding: 6px 2px;")
        lay.addWidget(self._empty)
        panel.conversation_changed.connect(self.refresh)
        self.refresh()
        # older chats named after their first line get a 3-5 word topic title (signal -> refresh on the UI thread)
        conversations.retitle_old(panel.conversation_changed.emit)

    def refresh(self):
        current = self._panel.current_conversation_id()
        self._list.clear()
        convs = conversations.list_all()
        for c in convs:
            item = QListWidgetItem(f"{c['title']}\n{_when(c['updated'])}")
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            item.setToolTip(c["title"])
            self._list.addItem(item)
            if c["id"] == current:
                item.setSelected(True)
                self._list.setCurrentItem(item)
        self._empty.setVisible(not convs)
        self._save.setText("Saved" if current else "Save")

    def _busy(self) -> bool:
        if self._panel.is_busy():
            QMessageBox.information(self, "Cursiv", "Cursiv is still answering — wait a moment or press Stop.")
            return True
        return False

    def _new_chat(self):
        if self._busy() or not confirm_leave(self.window(), self._panel):
            return
        self._panel.new_conversation()

    def _save_chat(self):
        if self._panel.current_conversation_id():
            self._panel.save_conversation()
            return
        if not self._panel._history:
            QMessageBox.information(self, "Cursiv", "There's nothing to save yet — start a conversation first.")
            return
        title, ok = QInputDialog.getText(self, "Save conversation", "Name:",
                                         text=conversations.title_from(self._panel._history))
        if ok:
            self._panel.save_conversation(title.strip() or None)

    def _open(self, item: QListWidgetItem):
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        if conv_id == self._panel.current_conversation_id():
            return
        if self._busy() or not confirm_leave(self.window(), self._panel):
            self.refresh()
            return
        self._panel.open_conversation(conv_id)

    def _menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename = menu.addAction("Rename…")
        delete = menu.addAction("Delete")
        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen is rename:
            title, ok = QInputDialog.getText(self, "Rename conversation", "Name:", text=item.toolTip())
            if ok and title.strip():
                conversations.rename(conv_id, title)
                self.refresh()
        elif chosen is delete:
            if QMessageBox.question(self, "Cursiv", f"Delete \"{item.toolTip()}\"? This can't be undone.") \
                    == QMessageBox.StandardButton.Yes:
                conversations.delete(conv_id)
                if conv_id == self._panel.current_conversation_id():
                    self._panel.new_conversation()
                self.refresh()

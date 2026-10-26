"""Research entry points inside the existing desktop window.

This is presentation only: notebook and document operations use their existing
storage/verification APIs. Switching views never saves, sends or grants access.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

import theme


class ResearchFilesPanel(QWidget):
    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self._panel = panel
        self._pending_remove = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        title = QLabel("Research Files")
        title.setStyleSheet(f"color:{theme.TEXT};font-size:20px;font-weight:600;")
        layout.addWidget(title)
        scope = QLabel("Documents you import are available across workspaces. This library is not limited to a project. "
                       "Import a report or protocol, then ask Cursiv about it. The original file stays where it is.")
        scope.setWordWrap(True)
        scope.setStyleSheet(f"color:{theme.MUTED};")
        self._scope = scope
        layout.addWidget(scope)
        self._list = QListWidget()
        self._list.setWordWrap(True)
        self._list.currentItemChanged.connect(self._selection)
        self._list.setStyleSheet(f"QListWidget{{background:{theme.SURFACE};color:{theme.TEXT};"
                                f"border:1px solid {theme.BORDER};border-radius:8px;}}"
                                "QListWidget::item{padding:10px;}")
        layout.addWidget(self._list, 1)
        self._details = QLabel("")
        self._details.setWordWrap(True)
        self._details.setTextFormat(Qt.TextFormat.PlainText)
        self._details.setStyleSheet(f"color:{theme.MUTED};font-size:12px;")
        layout.addWidget(self._details)
        row = QHBoxLayout()
        self._import_btn = QPushButton("Import documents…")
        self._import_btn.setStyleSheet(theme.primary_button())
        self._import_btn.clicked.connect(self._import)
        self._ask_btn = QPushButton("Ask about selected")
        self._ask_btn.setStyleSheet(theme.ghost_button())
        self._ask_btn.clicked.connect(self._ask)
        self._remove_btn = QPushButton("Remove from library")
        self._remove_btn.setStyleSheet(theme.ghost_button())
        self._remove_btn.clicked.connect(self._propose_remove)
        for button in (self._import_btn, self._ask_btn, self._remove_btn):
            row.addWidget(button)
        layout.addLayout(row)
        self._status = QLabel("")
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._confirm_row = QWidget()
        confirm = QHBoxLayout(self._confirm_row)
        confirm.setContentsMargins(0, 0, 0, 0)
        self._confirm_remove = QPushButton("Yes, remove this copy")
        self._confirm_remove.clicked.connect(self._remove)
        cancel = QPushButton("Keep it")
        cancel.clicked.connect(self._cancel_remove)
        confirm.addWidget(self._confirm_remove)
        confirm.addWidget(cancel)
        confirm.addStretch()
        layout.addWidget(self._confirm_row)
        self._confirm_row.hide()
        self.refresh()

    def refresh(self):
        from cursiv_engine.core import documents
        self._cancel_remove()
        self._status.clear()
        self._list.clear()
        try:
            rows = documents.library()
        except (OSError, ValueError) as exc:
            self._status.setText(f"Could not read the document library: {exc}")
            return
        for record in rows:
            item = QListWidgetItem(f"{record['name']}\n{record['pages']} pages · imported {record['imported']}")
            item.setData(Qt.ItemDataRole.UserRole, record)
            self._list.addItem(item)
        if rows:
            self._list.setCurrentRow(0)
        else:
            self._status.setText("No documents yet. Import a PDF, text file, Markdown file or CSV to begin.")
        self._selection()

    def _selected(self):
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selection(self, *_):
        record = self._selected()
        self._ask_btn.setEnabled(bool(record))
        self._remove_btn.setEnabled(bool(record))
        self._details.setText("Source fingerprint: " + record['fingerprint'] if record else "")

    def _import(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Import research documents", "",
                                              "Documents (*.pdf *.txt *.md *.csv)")
        if not files:
            return
        self.import_files(files)

    def import_files(self, files):
        """Used by the picker; success follows the existing import operation."""
        from pathlib import Path
        from cursiv_engine.core import documents
        done, failed = [], []
        for name in files:
            try:
                record = documents.add(name)
                done.append(record['name'])
            except Exception as exc:
                failed.append(f"{Path(name).name}: {exc}")
        self.refresh()
        parts = (["Document indexed: " + ", ".join(done)] if done else [])
        if failed:
            parts.append("Not imported: " + "; ".join(failed))
        self._status.setText("\n".join(parts))

    def _ask(self):
        record = self._selected()
        if record:
            workspace = self.parent()
            while workspace is not None and not isinstance(workspace, ResearchWorkspace):
                workspace = workspace.parent()
            if workspace is not None:
                workspace.show_chat()
            # Preserve an unfinished message rather than replacing it with a template.
            if not self._panel._input.toPlainText().strip():
                self._panel.prefill(f'What does "{record["name"]}" say about ')
            self._panel._input.setFocus()

    def _propose_remove(self):
        record = self._selected()
        if record:
            self._pending_remove = dict(record)
            self._status.setText(f'Remove "{record["name"]}" from this library? The original file stays where it is.')
            self._confirm_row.show()

    def _cancel_remove(self):
        self._pending_remove = None
        if hasattr(self, '_confirm_row'):
            self._confirm_row.hide()

    def _remove(self):
        from cursiv_engine.core import documents
        record = self._pending_remove
        if not record:
            return
        try:
            removed = documents.remove(record['id'])
        except (OSError, ValueError) as exc:
            self._status.setText(f"Could not remove the library copy: {exc}")
            return
        self.refresh()
        self._status.setText("Removed from the library. The original file is unchanged." if removed else
                             "That document is no longer in the library.")


class ResearchWorkspace(QWidget):
    def __init__(self, chat_page, panel, parent=None):
        super().__init__(parent)
        self._panel = panel
        self._chat_page = chat_page
        self._files = None
        self._notebook = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        actions = QHBoxLayout()
        actions.setContentsMargins(14, 10, 14, 0)
        actions.setSpacing(8)
        self._actions = {}
        for title, method in (("Record Observation", self.record_observation), ("Ask Cursiv", self.show_chat),
                              ("Research Files", self.open_files), ("Field Notebook", self.open_notebook)):
            button = QPushButton(title)
            button.setObjectName(title.replace(' ', ''))
            button.setStyleSheet(theme.ghost_button(9))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, go=method: self._invoke(go))
            self._actions[title] = button
            actions.addWidget(button, 1)
        layout.addLayout(actions)
        self._view_status = QLabel("")
        self._view_status.setTextFormat(Qt.TextFormat.PlainText)
        self._view_status.setWordWrap(True)
        self._view_status.setStyleSheet(f"color:{theme.RED};padding:0 14px;")
        self._view_status.hide()
        layout.addWidget(self._view_status)
        self._guidance = QFrame()
        self._guidance.setStyleSheet(f"QFrame{{background:{theme.SURFACE};border:1px solid {theme.BORDER};border-radius:8px;}}"
                                    "QLabel{border:none;background:transparent;}")
        guide = QVBoxLayout(self._guidance)
        guide.setContentsMargins(16, 10, 16, 10)
        top = QHBoxLayout()
        intro = QLabel("Start with your research")
        intro.setStyleSheet(f"color:{theme.ACCENT};font-size:15px;font-weight:600;")
        top.addWidget(intro, 1)
        example = QPushButton("Show an example")
        example.clicked.connect(lambda: self._sample.setVisible(not self._sample.isVisible()))
        dismiss = QPushButton("Got it — continue")
        dismiss.clicked.connect(self._dismiss_guidance)
        for button in (example, dismiss):
            button.setStyleSheet(theme.ghost_button(8))
            top.addWidget(button)
        guide.addLayout(top)
        text = QLabel("Describe a reading, site and time; review before saving. Notebook keeps observations. "
                      "Research Files holds imported documents. Confirmed memory keeps context. Local work needs no Wi-Fi.")
        text.setWordWrap(True)
        text.setStyleSheet(f"color:{theme.MUTED};")
        guide.addWidget(text)
        self._sample = QLabel("Example only — not saved\nWater temperature was 21.4°C at Willow Basin at 2:15 pm.")
        self._sample.setWordWrap(True)
        self._sample.setTextFormat(Qt.TextFormat.PlainText)
        self._sample.hide()
        guide.addWidget(self._sample)
        layout.addWidget(self._guidance)
        self._guidance.hide()
        self._compact_guide = QPushButton("Getting started · Show guide")
        self._compact_guide.setStyleSheet(theme.ghost_button(7))
        self._compact_guide.clicked.connect(self._expand_guidance)
        layout.addWidget(self._compact_guide, 0, Qt.AlignmentFlag.AlignLeft)
        self._compact_guide.hide()
        self._back = QPushButton("← Back to chat")
        self._back.setStyleSheet(theme.ghost_button())
        self._back.clicked.connect(self.show_chat)
        layout.addWidget(self._back, 0, Qt.AlignmentFlag.AlignLeft)
        self._back.hide()
        self._stack = QStackedWidget()
        self._stack.addWidget(chat_page)
        layout.addWidget(self._stack, 1)

    def _invoke(self, action):
        self._view_status.hide()
        try:
            action()
        except Exception as exc:
            self._view_status.setText(f"Could not open this view: {exc}. Your current message has been kept.")
            self._view_status.show()

    def show_chat(self):
        self._stack.setCurrentWidget(self._chat_page)
        self._back.hide()
        self._panel._input.setFocus()

    def show_getting_started(self):
        self.show_chat()
        if self.window().height() < 600:
            self._guidance.hide()
            self._compact_guide.show()
        else:
            self._compact_guide.hide()
            self._guidance.show()

    def _expand_guidance(self):
        self._compact_guide.hide()
        self._guidance.show()

    def _dismiss_guidance(self):
        self._guidance.hide()
        self._compact_guide.setVisible(self.window().height() < 600)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_compact_guide') and self.window().height() < 600 and self._guidance.isVisible():
            self._guidance.hide()
            self._compact_guide.show()

    def record_observation(self):
        self.show_getting_started()

    def open_files(self):
        if self._files is None:
            self._files = ResearchFilesPanel(self._panel)
            self._stack.addWidget(self._files)
        else:
            self._files.refresh()
        self._guidance.hide()
        self._compact_guide.hide()
        self._back.show()
        self._stack.setCurrentWidget(self._files)

    def open_notebook(self, photos=None):
        if self._notebook is None:
            from field_notebook import FieldNotebookDialog
            from cursiv_engine.memory.semantic import current_person
            page = QWidget()
            contents = QVBoxLayout(page)
            contents.setContentsMargins(12, 0, 12, 0)
            scope = QLabel("All notebook entries are shown here. Project labels do not restrict access to records.")
            scope.setWordWrap(True)
            scope.setStyleSheet(f"color:{theme.MUTED};")
            contents.addWidget(scope)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            self._notebook = FieldNotebookDialog(observer=current_person().title())
            self._notebook.setWindowFlags(Qt.WindowType.Widget)
            self._notebook.finished.connect(self.show_chat)
            scroll.setWidget(self._notebook)
            contents.addWidget(scroll, 1)
            self._notebook_page = page
            self._stack.addWidget(page)
        self._notebook.refresh()
        if photos:
            self._notebook.add_photos(photos)
        self._guidance.hide()
        self._compact_guide.hide()
        self._back.show()
        self._stack.setCurrentWidget(self._notebook_page)
        self._notebook.show()

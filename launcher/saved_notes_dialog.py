"""Saved Notes: existing Qt/theme patterns, expandable records, no archive writes."""
from collections import Counter
from html import escape
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QAbstractItemView, QComboBox, QDialog, QFileDialog, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
    QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout)
import theme
import saved_notes as notes

ROLE = Qt.ItemDataRole.UserRole


class SavedNotesDialog(QDialog):
    def __init__(self, parent=None, *, category=None, query=''):
        super().__init__(parent)
        self.setWindowTitle('Cursiv — Saved Notes')
        self.resize(940, 650)
        self.setStyleSheet(f'''
            QDialog {{ background: {theme.BG}; color: {theme.TEXT}; }}
            QLabel {{ color: {theme.TEXT}; background: transparent; }}
            QListWidget, QTreeWidget, QPlainTextEdit {{ background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid {theme.BORDER}; border-radius: 6px; }}
            QListWidget::item {{ padding: 8px; }}
            QListWidget::item:selected, QTreeWidget::item:selected {{ background: {theme.SURFACE2}; color: {theme.TEXT}; }}
            QTreeWidget::item {{ padding: 7px 4px; }}
            QHeaderView::section {{ background: {theme.SURFACE2}; color: {theme.MUTED}; border: none; padding: 7px; }}
            QLineEdit, QComboBox {{ background: {theme.SURFACE}; color: {theme.TEXT};
                border: 1px solid {theme.BORDER}; border-radius: 4px; padding: 7px; }}
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        self._title = QLabel('Saved Notes')
        self._title.setStyleSheet(f'color: {theme.ACCENT}; font-size: 18px; font-weight: 650;')
        layout.addWidget(self._title)
        layout.addWidget(QLabel('Browse the notes you kept. Expand a note to read its full content and details.'))
        controls = QHBoxLayout()
        self._search = QLineEdit(query)
        self._search.setPlaceholderText('Search notes…')
        controls.addWidget(self._search, 1)
        self._sort = QComboBox()
        for label, value in (('Newest first', 'newest'), ('Oldest first', 'oldest'), ('Category', 'category')):
            self._sort.addItem(label, value)
        controls.addWidget(self._sort)
        refresh = QPushButton('Refresh')
        refresh.setStyleSheet(theme.ghost_button())
        refresh.clicked.connect(self.reload)
        controls.addWidget(refresh)
        layout.addLayout(controls)
        split = QSplitter(Qt.Orientation.Horizontal)
        self._categories = QListWidget()
        self._categories.setMinimumWidth(160)
        self._categories.setMaximumWidth(240)
        split.addWidget(self._categories)
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(['Note', 'Category', 'Saved', 'Source'])
        self._tree.setColumnWidth(0, 350)
        self._tree.setColumnWidth(1, 110)
        self._tree.setColumnWidth(2, 145)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            self._tree.header().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setUniformRowHeights(False)
        self._tree.itemExpanded.connect(self._expand)
        self._tree.itemSelectionChanged.connect(self._selection_changed)
        split.addWidget(self._tree)
        split.setStretchFactor(1, 1)
        split.setSizes([180, 720])
        layout.addWidget(split, 1)
        self._status = QLabel('')
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f'color: {theme.MUTED}; font-size: 12px;')
        layout.addWidget(self._status)
        bottom = QHBoxLayout()
        self._copy = QPushButton('Copy selected')
        self._copy.clicked.connect(self._copy_selected)
        self._export = QPushButton('Export selected…')
        self._export.clicked.connect(self._export_selected)
        for button in (self._copy, self._export):
            button.setStyleSheet(theme.ghost_button())
            bottom.addWidget(button)
        delete = QPushButton('Delete selected')
        delete.setStyleSheet(theme.ghost_button())
        delete.setEnabled(False)
        delete.setToolTip('This archive has no supported deletion API. This viewer never rewrites your notes.')
        self._delete = delete
        bottom.addWidget(delete)
        bottom.addStretch(1)
        done = QPushButton('Done')
        done.setStyleSheet(theme.primary_button())
        done.clicked.connect(self.close)
        bottom.addWidget(done)
        layout.addLayout(bottom)
        self._records = []
        self._warnings = []
        self._categories.currentRowChanged.connect(self._filter)
        self._search.textChanged.connect(self._filter)
        self._sort.currentIndexChanged.connect(self._filter)
        self.reload(category=category)

    def reload(self, checked=False, *, category=None):
        if category is None and self._categories.currentItem():
            category = self._categories.currentItem().data(ROLE)
        try:
            records, warnings = notes.read_notes()
        except (OSError, ValueError) as exc:
            self._records = []
            self._tree.clear()
            self._categories.clear()
            self._title.setText('Saved Notes — unavailable')
            self._status.setText(f'Could not read saved notes: {exc}')
            self._selection_changed()
            return
        self._records, self._warnings = records, warnings
        self._title.setText(f'Saved Notes ({len(records)})')
        counts = Counter(notes.category(record) for record in records)
        if category is not None:
            category = next((raw for raw in counts if raw.casefold() == category.casefold()), category)
        self._categories.blockSignals(True)
        self._categories.clear()
        all_item = QListWidgetItem(f'All notes ({len(records)})')
        all_item.setData(ROLE, None)
        self._categories.addItem(all_item)
        selected = 0
        for raw, count in sorted(counts.items()):
            item = QListWidgetItem(f'{raw.replace("_", " ").title()} ({count})')
            item.setData(ROLE, raw)
            self._categories.addItem(item)
            if raw == category:
                selected = self._categories.count() - 1
        if category is not None and category not in counts:
            item = QListWidgetItem(f'{category.replace("_", " ").title()} (0)')
            item.setData(ROLE, category)
            self._categories.addItem(item)
            selected = self._categories.count() - 1
        self._categories.setCurrentRow(selected)
        self._categories.blockSignals(False)
        self._filter()

    def apply_request(self, category=None, query=''):
        self._search.setText(query)
        if category is None:
            self._categories.setCurrentRow(0)
        self.reload(category=category)

    def _filter(self, *args):
        selected = self._categories.currentItem()
        category = selected.data(ROLE) if selected else None
        self._tree.clear()
        indexes = notes.select(self._records, self._search.text(), category, self._sort.currentData())
        for index in indexes:
            record = self._records[index]
            query, answer, _ = notes.content(record)
            preview = ' '.join((query or answer or 'Untitled note').split())
            item = QTreeWidgetItem([preview[:100] + ('…' if len(preview) > 100 else ''),
                notes.category(record).replace('_', ' ').title(), notes.date_label(record), str(record.get('source', 'Not recorded'))])
            item.setData(0, ROLE, ('note', index))
            item.setToolTip(0, '<qt>' + escape(preview[:500]) + '</qt>')
            QTreeWidgetItem(item, ['Expand to read'])
            self._tree.addTopLevelItem(item)
        self._status.setText(f'{len(indexes)} of {len(self._records)} notes shown.' +
            (f' {len(self._warnings)} unreadable record(s); archive unchanged.' if self._warnings else ''))
        self._selection_changed()

    def _expand(self, item):
        data = item.data(0, ROLE)
        if not data or item.data(0, ROLE + 1):
            return
        kind, index = data
        item.setData(0, ROLE + 1, True)
        item.takeChildren()
        record = self._records[index]
        body = QTreeWidgetItem(item)
        body.setFirstColumnSpanned(True)
        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setMinimumHeight(200)
        if kind == 'note':
            editor.setPlainText(notes.full_text(record))
            metadata = QTreeWidgetItem(item, ['Details: ID, source, timestamps and metadata'])
            metadata.setData(0, ROLE, ('metadata', index))
            QTreeWidgetItem(metadata, ['Expand for metadata'])
        else:
            editor.setPlainText(json.dumps(record, ensure_ascii=False, indent=2))
        self._tree.setItemWidget(body, 0, editor)

    def _selected_records(self):
        indexes = set()
        for item in self._tree.selectedItems():
            while item is not None:
                data = item.data(0, ROLE)
                if data:
                    indexes.add(data[1])
                    break
                item = item.parent()
        return [self._records[index] for index in sorted(indexes) if index < len(self._records)]

    def _selection_changed(self):
        selected = bool(self._selected_records())
        self._copy.setEnabled(selected)
        self._export.setEnabled(selected)

    def _copy_selected(self):
        QApplication.clipboard().setText('\n\n---\n\n'.join(notes.full_text(r) for r in self._selected_records()))
        self._status.setText('Selected note content copied.')

    def _export_selected(self):
        records = self._selected_records()
        if not records:
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export selected notes', 'Cursiv-notes.json', 'JSON (*.json)')
        if not path:
            return
        try:
            notes.export_selected(records, path)
            self._status.setText(f'Exported and verified {len(records)} note(s). Original notes unchanged.')
        except (OSError, ValueError) as exc:
            self._status.setText(f'Export not confirmed: {exc}')

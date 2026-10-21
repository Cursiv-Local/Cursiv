"""
"What I remember" -- see, search, add and delete Cursiv's saved memories.

Shows the logged-in person's facts plus family-wide ones (memory/semantic.py),
with a learning on/off switch. Opened from Settings and the tray menu.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout,
)
from theme import BG, BG2, BORDER, GOLD, SILVER, SILV2  # one palette for every window (theme.py)



class MemoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from cursiv_v215.memory import semantic as sem
        self._sem = sem
        self.setWindowTitle("Cursiv — What I Remember")
        self.resize(660, 600)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel {{ color: {SILVER}; background: transparent; }}
            QListWidget {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 6px; font-size: 13px; }}
            QListWidget::item {{ padding: 7px 6px; border-bottom: 1px solid {BORDER}; }}
            QListWidget::item:selected {{ background: #1b1f2a; }}
            QLineEdit, QComboBox {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; border-radius: 4px; padding: 6px; }}
            QPushButton {{ background: #d4b04c; color: #17120a; border: none; border-radius: 4px; padding: 6px 14px; font-weight: 600; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
            QCheckBox {{ color: {SILVER}; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        who = sem.current_person()
        title = QLabel(f"What I remember — {who.title() if who != sem.SHARED else 'Family'}")
        title.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: 700;")
        lay.addWidget(title)
        sub = QLabel("Things Cursiv keeps in mind about you, saved only on this computer. Facts marked "
                     "\"family\" are shared with everyone who uses Cursiv here.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        lay.addWidget(sub)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search memories…")
        self._search.textChanged.connect(self._refresh)
        lay.addWidget(self._search)
        self._historical = QCheckBox('Include superseded memories')
        self._historical.toggled.connect(self._refresh)
        lay.addWidget(self._historical)
        self._list = QListWidget()
        self._list.setWordWrap(True)
        lay.addWidget(self._list, 1)

        add_row = QHBoxLayout()
        self._new = QLineEdit()
        self._new.setPlaceholderText("Add something to remember…")
        self._new.returnPressed.connect(self._add)
        add_row.addWidget(self._new, 1)
        self._scope = QComboBox()
        self._scope.addItem("Just me", "me")
        self._scope.addItem("Whole family", "family")
        add_row.addWidget(self._scope)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        add_row.addWidget(add_btn)
        lay.addLayout(add_row)

        bottom = QHBoxLayout()
        self._learn = QCheckBox("Learn lasting facts from our conversations")
        self._learn.setChecked(sem.learning_enabled())
        self._learn.toggled.connect(self._set_learning)
        bottom.addWidget(self._learn, 1)
        delete = QPushButton("Forget selected")
        delete.setObjectName("ghost")
        delete.clicked.connect(self._delete)
        bottom.addWidget(delete)
        done = QPushButton("Done")
        done.clicked.connect(self.accept)
        bottom.addWidget(done)
        lay.addLayout(bottom)
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        lay.addWidget(self._status)
        self._refresh()

    def _refresh(self):
        q = self._search.text().strip().lower()
        try:
            facts = self._sem.list_facts(self._sem.current_person(), include_superseded=self._historical.isChecked())
        except OSError as exc:
            self._status.setText(f'Could not read memories: {type(exc).__name__}')
            return
        if q:
            facts = [f for f in facts if q in f["text"].lower()]
        self._list.clear()
        for f in reversed(facts):
            item = QListWidgetItem(f"{f['text']}\n{self._sem.fact_subtitle(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f["id"])
            self._list.addItem(item)
        self._status.setText(f"{len(facts)} memor{'y' if len(facts) == 1 else 'ies'}"
                             + ("" if self._sem.embeddings_available() else
                                "  ·  matching by keywords (Setup can install the local meaning-search model)"))

    def _set_learning(self, on):
        try:
            self._sem.set_learning(on)
        except (OSError, ValueError) as exc:
            self._learn.blockSignals(True)
            self._learn.setChecked(self._sem.learning_enabled())
            self._learn.blockSignals(False)
            self._status.setText(f'Learning setting not saved: {type(exc).__name__}')

    def _add(self):
        text = self._new.text().strip()
        if not text:
            return
        person = self._sem.SHARED if self._scope.currentData() == "family" else None
        try:
            saved = self._sem.add_fact(text, person, source="manual")
        except (OSError, ValueError) as exc:          # too long, disk full, read-only drive: say so
            self._status.setText(f"Not saved: {exc}")
            return
        self._new.clear()
        self._refresh()
        self._status.setText("Saved and verified." if saved else "Already remembered.")

    def _delete(self):
        item = self._list.currentItem()
        try:
            if item and self._sem.delete_fact(item.data(Qt.ItemDataRole.UserRole)):
                self._refresh()
        except OSError as exc:
            self._status.setText(f'Could not confirm deletion: {type(exc).__name__}')

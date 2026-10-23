"""Small Qt journal panel using the same validated commands as conversation."""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPlainTextEdit,
                            QLineEdit, QPushButton, QComboBox, QCheckBox, QLabel, QMessageBox)
from cursiv_engine.core import curiosity, curiosity_engine


class CuriosityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from cursiv_engine.memory import semantic
        self.person = semantic.current_person()
        self.setWindowTitle('Curiosity Journal')
        self.resize(820, 650)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Evidence-based questions. Hypotheses are not recorded facts.'))
        self.project = QLineEdit('general')
        self.project.setPlaceholderText('Project/workspace association')
        layout.addWidget(self.project)
        self.items = QListWidget()
        self.items.currentRowChanged.connect(self.show_record)
        layout.addWidget(self.items)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details)
        self.question = QLineEdit()
        self.question.setPlaceholderText('Manual question, or field:<id> / memory:<id> as resolution evidence')
        layout.addWidget(self.question)
        row = QHBoxLayout()
        for label, action in [('Add', 'add'), ('Evaluate', 'evaluate'), ('Review evidence', 'review'),
                              ('Open', 'open'), ('Investigate', 'investigate'), ('Await evidence', 'await'),
                              ('Dismiss', 'dismiss'), ('Resolve', 'resolve'), ('Reopen', 'reopen')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, a=action: self.action(a))
            row.addWidget(button)
        layout.addLayout(row)
        self.automatic = QCheckBox('Automatic evaluation (requires memory learning)')
        self.suggestions = QCheckBox('Occasional suggestions (at most one per day)')
        layout.addWidget(self.automatic)
        layout.addWidget(self.suggestions)
        freq = QHBoxLayout()
        freq.addWidget(QLabel('Evaluate every eligible event count:'))
        self.frequency = QComboBox()
        for value in (1, 5, 10, 20, 100):
            self.frequency.addItem(str(value), value)
        freq.addWidget(self.frequency)
        layout.addLayout(freq)
        self.automatic.toggled.connect(lambda value: self.setting(automatic=value))
        self.suggestions.toggled.connect(lambda value: self.setting(suggestions=value))
        self.frequency.activated.connect(lambda index: self.setting(frequency=self.frequency.itemData(index)))
        bottom = QHBoxLayout()
        for label, action in [('Refresh', 'refresh'), ('Export', 'export'), ('Clear journal…', 'clear')]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, a=action: self.action(a))
            bottom.addWidget(button)
        layout.addLayout(bottom)
        self.refresh()

    def refresh(self):
        try:
            data = curiosity.load(self.person)
            self.records = sorted(data['records'], key=lambda r: -r['score'])
            self.items.clear()
            for record in self.records:
                self.items.addItem(f"{record['status']} · {record['project']} · {record['question']}")
            for control, key in ((self.automatic, 'automatic'), (self.suggestions, 'suggestions')):
                control.blockSignals(True)
                control.setChecked(data['settings'][key])
                control.blockSignals(False)
            self.frequency.setCurrentIndex(max(0, self.frequency.findData(data['settings']['frequency'])))
            if self.records:
                self.items.setCurrentRow(0)
        except (OSError, ValueError) as exc:
            self.details.setPlainText(f'Journal unavailable: {exc}')

    def show_record(self, index):
        if 0 <= index < len(getattr(self, 'records', [])):
            self.details.setPlainText(curiosity.render([self.records[index]]))

    def setting(self, **changes):
        try:
            curiosity.configure(self.person, **changes)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Setting not saved', str(exc))
        self.refresh()

    def action(self, action):
        index = self.items.currentRow()
        ident = self.records[index]['id'] if 0 <= index < len(self.records) else ''
        if action == 'refresh':
            self.refresh()
            return
        if action == 'clear':
            if QMessageBox.question(self, 'Clear journal?',
                'Clear entries and disable automatic curiosity? Verified recovery backups remain on this drive.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
            command = 'curiosity clear confirm'
        elif action == 'add':
            command = 'curiosity add ' + self.question.text()
        elif action in ('evaluate', 'export'):
            command = 'curiosity ' + action
        else:
            command = f'curiosity {action} {ident}'
            if action == 'resolve':
                command += ' :: ' + self.question.text()
        result = curiosity_engine.command(command, self.person, self.project.text().strip() or 'general')
        self.refresh()
        self.details.setPlainText(result or 'No action performed.')

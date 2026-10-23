"""Startup-only unlock/migration UI. Never receives model output or chat text."""
from __future__ import annotations

from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
from cursiv_engine.core import vault, vault_migration

SCOPE = (
    'Encrypt saved conversations, memories, saved notes, session history, project/style notes, '
    'curiosity records and their local backups. Existing IDs and data formats stay unchanged inside encryption.\n\n'
    'A separate passphrase is required each time Cursiv opens. Losing it loses access; login recovery cannot '
    'recover it. Keep an independent backup of the passphrase.\n\n'
    'Notebook observations/photos, workspace files, explicit exports/training data, logs and older external '
    'copies are not encrypted by this option. Existing deleted plaintext can remain recoverable on disk '
    'or in OneDrive history. Use OS/drive encryption for that threat.\n\n'
    'Close all other copies of Cursiv first. Encryption makes authenticated recovery copies before changing '
    'existing files. Keep the data-vault.json file and .vault-recovery folder with your data.'
)


def startup(*, configure=False) -> bool:
    """False means quit before importing chat/settings or starting background writers."""
    if configure:
        if QMessageBox.question(None, 'Optional data encryption', SCOPE + '\n\nEnable or resume encryption?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return False
        password, ok = QInputDialog.getText(None, 'Encryption passphrase',
                                           'Separate passphrase (at least 16 characters):',
                                           QLineEdit.EchoMode.Password)
        if not ok:
            return False
        confirmation, ok = QInputDialog.getText(None, 'Confirm passphrase', 'Repeat the encryption passphrase:',
                                               QLineEdit.EchoMode.Password)
        if not ok or confirmation != password:
            QMessageBox.warning(None, 'Encryption unchanged', 'Passphrases did not match. No data was changed.')
            return False
        try:
            vault_migration.require_closed()
            counts = vault_migration.migrate(password)
        except Exception as exc:
            QMessageBox.critical(None, 'Encryption not completed',
                                 f'{exc}\n\nKeep all files. Reopen with --encrypt-data to resume using the same passphrase.')
            return False
        QMessageBox.information(None, 'Encryption ready',
                                f'Encrypted and verified {sum(counts.values())} files. Open Cursiv normally to unlock.')
        return False
    if not any((r / vault.MARKER).exists() for r in vault.roots()):
        return True
    while True:
        password, ok = QInputDialog.getText(None, 'Unlock Cursiv data', 'Encryption passphrase:',
                                           QLineEdit.EchoMode.Password)
        if not ok:
            return False
        try:
            vault.unlock(password)
            return True
        except vault.VaultError as exc:
            QMessageBox.warning(None, 'Data stays locked', str(exc))

"""Startup-only unlock/migration UI. Never receives model output or chat text.

Since U97 a computer's conversations and memories are always encrypted: the first
start asks for a passphrase and encrypts what is already there; every start after
unlocks it. A Cursiv USB drive stays readable (the person's choice, like the AI
keys a drive carries); its data is decrypted on the way to the drive and
encrypted again when it comes back (launcher/usb_sync.py).
"""
from __future__ import annotations

import os

from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
from cursiv_engine.core import vault, vault_migration

SCOPE = (
    'Cursiv encrypts your saved conversations, memories, saved notes, session history, project and style '
    'notes, curiosity records and their local backups on this computer. Nothing changes in how you use them.\n\n'
    'Choose a passphrase of at least 16 characters. Cursiv asks for it each time it opens. If you lose it, '
    'that data cannot be recovered (your Cursiv login cannot reset it), so write it down somewhere safe.\n\n'
    'Not covered: field notebook entries and photos, workspace files, exports, logs, and copies on a Cursiv '
    'USB drive (a drive stays readable; use BitLocker To Go if it could be lost). Deleted files from before '
    'encryption can remain recoverable on disk or in OneDrive history.'
)


def _portable() -> bool:
    return os.environ.get('CURSIV_PORTABLE') == '1'


def _ask_new_passphrase() -> str | None:
    while True:
        password, ok = QInputDialog.getText(None, 'Encryption passphrase',
                                           'Choose a passphrase (at least 16 characters):',
                                           QLineEdit.EchoMode.Password)
        if not ok:
            return None
        if len(password) < 16:
            QMessageBox.warning(None, 'Passphrase too short', 'Use at least 16 characters. Nothing was changed.')
            continue
        confirmation, ok = QInputDialog.getText(None, 'Confirm passphrase', 'Type the passphrase again:',
                                               QLineEdit.EchoMode.Password)
        if not ok:
            return None
        if confirmation == password:
            return password
        QMessageBox.warning(None, 'Passphrases did not match', 'They did not match. Nothing was changed; try again.')


def _migrate(password: str) -> bool:
    try:
        vault_migration.require_closed()
        vault_migration.migrate(password)          # resumable; unlocks every root when done
        return True
    except Exception as exc:
        QMessageBox.critical(None, 'Encryption not finished',
                             f'{exc}\n\nNothing was lost: every file is kept and recovery copies were made. '
                             'Open Cursiv again and enter the same passphrase to finish.')
        return False


def _unfinished() -> bool:
    for root in vault.roots():
        if (root / vault.MARKER).exists() and vault.metadata(root)['state'] != 'ready':
            return True
    return False


def startup(*, configure=False) -> bool:
    """False means quit before importing chat/settings or starting background writers.

    configure=True (--encrypt-data) is kept for older instructions; it resumes or sets up
    exactly like a normal start.
    """
    has_vault = any((r / vault.MARKER).exists() for r in vault.roots())
    if not has_vault:
        if _portable():
            return True                    # a drive stays readable
        QMessageBox.information(None, 'Cursiv encrypts your data', SCOPE)
        password = _ask_new_passphrase()
        if password is None:
            QMessageBox.information(None, 'Cursiv', 'Cursiv needs an encryption passphrase to open. '
                                                    'Nothing was changed.')
            return False
        if not _migrate(password):
            return False
        # A computer whose other data folder had no data yet gets its vault on first write.
        return True
    while True:
        password, ok = QInputDialog.getText(None, 'Unlock Cursiv data', 'Encryption passphrase:',
                                           QLineEdit.EchoMode.Password)
        if not ok:
            return False
        try:
            if _unfinished():
                for root in vault.roots():                      # check it before resuming
                    if (root / vault.MARKER).exists():
                        vault.authenticate(root, password)
                return _migrate(password)
            vault.unlock(password)
            if not _portable() and not all((r / vault.MARKER).exists() for r in vault.roots() if r.exists()):
                return _migrate(password)                       # a data folder added since: encrypt it too
            return True
        except vault.VaultError as exc:
            QMessageBox.warning(None, 'Data stays locked', str(exc))

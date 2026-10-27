"""
Field Notebook window (research roadmap R1): record observations, see them,
correct one (a new entry with a reason), check the log is intact, export.
All storage and checks are in cursiv_engine/core/fieldlog.py.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QMenu,
)

import theme
from cursiv_engine.core import fieldlog

ROWS = 2      # measurement rows shown at first; "+ Another measurement" adds more


class FieldNotebookDialog(QDialog):
    def __init__(self, parent=None, observer: str = "", photos=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Field Notebook")
        self.resize(1000, 860)
        self._correcting: str = ""
        self._photos: list = []                 # files picked for this entry (or stored names when correcting)
        self._loc_from_photo = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(10)

        title = QLabel("Field Notebook")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        outer.addWidget(title)
        intro = QLabel("Recorded observations are kept as entered. Model suggestions stay in chat until you record them. "
                       "Corrections append a new entry with a reason; fingerprints detect later changes.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {theme.MUTED};")
        from phone_help import capture_html
        intro.setText(intro.text() + '<br><br>' + capture_html(theme.LINK))
        intro.setTextFormat(Qt.TextFormat.RichText)
        intro.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        intro.setOpenExternalLinks(True)
        outer.addWidget(intro)

        # ── New entry ──────────────────────────────────────────────────
        card = QFrame(); card.setObjectName("card")
        card.setStyleSheet(f"QFrame#card {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 10px; }}")
        form_box = QVBoxLayout(card); form_box.setContentsMargins(16, 12, 16, 12)
        self._form_title = QLabel("New entry"); self._form_title.setStyleSheet("font-weight: 600;")
        form_box.addWidget(self._form_title)
        form = QFormLayout(); form.setHorizontalSpacing(12)
        # The same on every system (macOS's default keeps fields narrow and labels right-aligned)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._observer = QLineEdit(observer); self._observer.setPlaceholderText("Who recorded it")
        self._site = QLineEdit(); self._site.setPlaceholderText("Site or station name")
        coords = QHBoxLayout()
        self._lat = QLineEdit(); self._lat.setPlaceholderText("Latitude, e.g. 44.1234")
        self._lon = QLineEdit(); self._lon.setPlaceholderText("Longitude, e.g. -71.5678")
        coords.addWidget(self._lat); coords.addWidget(self._lon)
        cw = QWidget(); cw.setLayout(coords); cw.setStyleSheet("background: transparent;")
        coords.setContentsMargins(0, 0, 0, 0)
        form.addRow("Observer", self._observer)
        form.addRow("Site", self._site)
        sample_row = QHBoxLayout(); sample_row.setContentsMargins(0, 0, 0, 0)
        self._sample = QLineEdit(); self._sample.setPlaceholderText("Optional, e.g. a vial or bag label")
        new_id = QPushButton("New ID"); new_id.setStyleSheet(theme.ghost_button())
        new_id.setToolTip("Site initials, today's date and the next free number")
        new_id.clicked.connect(lambda: self._sample.setText(fieldlog.new_sample_id(self._site.text())))
        sample_row.addWidget(self._sample, 1); sample_row.addWidget(new_id)
        sw = QWidget(); sw.setLayout(sample_row); sw.setStyleSheet("background: transparent;")
        form.addRow("Sample ID", sw)
        form.addRow("Location (decimal degrees)", cw)
        form_box.addLayout(form)

        grid = QGridLayout(); grid.setHorizontalSpacing(8)
        for col, head in enumerate(("Measurement", "Value (kept exactly as typed)", "Unit")):
            h = QLabel(head); h.setStyleSheet(f"color: {theme.MUTED}; font-size: 12px;"); grid.addWidget(h, 0, col)
        self._rows: list[tuple[QLineEdit, QLineEdit, QLineEdit]] = []
        self._grid = grid
        for _ in range(ROWS):
            self._add_row()
        form_box.addLayout(grid)
        more = QPushButton("+ Another measurement"); more.setStyleSheet(theme.ghost_button())
        more.clicked.connect(self._add_row)
        form_box.addWidget(more, 0, Qt.AlignmentFlag.AlignLeft)

        self._note = QPlainTextEdit(); self._note.setPlaceholderText("Notes (conditions, what you saw, anything else)")
        self._note.setFixedHeight(52)
        form_box.addWidget(self._note)
        photo_row = QHBoxLayout()
        add_photo = QPushButton("📎  Add photos…"); add_photo.setStyleSheet(theme.ghost_button())
        add_photo.setToolTip("Attach photos to this entry. The time and GPS position the camera recorded are kept, "
                             "and a missing location is filled in from the photo.")
        add_photo.clicked.connect(self._pick_photos)
        self._photo_lbl = QLabel(""); self._photo_lbl.setStyleSheet(f"color: {theme.MUTED};")
        photo_row.addWidget(add_photo); photo_row.addWidget(self._photo_lbl, 1)
        form_box.addLayout(photo_row)
        buttons = QHBoxLayout()
        self._save = QPushButton("Save entry"); self._save.setStyleSheet(theme.primary_button())
        self._save.clicked.connect(self._save_entry)
        self._cancel = QPushButton("Cancel correction"); self._cancel.setStyleSheet(theme.ghost_button())
        self._cancel.clicked.connect(self._clear_form); self._cancel.setVisible(False)
        buttons.addWidget(self._save); buttons.addWidget(self._cancel); buttons.addStretch(1)
        self._status = QLabel(""); self._status.setWordWrap(True)
        buttons.addWidget(self._status, 2)
        form_box.addLayout(buttons)
        outer.addWidget(card)

        # ── Entries ────────────────────────────────────────────────────
        self._integrity = QLabel("")
        outer.addWidget(self._integrity)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["#", "Recorded", "Site", "Measurements", "Recorded note"])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setMinimumHeight(220)
        outer.addWidget(self._table, 1)

        foot = QHBoxLayout()
        fix = QPushButton("Correct selected…"); fix.setStyleSheet(theme.ghost_button()); fix.clicked.connect(self._start_correction)
        check = QPushButton("Check integrity"); check.setStyleSheet(theme.ghost_button()); check.clicked.connect(self._check)
        exp = QPushButton("Export…"); exp.setStyleSheet(theme.ghost_button()); exp.clicked.connect(self._export)
        rep = QPushButton("Report…"); rep.setStyleSheet(theme.ghost_button()); rep.clicked.connect(self._report)
        share = QPushButton("Share with team…"); share.setStyleSheet(theme.ghost_button()); share.clicked.connect(self._share)
        imp = QPushButton("Import from team…"); imp.setStyleSheet(theme.ghost_button() +
                                                                  "QPushButton::menu-indicator { image: none; width: 0; }")
        imp_menu = QMenu(imp)
        imp_menu.addAction("From a USB stick or shared folder…", self._import)
        imp_menu.addAction("From a USB stick or shared folder, every photo required…", self._import_strict)
        imp_menu.addAction("From the phone notebook (.cursivsync file)…", self._import_phone)
        imp_menu.addAction("Receive from a phone over Wi-Fi…", self._receive_phone)
        imp_menu.addSeparator()
        imp_menu.addAction("Revoke a lost or retired device's key…", self._revoke)
        imp.setMenu(imp_menu)
        self._name_btn = QPushButton(""); self._name_btn.setStyleSheet(theme.ghost_button())
        self._name_btn.setToolTip("Whose notebook this is. Shared and imported work is kept in this name (U103).")
        self._name_btn.clicked.connect(self._name)
        self._show_name()
        close = QPushButton("Close"); close.setStyleSheet(theme.ghost_button()); close.clicked.connect(self.accept)
        key = QPushButton("Signing key…"); key.setStyleSheet(theme.ghost_button()); key.clicked.connect(self._signing_key)
        key.setToolTip("Protect this notebook's signing key with a passphrase, or unlock it (U105).")
        for b in (fix, check, exp, rep):
            foot.addWidget(b)
        foot.addStretch(1); foot.addWidget(close)
        outer.addLayout(foot)
        sharing = QHBoxLayout()
        for b in (share, imp, self._name_btn, key):
            sharing.addWidget(b)
        sharing.addStretch(1)
        outer.addLayout(sharing)
        self.refresh()
        from cursiv_engine.core import devicekey
        if devicekey.protected() and not devicekey.unlocked():
            self._status.setText("The signing key is locked: entries save as usual, but shares and exports can't "
                                 "be signed until you unlock it (Signing key…).")

    # ── form ───────────────────────────────────────────────────────────
    def _add_row(self):
        r = len(self._rows) + 1
        name, value, unit = QLineEdit(), QLineEdit(), QLineEdit()
        if r == 1:
            name.setPlaceholderText("e.g. water temp"); value.setPlaceholderText("12.40"); unit.setPlaceholderText("°C")
        for col, w in enumerate((name, value, unit)):
            self._grid.addWidget(w, r, col)
        self._rows.append((name, value, unit))

    # ── photos ────────────────────────────────────────────────────────
    def _pick_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add photos to this entry", "",
            "Photos (" + " ".join("*" + e for e in sorted(fieldlog.PHOTO_EXTS)) + ")")
        if files:
            self.add_photos(files)

    def add_photos(self, files) -> None:
        """Attach photos to the entry being written; fill a blank location from the first photo's GPS."""
        from pathlib import Path
        big = []
        for f in files:
            mb = Path(str(f)).stat().st_size / 2**20 if Path(str(f)).exists() else 0
            if mb > fieldlog.PHOTO_MAX_MB:
                QMessageBox.warning(self, "Photo too large",
                                    f"{Path(str(f)).name} is {mb:.0f} MB; photos over {fieldlog.PHOTO_MAX_MB} MB aren't kept.")
                continue
            if mb > fieldlog.PHOTO_WARN_MB:
                big.append(Path(str(f)).name)
            if f not in self._photos:
                self._photos.append(f)
        note = ""
        if not self._lat.text().strip() and not self._lon.text().strip():
            for f in files:
                info = fieldlog.photo_info(Path(f)) if Path(str(f)).exists() else {}
                if info.get("lat") is not None:
                    self._lat.setText(str(info["lat"])); self._lon.setText(str(info["lon"]))
                    self._loc_from_photo = True
                    note = " · location filled in from the photo's GPS"
                    break
        n = len(self._photos)
        if big:
            note += f" · {', '.join(big)} over {fieldlog.PHOTO_WARN_MB} MB"
        self._photo_lbl.setText(f"{n} photo{'s' if n != 1 else ''} attached{note}" if n else "")

    def _clear_form(self):
        self._correcting = ""
        self._photos = []
        self._loc_from_photo = False
        self._photo_lbl.setText("")
        self._form_title.setText("New entry")
        self._cancel.setVisible(False)
        self._save.setText("Save entry")
        for w in (self._site, self._sample, self._lat, self._lon):
            w.clear()
        for row in self._rows:
            for w in row:
                w.clear()
        self._note.clear()

    def _fields(self) -> dict:
        lat, lon = self._lat.text().strip(), self._lon.text().strip()
        return {
            "observer": self._observer.text(), "site": self._site.text(),
            "lat": lat or None, "lon": lon or None,
            "location_source": ("photo GPS" if self._loc_from_photo else "typed") if lat else "",
            "photos": list(self._photos),
            "measurements": [{"name": n.text(), "value": v.text(), "unit": u.text()}
                             for n, v, u in self._rows if n.text().strip()],
            "note": self._note.toPlainText(),
            "sample_id": self._sample.text(),
        }

    def _save_entry(self):
        f = self._fields()
        try:
            if self._correcting:
                reason, ok = QInputDialog.getText(self, "Reason for the correction",
                                                  "Why is this entry being corrected? (kept with both entries)")
                if not ok:
                    return
                e = fieldlog.correct(self._correcting, reason, **f)
            else:
                e = fieldlog.add(**f)
            actual = next((row for row in fieldlog.entries() if row.get('id') == e.get('id')), None)
            if actual != e or actual is None or fieldlog.record_problems(actual) or fieldlog.verify():
                raise OSError('read-back or chain verification failed; an entry may exist')
        except ValueError as exc:
            self._status.setText(f"Not saved: {exc}.")
            self._status.setStyleSheet(f"color: {theme.RED};")
            return
        except OSError as exc:
            self._status.setText(f"Not saved or not confirmed: {exc}. Check the notebook before retrying.")
            self._status.setStyleSheet(f"color: {theme.RED};")
            return
        try:
            from cursiv_engine.core import curiosity_engine
            from cursiv_engine.memory import semantic
            curiosity_engine.notify(semantic.current_person())
        except (OSError, ValueError):
            pass  # an optional suggestion cannot turn a verified save into failure
        sample = f" · sample {e['sample_id']}" if e.get('sample_id') else ''
        self._status.setText(f"Saved #{e['seq']}{sample} · fingerprint {e['hash'][:12]} · chain intact"
                             + (f" · {fieldlog.share_problem}" if fieldlog.share_problem else ""))
        self._status.setToolTip(f"Record ID: {e['id']}\nSHA-256: {e['hash']}")
        self._status.setStyleSheet(f"color: {theme.GREEN};")
        self._clear_form()
        self.refresh()

    def _start_correction(self):
        row = self._table.currentRow()
        if row < 0:
            self._status.setText("Select the entry to correct first.")
            return
        e = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._clear_form()
        self._correcting = e["id"]
        self._form_title.setText(f"Correcting #{e['seq']} (the original stays in the log)")
        self._save.setText("Save correction")
        self._cancel.setVisible(True)
        self._observer.setText(e["observer"]); self._site.setText(e["site"])
        self._sample.setText(e.get("sample_id", ""))
        self._lat.setText("" if e["lat"] is None else str(e["lat"]))
        self._lon.setText("" if e["lon"] is None else str(e["lon"]))
        while len(self._rows) < len(e["measurements"]):
            self._add_row()
        for (n, v, u), m in zip(self._rows, e["measurements"]):
            n.setText(m["name"]); v.setText(m["value"]); u.setText(m["unit"])
        self._note.setPlainText(e["note"])
        self._photos = list(e.get("photos") or [])
        self._photo_lbl.setText(f"{len(self._photos)} photo(s) kept from the original" if self._photos else "")

    # ── list, checks, export ───────────────────────────────────────────
    def done(self, result):
        """Closing the notebook on a drive brings its team copy up to date (U103)."""
        try:
            from cursiv_engine.core import fieldsync
            fieldsync.auto_share()
            fieldlog.share_problem = ""
        except (OSError, ValueError) as exc:
            fieldlog.share_problem = f"the team copy on the drive wasn't updated ({exc})"
        super().done(result)

    def refresh(self):
        rows = fieldlog.current()
        self._table.setRowCount(len(rows))
        for r, e in enumerate(reversed(rows)):
            meas = ", ".join(f"{m['name']} {m['value']}{(' ' + m['unit']) if m['unit'] else ''}" for m in e["measurements"])
            site = e["site"] + (f"  [{e['sample_id']}]" if e.get("sample_id") else "")
            photos = len(e.get("photos") or [])
            cells = [str(e["seq"]), e["recorded_local"].replace("T", " ")[:19], site, meas,
                     (f"📷 {photos}  " if photos else "") + e["note"]
                     + (f"  (corrects an earlier entry: {e['reason']})" if e.get("corrects") else "")]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, e)
                item.setToolTip('Recorded observation · ' + ('entered through chat' if e.get('chat_request_id') else
                                                          'notebook entry') +
                                f"\nRecord ID: {e['id']}\nFingerprint: {e['hash']}\n"
                                'Recording does not independently verify the observation.')
                self._table.setItem(r, c, item)
        self._show_integrity()

    def _show_integrity(self):
        problems = fieldlog.verify()
        n = len(fieldlog.entries())
        if problems:
            self._integrity.setText(f"⚠ The log has {len(problems)} problem(s). Click Check integrity for details.")
            self._integrity.setStyleSheet(f"color: {theme.RED};")
        else:
            self._integrity.setText(f"● {n} entries recorded, all intact and in order.")
            self._integrity.setStyleSheet(f"color: {theme.GREEN};")

    def _check(self):
        problems = fieldlog.verify() + fieldlog.photo_problems()     # photos too (slower, so only on request)
        if not problems:
            QMessageBox.information(self, "Field log", f"All {len(fieldlog.entries())} entries are intact and in order, "
                                                       "and every photo matches its fingerprint.\n\n" + fieldlog.CHECK_MEANS)
        else:
            QMessageBox.warning(self, "Field log", "\n".join(problems))
        self._show_integrity()

    def _export(self):
        from pathlib import Path
        folder = QFileDialog.getExistingDirectory(self, "Export the field log to…")
        if not folder:
            return
        try:
            paths = fieldlog.export(Path(folder) / "Cursiv field log")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Not exported", f"{exc}\n\nAny earlier export there is unchanged.")
            return
        QMessageBox.information(self, "Exported", "Saved and checked against its signature:\n"
                                + "\n".join(str(p) for p in paths.values()))

    def _report(self):
        """A printable report of the current entries, opened in the browser."""
        from pathlib import Path
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        rows = fieldlog.current()
        if not rows:
            QMessageBox.information(self, "Field report", "The field log is empty.")
            return
        folder = fieldlog.log_dir() / "reports"
        from datetime import datetime
        from cursiv_engine.core import atomic
        path = Path(folder) / f"field-report-{datetime.now():%Y-%m-%d_%H%M%S}.html"
        try:
            atomic.write_text(path, fieldlog.report_html(rows))
        except OSError as exc:
            QMessageBox.warning(self, "Field report", f"Couldn't save the report ({exc}).")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ── team sync (core/fieldsync.py): a USB drive or a shared folder, no internet ──
    def _share(self):
        from pathlib import Path
        from cursiv_engine.core import fieldsync
        folder = QFileDialog.getExistingDirectory(self, "Share the field log to (a USB drive or shared folder)…")
        if not folder:
            return
        try:
            out = fieldsync.share(Path(folder), self._observer.text().strip())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Not shared", str(exc))
            return
        QMessageBox.information(self, "Shared", f"This laptop's field log is in:\n{out}\n\n"
                                "On each other laptop: Import from team… and pick the same drive. "
                                "Only the field log is shared; memories and documents stay on this computer.")

    def _signing_key(self):
        """Protect the key that signs this notebook's shares and exports with a passphrase (U105), or unlock
        it. On a drive the key is otherwise readable by anyone holding the drive."""
        from cursiv_engine.core import devicekey
        if devicekey.protected() and not devicekey.unlocked():
            phrase, ok = QInputDialog.getText(self, "Unlock the signing key", "Signing-key passphrase:",
                                              QLineEdit.EchoMode.Password)
            if not ok:
                return
            try:
                devicekey.unlock(phrase)
            except ValueError as exc:
                QMessageBox.warning(self, "Still locked", str(exc))
                return
            self._status.setText("Signing key unlocked for this session. Shares and exports are signed again.")
            return
        if devicekey.protected():
            QMessageBox.information(self, "Signing key", "The signing key is protected by a passphrase and is "
                                    "unlocked for this session.")
            return
        ok = QMessageBox.question(
            self, "Protect the signing key",
            "This notebook's shares and exports are signed with a key stored in its data folder. On a Cursiv "
            "drive anyone holding the drive can read that key and sign in this notebook's name.\n\n"
            "Protect it with a passphrase? The key stays the same, so computers that already know it keep "
            "accepting its shares. You'll enter the passphrase once each time Cursiv starts, before sharing or "
            "exporting. Without it nothing can be signed, so keep it safe.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ok != QMessageBox.StandardButton.Yes:
            return
        first, ok = QInputDialog.getText(self, "Signing-key passphrase",
                                         f"New passphrase (at least {devicekey.MIN_PASSPHRASE} characters):",
                                         QLineEdit.EchoMode.Password)
        if not ok:
            return
        again, ok = QInputDialog.getText(self, "Signing-key passphrase", "Type it again:", QLineEdit.EchoMode.Password)
        if not ok:
            return
        if first != again:
            QMessageBox.warning(self, "Not protected", "The two passphrases don't match. Nothing was changed.")
            return
        try:
            info = devicekey.protect(first)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Not protected", str(exc))
            return
        self._status.setText(f"Signing key {info['key_id']} is now protected by a passphrase.")

    def _show_name(self):
        from cursiv_engine.core import fieldlog
        try:
            name = fieldlog.identity().get("name", "")
        except fieldlog.IdentityDamaged:
            name = ""
        self._name_btn.setText(f"Notebook: {name}…" if name else "Name this notebook…")

    def _name(self):
        """The person who records in this notebook. Their shared work arrives on the team's main computer in
        this name, with its photos (U103). Renaming keeps the notebook's id, so earlier work stays theirs."""
        from cursiv_engine.core import fieldlog
        try:
            current = fieldlog.identity().get("name", "")
        except fieldlog.IdentityDamaged as exc:
            QMessageBox.warning(self, "Notebook name", str(exc))
            return
        name, ok = QInputDialog.getText(self, "Name this notebook",
                                        "Who records in this notebook? (their name, as the team should see it)",
                                        text=current)
        if not ok:
            return
        try:
            fieldlog.set_name(name)
        except ValueError as exc:
            QMessageBox.warning(self, "Not named", str(exc))
            return
        self._show_name()

    def _revoke(self):
        """The team lead marks a lost, stolen or retired phone or laptop: its new files are refused."""
        from cursiv_engine.core import fieldsync
        devices = sorted(p.name[:-len(".key.json")] for p in fieldsync.team_dir().glob("*.key.json")) \
            if fieldsync.team_dir().is_dir() else []
        gone = {v["device"] for v in fieldsync.revoked().values()}
        devices = [d for d in devices if d not in gone]
        if not devices:
            QMessageBox.information(self, "Revoke a key", "No imported device has a signing key to revoke yet.")
            return
        device, ok = QInputDialog.getItem(self, "Revoke a device's key",
                                          "Device (its new files will be refused; what's already imported stays):",
                                          devices, 0, False)
        if not ok:
            return
        reason, ok = QInputDialog.getText(self, "Reason", "Why? (lost, stolen, retired…) Kept with the revocation:")
        if not ok:
            return
        try:
            fieldsync.revoke(device, reason, by=self._observer.text().strip())
        except ValueError as exc:
            QMessageBox.warning(self, "Not revoked", str(exc))
            return
        QMessageBox.information(self, "Revoked", f"{device}'s key is revoked. New files signed by it will be refused.")

    def _import_phone(self):
        """A file from the phone notebook (website/notebook), sent by USB, AirDrop or Quick Share."""
        from pathlib import Path
        from cursiv_engine.core import fieldsync
        f, _ = QFileDialog.getOpenFileName(self, "Import from the phone notebook", "",
                                           "Phone notebook (*.cursivsync)")
        if f:
            self._show_import(lambda: fieldsync.import_phone_bundle(Path(f)))

    def _receive_phone(self):
        """The phone sends its file over the local Wi-Fi, through the phone's browser (no cable, no internet)."""
        from phone_receive_dialog import PhoneReceiveDialog
        dlg = PhoneReceiveDialog(self)
        dlg.exec()
        if dlg.imported:
            self.refresh()

    def _import(self):
        from pathlib import Path
        from cursiv_engine.core import fieldsync
        folder = QFileDialog.getExistingDirectory(self, "Import field logs from…")
        if folder:
            self._show_import(lambda: fieldsync.import_folder(Path(folder)))

    def _import_strict(self):
        """U105: refuse a notebook whose photos aren't all present and intact, so the import is complete."""
        from pathlib import Path
        from cursiv_engine.core import fieldsync
        folder = QFileDialog.getExistingDirectory(self, "Import field logs (every photo required) from…")
        if folder:
            self._show_import(lambda: fieldsync.import_folder(Path(folder), strict=True))

    def _show_import(self, run):
        from cursiv_engine.core import fieldsync
        try:
            text = fieldsync.report_text(run())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Not imported", str(exc))
            return
        problem = any(w in text for w in ("CONFLICT", "NOT IMPORTED", "CHECK"))
        self._status.setText(text.splitlines()[0])
        self._status.setStyleSheet(f"color: {theme.AMBER if problem else theme.GREEN};")
        (QMessageBox.warning if problem else QMessageBox.information)(
            self, "Team field logs", text + "\n\nFor the whole team: type 'team log' or 'team log export' in the chat.")

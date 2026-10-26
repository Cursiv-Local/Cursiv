"""
Make a Cursiv USB -- copies the program, the Ollama engine and the chosen AI
models onto a drive so Cursiv runs from it on any Windows PC with one
double-click and nothing installed (see portable.py for how the copy runs).

Private data (memories, keys, conversations, training data) is left OFF by
default, so a USB can be handed to someone else as a fresh Cursiv of their
own. Ticking "Include my memories, keys and settings" copies them too.

Re-running on the same drive only copies what changed, so updating a USB after
a Cursiv update is quick. "Check drive" reads the drive and reports what an update
would change without writing anything. Personal data is compared file by file
(usb_sync): newer drive data is kept, and a drive file is backed up before it is
replaced.
"""
from __future__ import annotations

import sys as _sys
from typing import cast as _cast
from usb_ops_runtime import UsbRuntime
import usb_ops as _usb_ops


def _runtime() -> UsbRuntime:
    """Explicit compatibility services: callables and per-turn records live here."""
    return _cast(UsbRuntime, _sys.modules[__name__])

import ctypes
import json
import os
import shutil
import string
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)
import usb_sync
from theme import BG, BG2, BORDER, GOLD, SILVER, SILV2, RED, GREEN  # one palette for every window (theme.py)


FAT32_MAX = 4 * 1024 ** 3 - 1
OLLAMA_API = "http://127.0.0.1:11434"

# Always on the USB so Cursiv runs offline anywhere: a qwen chat model (first
# one installed, else downloaded) and the memory-search embedding model.
REQUIRED_CHAT = ("qwen3:4b-instruct",)   # the tested model; Apache 2.0: fine to give away or sell (MODELS.md)
REQUIRED_EMBED = "nomic-embed-text:latest"
GB = 1024 ** 3

START_BAT = '@echo off\r\nstart "" "%~dp0Cursiv\\Cursiv.exe"\r\n'
README = """CURSIV ON A USB DRIVE: START HERE
===================================

TO START
  Double-click "Start Cursiv" (Start Cursiv.bat). That's all.
  Nothing is installed on the computer. Cursiv, its AI engine (Ollama) and the AI
  model can run from this drive. Cursiv's portable data and workspace stay on it.
  Windows and an existing host Ollama service may retain their own system traces.
  Works on Windows 10 and 11 (64-bit).

THE FIRST TIME
  1. Windows may ask whether to run it ("Windows protected your PC"): click
     More info, then Run anyway. Cursiv isn't code-signed yet.
  2. Create an account: a username, a password and security questions. They stay
     on this drive. Only someone signed in can add another account later.
  3. Cursiv opens. The badge at the top right says LOCAL ONLY when the internet is
     blocked (a "Field copy" drive starts that way; otherwise type: offline on).
     Just type a question.
  The first answer takes longer while the model loads from the drive.

WHAT TO TRY
  help                     what Cursiv can do
  demo                     the field notebook, documents and calculations with
                           sample data, kept apart from your own (demo off to end)
  Field Notebook           (sidebar) record observations; nothing is ever overwritten
  status                   what's on and off, and which AI model is answering

WHAT'S ON THIS DRIVE
  Start Cursiv.bat         starts Cursiv
  Cursiv\\                  the program
  Home\\                    everything Cursiv saves: accounts, memories, field
                           notebook, documents, settings (Home\\.cursiv)
  Workspace\\               authorized research and project files

  Updating the drive never overwrites newer data on it: for each file the newer
  copy is kept, and a drive file is backed up (Home\\.cursiv\\backups) before it is
  replaced. Keep a separate backup.
  Cursiv does not encrypt this drive. Anyone with access may read its files and
  copied credentials. Use drive encryption when appropriate. A lost or damaged
  drive is not recoverable without a separate backup. Close Cursiv before ejecting.
  Models\\                  the AI models
  Ollama\\                  the AI engine
  Licenses\\                licences for Cursiv, Ollama and each model; keep them
                           with the drive if you give or sell a copy

START OVER (REMOVE THE ACCOUNTS)
  In Cursiv: Settings > Your data & account > Accounts on this computer.
  "Remove an account..." removes one login (its username and your password).
  "Start over: remove all accounts" removes every login (your password); Cursiv
  closes and the next start asks you to create an account. Your notebook,
  memories and documents stay.
  Can't sign in at all: close Cursiv and delete the folder Home\\.cursiv\\runtime.
  To remove everything, delete Home\\.cursiv entirely.

IF SOMETHING ISN'T RIGHT
  - Cursiv is already open on this computer: close it first (one at a time).
  - The computer runs its own Ollama: Cursiv uses that one and its models. Quit
    Ollama from the tray on that computer to use this drive's models.
  - Slow: normal on computers without a graphics card (about 15 s an answer).
  - Settings > Help & diagnostics has a problem report.

UPDATING THIS DRIVE
  Update Cursiv on your computer, then open "Make a Cursiv USB..." and pick this
  drive. "Check drive" shows what is out of date without changing anything;
  "Update USB" copies only what changed. With "Include my memories..." ticked, your
  conversations, field notebook, memories and settings from that computer are
  brought up to date too; anything newer on this drive is kept.

TAKING YOUR WORK BACK TO A COMPUTER
  On a computer with Cursiv installed, open "Make a Cursiv USB...", pick this
  drive and click "Bring drive data here". Conversations, notebook entries,
  memories and settings that are new or newer on the drive are copied, then put
  in place the next time Cursiv starts. Anything newer on the computer is kept,
  and every replaced file is backed up first. Accounts and passwords stay as they
  are on each computer.

A TEAM WITH ONE MAIN COMPUTER
  Each person gets a drive made with their name ("Whose drive is this?" in Make
  a Cursiv USB). The drive's field notebook is theirs, on any computer they plug
  it into. Cursiv keeps a team copy of it at the top of the drive
  (cursiv-field-share), brought up to date when Cursiv starts and quits.
  On the main computer, plug the drives in one at a time and use Import from
  team... in the Field Notebook (or "Bring drive data here"): each person's
  entries and photos go into the team view in their name, never over the main
  computer's own notebook. A damaged copy is refused whole; importing again
  changes nothing. "team log" and "team log export" show everyone's work, with
  whose each entry and photo is. Nothing is encrypted per person: anyone signed
  in on the main computer can read the team's work.
  Making a drive, tick only the team notebooks that drive should carry.

More: https://cursiv.us  ·  Source: https://github.com/Cursiv-Local/Cursiv
"""


# ── Sources ──────────────────────────────────────────────────────────────────

def program_dir() -> Path | None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.program_dir(_runtime())



def models_dir() -> Path:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.models_dir(_runtime())



def ollama_dir() -> Path | None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.ollama_dir(_runtime())



def list_models() -> list[dict]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.list_models(_runtime())



# ── Licenses on the drive ────────────────────────────────────────────────────
# Every model's license travels with it: Ollama stores the text as a layer of
# the model ("application/vnd.ollama.image.license"). Cursiv's and Ollama's own
# licenses ship with Cursiv in cursiv_engine/licenses/.

_LICENSE_LAYER = "application/vnd.ollama.image.license"
_BUNDLED_LICENSES = Path(__file__).resolve().parent.parent / "cursiv_engine" / "licenses"
if getattr(sys, "frozen", False):
    _BUNDLED_LICENSES = Path(sys.executable).resolve().parent / "_internal" / "cursiv_engine" / "licenses"

_EXTRA_TERMS = {
    "llama": "Built with Llama. Meta's Acceptable Use Policy is at the end of the license file.",
    "gemma": ("Google's Gemma Prohibited Use Policy also applies: "
              "https://ai.google.dev/gemma/prohibited_use_policy"),
}


def model_license(model: dict) -> str:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.model_license(_runtime(), model)



def _safe_name(name: str) -> str:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops._safe_name(_runtime(), name)



def write_licenses(root: Path, models: list[dict]) -> list[str]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.write_licenses(_runtime(), root, models)



def required_names(models: list[dict]) -> list[str]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.required_names(_runtime(), models)



def pull_model(tag: str, sig, cancel: threading.Event) -> None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.pull_model(_runtime(), tag, sig, cancel)



# ── Drives ───────────────────────────────────────────────────────────────────

def _volume_info(root: str) -> tuple[str, str]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops._volume_info(_runtime(), root)



def list_drives() -> list[dict]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.list_drives(_runtime())



# ── Copy plan ────────────────────────────────────────────────────────────────

def _program_files(src: Path, include_private: bool) -> list[tuple[Path, Path]]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops._program_files(_runtime(), src, include_private)



def build_plan(models: list[dict], include_private: bool, ollama_src: Path | None) -> list[tuple[Path, Path]]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.build_plan(_runtime(), models, include_private, ollama_src)



MTIME_SLACK = 2.0      # seconds -- FAT-family drives store times in 2-second steps
PRIVATE_MARKER = Path("Home") / ".cursiv-private-copy"   # set when a private copy was made
PRUNED_DIRS = ("Cursiv", "Ollama")      # program files only; models and personal data are never pruned


def _needs_copy(src: Path, dest: Path) -> bool:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops._needs_copy(_runtime(), src, dest)



def _is_personal(rel: Path) -> bool:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops._is_personal(_runtime(), rel)



def stale_files(root: Path, plan: list[tuple[Path, Path]]) -> list[Path]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.stale_files(_runtime(), root, plan)



def verify_usb(plan: list[tuple[Path, Path]]) -> list[str]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.verify_usb(_runtime(), plan)



def copy_files(todo: list[tuple[Path, Path]], progress, cancel: threading.Event) -> None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.copy_files(_runtime(), todo, progress, cancel)



def _download_ollama(dest_dir: Path, progress, cancel: threading.Event) -> Path:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops._download_ollama(_runtime(), dest_dir, progress, cancel)



# ── Worker ───────────────────────────────────────────────────────────────────

class _Signals(QObject):
    progress = pyqtSignal(int, str)        # percent (-1 = busy), text
    done     = pyqtSignal(bool, str)
    planned  = pyqtSignal(object, str)     # drive -> computer plan (or None), message
    staged   = pyqtSignal(bool, str)


def make_usb(root: Path, models: list[dict], include_private: bool, sig: _Signals, cancel: threading.Event, field: bool=False,
             include_keys: bool=False, workspace_name: str = "", team_ids: list[str] | tuple = ()) -> None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.make_usb(_runtime(), root, models, include_private, sig, cancel, field, include_keys,
                             workspace_name, team_ids)



def _team_import(root: Path) -> str:
    """A team drive's notebook (U103): imported into the team view in that person's name, from the share
    Cursiv on the drive keeps at the drive's top. Checked like any team share; never copied over this
    computer's own notebook."""
    from cursiv_engine.core import fieldsync
    if not (root / fieldsync.SHARE_DIR).is_dir():
        return ("Field notebook: this drive's notebook belongs to someone else, but its team copy isn't on the "
                "drive yet. Start Cursiv from the drive once (or use Share with team… in its notebook), then "
                "bring the drive in again. Nothing from the notebook was copied.")
    try:
        return "Field notebook, added to the team view:\n" + fieldsync.report_text(fieldsync.import_folder(root))
    except (OSError, ValueError) as exc:
        return f"Field notebook: not imported ({exc}). Nothing from it was copied."


def check_usb(root: Path, models: list[dict], include_private: bool, include_keys: bool=False) -> tuple[bool, str]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.check_usb(_runtime(), root, models, include_private, include_keys)



def update_plan(root: Path, pairs: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.update_plan(_runtime(), root, pairs)



def tidy_root(root: Path) -> None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.tidy_root(_runtime(), root)



# ── Dialog ───────────────────────────────────────────────────────────────────

class UsbMakerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Make a Cursiv USB")
        self.setMinimumWidth(560)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel, QCheckBox {{ color: {SILVER}; background: transparent; }}
            QPushButton {{ background: #d4b04c; color: #17120a; border: none; border-radius: 4px;
                           padding: 6px 14px; font-weight: 600; }}
            QPushButton:disabled {{ background: #2a2a3f; color: #777; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
            QComboBox, QListWidget, QLineEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};
                                      border-radius: 4px; padding: 4px; }}
            QProgressBar {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 3px; color: {SILVER};
                            text-align: center; height: 16px; }}
            QProgressBar::chunk {{ background: #d4b04c; }}
        """)
        self._sig = _Signals()
        self._sig.progress.connect(self._on_progress)
        self._sig.done.connect(self._on_done)
        self._sig.planned.connect(self._on_planned)
        self._sig.staged.connect(self._on_staged)
        self._cancel = threading.Event()
        self._running = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(10)
        title = QLabel("Put Cursiv on a USB drive")
        title.setStyleSheet(f"color: {GOLD}; font-size: 16px; font-weight: 700;")
        lay.addWidget(title)
        sub = QLabel("The drive gets Cursiv, the Ollama AI engine, a qwen chat model and memory "
                     "search (always included), plus any other models you pick. Plug it into any "
                     "Windows PC and double-click \"Start Cursiv\" — nothing is installed, and it "
                     "works offline.")
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        lay.addWidget(sub)

        lay.addWidget(QLabel("Drive"))
        drow = QHBoxLayout()
        self._drive_box = QComboBox()
        drow.addWidget(self._drive_box, 1)
        refresh = QPushButton("Refresh")
        refresh.setObjectName("ghost")
        refresh.clicked.connect(self._load_drives)
        drow.addWidget(refresh)
        lay.addLayout(drow)

        lay.addWidget(QLabel("AI models to include"))
        self._model_list = QListWidget()
        self._model_list.setMinimumHeight(150)
        self._model_list.itemChanged.connect(self._update_total)
        self._drive_box.currentIndexChanged.connect(self._drive_changed)
        lay.addWidget(self._model_list)

        self._private = QCheckBox("Include my memories, conversations and settings (private — only for your own USB)")
        self._private.setToolTip("Your AI keys are not included unless you also tick the box below.")
        self._private.toggled.connect(self._update_total)
        lay.addWidget(self._private)
        self._keys = QCheckBox("Also copy my AI keys (readable on this drive: anyone with the drive can use them)")
        self._keys.setToolTip("Off by default. Keys are personal; leave this off for any drive you give to someone.")
        self._keys.setEnabled(False)
        self._private.toggled.connect(lambda on: (self._keys.setEnabled(on), on or self._keys.setChecked(False)))
        lay.addWidget(self._keys)

        self._field = QCheckBox("Field copy: starts in offline mode, no break reminders, no learned guesses")
        self._field.setToolTip("For research or field use. All three can be changed in Settings on the drive.")
        lay.addWidget(self._field)

        # Whose drive, and whose work it carries (U103)
        self._workspace = QLineEdit()
        self._workspace.setMaxLength(60)
        self._workspace.setPlaceholderText("Whose drive is this? (optional: their name)")
        self._workspace.setToolTip("The drive gets its own field notebook in this name. When it comes back, its work "
                                   "goes into this computer's team view under this name, never over this "
                                   "computer's notebook.")
        lay.addWidget(self._workspace)
        self._team_label = QLabel("Also put these notebooks on the drive (read only there):")
        lay.addWidget(self._team_label)
        self._team_list = QListWidget()
        self._team_list.setMaximumHeight(110)
        lay.addWidget(self._team_list)
        self._load_notebooks()

        self._total = QLabel("")
        self._total.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        self._total.setWordWrap(True)
        lay.addWidget(self._total)

        self._bar = QProgressBar()
        self._bar.setVisible(False)
        lay.addWidget(self._bar)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        lay.addWidget(self._status)

        brow = QHBoxLayout()
        brow.addStretch(1)
        self._check = QPushButton("Check drive")
        self._check.setObjectName("ghost")
        self._check.setToolTip("Read the drive and list what an update would change. Nothing is written.")
        self._check.clicked.connect(self._check_drive)
        brow.addWidget(self._check)
        self._bring = QPushButton("Bring drive data here")
        self._bring.setObjectName("ghost")
        self._bring.setToolTip("Copy conversations, notebook entries, memories and settings that are new or "
                               "newer on the drive into Cursiv on this computer. Anything newer here is kept.")
        self._bring.clicked.connect(self._bring_data)
        self._bring.setVisible(False)
        brow.addWidget(self._bring)
        self._go = QPushButton("Make USB")
        self._go.clicked.connect(self._start)
        brow.addWidget(self._go)
        self._stop = QPushButton("Stop")
        self._stop.setObjectName("ghost")
        self._stop.clicked.connect(self._cancel.set)
        self._stop.setVisible(False)
        brow.addWidget(self._stop)
        close = QPushButton("Close")
        close.setObjectName("ghost")
        close.clicked.connect(self.close)
        brow.addWidget(close)
        lay.addLayout(brow)

        self._models = list_models()
        self._required = required_names(self._models)
        have = {m["name"] for m in self._models}
        for name in self._required:
            if name not in have:
                item = QListWidgetItem(f"{name}   (required — downloaded first)")
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._model_list.addItem(item)
        for m in self._models:
            required = m["name"] in self._required
            item = QListWidgetItem(f"{m['name']}   ({m['size'] / GB:.1f} GB)" + ("   — required" if required else ""))
            item.setData(Qt.ItemDataRole.UserRole, m["name"])
            if required:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)      # always included, can't untick
            else:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)   # full experience by default
            self._model_list.addItem(item)
        self._load_drives()

    # ── helpers ──────────────────────────────────────────────────────────
    def _load_drives(self):
        self._drive_box.clear()
        for d in list_drives():
            kind = "USB / card" if d["removable"] else "external drive"
            name = d["label"] or "No name"
            self._drive_box.addItem(
                f"{d['letter']}:  {name}  —  {kind}, {d['fs'] or '?'}, "
                f"{d['free'] / GB:.0f} GB free of {d['total'] / GB:.0f} GB", d)
        if self._drive_box.count() == 0:
            self._drive_box.addItem("No USB drive found — plug one in and click Refresh", None)
        self._update_total()

    def _chosen_models(self) -> list[dict]:
        names = set(self._required)
        for i in range(self._model_list.count()):
            it = self._model_list.item(i)
            if it.flags() & Qt.ItemFlag.ItemIsUserCheckable and it.checkState() == Qt.CheckState.Checked:
                names.add(it.data(Qt.ItemDataRole.UserRole))
        return [m for m in self._models if m["name"] in names]

    def _update_total(self, *_):
        models = self._chosen_models()
        blobs = {b: b.stat().st_size for m in models for b in m["blobs"]}
        size = sum(blobs.values()) + 3.2 * GB          # + program and Ollama engine, roughly
        d = self._drive_box.currentData()
        txt = f"About {size / GB:.1f} GB to copy."
        if d:
            txt += f"  The drive has {d['free'] / GB:.0f} GB free."
            if d["fs"] == "FAT32" and any(s > FAT32_MAX for s in blobs.values()):
                txt += "  This drive is FAT32 and can't hold the larger models — reformat it as exFAT first."
        self._total.setText(txt)
        self._go.setEnabled(bool(d) and not self._running)
        self._check.setEnabled(bool(d) and not self._running)
        self._bring.setEnabled(bool(d) and not self._running)

    def _drive_changed(self, *_):
        """A drive that already has Cursiv is updated, not made again; one that
        holds a private copy keeps getting your data unless you untick it."""
        d = self._drive_box.currentData()
        root = Path(d["root"]) if d else None
        made = bool(root and (root / "Cursiv" / "portable.cursiv").exists())
        self._go.setText("Update USB" if made else "Make USB")
        # Only the installed app has a computer side to bring data to.
        self._bring.setVisible(bool(root and (root / "Home" / ".cursiv").is_dir())
                               and os.environ.get("CURSIV_PORTABLE") != "1")
        if root and (root / PRIVATE_MARKER).exists():
            self._private.setChecked(True)

    def _check_drive(self):
        d = self._drive_box.currentData()
        if not d or self._running:
            return
        self._running = True
        self._go.setEnabled(False)
        self._check.setEnabled(False)
        self._bar.setVisible(True)
        self._bar.setRange(0, 0)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        self._status.setText("Reading the drive…")
        root, models, private = Path(d["root"]), self._chosen_models(), self._private.isChecked()
        keys = private and self._keys.isChecked()

        def work():
            try:
                ok, report = check_usb(root, models, private, keys)
                self._sig.done.emit(True, report)
            except Exception as exc:
                self._sig.done.emit(False, f"Couldn't check the drive: {exc}")
        threading.Thread(target=work, daemon=True).start()

    def _busy(self, text: str):
        self._running = True
        for b in (self._go, self._check, self._bring):
            b.setEnabled(False)
        self._bar.setVisible(True)
        self._bar.setRange(0, 0)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        self._status.setText(text)

    def _bring_data(self):
        d = self._drive_box.currentData()
        if not d or self._running:
            return
        self._busy("Comparing the drive with this computer…")
        drive_data = Path(d["root"]) / "Home" / ".cursiv"

        def work():
            try:
                items = usb_sync.plan_import(drive_data, *usb_sync.import_targets())
                message = usb_sync.describe_import(items)
                if any(it["action"] == "team" for it in items):
                    message = _team_import(Path(d["root"])) + "\n\n" + message
                self._sig.planned.emit(items, message)
            except Exception as exc:
                self._sig.planned.emit(None, f"Couldn't compare the drive: {exc}")
        threading.Thread(target=work, daemon=True).start()

    def _on_planned(self, items, message: str):
        if items is None or not usb_sync.todo(items):
            self._on_done(items is not None, message if items is None else message + " Nothing to bring.")
            return
        ok = QMessageBox.question(
            self, "Bring drive data to this computer",
            f"{message}\n\nThese files are copied to this computer now and put in place the next time "
            "Cursiv starts, before it reads anything. Each file this computer already has is backed up "
            "first. Accounts and passwords are not changed. Saved keys are encrypted for this Windows "
            "account.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ok != QMessageBox.StandardButton.Yes:
            self._on_done(True, "Nothing was copied.")
            return
        self._cancel.clear()
        self._stop.setVisible(True)

        def work():
            try:
                usb_sync.stage_import(items, self._sig.progress.emit, self._cancel)
                self._sig.staged.emit(True, f"Copied {len(usb_sync.todo(items))} file(s) from the drive. "
                                            "They go into place the next time Cursiv starts.")
            except InterruptedError:
                self._sig.staged.emit(False, "Stopped. Nothing on this computer was changed.")
            except Exception as exc:
                self._sig.staged.emit(False, f"Couldn't copy from the drive: {exc}. Nothing on this computer was changed.")
        threading.Thread(target=work, daemon=True).start()

    def _on_staged(self, ok: bool, message: str):
        self._on_done(ok, message)
        if not ok:
            return
        again = QMessageBox.question(
            self, "Finish bringing your data in",
            message + "\n\nClose Cursiv now? Open it again to finish; you can unplug the drive first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if again == QMessageBox.StandardButton.Yes:
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()

    # ── run ──────────────────────────────────────────────────────────────
    def _start(self):
        d = self._drive_box.currentData()
        if not d:
            return
        if not self._private.isChecked() and (Path(d["root"]) / PRIVATE_MARKER).exists():
            ok = QMessageBox.question(
                self, "Private data on this drive",
                "This drive has a private copy of your memories and settings from an earlier "
                "time. It may also contain readable AI keys that anyone with the drive can use. "
                "Updating preserves that data; this is not a way to reset a drive "
                "for another person.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
        if self._private.isChecked():
            keys = self._keys.isChecked()
            ok = QMessageBox.question(
                self, "Private data",
                "Your memories, conversations and settings will be copied onto the drive. Anyone with "
                "the drive can read them. " +
                ("Your AI keys will be copied too, readable, so anyone with the drive can use them. "
                 if keys else "Your AI keys will not be copied. ") + "\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
        missing = [tag for tag in required_names(list_models()) if tag not in {m['name'] for m in list_models()}]
        if missing or ollama_dir() is None:
            ok = QMessageBox.question(self, 'Downloads required',
                'Making this USB requires downloading missing models or the Ollama runtime. '
                'This may use several GB of internet data. Download and continue?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
        self._running = True
        self._cancel.clear()
        self._go.setEnabled(False)
        self._check.setEnabled(False)
        self._stop.setVisible(True)
        self._bar.setVisible(True)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        threading.Thread(target=make_usb,
                         args=(Path(d["root"]), self._chosen_models(), self._private.isChecked(),
                               self._sig, self._cancel, self._field.isChecked(),
                               self._private.isChecked() and self._keys.isChecked(),
                               self._workspace.text().strip(), self._chosen_notebooks()),
                         daemon=True).start()

    def _load_notebooks(self):
        """This computer's notebook and the team notebooks imported here, none ticked: only the work someone
        chooses goes onto a drive."""
        self._team_list.clear()
        try:
            from cursiv_engine.core import fieldsync
            books = fieldsync.notebooks_here()
        except (OSError, ValueError):
            books = []
        for b in books:
            label = (b["name"] or b["id"]) + (" (this computer)" if b["own"] else "") + f" · {b['entries']} entries"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, b["id"])
            self._team_list.addItem(item)
        self._team_label.setVisible(bool(books))
        self._team_list.setVisible(bool(books))

    def _chosen_notebooks(self) -> list[str]:
        return [self._team_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._team_list.count())
                if self._team_list.item(i).checkState() == Qt.CheckState.Checked]

    def _on_progress(self, pct: int, text: str):
        if pct < 0:
            self._bar.setRange(0, 0)
        else:
            self._bar.setRange(0, 100)
            self._bar.setValue(pct)
        self._status.setText(text)

    def _on_done(self, ok: bool, message: str):
        self._running = False
        self._bar.setVisible(False)
        self._stop.setVisible(False)
        self._status.setText(message)
        self._status.setStyleSheet(f"color: {GREEN if ok else RED}; font-size: 12px;")
        self._load_drives()

    def closeEvent(self, e):
        if self._running:
            self._cancel.set()
        super().closeEvent(e)

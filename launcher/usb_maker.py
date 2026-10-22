"""
Make a Cursiv USB -- copies the program, the Ollama engine and the chosen AI
models onto a drive so Cursiv runs from it on any Windows PC with one
double-click and nothing installed (see portable.py for how the copy runs).

Private data (memories, keys, conversations, training data) is left OFF by
default, so a USB can be handed to someone else as a fresh Cursiv of their
own. Ticking "Include my memories, keys and settings" copies them too.

Re-running on the same drive only copies what changed (same size = skip),
so updating a USB after a Cursiv update is quick.
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
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)
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

  Updates preserve existing personal data. Legacy data conflicts stop startup
  after verified backups; they are never silently merged. Keep a separate backup.
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
  Update Cursiv on your computer, then use "Make a Cursiv USB..." again on the same
  drive. Only changed files are copied.

More: https://cursiv.winklers-llc.com  ·  Source: https://github.com/winklersllc2026-bit/Cursiv
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
# licenses ship with Cursiv in cursiv_v215/licenses/.

_LICENSE_LAYER = "application/vnd.ollama.image.license"
_BUNDLED_LICENSES = Path(__file__).resolve().parent.parent / "cursiv_v215" / "licenses"
if getattr(sys, "frozen", False):
    _BUNDLED_LICENSES = Path(sys.executable).resolve().parent / "_internal" / "cursiv_v215" / "licenses"

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



def wipe_private_copy(root: Path) -> bool:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.wipe_private_copy(_runtime(), root)



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


def make_usb(root: Path, models: list[dict], include_private: bool, sig: _Signals, cancel: threading.Event, field: bool=False) -> None:
    """Compatibility entry point; implementation in chat.usb_ops."""
    return _usb_ops.make_usb(_runtime(), root, models, include_private, sig, cancel, field)



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
            QComboBox, QListWidget {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};
                                      border-radius: 4px; padding: 4px; }}
            QProgressBar {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 3px; color: {SILVER};
                            text-align: center; height: 16px; }}
            QProgressBar::chunk {{ background: #d4b04c; }}
        """)
        self._sig = _Signals()
        self._sig.progress.connect(self._on_progress)
        self._sig.done.connect(self._on_done)
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
        lay.addWidget(self._model_list)

        self._private = QCheckBox("Include my memories, keys and settings (private — only for your own USB)")
        self._private.setToolTip('Copied API keys are exported in readable form for use on other computers. '
                                 'Anyone with the drive can read and use those keys.')
        self._private.toggled.connect(self._update_total)
        lay.addWidget(self._private)

        self._field = QCheckBox("Field copy: starts in offline mode, no break reminders, no learned guesses")
        self._field.setToolTip("For research or field use. All three can be changed in Settings on the drive.")
        lay.addWidget(self._field)

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

    # ── run ──────────────────────────────────────────────────────────────
    def _start(self):
        d = self._drive_box.currentData()
        if not d:
            return
        if not self._private.isChecked() and (Path(d["root"]) / PRIVATE_MARKER).exists():
            ok = QMessageBox.question(
                self, "Private data on this drive",
                "This drive has a private copy of your memories, keys and settings from an "
                "earlier time. It may contain readable API keys that anyone with the drive can use. "
                "Updating preserves that data; this is not a way to reset a drive "
                "for another person.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
        if self._private.isChecked():
            ok = QMessageBox.question(
                self, "Private data",
                "Your memories, keys and conversations will be copied onto the drive. Copied API keys "
                "are exported in readable form for use on other computers. Anyone with the drive can "
                "read and use those keys and read the copied personal data.\n\nContinue?",
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
        self._stop.setVisible(True)
        self._bar.setVisible(True)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        threading.Thread(target=make_usb,
                         args=(Path(d["root"]), self._chosen_models(), self._private.isChecked(),
                               self._sig, self._cancel, self._field.isChecked()),
                         daemon=True).start()

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

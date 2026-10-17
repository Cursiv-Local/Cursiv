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

BG, BG2, BORDER = "#0b0b12", "#13131e", "#2a2a3f"
GOLD, SILVER, SILV2 = "#FFD700", "#C8C8D4", "#666680"
GREEN, RED = "#3ecf6e", "#FF4455"

FAT32_MAX = 4 * 1024 ** 3 - 1
OLLAMA_API = "http://127.0.0.1:11434"

# Always on the USB so Cursiv runs offline anywhere: a qwen chat model (first
# one installed, else downloaded) and the memory-search embedding model.
REQUIRED_CHAT = ("qwen3:4b", "qwen2.5:1.5b")   # Apache 2.0: fine to give away or sell (MODELS.md)
REQUIRED_EMBED = "nomic-embed-text:latest"
GB = 1024 ** 3

START_BAT = '@echo off\r\nstart "" "%~dp0Cursiv\\Cursiv.exe"\r\n'
README = """Cursiv on a USB
================

To start: double-click "Start Cursiv".

Nothing gets installed on the computer. Cursiv, its AI engine (Ollama) and
the AI models all run from this drive, and everything Cursiv saves stays on
this drive (in the Home folder).

Works on Windows 10 and 11 (64-bit). Answers are slower than from an internal
drive while a model first loads.

If Cursiv is already installed and open on the computer, close it first --
only one Cursiv runs at a time.

If the computer already runs its own Ollama, Cursiv uses that one and its
models instead of the ones on this drive. Quit Ollama from the tray on that
computer to use this drive's models.

To update this USB: update Cursiv on your computer, then use
"Make a Cursiv USB..." again on the same drive. Only changed files are copied.

Licenses: Cursiv and Ollama are MIT-licensed. Each AI model in the Models
folder has its own license (qwen3 and qwen2.5:1.5b: Apache 2.0; llama models:
Llama Community License, "Built with Llama"; gemma: Gemma Terms of Use). See
MODELS.md at https://github.com/winklersllc2026-bit/Cursiv before giving away
or selling a drive.
"""


# ── Sources ──────────────────────────────────────────────────────────────────

def program_dir() -> Path | None:
    """The built Cursiv folder to copy (the running app, or dist\\Cursiv in a dev checkout)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    dev = Path(__file__).resolve().parent.parent / "dist" / "Cursiv"
    return dev if (dev / "Cursiv.exe").exists() else None


def models_dir() -> Path:
    return Path(os.environ.get("OLLAMA_MODELS") or (Path.home() / ".ollama" / "models"))


def ollama_dir() -> Path | None:
    exe = shutil.which("ollama")
    if exe:
        return Path(exe).resolve().parent
    d = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
    return d if (d / "ollama.exe").exists() else None


def list_models() -> list[dict]:
    """Every pulled Ollama model: name, manifest path, blob files and total size."""
    base = models_dir()
    mroot = base / "manifests"
    out = []
    if not mroot.is_dir():
        return out
    for mf in mroot.rglob("*"):
        if not mf.is_file():
            continue
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except Exception:
            continue
        digests = [l.get("digest", "") for l in data.get("layers", [])]
        digests.append((data.get("config") or {}).get("digest", ""))
        blobs = [base / "blobs" / d.replace(":", "-") for d in digests if d]
        blobs = [b for b in blobs if b.exists()]
        parts = mf.relative_to(mroot).parts          # registry / namespace / name / tag
        name = f"{parts[-2]}:{parts[-1]}" if len(parts) >= 2 else mf.name
        if len(parts) >= 3 and parts[-3] != "library":
            name = f"{parts[-3]}/{name}"
        out.append({"name": name, "manifest": mf, "blobs": blobs,
                    "size": sum(b.stat().st_size for b in blobs)})
    return sorted(out, key=lambda m: m["name"])


def required_names(models: list[dict]) -> list[str]:
    names = {m["name"] for m in models}
    chat = next((n for n in REQUIRED_CHAT if n in names), REQUIRED_CHAT[0])
    return [chat, REQUIRED_EMBED]


def pull_model(tag: str, sig, cancel: threading.Event) -> None:
    """Download a model into this computer's Ollama so it can be copied."""
    from cursiv_v215.core import netgate
    netgate.require(f"Downloading {tag}")
    req = urllib.request.Request(f"{OLLAMA_API}/api/pull",
                                 data=json.dumps({"name": tag, "stream": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=3600)
    except Exception:
        raise RuntimeError(f"{tag} isn't downloaded yet and Ollama isn't running to fetch it. "
                           "Open Setup, start Ollama, then try again.")
    with r:
        for line in r:
            if cancel.is_set():
                raise InterruptedError
            try:
                st = json.loads(line.decode())
            except Exception:
                continue
            if st.get("error"):
                raise RuntimeError(f"Downloading {tag} failed: {st['error']}")
            total, done = st.get("total") or 0, st.get("completed") or 0
            if total and done:
                sig.progress.emit(int(done * 100 / total),
                                  f"Downloading {tag} first… {done / 1e9:.2f} of {total / 1e9:.2f} GB")
            if st.get("status") == "success":
                return
    raise RuntimeError(f"Downloading {tag} ended early — try again.")


# ── Drives ───────────────────────────────────────────────────────────────────

def _volume_info(root: str) -> tuple[str, str]:
    label = ctypes.create_unicode_buffer(261)
    fs = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root), label, 261, None, None, None, fs, 261)
    return (label.value, fs.value) if ok else ("", "")


def list_drives() -> list[dict]:
    """Removable drives plus external fixed drives (USB SSDs report as fixed).
    Never the Windows drive."""
    drives = []
    if sys.platform != "win32":
        return drives
    system = os.environ.get("SystemDrive", "C:").upper()[:1]
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if not mask & (1 << i) or letter == system:
            continue
        root = f"{letter}:\\"
        kind = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
        if kind not in (2, 3):                 # 2 = removable, 3 = fixed
            continue
        try:
            usage = shutil.disk_usage(root)
        except Exception:
            continue                           # empty card reader etc.
        label, fs = _volume_info(root)
        drives.append({"root": root, "letter": letter, "label": label, "fs": fs.upper(),
                       "removable": kind == 2, "free": usage.free, "total": usage.total})
    return drives


# ── Copy plan ────────────────────────────────────────────────────────────────

def _program_files(src: Path, include_private: bool) -> list[tuple[Path, Path]]:
    skip_top = {"unins000.dat", "unins000.exe"}
    pairs = []
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        top = rel.parts[0]
        if top in skip_top or ".bak" in top:   # installer leftovers, old-version backups
            continue
        if ".cursiv" in rel.parts and not include_private:
            continue                           # memories, keys, training data
        pairs.append((f, Path("Cursiv") / rel))
    return pairs


def build_plan(models: list[dict], include_private: bool, ollama_src: Path | None) -> list[tuple[Path, Path]]:
    prog = program_dir()
    if prog is None:
        raise RuntimeError("Couldn't find the Cursiv program files to copy.")
    pairs = _program_files(prog, include_private)
    if ollama_src:
        for f in ollama_src.rglob("*"):
            if f.is_file() and not f.name.lower().startswith("unins"):
                pairs.append((f, Path("Ollama") / f.relative_to(ollama_src)))
    mbase = models_dir()
    seen = set()
    for m in models:
        for f in [m["manifest"], *m["blobs"]]:
            if f not in seen:
                seen.add(f)
                pairs.append((f, Path("Models") / f.relative_to(mbase)))
    if include_private:
        home_data = Path.home() / ".cursiv"
        if home_data.is_dir():
            for f in home_data.rglob("*"):
                if f.is_file():
                    pairs.append((f, Path("Home") / ".cursiv" / f.relative_to(home_data)))
    return pairs


MTIME_SLACK = 2.0      # seconds -- FAT-family drives store times in 2-second steps
PRIVATE_MARKER = Path("Home") / ".cursiv-private-copy"   # set when a private copy was made
PRUNED_DIRS = ("Cursiv", "Ollama")      # program files only; models and personal data are never pruned


def _needs_copy(src: Path, dest: Path) -> bool:
    """Copy unless the drive already has this exact file (same size and time --
    copies keep the source's modified time, so a rebuilt file of the same size
    still differs)."""
    try:
        s, d = src.stat(), dest.stat()
    except Exception:
        return True
    return s.st_size != d.st_size or abs(s.st_mtime - d.st_mtime) > MTIME_SLACK


def _is_personal(rel: Path) -> bool:
    return ".cursiv" in rel.parts or rel.name == "portable.cursiv"


def stale_files(root: Path, plan: list[tuple[Path, Path]]) -> list[Path]:
    """Files in the drive's program folders that the current build doesn't have
    (e.g. a library a newer Cursiv dropped). Never personal data."""
    wanted = {d.resolve() for _s, d in plan}
    out = []
    for top in PRUNED_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.is_file() and f.resolve() not in wanted and not _is_personal(f.relative_to(root)):
                out.append(f)
    return out


def verify_usb(plan: list[tuple[Path, Path]]) -> list[str]:
    """Every planned file is on the drive with the right size and time.
    Returns the problems (empty list = the drive matches the build)."""
    problems = []
    for src, dest in plan:
        if not dest.exists():
            problems.append(f"missing: {dest}")
        elif _needs_copy(src, dest):
            problems.append(f"different: {dest}")
    return problems


def wipe_private_copy(root: Path) -> bool:
    """Remove personal data that an earlier private copy put on the drive.
    Only acts when the marker says a private copy was made -- data the drive's
    own user created later on a fresh copy is left alone."""
    if not (root / PRIVATE_MARKER).exists():
        return False
    shutil.rmtree(root / "Home" / ".cursiv", ignore_errors=True)
    prog = root / "Cursiv"
    if prog.is_dir():
        for d in sorted(prog.rglob(".cursiv"), key=lambda p: len(p.parts), reverse=True):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
    (root / PRIVATE_MARKER).unlink(missing_ok=True)
    return True


def copy_files(todo: list[tuple[Path, Path]], progress, cancel: threading.Event) -> None:
    """Copy each file to a .part file, flush it to disk, then rename it into
    place -- an interrupted copy never leaves a half-written file behind."""
    total = sum(s.stat().st_size for s, _ in todo) or 1
    copied = 0
    for i, (src, dest) in enumerate(todo, 1):
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        with open(src, "rb") as fi, open(part, "wb") as fo:
            while chunk := fi.read(8 << 20):
                if cancel.is_set():
                    fo.close()
                    part.unlink(missing_ok=True)
                    raise InterruptedError
                fo.write(chunk)
                copied += len(chunk)
                progress(int(copied * 100 / total),
                         f"Copying {i} of {len(todo)} files — {copied / GB:.1f} of {total / GB:.1f} GB")
            fo.flush()
            os.fsync(fo.fileno())
        os.replace(part, dest)
        shutil.copystat(src, dest, follow_symlinks=True)


def _download_ollama(dest_dir: Path, progress, cancel: threading.Event) -> Path:
    """Download Ollama's Windows zip from its latest GitHub release and check it
    against the SHA-256 GitHub publishes for that file. Returns the unpacked folder."""
    import hashlib
    api = urllib.request.Request("https://api.github.com/repos/ollama/ollama/releases/latest",
                                 headers={"User-Agent": "Cursiv-USB"})
    with urllib.request.urlopen(api, timeout=30) as r:
        release = json.loads(r.read())
    asset = next((a for a in release.get("assets", []) if a.get("name") == "ollama-windows-amd64.zip"), None)
    digest = (asset or {}).get("digest", "")
    if not asset or not digest.startswith("sha256:"):
        raise RuntimeError("Couldn't find a checksum for the Ollama download, so it wasn't used. "
                           "Install Ollama on this computer (Setup window) and try again.")
    zpath = dest_dir / "ollama.zip"
    sha = hashlib.sha256()
    req = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "Cursiv-USB"})
    with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while chunk := r.read(1 << 20):
            if cancel.is_set():
                raise InterruptedError
            out.write(chunk)
            sha.update(chunk)
            got += len(chunk)
            progress(int(got * 100 / total) if total else -1,
                     f"Downloading Ollama… {got >> 20} MB" + (f" of {total >> 20} MB" if total else ""))
    if "sha256:" + sha.hexdigest() != digest:
        zpath.unlink(missing_ok=True)
        raise RuntimeError("The Ollama download didn't match its published checksum, so it wasn't used. Try again.")
    out_dir = dest_dir / "ollama"
    with zipfile.ZipFile(zpath) as z:
        z.extractall(out_dir)
    return out_dir


# ── Worker ───────────────────────────────────────────────────────────────────

class _Signals(QObject):
    progress = pyqtSignal(int, str)        # percent (-1 = busy), text
    done     = pyqtSignal(bool, str)


def make_usb(root: Path, models: list[dict], include_private: bool,
             sig: _Signals, cancel: threading.Event) -> None:
    try:
        have = {m["name"] for m in list_models()}
        for tag in required_names(list_models()):
            if tag not in have:
                pull_model(tag, sig, cancel)
        chosen = {m["name"] for m in models} | set(required_names(list_models()))
        models = [m for m in list_models() if m["name"] in chosen]

        osrc = ollama_dir()
        tmp_zip_dir = None
        if osrc is None:
            sig.progress.emit(-1, "Downloading the Ollama engine (about 1-2 GB)…")
            tmp_zip_dir = Path(tempfile.mkdtemp(prefix="cursiv_ollama_"))
            osrc = _download_ollama(tmp_zip_dir, sig.progress.emit, cancel)

        # Fresh copy on a drive that once held a private one: remove that first.
        wiped = False if include_private else wipe_private_copy(root)

        plan = [(s, root / d) for s, d in build_plan(models, include_private, osrc)]
        todo = [(s, d) for s, d in plan if _needs_copy(s, d)]
        total = sum(s.stat().st_size for s, _ in todo) or 1

        _, fs = _volume_info(str(root))
        if fs.upper() == "FAT32" and any(s.stat().st_size > FAT32_MAX for s, _ in todo):
            raise RuntimeError("This drive is formatted FAT32, which can't hold files over 4 GB "
                               "(some AI models are bigger). Reformat it as exFAT and try again.")
        free = shutil.disk_usage(str(root)).free
        if total > free:
            raise RuntimeError(f"Not enough space: needs {total / GB:.1f} GB, the drive has "
                               f"{free / GB:.1f} GB free. Untick some models and try again.")

        copy_files(todo, sig.progress.emit, cancel)
        for f in stale_files(root, plan):
            f.unlink(missing_ok=True)
        for leftover in root.rglob("*.part"):
            leftover.unlink(missing_ok=True)
        if include_private:
            (root / PRIVATE_MARKER).parent.mkdir(parents=True, exist_ok=True)
            (root / PRIVATE_MARKER).write_text(
                "This drive holds a private copy of someone's Cursiv data. Making a fresh "
                "copy on it removes that data.\n", encoding="utf-8")

        sig.progress.emit(-1, "Checking the drive matches…")
        problems = verify_usb(plan)
        if problems:
            raise RuntimeError(f"{len(problems)} file(s) didn't copy correctly (first: {problems[0]}). "
                               "Click Make USB again to fix them.")

        if include_private:
            # Saved keys are encrypted for this Windows account; the USB runs on
            # other PCs, so its copy holds them readable (the note below says so).
            from cursiv_v215.core import keystore
            for cfg_file in (root / "Cursiv").rglob("config.json"):
                if cfg_file.parent.name == ".cursiv":
                    keystore.export_readable(cfg_file)

        (root / "Cursiv" / "portable.cursiv").write_text(
            "This copy of Cursiv runs from this drive. See README.txt.\n", encoding="utf-8")
        (root / "Home").mkdir(exist_ok=True)
        (root / "Start Cursiv.bat").write_bytes(START_BAT.encode("ascii"))
        (root / "README.txt").write_text(README, encoding="utf-8")
        ico = next((root / "Cursiv").rglob("cursiv.ico"), None)
        if ico:
            try:
                shutil.copy2(ico, root / "cursiv.ico")
                (root / "autorun.inf").write_text("[autorun]\r\nlabel=Cursiv\r\nicon=cursiv.ico\r\n", encoding="utf-8")
            except Exception:
                pass
        if tmp_zip_dir:
            shutil.rmtree(tmp_zip_dir, ignore_errors=True)
        note = (" Your memories, keys and settings are on it — keep it safe."
                if include_private else " It starts fresh, so it can be given to someone else.")
        if wiped:
            note += " The private data from the earlier copy was removed from the drive."
        sig.done.emit(True, f"Done. Plug the drive into any Windows PC and double-click "
                            f"\"Start Cursiv\".{note}")
    except InterruptedError:
        sig.done.emit(False, "Stopped. Click Make USB again to pick up where it left off.")
    except Exception as exc:
        sig.done.emit(False, f"Couldn't finish: {exc}")


# ── Dialog ───────────────────────────────────────────────────────────────────

class UsbMakerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cursiv — Make a Cursiv USB")
        self.setMinimumWidth(560)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; color: {SILVER}; }}
            QLabel, QCheckBox {{ color: {SILVER}; background: transparent; }}
            QPushButton {{ background: #2255DD; color: #fff; border: none; border-radius: 4px;
                           padding: 6px 14px; font-weight: 600; }}
            QPushButton:disabled {{ background: #2a2a3f; color: #777; }}
            QPushButton#ghost {{ background: transparent; color: {SILVER}; border: 1px solid {BORDER}; font-weight: 400; }}
            QComboBox, QListWidget {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER};
                                      border-radius: 4px; padding: 4px; }}
            QProgressBar {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 3px; color: {SILVER};
                            text-align: center; height: 16px; }}
            QProgressBar::chunk {{ background: #2255DD; }}
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
        self._private.toggled.connect(self._update_total)
        lay.addWidget(self._private)

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
                "earlier time. Making a fresh copy removes them from the drive (they stay on "
                "this computer).\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ok != QMessageBox.StandardButton.Yes:
                return
        if self._private.isChecked():
            ok = QMessageBox.question(
                self, "Private data",
                "Your memories, keys and conversations will be copied onto the drive. Anyone who "
                "has the drive can read them.\n\nContinue?",
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
                               self._sig, self._cancel),
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

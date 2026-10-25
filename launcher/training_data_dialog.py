"""
Cursiv — Training Data dialog.

A storage box for cursiv_engine/training/paths.py's TRAINING_JSONL -- the
file LoRA training reads from. This dialog gives three ways to add to it:

  - Upload an image: run vision analysis on it and store the description
    as a {prompt, response} example.
  - Paste JSON directly: for anyone who already has a training example
    in hand and just wants it in the store.
  - (Typed notes -> JSON happens in the chat itself -- see
    chat_commands.py's _looks_like_text_to_json_request -- not here.)

Every entry, however it arrived, can be viewed, copied, or deleted from
the same list.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDialog, QLabel, QPushButton,
    QPlainTextEdit, QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QSizePolicy, QInputDialog,
)

import chat_commands as cc
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2  # one palette for every window (theme.py)

_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"


class _UploadSignals(QObject):
    done = pyqtSignal(bool, str)   # (ok, message)


class TrainingDataDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._entries: list[dict] = []
        self._upload_signals = _UploadSignals()
        self._upload_signals.done.connect(self._on_upload_done)

        self.setWindowTitle("Cursiv — Training Data")
        self.setMinimumSize(640, 620)
        self.setStyleSheet(f"QDialog {{ background: {BG}; }} QLabel {{ color: {SILVER}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        header = QLabel("Training data")
        header.setStyleSheet(f'color: {GOLD}; font-size: 18px; font-weight: 700; font-family: "Segoe UI", "Segoe UI Historic";')
        lay.addWidget(header)
        lay.addWidget(self._note_label(
            "These are the examples LoRA training learns from. Add them here, or "
            "convert notes in chat: try \"translate my notes into JSON for "
            "training\"."
        ))

        self._count_label = self._section_label("")
        lay.addWidget(self._count_label)

        self._list = QListWidget()
        self._style_list(self._list)
        self._list.setMaximumHeight(160)
        self._list.currentRowChanged.connect(self._on_select)
        lay.addWidget(self._list)

        self._detail = QPlainTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setPlaceholderText("Select an entry above to view its JSON.")
        self._style_box(self._detail)
        self._detail.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self._detail, 1)

        row = QHBoxLayout()
        copy_btn = QPushButton("Copy Selected")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(self._btn_style())
        copy_btn.clicked.connect(self._copy_selected)
        row.addWidget(copy_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet(self._btn_style())
        delete_btn.clicked.connect(self._delete_selected)
        row.addWidget(delete_btn)

        self._upload_btn = QPushButton("Upload Image…")
        self._upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._upload_btn.setStyleSheet(self._btn_style(primary=True))
        self._upload_btn.clicked.connect(self._upload_image)
        row.addWidget(self._upload_btn)
        lay.addLayout(row)

        lay.addWidget(self._section_label("ADD JSON MANUALLY"))
        self._paste_box = QPlainTextEdit()
        self._paste_box.setPlaceholderText('{"prompt": "...", "response": "..."}')
        self._style_box(self._paste_box)
        self._paste_box.setFixedHeight(90)
        lay.addWidget(self._paste_box)

        add_btn = QPushButton("Add to Training Data")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(self._btn_style(primary=True))
        add_btn.clicked.connect(self._add_pasted)
        lay.addWidget(add_btn)

        lay.addWidget(self._section_label("TRAIN"))
        lay.addWidget(self._note_label(
            "Fine-tunes a small local model (Qwen2.5-1.5B) on everything stored above. "
            "Needs real disk space and RAM to run -- checked before anything starts."
        ))
        self._train_btn = QPushButton("Start LoRA Training…")
        self._train_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._train_btn.setStyleSheet(self._btn_style())
        self._train_btn.clicked.connect(self._start_lora_training)
        lay.addWidget(self._train_btn)

        self._merge_btn = QPushButton("Merge Latest Adapter into Ollama…")
        self._merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._merge_btn.setStyleSheet(self._btn_style())
        self._merge_btn.setToolTip(
            "Converts the most recently trained adapter to GGUF and layers it "
            "onto Ollama's qwen2.5:1.5b as a new chattable model."
        )
        self._merge_btn.clicked.connect(self._merge_into_ollama)
        lay.addWidget(self._merge_btn)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"color: {SILV2}; font-size: 11px;")
        lay.addWidget(self._status)

        self._refresh()

    # ── Styling helpers ──────────────────────

    def _note_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {SILV2}; font-size: 12px;")
        return lbl

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {LGOLD}; font-size: 10px; font-weight: 700; letter-spacing: 1px; margin-top: 6px;")
        return lbl

    def _style_list(self, lst: QListWidget) -> None:
        lst.setStyleSheet(
            f"QListWidget {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; font-size: 12px; }}"
            f"QListWidget::item {{ padding: 6px; }}"
            f"QListWidget::item:selected {{ background: rgba(212,175,55,0.15); color: {GOLD}; }}"
        )

    def _style_box(self, box: QPlainTextEdit) -> None:
        box.setStyleSheet(
            f"QPlainTextEdit {{ background: {BG2}; color: {SILVER}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 8px; font-size: 12px; font-family: Consolas, monospace; }}"
            f"QPlainTextEdit:focus {{ border-color: {LGOLD}; }}"
        )

    def _btn_style(self, primary: bool = False) -> str:
        if primary:
            return (
                "QPushButton { background: #d4b04c; color: #17120a; font-weight: 600; border: none; border-radius: 6px; padding: 8px; }"
                "QPushButton:hover { background: #e2c062; }"
                "QPushButton:disabled { background: #444; color: #999; }"
            )
        return (
            f"QPushButton {{ background: transparent; color: {GOLD}; border: 1px solid {LGOLD}; "
            f"border-radius: 6px; padding: 8px; }}"
            f"QPushButton:hover {{ background: rgba(212,175,55,0.08); }}"
        )

    # ── Data ─────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._entries = cc.list_training_entries()
        self._list.clear()
        for e in self._entries:
            preview = str(e.get("prompt", "") or e.get("response", ""))[:60]
            source = e.get("source", "unknown")
            ts = str(e.get("timestamp", ""))[:19]
            self._list.addItem(QListWidgetItem(f"[{source}]  {preview}  ·  {ts}"))
        self._count_label.setText(f"{len(self._entries)} EXAMPLE{'S' if len(self._entries) != 1 else ''} STORED")
        self._detail.clear()

    def _on_select(self, row: int) -> None:
        if row < 0 or row >= len(self._entries):
            self._detail.clear()
            return
        entry = {k: v for k, v in self._entries[row].items() if k != "_line"}
        self._detail.setPlainText(json.dumps(entry, indent=2, ensure_ascii=False))

    def _copy_selected(self) -> None:
        text = self._detail.toPlainText()
        if not text.strip():
            self._status.setText("Select an entry first.")
            return
        QGuiApplication.clipboard().setText(text)
        self._status.setText("Copied to clipboard.")

    def _delete_selected(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._entries):
            self._status.setText("Select an entry first.")
            return
        entry = self._entries[row]
        preview = str(entry.get("prompt", "") or entry.get("response", ""))[:60]
        if QMessageBox.question(
            self, "Delete Example",
            f"Delete this training example?\n\n{preview}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        ok, msg = cc.delete_training_entry(entry["_line"])
        self._status.setText(msg)
        self._refresh()

    def _add_pasted(self) -> None:
        raw = self._paste_box.toPlainText()
        ok, msg = cc.add_training_entry_json(raw)
        self._status.setText(msg)
        if ok:
            self._paste_box.clear()
            self._refresh()

    def _upload_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Upload Image for Training", "", _IMAGE_FILTER)
        if not path:
            return
        self._upload_btn.setEnabled(False)
        self._status.setText("Analyzing image…")
        threading.Thread(target=self._run_upload, args=(path,), daemon=True).start()

    def _run_upload(self, path: str) -> None:
        try:
            data = Path(path).read_bytes()
            ext = Path(path).suffix.lstrip(".").lower() or "png"
            ok, msg, _entry = cc.image_to_training_entry(data, self._cfg, ext=ext)
        except Exception as e:
            ok, msg = False, f"Upload failed: {e}"
        self._upload_signals.done.emit(ok, msg)

    def _on_upload_done(self, ok: bool, msg: str) -> None:
        self._upload_btn.setEnabled(True)
        self._status.setText(msg)
        if ok:
            self._refresh()

    # ── LoRA training ────────────────────────────────────────────────────
    # torch/transformers/peft/accelerate/datasets are NOT bundled in the
    # installer (multi-GB) -- training runs through a real system Python in
    # a visible terminal, same pattern as the Winkler-Codex model download
    # in cursiv_launcher.py. check_requirements() is pure stdlib + psutil,
    # so it's safe to call even before those packages are installed.

    def _start_lora_training(self) -> None:
        from cursiv_engine.training import lora_trainer as lt
        # Asks the system Python which packages it has -- a few seconds.
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self._status.setText("Checking Python and training packages…")
        QGuiApplication.processEvents()
        try:
            req = lt.check_requirements()
        finally:
            QGuiApplication.restoreOverrideCursor()
            self._status.setText("")

        if not req["python_ok"]:
            QMessageBox.warning(
                self, "Python Required",
                "LoRA training runs through a real Python interpreter with "
                "machine-learning packages installed -- none was found on this "
                "system.\n\nInstall Python from python.org (or re-run Cursiv's "
                "full setup script, which installs it), then try again."
            )
            return

        lines = [
            f"Base model: {req['base_model']}  (~3 GB download, one-time)",
            "",
            f"Free disk space:   {req['disk_free_gb']} GB   "
            + ("OK" if req["disk_ok"] else f"need at least {lt.MIN_FREE_DISK_GB:.0f} GB"),
        ]
        if req["ram_total_gb"]:
            lines.append(
                f"Total RAM:         {req['ram_total_gb']} GB   "
                + ("OK" if req["ram_ok"] else f"need at least {lt.MIN_FREE_RAM_GB:.0f} GB")
            )
        lines.append(
            "GPU:               "
            + (req["gpu_name"] if req["gpu_available"] else "none detected -- trains on CPU (slower, but works)")
        )
        lines.append(
            f"Training examples: {req['example_count']}"
            + ("" if req["examples_ok"] else f"  (fewer than the recommended {lt.MIN_EXAMPLES} -- results may be weak)")
        )
        if not req["gpu_available"] and req["example_count"]:
            lines.append(
                f"Estimated time:    ~{req['est_cpu_hours']} hour(s) on CPU, "
                f"{req['default_epochs']} epoch (a GPU would be much faster)"
            )
        summary = "\n".join(lines)

        if not req["disk_ok"]:
            QMessageBox.warning(self, "Not Enough Disk Space",
                                 summary + "\n\nFree up some space and try again.")
            return
        if req["example_count"] == 0:
            QMessageBox.information(
                self, "No Training Data",
                "Add some training examples first -- upload an image, paste JSON, "
                "or type notes and ask to translate them into JSON for training."
            )
            return

        if req["missing_packages"]:
            reply = QMessageBox.question(
                self, "Install Training Packages",
                summary + f"\n\nMissing packages: {', '.join(req['missing_packages'])}\n\n"
                "Install them now? This downloads roughly 1-2 GB (PyTorch's CPU "
                "build, plus the rest) in a terminal window you can watch.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._launch_terminal_script(
                self._install_script(req["python_exe"]),
                "Cursiv — Installing Training Packages",
            )
            return

        reply = QMessageBox.question(
            self, "Start LoRA Training",
            summary + "\n\nThis trains a small local model on everything currently "
            "in your training data store. It runs in a terminal window you can "
            "minimize and leave running -- CPU training can take a while depending "
            "on how much data you have.\n\nStart now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._launch_terminal_script(self._train_script(req["python_exe"]), "Cursiv — LoRA Training")

    def _launch_terminal_script(self, script: str, label: str) -> None:
        import subprocess
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(cc._CHAT_ROOT),
            )
            self._status.setText(f"{label} launched in a new terminal window.")
        except Exception as e:
            self._status.setText(f"Could not launch terminal: {e}")

    def _install_script(self, python_exe: str) -> str:
        return (
            "Write-Host '' ;"
            "Write-Host '  Cursiv — Installing LoRA Training Packages' -ForegroundColor DarkYellow ;"
            "Write-Host '' ;"
            f"& '{python_exe}' -m pip install --upgrade torch --index-url https://download.pytorch.org/whl/cpu ;"
            f"& '{python_exe}' -m pip install --upgrade transformers peft accelerate datasets ;"
            "Write-Host '' ;"
            "Write-Host '  Packages installed. Click Start LoRA Training again to begin.' -ForegroundColor Green ;"
            "Write-Host '' ;"
            "Write-Host '  Press Enter to close...' -NoNewline ;"
            "Read-Host"
        )

    @staticmethod
    def _ps_quote(text: str) -> str:
        return "'" + text.replace("'", "''") + "'"

    def _train_script(self, python_exe: str) -> str:
        from cursiv_engine.training import lora_trainer as lt
        data_root = str(cc._CHAT_ROOT)
        return (
            "Write-Host '' ;"
            "Write-Host '  Cursiv — LoRA Training' -ForegroundColor DarkYellow ;"
            "Write-Host '' ;"
            f"& '{python_exe}' -E -u -c {self._ps_quote(lt.module_launch_code(data_root, 'cursiv_engine.training.lora_trainer'))} ;"
            "Write-Host '' ;"
            "Write-Host '  Press Enter to close...' -NoNewline ;"
            "Read-Host"
        )

    # ── Merge into Ollama ────────────────────────────────────────────────
    # Converts the adapter directly to GGUF (no full-model merge needed)
    # and layers it onto Ollama's own qwen2.5:1.5b via a Modelfile ADAPTER
    # directive -- verified compatible (same Instruct checkpoint, confirmed
    # via Ollama's manifest shipping the matching ChatML template). Runs in
    # a terminal for the same reason training does: a real download (the
    # ~1GB base model, first time only) and a step that can take a minute.

    def _merge_into_ollama(self) -> None:
        from cursiv_engine.training import ollama_merge as om
        req = om.check_merge_requirements()

        if req["adapter_count"] == 0:
            QMessageBox.information(
                self, "No Trained Adapter",
                "Train a LoRA adapter first with \"Start LoRA Training…\" above."
            )
            return
        if not req["ollama_ok"]:
            QMessageBox.warning(
                self, "Ollama Required",
                "Ollama isn't installed. Install it first (tray menu → Install "
                "Ollama), then try again."
            )
            return
        if not req["disk_ok"]:
            QMessageBox.warning(
                self, "Not Enough Disk Space",
                f"Free disk: {req['disk_free_gb']} GB -- need at least "
                f"{om.MIN_FREE_DISK_GB:.0f} GB. Free up some space and try again."
            )
            return

        name, ok = QInputDialog.getText(
            self, "Merge into Ollama", "Name for the new Ollama model:",
            text="cursiv-tuned",
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        latest = Path(req["latest_adapter"]).name
        reply = QMessageBox.question(
            self, "Merge into Ollama",
            f"Merge the most recent adapter ({latest}) into a new Ollama model "
            f"named '{name}'?\n\n"
            f"Base model: {req['base_tag']}  (~1 GB, pulled automatically if not "
            f"already present)\n"
            f"Free disk: {req['disk_free_gb']} GB\n\n"
            "Runs in a terminal window you can watch. Once done, chat with it "
            f"via 'ollama run {name}'.\n\nStart now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._launch_terminal_script(
            self._merge_script(req["python_exe"], name), "Cursiv — Merging into Ollama"
        )

    def _merge_script(self, python_exe: str, model_name: str) -> str:
        from cursiv_engine.training import lora_trainer as lt
        data_root = str(cc._CHAT_ROOT)
        safe_name = model_name.replace("'", "''")
        return (
            "Write-Host '' ;"
            "Write-Host '  Cursiv — Merging LoRA Adapter into Ollama' -ForegroundColor DarkYellow ;"
            "Write-Host '' ;"
            f"& '{python_exe}' -E -u -c {self._ps_quote(lt.module_launch_code(data_root, 'cursiv_engine.training.ollama_merge'))} --name '{safe_name}' ;"
            "Write-Host '' ;"
            "Write-Host '  Press Enter to close...' -NoNewline ;"
            "Read-Host"
        )

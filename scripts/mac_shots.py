"""
Screenshots of Cursiv's real windows on the machine it runs on: the main window
(with the field demo's sample data), Tools, Settings → Privacy & internet and the
Field Notebook. Run by .github/workflows/mac-build.yml on GitHub's Mac, so the Mac
version can be seen before anyone has one in hand. No AI model is needed and none
of the windows show an AI answer.

    python scripts/mac_shots.py <output folder>
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / "launcher")]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)

out = Path(sys.argv[1] if len(sys.argv) > 1 else "mac-shots")
out.mkdir(parents=True, exist_ok=True)
home = Path(tempfile.mkdtemp(prefix="cursiv_shots_home_"))
os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)
os.environ["CURSIV_APP_DATA"] = str(home / "appdata")

from cursiv_engine.core import demo, netgate  # noqa: E402

netgate.set_offline(True)
demo.load()

from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv[:1])
import theme  # noqa: E402

theme.install()
app.setStyleSheet(theme.live(theme.APP_QSS))
import cursiv_launcher as cl  # noqa: E402
import nav_windows  # noqa: E402
from field_notebook import FieldNotebookDialog  # noqa: E402
from settings_dialog import SettingsDialog  # noqa: E402

w = cl.CursivLauncher("Demo")
w.resize(1280, 820)
w.show()
windows = {"main": w}


def open_rest():
    t = nav_windows.ToolsDialog(w); t.resize(760, 760); t.show(); windows["tools"] = t
    s = SettingsDialog(w); s.resize(1000, 700); s.show(); windows["settings"] = s
    n = FieldNotebookDialog(w, observer="Sample observer A"); n.resize(1000, 860); n.show(); windows["notebook"] = n


def save():
    for name, win in windows.items():
        win.grab().save(str(out / f"mac-{name}.png"))
        print("saved", out / f"mac-{name}.png", flush=True)
    demo.off()
    app.quit()


QTimer.singleShot(1500, open_rest)
QTimer.singleShot(5000, save)
app.exec()

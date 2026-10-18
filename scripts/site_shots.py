"""
Website screenshots of real answers, drawn sharp (2x).

    py -3.13 scripts/site_shots.py ask      # run the questions through Cursiv (needs the local model)
    py -3.13 scripts/site_shots.py draw     # draw the saved answers in the real window
    py -3.13 scripts/site_shots.py windows  # the Settings and Setup windows, as they open on this PC

`ask` copies this tree into an empty folder with an empty home folder, turns
offline mode on, and sends each conversation below through the same path as the
chat window (commands first, then chat()). The replies are saved unedited to
website/assets/shots/answers.json with the commit and date, so the site can say
exactly where each screen came from.

`draw` opens the real Cursiv window (no saved conversations, offline) at 2x
scale for each conversation, puts the saved turns in it the way a live answer
is shown, and saves website/assets/shots/<name>.png. Nothing in a screenshot is
typed by hand.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "website" / "assets" / "shots"
ANSWERS = OUT / "answers.json"

# name: (theme, [messages in order])
SHOTS = {
    "water": ("light", ["How do I purify creek water so it's safe to drink?"]),
    "bleeding": ("light", ["My son cut his leg and it's bleeding badly."]),
    "unknown": ("light", ["What did Dr. Harold Finchley's 1987 study on cattle and creek bacteria find?",
                          "What's my neighbor's name?"]),
    "math": ("light", ["I have to wake up at 6:00 AM, I want 8 hours of sleep, and it takes me 30 minutes "
                       "to fall asleep. What time should I get in bed?",
                       "Give me exactly 4 steps to check a well pump that stopped working, one sentence each."]),
    "memory": ("light", ["remember the north transect marker is 40 m past the culvert",
                         "where is the north transect marker?"]),
    "dark": ("dark", ["Is it safe?"]),
}

ASK_CHILD = r'''
import json, sys
sys.path[:0] = [".", "launcher"]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)
from cursiv_v215.core import netgate
netgate.set_offline(True)
from cursiv_v215.ui import chat_app as ca
import chat_commands as cc
ca._learn_later = lambda *a, **k: None
out = {}
for name, msgs in json.loads(sys.argv[1]).items():
    history, turns = [], []
    for text in msgs:
        res = cc.handle_command(text, {}, history)
        if res is None:
            parts = []
            for chunk in ca.chat(text, list(history), "", None, replace_draft=True):
                if chunk.startswith(ca.REPLACE_SENTINEL):
                    parts = [chunk[len(ca.REPLACE_SENTINEL):]]
                elif not chunk.startswith((ca.WRITE_SENTINEL, ca.RATE_SENTINEL)):
                    parts.append(chunk)
            reply, kind = "".join(parts), "chat"
        elif hasattr(res, "generator"):
            reply, kind = res.intro + "\n\n" + "".join(c for c in res.generator if isinstance(c, str)), "command"
        else:
            reply, kind = res.text, "command"
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
        turns.append({"ask": text, "reply": reply, "kind": kind})
    out[name] = turns
    print(json.dumps({"done": name}), flush=True)
print(json.dumps({"answers": out}), flush=True)
'''

DRAW_CHILD = r'''
import json, sys, time
sys.path[:0] = [".", "launcher"]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)
mode, turns, dest = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
from cursiv_v215.chat import keys
keys.store_key("ui_theme", mode)
from cursiv_v215.core import netgate
netgate.set_offline(True)
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
app = QApplication(sys.argv[:1])
import theme
theme.install()
app.setStyleSheet(theme.live(theme.APP_QSS))
import cursiv_launcher as cl
w = cl.CursivLauncher("Demo")
w.resize(1180, 820)
w.show()
p = w._chat_panel

def fill():
    p._clear_empty_state()
    for t in turns:
        p._append_user(t["ask"])
        p._begin_turn()
        p._reply_is_chat = t["kind"] == "chat"
        p._on_chunk(t["reply"])
        p._on_done()
    bar = p._transcript.verticalScrollBar()
    bar.setValue(0)

def shot():
    w.grab().save(dest)
    app.quit()

QTimer.singleShot(1500, fill)
QTimer.singleShot(3500, shot)
app.exec()
'''


WINDOW_CHILD = r'''
import sys
sys.path[:0] = [".", "launcher"]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)
from cursiv_v215.chat import keys
keys.store_key("ui_theme", "light")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
app = QApplication(sys.argv[:1])
import theme
theme.install()
app.setStyleSheet(theme.live(theme.APP_QSS))
which, dest = sys.argv[1], sys.argv[2]
if which == "settings":
    from settings_dialog import SettingsDialog
    w = SettingsDialog(None)
    w.resize(1000, 680)
else:
    from setup_dialog import SetupDialog
    w = SetupDialog(None)
    w.resize(860, 760)
w.show()
QTimer.singleShot(4000, lambda: (w.grab().save(dest), app.quit()))
app.exec()
'''


def windows() -> None:
    """Settings (Privacy & internet) and Setup, drawn at 2x. Setup shows this PC's real
    state: Ollama and the models installed here."""
    for which, name in (("settings", "settings-light.png"), ("setup", "setup.png")):
        scratch, env = _fresh_copy()
        env["QT_SCALE_FACTOR"] = "2"
        try:
            dest = OUT / name
            subprocess.run([sys.executable, "-c", WINDOW_CHILD, which, str(dest)], cwd=scratch / "app",
                           env=env, timeout=120)
            print(f"saved {dest}")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


def _fresh_copy() -> tuple[Path, dict]:
    scratch = Path(tempfile.mkdtemp(prefix="cursiv_shots_"))
    for part in ("cursiv_v215", "launcher"):
        shutil.copytree(REPO / part, scratch / "app" / part, ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
    (scratch / "home").mkdir()
    env = {**os.environ, "USERPROFILE": str(scratch / "home"), "HOME": str(scratch / "home"),
           "PYTHONIOENCODING": "utf-8"}
    for k in ("BRAVE_API_KEY", "CURSIV_RELAY_URL", "CURSIV_FLEET_TOKEN"):
        env.pop(k, None)
    return scratch, env


def ask() -> None:
    scratch, env = _fresh_copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    try:
        proc = subprocess.run([sys.executable, "-c", ASK_CHILD, json.dumps({k: v[1] for k, v in SHOTS.items()})],
                              cwd=scratch / "app", env=env, capture_output=True, text=True, encoding="utf-8")
        answers = next(json.loads(l)["answers"] for l in proc.stdout.splitlines() if l.startswith('{"answers"'))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    ANSWERS.write_text(json.dumps({"commit": commit, "date": time.strftime("%Y-%m-%d"), "offline": True,
                                   "conversations": answers}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved {ANSWERS}")


def draw() -> None:
    data = json.loads(ANSWERS.read_text(encoding="utf-8"))
    for name, (mode, _msgs) in SHOTS.items():
        turns = data["conversations"].get(name)
        if not turns:
            continue
        scratch, env = _fresh_copy()
        env["QT_SCALE_FACTOR"] = "2"                       # sharp on the site: drawn at twice the size
        try:
            dest = OUT / f"{name}.png"
            subprocess.run([sys.executable, "-c", DRAW_CHILD, mode, json.dumps(turns), str(dest)],
                           cwd=scratch / "app", env=env, timeout=120)
            print(f"saved {dest}")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    {"ask": ask, "draw": draw, "windows": windows}[sys.argv[1] if len(sys.argv) > 1 else "draw"]()

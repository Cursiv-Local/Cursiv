"""What has to survive closing Cursiv: a saved note and offline mode. Each check
saves in one Python process and reads it back in a fresh one, as a restart would,
with the network blocked in both (Findings P1, field-demo checklist)."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SAVE = r'''
import sys
sys.path[:0] = [".", "launcher"]
from cursiv_v215.core import netgate
netgate.set_offline(True)
from cursiv_v215.memory import semantic
print(semantic.memory_command("remember the north transect marker is 40 m past the culvert"))
'''

READ = r'''
import json, sys, socket
sys.path[:0] = [".", "launcher"]
from cursiv_v215.core import netgate
blocked = False
try:
    socket.create_connection(("1.1.1.1", 53), timeout=2)
except OSError:
    blocked = True
from cursiv_v215.memory import semantic
facts = semantic.list_facts()
print(json.dumps({"offline": netgate.is_offline(), "blocked": blocked,
                  "facts": [(f["text"], semantic.origin_of(f), f.get("date", "")) for f in facts]}))
'''


def _run(code, home, app):
    env = {**os.environ, "USERPROFILE": str(home), "HOME": str(home), "QT_QPA_PLATFORM": "offscreen",
           "PYTHONIOENCODING": "utf-8"}
    out = subprocess.run([sys.executable, "-c", code], cwd=app, env=env, capture_output=True, text=True,
                         encoding="utf-8", timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout.strip().splitlines()[-1]


def test_a_note_and_offline_mode_survive_a_restart(tmp_path):
    import shutil
    app = tmp_path / "app"
    for part in ("cursiv_v215", "launcher"):
        shutil.copytree(ROOT / part, app / part, ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
    home = tmp_path / "home"
    home.mkdir()

    assert "I'll remember" in _run(SAVE, home, app)
    after = json.loads(_run(READ, home, app))          # a new process: Cursiv opened again

    assert after["offline"] is True                    # offline mode is still on
    assert after["blocked"] is True                    # and outside connections are refused
    notes = {text: (origin, date) for text, origin, date in after["facts"]}
    assert "the north transect marker is 40 m past the culvert" in notes
    origin, date = notes["the north transect marker is 40 m past the culvert"]
    assert origin == "user_said" and len(date) == 10   # attributed to the person, dated

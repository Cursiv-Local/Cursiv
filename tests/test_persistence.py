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

    receipt = _run(SAVE, home, app)
    assert receipt.startswith('Saved to memory:') and 'Memory ID:' in receipt
    after = json.loads(_run(READ, home, app))          # a new process: Cursiv opened again

    assert after["offline"] is True                    # offline mode is still on
    assert after["blocked"] is True                    # and outside connections are refused
    notes = {text: (origin, date) for text, origin, date in after["facts"]}
    assert "the north transect marker is 40 m past the culvert" in notes
    origin, date = notes["the north transect marker is 40 m past the culvert"]
    assert origin == "user_said" and len(date) == 10   # attributed to the person, dated


FIELD = r'''
import json, sys
from pathlib import Path
sys.path[:0] = [".", "launcher"]
import portable
home = Path(sys.argv[1])
portable.apply_field_defaults(home)
from cursiv_v215.core import netgate
from cursiv_v215.chat import keys
from cursiv_v215.memory import semantic
from cursiv_v215.core import phases
print(json.dumps({"offline": netgate.is_offline(), "breaks": phases._break_notes_on(),
                  "learning": semantic.learning_enabled()}))
'''


def test_a_field_copy_starts_offline_quiet_and_not_learning(tmp_path):
    import shutil
    app = tmp_path / "app"
    for part in ("cursiv_v215", "launcher"):
        shutil.copytree(ROOT / part, app / part, ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "USERPROFILE": str(home), "HOME": str(home), "QT_QPA_PLATFORM": "offscreen",
           "PYTHONIOENCODING": "utf-8"}
    out = subprocess.run([sys.executable, "-c", FIELD, str(home)], cwd=app, env=env, capture_output=True,
                         text=True, encoding="utf-8", timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert json.loads(out.stdout.strip().splitlines()[-1]) == {"offline": True, "breaks": False, "learning": False}
    assert (home / ".cursiv" / "field_defaults_applied").exists()      # once only


def test_a_failed_save_leaves_the_old_file_intact(tmp_path, monkeypatch):
    import os
    from cursiv_v215.core import atomic
    f = tmp_path / "memory_facts.jsonl"
    atomic.write_text(f, "old\n")

    def power_cut(*a, **k):
        raise OSError("power cut before the swap")
    monkeypatch.setattr(os, "replace", power_cut)
    try:
        atomic.write_text(f, "new, half writ")
    except OSError:
        pass
    assert f.read_text(encoding="utf-8") == "old\n"            # never half of each


def test_automatic_fact_survives_restart_and_is_retrieved_without_history(tmp_path):
    import shutil
    app, home = tmp_path / 'app', tmp_path / 'home'
    home.mkdir()
    for part in ('cursiv_v215', 'launcher'):
        shutil.copytree(ROOT / part, app / part, ignore=shutil.ignore_patterns('__pycache__', '.cursiv'))
    save = '''
from cursiv_v215.core import netgate
netgate.set_offline(True)
from cursiv_v215.memory import semantic as sem
sem.set_person('bob')
sem.embed = lambda _: None
print(sem.learn_from_exchange("I'm building Cursiv for field research", 'Okay', lambda _: '', person='bob'))
'''
    read = '''
from cursiv_v215.memory import semantic as sem
sem.embed = lambda _: None
sem._strand_items = lambda: []
print(sem.build_context('Bob building Cursiv field research', person='bob'))
'''
    assert 'Cursiv' in _run(save, home, app)
    assert 'Cursiv' in _run(read, home, app)

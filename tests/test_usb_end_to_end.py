"""The whole Cursiv USB life cycle, end to end. Runs on every push, PR and release.

A computer's data -> Make USB (real make_usb) -> start from the drive in a fresh
process as the packaged app would (real portable.activate) -> save something there
-> move the drive to another letter/PC -> bring the drive's work back to a second
computer (real staged import). Only hardware and downloads are faked: a temporary
folder stands in for the drive, and the program/engine/model files are small stubs.

    python -m pytest -m usb -v
"""
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.usb
REPO = Path(__file__).resolve().parent.parent
PERSONAL_KEY = "gsk_TEST_PERSONAL_KEY_DO_NOT_COPY"


class _Signal:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class _Sig:
    def __init__(self):
        self.progress, self.done = _Signal(), _Signal()

    @property
    def result(self):
        return self.done.calls[-1]


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def kit(tmp_path, monkeypatch):
    """A computer with Cursiv installed and personal data, plus an empty drive."""
    import usb_maker
    import usb_sync
    from cursiv_engine.core import keystore
    prog = tmp_path / "installed" / "Cursiv"
    _write(prog / "Cursiv.exe", "program bytes")
    _write(prog / "_internal" / "lib.txt", "library")
    _write(prog / "_internal" / ".cursiv" / "config.json", '{"never": "copied from the program folder"}')
    models = tmp_path / "models"
    blob = _write(models / "blobs" / "sha256-aaa", "model weights")
    manifests = []
    for name, tag in (("qwen3", "4b-instruct"), ("nomic-embed-text", "latest")):
        m = _write(models / "manifests" / "registry.ollama.ai" / "library" / name / tag,
                   json.dumps({"layers": [{"digest": "sha256:aaa", "mediaType": "application/vnd.ollama.image.model"}]}))
        manifests.append({"name": f"{name}:{tag}", "manifest": m, "blobs": [blob], "size": blob.stat().st_size})
    engine = tmp_path / "ollama"
    _write(engine / "ollama.exe", "engine")
    app, home = tmp_path / "pc" / "app", tmp_path / "pc" / "home" / ".cursiv"
    _write(app / "config.json", json.dumps({"groq_key": PERSONAL_KEY, "ui_theme": "dark"}))
    _write(app / "memory_facts.jsonl", json.dumps({"id": "pc0000001", "person": "jw", "text": "Made on the PC",
                                                   "source": "manual", "created": "2026-10-24 09:00"}) + "\n")
    _write(home / "conversations" / "c1.json", '{"messages": []}')
    _write(home / "fieldlog" / "observations.jsonl", '{"id": "f1"}\n')
    _write(home / "config.json", json.dumps({"ui_theme": "light"}))   # a stale older copy, as on real PCs
    import os
    os.utime(home / "config.json", (1_000_000, 1_000_000))
    drive = tmp_path / "E-drive"
    drive.mkdir()
    monkeypatch.setattr(usb_maker, "program_dir", lambda: prog)
    monkeypatch.setattr(usb_maker, "models_dir", lambda: models)
    monkeypatch.setattr(usb_maker, "list_models", lambda: manifests)
    monkeypatch.setattr(usb_maker, "ollama_dir", lambda: engine)
    monkeypatch.setattr(usb_maker, "_volume_info", lambda root: ("CURSIV", "EXFAT"))
    monkeypatch.setattr(usb_sync, "data_sources", lambda: [app, home])
    monkeypatch.setattr(keystore, "_dpapi_available", lambda: False)
    return {"drive": drive, "app": app, "home": home, "models": manifests, "tmp": tmp_path}


def _make(kit, *, keys=False):
    import usb_maker
    sig = _Sig()
    usb_maker.make_usb(kit["drive"], kit["models"], True, sig, threading.Event(), False, keys)
    ok, message = sig.result
    assert ok, message
    return message


def _start_from(drive: Path, code: str) -> dict:
    """Start like Cursiv.exe on the drive does: a fresh process, frozen, portable."""
    script = f"""
import json, os, sys
sys.frozen = True
sys.executable = {str(drive / 'Cursiv' / 'Cursiv.exe')!r}
sys.path[:0] = [{str(REPO)!r}, {str(REPO / 'launcher')!r}]
import portable
active = portable.activate()
from cursiv_engine.core import paths
out = {{"active": active, "app_data": str(paths.APP_DATA), "home": os.environ.get("HOME")}}
{code}
print(json.dumps(out))
"""
    env = {k: v for k, v in __import__("os").environ.items() if not k.startswith("CURSIV_")}
    run = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=180, env=env)
    assert run.returncode == 0, run.stderr[-3000:]
    return json.loads(run.stdout.strip().splitlines()[-1])


def test_usb_full_life_cycle(kit):
    drive, tmp = kit["drive"], kit["tmp"]
    # An older USB maker's leftovers that conflict with Home (the 2026-10-24 startup failure).
    _write(drive / "Cursiv" / "_internal" / ".cursiv" / "memory.json", '{"legacy": true}')
    _write(drive / "Home" / ".cursiv" / "memory.json", '{"home": true}')

    message = _make(kit)
    assert "Your AI keys were not copied." in message
    data = drive / "Home" / ".cursiv"
    assert (drive / "Start Cursiv.bat").read_text(encoding="ascii").strip().endswith(r'"%~dp0Cursiv\Cursiv.exe"')
    assert (drive / "Cursiv" / "portable.cursiv").exists() and (drive / "Ollama" / "ollama.exe").exists()
    assert (drive / "Models" / "blobs" / "sha256-aaa").exists()
    assert (data / "memory_facts.jsonl").read_text(encoding="utf-8") == (kit["app"] / "memory_facts.jsonl").read_text(encoding="utf-8")
    assert (data / "conversations" / "c1.json").exists() and (data / "fieldlog" / "observations.jsonl").exists()
    assert (data / "portable-layout-v1.json").exists()        # the conflict did not stop anything
    config = json.loads((data / "config.json").read_text(encoding="utf-8"))
    assert config.get("ui_theme") == "dark" and "groq_key" not in config        # live settings, no personal key
    assert PERSONAL_KEY not in "".join(p.read_text(encoding="utf-8", errors="ignore")
                                       for p in drive.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl"))
    assert not (drive / "Cursiv" / "_internal" / ".cursiv" / "config.json").exists()   # never from the program folder

    # Start from the drive: everything Cursiv writes lands on it.
    started = _start_from(drive, """
from cursiv_engine.memory import semantic
# This fresh child does not inherit pytest's semantic-memory fixture.
semantic._embed_ok = False  # no local embedding discovery in an offline regression
semantic.add_fact("Written while running from the USB", "jw", "manual")
out["facts_file"] = str(semantic.FACTS_FILE)
""")
    assert started["active"] and Path(started["app_data"]) == data
    assert Path(started["facts_file"]).is_relative_to(drive)
    assert "Written while running from the USB" in (data / "memory_facts.jsonl").read_text(encoding="utf-8")
    backups_before = sorted(p.name for p in (data / "backups").iterdir())

    # The drive is unplugged and comes back as another letter on another PC.
    moved = tmp / "F-drive"
    shutil.move(str(drive), str(moved))
    again = _start_from(moved, """
from cursiv_engine.memory import semantic
out["facts"] = [f["text"] for f in semantic.list_facts("jw")]
""")
    assert again["active"] and Path(again["app_data"]) == moved / "Home" / ".cursiv"
    assert "Written while running from the USB" in again["facts"] and "Made on the PC" in again["facts"]
    assert sorted(p.name for p in (moved / "Home" / ".cursiv" / "backups").iterdir()) == backups_before

    # Back on a second computer: bring the drive's work in (staged, applied at next start).
    import usb_sync
    pc2_app, pc2_home = tmp / "pc2" / "app", tmp / "pc2" / "home" / ".cursiv"
    pc2_app.mkdir(parents=True)
    pc2_home.mkdir(parents=True)
    items = usb_sync.plan_import(moved / "Home" / ".cursiv", pc2_app.resolve(), pc2_home.resolve())
    import cursiv_engine.memory  # noqa: F401
    original = (usb_sync.import_targets, usb_sync.pending_dir)
    try:
        usb_sync.import_targets = lambda: (pc2_app.resolve(), pc2_home.resolve())
        usb_sync.pending_dir = lambda: pc2_home / usb_sync.PENDING
        usb_sync.stage_import(items)
        shutil.rmtree(moved)                                    # the drive can be gone by then
        done = usb_sync.apply_pending_import()
    finally:
        usb_sync.import_targets, usb_sync.pending_dir = original
    assert done["applied"] >= 3
    assert "Written while running from the USB" in (pc2_app / "memory_facts.jsonl").read_text(encoding="utf-8")
    assert (pc2_home / "conversations" / "c1.json").exists()


def test_update_keeps_newer_drive_data_and_the_drives_own_keys(kit):
    import usb_maker
    drive = kit["drive"]
    _make(kit)
    data = drive / "Home" / ".cursiv"
    # The drive's owner added their own key there and wrote newer notes on the drive.
    cfg = json.loads((data / "config.json").read_text(encoding="utf-8"))
    cfg["groq_key"] = "drive-own-key"
    _write(data / "config.json", json.dumps(cfg))
    with (data / "fieldlog" / "observations.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"id": "f2-on-the-drive"}\n')
    # Meanwhile the computer changed a setting.
    import os
    import time
    changed = _write(kit["app"] / "config.json", json.dumps({"groq_key": PERSONAL_KEY, "ui_theme": "high-contrast"}))
    later = time.time() + 60        # beyond the 2-second FAT/exFAT time slack
    os.utime(changed, (later, later))
    _make(kit)
    cfg = json.loads((data / "config.json").read_text(encoding="utf-8"))
    assert cfg["groq_key"] == "drive-own-key"                         # never replaced or removed
    assert cfg.get("ui_theme") == "high-contrast"                     # newer setting from the computer
    assert "f2-on-the-drive" in (data / "fieldlog" / "observations.jsonl").read_text(encoding="utf-8")
    up_to_date, report = usb_maker.check_usb(drive, kit["models"], True)
    assert up_to_date, report


def test_keys_are_copied_only_with_the_separate_opt_in(kit):
    message = _make(kit, keys=True)
    assert "copied and are readable on this drive" in message
    cfg = json.loads((kit["drive"] / "Home" / ".cursiv" / "config.json").read_text(encoding="utf-8"))
    assert cfg["groq_key"] == PERSONAL_KEY


def test_a_fresh_kit_without_personal_data_has_none(kit):
    import usb_maker
    sig = _Sig()
    usb_maker.make_usb(kit["drive"], kit["models"], False, sig, threading.Event(), False)
    assert sig.result[0], sig.result[1]
    home = kit["drive"] / "Home"
    assert not (home / ".cursiv" / "memory_facts.jsonl").exists() and not (home / ".cursiv" / "config.json").exists()
    started = _start_from(kit["drive"], "")
    assert started["active"] and Path(started["app_data"]) == home / ".cursiv"


def test_the_usb_gate_runs_on_every_push_pr_commit_and_release():
    workflow = (REPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "python -m pytest tests -m usb" in workflow
    assert 'branches: ["**"]' in workflow.split("pull_request:")[0]          # every branch push, not tags
    release = (REPO / "scripts" / "build_release.py").read_text(encoding="utf-8")
    assert "portable_report = verify_portable(work, env)" in release
    hook = (REPO / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    assert "-m usb" in hook
    selftest = (REPO / "launcher" / "selftest.py").read_text(encoding="utf-8")
    assert '("portable storage", portable_storage)' in selftest


def test_a_drive_made_for_one_scientist_starts_their_own_notebook_with_chosen_work(kit, monkeypatch):
    """U103: Make USB with a name and chosen notebooks (the real make_usb). The drive gets its own notebook
    and signing key in that name; the computer's notebook isn't copied onto it; only the chosen work is."""
    import usb_maker
    from cursiv_engine.core import fieldlog, fieldsync
    pc_notebook = kit["tmp"] / "pc-notebook"
    monkeypatch.setattr(fieldlog, "log_dir", lambda: pc_notebook)
    fieldlog.set_name("Base station")
    fieldlog.add(observer="lead", note="season start", sample_id="BS-0001")
    fieldlog.add(observer="lead", note="calibrated meters")
    _write(kit["home"] / "device_key.json", '{"the computer": "key"}')
    sig = _Sig()
    usb_maker.make_usb(kit["drive"], kit["models"], True, sig, threading.Event(), True, False,
                       "Ana Ruiz", [fieldlog.identity()["id"]])
    ok, message = sig.result
    assert ok, message
    assert "Ana Ruiz's" in message and "Base station" in message
    notebook = kit["drive"] / "Home" / ".cursiv" / "fieldlog"
    me = json.loads((notebook / "notebook.json").read_text(encoding="utf-8"))
    assert me["name"] == "Ana Ruiz" and me["id"] != fieldlog.identity()["id"]
    assert not (notebook / "observations.jsonl").exists()                 # her own notebook starts empty
    assert not (kit["drive"] / "Home" / ".cursiv" / "device_key.json").exists()   # and gets its own key
    copied = fieldsync._read_lines(notebook / "team" / f"{fieldlog.identity()['id']}.jsonl")
    assert [e["hash"] for e in copied] == [e["hash"] for e in fieldlog.entries()]
    # Made again: still the same person's notebook (same id), nothing duplicated
    usb_maker.make_usb(kit["drive"], kit["models"], True, sig, threading.Event(), True, False,
                       "Ana Ruiz", [fieldlog.identity()["id"]])
    assert sig.result[0], sig.result[1]
    assert json.loads((notebook / "notebook.json").read_text(encoding="utf-8"))["id"] == me["id"]

"""Plugins only run when approved, memories stay with their person, the USB
edition keeps data on the drive, and updates compare versions correctly.

Run:  python -m pytest tests/
Uses temporary folders only -- never your real plugins, memories or settings.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


# ── Plugins: nothing runs without approval ──────────────────────────────────

PLUGIN = '''
PLUGIN = {"description": "says hello"}

def register(cursiv):
    cursiv.add_command("hello", lambda rest: "hi " + rest)
'''


@pytest.fixture
def plugins(tmp, monkeypatch):
    from cursiv_v215.core import plugins as pl
    d = tmp / "plugins"
    monkeypatch.setattr(pl, "DIR", d)
    monkeypatch.setattr(pl, "STATE_FILE", d / "_plugins.json")
    monkeypatch.setattr(pl, "LOG_FILE", d / "_install_log.jsonl")
    pl.load_all(force=True)
    yield pl
    pl.load_all(force=True)


def test_approved_plugin_runs(plugins):
    assert "Installed" in plugins.install("greeter", PLUGIN, "test")
    assert plugins.run_command("hello there") == "hi there"


def test_unapproved_plugin_file_does_not_load(plugins):
    plugins.DIR.mkdir(parents=True, exist_ok=True)
    (plugins.DIR / "sneaky.py").write_text(PLUGIN, encoding="utf-8")
    plugins.load_all(force=True)
    assert plugins.run_command("hello there") is None
    assert "not approved" in plugins._status["sneaky"]["error"]


def test_plugin_changed_after_approval_does_not_load(plugins):
    plugins.install("greeter", PLUGIN, "test")
    (plugins.DIR / "greeter.py").write_text(PLUGIN.replace("hi ", "pwned "), encoding="utf-8")
    plugins.load_all(force=True)
    assert plugins.run_command("hello there") is None
    assert "changed since you approved" in plugins._status["greeter"]["error"]


def test_switched_off_plugin_does_not_run(plugins):
    plugins.install("greeter", PLUGIN, "test")
    plugins.set_enabled("greeter", False)
    plugins.load_all(force=True)
    assert plugins.run_command("hello there") is None


# ── Memory: each person's facts stay theirs ─────────────────────────────────

@pytest.fixture
def memory(tmp, monkeypatch):
    from cursiv_v215.memory import semantic as sem
    monkeypatch.setattr(sem, "CURSIV_DIR", tmp)
    monkeypatch.setattr(sem, "FACTS_FILE", tmp / "memory_facts.jsonl")
    monkeypatch.setattr(sem, "embed", lambda texts: None)       # keyword matching, no Ollama
    monkeypatch.setattr(sem, "_strand_items", lambda: [])
    return sem


def test_one_persons_memories_are_not_recalled_for_another(memory):
    memory.add_fact("Alice's bank PIN hint is her first dog's name", person="alice")
    memory.add_fact("Bob is learning to play the guitar", person="bob")
    bob_sees = " ".join(text for _s, _k, text in memory.recall("what is the bank PIN hint dog name", person="bob"))
    assert "Alice" not in bob_sees
    assert all(f["person"] in ("bob", memory.SHARED) for f in memory.list_facts("bob"))


def test_family_facts_are_shared(memory):
    memory.add_fact("The family dog is called Biscuit", person=memory.SHARED)
    assert any("Biscuit" in t for _s, _k, t in memory.recall("what is the family dog called", person="bob"))


def test_duplicate_fact_is_not_saved_twice(memory):
    assert memory.add_fact("Bob likes tea", person="bob")
    assert memory.add_fact("Bob likes tea", person="bob") is None


# ── USB edition: data stays on the drive ────────────────────────────────────

@pytest.mark.skipif(sys.platform != "win32", reason="the Cursiv USB edition is Windows-only for now")
def test_portable_mode_points_home_models_and_ollama_at_the_drive(tmp, monkeypatch):
    import portable
    drive = tmp / "drive"
    (drive / "Cursiv").mkdir(parents=True)
    (drive / "Cursiv" / portable.MARKER).write_text("x")
    (drive / "Ollama").mkdir()
    (drive / "Ollama" / "ollama.exe").write_text("x")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(drive / "Cursiv" / "Cursiv.exe"))
    for var in ("USERPROFILE", "HOME", "OLLAMA_MODELS", "PATH", "CURSIV_PORTABLE",
                "CURSIV_REAL_HOME", "CURSIV_USB_ROOT", 'CURSIV_APP_DATA', 'CURSIV_DATA_DIR',
                'CURSIV_HOST_LOCALAPPDATA', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP'):
        monkeypatch.setenv(var, os.environ.get(var, ""))
    real_home = os.environ["USERPROFILE"]

    assert portable.activate() is True
    assert Path(os.environ["USERPROFILE"]) == drive / "Home"
    assert Path(os.environ["OLLAMA_MODELS"]) == drive / "Models"
    assert os.environ["PATH"].startswith(str(drive / "Ollama"))
    assert os.environ["CURSIV_REAL_HOME"] == real_home


def test_normal_install_is_not_portable(tmp, monkeypatch):
    import portable
    (tmp / "Cursiv").mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp / "Cursiv" / "Cursiv.exe"))
    assert portable.usb_root() is None


# ── Updates: version comparison ─────────────────────────────────────────────

@pytest.mark.parametrize("remote,current,newer", [
    ("v3.14-U58", "3.14-U57", True),
    ("v3.14-U58", "3.14-U58", False),
    ("v3.14-U9", "3.14-U58", False),      # numeric, not alphabetical
    ("v3.14-U100", "3.14-U99", True),
    ("v3.15", "3.14-U58", True),
    ("v3.14", "3.14-U1", False),
])
def test_update_version_comparison(remote, current, newer):
    from cursiv_launcher import _version_is_newer
    assert _version_is_newer(remote, current) is newer

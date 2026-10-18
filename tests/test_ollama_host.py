"""Where the local AI engine lives, on Windows and macOS (core/ollama_host.py)."""
from pathlib import Path

from cursiv_v215.core import ollama_host as oh


def _no_path(monkeypatch):
    monkeypatch.setattr(oh.shutil, "which", lambda name: None)


def test_mac_finds_ollama_app_in_the_users_applications(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    monkeypatch.setattr(oh, "MAC", True)
    monkeypatch.setattr(oh, "WINDOWS", False)
    monkeypatch.setattr(oh, "_mac_apps", lambda: [tmp_path / "sys" / "Ollama.app", tmp_path / "Applications" / "Ollama.app"])
    assert not oh.installed()
    cli = tmp_path / "Applications" / "Ollama.app" / "Contents" / "Resources" / "ollama"
    cli.parent.mkdir(parents=True)
    cli.write_text("x")
    assert oh.exe() == str(cli) and oh.mac_app() == tmp_path / "Applications" / "Ollama.app"


def test_windows_finds_the_installed_exe(tmp_path, monkeypatch):
    _no_path(monkeypatch)
    monkeypatch.setattr(oh, "MAC", False)
    monkeypatch.setattr(oh, "WINDOWS", True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert oh.exe() is None
    exe = tmp_path / "Programs" / "Ollama" / "ollama.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("x")
    assert oh.exe() == str(exe)


def test_on_the_path_wins(monkeypatch):
    monkeypatch.setattr(oh.shutil, "which", lambda name: "/opt/homebrew/bin/ollama")
    assert oh.exe() == "/opt/homebrew/bin/ollama"


def test_the_installer_matches_the_system():
    assert oh.INSTALLER_URL.endswith("Ollama-darwin.zip" if oh.MAC else "OllamaSetup.exe")

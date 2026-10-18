"""Where program data lives (core/paths.py): next to the program, except inside the Mac app."""
import sys
from pathlib import Path

from cursiv_v215.core import paths


def test_source_and_windows_keep_the_folder_next_to_the_program(monkeypatch):
    monkeypatch.delenv("CURSIV_APP_DATA", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert paths.app_data_dir() == paths.PROGRAM_ROOT / ".cursiv"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert paths.app_data_dir() == paths.PROGRAM_ROOT / ".cursiv"


def test_the_mac_app_uses_application_support(monkeypatch):
    monkeypatch.delenv("CURSIV_APP_DATA", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert paths.app_data_dir() == Path.home() / "Library" / "Application Support" / "Cursiv"


def test_an_explicit_folder_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("CURSIV_APP_DATA", str(tmp_path))
    assert paths.app_data_dir() == tmp_path


def test_every_settings_reader_uses_the_same_file():
    from cursiv_v215.chat import keys
    from cursiv_v215.core import netgate
    assert keys.KEYS_FILE == netgate.CONFIG_FILE == paths.APP_DATA / "config.json"

"""Settings → Updates answers inside Settings.

The owner reported that the update button did nothing. The check ran, but every result went
to the main window's status line, behind Settings, and the button was labelled "Open".
"""
import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton

import cursiv_launcher as launcher
from settings_dialog import SettingsDialog

_app = QApplication.instance() or QApplication([])


class Window(QMainWindow):
    _check_updates = launcher.CursivLauncher._check_updates
    _on_update_result = launcher.CursivLauncher._on_update_result
    _set_status = launcher.CursivLauncher._set_status
    _update_status = launcher.CursivLauncher._update_status

    def __init__(self):
        super().__init__()
        self._upd_btn = QPushButton("Check for Updates", self)
        self._status_lbl = QLabel("Ready.", self)


class Checker:
    """Stands in for the GitHub request; the test decides when and what it answers."""
    last = None

    def __init__(self, on_result):
        self.on_result = on_result
        Checker.last = self

    def check(self):
        pass


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(launcher, "UpdateChecker", Checker)
    monkeypatch.setattr(launcher, "_net_allowed", lambda: True)
    win = Window()
    dlg = SettingsDialog(win, "Updates")
    dlg.win = win
    yield dlg
    dlg.deleteLater()
    win.deleteLater()


def _click(dlg):
    dlg._update_btn.click()


def test_the_button_says_what_it_does(settings):
    assert settings._update_btn.text() == "Check now"


def test_settings_shows_checking_and_blocks_a_second_check(settings):
    _click(settings)
    assert "GitHub" in settings._update_result.text()
    assert not settings._update_btn.isEnabled()


def test_up_to_date_is_shown_inside_settings(settings):
    _click(settings)
    Checker.last.on_result(dict(ok=True, tag=launcher._CURRENT_VERSION, body="", exe_url=None))
    assert "up to date" in settings._update_result.text()
    assert settings._update_btn.isEnabled()


def test_a_failed_check_is_shown_inside_settings(settings):
    _click(settings)
    Checker.last.on_result(dict(ok=False, error="timed out"))
    assert "timed out" in settings._update_result.text()
    assert settings._update_btn.isEnabled()


def test_offline_mode_is_shown_inside_settings(settings, monkeypatch):
    monkeypatch.setattr(launcher, "_net_allowed", lambda: False)
    Checker.last = None
    _click(settings)
    assert Checker.last is None                                 # GitHub is not contacted
    assert "Offline mode is on" in settings._update_result.text()
    assert settings._update_btn.isEnabled()


def test_a_newer_version_is_shown_and_still_opens_the_update_window(settings, monkeypatch):
    opened = []

    class Dialog:
        def __init__(self, tag, *args, **kwargs):
            opened.append(tag)

        def exec(self):
            pass

    monkeypatch.setattr(launcher, "UpdateDialog", Dialog)
    monkeypatch.setattr(launcher, "_version_is_newer", lambda *_: True)
    _click(settings)
    Checker.last.on_result(dict(ok=True, tag="3.14-U999", body="", exe_url=None))
    assert opened == ["3.14-U999"]
    assert "3.14-U999" in settings._update_result.text()
    assert settings._update_btn.isEnabled()


def test_a_tray_check_after_settings_does_not_write_to_settings(settings):
    _click(settings)
    Checker.last.on_result(dict(ok=True, tag=launcher._CURRENT_VERSION, body="", exe_url=None))
    before = settings._update_result.text()
    settings.win._check_updates()                               # tray and automatic checks pass no report
    Checker.last.on_result(dict(ok=False, error="timed out"))
    assert settings._update_result.text() == before
    assert "timed out" in settings.win._status_lbl.text()

"""
Cursiv Desktop Launcher — entry point.
Run:  pythonw launcher/main.py          (no console)
      python   launcher/main.py          (with console for debugging)
      python   -m launcher               (from repo root)
"""

import os
import sys
from pathlib import Path

# ── Cursiv.exe --plugin-runner: one plugin call in its own process (U98) ──────
# Before anything else: no data folders, no Qt, no Cursiv modules. The runner is
# standard library only and reads its request from stdin (core/plugin_runner.py).
if "--plugin-runner" in sys.argv[1:2] and os.environ.get("CURSIV_PLUGIN_SANDBOX") == "1":
    if getattr(sys, "frozen", False):
        sys.path.insert(0, os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))))
    from cursiv_engine.core import plugin_runner as _plugin_runner
    sys.exit(_plugin_runner.main())

# ── Ensure repo root is on sys.path so cursiv_engine imports work ─────────────
if getattr(sys, "frozen", False):
    _ROOT = Path(sys.executable).parent
else:
    _ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── One home for user data (installed app only) ───────────────────────────
# Before anything touches .cursiv: point the program-folder .cursiv folders at
# %USERPROFILE%\.cursiv so updates and reinstalls can never wipe user data.
# Running off a Cursiv USB? Point home/models/Ollama at the drive before
# anything below reads Path.home().
try:
    from portable import activate as _activate_portable
    _activate_portable()
except Exception as exc:
    # Never continue with host paths after detecting an unusable portable drive.
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, str(exc), 'Cursiv portable storage unavailable', 0x10)
    finally:
        raise SystemExit(f'Portable startup stopped: {exc}')

try:
    from data_home import link_data_folders
    link_data_folders()
except Exception:
    pass

# ── Error popups with a "Send problem report" button ─────────────────────
def _error_box(title: str, text: str, critical: bool = True) -> None:
    """Show an error with a 'Send problem report' button (sends Cursiv's logs
    to Joshua -- see problem_report.py). Falls back to a plain box."""
    try:
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(QMessageBox.Icon.Critical if critical else QMessageBox.Icon.Warning, title, text)
        report_btn = box.addButton("Send problem report", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is report_btn:
            from problem_report import open_report
            open_report(None, f"{title}\n{text}")
    except Exception:
        pass


# ── Crash logging ─────────────────────────────────────────────────────────
# The packaged build runs with console=False (no terminal window), which
# means Python's *default* crash handler tries to write to sys.stderr --
# and sys.stderr is None in a windowed PyInstaller build. That failure is
# itself silent. Worse, PyQt6's default behavior when an exception escapes
# a slot (a button click, a QTimer.singleShot callback -- e.g. the ones
# that fire 200ms/1.8s/3s after the main window is constructed, right in
# the "opens and closes after a few seconds" window) with no custom
# sys.excepthook installed is to hard-abort via qFatal -- immediate, no
# trace. main.py already had a try/except around constructing and showing
# the main window, but that block returns long before these deferred
# callbacks ever run inside the Qt event loop, so it can't catch them.
# This replaces the default handler with one that always writes to a file
# (never relies on stdout/stderr existing) and shows a real dialog instead
# of the process just vanishing.
_CRASH_LOG = Path.home() / ".cursiv" / "crash.log"


def _log_crash(exc_type, exc_value, exc_tb) -> None:
    import datetime
    import traceback
    try:
        _CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _CRASH_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 70}\n{datetime.datetime.now().isoformat()}\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is not None:
            _error_box(
                "Cursiv — Unexpected Error",
                "Cursiv hit an unexpected error and needs to close.\n\n"
                f"Details were saved to:\n{_CRASH_LOG}\n\n"
                f"{exc_type.__name__}: {exc_value}",
            )
    except Exception:
        pass


sys.excepthook = _log_crash

try:
    import faulthandler
    _CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
    _crash_fh = open(_CRASH_LOG, "a", encoding="utf-8")
    faulthandler.enable(file=_crash_fh)
except Exception:
    pass


# ── Windows: enable DPI awareness before QApplication is created ─────────────
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    if "--selftest" in sys.argv:            # Cursiv --selftest [report-file]: check, report, exit
        import selftest
        i = sys.argv.index("--selftest")
        sys.exit(selftest.run(sys.argv[i + 1] if len(sys.argv) > i + 1 else None))
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtCore import Qt
    except ImportError:
        print(
            "PyQt6 is not installed.\n"
            "Run:  pip install PyQt6\n"
            "Then restart Cursiv."
        )
        sys.exit(1)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    try:
        import theme
        theme.install()                        # light mode: older windows' colours follow too
        app.setStyleSheet(theme.APP_QSS)       # one look for every window
    except Exception:
        pass
    app.setApplicationName("Cursiv")
    app.setApplicationDisplayName("Cursiv")
    app.setApplicationVersion("3.14")
    app.setOrganizationName("Joshua Winkler")
    app.setQuitOnLastWindowClosed(False)

    # Hold a separate OS lease before any chat module can load private stores.
    # The offline migration uses the same lease; it cannot race autosave/learning.
    try:
        from cursiv_engine.core.data_lease import DataLease
        from encryption_dialog import startup as _unlock_data
        _data_lease = DataLease()
        _data_lease.__enter__()
        _data_lease.hold_until_exit()
        if not _unlock_data(configure='--encrypt-data' in sys.argv):
            _data_lease.__exit__(None, None, None)
            sys.exit(0)
    except OSError as exc:
        QMessageBox.critical(None, 'Cursiv data unavailable', str(exc))
        sys.exit(1)

    # Data brought from a Cursiv USB ("Bring drive data to this computer") is
    # applied here: the lease is held and no store has been read yet.
    if os.environ.get('CURSIV_PORTABLE') != '1':
        try:
            import usb_sync
            done = usb_sync.apply_pending_import()
            if done:
                QMessageBox.information(
                    None, 'Cursiv: data from your USB',
                    f"Brought {done['applied']} file(s) from your USB into Cursiv on this computer. "
                    f"Anything newer here was kept, and {done['backed_up']} replaced file(s) were "
                    f"backed up first.\n\nDetails: {done['report']}")
        except Exception as exc:
            QMessageBox.warning(None, 'Cursiv: data from your USB',
                                f"The data copied from your USB wasn't fully applied. Files already brought in "
                                f"stay (each replaced one was backed up); the rest is tried again at the next "
                                f"start.\n\n{exc}")

    # ── Single-instance enforcement ───────────────────────────────────────
    try:
        from cursiv_launcher import _acquire_instance_lock
        if not _acquire_instance_lock():
            QMessageBox.information(
                None,
                "Cursiv",
                "Cursiv Launcher is already running.\n"
                "Check the system tray (bottom-right).",
            )
            sys.exit(0)
    except ImportError:
        pass  # cursiv_launcher not yet importable — skip (shouldn't happen)

    # ── Auth gate ─────────────────────────────────────────────────────────
    # Fails closed: if the login can't load or breaks, Cursiv stops instead of
    # opening without it. (It used to warn and continue as "Joshua".)
    username = ""
    try:
        from cursiv_engine.guardian.access_gate import is_setup_complete
        from login_dialog import LoginDialog, SetupDialog

        if not is_setup_complete():
            dlg = SetupDialog()
            if not dlg.exec() or not dlg.accepted_ok():
                sys.exit(0)
        else:
            dlg = LoginDialog()
            if not dlg.exec() or not dlg.accepted_ok():
                sys.exit(0)
        username = dlg.get_username() or "friend"

    except SystemExit:
        raise
    except Exception as e:
        _error_box(
            "Cursiv — Login Unavailable",
            "Cursiv's login couldn't load, so Cursiv won't open — it never runs "
            "without the login.\n\n"
            f"Technical detail: {type(e).__name__}: {e}\n\n"
            "Reinstalling the latest version from the website usually fixes this "
            "(your data is kept). Or click Send problem report.",
        )
        sys.exit(1)

    # ── Main launcher window ──────────────────────────────────────────────
    try:
        from cursiv_launcher import CursivLauncher
    except ImportError as e:
        QMessageBox.critical(None, "Cursiv — Import Error", str(e))
        sys.exit(1)

    # Constructing the window does real work now (the chat panel loads its
    # own command router, which pulls in a long chain of cursiv_engine
    # modules) -- previously nothing here caught a failure, so any error
    # partway through construction meant total silence: no window, no tray
    # icon, no message, the process just exits. Surfacing it explicitly so
    # a real failure is at least visible and reportable instead of looking
    # like "login worked, then nothing happened."
    try:
        window = CursivLauncher(username=username)
        window.show()
    except Exception:
        import traceback
        details = traceback.format_exc()
        _error_box(
            "Cursiv — Startup Error",
            "Cursiv couldn't finish opening its main window.\n\n"
            f"{details}",
        )
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

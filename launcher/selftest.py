"""
`Cursiv --selftest [report-file]`: start the built app without a window, check that
its parts load and work on this computer, print a report and exit (0 = all passed).

Used by the macOS build on GitHub (no screen, no AI model), and useful on any
computer when something seems broken. It doesn't need the AI engine or the internet,
and it writes only a small test file in the data folders, which it removes.
"""
from __future__ import annotations

import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path


def _checks():
    def imports():
        import cursiv_engine.ui.chat_app      # noqa: F401
        import chat_commands                # noqa: F401
        import cursiv_launcher              # noqa: F401
        import pypdf                        # noqa: F401
        return "chat engine, commands, window code and the PDF reader load"

    def data_folders():
        from cursiv_engine.core import paths
        out = []
        for d in (paths.APP_DATA, Path.home() / ".cursiv"):
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".selftest"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            out.append(str(d))
        return "writable: " + ", ".join(out)

    def portable_storage():
        """Run from a Cursiv USB, everything must be on that drive (launcher/portable.py)."""
        if os.environ.get("CURSIV_PORTABLE") != "1":
            return "installed copy (not running from a Cursiv USB)"
        from cursiv_engine.core import paths
        drive = Path(os.environ["CURSIV_USB_ROOT"]).resolve()
        for name, folder in (("data", paths.APP_DATA), ("home", Path.home())):
            if not Path(folder).resolve().is_relative_to(drive):
                raise RuntimeError(f"{name} folder {folder} is not on the drive {drive}")
        probe = paths.APP_DATA / ".selftest-portable"
        probe.write_text("ok", encoding="utf-8")
        if probe.read_text(encoding="utf-8") != "ok":
            raise RuntimeError("drive write could not be read back")
        probe.unlink()
        return f"running from the drive {drive}; data at {paths.APP_DATA}"

    def reference():
        from cursiv_engine.core import reference
        n = len(reference.entries())
        assert n >= 100, n
        return f"{n} offline reference entries"

    def calculations():
        from cursiv_engine.core import calc
        w = calc.work_out("Convert 12.4 C to F")
        assert w and abs(w.value - 54.32) < 1e-6, w
        d = calc.work_out("What is the distance and bearing from 44.1234, -71.5678 to 44.1300, -71.5600?")
        assert d and abs(d.value - 963.1) < 0.5, d
        return "12.4 C = 54.32 F; 963.1 m between two GPS points"

    def field_notebook():
        from cursiv_engine.core import devicekey, fieldlog
        real, real_key = fieldlog.log_dir, devicekey.key_file
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp).resolve()       # macOS /var aliases /private/var
            fieldlog.log_dir = lambda: scratch
            devicekey.key_file = lambda: scratch / "device_key.json"   # never this computer's real key
            devicekey._cache.clear()
            try:
                e = fieldlog.add(observer="selftest", site="Test", measurements=[{"name": "pH", "value": "7.20"}])
                assert fieldlog.verify() == [] and e["measurements"][0]["value"] == "7.20"
                paths = fieldlog.export(scratch / "export")
                assert {"csv", "json", "geojson", "report", "signature"} <= set(paths)
                assert fieldlog.verify_export(scratch / "export") == []
            finally:
                fieldlog.log_dir, devicekey.key_file = real, real_key
                devicekey._cache.clear()
        return "an entry saved, fingerprint chain checked, exported and signed, signature verified"

    def documents():
        from cursiv_engine.core import documents
        assert documents.search("anything at all") is not None
        return "document search works"

    def window():
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([sys.argv[0]])
        import theme
        from cursiv_launcher import CursivLauncher
        theme.install()
        shell = CursivLauncher('Self-test')
        try:
            assert shell._chat_panel._net_pill.text()
            return ('full launcher, title bar, tray and chat window build '
                    f"(badge: {shell._chat_panel._net_pill.text().strip('● ')})")
        finally:
            shell._phone_sync_timer.stop()
            shell._tray.hide()
            shell.deleteLater()

    def engine():
        from cursiv_engine.core import ollama_host
        where = ollama_host.exe()
        return (f"Ollama found at {where}" + (" and running" if ollama_host.running() else ", not running")
                if where else "Ollama not installed (Setup installs it)")

    def owner_identity():
        from cursiv_engine.core import release_identity
        return 'Pinned owner key ' + release_identity.public_identity()['key_id']

    return [("imports", imports), ("owner release identity", owner_identity), ("data folders", data_folders),
            ("portable storage", portable_storage), ("offline reference", reference),
            ("calculations", calculations), ("field notebook", field_notebook), ("documents", documents),
            ("window", window), ("AI engine (information only)", engine)]


def run(report: str | None = None) -> int:
    import threading
    # The chat window starts a background model lookup; it may still be finishing when the
    # self-test exits. Its errors aren't part of the result.
    threading.excepthook = lambda args: None
    os.environ["CURSIV_NO_ENGINE_START"] = "1"         # check the window, but never start the AI engine
    lines, failed = [], 0
    try:
        from cursiv_engine.core import selfknow
        version = selfknow.VERSION
    except Exception:
        version = "?"
    lines.append(f"Cursiv {version} self-test on {platform.system()} {platform.release()} ({platform.machine()}), "
                 f"Python {platform.python_version()}, frozen={getattr(sys, 'frozen', False)}")
    for name, fn in _checks():
        try:
            lines.append(f"PASS  {name}: {fn()}")
        except Exception as exc:
            if name.startswith("AI engine"):
                lines.append(f"INFO  {name}: {exc}")
                continue
            failed += 1
            lines.append(f"FAIL  {name}: {type(exc).__name__}: {exc}")
            lines.append("      " + traceback.format_exc().strip().splitlines()[-1])
    lines.append("ALL PASSED" if not failed else f"{failed} FAILED")
    text = "\n".join(lines)
    if report:
        Path(report).write_text(text + "\n", encoding="utf-8")
    try:
        print(text, flush=True)
    except Exception:
        pass                                  # a windowed Windows build has no console
    return 0 if not failed else 1

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
        import cursiv_v215.ui.chat_app      # noqa: F401
        import chat_commands                # noqa: F401
        import cursiv_launcher              # noqa: F401
        import pypdf                        # noqa: F401
        return "chat engine, commands, window code and the PDF reader load"

    def data_folders():
        from cursiv_v215.core import paths
        out = []
        for d in (paths.APP_DATA, Path.home() / ".cursiv"):
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".selftest"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            out.append(str(d))
        return "writable: " + ", ".join(out)

    def reference():
        from cursiv_v215.core import reference
        n = len(reference.entries())
        assert n >= 100, n
        return f"{n} offline reference entries"

    def calculations():
        from cursiv_v215.core import calc
        w = calc.work_out("Convert 12.4 C to F")
        assert w and abs(w.value - 54.32) < 1e-6, w
        d = calc.work_out("What is the distance and bearing from 44.1234, -71.5678 to 44.1300, -71.5600?")
        assert d and abs(d.value - 963.1) < 0.5, d
        return "12.4 C = 54.32 F; 963.1 m between two GPS points"

    def field_notebook():
        from cursiv_v215.core import fieldlog
        real = fieldlog.log_dir
        with tempfile.TemporaryDirectory() as tmp:
            fieldlog.log_dir = lambda: Path(tmp)
            try:
                e = fieldlog.add(observer="selftest", site="Test", measurements=[{"name": "pH", "value": "7.20"}])
                assert fieldlog.verify() == [] and e["measurements"][0]["value"] == "7.20"
                paths = fieldlog.export(Path(tmp) / "export")
                assert {"csv", "json", "geojson", "report"} <= set(paths)
            finally:
                fieldlog.log_dir = real
        return "an entry saved, fingerprint chain checked, exported"

    def documents():
        from cursiv_v215.core import documents
        assert documents.search("anything at all") is not None
        return "document search works"

    def window():
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([sys.argv[0]])
        import theme
        import chat_panel
        theme.install()
        panel = chat_panel.ChatPanel()
        assert panel._net_pill.text()
        return f"chat window builds (badge: {panel._net_pill.text().strip('● ')})"

    def engine():
        from cursiv_v215.core import ollama_host
        where = ollama_host.exe()
        return (f"Ollama found at {where}" + (" and running" if ollama_host.running() else ", not running")
                if where else "Ollama not installed (Setup installs it)")

    return [("imports", imports), ("data folders", data_folders), ("offline reference", reference),
            ("calculations", calculations), ("field notebook", field_notebook), ("documents", documents),
            ("window", window), ("AI engine (information only)", engine)]


def run(report: str | None = None) -> int:
    import threading
    # The chat window starts a background model lookup; it may still be finishing when the
    # self-test exits. Its errors aren't part of the result.
    threading.excepthook = lambda args: None
    lines, failed = [], 0
    try:
        from cursiv_v215.core import selfknow
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

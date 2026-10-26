"""
The team-drive demo (U103): three scientists' field drives brought into one main computer, and a new
drive sent back out with chosen notebooks. Everything goes through Cursiv's own code (the notebook,
team sync, the USB maker's naming and copying) in a throwaway folder; screenshots are of the real
windows. Nothing reads or changes the data of the person running it.

    python scripts/team_demo.py setup <folder>              make the drives and the main computer
    python scripts/team_demo.py shots <folder> <out>        open the real windows and save screenshots

Each place (a drive, the main computer) runs in its own process, as Cursiv does: a drive's Cursiv sees
the drive as its home, exactly as portable.activate() sets it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SCIENTISTS = {
    "Ana Ruiz": dict(code="WC", sites=["Willow Creek WC-1", "Willow Creek WC-2", "Willow Creek WC-3"],
                     measures=lambda i: [("pH", f"{7.1 + (i % 4) / 10:.1f}", ""),
                                         ("dissolved oxygen", f"{8.6 - (i % 5) * 0.3:.1f}", "mg/L"),
                                         ("water temp", f"{12.4 + (i % 6) * 0.7:.1f}", "°C")],
                     notes=["riffle below the footbridge", "slight turbidity after rain",
                            "caddisfly cases on the cobbles", "beaver dam upstream raised the pool"]),
    "Ben Okafor": dict(code="PL", sites=["Pine Lake north buoy", "Pine Lake boat launch"],
                       measures=lambda i: [("Secchi depth", f"{3.2 - (i % 4) * 0.4:.1f}", "m"),
                                           ("water temp", f"{16.0 + (i % 5) * 0.6:.1f}", "°C"),
                                           ("dissolved oxygen", f"{9.1 - (i % 3) * 0.5:.1f}", "mg/L")],
                       notes=["calm, light wind from the west", "algae visible along the shore",
                              "loons on the north side", "sample taken at 1 m depth"]),
    "Cara Lindqvist": dict(code="HE", sites=["Harbor estuary mouth", "Harbor estuary marsh edge"],
                           measures=lambda i: [("salinity", f"{18 + (i % 6) * 1.5:.1f}", "ppt"),
                                               ("turbidity", f"{6 + (i % 4) * 2.5:.1f}", "NTU"),
                                               ("water temp", f"{14.2 + (i % 5) * 0.5:.1f}", "°C")],
                           notes=["incoming tide", "eelgrass bed visible at low water",
                                  "fresh outflow after the storm", "crab burrows along the bank"]),
}
MAIN = "Field station"
NEW_DRIVE = "Dee Park"
CHOSEN = ("Ana Ruiz", "Cara Lindqvist")


def drive_root(base: Path, who: str) -> Path:
    return base / "drives" / who.replace(" ", "_")


def _env(base: Path, where: str) -> dict:
    """The environment Cursiv has at that place: a drive's home is on the drive (portable.activate)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CURSIV_")}
    if where == "main":
        home = base / "main" / "home"
        env.update(HOME=str(home), USERPROFILE=str(home), CURSIV_APP_DATA=str(home / "appdata"))
    else:
        root = drive_root(base, where)
        home = root / "Home"
        env.update(HOME=str(home), USERPROFILE=str(home), CURSIV_PORTABLE="1", CURSIV_USB_ROOT=str(root),
                   CURSIV_APP_DATA=str(home / ".cursiv"), CURSIV_DATA_DIR=str(home / ".cursiv"))
    home.mkdir(parents=True, exist_ok=True)
    return env


def _run(base: Path, where: str, *args: str) -> None:
    subprocess.run([sys.executable, __file__, *args], env=_env(base, where), check=True, cwd=str(REPO))


def _imports():
    sys.path[:0] = [str(REPO), str(REPO / "launcher")]
    for m in ("codex_tool_bridge", "knowledge_brain"):
        sys.modules.setdefault(m, None)


def _photo(path: Path, caption: str, seed: int) -> Path:
    """A plain stand-in for a field photo (sky, tree line, water) with its caption."""
    from PIL import Image, ImageDraw
    w, h = 960, 640
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        if y < h * 0.45:
            t = y / (h * 0.45)
            c = (int(120 + 80 * t), int(170 + 50 * t), int(225 - 10 * t))
        else:
            t = (y - h * 0.45) / (h * 0.55)
            c = (int(40 + 30 * t + seed % 20), int(90 + 40 * t), int(110 + 30 * t))
        d.line([(0, y), (w, y)], fill=c)
    for x in range(0, w, 6):
        top = int(h * 0.38 + 30 * ((x * 7 + seed * 13) % 17) / 17)
        d.line([(x, top), (x, int(h * 0.46))], fill=(30, 70 + seed % 30, 40), width=6)
    d.rectangle([0, h - 56, w, h], fill=(0, 0, 0))
    d.text((18, h - 42), caption, fill=(240, 240, 240))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=82)
    return path


def _record(who: str, n: int) -> None:
    """In the scientist's drive process: a field season, with photos, then quit (which shares)."""
    _imports()
    from cursiv_engine.core import fieldlog, fieldsync
    spec = SCIENTISTS[who]
    camera = Path(os.environ["HOME"]).parent / "camera"
    for i in range(n):
        site = spec["sites"][i % len(spec["sites"])]
        photos = [_photo(camera / f"{spec['code']}-{i:02d}.jpg", f"{site} · {who}", i)] if i % 3 == 0 else None
        fieldlog.add(observer=who, site=site, sample_id=f"{spec['code']}-1014-{i + 1:02d}",
                     measurements=[{"name": a, "value": v, "unit": u} for a, v, u in spec["measures"](i)],
                     note=spec["notes"][i % len(spec["notes"])], photos=photos, project="FALL-2026")
    fieldsync.auto_share()


def setup(base: Path) -> None:
    base.mkdir(parents=True, exist_ok=True)
    _imports()
    from cursiv_engine.core import fieldlog
    for who in SCIENTISTS:                     # Make USB with "Whose drive is this?" filled in
        fieldlog.name_new_notebook(drive_root(base, who) / "Home" / ".cursiv" / "fieldlog", who)
    for who, n in zip(SCIENTISTS, (9, 7, 8)):
        _run(base, who, "_record", who, str(n))
    _run(base, "main", "_main")
    print("ready:", base)


def _main() -> None:
    _imports()
    from cursiv_engine.core import fieldlog
    fieldlog.set_name(MAIN)
    fieldlog.add(observer="Lead", note="Season start: meters calibrated (pH 4/7/10, DO at 100% air)",
                 project="FALL-2026")


# ── screenshots ─────────────────────────────────────────────────────────────

def shots(base: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    _run(base, "Ana Ruiz", "_shot_drive", str(out), "Ana Ruiz", "01-ana-drive")
    _run(base, "main", "_shot_import", str(out), str(base))
    _run(base, "main", "_shot_new_drive", str(out), str(base))
    _run(base, NEW_DRIVE, "_shot_drive", str(out), NEW_DRIVE, "08-dee-drive")
    _run(base, "main", "_shot_capabilities", str(out))
    print("saved in", out)


def _app():
    _imports()
    from cursiv_engine.core import netgate
    netgate.set_offline(True)
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])
    import theme
    theme.install()
    app.setStyleSheet(theme.live(theme.APP_QSS))
    return app


def _wait(app, ms: int) -> None:
    from PyQt6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _chat(app, window, text: str, out: Path, name: str, timeout_s: int = 180, top: bool = False) -> None:
    """Type a message into the real chat and save the window once the answer is in (top: show the start
    of a long answer, such as the team log's header)."""
    import time
    panel = window._chat_panel
    panel.new_conversation()
    panel._input.setPlainText(text)
    panel._send()
    _wait(app, 500)
    start = time.time()
    while panel.is_busy() and time.time() - start < timeout_s:
        _wait(app, 300)
    _wait(app, 800)
    if top:
        panel._transcript.verticalScrollBar().setValue(0)
        _wait(app, 300)
    window.grab().save(str(out / f"{name}.png"))


def _main_window(user: str):
    import cursiv_launcher as cl
    # As a returning user sees it: no first-run welcome, and no Setup window (the demo shows the work,
    # not installing the AI engine). Both would wait for a click.
    cl._mark_getting_started_seen()
    cl.CursivLauncher._maybe_open_setup = lambda self: None
    w = cl.CursivLauncher(user)
    w.resize(1280, 820)
    w.show()
    return w


def _notebook(parent, observer: str):
    from field_notebook import FieldNotebookDialog
    n = FieldNotebookDialog(parent, observer=observer)
    n.resize(1100, 860)
    n.show()
    return n


def _shot_drive(out: str, who: str, name: str) -> None:
    out = Path(out)
    app = _app()
    w = _main_window(who.split()[0])
    _wait(app, 1500)
    n = _notebook(w, who)
    _wait(app, 1200)
    n.grab().save(str(out / f"{name}-notebook.png"))
    n.close()
    _chat(app, w, "team log" if who == NEW_DRIVE else "field log", out, f"{name}-chat", top=True)


def _report_box(parent, title: str, text: str, out: Path, name: str, app) -> None:
    from PyQt6.QtWidgets import QMessageBox
    box = QMessageBox(QMessageBox.Icon.Information, title, text, QMessageBox.StandardButton.Ok, parent)
    box.setModal(False)
    box.show()
    _wait(app, 700)
    box.grab().save(str(out / f"{name}.png"))
    box.close()


def _shot_import(out: str, base: str) -> None:
    """The main computer takes the three drives one at a time (Import from team…)."""
    out, base = Path(out), Path(base)
    app = _app()
    from cursiv_engine.core import fieldsync
    w = _main_window("Lead")
    _wait(app, 1500)
    for k, who in enumerate(SCIENTISTS, start=2):
        text = fieldsync.report_text(fieldsync.import_folder(drive_root(base, who)))
        _report_box(w, "Team field logs", text + "\n\nFor the whole team: type 'team log' or 'team log export' "
                    "in the chat.", out, f"0{k}-import-{who.split()[0].lower()}", app)
    n = _notebook(w, "Lead")
    _wait(app, 1000)
    n.grab().save(str(out / "05-main-notebook.png"))
    n.close()
    _chat(app, w, "team log", out, "06-team-log", top=True)
    paths = fieldsync.team_export(base / "export")
    (out / "export-path.txt").write_text(json.dumps({k: str(v) for k, v in paths.items()}), encoding="utf-8")


def _shot_new_drive(out: str, base: str) -> None:
    """Make a Cursiv USB for Dee Park, carrying Ana's and Cara's notebooks only."""
    out, base = Path(out), Path(base)
    app = _app()
    import usb_maker
    from PyQt6.QtCore import Qt
    from cursiv_engine.core import fieldlog, fieldsync
    root = drive_root(base, NEW_DRIVE)
    root.mkdir(parents=True, exist_ok=True)
    usb_maker.list_drives = lambda: [{"root": str(root) + os.sep, "letter": "E", "label": "DEE-FIELD",
                                      "fs": "EXFAT", "removable": True, "free": 118 << 30, "total": 128 << 30}]
    dlg = usb_maker.UsbMakerDialog()
    dlg.resize(700, 900)
    dlg.show()
    _wait(app, 1500)
    dlg._field.setChecked(True)
    dlg._workspace.setText(NEW_DRIVE)
    for i in range(dlg._team_list.count()):
        item = dlg._team_list.item(i)
        if any(item.text().startswith(c) for c in CHOSEN):
            item.setCheckState(Qt.CheckState.Checked)
    _wait(app, 600)
    dlg.grab().save(str(out / "07-make-usb.png"))
    # What Make USB then does for the notebook (usb_ops.make_usb): the drive's own notebook in Dee's name,
    # and only the ticked notebooks copied onto it. (Program and model files aren't copied for the demo.)
    names = {v: k for k, v in fieldlog.notebook_names().items()}
    notebook = root / "Home" / ".cursiv" / "fieldlog"
    fieldlog.name_new_notebook(notebook, NEW_DRIVE)
    fieldsync.copy_notebooks_to(notebook, [names[c] for c in CHOSEN])


def _shot_capabilities(out: str) -> None:
    """The rest of Cursiv on the main computer: a calculation done by code, the integrity check, and a
    live local-model answer (the overconfidence note appears only if that answer settles the verdict)."""
    out = Path(out)
    app = _app()
    w = _main_window("Lead")
    _wait(app, 1500)
    _chat(app, w, "oxygen saturation at 18.6 °C", out, "09-calculation")
    _chat(app, w, "field log check", out, "10-integrity")
    _chat(app, w, "My dissolved oxygen meter reads 12.5 mg/L at 10 °C. Is my meter broken?", out,
          "11-model-answer", top=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "setup":
        setup(Path(sys.argv[2]))
    elif cmd == "shots":
        shots(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "_record":
        _record(sys.argv[2], int(sys.argv[3]))
    elif cmd == "_main":
        _main()
    elif cmd == "_shot_drive":
        _shot_drive(*sys.argv[2:5])
    elif cmd == "_shot_import":
        _shot_import(*sys.argv[2:4])
    elif cmd == "_shot_capabilities":
        _shot_capabilities(sys.argv[2])
    elif cmd == "_shot_new_drive":
        _shot_new_drive(*sys.argv[2:4])
    else:
        raise SystemExit(__doc__)

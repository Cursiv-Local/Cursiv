"""Field notebook (research roadmap R1): append-only, tamper-evident, exact values, exports."""
import csv
import json

import pytest

from cursiv_v215.core import fieldlog as fl


@pytest.fixture
def log(tmp_path, monkeypatch):
    monkeypatch.setattr(fl, "log_dir", lambda: tmp_path / "fieldlog")
    return fl


def test_values_are_kept_exactly_as_typed(log):
    e = log.add(observer="Dana", site="North transect", measurements=[{"name": "water temp", "value": "12.40", "unit": "C"}])
    assert e["measurements"][0]["value"] == "12.40" and e["measurements"][0]["number"] == 12.4
    assert log.entries()[0]["measurements"][0]["value"] == "12.40"


def test_corrections_add_an_entry_and_keep_the_original(log):
    a = log.add(site="Pond", measurements=[{"name": "pH", "value": "7.9", "unit": ""}])
    b = log.correct(a["id"], "meter not calibrated; re-read", measurements=[{"name": "pH", "value": "7.2", "unit": ""}])
    assert [e["id"] for e in log.entries()] == [a["id"], b["id"]]             # both kept
    assert [e["id"] for e in log.current()] == [b["id"]]                       # the correction stands
    assert b["corrects"] == a["id"] and b["site"] == "Pond"                    # copied fields
    with pytest.raises(ValueError):
        log.correct(a["id"], "")                                               # a reason is required


def test_the_log_is_intact_until_someone_edits_it(log):
    log.add(note="first")
    log.add(measurements=[{"name": "count", "value": "14", "unit": "frogs"}])
    log.add(note="third")
    assert log.verify() == []
    lines = log.log_file().read_text(encoding="utf-8").splitlines()

    changed = json.loads(lines[1]); changed["measurements"][0]["value"] = "41"
    log.log_file().write_text("\n".join([lines[0], json.dumps(changed), lines[2]]) + "\n", encoding="utf-8")
    assert any("changed after it was recorded" in p for p in log.verify())

    log.log_file().write_text("\n".join([lines[0], lines[2]]) + "\n", encoding="utf-8")   # one removed
    assert any("removed, inserted or reordered" in p for p in log.verify())


def test_a_cut_off_last_line_is_reported_not_hidden(log):
    log.add(note="ok")
    with log.log_file().open("a", encoding="utf-8") as f:
        f.write('{"id": "half')                                                # power cut mid-write
    assert log.entries()[0]["note"] == "ok"
    assert any("isn't a complete entry" in p for p in log.verify())


def test_bad_input_is_refused(log):
    with pytest.raises(ValueError):
        log.add(note="x", lat=95, lon=10)
    with pytest.raises(ValueError):
        log.add(note="x", lat=44.0)
    with pytest.raises(ValueError):
        log.add()
    assert log.entries() == []


def test_exports_match_what_was_entered(log, tmp_path):
    a = log.add(observer="Dana", site="North transect", lat=44.1234, lon=-71.5678, location_source="typed",
                measurements=[{"name": "water temp", "value": "12.40", "unit": "C"},
                              {"name": "pH", "value": "7.2", "unit": ""}], note="turbid")
    log.add(note="no coordinates")
    paths = log.export(tmp_path / "out")
    rows = list(csv.DictReader(paths["csv"].open(encoding="utf-8")))
    assert [(r["measurement"], r["value"], r["unit"]) for r in rows[:2]] == [("water temp", "12.40", "C"), ("pH", "7.2", "")]
    assert rows[0]["fingerprint"] == a["hash"] and rows[2]["note"] == "no coordinates"
    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert data["integrity"] == "intact" and len(data["entries"]) == 2
    geo = json.loads(paths["geojson"].read_text(encoding="utf-8"))
    assert [f["geometry"]["coordinates"] for f in geo["features"]] == [[-71.5678, 44.1234]]


def test_typed_entries(log):
    reply = log.command("log site: North transect; water temp 12.4 C; pH 7.2; 44.1234, -71.5678; note: turbid", "Dana")
    assert reply.startswith("Saved to the field log")
    e = log.entries()[0]
    assert e["site"] == "North transect" and e["observer"] == "Dana" and e["location_source"] == "typed"
    assert [(m["name"], m["value"], m["unit"]) for m in e["measurements"]] == [("water temp", "12.4", "C"), ("pH", "7.2", "")]
    assert e["note"] == "turbid"
    assert "intact" in log.command("field log check")
    assert "North transect" in log.command("field log")
    assert log.command("hello there") is None


def test_chat_window_command_saves_an_entry(tmp_path, monkeypatch):
    import chat_commands
    monkeypatch.setattr(fl, "log_dir", lambda: tmp_path / "fieldlog")
    res = chat_commands.handle_command("log site: Pond 2; dissolved oxygen 8.1 mg/L", {}, [])
    assert "Saved to the field log" in res.text
    assert fl.entries()[0]["measurements"][0]["unit"] == "mg/L"


@pytest.mark.parametrize("text", ["log out", "log in", "log into my email", "log me out"])
def test_account_words_are_not_field_entries(log, text):
    assert log.command(text) is None and log.entries() == []


def test_the_log_survives_a_restart(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    env = {**os.environ, "USERPROFILE": str(tmp_path), "HOME": str(tmp_path), "PYTHONIOENCODING": "utf-8"}
    write = "import sys; sys.path.insert(0, '.'); from cursiv_v215.core import fieldlog as f; f.add(site='Pond', note='seen')"
    read = ("import sys, json; sys.path.insert(0, '.'); from cursiv_v215.core import fieldlog as f; "
            "print(json.dumps([len(f.entries()), f.verify()]))")
    subprocess.run([sys.executable, "-c", write], cwd=root, env=env, check=True)
    out = subprocess.run([sys.executable, "-c", read], cwd=root, env=env, check=True, capture_output=True, text=True)
    assert out.stdout.strip() == "[1, []]"


def test_notebook_window_saves_corrects_and_shows_integrity(log, monkeypatch):
    from PyQt6.QtWidgets import QApplication, QInputDialog
    app = QApplication.instance() or QApplication([])
    import field_notebook
    w = field_notebook.FieldNotebookDialog(None, observer="Dana")
    w._site.setText("Pond 2"); w._lat.setText("44.5"); w._lon.setText("-71.1")
    n, v, u = w._rows[0]; n.setText("water temp"); v.setText("12.40"); u.setText("C")
    w._save_entry()
    assert log.entries()[0]["measurements"][0]["value"] == "12.40" and w._table.rowCount() == 1
    w._table.selectRow(0); w._start_correction()
    w._rows[0][1].setText("12.10")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("misread the thermometer", True))
    w._save_entry()
    assert len(log.entries()) == 2 and w._table.rowCount() == 1           # original kept, correction shown
    assert "intact" in w._integrity.text()

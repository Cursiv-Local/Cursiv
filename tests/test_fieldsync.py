"""Team sync without internet (research roadmap R6): three laptops, one USB drive,
nothing lost or duplicated, and nothing resolved silently."""
import json
from contextlib import contextmanager

import pytest

from cursiv_v215.core import fieldlog, fieldsync


@pytest.fixture
def team(tmp_path, monkeypatch):
    """laptop("A") switches which laptop's log the calls use."""
    state = {}
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / state["name"] / "fieldlog")
    monkeypatch.setattr(fieldlog, "_device", lambda: "laptop" + state["name"])

    @contextmanager
    def laptop(name):
        state["name"] = name
        yield

    return laptop, tmp_path / "usb"


def _week(laptop, name, n):
    with laptop(name):
        for i in range(n):
            fieldlog.add(observer=name, site=f"Site {i % 3}", measurements=[{"name": "pH", "value": f"7.{i}"}])


def test_three_laptops_merge_with_nothing_lost_or_duplicated(team):
    laptop, usb = team
    for name, n in (("A", 5), ("B", 4), ("C", 6)):
        _week(laptop, name, n)
        with laptop(name):
            fieldsync.share(usb)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["added"] == {"laptopB": 4, "laptopC": 6} and r["own"] and not r["conflicts"] and not r["rejected"]
        rows = fieldsync.team_entries()
        assert len(rows) == 15 and len({e["hash"] for e in rows}) == 15
        assert fieldlog.verify() == []                         # A's own chain is untouched
        assert len(fieldlog.entries()) == 5
        again = fieldsync.import_folder(usb)                    # importing twice adds nothing
        assert again["added"] == {} and sorted(again["unchanged"]) == ["laptopB", "laptopC"]
        assert len(fieldsync.team_entries()) == 15
    _week(laptop, "B", 2)                                       # B keeps logging, shares again
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        assert fieldsync.import_folder(usb)["added"] == {"laptopB": 2}
        assert len(fieldsync.team_entries()) == 17


def test_a_changed_or_cut_off_share_is_not_imported(team):
    laptop, usb = team
    _week(laptop, "B", 3)
    with laptop("B"):
        out = fieldsync.share(usb)
    log = out / "laptopB.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    e = json.loads(lines[1]); e["measurements"][0]["value"] = "9.9"
    log.write_text("\n".join([lines[0], json.dumps(e), lines[2]]) + "\n", encoding="utf-8")
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert not r["added"] and "changed after it was recorded" in r["rejected"][0]
    log.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")          # the copy was cut off
    with laptop("A"):
        assert "manifest says 3 entries but the copy has 2" in fieldsync.import_folder(usb)["rejected"][0]


def test_different_history_keeps_both_and_chooses_neither(team, tmp_path):
    laptop, usb = team
    _week(laptop, "B", 3)
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        fieldsync.import_folder(usb)
    # B's log is replaced by a different one (e.g. restored from an old backup and re-logged)
    import shutil
    shutil.rmtree(tmp_path / "B")
    _week(laptop, "B", 4)
    with laptop("B"):
        fieldsync.share(usb)
    with laptop("A"):
        r = fieldsync.import_folder(usb)
        assert r["conflicts"] and "neither was chosen" in r["conflicts"][0]
        kept = sorted(p.name for p in fieldsync.team_dir().iterdir())
        assert kept[0].startswith("laptopB.conflict-") and kept[1] == "laptopB.jsonl"
        assert len(fieldsync.team_entries()) == 3                # the earlier copy is still the team view


def test_the_same_sample_id_on_two_laptops_is_reported(team):
    laptop, usb = team
    for name in ("A", "B"):
        with laptop(name):
            fieldlog.add(observer=name, sample_id="NT-20261018-001", note="bottle 1")
            fieldsync.share(usb)
    with laptop("A"):
        text = fieldsync.report_text(fieldsync.import_folder(usb))
        assert "CHECK sample NT-20261018-001 was recorded on 2 laptops" in text


def test_only_the_field_log_is_shared(team, tmp_path):
    laptop, usb = team
    _week(laptop, "A", 1)
    with laptop("A"):
        out = fieldsync.share(usb)
    assert sorted(p.name for p in out.iterdir()) == ["laptopA.jsonl", "laptopA.manifest.json"]


def test_team_export_and_commands(team, tmp_path):
    laptop, usb = team
    _week(laptop, "B", 2)
    with laptop("B"):
        assert "Shared this laptop's field log" in fieldsync.command(f"field log share {usb}")
    with laptop("A"):
        fieldlog.add(observer="A", note="first")
        assert "laptopB: 2 new entries" in fieldsync.command(f'field log import "{usb}"')
        assert "3 entries from 2 devices" in fieldsync.command("team log")
        paths = fieldsync.team_export(tmp_path / "out")
        csv_text = paths["csv"].read_text(encoding="utf-8")
        assert csv_text.count("laptopB") == 2 and csv_text.count("laptopA") == 1
        assert len(json.loads(paths["json"].read_text(encoding="utf-8"))["entries"]) == 3
        assert fieldsync.command("what's the weather") is None
        assert "Not done" in fieldsync.command(f"field log import {tmp_path / 'nothing'}")

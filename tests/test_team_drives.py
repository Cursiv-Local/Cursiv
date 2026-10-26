"""U103: a research team on field drives, brought back to one main computer. Part of the mandatory USB
gate (python -m pytest -m usb), so it runs on every push, PR and release.

Each scientist has a Cursiv drive named for them. They record (with photos) on whatever PC is at hand,
the main computer included. The main computer takes the drives one at a time. Every entry and every
photo must arrive byte for byte, in that scientist's name; damage on a drive is refused whole and never
half-imported; a drive pulled mid-import leaves nothing half-written; importing again changes nothing;
the main computer's own notebook is never replaced; and a new drive carries only the scientists' work
someone chose. Only hardware is faked: folders stand in for the drives and the main computer."""
import csv
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from cursiv_engine.core import atomic, devicekey, fieldlog, fieldsync, paths

pytestmark = pytest.mark.usb


class Team:
    """Folders for the main computer and each drive; `at(place)` makes Cursiv run from that place."""

    def __init__(self, tmp: Path, monkeypatch):
        self.tmp = tmp
        self.place = {"home": tmp / "main" / "home", "root": None}
        monkeypatch.setattr(fieldlog, "log_dir", lambda: self.place["home"] / ".cursiv" / "fieldlog")
        monkeypatch.setattr(devicekey, "key_file", lambda: self.place["home"] / ".cursiv" / "device_key.json")
        monkeypatch.setattr(paths, "portable_root", lambda: self.place["root"])
        monkeypatch.setattr(fieldlog, "_last_share", -fieldlog.SHARE_EVERY_S)
        fieldlog._fresh_id.clear()

    def drive(self, name: str) -> Path:
        root = self.tmp / "drives" / name.replace(" ", "_")
        if not (root / "Home").exists():
            # What Make USB does for a drive named for one person (usb_ops.make_usb)
            fieldlog.name_new_notebook(root / "Home" / ".cursiv" / "fieldlog", name)
        return root

    @contextmanager
    def at(self, where):
        """where: "main" or a drive's root."""
        old = dict(self.place)
        if where == "main":
            self.place.update(home=self.tmp / "main" / "home", root=None)
        else:
            self.place.update(home=Path(where) / "Home", root=Path(where))
        try:
            yield
        finally:
            self.place.update(old)


@pytest.fixture
def team(tmp_path, monkeypatch):
    return Team(tmp_path, monkeypatch)


def _photo(tmp: Path, label: str) -> Path:
    p = tmp / "camera" / f"{label}.jpg"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xd8\xff\xe0" + hashlib.sha256(label.encode()).digest() * 40 + b"\xff\xd9")
    return p


def _record(team: Team, drive: Path, who: str, n: int, *, photo_every: int = 4, start: int = 0):
    with team.at(drive):
        for i in range(start, start + n):
            photos = [_photo(team.tmp, f"{who}-{i}")] if i % photo_every == 0 else None
            fieldlog.add(observer=who, site=f"Site {i % 5}", sample_id=f"{who[:2].upper()}-{i:04d}",
                         measurements=[{"name": "pH", "value": f"7.{i % 10}"},
                                       {"name": "water temp", "value": f"{12 + i % 9}.4", "unit": "°C"}],
                         note=f"{who}: observation {i} — façade, ñ, 雨", photos=photos)
        fieldsync.auto_share()                       # what Cursiv does when it quits on the drive


def _own_rows(team: Team, drive: Path) -> list[dict]:
    with team.at(drive):
        return fieldlog.entries()


def _snapshot(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


SCIENTISTS = ("Ana Ruiz", "Ben Okafor", "Cara Lindqvist")


def test_three_scientists_on_field_drives_arrive_in_their_names(team):
    with team.at("main"):
        fieldlog.set_name("Base station")
        fieldlog.add(observer="lead", note="season start")
        main_log = fieldlog.log_file().read_bytes()
    drives = {who: team.drive(who) for who in SCIENTISTS}
    for k, (who, d) in enumerate(drives.items()):
        _record(team, d, who, 6 + k)                 # a week on laptops in the field...
        _record(team, d, who, 2, start=50)           # ...and a day with the drive in the main computer itself
    with team.at("main"):
        for who, d in drives.items():                # plugged in one at a time
            r = fieldsync.import_folder(d)
            assert not r["rejected"] and not r["conflicts"] and not r["photos_missing"], r
            (nid, added), = r["added"].items()
            assert added == len(_own_rows(team, d)) and fieldlog.notebook_names()[nid] == who
            assert who in fieldsync.report_text(r)
        assert fieldlog.log_file().read_bytes() == main_log          # the main notebook is untouched
        names = fieldlog.notebook_names()
        for who, d in drives.items():                # every entry, byte for byte, in that scientist's name
            theirs = _own_rows(team, d)
            mine = fieldsync._read_lines(fieldsync.team_dir() / f"{theirs[0]['device']}.jsonl")
            assert mine == theirs and names[theirs[0]["device"]] == who
        for who, d in drives.items():                # and every photo
            for e in _own_rows(team, d):
                for rel in e["photos"]:
                    assert fieldlog.photo_path(rel).read_bytes() == (d / "Home" / ".cursiv" / "fieldlog" / rel).read_bytes()
        assert all(w in fieldsync.command("team log") for w in SCIENTISTS)
        paths_ = fieldsync.team_export(team.tmp / "export")
        rows = list(csv.DictReader(paths_["csv"].open(encoding="utf-8")))
        for who in SCIENTISTS:                       # the export says whose each row and photo is
            mine = [r for r in rows if r["observer"] == who]
            assert mine and {r["notebook_name"] for r in mine} == {who}
            assert any(r["photos"] for r in mine)
        before = _snapshot(fieldlog.log_dir())
        for d in drives.values():                    # bringing the same drives again changes nothing
            again = fieldsync.import_folder(d)
            assert not again["added"] and not again["rejected"]
        assert _snapshot(fieldlog.log_dir()) == before


def test_a_big_team_arrives_complete(team):
    drives = [team.drive(f"Scientist {i:02d}") for i in range(20)]
    for i, d in enumerate(drives):
        _record(team, d, f"Scientist {i:02d}", 60, photo_every=10)
    with team.at("main"):
        for d in drives:
            r = fieldsync.import_folder(d)
            assert not r["rejected"] and not r["conflicts"] and not r["photos_missing"]
        rows = fieldsync.team_entries()
        assert len(rows) == 20 * 60 and len({e["hash"] for e in rows}) == 20 * 60
        assert fieldsync.team_problems() == []
        expected = {e["hash"] for d in drives for e in _own_rows(team, d)}
        assert {e["hash"] for e in rows} == expected
        assert len(fieldlog.notebook_names()) == 20


@pytest.mark.parametrize("damage", ["changed entry", "cut off", "manifest missing", "manifest count", "garbage",
                                    "bad photo"])
def test_damage_on_a_drive_is_refused_whole(team, damage):
    good, bad = team.drive("Ana Ruiz"), team.drive("Ben Okafor")
    _record(team, good, "Ana Ruiz", 8)
    _record(team, bad, "Ben Okafor", 8)
    share = bad / fieldsync.SHARE_DIR
    (log,) = share.glob("*.jsonl")
    lines = log.read_text(encoding="utf-8").splitlines()
    if damage == "changed entry":
        e = json.loads(lines[3]); e["measurements"][0]["value"] = "9.9"; lines[3] = json.dumps(e)
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif damage == "cut off":
        data = log.read_bytes(); log.write_bytes(data[: len(data) // 2])
    elif damage == "manifest missing":
        log.with_name(log.stem + ".manifest.json").unlink()
    elif damage == "manifest count":
        m = log.with_name(log.stem + ".manifest.json"); d = json.loads(m.read_text(encoding="utf-8"))
        d["entries"] = 5; m.write_text(json.dumps(d), encoding="utf-8")
    elif damage == "garbage":
        log.write_bytes(b"\x00\x13not a field log\xff" * 50)
    elif damage == "bad photo":
        p = next(share.glob("photos/*")); p.write_bytes(p.read_bytes()[:-1] + b"\x00")
    with team.at("main"):
        for d in (good, bad):
            r = fieldsync.import_folder(d)
            if d == good:
                assert sum(r["added"].values()) == 8
        bens = fieldsync.team_dir() / f"{log.stem}.jsonl"
        if damage == "bad photo":
            assert r["photos_missing"] == {log.stem: 1}           # the entries arrive; the photo is named
            assert bens.exists() and fieldsync.team_problems() == []
            assert not any(fieldlog.photo_path(rel).exists() and
                           hashlib.sha256(fieldlog.photo_path(rel).read_bytes()).hexdigest() != Path(rel).stem
                           for e in fieldsync.team_entries() for rel in e["photos"])
        else:
            assert r["rejected"] and not bens.exists()            # refused whole: nothing of it here
        assert len([e for e in fieldsync.team_entries() if e["observer"] == "Ana Ruiz"]) == 8
    with team.at(bad):                                            # the drive shares again (its next start)
        fieldsync.auto_share()
    with team.at("main"):
        r = fieldsync.import_folder(bad)
        assert not r["rejected"] and not r["photos_missing"]
        assert len([e for e in fieldsync.team_entries() if e["observer"] == "Ben Okafor"]) == 8


def test_a_drive_pulled_mid_import_leaves_nothing_half_written(team, monkeypatch):
    drives = [team.drive(w) for w in SCIENTISTS]
    for w, d in zip(SCIENTISTS, drives):
        _record(team, d, w, 12)
    real, calls = atomic.write_bytes, {"n": 0}

    def pulled(path, data, **kw):
        calls["n"] += 1
        if calls["n"] == 7:
            raise OSError(5, "The device is not ready")              # the drive was pulled
        return real(path, data, **kw)
    with team.at("main"):
        monkeypatch.setattr(atomic, "write_bytes", pulled)
        with pytest.raises(OSError):
            for d in drives:
                fieldsync.import_folder(d)
        monkeypatch.setattr(atomic, "write_bytes", real)
        for f in fieldsync.team_dir().glob("*.jsonl"):              # whatever arrived is whole and checks out
            rows = fieldsync._read_lines(f)
            assert fieldsync.chain_problems(rows) == []
        assert not [p for p in fieldlog.log_dir().rglob("*") if p.name.endswith(".tmp")]
        for d in drives:                                            # plugged in again: it completes
            assert not fieldsync.import_folder(d)["rejected"]
        assert len(fieldsync.team_entries()) == 36 and fieldsync.team_problems() == []


def test_a_new_drive_carries_only_the_work_chosen(team):
    drives = {w: team.drive(w) for w in SCIENTISTS}
    for w, d in drives.items():
        _record(team, d, w, 5)
    with team.at("main"):
        for d in drives.values():
            fieldsync.import_folder(d)
        books = {b["name"]: b for b in fieldsync.notebooks_here()}
        assert set(SCIENTISTS) <= set(books)
        chosen = [books["Ana Ruiz"]["id"], books["Cara Lindqvist"]["id"]]
        new_drive = team.drive("Dee Park")
        copied = fieldsync.copy_notebooks_to(new_drive / "Home" / ".cursiv" / "fieldlog", chosen)
        assert copied == {chosen[0]: 5, chosen[1]: 5}
        assert fieldsync.copy_notebooks_to(new_drive / "Home" / ".cursiv" / "fieldlog", chosen) == {c: 0 for c in chosen}
    with team.at(new_drive):                                       # on the new drive: only Ana's and Cara's work
        names = set(fieldlog.notebook_names().values())
        assert names == {"Dee Park", "Ana Ruiz", "Cara Lindqvist"}
        rows = fieldsync.team_entries()
        assert {e["observer"] for e in rows} == {"Ana Ruiz", "Cara Lindqvist"} and len(rows) == 10
        assert all(fieldlog.photo_path(rel).exists() for e in rows for rel in e["photos"])
        assert fieldlog.identity()["name"] == "Dee Park"
        assert fieldlog.name_new_notebook(fieldlog.log_dir(), "Dee Park")["id"] == fieldlog.identity()["id"]


def test_bringing_a_drive_in_never_replaces_the_main_notebook(team):
    import usb_sync
    with team.at("main"):
        fieldlog.add(observer="lead", note="base")
    d = team.drive("Ana Ruiz")
    _record(team, d, "Ana Ruiz", 3)
    home = team.tmp / "main" / "home" / ".cursiv"
    items = usb_sync.plan_import(d / "Home" / ".cursiv", team.tmp / "main" / "app", home)
    notebook = [it for it in items if it["rel"].parts[0] == "fieldlog"]
    assert notebook and {it["action"] for it in notebook} == {"team"}
    assert "Ana Ruiz's field notebook goes to the team view" in usb_sync.describe_import(items)


def test_naming_a_notebook_keeps_its_work(team):
    with team.at("main"):
        fieldlog.add(observer="lead", note="first")
        nid = fieldlog.identity()["id"]
        assert "no name yet" in fieldsync.command("field log name")
        assert "now named Base station" in fieldsync.command('field log name "Base station"')
        assert fieldlog.identity()["id"] == nid and fieldlog.verify() == []      # the entries still check out
        assert "Not named" in fieldsync.command("field log name " + "x" * 61)
        fieldlog.add(observer="lead", note="second")
        assert {e["device"] for e in fieldlog.entries()} == {nid}

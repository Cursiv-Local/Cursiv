"""U102: the field notebook's integrity scenarios in one place (docs/NOTEBOOK-INTEGRITY.md).

Each test damages a notebook the way something real could (an edit, a deletion, a power cut, two
writers) and checks that Cursiv's own code -- never a model -- says exactly what's wrong, and that
nothing is lost or quietly repaired. Conflicting imports between devices are covered in
tests/test_fieldsync.py (test_different_history_keeps_both_and_chooses_neither and the shares tests).
"""
import json
import threading

import pytest

from cursiv_engine.core import fieldlog


@pytest.fixture
def book(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "fieldlog")
    for n, temp in enumerate(("14.2", "14.6", "13.9", "15.1"), 1):
        fieldlog.add(site="North Creek", sample_id=f"NC-{n}",
                     measurements=[{"name": "water temp", "value": temp, "unit": "C"}])
    return fieldlog.log_file()


def _lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def _write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_01_valid_records_verify(book):
    assert fieldlog.verify() == [] and len(fieldlog.entries()) == 4


def test_02_a_correction_keeps_the_original(book):
    original = fieldlog.entries()[1]
    fixed = fieldlog.correct(original["id"], "meter misread", measurements=[
        {"name": "water temp", "value": "14.8", "unit": "C"}])
    assert fieldlog.entries()[1] == original and fixed["corrects"] == original["id"]
    assert [e["id"] for e in fieldlog.current()].count(original["id"]) == 0 and fieldlog.verify() == []


def test_03_a_deleted_record_is_detected(book):
    lines = _lines(book)
    _write(book, lines[:1] + lines[2:])
    assert any("doesn't follow the entry before it" in p for p in fieldlog.verify())


def test_04_a_changed_observation_is_detected(book):
    lines = _lines(book)
    lines[1] = lines[1].replace('"14.6"', '"16.6"')
    _write(book, lines)
    assert any("was changed after it was recorded" in p for p in fieldlog.verify())


def test_05_reordered_records_are_detected(book):
    lines = _lines(book)
    lines[1], lines[2] = lines[2], lines[1]
    _write(book, lines)
    assert fieldlog.verify()


def test_06_a_duplicated_record_is_detected(book):
    lines = _lines(book)
    _write(book, lines[:2] + [lines[1]] + lines[2:])
    assert fieldlog.verify()


def test_07_a_broken_link_is_detected(book):
    lines = _lines(book)
    row = json.loads(lines[2])
    row["prev"] = "0" * 64
    lines[2] = json.dumps(row)
    _write(book, lines)
    problems = fieldlog.verify()
    assert any("doesn't follow" in p for p in problems) and any("was changed" in p for p in problems)


def test_08_an_interrupted_write_loses_only_that_entry_and_says_so(book):
    with book.open("a", encoding="utf-8") as f:
        f.write('{"schema":1,"id":"half-written","seq":5,')        # what a power cut leaves
    assert len(fieldlog.entries()) == 4
    assert any("isn't a complete entry" in p for p in fieldlog.verify())
    fieldlog.add(site="Mill Race", note="after the power cut")       # the next entry starts on a new line
    assert len(fieldlog.entries()) == 5 and fieldlog.entries()[-1]["site"] == "Mill Race"


def test_09_concurrent_writers_lose_nothing_and_keep_the_chain(book):
    errors = []

    def writer(n):
        try:
            for i in range(10):
                fieldlog.add(site=f"Plot {n}", note=f"reading {i}")
        except Exception as exc:          # noqa: BLE001 -- collected and asserted below
            errors.append(exc)
    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(fieldlog.entries()) == 44 and fieldlog.verify() == []
    assert [e["seq"] for e in fieldlog.entries()] == list(range(1, 45))


def test_10_corrupted_bytes_are_reported_not_read_as_empty(book):
    lines = _lines(book)
    lines[2] = "\x00\x07 garbage \x1b"
    _write(book, lines)
    assert len(fieldlog.entries()) == 3                                # the rest are still there
    assert any("line 3 isn't a complete entry" in p for p in fieldlog.verify())


def test_11_a_crash_mid_save_leaves_the_notebook_readable(book):
    # An atomic write that died before its swap leaves a hidden temporary file beside the log.
    (book.parent / f".{book.name}-crashed.tmp").write_text("partial", encoding="utf-8")
    assert len(fieldlog.entries()) == 4 and fieldlog.verify() == []


def test_13_an_export_verifies_and_a_changed_export_does_not(book, tmp_path):
    paths = fieldlog.export(tmp_path / "export")
    folder = paths["csv"].parent
    assert fieldlog.verify_export(folder) == []
    csv = paths["csv"]
    csv.write_text(csv.read_text(encoding="utf-8").replace("14.6", "16.6"), encoding="utf-8")
    assert fieldlog.verify_export(folder)


def test_14_a_fully_rewritten_chain_still_verifies_so_it_is_not_called_proof(book):
    """The limit, stated as a test: someone who rewrites EVERY entry and recomputes every fingerprint
    makes a chain that verifies. The chain shows nothing changed after it was chained, not who made it
    or that it was never rebuilt. That's what signed exports and shares (device keys) are for, and why
    Cursiv says "tamper-evident", never "tamper-proof"."""
    rows = fieldlog.entries()
    prev = fieldlog.GENESIS
    rebuilt = []
    for e in rows:
        e = dict(e, prev=prev)
        if e["sample_id"] == "NC-2":
            e["measurements"] = [{"name": "water temp", "value": "19.0", "number": 19.0, "unit": "C"}]
        e["hash"] = fieldlog._fingerprint(e)
        prev = e["hash"]
        rebuilt.append(json.dumps(e, ensure_ascii=False, separators=(",", ":")))
    _write(book, rebuilt)
    assert fieldlog.verify() == []          # the chain alone can't tell


def test_a_passing_check_says_what_it_does_and_does_not_show(book):
    out = fieldlog.command("field log check")
    assert out.startswith("All 4 entries are intact and in order.") and "doesn't show who made them" in out
    from cursiv_engine.core import notebook_tools
    assert "a signed export does" in notebook_tools.execute(notebook_tools.VERIFY, {}).render()

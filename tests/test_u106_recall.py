"""Beginner notebook retrieval is deterministic, scoped and read-only."""
from datetime import date, datetime, time
from pathlib import Path
import sys

import pytest

from cursiv_engine.core import field_recall, fieldlog, notebook_tools


class Monday(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 26)


@pytest.fixture
def notebook(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "synthetic-notebook")
    monkeypatch.setattr(field_recall, "date", Monday)
    rows = []
    for sample, site, measure, value, day, note in (
        ("WB-001", "Willow Basin", "water temp", "21.4", 25, "cloudy"),
        ("WB-002", "Willow Basin", "soil temp", "17.5", 25, "dry soil"),
        ("EM-001", "East Meadow", "water temp", "19.2", 25, "clear"),
        ("WB-003", "Willow Basin", "water temp", "22.0", 26, "clear"),
        ("WB-004", "Willow Basin", "water temp", "18.0", 20, "clear"),
    ):
        timestamp = datetime.combine(date(2026, 10, day), time(12)).astimezone().timestamp()
        with monkeypatch.context() as clock:
            clock.setattr(fieldlog.time, "time", lambda: timestamp)
            rows.append(fieldlog.add(sample_id=sample, site=site,
                measurements=[dict(name=measure, value=value, unit="C")], note="Synthetic fixture: " + note))
    assert fieldlog.verify() == []
    return {row["sample_id"]: row for row in rows}


def _answer(question):
    native = notebook_tools.command(question, [])
    return native.render() if native is not None else field_recall.command(question)


def test_frozen_beginner_queries_select_exact_records_without_writes(notebook):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bench" / "researcher"))
    from recall_cases import CASES
    before = fieldlog.log_file().read_bytes()
    for name, question, expected in CASES:
        answer = _answer(question)
        if expected is None:
            assert answer is None, (name, answer)
        else:
            assert answer is not None, name
            actual = sorted(sample for sample, row in notebook.items() if row["id"] in answer)
            assert actual == sorted(expected), (name, answer)
    assert fieldlog.log_file().read_bytes() == before


def test_native_notebook_read_keeps_dates_and_source_timestamps(notebook):
    result = notebook_tools.command("Show my field notebook from yesterday.", [])
    assert result.ok and result.filters["start"] == result.filters["end"] == "2026-10-25"
    assert {row["sample_id"] for row in result.records} == {"WB-001", "WB-002", "EM-001"}
    answer = result.render()
    assert "2026-10-25" in answer and "saved local record timestamps" in answer
    assert "Searched this field notebook" in answer
    assert notebook["WB-003"]["id"] not in answer


@pytest.mark.parametrize("weekday,day", [("Monday", 19), ("Tuesday", 20), ("Wednesday", 21),
    ("Thursday", 22), ("Friday", 23), ("Saturday", 24), ("Sunday", 25)])
def test_last_weekday_is_strictly_previous(notebook, weekday, day):
    filters = field_recall.filters_for_request(f"What did I record last {weekday}?")
    assert filters["start"] == filters["end"] == f"2026-10-{day}"


def test_site_measurement_sample_and_date_filters_combine(notebook):
    answer = _answer("Show water temperature at Willow Basin for sample WB-001 yesterday.")
    assert notebook["WB-001"]["id"] in answer
    assert all(row["id"] not in answer for sample, row in notebook.items() if sample != "WB-001")
    assert "site: Willow Basin" in answer and "measurement: water temperature" in answer


def test_unknown_site_is_not_replaced_with_a_nearby_site(notebook):
    answer = _answer("What was the water temperature at Willow yesterday?")
    assert "No matching" in answer
    assert all(row["id"] not in answer for row in notebook.values())
    assert "site: Willow" in answer


def test_soil_temperature_does_not_select_water_temperature(notebook):
    answer = _answer("What was the soil temperature at Willow Basin yesterday?")
    assert notebook["WB-002"]["id"] in answer
    assert all(row["id"] not in answer for sample, row in notebook.items() if sample != "WB-002")


@pytest.mark.parametrize("question", [
    "What did I record last month?", "Show my field notebook on Tuesday.",
    "Show my field notebook on 2026-02-31.",
])
def test_unresolved_or_invalid_date_asks_before_scanning(notebook, monkeypatch, question):
    monkeypatch.setattr(field_recall, "query", lambda **kw: pytest.fail("Ambiguous date must not scan all records"))
    answer = _answer(question)
    assert "date" in answer.lower() and "?" in answer


def test_iso_range_is_applied_by_both_native_read_routes(notebook):
    for question in ("Show my field notebook between 2026-10-20 and 2026-10-25.",
                     "What did I record between 2026-10-20 and 2026-10-25?"):
        answer = _answer(question)
        assert notebook["WB-004"]["id"] in answer and notebook["WB-003"]["id"] not in answer
        assert "2026-10-20 to 2026-10-25" in answer


@pytest.mark.parametrize("suffix,expected", [
    ("since 2026-10-25", {"WB-001", "WB-003"}),
    ("from 2026-10-20 to 2026-10-25", {"WB-001", "WB-004"}),
    ("between 2026-10-20 and 2026-10-25", {"WB-001", "WB-004"}),
])
def test_site_stops_before_iso_date_scope(notebook, suffix, expected):
    answer = _answer("What was the water temperature at Willow Basin " + suffix + "?")
    found = {sample for sample, row in notebook.items() if row["id"] in answer}
    assert found == expected
    assert "site: Willow Basin;" in answer


def test_sample_mentions_obey_every_requested_filter(notebook, monkeypatch):
    expected = None
    for sample, site, measure, day in (("WB-009", "Willow Basin", "water temp", 25),
        ("WB-010", "Willow Basin", "water temp", 26), ("EM-009", "East Meadow", "water temp", 25),
        ("WB-011", "Willow Basin", "soil temp", 25)):
        stamp = datetime.combine(date(2026, 10, day), time(12)).astimezone().timestamp()
        with monkeypatch.context() as clock:
            clock.setattr(fieldlog.time, "time", lambda: stamp)
            row = fieldlog.add(sample_id=sample, site=site,
                measurements=[dict(name=measure, value="15", unit="C")], note="Mentions missing sample WB-999")
            if sample == "WB-009":
                expected = row["id"]
    result = field_recall.query(sample="WB-999", site="Willow Basin", measure="water temperature",
                               start="2026-10-25", end="2026-10-25")
    assert not result["records"] and [row["id"] for row in result["mentions"]] == [expected]


def test_read_tool_filters_do_not_grant_paths_or_writes(notebook):
    result = notebook_tools.execute(notebook_tools.READ,
        dict(site="Willow Basin", measure="water temperature", start="2026-10-25", end="2026-10-25"))
    assert result.ok and [row["sample_id"] for row in result.records] == ["WB-001"]
    refused = notebook_tools.execute(notebook_tools.READ, dict(path="../elsewhere", site="Willow Basin"))
    assert not refused.ok and not refused.records


def test_dated_record_phrase_routes_with_exact_site_and_range(notebook):
    result = field_recall.request('Find records at Willow Basin from 2026-10-25 to 2026-10-26.')
    assert {row['sample_id'] for row in result['records']} == {'WB-001', 'WB-002', 'WB-003'}
    assert result['filters']['site'] == 'Willow Basin'
    assert result['filters']['start'] == '2026-10-25' and result['filters']['end'] == '2026-10-26'
    assert field_recall.request('Find records about classical music.') is None


def test_damaged_notebook_is_not_a_successful_native_read(notebook):
    with fieldlog.log_file().open("ab") as stream:
        stream.write(b'{"incomplete":')
    result = notebook_tools.command("Show my field notebook from yesterday.", [])
    assert not result.ok and not result.records
    assert "integrity problems" in result.render()

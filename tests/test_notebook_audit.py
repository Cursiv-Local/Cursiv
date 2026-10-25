"""U100 audit of the U99 test run: field-notebook writes, lookups, verification, IDs, corrections.

Each test reproduces a failure from the owner's transcript (2026-10-25)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "launcher"))

from cursiv_engine.core import fieldlog, notebook_proposals, notebook_tools


@pytest.fixture
def book(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path)
    return tmp_path


def _save(proposal):
    import chat_commands
    assert proposal is not None and proposal.ok, proposal and proposal.problems
    out = chat_commands.notebook_command(proposal.command, []) or chat_commands.handle_command(proposal.command, {}, [])
    return getattr(out, "text", out)


W001 = "Record field observation: ORION-742, sample W-001, 18.6°C, 12:40, site Willow Basin."


def test_codes_are_not_read_as_negative_measurements():
    # Was saved as measurements "ORION = -742" and "sample W = -1" with the rest of the sentence as a unit.
    f = fieldlog.parse("ORION-742, sample W-001, 18.6°C, 12:40, site Willow Basin.")
    assert f["sample_id"] == "W-001" and f["site"] == "Willow Basin"
    assert f["measurements"] == [{"name": "temperature", "value": "18.6", "unit": "°C"}]
    assert f["note"] == "ORION-742; 12:40"
    # The notebook's own syntax is unchanged.
    g = fieldlog.parse("site: North transect; water temp 12.4 C; pH 7.2; temp -1.5 C; 44.1234, -71.5678; note: turbid")
    assert [m["value"] for m in g["measurements"]] == ["12.4", "7.2", "-1.5"] and g["lat"] == 44.1234


def test_a_plain_words_record_gets_a_card_not_a_silent_save(book):
    assert notebook_tools.command(W001, []) is None          # no longer saved straight away
    card = notebook_proposals.record(W001)
    assert notebook_proposals.understood(card)
    assert card.card_lines() == ["sample: W-001", "site: Willow Basin", "temperature 18.6 °C",
                                 "note: ORION-742", "note: 12:40"]
    assert fieldlog.entries() == []                           # nothing until Save


def test_a_saved_record_is_found_by_sample_and_record_id(book):
    _save(notebook_proposals.record(W001))
    row = fieldlog.entries()[0]
    for ask in ("Show the exact stored observation for sample W-001.", f"field log entry {row['id']}"):
        import chat_commands
        out = chat_commands.notebook_command(ask, []) or chat_commands.handle_command(ask, {}, [])
        assert row["id"] in out.text and "18.6" in out.text, ask


def test_verify_reports_what_it_checked_and_never_verifies_nothing(book):
    _save(notebook_proposals.record(W001))
    out = notebook_tools.command("Verify the integrity of all ORION-742 field observations.", []).render()
    assert "SHA-256 chain verified" in out and "Records for ORION-742: 1" in out
    none = notebook_tools.command("Verify the integrity of all LYRA-208 field observations.", []).render()
    assert "No records mention LYRA-208, so nothing was checked for it." in none


def test_a_code_is_not_a_site_unless_the_person_said_so():
    # The model proposed "site: W-003" and "site: ORION-742".
    assert notebook_proposals.fix_details("site: W-003; water temp 17.4 °C",
                                          "Record W-003 with a water temperature of 17.4°C") == \
        "water temp 17.4 °C; note: W-003"
    assert "site: ORION-742" not in notebook_proposals.fix_details(
        "site: ORION-742; pH 7.3; sample: W-002", "Record sample W-002, pH 7.3, ORION-742.")
    assert notebook_proposals.fix_details("site: NC-12; pH 7", "log site NC-12, pH 7") == "site: NC-12; pH 7"


def test_corrections_append_and_keep_the_original(book):
    _save(notebook_proposals.record(W001))
    original = fieldlog.entries()[0]
    card = notebook_proposals.correction("Correct W-001 temperature from 18.6°C to 18.9°C without erasing the original.")
    assert card.ok and card.card_lines()[1] == "temperature: 18.6 → 18.9 °C"
    out = _save(card)
    assert "the original entry is unchanged" in out
    rows = fieldlog.entries()
    assert rows[0] == original and len(rows) == 2 and fieldlog.verify() == []
    assert rows[1]["corrects"] == original["id"] and rows[1]["measurements"][0]["value"] == "18.9"
    assert rows[1]["sample_id"] == "W-001" and "Correct W-001" in rows[1]["reason"]
    history = notebook_tools.command("Show the full correction history for W-001.", []).render()
    assert original["id"] in history and rows[1]["id"] in history and "corrects" in history


def test_a_correction_with_the_wrong_old_value_or_record_is_refused(book):
    _save(notebook_proposals.record(W001))
    assert "is 18.6, not 18.4" in notebook_proposals.correction(
        "Correct W-001 temperature from 18.4°C to 18.9°C").problems[0]
    assert "no record for W-009" in notebook_proposals.correction(
        "Correct W-009 temperature from 18.6°C to 18.9°C").problems[0]
    assert "no pH reading" in notebook_proposals.correction("Fix W-001 pH from 7 to 7.2").problems[0]
    assert len(fieldlog.entries()) == 1


def test_a_sample_only_mentioned_in_a_note_is_reported_as_such(book):
    _save(notebook_proposals.record("Record W-003, water temp 17.4 C"))
    out = notebook_tools.command("Show the full correction history for W-003.", []).render()
    assert "No record has sample ID W-003, but 1 mention it" in out


def test_records_with_a_project_keep_old_entries_byte_for_byte(book):
    fieldlog.add(site="Pond", note="old style")
    old = fieldlog.entries()[0]
    assert "project" not in old
    fieldlog.add(project="ORION-742", sample_id="W-1", note="new")
    assert fieldlog.entries()[0] == old and fieldlog.entries()[1]["project"] == "ORION-742"
    assert fieldlog.verify() == []
    with pytest.raises(ValueError):
        fieldlog.add(project="bad id!", note="x")

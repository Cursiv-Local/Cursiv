"""U101 starter profiles: markdown files that ship with Cursiv, reading only what code allows."""
import pytest

from cursiv_engine.agents import custom, profile_context
from cursiv_engine.core import fieldlog


@pytest.fixture(autouse=True)
def agents_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(custom, "DIR", tmp_path / "agents")
    return tmp_path


@pytest.fixture
def book(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, "log_dir", lambda: tmp_path / "notebook")
    return tmp_path


def test_five_starters_ship_and_read_only_what_is_allowed():
    rows = {s["name"]: s for s in custom.starters()}
    assert set(rows) == {"field", "checker", "report", "protocol", "writer"}
    assert rows["checker"]["reads"] == ["notebook"] and rows["protocol"]["reads"] == ["documents"]
    assert rows["writer"]["reads"] == [] and set(rows["report"]["reads"]) == {"notebook", "documents", "calculations"}
    for s in rows.values():
        assert set(s["reads"]) <= set(profile_context.READS) and s["title"] and len(s["job"]) > 80


def test_a_starter_is_used_until_the_person_makes_their_own(agents_dir):
    assert custom.load("checker")["starter"]
    assert "@checker" in custom.listing() and "Data checker" in custom.listing()
    assert "nothing to delete" in custom.delete("checker")
    custom.teach("checker", "our pH meter reads 0.1 high")
    own = custom.load("checker")
    assert not own.get("starter") and own["reads"] == ["notebook"] and own["knowledge"] == ["our pH meter reads 0.1 high"]
    assert [a["name"] for a in custom.everyone()].count("checker") == 1


def test_a_profile_can_never_be_given_more_than_reading(agents_dir):
    custom.save({"name": "sneaky", "job": "do anything", "knowledge": [], "reads": ["files", "notebook", "web"]})
    a = custom.load("sneaky")
    text, own = profile_context.context(a, "hello")
    assert "Field notebook" in text                          # notebook allowed, read only
    perms = custom.permissions_answer(custom.load("checker"))
    assert "read only" in perms and "cannot save, change, correct or delete anything" in perms


def test_the_data_checker_findings_are_worked_out_by_code(book):
    fieldlog.add(site="Pond", sample_id="P-1", measurements=[{"name": "water temp", "value": "14.2", "unit": "C"}])
    fieldlog.add(site="Pond", sample_id="P-1", measurements=[{"name": "pH", "value": "7.1", "unit": ""}])
    fieldlog.add(note="W-004", measurements=[{"name": "temperature", "value": "coldish", "unit": ""}])
    fieldlog.add(site="Creek", measurements=[{"name": "nitrate", "value": "2.1", "unit": ""}])
    found = profile_context.findings()
    assert any("Sample ID P-1 is used by 2" in f for f in found)
    assert any('"coldish", not a number' in f for f in found)
    assert any("nitrate 2.1 has no unit" in f for f in found)
    assert any("neither a site nor a sample ID" in f for f in found)
    assert not any("pH 7.1 has no unit" in f for f in found)          # pH has no unit by nature
    text, _ = profile_context.context(custom.load("checker"), "check my data")
    assert "Findings from Cursiv's checks (code, not the model)" in text and "integrity chain was verified" in text


def test_a_clean_notebook_is_not_called_correct(book):
    fieldlog.add(site="Pond", sample_id="P-1", measurements=[{"name": "water temp", "value": "14.2", "unit": "C"}])
    text, _ = profile_context.context(custom.load("checker"), "check my data")
    assert "found nothing" in text


def test_the_protocol_helper_never_falls_back_to_general_knowledge(monkeypatch):
    from cursiv_engine.core import documents
    monkeypatch.setattr(documents, "library", lambda: [{"name": "SOP.txt", "id": "x"}])
    monkeypatch.setattr(documents, "search", lambda q, **_: [])
    text, own = profile_context.context(custom.load("protocol"), "What's the holding time for nitrate?")
    assert own.startswith("Your imported documents don't cover that") and "no AI model" in own


def test_the_writer_reads_nothing():
    text, own = profile_context.context(custom.load("writer"), "Write a post about our creek cleanup")
    assert text == "" and own == ""


def test_profile_document_search_allows_word_endings(monkeypatch, tmp_path):
    from cursiv_engine.core import documents
    from cursiv_engine.core.documents import Passage
    monkeypatch.setattr(documents, "_passages", lambda: [Passage("x", "SOP.txt", 1,
        "Nitrate samples: preserved with sulfuric acid, the holding time is 28 days.")])
    q = "how long can I hold a nitrate sample?"
    assert documents.search(q) == []                      # the main chat's search is unchanged
    assert documents.search(q, stem=True)


def test_numbers_and_units_a_profile_adds_are_noted(book):
    fieldlog.add(site="Mill Race", sample_id="MR-1", measurements=[{"name": "nitrate", "value": "2.1", "unit": ""}])
    a = custom.load("report")
    supplied, _ = profile_context.context(a, "write a report")
    note = profile_context.answer_note("Mill Race nitrate was 2.1 mg/L, up from 1.4 last year.", supplied, a)
    assert "1.4" in note and "nitrate 2.1 was recorded with no unit, but the answer says 2.1 mg/L" in note
    assert profile_context.answer_note("Mill Race nitrate was 2.1 (no unit recorded).", supplied, a) == ""

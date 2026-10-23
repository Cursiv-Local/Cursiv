"""The field demo (core/demo.py): sample data apart from real records, marked as samples,
and the real notebook and documents back untouched afterwards."""
from pathlib import Path

import pytest

from cursiv_engine.core import demo, documents, fieldlog
from test_netgate import fresh  # noqa: F401  (fixture)


@pytest.fixture
def home(tmp_path, monkeypatch, fresh):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    documents._passages.cache = None
    yield tmp_path / "home"
    documents._passages.cache = None


def test_demo_is_sample_data_kept_apart_from_real_records(home):
    real = fieldlog.add(observer="Me", site="My real site", measurements=[{"name": "pH", "value": "7.0"}])
    out = demo.command("demo")
    assert "Field demo on" in out and "demo off" in out
    assert demo.active() and fieldlog.log_dir() == demo.root() / "fieldlog"
    rows = fieldlog.current()
    assert len(rows) == 6 and all(e["note"].startswith("SAMPLE DATA") for e in rows)
    assert real["id"] not in {e["id"] for e in fieldlog.entries()}
    assert any(e.get("corrects") for e in fieldlog.entries())                      # one correction, with a reason
    assert sum(1 for e in rows if e.get("sample_id")) == 3
    assert fieldlog.verify() == []
    found = documents.search("How long can our water samples stay on ice before they reach the lab?")
    assert found and "24 hours" in found[0].text and found[0].name.startswith("SAMPLE")
    assert "phosphorus" not in documents.prompt_block(found, False).lower()
    demo.command("demo off")
    assert not demo.active() and not demo.root().exists()
    assert [e["id"] for e in fieldlog.entries()] == [real["id"]] and fieldlog.verify() == []
    assert documents.library() == []


def test_loading_again_starts_fresh_and_questions_are_listed(home):
    demo.load()
    fieldlog.add(observer="x", note="extra")
    demo.load()
    assert len(fieldlog.current()) == 6
    assert "field report" in demo.questions_text()
    assert demo.command("demo off").startswith("Demo off")
    assert demo.command("demo off") == "The demo isn't on."
    assert demo.command("hello") is None

"""U100: each conversation keeps a short note so it can be picked up later."""
import pytest

from cursiv_engine.memory import session_notes as sn


@pytest.fixture(autouse=True)
def notes(tmp_path, monkeypatch):
    monkeypatch.setattr(sn, "DIR", tmp_path / "session_notes")
    sn._active.update(conv="", note="")
    yield tmp_path
    sn._active.update(conv="", note="")


HISTORY = [
    {"role": "user", "content": "I'm planning the North Creek survey before the freeze."},
    {"role": "assistant", "content": "Good plan. Mornings are best for consistent temperatures."},
    {"role": "user", "content": "log site: North Creek; sample ID: NC-1; water temp 14.2 C"},
    {"role": "assistant", "content": "Logged. Sample NC-1. Record 334001fca158 · fingerprint 788e5c19 · read-back matched · chain intact."},
    {"role": "user", "content": "remember Sam handles samples on Fridays"},
    {"role": "assistant", "content": "Saved to memory: Sam handles samples on Fridays Memory ID: a62afe5eab; saved and verified."},
]
MODEL = ("Goal: water samples at North Creek before the freeze\nDecided: sample mornings only\n"
         "Open: rainfall data for last week; check the cattle fence\nNext: log site 2 on Friday")


def test_done_comes_only_from_cursivs_records():
    done = sn.done_lines(HISTORY + [{"role": "assistant", "content": "I logged everything and saved your file."}])
    assert done == ["Logged to the field notebook: Sample NC-1 (record 334001fca158)",
                    "Saved to memory: Sam handles samples on Fridays"]


def test_a_note_is_written_kept_and_picked_up():
    note = sn.update("conv1", "North Creek survey", HISTORY, lambda m: MODEL, force=True)
    assert "Goal: water samples at North Creek before the freeze" in note
    assert "- Logged to the field notebook: Sample NC-1 (record 334001fca158)" in note
    assert "Next: log site 2 on Friday" in note
    # Never said in the conversation, so never written into the note (U100 review of the live model):
    assert "rainfall" not in note and "cattle fence" not in note
    assert "Decided:" not in note         # "mornings" was the assistant's suggestion, not a decision
    assert "summarised by the AI model" in note
    assert sn.load("conv1") == note
    assert sn.picking_up(note) == "Picking up: water samples at North Creek before the freeze — next: log site 2 on Friday"
    sn.set_active("conv1")
    assert "Where this conversation left off" in sn.prompt_block() and "NC-1" in sn.prompt_block()
    sn.set_active("")
    assert sn.prompt_block() == ""


def test_the_summary_is_kept_between_refreshes_and_done_stays_current():
    sn.update("conv1", "Survey", HISTORY, lambda m: MODEL, force=True)
    more = HISTORY + [{"role": "user", "content": "log site: Plot 2; water temp 13 C"},
                      {"role": "assistant", "content": "Logged. Sample P-2. Record 4e8a25ed4895 · fingerprint x."}]
    note = sn.update("conv1", "Survey", more, lambda m: (_ for _ in ()).throw(AssertionError("not asked")))
    assert "Goal: water samples at North Creek" in note and "record 4e8a25ed4895" in note


def test_a_failing_model_still_leaves_a_records_only_note():
    note = sn.update("conv2", "Survey", HISTORY, lambda m: (_ for _ in ()).throw(RuntimeError("down")), force=True)
    assert "Logged to the field notebook" in note and "summarised by the AI model" not in note


def test_notes_are_encrypted_like_conversations():
    from pathlib import Path
    from cursiv_engine.core import vault
    assert vault.covered(Path("session_notes/abc.md"))


def test_owner_invalidation_during_summary_does_not_save(notes):
    valid=[True]
    def ask(messages):
        valid[0]=False
        return MODEL
    assert sn.update('cancelled','Survey',HISTORY,ask,force=True,valid=lambda:valid[0])==''
    assert not sn.DIR.exists()


def test_summary_keeps_its_original_storage_destination(notes,monkeypatch):
    original=sn.DIR
    def ask(messages):
        monkeypatch.setattr(sn,'DIR',notes/'different-destination')
        return MODEL
    note=sn.update('captured','Survey',HISTORY,ask,force=True)
    assert sn.load('captured',folder=original)==note
    assert not sn.DIR.exists()

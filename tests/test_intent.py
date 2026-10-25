"""U99: conversational actions. The model only proposes one of Cursiv's own commands;
Cursiv checks it against the person's words, asks before changing anything, and runs it
through the native code that gives a receipt."""
import json

import pytest

from cursiv_engine.core import intent
from test_chat_rendering import panel  # noqa: F401  (the same headless chat panel)


def model(action, **slots):
    return lambda messages: json.dumps({"action": action, "slots": slots})


@pytest.mark.parametrize("text", [
    "Add a note that North Creek was 14.2 C and cloudy today",
    "jot down: south pond pH 6.4, algae at the edges",
    "remember that my truck's spare key is in the blue box",
    "work in my Field Data folder",
    "go offline for the rest of the day",
    "what did I log at North Creek yesterday?",
])
def test_actions_reach_the_model_step(text):
    assert intent.might_be_action(text)


@pytest.mark.parametrize("text", [
    "What is a riffle in a stream?",
    "Why do people keep field notebooks?",
    "Tell me a joke about data logging",
    "hi",
    "How do I purify creek water?",
])
def test_plain_chat_skips_the_model_step(text):
    assert not intent.might_be_action(text)


def test_a_clean_log_proposal_needs_a_yes():
    said = "Add a note that North Creek was 14.2 C and cloudy today"
    p = intent.propose(said, model("notebook.log", details="site: North Creek; water temp 14.2 C; note: cloudy"))
    assert p.ok and p.needs_confirm and p.command == "log site: North Creek; water temp 14.2 C; note: cloudy"
    assert p.card_lines() == ["site: North Creek", "water temp 14.2 C", "note: cloudy"]


@pytest.mark.parametrize("action,slots,problem", [
    ("notebook.log", {"details": "site: North Creek; water temp 15.0 C"}, "the number 15.0"),
    ("notebook.log", {"details": "site: East Fork; water temp 14.2 C"}, "site name"),
    ("file.append", {"path": "secrets.txt", "text": "14.2"}, "file name"),
    ("file.append", {"path": "notes.txt", "text": "Site Z, 99 C"}, "number 99"),
    ("workspace.set", {"folder": "C:\\Windows"}, "folder"),
    ("memory.save", {"fact": "the person prefers dangerous shortcuts"}, "isn't what you said"),
    ("notebook.average", {"kind": "sum", "measure": "water temp", "scope": "TEST"}, "calculation"),
])
def test_invented_details_are_never_offered(action, slots, problem):
    said = "Add a note that North Creek was 14.2 C and cloudy today, put it in notes.txt, remember I like rice"
    p = intent.build(action, slots, said)
    assert not p.ok and any(problem in x for x in p.problems), p.problems


def test_none_unknown_or_broken_replies_are_ignored():
    said = "log the creek reading 14.2 C"
    assert intent.propose(said, model("none")) is None
    assert intent.propose(said, model("delete.everything")) is None
    assert intent.propose(said, lambda m: "not json at all") is None
    assert intent.propose(said, lambda m: (_ for _ in ()).throw(RuntimeError("model down"))) is None


def test_paths_outside_the_workspace_are_refused():
    p = intent.build("file.read", {"path": "../secrets.bat"}, "read ../secrets.bat")
    assert not p.ok and "only files inside your workspace" in p.problems


# ── in the chat window ──────────────────────────────────────────────────────

def _turn(panel, monkeypatch, text, proposal):
    import chat_commands
    import chat_panel
    monkeypatch.setattr(chat_panel, "cc", chat_commands, raising=False)
    monkeypatch.setattr(panel, "_propose_action", lambda t: proposal)
    panel._reply_is_chat = False
    panel._run_turn(text, [])
    from PyQt6.QtWidgets import QApplication
    QApplication.processEvents()


def test_a_change_waits_on_the_card_and_save_runs_the_real_command(panel, monkeypatch, tmp_path):
    import chat_commands as cc
    said = "Add a note that North Creek was 14.2 C and cloudy today"
    proposal = intent.build("notebook.log", {"details": "site: North Creek; water temp 14.2 C; note: cloudy"}, said)
    ran = []
    monkeypatch.setattr(cc, "notebook_command", lambda text, *a, **k: ran.append(text) or None)
    monkeypatch.setattr(cc, "memory_command", lambda *a, **k: None)
    monkeypatch.setattr(cc, "handle_command", lambda *a, **k: None)
    _turn(panel, monkeypatch, said, proposal)
    assert ran == [said]                                # only the plain words reached the native check
    text = panel._transcript.toPlainText()
    assert "Save to your field notebook?" in text and "Runs: log site: North Creek" in text
    key = next(iter(panel._intents))
    monkeypatch.setattr(panel, "_begin_turn", lambda *a: None)
    started = []
    monkeypatch.setattr("threading.Thread", lambda target, args, daemon: type(
        "T", (), {"start": lambda self: started.append(args)})())
    panel._answer_intent("save", key)
    assert started and started[0][0] == "log site: North Creek; water temp 14.2 C; note: cloudy"
    assert started[0][2] is False                       # the confirmed command is not re-interpreted
    panel._answer_intent("save", key)                   # a second click does nothing
    assert len(started) == 1


def test_cancel_changes_nothing(panel, monkeypatch):
    proposal = intent.build("offline.on", {}, "go offline for the day")
    import chat_commands as cc
    for name in ("notebook_command", "memory_command", "handle_command"):
        monkeypatch.setattr(cc, name, lambda *a, **k: None)
    _turn(panel, monkeypatch, "go offline for the day", proposal)
    key = next(iter(panel._intents))
    panel._answer_intent("cancel", key)
    assert "Cancelled. Nothing was changed." in panel._transcript.toPlainText()


def test_an_unchecked_proposal_offers_only_edit(panel, monkeypatch):
    proposal = intent.build("notebook.log", {"details": "site: North Creek; water temp 15.0 C"},
                            "North Creek was 14.2 C")
    import chat_commands as cc
    for name in ("notebook_command", "memory_command", "handle_command"):
        monkeypatch.setattr(cc, name, lambda *a, **k: None)
    _turn(panel, monkeypatch, "North Creek was 14.2 C", proposal)
    text = panel._transcript.toPlainText()
    assert "Nothing was saved" in text and "the number 15.0 isn't in what you wrote" in text
    html = panel._transcript.toHtml()
    assert "cursiv://intent/edit/" in html and "cursiv://intent/save/" not in html


def test_folder_names_become_real_paths(tmp_path, monkeypatch):
    (tmp_path / "Documents" / "Field Data").mkdir(parents=True)
    (tmp_path / "Desktop").mkdir()
    monkeypatch.setenv("CURSIV_REAL_HOME", str(tmp_path))
    p = intent.build("workspace.set", {"folder": "Field Data"}, "work in my Field Data folder")
    assert p.ok and p.command == f"workspace {tmp_path / 'Documents' / 'Field Data'} and files on"
    missing = intent.build("workspace.set", {"folder": "Nowhere"}, "work in my Nowhere folder")
    assert not missing.ok and "couldn't find a folder" in missing.problems[0]


def test_workspace_and_files_on_in_one_confirmed_command(tmp_path, monkeypatch):
    import chat_commands as cc
    from cursiv_engine.core import workspace
    monkeypatch.setattr(workspace, "config_file", lambda: tmp_path / "workspace_access.json")
    folder = tmp_path / "Field Data"
    folder.mkdir()
    cfg = cc._default_cfg()
    out = cc.handle_command(f"workspace {folder} and files on", cfg, []).text
    assert "File access → ON" in out and cfg["file_access"] is True and cfg["workspace"].endswith("Field Data")


def test_split_observation_keys_are_put_back_together():
    said = "Willow Spring 10.2 C, cattle tracks nearby"
    p = intent.build("notebook.log", {"site": "Willow Spring", "measurement": "water temp", "value": 10.2,
                                      "unit": "C", "note": "cattle tracks nearby"}, said)
    assert p.ok and p.command == "log site: Willow Spring; water temp 10.2 C; note: cattle tracks nearby"


def test_prompt_examples_are_not_copied_from_the_test_set():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench" / "intent"))
    from phrasings import CASES
    for text, _, _ in CASES:
        assert f'"{text}"' not in intent.PROMPT, text


def test_forget_needs_a_request_to_forget():
    assert not intent.build("memory.forget", {"words": "things a lot lately"}, "I forget things a lot lately").ok
    assert intent.build("memory.forget", {"words": "gate code"}, "delete the memory about the gate code").ok
    assert intent.build("memory.forget", {"words": "bee sting"}, "you can forget the bee sting thing").ok


def test_a_trailing_full_stop_is_not_a_changed_text():
    p = intent.build("file.create", {"path": "summary.md", "text": "Survey went well."},
                     "create summary.md saying Survey went well")
    assert p.ok

"""Cursiv looking at itself: its own source, its last answer's real instructions, its stores.

Everything here is read-only and application-authored; answers about itself are
grounded in labelled evidence instead of a guess.
"""
import pytest

from cursiv_engine.core import last_turn, self_source, self_stores, selfknow


@pytest.fixture(autouse=True)
def _fresh_record():
    last_turn.clear()
    yield
    last_turn.clear()


# ── source ─────────────────────────────────────────────────────────────────

def test_source_search_and_read_are_labelled():
    hits = self_source.search("drop_false_refusal")
    assert any(h["path"] == "cursiv_engine/chat/response_style.py" for h in hits)
    where, body = self_source.read("cursiv_engine/core/last_turn.py", 1, 5)
    assert where.startswith("Read from Cursiv's own source") and "last_turn.py, lines 1–5" in where
    assert body.splitlines()[0].strip().startswith("1")


@pytest.mark.parametrize("path", ["../secrets.bat", "cursiv_engine/../secrets.bat", "C:/Windows/win.ini",
                                  ".cursiv/config.json", "tests/conftest.py", "secrets.bat",
                                  "cursiv_engine/licenses/Cursiv-LICENSE.txt"])
def test_only_cursivs_own_source_can_be_read(path):
    with pytest.raises(ValueError):
        self_source.read(path)


def test_excerpts_stay_within_budget():
    text = self_source.excerpts("memory matched to the question", budget=400)
    assert text and len(text) < 700 and "Cursiv's own source" in text


# ── last answer record ─────────────────────────────────────────────────────

def _fake_local(monkeypatch, seen):
    from cursiv_engine.ui import chat_app as ca
    from test_netgate import _local_model
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", lambda messages, **kw: seen.append(messages) or iter(["Done."]))
    return ca


def test_last_answer_is_recorded_in_memory_and_shown(monkeypatch):
    import chat_commands as cc
    seen = []
    ca = _fake_local(monkeypatch, seen)
    "".join(ca.chat("What is a good way to store field samples?", [], "", None))
    record = last_turn.get()
    names = [b["name"] for b in record["assembled"]]
    assert any("persona" in n for n in names) and "What is a good way" in record["question"]
    shown = cc.handle_command("self prompt", cc._default_cfg(), []).text
    assert "kept in memory only" in shown and "Cursiv's persona and rules" in shown


def test_a_question_about_the_last_answer_sees_that_answer(monkeypatch):
    seen = []
    ca = _fake_local(monkeypatch, seen)
    "".join(ca.chat("What is a good way to store field samples?", [], "", None))
    first_blocks = [b["name"] for b in last_turn.get()["assembled"]]
    "".join(ca.chat("Why did you answer that way?", [], "", None))
    system = seen[-1][0]["content"]
    assert "The record of your last answer" in system
    assert first_blocks[0] in system           # the previous answer's blocks, not this turn's
    assert "say plainly that you can't see it" in system


def test_self_prompt_before_any_answer():
    assert "No answer has been recorded" in last_turn.summary()


# ── stores ─────────────────────────────────────────────────────────────────

def test_stores_inventory_counts_without_changing_anything():
    from cursiv_engine.memory import semantic
    semantic.add_fact("Dana's sister is called Mia.", "dana", "manual")
    before = semantic.FACTS_FILE.read_bytes()
    text = self_stores.summary("dana")
    assert "Memories about you**: 1 (1 you said or saved, 0 inferred by Cursiv)" in text
    assert "Saved notes" in text and "nothing reads it back into answers" in text
    assert semantic.FACTS_FILE.read_bytes() == before


# ── privacy wording ────────────────────────────────────────────────────────

def test_privacy_is_stated_as_current_facts_not_a_promise():
    from cursiv_engine.core import speed
    from cursiv_engine.ui import chat_app as ca
    compact = speed.compact_persona(ca.SYSTEM_PROMPT_FILE)
    full = ca.SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    for text in (compact, full, selfknow.SELF_PROMPT):
        assert "Never promise" in text
    assert "their data stays on their computer" not in full


def test_self_questions_include_why_and_how():
    for q in ("Why did you refuse that?", "How do you remember things?", "Can you look at your own source code?"):
        assert selfknow.is_self_question(q), q


def test_file_tools_are_not_offered_without_a_workspace():
    from cursiv_engine.core import tools
    offered = []
    def ask(messages):
        offered.append(messages[0]["content"])
        return '{"calls": [{"tool": "system_info", "args": {}}, {"tool": "list_folder", "args": {"path": "."}}]}'
    calls = tools.plan("Does anything I type here leave my computer?", ask, files=False)
    assert [c["tool"] for c in calls] == ["system_info"]
    assert "list_folder" not in offered[0] and "read_file" not in offered[0]
    assert "list_folder" in [c["tool"] for c in tools.plan("list my workspace", ask, files=True)]


@pytest.mark.parametrize("question", ["Does anything I type here leave my computer?", "Is my data private?",
                                      "Where does my data go?", "Do my messages get sent to the cloud?"])
def test_privacy_questions_get_the_live_application_answer(question, monkeypatch):
    from cursiv_engine.chat import keys, status
    from cursiv_engine.ui import chat_app as ca
    monkeypatch.setattr(status.netgate, "is_offline", lambda: False)
    monkeypatch.setattr(keys, "saved_key", lambda field: "x" if field == "groq_key" else "")
    monkeypatch.setattr(ca, "_call_ollama", lambda *a, **k: pytest.fail("a privacy question must not reach a model"))
    out = "".join(ca.chat(question, [], "", None))
    assert "Can go online:" in out and "Groq" in out and "no AI model" in out
    assert "stored in files on this computer" in out


@pytest.mark.parametrize("question", ["Can you send this paragraph to my printer?", "Will the package leave the warehouse today?"])
def test_ordinary_questions_are_not_privacy_questions(question):
    from cursiv_engine.chat import status
    assert not status.answers_network_question(question)


def test_how_memory_works_is_answered_from_reviewed_facts_but_recall_is_not():
    from cursiv_engine.core import feature_answers
    answer = feature_answers.answer("How do you remember things about me?")
    assert "persistent local memory across restarts" in answer and "files on this computer" in answer
    assert feature_answers.answer("Do you remember what I said about soil?") is None

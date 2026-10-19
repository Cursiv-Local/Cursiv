"""Cross-Check (core/crosscheck.py, launcher/crosscheck_dialog.py, the Cross-check button in
launcher/chat_panel.py): another AI reviews one answer, only on request, after the person sees
exactly what goes where. No real provider is called in these tests: the provider call is replaced
by a recorder, and any other outside connection is refused by test_netgate's harness."""
import pytest
from PyQt6.QtWidgets import QApplication, QDialog

from cursiv_v215.core import crosscheck, netgate
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)

QUESTION = "How long can water samples stay on ice before the lab?"
ANSWER = ("Keep them at 4 °C and get them to the lab within 24 hours.\n\n"
          "*(From Cursiv's offline reference, water purification [survival/water-purification]: ...)*\n\n"
          "*[Sources: Cursiv Offline Reference (water purification). Wording by the AI model]*\n"
          "*[Answered by Ollama · qwen3:4b-instruct]*")
PRIVATE = "PRIVATE-MEMORY: the safe code is 4417"


class Recorder:
    """Stands in for a provider: records what it was sent, replies with `reply`."""
    def __init__(self, reply="1. Verifiable errors: None\n5. Overall: fine.", raise_exc=None):
        self.calls, self.reply, self.raise_exc = [], reply, raise_exc

    def __call__(self, messages, key):
        self.calls.append((messages, key))
        if self.raise_exc:
            raise self.raise_exc
        yield from [self.reply]


@pytest.fixture
def keys(tmp_path, monkeypatch):
    """No saved keys unless a test gives one in cfg; offline mode off (a fresh install)."""
    from cursiv_v215.chat import keys as k
    monkeypatch.setattr(netgate, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(k, "KEYS_FILE", tmp_path / "config.json")
    return {"anthropic_key": "sk-test-not-real"}


# ── 1. what goes to the reviewer: exactly the question and the answer ─────────────

def test_the_reviewer_gets_the_question_and_the_answers_own_words_only(keys):
    p = crosscheck.build("claude", QUESTION, ANSWER)
    rec = Recorder()
    r = crosscheck.review(p, cfg=keys, call=rec)
    assert r.ok and "Overall: fine" in r.text
    (messages, key), = rec.calls
    assert key == "sk-test-not-real"
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[0]["content"] == crosscheck.REVIEW_INSTRUCTION
    sent = messages[1]["content"]
    assert QUESTION in sent and "within 24 hours" in sent
    assert "Answered by" not in sent and "Sources:" not in sent      # Cursiv's own status lines stay here
    assert p.preview() == f"[Instructions to the reviewer]\n{messages[0]['content']}\n\n{sent}"   # preview == sent


def test_the_instruction_asks_for_the_four_kinds_and_no_rewrite():
    for part in ("Verifiable errors", "Unsupported claims", "Missing assumptions", "Differences in interpretation",
                 "must not rewrite the answer"):
        assert part in crosscheck.REVIEW_INSTRUCTION


def test_a_long_answer_is_cut_and_the_preview_says_so():
    p = crosscheck.build("openai", QUESTION, "x" * 20000)
    assert p.trimmed and len(p.user) < crosscheck.MAX_CHARS + 200 and "was not sent" in p.user


# ── 2/3. nothing is sent without the person asking and confirming ────────────────

_APP = []                                     # the QApplication must outlive every panel


@pytest.fixture
def panel(keys, monkeypatch):
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    import chat_panel
    from cursiv_v215.chat import status
    monkeypatch.setattr(status, "local_models", lambda timeout=2.0: ["qwen3:4b-instruct"])
    p = chat_panel.ChatPanel()
    p._cfg.update(keys)
    p._history = [{"role": "user", "content": "earlier: " + PRIVATE},
                  {"role": "assistant", "content": "noted"},
                  {"role": "user", "content": QUESTION}, {"role": "assistant", "content": ANSWER}]
    p._last_exchange = (QUESTION, ANSWER)
    p._streaming = False
    yield p
    p.deleteLater()


def _no_send(monkeypatch):
    sent = []
    monkeypatch.setattr(crosscheck, "review", lambda payload, cfg=None, call=None: sent.append(payload) or
                        crosscheck.Review(True, payload.provider, payload.to, "review"))
    return sent


def test_cancelling_the_confirmation_sends_nothing(panel, monkeypatch):
    import crosscheck_dialog
    sent = _no_send(monkeypatch)
    monkeypatch.setattr(crosscheck_dialog.CrossCheckDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    panel._cross_check()
    assert sent == []


def test_confirming_sends_only_the_last_question_and_answer(panel, monkeypatch):
    import crosscheck_dialog
    import threading
    sent = _no_send(monkeypatch)
    monkeypatch.setattr(crosscheck_dialog.CrossCheckDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(threading, "Thread", lambda target, daemon=None: type("T", (), {"start": lambda s: target()})())
    panel._cross_check()
    (payload,) = sent
    assert QUESTION in payload.user and PRIVATE not in payload.preview() and "earlier:" not in payload.preview()


def test_a_normal_chat_turn_never_calls_a_reviewer(fresh, outbound, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    _local_model(monkeypatch, reply="Within 24 hours, on ice.")
    monkeypatch.setattr(crosscheck, "review", lambda *a, **k: pytest.fail("a review was sent"))
    monkeypatch.setattr(ca, "_call_claude_direct", lambda *a, **k: pytest.fail("Claude was called"))
    out = "".join(ca.chat(QUESTION, [], "", None))                 # a normal local turn
    assert "24 hours" in out and outbound == []


def test_the_button_waits_for_a_finished_answer(panel):
    panel._begin_turn()
    assert not panel._cc_btn.isEnabled() and panel._last_exchange is None


# ── 4. no key: explained, nothing sent ──────────────────────────────────────────

def test_no_key_means_no_provider_and_a_plain_message(keys, monkeypatch):
    from cursiv_v215.chat import keys as k
    monkeypatch.setattr(k, "saved_key", lambda field: "")
    assert crosscheck.available({}) == []
    rec = Recorder()
    r = crosscheck.review(crosscheck.build("groq", QUESTION, ANSWER), cfg={}, call=rec)
    assert not r.ok and "No Groq (free key) key is saved, so nothing was sent" in r.text and rec.calls == []
    assert crosscheck.available(keys) == [("claude", "Anthropic (Claude)")]


def test_offline_mode_refuses_and_sends_nothing(keys):
    netgate.set_offline(True)
    rec = Recorder()
    r = crosscheck.review(crosscheck.build("claude", QUESTION, ANSWER), cfg=keys, call=rec)
    assert not r.ok and r.text.startswith("Nothing was sent.") and "Offline mode is on" in r.text
    assert rec.calls == []


# ── 5. provider trouble never touches the answer ───────────────────────────────

@pytest.mark.parametrize("rec,phrase", [
    (Recorder(reply="\n[Claude error 401: invalid x-api-key]"), "returned an error"),
    (Recorder(reply=""), "empty reply"),
    (Recorder(raise_exc=TimeoutError("timed out")), "didn't answer (TimeoutError)"),
    (Recorder(reply="<<<RATE_LIMIT_EXHAUSTED>>>"), "rate-limiting"),
])
def test_provider_failures_become_a_plain_not_done(keys, rec, phrase):
    r = crosscheck.review(crosscheck.build("claude", QUESTION, ANSWER), cfg=keys, call=rec)
    assert not r.ok and phrase in r.text


def test_a_review_or_a_failure_is_added_below_and_changes_nothing_else(panel):
    panel._transcript.setPlainText(QUESTION + "\n" + "Keep them at 4 °C and get them to the lab within 24 hours.")
    before_history = [dict(m) for m in panel._history]
    panel._on_cross_check(crosscheck.Review(False, "claude", "Anthropic (Claude)", "Anthropic (Claude) returned an "
                                                                                   "error: [Claude error 401]."))
    panel._on_cross_check(crosscheck.Review(True, "claude", "Anthropic (Claude)", "1. Verifiable errors: None"))
    text = panel._transcript.toPlainText()
    assert "within 24 hours" in text                                   # the answer is still there
    assert "Cross-check with Anthropic (Claude): not done" in text
    assert "a second opinion to weigh, not a verdict" in text
    assert panel._history == before_history                            # not added to the conversation

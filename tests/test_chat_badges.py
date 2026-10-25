"""U98 chat look: Cursiv's own answers, model answers and notices look different."""
import chat_badges as cb
from test_chat_rendering import panel  # noqa: F401  (the same headless chat panel)


def test_worked_by_cursiv_badge_says_no_model():
    html = cb.badge("Sources: Cursiv calculation (units; no AI model)")
    assert "✓" in html and "Worked out by Cursiv · units" in html and "no AI model" in html
    assert cb.worked_by_cursiv("Sources: your field notebook, calculated by Cursiv (no AI model)")
    assert not cb.worked_by_cursiv("Sources: Your documents (x.pdf p. 1). Wording by the AI model")


def test_model_badges_keep_their_labels():
    assert "Local · qwen3:4b-instruct" in cb.badge("Answered by Ollama · qwen3:4b-instruct")
    assert "Online · OpenAI" in cb.badge("Answered by OpenAI")
    assert "⚠" in cb.badge("Cursiv's check: the answer contradicts the calculation")


def test_notebook_save_becomes_a_receipt_with_its_own_words():
    text = "Logged. Sample TEST-1. Record 334001fca158 · fingerprint 788e5c190136 · read-back matched · chain intact."
    html = cb.receipt(text)
    assert "Saved to your field notebook" in html
    for part in ("Sample TEST-1", "Record 334001fca158", "read-back matched", "chain intact"):
        assert part in html
    assert cb.receipt("Just some command output") is None


def test_first_offline_is_celebrated_once(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "moments_file", lambda: tmp_path / "ui_moments.json")
    assert cb.seen_once("offline_celebrated") is False
    assert cb.seen_once("offline_celebrated") is True
    html = cb.receipt("Offline mode ON — Cursiv won't connect…", first_offline=True)
    assert "Offline mode is on" in html and "First time offline" in html
    assert "First time offline" not in cb.receipt("Offline mode ON — …")


def test_problems_are_plain_and_say_what_to_do():
    html = cb.problem("HTTPConnectionPool(host='localhost', port=11434): Connection refused")
    assert "local AI engine isn't running" in html and "cursiv://setup" in html and "Detail:" in html
    assert "didn't accept the key" in cb.problem("Error code: 401 - invalid api key")
    other = cb.problem("KeyError: 'x'")
    assert "Something went wrong" in other and "cursiv://report" in other


def test_starters_cover_the_core_jobs():
    html = cb.starters(lambda t: "cursiv://prompt/" + t)
    for title in ("Field notes", "Calculations", "Your documents", "Offline"):
        assert title in html
    assert html.count("cursiv://prompt/") == 4


def test_tour_shows_after_the_first_model_answer_only(panel):
    panel._on_chunk("Hello.\n\n*[Answered by Ollama · test-model]*")
    panel._on_done()
    assert "A few things to try next" in panel._transcript.toPlainText()
    panel._begin_turn("again")
    panel._reply_is_chat = True
    panel._on_chunk("Again.\n\n*[Answered by Ollama · test-model]*")
    panel._on_done()
    assert panel._transcript.toPlainText().count("A few things to try next") == 1


def test_command_receipt_renders_as_card_in_the_panel(panel):
    panel._reply_is_chat = False             # a command result, not a model answer
    panel._on_chunk("Logged. Sample A-1. Record abc · fingerprint def · read-back matched · chain intact.")
    panel._on_done()
    text = panel._transcript.toPlainText()
    assert "Saved to your field notebook" in text and "Sample A-1" in text

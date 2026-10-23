"""A revised answer replaces the draft in the chat window and history (AUDIT C-007)."""
from types import SimpleNamespace

from test_verify import _ledger


def _revising(monkeypatch):
    from cursiv_engine.core import speed
    monkeypatch.setattr(speed, 'battery_saver', lambda: False)  # explicitly exercise the optional review
    from cursiv_engine.ui import chat_app as ca

    def fake_stream(message, history, api_key, files, file_access, root_path, openai_key,
                    confirm_writes, anthropic_key, force_provider, reply):
        for chunk in ("Set the retry limit to 5 retries.", "\n\n*[Answered by Ollama · qwen3:4b]*"):
            reply.append(chunk)
            yield chunk

    def ask(messages, max_tokens=400):
        if messages[0]["content"].startswith("Rewrite"):
            return "The retry limit is exactly 3 retries.\n\n" + _ledger()
        return "CLEAR"

    learned = {}
    # This fake stream bypasses _chat_stream's normal per-turn reset.
    monkeypatch.setattr(ca, "_WORKED", None)
    from cursiv_engine.chat import review
    monkeypatch.setattr(review, 'mode', lambda: 'full')  # explicitly exercise legacy bounded rewrite behavior
    monkeypatch.setattr(ca, "_chat_stream", fake_stream)
    monkeypatch.setattr(ca, "_router_llm", ask)
    monkeypatch.setattr(ca, "_learn_later", lambda message, reply, **kw: learned.update(reply=reply, **kw))
    return ca, learned


def test_window_gets_one_replacement_with_the_footer(monkeypatch):
    ca, learned = _revising(monkeypatch)
    chunks = list(ca.chat("The retry limit is exactly 3 retries. Is this correct?", [], "", None,
                          replace_draft=True))
    final = [c for c in chunks if c.startswith(ca.REPLACE_SENTINEL)]
    assert len(final) == 1
    text = final[0][len(ca.REPLACE_SENTINEL):]
    assert text.startswith("The retry limit is exactly 3 retries.")
    assert "5 retries" not in text.split("Revised after a check")[0]
    assert "Revised after a check" in text and "Answered by Ollama" in text
    assert "Set the retry limit to 5" not in learned["reply"]       # learning sees only the final answer


def test_other_callers_still_get_the_appended_revision(monkeypatch):
    ca, _ = _revising(monkeypatch)
    out = "".join(ca.chat("The retry limit is exactly 3 retries. Is this correct?", [], "", None))
    assert ca.REPLACE_SENTINEL not in out and "Revised after check" in out


def test_chat_panel_swaps_the_draft_in_place():
    from PyQt6.QtWidgets import QApplication, QTextEdit
    from PyQt6.QtGui import QTextCursor
    import chat_panel
    app = QApplication.instance() or QApplication([])
    view = QTextEdit()
    view.setPlainText("You: question\nCursiv: ")
    cursor = QTextCursor(view.document())
    cursor.movePosition(QTextCursor.MoveOperation.End)
    panel = SimpleNamespace(_transcript=view, _reply_start=cursor.position(), _reply_text="")
    cursor.insertText("draft with a mistake")
    chat_panel.ChatPanel._on_replace(panel, "the checked answer")
    assert view.toPlainText() == "You: question\nCursiv: the checked answer"
    assert panel._reply_text == "the checked answer"
    assert app is not None


def test_check_notes_are_short_and_plain():
    from types import SimpleNamespace
    from cursiv_engine.ui import chat_app as ca
    raw = ("- **Unsupported Claims:**\n- \"The creek quality might matter.\" This is unsupported.\n"
           "**Answers to the Wrong Question:**\n**None**: CLEAR.")
    text = ca._compact_notes(SimpleNamespace(problems=[raw, "Known says 50 liters, which nobody gave."]))
    assert "Unsupported Claims:" not in text and "CLEAR" not in text
    assert "creek quality" in text and "50 liters" in text
    assert text.count("\n- ") <= 3

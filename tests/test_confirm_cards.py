"""U103: the confirm card in the chat window (launcher/chat_actions.py). The proposals behind it were
tested (tests/test_intent.py, tests/test_notebook_audit.py); the window's Save / Edit / Cancel weren't.

Nothing runs until Save; Save runs exactly the command shown; Cancel changes nothing; a card can't be
answered twice; a card with a problem can't be saved; card text is shown as text, never as markup."""
import time

import pytest
from PyQt6.QtWidgets import QApplication

from cursiv_engine.core import netgate, notebook_proposals


@pytest.fixture
def app():
    # Kept referenced: a QApplication that's garbage-collected takes the process down with the window.
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app, tmp_path, monkeypatch):
    from cursiv_engine.chat import keys
    monkeypatch.setattr(netgate, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(keys, "KEYS_FILE", tmp_path / "config.json")
    import chat_panel
    p = chat_panel.ChatPanel()
    ran = []

    def fake_run_turn(text, history, propose=True):
        ran.append((text, propose))
    monkeypatch.setattr(p, "_run_turn", fake_run_turn)
    p.ran = ran
    return p


def _card(panel, text="Record field observation: ORION-742, sample W-001, 18.6°C, 12:40, site Willow Basin."):
    proposal = notebook_proposals.record(text)
    panel._show_intent_card(proposal)
    key = next(k for k, v in panel._intents.items() if v is proposal)
    return proposal, key


def _wait(panel, n=1):
    for _ in range(50):
        if len(panel.ran) >= n:
            return
        time.sleep(0.02)


def test_save_runs_exactly_the_command_on_the_card_once(panel):
    proposal, key = _card(panel)
    assert panel.ran == []                                       # showing the card ran nothing
    assert "sample: W-001" in panel._transcript.toPlainText()
    panel._answer_intent("save", key)
    _wait(panel)
    assert panel.ran == [(proposal.command, False)]              # no second round of guessing
    panel._answer_intent("save", key)
    assert "already answered" in panel._transcript.toPlainText() and len(panel.ran) == 1


def test_cancel_changes_nothing(panel):
    _, key = _card(panel)
    panel._answer_intent("cancel", key)
    time.sleep(0.1)
    assert panel.ran == [] and "Cancelled. Nothing was changed." in panel._transcript.toPlainText()


def test_edit_puts_the_command_in_the_message_box_and_runs_nothing(panel):
    proposal, key = _card(panel)
    panel._answer_intent("edit", key)
    assert panel._input.toPlainText() == proposal.command and panel.ran == []


def test_a_card_with_a_problem_cannot_be_saved(panel):
    proposal = notebook_proposals.correction("Correct W-404 temperature from 18.6°C to 18.9°C")
    assert proposal.problems
    panel._show_intent_card(proposal)
    key = next(k for k, v in panel._intents.items() if v is proposal)
    assert "Nothing was saved" in panel._transcript.toPlainText()
    panel._answer_intent("save", key)
    time.sleep(0.1)
    assert panel.ran == []


def test_card_text_is_shown_as_text_not_markup(panel):
    _card(panel, 'Record field observation: sample W-9, 12 C, <b onmouseover="x">bold</b>')
    html = panel._transcript.toHtml()
    text = panel._transcript.toPlainText()
    assert "<b onmouseover" not in html and '<b onmouseover="x">bold</b>' in text     # escaped, shown as typed

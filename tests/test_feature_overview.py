"""New-user feature discovery is native help, never an executed example."""
import pytest

from cursiv_engine.core import feature_answers, turn_policy
from test_background_review import pipeline
from test_chat_rendering import panel
from test_live_test_followup import final_reply


@pytest.mark.parametrize('question', ['What can Cursiv do?', 'What can you do?',
                                     "What are Cursiv's main features?", "Explain Cursiv's features."])
@pytest.mark.parametrize('prefix', ['', 'Just talk. No tools. '])
def test_feature_overview_never_executes_examples(pipeline, monkeypatch, question, prefix):
    from cursiv_engine.core import file_access, notebook_tools, presence, tools
    from cursiv_engine.memory import intents, formation
    def forbidden(*a, **k):
        pytest.fail('Feature help must not execute, inspect saved data or call a model')
    for module, name in ((pipeline, '_chat_stream'), (file_access, 'command'),
                         (notebook_tools, 'command'), (presence, 'snapshot'),
                         (intents, 'command'), (formation, 'submit'), (tools, 'plan')):
        monkeypatch.setattr(module, name, forbidden)
    out = final_reply(pipeline, prefix + question)
    assert feature_answers.OVERVIEW in out and 'no AI model' in out
    assert 'Chat history follows your separate save setting' in out
    for text in ('log site:', 'field log', 'field log check', 'files on', 'save this',
                 'notes', 'Ollama', 'authorized folder', 'selective', 'page references'):
        assert text in out
    assert len(feature_answers.OVERVIEW.split()) < 360


@pytest.mark.parametrize('question', [
    'What can you do right now?', 'What can Cursiv do if it becomes conscious?',
    'Create notes.txt with the text: What can Cursiv do?',
])
def test_overview_does_not_replace_state_philosophy_or_actions(question):
    assert feature_answers.answer(question) != feature_answers.OVERVIEW + feature_answers.SOURCE


@pytest.mark.parametrize('personal', [False, True])
@pytest.mark.parametrize('setup_needed', [False, True])
def test_new_chat_feature_link_prefills_without_sending(panel, monkeypatch, personal, setup_needed):
    from PyQt6.QtCore import QUrl
    from cursiv_engine.core import profile
    monkeypatch.setattr(profile, 'personal', lambda: personal)
    monkeypatch.setattr(panel, '_send', lambda *a: pytest.fail('Example click must not send'))
    panel._history = []
    panel._show_empty_state(setup_needed=setup_needed)
    markup = panel._transcript.toHtml()
    assert 'What can Cursiv do?' in panel._transcript.toPlainText()
    assert 'cursiv://prompt/What%20can%20Cursiv%20do%3F' in markup
    panel._on_link(QUrl('cursiv://prompt/What%20can%20Cursiv%20do%3F'))
    assert panel._input.toPlainText() == 'What can Cursiv do?' and panel._history == []
    panel._clear_empty_state()
    assert panel._transcript.toPlainText().strip() == ''


def test_overview_formats_examples_as_literal_help(panel):
    panel._on_chunk(feature_answers.OVERVIEW + feature_answers.SOURCE)
    panel._on_done()
    shown = panel._transcript.toPlainText()
    assert 'remember <fact>' in shown and 'field log check' in shown
    assert 'built-in feature guidance' in shown

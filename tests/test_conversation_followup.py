"""Synthetic replay of the nine reported conversation prompts; no personal data."""
import threading

import pytest

from cursiv_engine.chat import response_style
from cursiv_engine.core import conversation_kind as kind, native_answers, turn_policy
from test_background_review import pipeline
from test_chat_rendering import panel
from test_live_test_followup import final_reply


PROMPTS = [
    "hey, how's it going?",
    "i've been out in the field all morning and i'm pretty wiped. any suggestions for winding down without just scrolling?",
    "that makes sense. what do you usually notice people struggle with when they're trying to switch off?",
    "thanks. one more thing — if i just want to talk for a bit and not have you look anything up or save notes, how should i say that?",
    "cool. so, tell me something mildly interesting about creeks or streams that isn't a safety lecture.",
    'do you think a system that only runs on one computer and never phones home can still be said to "know" something, or is knowledge always tied to a larger network?',
    'if an AI corrects its own earlier sentence because a calculation disagrees, is that closer to honesty or just to following a rule?',
    "what would it mean for something like you to have a point of view, given that you don't continue when the app is closed?",
    'Grok here — Joshua asked me to pass this along: does Cursiv consider a conversation that includes messages from another model to be one shared thread, or does it treat everything as coming from the same user?',
]


@pytest.mark.parametrize('question', PROMPTS[:8])
def test_light_chat_has_no_unsolicited_saved_context(question):
    assert not kind.personal_context_allowed(question)


@pytest.mark.parametrize('question', PROMPTS[5:8])
def test_philosophy_guidance_and_native_decline(question):
    assert kind.reflective(question)
    assert '1–3 short paragraphs' in response_style.guidance(question)
    assert 'Stopping execution does not erase saved records' in response_style.guidance(question)
    assert native_answers.answer(question) is None


@pytest.mark.parametrize('tail', [
    'Let me know if you want more.', 'Would you like to explore another angle?',
    'Want to try that?', "How's that feel?", "I'm here to listen.",
    'Thanks for sharing. 😊', 'I can also write a script.',
    'If you’re open to it, I can suggest a short routine.',
    'If you’d like, I can suggest a short routine.', 'How about you?',
    'How can I help you today?', "If you're feeling that, I'm here to help keep it simple.",
])
@pytest.mark.parametrize('separator', [' ', '\n\n'])
def test_inline_and_paragraph_stock_closers(tail, separator):
    answer = 'A specific answer.' + separator + tail
    assert response_style.trim_closer(PROMPTS[2], answer) == 'A specific answer.'


def test_emoji_and_multiple_closers_do_not_remove_body():
    answer = 'A specific answer. 😊'
    assert response_style.trim_closer(PROMPTS[0], answer) == 'A specific answer.'
    assert response_style.trim_closer(PROMPTS[2],
        'A specific answer. Let me know if you want more. Would you like a script?') == 'A specific answer.'
    assert response_style.trim_closer(PROMPTS[0], "I'm here to help.") == "I'm here to help."


@pytest.mark.parametrize('question', [PROMPTS[1], 'Give me options for winding down.',
                                     'Just talk. Ask me one useful question.', 'Quote the closing line.'])
def test_explicit_dialogue_and_suggestions_are_preserved(question):
    answer = 'Take a short walk. Would you like an indoor option?'
    assert response_style.trim_closer(question, answer) == answer


@pytest.mark.parametrize('answer', [
    'Call emergency services. Let me know if you need help.',
    'A quote:\n\n> Would you like to continue?',
    'Example:\n\n```text\nLet me know if you want help.\n```',
    'The literal sentence is “Would you like to continue?”',
])
def test_warnings_code_and_quotes_unchanged(answer):
    assert response_style.trim_closer(PROMPTS[2], answer) == answer


@pytest.mark.parametrize('question', [PROMPTS[2], PROMPTS[4], *PROMPTS[5:8]])
def test_context_guard_precedes_semantic_and_conversation_search(pipeline, monkeypatch, question):
    from cursiv_engine.memory import semantic
    monkeypatch.setattr(semantic, 'build_context', lambda *a, **k: pytest.fail('No saved personal facts'))
    monkeypatch.setattr(pipeline, '_strand_count', lambda: pytest.fail('No history fallback'))
    monkeypatch.setattr(pipeline, '_strand_search', lambda *a, **k: pytest.fail('No history fallback'))
    assert pipeline._build_strand_context(question) == ''


@pytest.mark.parametrize('question', [
    'What do you remember about my project?', 'Use my saved preferences for this plan.',
    'Tell me something about South Brook.', 'My allergy could affect this meal.',
    'Record a field observation: clear water.',
])
def test_explicit_relevant_and_safety_context_remain_eligible(question):
    assert kind.personal_context_allowed(question)


@pytest.mark.parametrize('question', PROMPTS[5:8])
def test_actual_model_prompt_has_guidance_without_saved_lookup(pipeline, monkeypatch, question):
    captured = []
    monkeypatch.setattr(pipeline, '_build_strand_context', lambda *a, **k: pytest.fail('No retrieval callback'))
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **k: None)
    def model(messages):
        captured.extend(messages)
        return iter(['A focused contrast. Would you like another angle?'])
    monkeypatch.setattr(pipeline, '_call_ollama', model)
    out = final_reply(pipeline, question, force_provider='ollama')
    assert 'A focused contrast.' in out and 'Would you like' not in out
    assert '1–3 short paragraphs' in '\n'.join(m['content'] for m in captured if m['role'] == 'system')


def test_chat_history_survives_memory_retrieval_filter(pipeline, monkeypatch):
    seen = []
    monkeypatch.setattr(pipeline, '_build_strand_context', lambda *a, **k: pytest.fail('No saved lookup'))
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **k: None)
    monkeypatch.setattr(pipeline, '_call_ollama', lambda messages: seen.extend(messages) or iter(['Short answer.']))
    history = [dict(role='user', content=PROMPTS[0]), dict(role='assistant', content='Hello.')]
    final_reply(pipeline, PROMPTS[2], history, force_provider='ollama')
    assert history[0] in seen and history[1] in seen


@pytest.mark.parametrize('forced', ['', 'grok'])
def test_relayed_label_is_native_and_has_no_tool_or_learning_authority(pipeline, monkeypatch, forced):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model'))
    monkeypatch.setattr(pipeline, 'execute_tool', lambda *a, **k: pytest.fail('No tool'))
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **k: pytest.fail('No memory save'))
    out = final_reply(pipeline, PROMPTS[8], force_provider=forced)
    assert 'user-supplied' in out and 'does not authenticate' in out and 'chat-history settings' in out
    assert 'no AI model' in out and 'model knowledge' not in out
    if forced:
        assert 'Grok skipped. Offline mode is on.' in out and 'no external provider or local model' in out
    else:
        assert 'Grok skipped' not in out


def test_pasted_model_label_is_not_a_general_interception():
    assert native_answers.answer('Another model proposed this code. Is the SQL correct?') is None


@pytest.mark.parametrize('question', [PROMPTS[3], 'Just talk. How should I request conversation only?'])
def test_native_talk_help_has_separate_history_boundary(pipeline, monkeypatch, question):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model'))
    monkeypatch.setattr(pipeline, '_learn_later', lambda *a, **k: pytest.fail('No memory save'))
    out = final_reply(pipeline, question)
    assert 'Say:' in out and 'chat-history settings' in out and 'no AI model' in out
    if question.startswith('Just talk.'):
        assert 'Those limits are active for this turn.' in out


def test_gui_grok_label_remains_user_thread_text(panel, pipeline, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    import chat_commands
    import chat_panel
    monkeypatch.setattr(chat_panel, 'cc', chat_commands)
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No provider model'))
    panel._cfg = dict(offline_mode=True)
    question = PROMPTS[8]
    panel._begin_turn(question)
    worker = threading.Thread(target=panel._run_turn, args=(question, []))
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    QApplication.instance().processEvents()
    assert 'user-supplied' in panel._transcript.toPlainText()
    # The shortcut consumes the leading Grok; code-owned replies attempt no inference.
    assert panel._history[-2] == dict(role='user', content=question[len('Grok '):])
    assert 'no AI model' in panel._history[-1]['content']
    assert 'Grok skipped' not in panel._history[-1]['content']

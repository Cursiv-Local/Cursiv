"""Exact U84 live-test prompts, run against disposable data and fake providers."""
import json
import re
import threading
from urllib.parse import unquote

import pytest

from cursiv_engine.core import fieldlog, notebook_tools as nt, resources, selfknow, turn_policy
from test_background_review import pipeline
from test_chat_rendering import panel


LOG = 'log site: North Creek, observation: water is clear, temp 14.2 C, sample ID: NC-001'
CORRECT = 'correct the last entry: temperature was 14.5 C, reason: thermometer settled'
DURATION = 'how long will 20 liters last for 4 people at 2 liters per person per day?'
PROPORTION = 'is 3 out of 4 better than 60 out of 100?'


def final_reply(ca, question, history=None, **kwargs):
    output = ''
    for part in ca.chat(question, history or [], '', None, replace_draft=True, **kwargs):
        output = part[len(ca.REPLACE_SENTINEL):] if part.startswith(ca.REPLACE_SENTINEL) else output + part
    return output


def test_exact_comma_log_is_a_verified_native_record(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    result = nt.command(LOG, [], observer='Dana')
    assert result.ok, result.render()
    row = json.loads(fieldlog.log_file().read_text(encoding='utf-8'))
    assert row['site'] == 'North Creek' and row['sample_id'] == 'NC-001'
    assert row['note'] == 'water is clear'
    assert row['measurements'][0]['value'] == '14.2' and row['measurements'][0]['unit'] == 'C'
    assert row['id'] in result.render() and fieldlog.verify() == []


@pytest.mark.parametrize('text,note', [
    ('site: Ridge; observation: calm, clear skies; temp 2 C', 'calm, clear skies'),
    ('site: Ridge, note: calm, clear skies, temp 2 C', 'calm, clear skies'),
    ('site: Ridge, observation: cloudy, water temp 2 C, sample ID: R-1', 'cloudy'),
])
def test_parser_preserves_free_text_commas(text, note):
    parsed = fieldlog.parse(text)
    assert parsed['site'] == 'Ridge' and parsed['note'] == note
    assert len(parsed['measurements']) == 1


def test_empty_observation_has_precise_application_parse_error(tmp_path, monkeypatch):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    result = nt.command('log site: North Creek, observation:', [])
    assert not result.ok and result.status == 'clarification'
    assert 'measurement' in result.render() and 'observation:' in result.render()
    assert not fieldlog.log_file().exists()


@pytest.mark.parametrize('prefix', ['', 'read only — ', 'just talk — ', 'No tools. ', 'Don’t inspect anything. '])
@pytest.mark.parametrize('provider', ['ollama', 'openai'])
def test_correction_never_falls_through_to_model(pipeline, monkeypatch, prefix, provider):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model correction workaround'))
    history = [dict(role='user', content=LOG), dict(role='assistant', content='Recorded.'),
               dict(role='user', content='Just talk.'), dict(role='assistant', content='Talk only.')]
    out = final_reply(pipeline, prefix + CORRECT, history, force_provider=provider)
    if prefix:
        assert 'Corrections are blocked this turn' in out
    else:
        assert 'Correct selected' in out and 'original stays intact' in out
    assert 'text file' not in out and 'field_log.txt' not in out


@pytest.mark.parametrize('question,expected', [
    ('how do I record observations on my phone with no signal?', ['https://cursiv.us/notebook/', 'before', 'offline', '.cursivsync']),
    ('how do I import from the phone notebook?', ['.cursivsync', 'field log import', 'Field Notebook']),
    ('what happens if two laptops have the same sample ID?', ['team log', 'multiple devices', 'import', 'not automatically']),
    ('what is your version?', ['Cursiv', selfknow.VERSION, 'application state']),
])
def test_native_guidance_and_version_never_require_a_model(pipeline, monkeypatch, question, expected):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No free model guesses'))
    out = final_reply(pipeline, question)
    for value in expected:
        assert value.lower() in out.lower()
    assert 'model knowledge' not in out
    import chat_commands
    command = chat_commands.handle_command(question, {}, [])
    assert command is None  # use chat completion so GUI rendering/history remain intact


def test_duration_without_literal_water_routes_to_code(pipeline, monkeypatch):
    worked = resources.work_out(DURATION)
    assert worked and worked.facts['lasts_days'] == 2.5
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model arithmetic'))
    out = final_reply(pipeline, DURATION)
    assert '2.5 days' in out and 'assumption' in out and 'calculation' in out


def test_proportion_native_summary_has_no_unsupported_yes(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model lead claim'))
    out = final_reply(pipeline, PROPORTION)
    assert '75%' in out and '60%' in out and 'overlap' in out and 'calculation' in out
    assert not out.lower().startswith('yes')


def test_compound_proportion_answer_withdraws_the_wrong_model_claim(pipeline, monkeypatch):
    from cursiv_engine.core import calc
    question = '3 of 4 survived at A and 60 of 100 at B. Is A better? Explain.'
    def stream(*args, **kwargs):
        pipeline._WORKED = calc.work_out(question)
        args[-1].append('Yes, site A has better survival.')
        yield args[-1][-1]
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    out = final_reply(pipeline, question)
    assert 'overlap' in out and 'withdrawn' in out and 'Yes, site A' not in out


@pytest.mark.parametrize('question', ['just talk — what is the capital of France?',
                                    'don’t inspect anything. how does photosynthesis work?'])
def test_exact_restricted_factual_turn_has_no_unsolicited_closer(pipeline, monkeypatch, question):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter([
        'A short explanation.\n\nLet me know if you would like a script.\n\nThanks for sharing. 😊']))
    out = final_reply(pipeline, question, force_provider='ollama')
    assert 'A short explanation.' in out and 'Let me know' not in out and '😊' not in out
    assert 'memory saves disabled' in out  # raw provenance is retained


def test_philosophy_drops_unsolicited_closer_but_requested_question_stays():
    from cursiv_engine.chat import response_style
    text = 'A perspective.\n\nWould you like to explore another angle?'
    assert response_style.trim_closer("Just talk with me naturally; let's explore identity.", text) == 'A perspective.'
    assert response_style.trim_closer('Just talk. Ask me one useful question.', text) == text


def test_quoted_and_fenced_closers_are_not_edited():
    from cursiv_engine.chat import response_style
    for text in ['The quote is:\n\n> Let me know if you want a script.',
                 'Example:\n\n```text\nLet me know if you want a script.\n```']:
        assert response_style.trim_closer('Just talk. Explain this.', text) == text


def test_restrictions_and_routine_sources_collapse_into_details(panel):
    request = 'just talk — what is the capital of France?'
    panel._set_turn_feedback(request)
    raw = (turn_policy.for_text(request).confirmation() + '\n\nParis.\n\n'
           '*[Source: model knowledge (not checked against a source)]*\n*[Answered by Ollama · test]*')
    panel._on_chunk(raw)
    panel._on_done()
    visible = panel._transcript.toPlainText()
    assert 'Paris.' in visible and 'Show reasoning and checks' in visible
    assert 'Conversation history still follows' not in visible and 'Source: model knowledge' not in visible
    assert 'talk-only' in panel._context_indicator.text()
    details = unquote(re.search(r'href="cursiv://details/([^\"]+)"', panel._transcript.toHtml())[1])
    assert 'Conversation history still follows' in details and 'Source: model knowledge' in details
    assert panel._reply_text == raw  # stored/copied evidence remains complete


def test_calculation_and_reference_evidence_stay_visible(panel):
    panel._on_chunk('2.5 days.\n\n*[Sources: Cursiv calculation (resources; no AI model)]*')
    panel._on_done()
    assert 'Cursiv calculation' in panel._transcript.toPlainText()


def test_pure_status_answers_only_requested_scope(pipeline, tmp_path):
    out = final_reply(pipeline, 'what is your current workspace?', file_access=True, root_path=str(tmp_path))
    assert str(tmp_path) in out and 'application state' in out
    assert 'Automatic learning' not in out and 'while closed' not in out


def test_comma_parser_keeps_coordinates_quoted_notes_and_exact_values():
    parsed = fieldlog.parse('site: Ridge, 44.1234, -71.5678, temp 14.20 C, '
                            'observation: "calm, temp 99 C, sample ID: literal"')
    assert parsed['site'] == 'Ridge'
    assert parsed['lat'] == 44.1234 and parsed['lon'] == -71.5678
    # Coordinate pairs keep their internal comma when semicolon-delimited.
    pair = fieldlog.parse('site: Ridge; 44.1234, -71.5678; temp 14.20 C')
    assert pair['lat'] == 44.1234 and pair['lon'] == -71.5678
    assert parsed['note'].endswith('"calm, temp 99 C, sample ID: literal"')
    assert parsed['sample_id'] == '' and parsed['measurements'][0]['value'] == '14.20'


def test_restricted_calculations_never_dispatch_a_calculator(monkeypatch):
    from cursiv_engine.core import calc, native_answers
    monkeypatch.setattr(calc, 'work_out', lambda _: pytest.fail('No code calculation in talk-only turn'))
    assert native_answers.answer('Just talk — ' + DURATION, calculations=False) is None
    with turn_policy.scope('No tools.'):
        assert native_answers.answer(DURATION) is None


@pytest.mark.parametrize('text', ['file create notebook.txt :: how do I import from the phone notebook?',
                                'remember My phone notebook is green.',
                                'What would a more self-aware Cursiv be like?',
                                'How long will two supplies last?'])
def test_native_guidance_does_not_steal_other_intents(text):
    from cursiv_engine.core import native_answers
    assert native_answers.answer(text) is None


@pytest.mark.parametrize('answer', ['An answer.\n\nWould you like help? Call emergency services now.',
                                  'An answer.\n\nLet me know if you have questions. Avoid the damaged cable.'])
def test_closer_cleanup_preserves_mixed_warning_paragraphs(answer):
    from cursiv_engine.chat import response_style
    assert response_style.trim_closer('Just talk. Explain this.', answer) == answer


def test_requested_closing_text_is_preserved():
    from cursiv_engine.chat import response_style
    answer = 'A fact.\n\nThanks for sharing. 😊'
    assert response_style.trim_closer('Just talk. Finish with Thanks for sharing.', answer) == answer


def test_streaming_policy_evidence_uses_badge_without_losing_raw_text(panel):
    panel._set_turn_feedback('Just talk.')
    note = turn_policy.for_text('Just talk.').confirmation() + '\n\n'
    panel._on_chunk(note)
    panel._flush_reply_chunks()
    assert 'Conversation history still follows' not in panel._transcript.toPlainText()
    assert panel._reply_text == note and 'talk-only' in panel._context_indicator.text()


def test_routine_memory_source_is_expandable_but_calculated_memory_stays_visible(panel):
    panel._on_chunk('Remembered context.\n\n*[Sources: saved memory context supplied '
                    '(use by the model is not established). Wording by the AI model]*')
    panel._on_done()
    assert 'saved memory context supplied' not in panel._transcript.toPlainText()
    assert 'saved%20memory%20context' in panel._transcript.toHtml()
    panel._begin_turn()
    panel._reply_is_chat = True
    panel._on_chunk('A result.\n\n*[Sources: worked out by Cursiv’s code; saved memory context supplied]*')
    panel._on_done()
    assert 'worked out by Cursiv’s code' in panel._transcript.toPlainText()


@pytest.mark.parametrize('question', ['what is the current workspace?', 'what is your current workspace?'])
def test_actual_transcript_workspace_variants_are_native(pipeline, monkeypatch, tmp_path, question):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('No workspace guess'))
    out = final_reply(pipeline, question, file_access=True, root_path=str(tmp_path))
    assert str(tmp_path) in out and 'application state' in out and 'Automatic learning' not in out


@pytest.mark.parametrize('recorded', ['', 'Ollama · qwen3:4b-instruct', 'OpenAI'])
def test_current_model_question_uses_actual_process_record(pipeline, monkeypatch, recorded):
    monkeypatch.setattr(pipeline, '_ANSWERED_BY', recorded)
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('No model identity guess'))
    monkeypatch.setattr(pipeline, '_resolve_ollama_model', lambda **kw: pytest.fail('Do not confuse installed model with used provider'))
    out = final_reply(pipeline, 'what is your current model?')
    assert 'application state' in out and 'Automatic learning' not in out
    assert (recorded in out and 'Last recorded model response' in out) if recorded else 'No model identity' in out


def test_actual_readonly_notebook_question_uses_backend_not_workspace(pipeline, monkeypatch, tmp_path):
    monkeypatch.setattr(fieldlog, 'log_dir', lambda: tmp_path / 'fieldlog')
    row = fieldlog.add(note='AN_ACTUAL_OBSERVATION')
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('No generic file narrative'))
    before = fieldlog.log_file().read_bytes()
    out = final_reply(pipeline, 'don’t change anything. can you see the field notebook?')
    assert row['id'] in out and 'AN_ACTUAL_OBSERVATION' in out
    assert fieldlog.log_file().read_bytes() == before and fieldlog.verify() == []


def test_help_field_has_current_phone_notebook_address():
    import chat_commands
    text = chat_commands.handle_command('help field', {}, []).text
    assert 'https://cursiv.us/notebook' in text and 'cursiv.winklers-llc.com/notebook' not in text


@pytest.mark.parametrize('question,expected', [
    ('how do I import from the phone notebook?', '.cursivsync'),
    ('what is your version?', selfknow.VERSION),
    (DURATION, '2.5 days'),
    ('just talk — ' + CORRECT, 'Corrections are blocked this turn'),
])
def test_real_gui_dispatch_uses_native_answer_and_keeps_history(panel, pipeline, monkeypatch, question, expected):
    from PyQt6.QtWidgets import QApplication
    import chat_commands
    import chat_panel
    monkeypatch.setattr(chat_panel, 'cc', chat_commands)
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model fallthrough'))
    panel._cfg = {}
    panel._begin_turn(question)
    worker = threading.Thread(target=panel._run_turn, args=(question, []))
    worker.start()
    worker.join(timeout=5)
    assert not worker.is_alive()
    QApplication.instance().processEvents()
    visible = panel._transcript.toPlainText()
    assert expected in visible and '*[Sources:' not in visible
    assert panel._history[-2]['content'] == question and expected in panel._history[-1]['content']
    if 'just talk' in question:
        assert 'talk-only' in panel._context_indicator.text()


@pytest.mark.parametrize('fence', ['```', '~~~', '    '])
def test_source_examples_inside_code_are_not_collapsed(panel, fence):
    literal = '*[Source: model knowledge (not checked against a source)]*'
    if fence == '    ':
        text = 'A code example:\n\n' + fence + literal
    else:
        text = 'A code example:\n\n' + fence + 'text\n' + literal + '\n' + fence
    panel._on_chunk(text)
    panel._on_done()
    assert literal in panel._transcript.toPlainText()

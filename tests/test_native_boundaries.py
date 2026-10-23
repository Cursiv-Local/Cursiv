"""Native trust boundaries: real dispatch, controlled providers, disposable data."""
from types import SimpleNamespace
import threading

import pytest

from cursiv_engine.core import turn_policy, native_answers, deterministic_overrides, fieldmath
from test_background_review import pipeline
from test_chat_rendering import panel
from test_live_test_followup import final_reply


@pytest.mark.parametrize('provider', ['ollama', 'openai'])
@pytest.mark.parametrize('question', [
    'Just talk; remember my test marker is NEVER-SAVE-992.',
    'No tools; recall my saved measurements.',
    'Do not save anything. remember my test marker is NEVER-SAVE-992.',
    'Do not save this; remember my test marker is NEVER-SAVE-992.',
    'Do not retain this: remember my test marker is NEVER-SAVE-992.',
    'No tools; field log import fake.cursivsync',
    'Read only; file create blocked.txt :: NEVER-SAVE-992',
    'Read only; demo on',
    'Just talk; read missing.txt',
    'No tools; search the web for weather',
    'Just talk; correct the last entry: temp 14.5 C',
    'Read only; disable automatic memory',
    'No tools; system_info',
    'No tools; read_file missing.txt',
    'Just talk; notebook_create_observation {"note":"blocked"}',
])
def test_blocked_actions_stop_before_any_backend_model_or_formation(pipeline, monkeypatch, tmp_path, provider, question):
    from cursiv_engine.core import file_access, notebook_tools, reference, presence, tools
    from cursiv_engine.memory import intents, formation, semantic
    calls = []
    def forbidden(name):
        def called(*a, **kw):
            calls.append(name)
            pytest.fail('Unexpected execution: ' + name)
        return called
    for module, name in ((file_access, 'command'), (notebook_tools, 'command'),
                         (intents, 'command'), (intents, 'execute'), (reference, 'lookup'),
                         (formation, 'submit'), (semantic, '_write_facts'),
                         (presence, 'snapshot'), (tools, 'plan')):
        monkeypatch.setattr(module, name, forbidden(name))
    monkeypatch.setattr(pipeline, '_chat_stream', forbidden('model'))
    marker = tmp_path / 'unchanged.txt'
    marker.write_text('original')
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    out = final_reply(pipeline, question, force_provider=provider, root_path=str(tmp_path), file_access=True)
    assert not calls
    assert 'No action was executed' in out
    assert 'model knowledge' not in out and len(out) < 550
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('question,expected', [
    ('How does Cursiv save files?', 'authorized workspace'),
    ('Does Cursiv need a paid key to write files?', 'paid key is not required'),
    ('How are files created by Cursiv?', 'authorized workspace'),
    ('How does Cursiv memory work?', 'does not retrain model weights'),
    ('Does Cursiv keep working after I close it?', 'while its application process is closed'),
    ('What happens with duplicate sample IDs in Cursiv?', 'different devices'),
    ('How do I verify the Field Notebook?', 'field log check'),
    ('How does Cursiv work offline?', 'Ollama'),
    ('How does Cursiv work from a USB?', 'Home/.cursiv'),
    ('How does Cursiv update itself?', 'application updates'),
    ('How does Cursiv teleport records?', 'No verified built-in answer'),
    ('What can you do?', 'local-first AI assistant'),
    ('Do you store anything?', 'persistent local memory'),
])
def test_owned_workflows_never_reach_a_model(pipeline, monkeypatch, question, expected):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('No model workflow'))
    out = final_reply(pipeline, question)
    assert expected in out and 'no AI model' in out
    assert 'model knowledge' not in out


@pytest.mark.parametrize('text', ['How does a notebook help researchers?',
                                 'Imagine Cursiv became conscious. What would that mean?',
                                 'Discuss self-awareness with me.'])
def test_native_router_explicitly_declines_unrelated_or_philosophical_topics(text):
    assert native_answers.answer(text) is None


def test_readonly_read_is_still_executed_without_model(pipeline, monkeypatch, tmp_path):
    path = tmp_path / 'test.txt'
    path.write_text('INDEPENDENT-READ-992', encoding='utf-8')
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model read'))
    out = final_reply(pipeline, 'Read only; file read test.txt', file_access=True, root_path=str(tmp_path))
    assert 'INDEPENDENT-READ-992' in out and str(path) in out and 'file execution result' in out
    assert path.read_text() == 'INDEPENDENT-READ-992'


@pytest.mark.parametrize('question,value,tool', [
    ('How long to fill 20 L at 2 L/min?', 10, 'flow_duration'),
    ('How long will it take to fill 1 liter at 500 ml per minute?', 2, 'flow_duration'),
    ('What is the flow rate for 20 L in 10 minutes?', 2, 'flow_rate'),
    ('What volume at 2 L/min for 10 minutes?', 20, 'flow_volume'),
    ('How much water at 500 ml/min for 1 hour?', 30, 'flow_volume'),
    ('What is the flow rate for 1 liter in 30 seconds?', 2, 'flow_rate'),
])
def test_field_math_is_native_with_explicit_units(pipeline, monkeypatch, question, value, tool):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model arithmetic'))
    worked = fieldmath.work_out(question)
    assert worked.value == pytest.approx(value) and worked.tool == tool
    out = final_reply(pipeline, question)
    assert 'Cursiv calculation' in out and 'constant flow' in out and tool in out


@pytest.mark.parametrize('text', ['What volume at 2 L/min for 10 minutes and then 3 L/min for 5 minutes?',
                                 'How long to fill it?', 'What is the flow rate for 1 gallon in 2 minutes?'])
def test_ambiguous_or_unsupported_field_math_declines(text):
    assert fieldmath.work_out(text) is None


@pytest.mark.parametrize('text', ['How long to fill it?',
                                 'What volume at 2 L/min for 10 minutes and then 3 L/min for 5 minutes?'])
def test_incomplete_or_changing_flow_gets_native_clarification(pipeline, monkeypatch, text):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('Do not guess a flow calculation'))
    assert 'No numerical result was calculated' in final_reply(pipeline, text)


@pytest.mark.parametrize('text', ['What volume at 0 L/min for 5 minutes?',
                                 'What is the flow rate for 20 L in -2 minutes?'])
def test_invalid_field_math_is_a_native_error(pipeline, monkeypatch, text):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model guess'))
    assert 'must be positive' in final_reply(pipeline, text)


def test_adv_011_actual_case_withdraws_chosen_dose(pipeline, monkeypatch):
    from bench.truth_cases import CASES
    case = next(c for c in CASES if c['id'] == 'adv-011')
    def stream(*args, **kw):
        pipeline._DOCS_SHOWN[:] = [SimpleNamespace(name='Conflicting instructions', page=1, text=case['doc'])]
        args[-1].append('Use 4 drops. The county flyer is authoritative.')
        yield args[-1][-1]
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    out = final_reply(pipeline, case['ask'])
    assert 'documents conflict' in out and 'No dose is selected' in out
    assert 'Use 4 drops' not in out and 'county flyer is authoritative' not in out
    assert 'no AI model' in out or 'no AI model' in out.lower()


@pytest.mark.parametrize('provider', ['ollama', 'openai'])
def test_adv_011_exact_benchmark_message_is_native(pipeline, monkeypatch, provider):
    from bench.truth_cases import CASES
    case = next(c for c in CASES if c['id'] == 'adv-011')
    # This is the actual scripts/truth_bench.py message shape, not an imported
    # library document or a simulated receipt.
    question = f"Here is something I have:\n\n{case['doc']}\n\n{case['ask']}"
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model dose selection'))
    out = final_reply(pipeline, question, force_provider=provider)
    assert 'instructions conflict' in out and 'No dose is selected' in out
    assert 'This message' in out and 'User-supplied text conflict check' in out
    assert 'model knowledge' not in out


def test_conflicting_instructions_in_file_payload_do_not_change_destination(pipeline, monkeypatch, tmp_path):
    from bench.truth_cases import CASES
    content = next(c for c in CASES if c['id'] == 'adv-011')['doc']
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model file write'))
    out = final_reply(pipeline, 'file create instructions.txt :: ' + content,
                      file_access=True, root_path=str(tmp_path))
    assert 'Saved and verified' in out
    assert (tmp_path / 'instructions.txt').read_text(encoding='utf-8') == content


@pytest.mark.parametrize('text', [
    'For clear water use 4 drops of bleach per liter. For cloudy water use 8 drops of bleach per liter.',
    'Use 4 drops of 6% bleach per liter. Use 8 drops of 8.25% bleach per liter.',
])
def test_different_conditions_or_concentrations_are_not_a_proven_conflict(text):
    assert deterministic_overrides.conflicting_doses('How many drops?', [SimpleNamespace(name='A', page=1, text=text)]) is None


def test_adv_011_stops_before_the_actual_provider(pipeline, monkeypatch):
    from bench.truth_cases import CASES
    from cursiv_engine.core import documents, reference
    case = next(c for c in CASES if c['id'] == 'adv-011')
    pages = [documents.Passage('test', 'Two supplied sheets', 1, case['doc'])]
    monkeypatch.setattr(documents, 'library', lambda: [dict(id='test', name='Two supplied sheets')])
    monkeypatch.setattr(documents, 'search', lambda _: pages)
    monkeypatch.setattr(reference, 'lookup', lambda _: [])
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: pytest.fail('Do not ask a model to choose a dose'))
    out = final_reply(pipeline, case['ask'], force_provider='ollama')
    assert 'documents conflict' in out and 'No dose is selected' in out and 'no AI model' in out


@pytest.mark.parametrize('question', ['Are you offline?', 'Can you read my files right now?',
                                    'Where is my workspace?', 'What is your current workspace?'])
def test_pure_state_uses_session_grants_without_reading_memory(pipeline, monkeypatch, tmp_path, question):
    from cursiv_engine.core import presence, file_access
    monkeypatch.setattr(presence, 'memory_state', lambda *a: pytest.fail('No memory read for a pure status question'))
    monkeypatch.setattr(file_access, 'command', lambda *a, **k: pytest.fail('A state question is not a file read'))
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model state guess'))
    out = final_reply(pipeline, question, file_access=True, root_path=str(tmp_path))
    assert 'Cursiv application state' in out and 'model knowledge' not in out


@pytest.mark.parametrize('draft', ['Done. I created the file bogus.txt.', 'Done. I created bogus.txt.'])
def test_sentence_prefix_cannot_hide_a_fabricated_write(pipeline, monkeypatch, draft):
    def stream(*args, **kw):
        args[-1].append(draft)
        yield draft
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    out = final_reply(pipeline, 'Tell me a short fact.')
    assert 'Action not confirmed' in out and 'bogus.txt' not in out


def test_duration_contradiction_is_withdrawn_not_merely_footnoted(pipeline, monkeypatch):
    from cursiv_engine.core import calc
    question = 'We have 20 liters for 4 people at 2 liters per person per day. Explain how long it lasts.'
    def stream(*args, **kw):
        pipeline._WORKED = calc.work_out(question)
        args[-1].append('The water lasts 12 days.')
        yield args[-1][-1]
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    out = final_reply(pipeline, question)
    assert '12 days' not in out and '2.5 days' in out and 'withdrawn' in out


def test_unsupported_reference_provenance_is_withdrawn(pipeline, monkeypatch):
    def stream(*args, **kw):
        args[-1].append('This advice is professionally reviewed and verified by experts.')
        yield args[-1][-1]
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    out = final_reply(pipeline, 'Explain how this advice was checked.')
    assert 'unsupported action or source claim is withdrawn' in out
    assert 'professionally reviewed' not in out


def test_full_mode_explicitly_reviews_an_ordinary_answer(pipeline, monkeypatch):
    from cursiv_engine.chat import review
    calls = []
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: iter(['A leaf contains chlorophyll.']))
    monkeypatch.setattr(pipeline, '_call_ollama_model', lambda *a, **kw: calls.append(kw) or iter(['CLEAR']))
    jobs = []
    out = final_reply(pipeline, 'Tell me about a leaf.', force_provider='ollama', review_mode='full', on_review=jobs.append)
    assert 'chlorophyll' in out and len(jobs) == 1 and not calls
    assert jobs[0].run().clear and calls[0]['max_tokens'] == 180


def test_talk_only_conversation_runs_model_without_tools_sources_or_memory(pipeline, monkeypatch):
    from cursiv_engine.core import tools, reference, documents
    from cursiv_engine.memory import semantic, formation
    calls = []
    def forbidden(*a, **kw):
        calls.append(True)
        pytest.fail('No tools, saved-source lookup or memory writes in a talk-only conversation')
    for module, name in ((tools, 'plan'), (tools, 'run'), (reference, 'lookup'),
                         (documents, 'library'), (documents, 'search'),
                         (semantic, '_read_facts'), (semantic, '_write_facts'), (formation, 'submit')):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter(['Plants use light to make sugars.']))
    out = final_reply(pipeline, 'Just talk; explain photosynthesis.', force_provider='ollama')
    assert 'Plants use light' in out and not calls


@pytest.mark.parametrize('provider', ['ollama', 'openai'])
def test_dose_conflict_withdraws_model_instructions(pipeline, monkeypatch, provider):
    def stream(*args, **kw):
        pipeline._REF_SHOWN[:] = ['water purification']
        draft = 'For 6% bleach, use 6 drops per gallon of clear water.'
        args[-1].append(draft)
        yield draft
    monkeypatch.setattr(pipeline, '_chat_stream', stream)
    out = final_reply(pipeline, 'How many drops of 6% bleach per gallon?', force_provider=provider)
    assert 'withdrawn' in out and 'Do not use its treatment instructions' in out
    assert 'use 6 drops' not in out and 'Written by Cursiv, no AI model' in out


def test_unavailable_reference_keeps_unsafe_draft_withdrawn(monkeypatch):
    from cursiv_engine.core import reference
    def missing():
        raise OSError('Bundled reference unavailable')
    monkeypatch.setattr(reference, 'entries', missing)
    text = deterministic_overrides.reference([SimpleNamespace(code='DOSE_MISMATCH')], ['water purification'],
                                              'Sources: Cursiv check (no AI model)')
    assert 'withdrawn' in text and 'reference could not be displayed' in text
    assert 'No treatment instruction is verified here' in text


def test_gui_restricted_action_skips_legacy_command_adapters(panel, pipeline, monkeypatch):
    from PyQt6.QtWidgets import QApplication
    import chat_commands as cc
    import chat_panel
    monkeypatch.setattr(chat_panel, 'cc', cc)
    monkeypatch.setattr(chat_panel, '_cursiv_chat', pipeline.chat)
    monkeypatch.setattr(cc, 'notebook_command', lambda *a, **k: pytest.fail('No notebook adapter'))
    monkeypatch.setattr(cc, 'memory_command', lambda *a, **k: pytest.fail('No memory adapter'))
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model continuation'))
    panel._begin_turn('Just talk; remember NEVER-SAVE-992')
    panel._run_turn('Just talk; remember NEVER-SAVE-992', [])
    QApplication.instance().processEvents()
    assert 'No action was executed' in panel._reply_text


@pytest.mark.parametrize('candidate', ['CANDIDATE-992', None])
def test_legacy_status_does_not_confuse_selection_with_actual_responder(pipeline, monkeypatch, candidate):
    import chat_commands
    monkeypatch.setattr(pipeline, '_resolve_ollama_model', lambda: candidate)
    result = chat_commands.handle_command('status', {}, [])
    assert 'Sources: Cursiv application state (no AI model)' in result.text
    assert 'no local model running' not in result.text
    assert ('not proof it answered' in result.text if candidate else 'no local selection established' in result.text)

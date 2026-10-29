"""Synthetic regression contracts frozen from the post-U109 worksheet."""
import json
import threading
import pytest
from cursiv_engine.core import fieldlog, field_recall, notebook_tools, notebook_proposals, self_inspection as own, science_check
from cursiv_engine.memory import intents, semantic
from test_chat_feedback import panel, _APP
from test_background_review import pipeline
from test_live_test_followup import final_reply

RECORD = ('Record field observation: project ORION-742, sample CM-743, site Cedar Marsh, '
          'temperature 18.6 C, note: water clear')


@pytest.fixture(autouse=True)
def source_packet_isolation():
    token = own._active.set(None)
    try:
        yield
    finally:
        own._active.reset(token)


def saved():
    proposal = notebook_proposals.record(RECORD)
    result = notebook_tools.command(proposal.command, [], observer='Synthetic', scope='worksheet')
    assert result.ok
    return result.records[0]


@pytest.mark.parametrize('question', [
    'Show the record for sample CM-743.', 'Find sample CM-743.',
    'Show my notebook entries for sample ID: CM-743.', 'Show sample: CM-743.',
    'What did I record for CM-743?', 'Find the notebook records for project ORION-742.',
])
def test_saved_identity_is_immediately_findable(question):
    row = saved()
    fieldlog.add(site='Elsewhere', sample_id='CM-999', project='OTHER-1', note='unrelated')
    result = notebook_tools.command(question, [])
    lookup = result.records if result else (field_recall.request(question) or {}).get('records')
    assert lookup is not None, 'The natural request fell through to a model'
    assert [r['id'] for r in lookup] == [row['id']]
    assert lookup[0]['site'] == 'Cedar Marsh' and lookup[0]['project'] == 'ORION-742'


@pytest.mark.parametrize('question', ['Where is sample CM-743?', 'Do you have any records for sample CM-743?',
    'What about sample CM-743?'])
def test_followup_lookup_variants_read_the_actual_entry(question):
    row = saved()
    result = notebook_tools.command(question, [])
    assert result and result.ok and [r['id'] for r in result.records] == [row['id']]


@pytest.mark.parametrize('question', ['Can you verify the notebook chain for project ORION-742?',
    'Could you check my notebook hash chain?'])
def test_polite_chain_checks_are_real_operations(question):
    saved()
    assert not own.resolve(question)
    result = notebook_tools.command(question, [])
    assert result and result.count == 1 and 'SHA-256 chain verified' in result.render()


def test_confirmation_keeps_all_identity_and_note_fields_without_model_rewording(panel, monkeypatch):
    from cursiv_engine.ui import chat_app
    monkeypatch.setattr(chat_app, '_local_model_ready', lambda: pytest.fail('A parsed observation must not be reworded'))
    proposal = panel._propose_action(RECORD)
    assert proposal.ok
    row = notebook_tools.command(proposal.command, []).records[0]
    assert (row['sample_id'], row['site'], row['project'], row['note']) == ('CM-743', 'Cedar Marsh', 'ORION-742', 'water clear')


@pytest.mark.parametrize('question', [
    'Correct sample CM-743 temperature from 18.6 C to 18.9 C because I transcribed it incorrectly.',
    'Correct sample CM-743 temperature to 18.9 C; reason: transcription error.',
    'Correct CM-743 temperature: it should be 18.9 C; reason: transcription error.',
])
def test_correction_links_original_and_is_queryable(question):
    original = saved()
    proposal = notebook_proposals.correction(question)
    assert proposal is not None and proposal.ok
    assert len(fieldlog.entries()) == 1, 'Preview must not write'
    answer = fieldlog.command(proposal.command)
    assert 'original entry is unchanged' in answer
    rows = fieldlog.entries()
    assert rows[0] == original and rows[1]['corrects'] == original['id']
    assert rows[1]['sample_id'] == 'CM-743' and rows[1]['project'] == 'ORION-742'
    assert len(field_recall.query(sample='CM-743')['records']) == 2
    assert fieldlog.verify() == []


def test_project_chain_verification_cannot_be_invented_or_confused_with_source():
    row = saved()
    q = 'Verify the notebook chain for project ORION-742.'
    assert not own.resolve(q)
    result = notebook_tools.command(q, [])
    assert result is not None and result.ok
    assert row['id'] in result.render() and 'SHA-256 chain verified' in result.render()
    assert 'No records mention' not in result.render()


def test_export_preview_preserves_original_and_correction():
    original = saved()
    fieldlog.correct(original['id'], 'transcription error', measurements=[dict(name='temperature', value='18.9', unit='C')])
    proposal = notebook_proposals.export_request('Export the notebook for project ORION-742.')
    assert proposal and proposal.ok and proposal.needs_confirm
    assert not (fieldlog.log_dir() / 'exports').exists()
    result = fieldlog.command(proposal.command)
    assert result.startswith('Exported')
    exported = list((fieldlog.log_dir() / 'exports').glob('*/observations.json'))
    assert len(exported) == 1
    rows = json.loads(exported[0].read_text(encoding='utf-8'))['entries']
    assert rows[0] == original and rows[1]['corrects'] == original['id']
    assert fieldlog.verify_export(exported[0].parent) == []


SOURCE_CASES = [
    ('Can you import and analyze PDFs?', 'pdf', 'pypdf'),
    ('Do you have Field Copy?', 'portable', 'make_usb'),
    ('Can you copy yourself to a USB drive?', 'portable', 'verify_usb'),
    ('Does your notebook use hashing or a chain?', 'chain', '_fingerprint'),
    ('How does your notebook hash chain work?', 'chain', 'SHA-256'),
    ('Where are my saved memories stored?', 'memory', '_write_facts'),
    ('Show me the code path for PDF import in Cursiv.', 'pdf', 'PdfReader'),
    ('What about your notebook hashing?', 'chain', '_fingerprint'),
]


@pytest.mark.parametrize('question,topic,witness', SOURCE_CASES)
def test_feature_answers_reach_checked_source_and_do_not_deny_witnesses(pipeline, monkeypatch, question, topic, witness):
    assert own.resolve(question) == topic
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: pytest.fail('Critical checked feature explanations are native'))
    text = final_reply(pipeline, question)
    assert witness in text and '.py' in text
    assert 'does not exist' not in text and 'not implemented' not in text


@pytest.mark.parametrize('question', ['Show my notebook entries for sample CM-743.',
    'Recall my test project.', 'Correct sample CM-743 temperature to 18.9 C.',
    'Verify the notebook chain for project ORION-742.'])
def test_record_operations_are_not_own_source_inspections(question):
    assert not own.resolve(question)


def test_short_memory_replacement_preserves_full_saved_fact():
    old = intents.command('remember my test sample is CM-742', [], person='dana').outcomes[0].records[0]
    result = intents.command('Correction: CM-743, not CM-742.', [], person='dana')
    assert result and result.ok
    active = semantic.list_facts('dana')
    assert len(active) == 1 and active[0]['text'] == 'my test sample is CM-743'
    assert active[0]['corrects'] == old['id']
    history = semantic.list_facts('dana', include_superseded=True)
    assert any(r['id'] == old['id'] and r['status'] == 'superseded' for r in history)
    assert 'CM-743' in intents.command('recall my test sample', [], person='dana').render()


def test_memory_fragment_never_changes_a_longer_identifier():
    intents.command('remember my test sample is CM-7429', [], person='dana')
    result = intents.command('Correction: CM-743, not CM-742.', [], person='dana')
    assert result and not result.ok
    assert semantic.list_facts('dana')[0]['text'] == 'my test sample is CM-7429'


def test_memory_fragment_changes_only_the_complete_value_in_a_sentence():
    intents.command('remember my sample is CM-742, distinct from CM-7429', [], person='dana')
    result = intents.command('Correction: CM-743, not CM-742.', [], person='dana')
    assert result.ok
    assert semantic.list_facts('dana')[0]['text'] == 'my sample is CM-743, distinct from CM-7429'


@pytest.mark.parametrize('target', ['identity', 'labelled_id'])
def test_memory_content_starting_with_id_and_explicit_id_label_both_work(target):
    old = intents.command('remember my identity label is researcher', [], person='dana').outcomes[0].records[0]
    query = 'identity' if target == 'identity' else 'ID: ' + old['id']
    result = intents.command('correct memory ' + query + ' to my identity label is scientist', [], person='dana')
    assert result.ok and result.outcomes[0].records[0]['corrects'] == old['id']


@pytest.mark.parametrize('draft', ['No evidence found in the notebook.', 'No matching Field Notebook entries.',
    'I cannot determine that from the available records.'])
def test_clean_uncertainty_or_empty_reads_are_not_overconfidence(draft):
    assert science_check.overconfidence_note('Is my sample safe?', draft) == ''


def test_native_provenance_skips_observation_warning_but_model_self_labels_do_not():
    q, d = 'Is my sample safe?', 'Yes, the result is safe (calculated by code).'
    assert science_check.overconfidence_note(q, d)
    assert not science_check.overconfidence_note(q, 'Yes, the arithmetic mean is 4.', authored='native')


@pytest.mark.parametrize('draft', ['Yes, 6', 'Yes, the mean of your readings is exactly 6.', 'Yes, definitely 6.'])
def test_real_calculation_provenance_exempts_pure_math_wording(draft):
    q = 'Calculate the mean of my sample readings: 3, 7, 8.'
    assert science_check.overconfidence_note(q, draft)
    assert science_check.overconfidence_note(q, draft, authored='calculation') == ''


@pytest.mark.parametrize('draft,noted', [('Yes, 6', False), ('Yes, 6 means the water is safe to drink.', True)])
def test_calculator_record_does_not_exempt_qualitative_model_overclaims(pipeline, monkeypatch, draft, noted):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: iter([draft]))
    out = final_reply(pipeline, 'Calculate the mean of my sample readings: 3, 7, 8.', review_mode='off')
    assert pipeline._WORKED and pipeline._WORKED.tool == 'stats'
    assert ('Cursiv\'s check: this answer sounds more certain' in out) == noted


def test_saved_casual_preference_reaches_existing_style_rules():
    from cursiv_engine.core import style
    intents.command('remember I prefer casual replies, like two researchers having coffee', [], person='dana')
    text = style.prompt_addendum('dana', 'Tell me about our next step.')
    assert 'two researchers having coffee' in text
    assert 'accuracy' in text and 'safety' in text


def approve(panel, monkeypatch):
    class RunNow:
        def __init__(self, target, args, daemon):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    monkeypatch.setattr(threading, 'Thread', RunNow)
    panel._answer_intent('save', next(iter(panel._intents)))
    _APP[0].processEvents()


def test_desktop_record_read_correct_verify_export_sequence(panel, monkeypatch):
    semantic.set_person('worksheet')
    panel._run_turn(RECORD, [])
    _APP[0].processEvents()
    assert fieldlog.entries() == []
    assert next(iter(panel._intents.values())).action.name == 'notebook.log'
    approve(panel, monkeypatch)
    original = fieldlog.entries()[0]
    panel._run_turn('Find sample CM-743.', [])
    _APP[0].processEvents()
    assert original['id'] in panel._transcript.toPlainText()
    correction = 'Correct sample CM-743 temperature to 18.9 C; reason: transcription error.'
    panel._run_turn(correction, [])
    _APP[0].processEvents()
    assert len(fieldlog.entries()) == 1
    assert next(iter(panel._intents.values())).action.name == 'notebook.correct'
    approve(panel, monkeypatch)
    assert fieldlog.entries()[1]['corrects'] == original['id']
    panel._run_turn('Verify the notebook chain for project ORION-742.', [])
    _APP[0].processEvents()
    assert 'all 2 entries' in panel._transcript.toPlainText()
    panel._run_turn('Export the notebook for project ORION-742.', [])
    _APP[0].processEvents()
    assert not (fieldlog.log_dir() / 'exports').exists()
    assert next(iter(panel._intents.values())).action.name == 'notebook.export'
    approve(panel, monkeypatch)
    files = list((fieldlog.log_dir() / 'exports').glob('*/observations.json'))
    assert len(json.loads(files[0].read_text(encoding='utf-8'))['entries']) == 2


def test_desktop_memory_correction_waits_on_card_and_keeps_lineage(panel, monkeypatch):
    semantic.set_person('dana')
    old = intents.command('remember my test sample is CM-742', [], person='dana').outcomes[0].records[0]
    panel._run_turn('Correction: CM-743, not CM-742.', [])
    _APP[0].processEvents()
    assert semantic.list_facts('dana')[0] == old
    proposal = next(iter(panel._intents.values()))
    assert proposal.action.name == 'memory.correct' and proposal.slots['fact'] == 'my test sample is CM-743'
    approve(panel, monkeypatch)
    current = semantic.list_facts('dana')[0]
    assert current['text'] == 'my test sample is CM-743' and current['corrects'] == old['id']


def test_memory_preview_staleness_cannot_correct_a_superseded_record(panel, monkeypatch):
    semantic.set_person('dana')
    old = intents.command('remember my test sample is CM-742', [], person='dana').outcomes[0].records[0]
    panel._run_turn('Correction: CM-743, not CM-742.', [])
    _APP[0].processEvents()
    semantic.update_fact(old['id'], 'my test sample is CM-744', person='dana')
    monkeypatch.setattr(panel, '_run_turn', lambda *a: pytest.fail('Stale memory edit must not run'))
    panel._answer_intent('save', next(iter(panel._intents)))
    assert semantic.list_facts('dana')[0]['text'] == 'my test sample is CM-744'


def test_unavailable_memory_on_approval_is_an_explicit_failure(panel, monkeypatch):
    semantic.set_person('dana')
    intents.command('remember my test sample is CM-742', [], person='dana')
    panel._run_turn('Correction: CM-743, not CM-742.', [])
    _APP[0].processEvents()
    monkeypatch.setattr(semantic, 'list_facts', lambda *a, **k: (_ for _ in ()).throw(OSError('unavailable')))
    panel._answer_intent('save', next(iter(panel._intents)))
    assert 'No correction was attempted' in panel._transcript.toPlainText()


def test_ambiguous_memory_fragment_requires_selection_then_preview():
    for text in ('my lake sample is CM-742', 'my marsh sample is CM-742'):
        intents.command('remember ' + text, [], person='dana')
    result = intents.command('Correction: CM-743, not CM-742.', [], person='dana', scope='x', preview_saves=True)
    assert result.clarification and len(semantic.list_facts('dana')) == 2
    picked = intents.command('1', [], person='dana', scope='x', preview_saves=True)
    assert picked.update_preview and not picked.outcomes
    assert all('CM-742' in r['text'] for r in semantic.list_facts('dana'))


def test_exact_project_filter_does_not_match_a_longer_code_or_note():
    row = saved()
    fieldlog.add(project='ORION-7429', sample_id='CM-744', note='mentions ORION-742')
    assert [r['id'] for r in field_recall.query(project='ORION-742')['records']] == [row['id']]
    assert [r['id'] for r in notebook_tools.command('Find project:ORION-742.', []).records] == [row['id']]


@pytest.mark.parametrize('question,topic', [(SOURCE_CASES[0][0], 'pdf'), (SOURCE_CASES[3][0], 'chain')])
def test_degraded_semantic_witnesses_return_unknown_without_feature_denial(question, topic):
    from cursiv_engine.core import source_analysis
    packet = own.prepare(question)
    assert packet and packet.analysis['feature_rules']
    degraded = dict(packet.analysis, feature_rules=None)
    text = source_analysis.native(degraded, topic)
    assert text.startswith('UNKNOWN:') and 'Searched installed source:' in text and '.py:' in text
    assert source_analysis.claim_issues(packet.analysis, 'Unknown, but Cursiv has no hashing or notebook verification.')


def test_saved_style_preference_is_not_taken_from_inference_or_another_person():
    from cursiv_engine.core import style
    semantic.add_fact('I prefer casual replies, like two researchers having coffee', person='other', source='manual', exact=True)
    semantic.add_fact('I prefer formal replies', person='dana', source='inferred', origin='inferred', exact=True)
    assert style.prompt_addendum('dana', 'Hello') == ''


def test_explicit_offline_status_control_is_application_owned(pipeline, monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate, 'is_offline', lambda: True)
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **kw: pytest.fail('Offline status is not inferred'))
    assert 'Offline mode is on.' in final_reply(pipeline, 'Is offline mode on?')


@pytest.mark.parametrize('draft,witness', [('Cursiv does not import PDFs.', 'PdfReader'),
    ('I cannot use Field Copy or copy portable workspaces.', 'make_usb'),
    ('There is no hashing or notebook verification.', '_fingerprint'),
    ('Cursiv has no persistent memory storage.', '_write_facts')])
def test_final_answer_guard_rechecks_core_denials_after_a_missed_route(pipeline, monkeypatch, draft, witness):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: iter([draft]))
    text = final_reply(pipeline, 'Tell me one useful thing about this app.', review_mode='off')
    assert witness in text and 'Checked installed source:' in text and 'Written by Cursiv' in text


def test_denial_recheck_honors_no_tools_and_scoped_access_limits(monkeypatch):
    from cursiv_engine.core import turn_policy, self_index
    monkeypatch.setattr(self_index, 'load', lambda *a: pytest.fail('No source read allowed'))
    with turn_policy.scope('No tools. Just talk.'):
        text = own.repair_capability_denial('Tell me about this app.', 'Cursiv does not import PDFs.')
        assert text.startswith('UNKNOWN:') and 'no source was read' in text
    assert own.repair_capability_denial('Read the attached file.', 'I cannot access your private PDF.') is None


def test_unrelated_feature_refusal_does_not_override_a_true_memory_claim(monkeypatch):
    from cursiv_engine.core import self_index
    monkeypatch.setattr(self_index, 'load', lambda *a: pytest.fail('No core feature was denied'))
    assert own.repair_capability_denial('Tell me about this app.',
        'Cursiv has no quantum weather engine, but does provide persistent memory.') is None
    assert own.repair_capability_denial('Tell me about this app.',
        'Persistent memory is available. Cursiv has no quantum weather engine.') is None

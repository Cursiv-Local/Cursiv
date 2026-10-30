"""U113 incidents: actual chat entry/stream/checker pipeline; only inference is stubbed."""
import json
import pytest
from cursiv_engine.core import science_check, self_inspection, self_index, last_turn, evidence_log
from test_background_review import pipeline


def final(ca, question, **kwargs):
    text=''
    for chunk in ca.chat(question, [], '', None, replace_draft=True, review_mode='off', **kwargs):
        if chunk.startswith(ca.REPLACE_SENTINEL):text=chunk[len(ca.REPLACE_SENTINEL):]
        else:text+=chunk
    return text


def test_reported_four_locations_through_chat(pipeline,monkeypatch):
    # Reconstructed wording: the owner supplied these values, not a full transcript.
    draft='Source locations: phases.py:64, claim_evidence.py:88, self_inspection.py:117, completion.py:120; all are source-code locations.'
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=final(pipeline,'Discuss a hypothetical plan.')
    assert draft in out
    assert 'additional scenario values' not in out and 'real measurements' not in out


def test_real_native_source_map_is_not_model_prose(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('Native source needs no inference'))
    out=final(pipeline,'Inspect your own source and show guardian functions, not hypothetical scenarios.')
    assert 'VERIFIED static source' in out
    assert 'No AI model was used for this declaration map.' in out
    assert 'additional scenario values' not in out


@pytest.mark.parametrize('location',[
    'phases.py:64, claim_evidence.py:88, self_inspection.py:117, completion.py:120',
    '`phases.py`, lines 64, 88, 117 and 120',
    'phases.py#L64-L88; completion.py:L117-L120',
    'phases.py at line 64 and lines 88, 117, 120',
])
def test_source_locator_numbers_are_not_scenario_measurements(location):
    assert not science_check.simulated_note('Explain a hypothetical code path.',location)


def test_matching_measurement_number_remains_a_measurement():
    note=science_check.simulated_note('Imagine an experiment.','phases.py:64; incubation took 64 hours.')
    assert '64' in note and 'result values' in note


@pytest.mark.parametrize('selection',['ollama','manager:openai::fixture-model'])
def test_exact_file_and_function_are_read_and_answered(pipeline,monkeypatch,selection):
    path='cursiv_engine/core/claim_evidence.py';reads=[];original=self_index.text
    def read(base,index,rel,*a,**k):
        reads.append(rel);return original(base,index,rel,*a,**k)
    monkeypatch.setattr(self_index,'text',read)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('Requested static target is native'))
    last_turn.diagnostics(True)
    try:
        out=final(pipeline,'Inspect cursiv_engine/core/claim_evidence.py and explain the function privacy_overclaim.',force_provider=selection)
        events=json.loads(last_turn.diagnostic_summary().split('\n',1)[1].rsplit('\nCommands:',1)[0])
    finally:last_turn.diagnostics(False)
    assert reads and reads[0]==path
    assert 'privacy_overclaim' in out and path in out and 'VERIFIED' in out
    assert any(r['event']=='evidence_returned' and r.get('path')==path for r in events)
    assert any(r['event']=='routing' and r.get('route')=='installed_source' for r in events)
    assert any(r['event']=='response_origin' and r.get('provider')=='none' for r in events)
    assert not any(r['event'] in ('transport','provider_attempt') for r in events)


@pytest.mark.parametrize('prefix',['No tools. ','Do not inspect any files. '])
def test_target_read_cannot_bypass_denial(pipeline,monkeypatch,prefix):
    monkeypatch.setattr(self_index,'text',lambda *a,**k:pytest.fail('No read authorized'))
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No model needed for denial'))
    out=final(pipeline,prefix+'Inspect cursiv_engine/core/claim_evidence.py and function privacy_overclaim.')
    assert 'disabled' in out or 'DENIED' in out


@pytest.mark.parametrize('draft',[
    'The documentation example says "the tests passed". This is not a runtime test report.',
    'The literal is `Cursiv is completely private`. It is an example, not a privacy guarantee.',
    'The result is not fully verified. More evidence is needed.',
])
def test_quoted_or_negated_claims_do_not_trigger_interference(pipeline,monkeypatch,draft):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=final(pipeline,'Explain the wording of this software example.')
    assert draft in out
    assert "Cursiv's check:" not in out and 'withdrawn' not in out


@pytest.mark.parametrize('draft',[
    'Example only: "No model was used." This is a quoted message.',
    'Source example:\n```python\nmessage = "No model was used."\n# Verified: True\n```\nThis is literal code.',
    'The quoted claim "I used a calculation tool" is an example, not an execution report.',
    'The quoted message "I saved this to memory" is an example, not a save receipt.',
])
def test_literal_examples_survive_all_postprocessors(pipeline,monkeypatch,draft):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=final(pipeline,'Discuss wording examples in software documentation.')
    assert draft in out
    assert 'withdrawn' not in out and "Cursiv's check:" not in out


@pytest.mark.parametrize('draft',[
    'I used a calculation tool for this answer.',
    'I saved this to memory.',
    'I searched the web for this answer.',
])
def test_actual_false_execution_claims_still_cannot_pass(pipeline,monkeypatch,draft):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=final(pipeline,'Discuss the requested operation.')
    assert 'withdrawn' in out or out.startswith('Action not confirmed:')
    assert not out.startswith(draft)


@pytest.mark.parametrize('question',[
    'Inspect `cursiv_engine/core/claim_evidence.py`, function named `privacy_overclaim`.',
    "Inspect claim_evidence.py and function 'privacy_overclaim'.",
    'Inspect the implementation of function privacy_overclaim.',
])
def test_explicit_target_wordings_share_the_same_verified_target(pipeline,monkeypatch,question):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('Native target needs no model'))
    out=final(pipeline,question)
    assert 'cursiv_engine/core/claim_evidence.py:' in out and 'privacy_overclaim' in out and 'VERIFIED' in out


def test_target_priority_under_existing_small_budget():
    from cursiv_engine.core import source_analysis
    result=source_analysis.collect('Inspect cursiv_engine/core/claim_evidence.py function privacy_overclaim.','target',
        limits=source_analysis.Limits(files=1,calls=2,depth=0))
    assert result['status']=='VERIFIED'
    assert result['requested_targets']==[('cursiv_engine/core/claim_evidence.py','privacy_overclaim')]
    assert result['evidence'][0]['path']=='cursiv_engine/core/claim_evidence.py'


def test_missing_target_never_substitutes_a_generic_architecture(pipeline,monkeypatch):
    reads=[];read=self_index.text
    def capture(base,index,path,*a,**kw):reads.append(path);return read(base,index,path,*a,**kw)
    monkeypatch.setattr(self_index,'text',capture)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**kw:pytest.fail('No invented explanation'))
    out=final(pipeline,'Inspect cursiv_engine/core/claim_evidence.py function nonexistent_audit_target.')
    assert reads==['cursiv_engine/core/claim_evidence.py']
    assert 'UNKNOWN' in out or 'NOT FOUND' in out


def test_restricted_target_remains_outside_source_inventory(pipeline,monkeypatch):
    monkeypatch.setattr(self_index,'text',lambda *a,**kw:pytest.fail('Station remains excluded'))
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**kw:pytest.fail('No model fallback'))
    out=final(pipeline,'Inspect cursiv_engine/station/server.py function start_server.')
    assert 'ACCESS DENIED' in out


def test_bad_citation_is_a_source_problem_not_a_scientific_measurement(pipeline,monkeypatch):
    from cursiv_engine.core import source_analysis
    monkeypatch.setattr(source_analysis,'native',lambda *a:None)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**kw:iter(['See cursiv_engine/core/claim_evidence.py:999999.']))
    out=final(pipeline,'Inspect your source and trace guardian checks, not hypothetical scenarios.')
    assert 'Source explanation withheld' in out and 'not supplied' in out
    assert 'additional scenario values' not in out


def test_invented_measurements_still_get_one_relevant_note(pipeline,monkeypatch):
    draft='| Trial | Measured result |\n| 1 | 12.3 |\n| 2 | 13.7 |'
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**kw:iter([draft]))
    out=final(pipeline,'Imagine an experiment comparing soil moisture.')
    assert 'invented for illustration' in out and out.count('additional result values')==1


@pytest.mark.parametrize('question',[
    'Do not invent hypothetical results. Explain the supplied records.',
    'This is not a hypothetical scenario. Explain the result.',
    'Explain the term "hypothetical" in documentation.',
])
def test_negated_or_literal_simulation_requests_are_not_simulations(question):
    assert not science_check.simulated_note(question,'The case identifier is 743.')



def test_quoted_value_does_not_hide_a_real_self_certification(pipeline,monkeypatch):
    draft='The proposed interpretation needs checking.\nVerified: "Yes"'
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=final(pipeline,'Discuss a research interpretation.')
    assert 'The proposed interpretation needs checking.' in out
    assert 'Verified:' not in out



@pytest.mark.parametrize('owner',['my','attached','selected','uploaded'])
def test_exact_installed_basename_does_not_capture_a_user_file(owner):
    assert not self_inspection.resolve(f'Inspect {owner} file claim_evidence.py function privacy_overclaim.')


def test_user_file_request_keeps_workspace_authorization(pipeline,monkeypatch):
    monkeypatch.setattr(self_index,'text',lambda *a,**k:pytest.fail('User-file request must not inspect installed source'))
    out=final(pipeline,'Read my file claim_evidence.py and explain function privacy_overclaim.')
    assert 'File access is off' in out or 'workspace' in out.lower()


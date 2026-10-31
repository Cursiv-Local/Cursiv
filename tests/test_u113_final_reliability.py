"""Final worksheet: synthetic drafts and real pipeline, never live providers."""
import json
import pytest
from cursiv_engine.core import claims,claim_evidence,science_check,verify,self_index,last_turn
from cursiv_engine.chat import provider_manager as manager,provider_settings as settings,provider_adapters as adapters
from cursiv_engine.chat.provider_types import ProviderError,ErrorCode
from test_background_review import pipeline

MARS=('Six astronauts are aboard a fictional Mars field station. Oxygen reserve is 74%, water reserve is 81%, '
      'and battery capacity is 63%. Earth communications are unavailable for 180 days. No consumption rates, '
      'reserve capacities, equipment diagnostics, or critical thresholds are provided. Are they safe, and how long can they survive?')
CORRECTION=('The 74%, 81%, 63% reserves and the 180-day communications outage are supplied scenario inputs, not '
 'independently verified observations. My earlier critical threshold was unsupported. Capacities, consumption rates '
 'and operating limits are missing, so safety and remaining lifetime cannot be determined from these percentages.')

def run(ca,text,history=None,**kw):
    output=''
    for chunk in ca.chat(text,history or [],'',None,replace_draft=True,review_mode='off',**kw):
        output=chunk[len(ca.REPLACE_SENTINEL):] if chunk.startswith(ca.REPLACE_SENTINEL) else output+chunk
    return output


def test_A_exact_worksheet_request_returns_decision_and_return_evidence(pipeline,monkeypatch):
    reads=[];original=self_index.text
    def read(base,index,path,*a,**k):reads.append(path);return original(base,index,path,*a,**k)
    monkeypatch.setattr(self_index,'text',read)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('Native target must not infer'))
    out=run(pipeline,'Inspect `cursiv_engine/core/claim_evidence.py`, read the actual implementation of '
        '`privacy_overclaim`, and explain its parameters, return values, and decision logic using verified source evidence.')
    assert reads[0]=='cursiv_engine/core/claim_evidence.py'
    assert 'privacy_overclaim' in out and 'answer: str' in out and 'question: str' in out
    assert 'not triggered' in out and 'return' in out.lower()
    assert 'additional scenario values' not in out


def test_B_exact_worksheet_locations_are_not_measurements():
    assert not science_check.simulated_note('Explain a hypothetical code path.',
        'completion.py:64; claim_evidence.py:88; turn_policy.py:117; phases.py:120')
    assert science_check.simulated_note('Imagine an experiment.','completion.py:64; time elapsed 64 hours.')


def test_D_visible_mathematical_verification_is_not_execution():
    text='The arithmetic is verified by substitution: 12 * 250 = 3 * 1000 = 3000.'
    assert not claims.tool_notes(text,claims.Evidence())
    assert not claim_evidence.unbacked(text,[])
    assert not verify.arithmetic_problems(text)
    assert verify.arithmetic_problems('12 * 250 = 3 * 900 = 3000.')


def test_D_dilution_actual_native_path(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter(['C1V1 = C2V2. Final volume 1000 mL; add 750 mL water.']))
    out=run(pipeline,'A researcher has 250 mL of a 12% salt solution and needs to dilute it to 3%. '
       'Calculate the final volume and water to add. Show the formula and verify the arithmetic.')
    assert '750' in out and ('1000' in out or '1,000' in out or '1 L' in out)
    assert 'withdrawn' not in out and 'no calculation tool ran' not in out


@pytest.mark.parametrize('draft',[
 'The supplied scenario states oxygen 74%, water 81%, battery 63%, and no Earth communications for 180 days. These are supplied inputs, not independently verified observations.',
 'This assessment is grounded in the evidence you supplied: oxygen 74%, water 81%, battery 63%, and 180 days without Earth communications.',
])
def test_E_user_supplied_inputs_do_not_require_external_lookup(pipeline,monkeypatch,draft):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=run(pipeline,'Oxygen reserve is 74%, water reserve is 81%, and battery capacity is 63%. Earth communications are unavailable for 180 days.')
    assert draft in out and 'withdrawn' not in out and 'no reference' not in out


def test_G_valid_uncertainty_survives(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([CORRECTION]))
    out=run(pipeline,MARS)
    assert CORRECTION in out and 'withdrawn' not in out and 'clinician' not in out


@pytest.mark.parametrize('draft',[
 'The crew are safe. Oxygen at 74% is above a critical threshold of 30%. They can survive 180 days.',
 'The supplies will last 180 days.',
])
def test_G_unsupported_resource_safety_and_runtime_are_checked(pipeline,monkeypatch,draft):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([draft]))
    out=run(pipeline,MARS)
    assert 'consumption' in out.lower() and ('cannot' in out.lower() or "can't" in out.lower())
    assert 'clinician' not in out and '911' not in out
    assert 'unsupported action or source claim is withdrawn' not in out


def test_H_substantive_correction_survives(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter([CORRECTION]))
    history=[dict(role='user',content=MARS),dict(role='assistant',content='The crew are safe above the critical 30% threshold for 180 days.')]
    out=run(pipeline,'Review your previous Mars station assessment. Identify unsupported thresholds, assumptions, '
       'or conclusions, and correct them using only the supplied information.',history)
    assert CORRECTION in out and 'unsupported action or source claim is withdrawn' not in out


def test_provider_switches_and_offline_transitions_use_only_mocked_adapters(pipeline,monkeypatch,tmp_path):
    from cursiv_engine.core import netgate
    offline={'value':False};sent=[]
    monkeypatch.setattr(settings,'FILE',tmp_path/'providers.json')
    monkeypatch.setattr(settings,'CREDENTIALS',tmp_path/'device'/'credentials.json')
    monkeypatch.setattr(settings,'key',lambda p:'synthetic-credential')
    monkeypatch.setattr(netgate,'is_offline',lambda:offline['value'])
    monkeypatch.setattr(netgate,'allowed',lambda:not offline['value'])
    def stream(req,result,key):
        sent.append((req.provider,req.model))
        result.text='A mocked research summary.';result.responding_provider=req.provider
        result.actual_model='reported-'+req.model;result.finish_reason='stop'
        yield result.text
    monkeypatch.setattr(adapters,'stream',stream)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No legacy fallback'))
    for provider in ('ollama','openai','groq','ollama'):
        with manager.turn_options(research_authorized=True):
            out=run(pipeline,'Summarize this synthetic research discussion.',force_provider='manager:'+provider+'::chosen-'+provider)
        assert sent[-1]==(provider,'chosen-'+provider)
        assert 'reported-chosen-'+provider in out and 'A mocked research summary.' in out
    offline['value']=True;before=len(sent)
    with manager.turn_options(research_authorized=True):
        out=run(pipeline,'Summarize this synthetic research discussion.',force_provider='manager:groq::chosen-groq')
    assert len(sent)==before and 'offline' in out.lower() and 'Groq' in out
    offline['value']=False
    with manager.turn_options(research_authorized=True):
        out=run(pipeline,'Summarize this synthetic research discussion.',force_provider='manager:openai::chosen-openai')
    assert sent[-1]==('openai','chosen-openai') and 'reported-chosen-openai' in out


def test_mocked_groq_error_keeps_actual_destination_and_never_falls_back(pipeline,monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'is_offline',lambda:False);monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(settings,'key',lambda p:'synthetic-credential')
    calls=[]
    def fail(req,result,key):
        calls.append(req.provider)
        raise ProviderError('groq',ErrorCode.TIMEOUT)
        yield
    monkeypatch.setattr(adapters,'stream',fail)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No fallback'))
    with manager.turn_options(research_authorized=True):
        out=run(pipeline,'Discuss synthetic observations.',force_provider='manager:groq::chosen-groq')
    assert calls==['groq'] and 'Groq' in out and 'OpenAI' not in out
    assert manager.snapshot().model=='chosen-groq'

def diagnostic_rows():
    return json.loads(last_turn.diagnostic_summary().split('\n',1)[1].rsplit('\nCommands:',1)[0])


def test_diagnostic_commands_and_offered_versus_executed():
    import chat_commands
    from cursiv_engine.core import tools,turn_policy
    assert 'Diagnostics on' in chat_commands.handle_command('self diagnostics on',{},[]).text
    try:
        tools.plan('Convert units.',lambda _: '{"calls":[]}',files=False)
        rows=diagnostic_rows()
        assert any(r['event']=='tools_offered' for r in rows)
        assert not any(r['event']=='tool_result' for r in rows)
        tools.run([dict(tool='system_info',args={})],policy=turn_policy.Policy(False,False,False,False))
        assert any(r['event']=='tool_result' and r['status']=='denied' for r in diagnostic_rows())
        assert '"event"' in chat_commands.handle_command('self diagnostics show',{},[]).text
    finally:
        off=chat_commands.handle_command('self diagnostics off',{},[]).text
    assert 'Diagnostics off' in off and not diagnostic_rows()


def test_diagnostics_source_permission_error_never_reports_a_read(pipeline,monkeypatch):
    def denied(*a,**kw):raise PermissionError('synthetic denial')
    monkeypatch.setattr(self_index,'text',denied)
    last_turn.diagnostics(True)
    try:
        out=run(pipeline,'Inspect cursiv_engine/core/claim_evidence.py function privacy_overclaim.')
        rows=diagnostic_rows()
    finally:last_turn.diagnostics(False)
    assert 'ACCESS DENIED' in out
    assert any(r['event']=='source_read_denied' for r in rows)
    assert not any(r['event']=='source_read' for r in rows)


def test_numeric_equalities_check_each_side_and_each_chain_link():
    assert not verify.arithmetic_problems('12 * 250 = 3 * 1000 = 3000.')
    assert verify.arithmetic_problems('12 * 250 = 3 * 1000 = 4000.')
    assert verify.arithmetic_problems('12 * 250 = 3 * 900 = 3000.')
    assert not verify.arithmetic_problems('1 * 2 = 6 / 3.')


def test_tool_claim_and_independent_review_still_require_actual_evidence():
    assert claims.tool_notes('I verified this using a calculator tool.',claims.Evidence())
    assert claims.reference_notes('This answer is based on professionally reviewed evidence you supplied: 74%.',
        claims.Evidence(question='Reserve74%.'))
    assert claims.reference_notes('This answer is grounded in the evidence you supplied: 99%.',
        claims.Evidence(question='Reserve74%.'))


def test_supplied_inputs_in_prior_user_turn_survive_correction_provenance(pipeline,monkeypatch):
    draft='This correction is grounded in the evidence you supplied: 74%, 81%, 63%, 180 days. No independent verification is claimed.'
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**kw:iter([draft]))
    out=run(pipeline,'Correct the earlier assessment using only my supplied values.',
        [dict(role='user',content=MARS),dict(role='assistant',content='Earlier unsupported assessment.')])
    assert draft in out and 'withdrawn' not in out


def test_resource_derivation_with_given_rates_is_not_rejected():
    ev=claims.Evidence(question='Oxygen capacity is100 L and consumption is10 L per day. No Earth contact for180 days.')
    assert not claims.certainty_notes('The supplies will last10 days.',ev)
    ev=claims.Evidence(question=MARS)
    assert not claims.certainty_notes('If the capacity and consumption are known, the supplies can last180 days.',ev)


@pytest.mark.parametrize('pending',[{}, {'operation':'write'}])
def test_workspace_preview_is_not_reported_as_executed(pipeline,monkeypatch,pending):
    from types import SimpleNamespace
    from cursiv_engine.core import file_access
    reply=SimpleNamespace(text='Synthetic file result.',pending=pending,
        receipts=[SimpleNamespace(operation='write',ok=True)])
    monkeypatch.setattr(file_access,'command',lambda *a,**kw:reply)
    last_turn.diagnostics(True)
    try:
        run(pipeline,'Discuss this synthetic filesystem result.')
        rows=diagnostic_rows()
    finally:last_turn.diagnostics(False)
    results=[r for r in rows if r['event']=='tool_result']
    assert bool(results)==(not bool(pending))
    assert any(r['event']=='response_origin' and r['provider']=='none' for r in rows)


def test_source_read_limits_stop_before_actual_reads(monkeypatch):
    from cursiv_engine.core import source_analysis
    from cursiv_engine.core import self_source
    base=self_source.root();index=self_index.load(base,self_source.version())
    path='cursiv_engine/core/claim_evidence.py'
    monkeypatch.setattr(self_index,'text',lambda *a,**kw:pytest.fail('Exhausted budget must prevent reads'))
    for key,value in [('attempts',1),('calls',1),('characters',1000)]:
        session=source_analysis.Session(base,index,source_analysis.Limits(files=1,calls=1,characters=1000))
        setattr(session,key,value)
        assert session.read(path) is None and session.limited
        assert not session.texts

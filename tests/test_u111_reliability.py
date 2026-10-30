"""U111 reconstructed incidents, frozen before deterministic repairs."""
import json
from pathlib import Path
import pytest
from cursiv_engine.core import notebook_tools as nt, notebook_proposals as np, intent, science_check as sc
from test_background_review import pipeline
from test_chat_feedback import panel
from test_live_test_followup import final_reply

CORPUS = json.loads((Path(__file__).parents[1] / 'bench/u111-reliability.json').read_text(encoding='utf-8'))
WRITING = [c['question'] for c in CORPUS['cases'] if c['id'] in ('roast', 'roast-restricted', 'promotional')]

@pytest.mark.parametrize('question', WRITING + [
    'Write a promotional description of my field notebook',
    'For a hypothetical scene, a researcher says "save pH 7 in my field notebook". Write a caption.',
    'Write an X post with the quoted example "log site: Pond; pH 7".',
])
def test_writing_is_not_an_operation(question):
    assert not nt.is_request(question, [])
    assert not intent.might_be_action(question)
    assert np.record(question) is None

def test_real_observation_still_requires_confirmation(panel,monkeypatch):
    from cursiv_engine.ui import chat_app
    monkeypatch.setattr(chat_app,'_local_model_ready',lambda:pytest.fail('The observation parser must not need a model'))
    p = panel._propose_action('Record water temperature 21.4°C at Willow Basin')
    assert p and p.ok and p.needs_confirm
    assert 'Willow Basin' in p.command and '21.4' in p.command

def test_separate_real_operation_keeps_quoted_note_in_confirmation():
    q = 'Write a post about research. Separately, record field observation: site: Pond; pH 7; note: "write a funny caption"'
    proposal = np.record(q)
    assert proposal and proposal.needs_confirm
    assert 'write a funny caption' in proposal.command and 'pH 7' in proposal.command

def test_explicit_record_keeps_unquoted_creative_words_as_observation_data():
    proposal=np.record('Record field observation: site: Pond; pH 7; note: write a story about frogs')
    assert proposal and proposal.needs_confirm and 'write a story about frogs' in proposal.command

@pytest.mark.parametrize('q',[
    'Discuss the example “save this in my field notebook”.',
    'In a hypothetical scene, someone would write data in the field notebook.',
    'Write a caption with `log site: Pond; pH 7`.',
])
def test_quoted_and_hypothetical_actions_are_inert(q):
    assert not nt.is_request(q,[])
    assert not intent.might_be_action(q)

def test_prepared_constraints_survive_compaction_without_unbounded_history(pipeline):
    from cursiv_engine.core import reasoning_context as rc
    history=[dict(role='user',content='Mars communications are unavailable during the first six months.')]
    context=rc.prompt('What should we do about oxygen?',history)
    messages=[dict(role='system',content='Persona'),dict(role='system',content=context),
        *[dict(role='user',content='Unrelated geology '+('x'*500)) for _ in range(30)],
        dict(role='user',content='What should we do about oxygen?')]
    slim=pipeline._slim(messages,7000)
    assert any('first six months' in m['content'] for m in slim if m['role']=='system')
    assert sum(len(m['content']) for m in slim)<=7000

def test_retrieved_project_constraints_are_labeled_and_checked():
    from cursiv_engine.core import reasoning_context as rc
    memory='Mars mission: Earth communications are unavailable during the first six months.'
    prompt=rc.prompt('What should we do about oxygen?',[],memory)
    assert 'not independently verified' in prompt
    assert rc.contradiction_note('What should we do about oxygen?','Contact Mission Control now.',[],memory)

def test_restored_connectivity_supersedes_the_old_constraint():
    from cursiv_engine.core import reasoning_context as rc
    history=[dict(role='user',content='Mars communications are unavailable during the first six months.'),
        dict(role='user',content='Mars communications have been restored.')]
    assert not rc.constraints('Can we contact Earth?',history)

def test_real_calculation_and_supplied_values_are_not_fabricated():
    q='Hypothetical inputs: 4 crew, 11 days.'
    d='| Crew | 4 |\n| Days | 11 |\n| Crew days | 44 |'
    assert not sc.simulated_note(q,d,calculated='4 * 11 = 44')

def test_a_supported_threshold_is_not_called_unsupported():
    from cursiv_engine.core import verify
    assert not verify.citation_problems('', 'EPA document: test limit 6.5.', 'The EPA limit is 6.5.')

@pytest.mark.parametrize('month,noted',[(2,True),(6,True),(7,False)])
def test_blackout_condition_expires_without_inventing_a_survey_date(month,noted):
    from cursiv_engine.core import reasoning_context as rc
    history=[dict(role='user',content='Mars communications are unavailable during the first six months.')]
    note=rc.contradiction_note(f'We are in mission month {month}. Can we contact Earth?', 'Contact Mission Control now.',history)
    assert bool(note)==noted
    if note: assert 'timing is unspecified' not in note

def test_denial_of_an_available_constraint_gets_the_actual_user_quote():
    from cursiv_engine.core import reasoning_context as rc
    said='Mars communications are unavailable during the first six months.'
    note=rc.contradiction_note('Was there any mission constraint?', 'No mission constraint prevents contact with Earth.',[dict(role='user',content=said)])
    assert said in note and 'If still within' in note

def test_self_review_invented_quote_is_checked_end_to_end(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:iter(['I previously said "The mine is definitely responsible". That was wrong.']))
    history=[dict(role='assistant',content='The low pH may indicate a problem.')]
    out=final_reply(pipeline,'Review your previous answer.',history,review_mode='off')
    assert 'not in the available earlier answers' in out

def test_preview_and_confirmation_are_real_without_a_model(panel,monkeypatch):
    from cursiv_engine.core import fieldlog
    from cursiv_engine.ui import chat_app
    monkeypatch.setattr(chat_app,'_local_model_ready',lambda:pytest.fail('No model needed'))
    question='Record water temperature 21.4°C at Willow Basin'
    panel._begin_turn(question)
    panel._run_turn(question,[])
    assert not fieldlog.entries()
    proposal=next(iter(panel._intents.values()))
    assert proposal and proposal.ok and proposal.needs_confirm
    from test_u109_postrelease import approve
    approve(panel,monkeypatch)
    entries=fieldlog.entries()
    assert len(entries)==1 and entries[0]['site']=='Willow Basin'
    import chat_commands
    result=chat_commands.handle_command('What observations have I saved at Willow Basin?',{},[])
    assert result and entries[0]['id'] in result.text
    assert fieldlog.verify()==[]

@pytest.mark.parametrize('question', [
    'Our Mars oxygen production declined 17%. Are our instrument readings safe?',
    'Our radiation instruments disagree. Is this safe?',
])
def test_mars_warning_is_domain_relevant(question):
    note = sc.overconfidence_note(question, 'Yes, it is safe.')
    assert note
    assert 'lab' not in note and 'health authority' not in note

def test_no_one_can_say_is_uncertainty_not_a_settled_no_verdict():
    assert not sc.overconfidence_note('I saw foam below the weir. Is it pollution?',
        'Not necessarily.\nNo one can say for sure without seeing or testing the water.')

def test_communicate_with_earth_wording_keeps_timing_conditional():
    from cursiv_engine.core import reasoning_context as rc
    history=[dict(role='user',content='Earth communications are unavailable for the first six months.')]
    note=rc.contradiction_note('What should we do about oxygen?',
        'Communicate with Earth. But Earth communications are unavailable for the first six months, so no real-time help is possible.',history)
    assert 'timing' in note and 'unspecified' in note and 'If the survey is within' in note

def test_water_caution_remains():
    assert 'lab' in sc.overconfidence_note('My water sample looks clear. Is it safe to drink?', 'Yes, it is safe to drink.')

def test_supplied_hypothetical_table_is_not_invented():
    q = 'Fictional Mars mission: production declined 17%, 11 reserve days, 4 crew.'
    d = '| Input | Supplied value |\n| Decline | 17% |\n| Reserve | 11 days |\n| Crew | 4 |'
    assert not sc.simulated_note(q, d)

def test_word_numbers_supplied_by_user_are_not_new_model_values():
    assert not sc.simulated_note('Fictional mission: four crew, eleven reserve days.',
        '| Crew | 4 |\n| Reserve | 11 days |')

def test_failed_length_revision_uses_only_a_complete_supported_prefix(pipeline,monkeypatch):
    draft='The Mars botanist forgot to water a plastic plant. It filed a complaint. '+('Still filing. '*40)
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**kw:iter([draft]))
    calls=[]
    monkeypatch.setattr(pipeline,'_local_llm',lambda *a,**kw:calls.append(1) or draft)
    out=final_reply(pipeline,'Write one funny X post about a plastic plant. Under 280 characters; output only the post.',review_mode='off')
    assert len(calls)==1 and len(out)<280 and out.endswith('.')
    assert draft.startswith(out) and not out.startswith('I could not')

def test_unknown_survey_timing_does_not_make_blackout_current():
    from cursiv_engine.core import reasoning_context as rc
    history=[dict(role='user',content='Earth communications are unavailable for the first six months.')]
    draft='Since Earth comms are unavailable for the first six months, this is not possible. So, the crew must act independently.'
    note=rc.contradiction_note('What should we do about oxygen?',draft,history)
    assert 'survey timing is unspecified' in note and 'If the survey is within' in note

def test_report_to_earth_advice_preserves_unknown_survey_timing():
    from cursiv_engine.core import reasoning_context as rc
    history=[dict(role='user',content='Earth communications are unavailable for the first six months.')]
    note=rc.contradiction_note('What should we do about oxygen?',
        'Report to mission control—even though Earth comms are off for the first six months, the crew should log this event.',history)
    assert 'timing' in note.lower() and 'unspecified' in note.lower() and 'if' in note.lower()

def test_few_new_hypothetical_numbers_are_still_not_observations():
    note=sc.simulated_note('Fictional Mars inputs: 17% decline, 11 days reserve, four crew.',
        'The system produces 83% of normal. Set a 3–5 day deadline.')
    assert 'assumptions or model-derived' in note and 'inputs are not invented' in note

def test_table_format_does_not_resolve_sample_count_conflicts():
    note=sc.grounding_note('The notes say three samples but the table lists four IDs.',
        'The table is a direct record, so it is more reliable.')
    assert 'conflicting sample totals are unresolved' in note

def test_another_agencys_limit_does_not_support_the_claim():
    from cursiv_engine.core import verify
    assert verify.citation_problems('', 'EPA inspected the site. WHO example limit 6.5.', 'The EPA limit is 6.5.')

def test_fabricated_experimental_table_still_noted():
    assert sc.simulated_note('Imagine an experiment.', '| Trial | Measured result |\n| 1 | 12.3 |\n| 2 | 13.7 |')

def test_short_form_final_delivery_has_enforced_length(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter(['Cursiv stores notes. ' * 30]))
    monkeypatch.setattr(pipeline, '_local_llm', lambda *a, **k: 'Cursiv: your field notes got their own AI intern.')
    out = final_reply(pipeline, 'Write one funny X post about a robot. Under 280 characters; output only the post.', review_mode='off')
    assert len(out) <= 280
    assert 'Sources:' not in out and 'Answered by' not in out

def test_restricted_writing_reaches_model_without_notebook_reads(pipeline, monkeypatch):
    from cursiv_engine.core import fieldlog
    monkeypatch.setattr(fieldlog, 'entries', lambda *a, **k: pytest.fail('No notebook read'))
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **k: iter(['Cursiv: even your field notes need a supervisor.']))
    out = final_reply(pipeline, WRITING[1], review_mode='off')
    assert 'need a supervisor' in out
    assert 'details needed' not in out

def test_unsupported_agency_threshold_requires_actual_source_even_if_named():
    from cursiv_engine.core import verify
    issues = verify.citation_problems('Do not invent EPA thresholds.', '', 'The EPA limit is pH 6.5.')
    assert issues

def test_invented_self_review_quotation_is_flagged():
    from cursiv_engine.core import claims
    ev = claims.Evidence(question='Review your previous answer.', earlier=['The low pH may indicate a problem.'])
    assert claims.problems('I previously said "The mine is definitely responsible". That was wrong.', ev)

def test_blackout_contradiction_is_flagged_without_model_review(pipeline, monkeypatch):
    history = [dict(role='user', content='Mars Expedition 2031: Earth communications are unavailable during the first six months. The survey date is unspecified.')]
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: iter(['Contact Mission Control now for instructions.']))
    out = final_reply(pipeline, 'What should we do about declining oxygen production?', history, review_mode='off')
    assert 'six months' in out and ('unspecified' in out or 'if' in out.lower())

def test_unsupported_mine_confirmation_gets_a_claim_specific_check(pipeline, monkeypatch):
    monkeypatch.setattr(pipeline, '_call_ollama', lambda *a, **kw: iter(['Acid mine drainage is confirmed. The EPA limit is pH 6.5.']))
    out = final_reply(pipeline, 'Our three stream samples have pH 7.1, 3.2 and 6.8 near an abandoned mine. What explains this?', review_mode='off')
    assert 'not confirmed' in out.lower() or 'hypothesis' in out.lower()
    assert 'unsupported' in out.lower() or 'not established' in out.lower()

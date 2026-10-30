"""Explicit backend contracts; synthetic transport evidence, no paid/live cloud calls."""
import json
import pytest
from cursiv_engine.chat import model_selection as selection
from test_background_review import pipeline
from test_chat_feedback import panel
from test_live_test_followup import final_reply

@pytest.fixture(autouse=True)
def isolate_provenance_records(monkeypatch):
    from cursiv_engine.core import last_turn
    from cursiv_engine.ui import chat_app
    token=selection._response.set(None)
    monkeypatch.setattr(last_turn,'_state',{})
    monkeypatch.setattr(chat_app,'_ANSWERED_BY','')
    try:
        from cursiv_engine.chat.provider_manager import turn_options
        # Synthetic transport tests explicitly authorize their synthetic context.
        with selection.use(None),selection.provenance_scope(False),turn_options(research_authorized=True): yield
    finally: selection._response.reset(token)

@pytest.mark.parametrize('provider',selection.PROVIDERS)
def test_exact_selection_round_trip(provider):
    assert selection.parse(provider+'::account-model:4b') == selection.Selection(provider,'account-model:4b')

@pytest.mark.parametrize('value',['unknown::anything','openai::bad model','ollama::','openai::bad\nmodel'])
def test_invalid_selection_is_not_a_provider_guess(value):
    with pytest.raises(ValueError): selection.parse(value)

def test_cloud_choice_offline_never_calls_local_or_cloud(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No fallback'))
    monkeypatch.setattr(pipeline,'_call_openai_direct',lambda *a,**k:pytest.fail('Offline'))
    out = final_reply(pipeline,'Explain how sediment settles.',force_provider='openai::account-model',review_mode='off')
    assert 'offline mode' in out and 'No fallback' in out and 'Answered by' not in out

def test_uninstalled_explicit_local_never_downloads(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_ollama_pulled_models',lambda:set())
    monkeypatch.setattr(pipeline,'_pull_ollama_model',lambda *a,**k:pytest.fail('No download'))
    out=final_reply(pipeline,'Explain sediment.',force_provider='ollama::missing-model',review_mode='off')
    assert 'not installed' in out and 'Answered by' not in out

def test_cloud_failure_has_selected_provider_attribution(pipeline,monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(pipeline,'_saved_key',lambda f:'synthetic-test-value')
    monkeypatch.setattr(pipeline,'_call_openai_direct',lambda *a,**k:iter(['[OpenAI error 429]']))
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No fallback'))
    out=final_reply(pipeline,'Explain sediment.',force_provider='openai::account-model',review_mode='off')
    assert 'OpenAI / account-model failed' in out and 'Answered by' not in out

def test_failed_exact_backend_never_starts_a_local_checker(pipeline,monkeypatch):
    monkeypatch.setattr(pipeline,'_router_llm',lambda *a,**k:pytest.fail('No local reviewer after a selected-provider failure'))
    monkeypatch.setattr(pipeline,'_call_ollama',lambda *a,**k:pytest.fail('No local fallback'))
    out=final_reply(pipeline,'Double-check this claim about sediment.',force_provider='openai::account-model',review_mode='full')
    assert 'offline mode' in out and 'Answered by' not in out

def test_exact_success_keeps_code_checks_without_rewriting_via_another_model(pipeline,monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(pipeline,'_saved_key',lambda f:'synthetic-test-value')
    monkeypatch.setattr(pipeline,'_router_llm',lambda *a,**k:pytest.fail('No alternate reviewer model'))
    def respond(*a,**kw):
        selection.record(pipeline._runtime(),'openai','account-model','actual-model')
        yield 'Sediment alone does not identify the pollution source.'
    monkeypatch.setattr(pipeline,'_call_openai_direct',respond)
    out=final_reply(pipeline,'Double-check this claim: sediment identifies the pollution source.',
        force_provider='openai::account-model',review_mode='full')
    assert 'actual-model' in out and 'Sediment alone' in out

def test_writing_retry_stays_with_the_selected_provider(pipeline,monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(pipeline,'_saved_key',lambda f:'synthetic-test-value')
    monkeypatch.setattr(pipeline,'_local_llm',lambda *a,**k:pytest.fail('No hidden local writer'))
    replies=iter(['I cannot post on social media.','Cursiv keeps your field notes close to your research.'])
    calls=[]
    def respond(*a,**kw):
        calls.append(1)
        selection.record(pipeline._runtime(),'openai','account-model')
        yield next(replies)
    monkeypatch.setattr(pipeline,'_call_openai_direct',respond)
    out=final_reply(pipeline,'Write a promotional post about Cursiv.',force_provider='openai::account-model')
    assert len(calls)==2 and 'keeps your field notes' in out and 'OpenAI' in out

def test_partial_selected_response_is_withdrawn_on_transport_failure(pipeline,monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(pipeline,'_saved_key',lambda f:'synthetic-test-value')
    def respond(*a,**kw):
        selection.record(pipeline._runtime(),'openai','account-model')
        yield 'Partial speculative answer.'
        yield pipeline.RATE_SENTINEL
    monkeypatch.setattr(pipeline,'_call_openai_direct',respond)
    out=final_reply(pipeline,'Explain sediment.',force_provider='openai::account-model')
    assert 'failed' in out and 'Partial speculative' not in out and 'Answered by' not in out

def test_picker_lists_installed_models_without_advanced_setting(panel):
    panel._on_models(['local-a:4b','local-b:8b'])
    panel._provider_box.setCurrentIndex(panel._provider_box.findData('ollama'))
    panel._on_provider_chosen(panel._provider_box.currentIndex())
    assert [panel._model_box.itemData(i) for i in range(panel._model_box.count())] == ['model:local-a:4b','model:local-b:8b']
    assert panel._cfg['selected_model']=='local-a:4b'

def test_cloud_picker_requires_supplied_model_id(panel):
    panel._provider_box.setCurrentIndex(panel._provider_box.findData('openai'))
    panel._on_provider_chosen(panel._provider_box.currentIndex())
    assert panel._cfg['selected_model']==''
    panel._exact_model.setText('account-model')
    assert panel._cfg['selected_provider']=='openai' and panel._cfg['selected_model']=='account-model'

def test_unconfigured_model_picker_does_not_disable_native_notebook_preview(panel,monkeypatch):
    from cursiv_engine.ui import chat_app
    from cursiv_engine.core import fieldlog
    panel._cfg.update(selected_provider='openai',selected_model='')
    monkeypatch.setattr(chat_app,'_local_model_ready',lambda:pytest.fail('Native preview needs no model'))
    panel._run_turn('Record water temperature 21.4°C at Willow Basin',[])
    assert panel._intents and not fieldlog.entries()

def test_refresh_does_not_replace_an_explicit_model(panel):
    panel._on_models(['local-a:4b','local-b:8b'])
    panel._provider_box.setCurrentIndex(panel._provider_box.findData('ollama'))
    panel._on_provider_chosen(panel._provider_box.currentIndex())
    panel._on_model_chosen(panel._model_box.findData('model:local-b:8b'))
    panel._on_models(['local-a:4b'])
    assert panel._cfg['selected_model']=='local-b:8b'
    assert panel._model_box.currentData()=='model:local-b:8b'

def test_advanced_explicit_model_choice_also_pins_the_backend(panel,monkeypatch):
    from cursiv_engine.chat import status
    monkeypatch.setattr(status,'show_all_models',lambda:True)
    panel._on_models(['local-a:4b','local-b:8b'])
    panel._on_model_chosen(panel._model_box.findData('model:local-b:8b'))
    assert panel._provider_box.currentData()=='ollama'
    assert panel._cfg['selected_provider']=='ollama' and panel._cfg['selected_model']=='local-b:8b'

@pytest.mark.parametrize('provider',['openai','claude','groq','gemini','grok'])
def test_transport_payload_and_resolved_model_are_truthful(pipeline,monkeypatch,provider):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    sent=[]
    data=dict(model='resolved-model',modelVersion='resolved-model',content=[dict(type='text',text='Answer')],
        choices=[dict(message=dict(content='Answer'),delta=dict(content='Answer'))],
        candidates=[dict(content=dict(parts=[dict(text='Answer')]))])
    class Response:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self,*a): return json.dumps(data).encode()
        def __iter__(self): return iter([('data: '+json.dumps(data)).encode()])
    def open_request(req,*a,**kw):
        sent.append((req.full_url,json.loads(req.data)))
        return Response()
    monkeypatch.setattr(pipeline.urllib.request,'urlopen',open_request)
    monkeypatch.setattr(pipeline,'_rate_limiter',None)
    runtime=pipeline._runtime()
    functions=dict(openai=lambda:runtime._call_openai_direct([], 'synthetic-test-value'),
        claude=lambda:runtime._call_claude_direct([], 'synthetic-test-value'),
        groq=lambda:runtime._call_groq_direct([], 'synthetic-test-value',100),
        gemini=lambda:runtime._call_gemini_direct([], 'synthetic-test-value',100),
        grok=lambda:runtime._call_xai_stream([], 'synthetic-test-value',False,100))
    with selection.use(selection.Selection(provider,'account-model')), selection.provenance_scope():
        assert 'Answer' in ''.join(functions[provider]())
    assert len(sent)==1
    if provider=='gemini': assert '/account-model:' in sent[0][0]
    else: assert sent[0][1]['model']=='account-model'
    assert 'resolved-model' in pipeline._ANSWERED_BY and 'requested account-model' in pipeline._ANSWERED_BY

def test_exact_text_prefix_keeps_case_of_model_id():
    import chat_commands
    provider,text=chat_commands.hey_prefix('model ollama TeamModel:4B :: Explain sediment')
    assert provider=='ollama::TeamModel:4B' and text=='Explain sediment'

def test_background_transport_does_not_replace_foreground_identity(pipeline):
    from cursiv_engine.core import last_turn
    with selection.provenance_scope():
        selection.record(pipeline._runtime(),'ollama','foreground-model','actual-foreground')
    before=last_turn.get()
    with selection.provenance_scope(False):
        selection.record(pipeline._runtime(),'groq','review-model','actual-review')
    assert last_turn.get()==before and 'actual-foreground' in pipeline._ANSWERED_BY

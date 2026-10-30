"""Provider contracts use synthetic API fixtures. No live cloud requests or keys."""
import io
import json
import threading
import urllib.error
import pytest

from cursiv_engine.chat import provider_registry as registry, provider_settings as settings
from cursiv_engine.chat import provider_manager as manager, provider_adapters as adapters, provider_http as http
from cursiv_engine.chat.provider_types import Request, Result, ProviderError, ErrorCode as E
from cursiv_engine.core import netgate


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'FILE', tmp_path/'provider_manager.json')
    monkeypatch.setattr(settings, 'CREDENTIALS', tmp_path/'device'/'credentials.json')
    monkeypatch.setattr(settings, 'APP_DATA', tmp_path/'legacy')
    monkeypatch.setattr(settings, '_session', {})
    monkeypatch.setattr(settings.keystore,'_keychain_put',lambda _:None)
    monkeypatch.setattr(netgate, 'allowed', lambda:True)
    monkeypatch.setattr(http.urllib.request.OpenerDirector, 'open', lambda *a,**k:pytest.fail('Unexpected network call'))
    manager._outcome.set(None)
    manager._request.set(None)


def key(monkeypatch, provider='openai'):
    monkeypatch.setattr(settings, 'key', lambda p:'synthetic-credential' if p == provider else '')


def request(provider='openai', model='chosen-model', **values):
    return Request(provider, model, [{'role':'user', 'content':'Preserve my exact prompt'}], **values)


def sse(*values):
    return io.BytesIO((''.join('data: '+json.dumps(v)+'\n\n' for v in values)+'data: [DONE]\n\n').encode())


@pytest.mark.parametrize('provider', [p.id for p in registry.providers()])
def test_registry_and_status_remain_visible_without_keys(provider):
    assert registry.get(provider).id == provider
    assert manager.status(provider)


@pytest.mark.parametrize('provider', ['openai','groq','gemini','claude','openrouter','grok'])
def test_missing_key_fails_locally_with_actual_provider(provider):
    assert list(manager.infer(request(provider))) == []
    result = manager.outcome()
    assert result.error == E.MISSING_KEY.value
    assert registry.get(provider).name in result.error_message
    assert result.attempted_provider == '' and result.responding_provider is None
    assert manager.snapshot().messages == request(provider).messages
    values, error = manager.models(provider, refresh=True)
    assert error.code == E.MISSING_KEY
    assert values and all(m.source == 'catalog' and not m.verified for m in values)


@pytest.mark.parametrize('provider', ['openai','groq','gemini','claude','openrouter','grok'])
def test_offline_takes_precedence_for_inference_discovery_and_auth(provider, monkeypatch):
    monkeypatch.setattr(netgate, 'allowed', lambda:False)
    list(manager.infer(request(provider)))
    assert manager.outcome().error == E.OFFLINE.value
    assert manager.models(provider, refresh=True)[1].code == E.OFFLINE


@pytest.mark.parametrize('provider', ['openai','groq','openrouter','grok','lmstudio','custom'])
def test_compatible_stream_pins_model_and_provenance(provider, monkeypatch):
    key(monkeypatch, provider)
    if provider == 'custom':
        settings.configure_endpoint(provider, url='http://127.0.0.1:9123/v1')
    sent = []
    def response(p, path, **kw):
        sent.append((p,path,kw))
        return sse({'model':'reported-model','choices':[{'delta':{'content':'Answer'},'finish_reason':None}]},
                   {'model':'reported-model','choices':[{'delta':{},'finish_reason':'stop'}], 'usage':{'total_tokens':3}})
    monkeypatch.setattr(http, 'open_response', response)
    assert ''.join(manager.infer(request(provider, research_authorized=True))) == 'Answer'
    result = manager.outcome()
    assert not result.error and result.actual_model == 'reported-model'
    assert result.requested_model == 'chosen-model' and result.responding_provider == provider
    assert sent[0][2]['payload']['model'] == 'chosen-model' and len(sent) == 1
    assert result.usage == {'total_tokens':3} and result.latency >= 0
    assert result.streamed and not result.streaming
    if provider == 'openrouter':
        assert sent[0][2]['payload']['provider']['allow_fallbacks'] is False


@pytest.mark.parametrize('provider', ['gemini','claude','ollama'])
def test_native_stream_protocols(provider, monkeypatch):
    key(monkeypatch, provider)
    sent = []
    def response(p, path, **kw):
        sent.append((path,kw['payload']))
        if p == 'gemini':
            return sse({'modelVersion':'native-resolved','candidates':[{'content':{'parts':[{'text':'Native answer'}]},'finishReason':'STOP'}],
                        'usageMetadata':{'totalTokenCount':4}})
        if p == 'claude':
            return sse({'type':'message_start','message':{'model':'native-resolved','usage':{'input_tokens':2}}},
                {'type':'content_block_delta','delta':{'type':'text_delta','text':'Native answer'}},
                {'type':'message_delta','delta':{'stop_reason':'end_turn'},'usage':{'output_tokens':2}})
        return io.BytesIO((json.dumps({'model':'native-resolved','message':{'content':'Native answer'},'done':True,'eval_count':4})+'\n').encode())
    monkeypatch.setattr(http, 'open_response', response)
    messages = [{'role':'system','content':'System instructions'}, *request().messages]
    assert ''.join(manager.infer(Request(provider,'chosen-model',messages,research_authorized=True))) == 'Native answer'
    assert manager.outcome().actual_model == 'native-resolved' and not manager.outcome().error
    if provider == 'gemini':
        assert 'systemInstruction' in sent[0][1] and 'contents' in sent[0][1]
    elif provider == 'claude':
        assert sent[0][1]['system'] == 'System instructions'
    else:
        assert sent[0][0] == '/api/chat'


@pytest.mark.parametrize('code,expected', [(401,E.INVALID_KEY),(403,E.PERMISSION),(404,E.MODEL),(429,E.RATE),(503,E.UNAVAILABLE)])
def test_http_errors_are_provider_specific_and_redacted(code, expected, monkeypatch):
    key(monkeypatch,'groq')
    secret = 'synthetic-credential'
    def fail(*a,**k):
        raise urllib.error.HTTPError('https://api.groq.com/secret',code,secret,{'Retry-After':'7'},io.BytesIO(json.dumps({'error':{'message':secret}}).encode()))
    monkeypatch.setattr(http.urllib.request.OpenerDirector,'open',fail)
    list(manager.infer(request('groq',research_authorized=True)))
    result = manager.outcome()
    assert result.error == expected.value and 'Groq' in result.error_message and 'OpenAI' not in result.error_message
    assert secret not in json.dumps(result.metadata())
    assert not result.responding_provider


def test_quota_timeout_and_incomplete_stream(monkeypatch):
    key(monkeypatch)
    monkeypatch.setattr(http.urllib.request.OpenerDirector,'open',lambda *a,**k: (_ for _ in ()).throw(TimeoutError()))
    list(manager.infer(request(research_authorized=True)))
    assert manager.outcome().error == E.TIMEOUT.value
    monkeypatch.setattr(http,'open_response',lambda *a,**k:sse({'choices':[{'delta':{'content':'Partial'}}]}))
    list(manager.infer(request(research_authorized=True)))
    assert manager.outcome().error == E.MALFORMED.value and manager.outcome().responding_provider is None
    error = urllib.error.HTTPError('https://example.com',429,'',{},io.BytesIO(b'{"error":{"code":"insufficient_quota"}}'))
    assert http._status_error('openai',error).code == E.QUOTA


@pytest.mark.parametrize('url', ['http://remote.example/v1','file:///secret','https://user:secret@remote.example/v1',
    'https://remote.example/v1?key=x','http://0.0.0.0/v1','http://127.0.0.1.evil.example/v1',
    'https://169.254.169.254/v1','https://remote.example/#x','https://remote.example/../v1'])
def test_unsafe_custom_endpoint_is_rejected(url):
    with pytest.raises(ProviderError) as error:
        settings.configure_endpoint('custom',url=url)
    assert error.value.code == E.ENDPOINT


@pytest.mark.parametrize('url', ['http://127.0.0.1:1234/v1','http://[::1]:1234/v1','http://localhost:1234/v1'])
def test_local_endpoints_work_offline(url,monkeypatch):
    settings.configure_endpoint('custom',url=url)
    monkeypatch.setattr(netgate,'allowed',lambda:False)
    assert http.preflight('custom')[1] is True


def test_remote_custom_offline_and_local_only_are_enforced(monkeypatch):
    settings.configure_endpoint('custom',url='https://research.example/v1')
    with pytest.raises(ProviderError) as error:
        http.preflight('custom',local_only=True)
    assert error.value.code == E.PERMISSION
    monkeypatch.setattr(netgate,'allowed',lambda:False)
    assert manager.models('custom',refresh=True)[1].code == E.OFFLINE


def test_redirects_never_forward_credentials():
    assert http._NoRedirect().redirect_request(None,None,307,'',{},'https://evil.example') is None


def test_preferences_and_cache_survive_disconnect(monkeypatch):
    settings.select('manual','groq','kept-model')
    assert settings.load()['provider'] == 'groq' and settings.load()['model'] == 'kept-model'
    settings.update(models={'groq':[{'id':'old-model','provider':'groq','source':'live','verified':True}]})
    values,error = manager.models('groq',refresh=True)
    assert error.code == E.MISSING_KEY
    assert any(m.id == 'old-model' and m.source == 'cached' and not m.verified for m in values)
    assert any(m.id == 'kept-model' for m in values)


def test_default_local_auto_never_uses_cloud(monkeypatch):
    calls=[]
    def discover(provider,key=''):
        calls.append(provider)
        return [registry.Model('qwen3:4b-instruct','ollama')] if provider == 'ollama' else []
    monkeypatch.setattr(adapters,'discover',discover)
    assert settings.load()['mode'] == 'local_auto'
    assert manager.choose('local_auto') == ('ollama','qwen3:4b-instruct')
    assert calls == ['ollama']


def test_cloud_auto_requires_explicit_authorization(monkeypatch):
    key(monkeypatch,'groq')
    with pytest.raises(ProviderError):
        manager.choose('cloud_auto')
    settings.authorize_cloud('groq',True)
    assert manager.choose('cloud_auto')[0] == 'groq'
    settings.authorize_cloud('groq',False)
    with pytest.raises(ProviderError):
        manager.choose('cloud_auto')


def test_cloud_auto_block_is_not_mislabeled_as_openai(monkeypatch):
    monkeypatch.setattr(netgate,'allowed',lambda:False)
    with pytest.raises(ProviderError) as error:
        manager.choose('cloud_auto')
    assert 'Cloud Automatic request blocked' in str(error.value) and 'OpenAI' not in str(error.value)


def test_research_context_requires_separate_consent(monkeypatch):
    key(monkeypatch)
    list(manager.infer(request()))
    assert manager.outcome().error == E.PERMISSION.value
    list(manager.infer(request(research_authorized=True,local_only=True)))
    assert manager.outcome().error == E.PERMISSION.value


def test_failed_request_retry_preserves_context_without_command_dispatch(monkeypatch):
    original=request(research_authorized=True)
    original.messages.insert(0,{'role':'system','content':'Authorized research context'})
    list(manager.infer(original))
    preserved=manager.snapshot()
    assert manager.outcome().error == E.MISSING_KEY.value
    key(monkeypatch)
    calls=[]
    def stream(req,result,credential):
        calls.append(req)
        result.text='Recovered'
        result.finish_reason='stop'
        result.responding_provider=req.provider
        yield result.text
    monkeypatch.setattr(adapters,'stream',stream)
    assert ''.join(manager.retry(preserved)) == 'Recovered'
    assert len(calls)==1 and calls[0].messages == original.messages
    assert original.model == 'chosen-model'
    with pytest.raises(ValueError):
        list(manager.retry(preserved,provider='groq'))


def test_cancel_and_unsolicited_tool_calls_never_execute(monkeypatch):
    cancel=threading.Event(); cancel.set()
    list(manager.infer(request('ollama',cancel=cancel)))
    assert manager.outcome().canceled
    key(monkeypatch)
    monkeypatch.setattr(http,'open_response',lambda *a,**k:sse({'model':'real','choices':[{'delta':{'tool_calls':[
        {'index':0,'id':'one','function':{'name':'fieldlog.add','arguments':'{}'}}]},'finish_reason':'tool_calls'}]}))
    list(manager.infer(request(research_authorized=True)))
    result=manager.outcome()
    assert result.error == E.CAPABILITY.value and result.tool_calls and not result.tool_results


def test_unreported_model_is_explicitly_requested_not_verified(monkeypatch):
    key(monkeypatch)
    monkeypatch.setattr(http,'open_response',lambda *a,**k:sse({'choices':[{'delta':{'content':'Answer'},'finish_reason':'stop'}]}))
    list(manager.infer(request(research_authorized=True)))
    assert manager.outcome().actual_model is None
    assert 'not independently reported' in manager.outcome().label()


def test_os_storage_failure_is_session_only(monkeypatch):
    monkeypatch.setattr(settings.keystore,'_crypt',lambda *a:(_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(settings.keystore,'_keychain_put',lambda _:None)
    message=settings.save_key('openai','synthetic-secret')
    assert 'session only' in message and settings.key('openai') == 'synthetic-secret'
    assert 'synthetic-secret' not in settings.CREDENTIALS.read_text(encoding='utf-8')
    settings.save_key('openai','')
    assert settings.key('openai') == ''


def test_ollama_discovery_includes_any_installed_model_size(monkeypatch):
    monkeypatch.setattr(http,'read_json',lambda *a,**k:{'models':[{'name':'my-model:custom','size':42000,'details':{'quantization_level':'Q4_K_M'}}]})
    found=adapters.discover('ollama')
    assert found[0].id == 'my-model:custom' and found[0].size == 42000 and found[0].verified
    assert found[0].quantization == 'Q4_K_M'


def test_fixed_provider_origins_cannot_be_overridden():
    settings.update(endpoints={'openai':{'url':'https://evil.example'}})
    assert http.location('openai')[0] == registry.get('openai').base_url


@pytest.mark.parametrize('provider', ['openai','groq','gemini','claude','openrouter','lmstudio','custom'])
def test_provider_auth_headers_are_distinct_and_credentials_never_enter_payload(provider,monkeypatch):
    if provider=='custom':
        settings.configure_endpoint(provider,url='http://127.0.0.1:9123/v1')
    sent=[]
    def receive(opener,request,**kw):
        sent.append(request)
        return io.BytesIO(b'{}')
    monkeypatch.setattr(http.urllib.request.OpenerDirector,'open',receive)
    with http.open_response(provider,'/models',credential='synthetic-credential'):
        pass
    headers={k.lower():v for k,v in sent[0].header_items()}
    name='x-goog-api-key' if provider=='gemini' else 'x-api-key' if provider=='claude' else 'authorization'
    assert headers[name].endswith('synthetic-credential')
    if provider=='claude':
        assert headers['anthropic-version']=='2023-06-01'
    assert sent[0].data is None


def test_gemini_invalid_key_and_custom_origin_binding(monkeypatch):
    error=urllib.error.HTTPError('https://example.com',400,'',{},io.BytesIO(
        b'{"error":{"details":[{"reason":"API_KEY_INVALID"}],"message":"not echoed"}}'))
    assert http._status_error('gemini',error).code == E.INVALID_KEY
    settings.configure_endpoint('custom',url='https://first.example/v1')
    settings.save_key('custom','synthetic-secret')
    assert settings.key('custom')=='synthetic-secret'
    settings.configure_endpoint('custom',url='https://second.example/v1')
    assert settings.key('custom')==''


@pytest.mark.parametrize('provider',['ollama','openai','groq','gemini','claude','openrouter','lmstudio','custom'])
def test_embedded_image_uses_exact_model_and_provider_native_schema(provider):
    image='data:image/png;base64,c3ludGhldGlj'
    message={'role':'user','content':[{'type':'text','text':'Describe this picture.'},
        {'type':'image_url','image_url':{'url':image}}]}
    path,payload=adapters.build(Request(provider,'exact-vision-model',[message],capability='vision'))
    assert 'exact-vision-model' in str(payload) or 'exact-vision-model' in path
    if provider=='ollama':
        assert payload['messages'][0]['images']==['c3ludGhldGlj']
    elif provider=='gemini':
        assert payload['contents'][0]['parts'][1]['inlineData']['data']=='c3ludGhldGlj'
    elif provider=='claude':
        assert payload['messages'][0]['content'][1]['source']['data']=='c3ludGhldGlj'
    else:
        assert payload['messages'][0]['content'][1]['image_url']['url']==image


def test_image_generation_cannot_choose_another_backend(monkeypatch):
    monkeypatch.setattr(adapters,'discover',lambda *a,**k:pytest.fail('No hidden discovery or model change'))
    list(manager.selected_infer([{'role':'user','content':'image a cat'}],capability='image_generation'))
    assert manager.outcome().error==E.CAPABILITY.value
    assert manager.snapshot().capability=='image_generation'
    assert not manager.outcome().responding_provider


def test_remote_image_urls_are_not_fetched_or_forwarded():
    req=Request('openai','exact-model',[{'role':'user','content':[{'type':'image_url','image_url':{'url':'https://unrelated.example/private'}}]}])
    with pytest.raises(ProviderError) as error:
        adapters.build(req)
    assert error.value.code==E.CAPABILITY


def test_custom_endpoint_change_during_build_never_sends_credentials(monkeypatch):
    settings.configure_endpoint('custom',url='https://first.example/v1')
    settings.save_key('custom','synthetic-secret')
    original=adapters.build
    def changed(req):
        payload=original(req)
        settings.configure_endpoint('custom',url='https://second.example/v1')
        return payload
    monkeypatch.setattr(adapters,'build',changed)
    list(manager.infer(request('custom',research_authorized=True)))
    assert manager.outcome().error==E.PERMISSION.value
    assert manager.snapshot().endpoint_url=='https://first.example/v1'
    assert settings.key('custom')==''


def test_retry_changed_endpoint_requires_new_authorization(monkeypatch):
    settings.configure_endpoint('custom',url='http://127.0.0.1:9123/v1')
    original=request('custom'); original.endpoint_url='http://127.0.0.1:9123/v1'
    settings.configure_endpoint('custom',url='http://127.0.0.1:9124/v1')
    with pytest.raises(ValueError):
        list(manager.retry(original))


def test_generation_budget_is_enforced_before_network_and_records_native_usage(monkeypatch):
    from cursiv_engine.chat import request_budget as rb
    with rb.use(rb.Budget(ceiling=0)):
        list(manager.infer(request('ollama')))
    assert manager.outcome().error==E.BUDGET.value
    key(monkeypatch)
    with rb.use(rb.Budget(ceiling=2,local_only=True)):
        list(manager.infer(request(research_authorized=True)))
    assert manager.outcome().error==E.PERMISSION.value
    events=[{'model':'chosen-model','message':{'content':'Answer'},'done':False},
            {'model':'chosen-model','message':{'content':''},'done':True,'prompt_eval_count':9,'eval_count':2}]
    monkeypatch.setattr(http.urllib.request.OpenerDirector,'open',lambda *a,**k:io.BytesIO(
        ''.join(json.dumps(v)+'\n' for v in events).encode()))
    budget=rb.Budget(ceiling=1)
    with rb.use(budget):
        assert ''.join(manager.infer(request('ollama')))=='Answer'
    assert len(budget.requests)==1
    row=budget.requests[0]
    assert row['provider']=='ollama' and row['requested_model']=='chosen-model'
    assert row['received_text'] and row['success'] and row['input_tokens']==9 and row['output_tokens']==2


def test_training_note_conversion_has_no_legacy_fallback(monkeypatch):
    from types import SimpleNamespace
    import command_media
    runtime=SimpleNamespace(_call_ollama=lambda *a:pytest.fail('No legacy local fallback'),
                            _call_openai_direct=lambda *a:pytest.fail('No legacy cloud fallback'))
    cfg={'selected_provider':'groq','selected_model':'exact-groq-model','openai_key':'synthetic-unused'}
    assert command_media._run_llm_once(runtime,[{'role':'user','content':'Private research notes'}],cfg)==''
    assert manager.outcome().provider=='groq' and manager.outcome().error==E.MISSING_KEY.value

"""Read-only comparisons and explicitly approved model management; mocked only."""
import io
import json
import threading
from pathlib import Path
import pytest
from cursiv_engine.chat import provider_local as local, provider_comparison as comparison
from cursiv_engine.chat import provider_http as http, provider_adapters as adapters, provider_settings as settings
from cursiv_engine.chat.provider_types import ProviderError, ErrorCode as E
from cursiv_engine.core import netgate


def test_pull_requires_consent_and_internet_even_through_loopback(monkeypatch):
    monkeypatch.setattr(http,'open_response',lambda *a,**k:pytest.fail('Not authorized'))
    with pytest.raises(ProviderError) as error:
        list(local.pull('any-model:4b'))
    assert error.value.code == E.PERMISSION
    monkeypatch.setattr(netgate,'allowed',lambda:False)
    with pytest.raises(ProviderError) as error:
        list(local.pull('any-model:4b',consent=True))
    assert error.value.code == E.OFFLINE


def test_pull_progress_cancel_and_delete_confirmation(monkeypatch):
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    sent=[]
    def response(provider,path,**kw):
        sent.append((path,kw))
        return io.BytesIO((json.dumps({'status':'downloading','total':100,'completed':45})+'\n'+
                           json.dumps({'status':'success'})+'\n').encode())
    monkeypatch.setattr(http,'open_response',response)
    assert list(local.pull('any-model:4b',consent=True)) == [(45,'downloading'),(0,'success')]
    cancel=threading.Event(); cancel.set()
    with pytest.raises(ProviderError) as error:
        list(local.pull('any-model:4b',consent=True,cancel=cancel))
    assert error.value.code == E.CANCELLED
    with pytest.raises(ProviderError):
        local.remove('any-model:4b')
    assert local.remove('any-model:4b',confirmed=True)
    assert sent[-1][0] == '/api/delete' and sent[-1][1]['method'] == 'DELETE'


def test_comparison_requires_cloud_consent_and_preserves_identical_context(monkeypatch):
    messages=[{'role':'system','content':'Frozen research context'}, {'role':'user','content':'Explain sediment settling.'}]
    with pytest.raises(ProviderError):
        comparison.prepare(messages,[('ollama','qwen3:4b-instruct'),('groq','exact-model')])
    plan=comparison.prepare(messages,[('ollama','qwen3:4b-instruct'),('groq','exact-model')],cloud_consent=True)
    messages[0]['content']='Changed after preparation'
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(settings,'key',lambda p:'synthetic-credential')
    sent=[]
    def stream(req,result,credential):
        sent.append(req.messages)
        result.text='Particles settle at different rates.'
        result.responding_provider=req.provider
        result.finish_reason='stop'
        yield result.text
    monkeypatch.setattr(adapters,'stream',stream)
    values=list(comparison.run(plan))
    assert sent[0] == sent[1] and sent[0][0]['content']=='Frozen research context'
    assert values[0]['context_sha256']==values[1]['context_sha256']
    assert all(v['tool_permissions']=='none' and not v['provenance']['tool_results'] for v in values)
    assert all('score' not in v for v in values)
    with pytest.raises(ProviderError):
        comparison.prepare(messages,[('ollama','a'),('openai','b')],cloud_consent=True,local_only=True)


def test_discovery_retry_is_bounded_and_respects_long_rate_limit(monkeypatch):
    count=[]
    def transient(*a,**k):
        count.append(1)
        if len(count)==1:
            raise ProviderError('ollama',E.UNAVAILABLE)
        return io.BytesIO(b'{"models":[]}')
    monkeypatch.setattr(http,'open_response',transient)
    monkeypatch.setattr(http.time,'sleep',lambda _:None)
    assert http.read_json('ollama','/api/tags') == {'models':[]}
    assert len(count)==2
    count.clear()
    def rate(*a,**k):
        count.append(1)
        raise ProviderError('groq',E.RATE,retry_after=30)
    monkeypatch.setattr(http,'open_response',rate)
    with pytest.raises(ProviderError):
        http.read_json('groq','/models')
    assert len(count)==1


def test_exact_image_generation_records_real_artifact_and_cache_is_idempotent(tmp_path,monkeypatch):
    import base64,hashlib
    from types import SimpleNamespace
    from cursiv_engine.chat import provider_manager as manager
    from cursiv_engine.chat.provider_types import Request
    import commands_images
    image=b'\x89PNG\r\n\x1a\nsynthetic-provider-fixture'
    encoded=base64.b64encode(image).decode()
    calls=[]
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(settings,'key',lambda p:'synthetic-credential')
    def response(provider,path,**kwargs):
        calls.append((provider,path,kwargs))
        return {'data':[{'b64_json':encoded}],'usage':{'total_tokens':12}}
    monkeypatch.setattr(http,'read_json',response)
    request=Request('openai','exact-image-model',[{'role':'user','content':'A research diagram.'}],
                    research_authorized=True,capability='image_generation')
    list(manager.infer(request))
    result=manager.outcome()
    assert not result.error and len(calls)==1 and calls[0][1]=='/images/generations'
    assert calls[0][2]['payload']['model']=='exact-image-model'
    assert result.actual_model is None and 'not independently reported' in result.label()
    assert encoded not in json.dumps(result.metadata())
    runtime=SimpleNamespace(_image_folder=lambda cfg:tmp_path)
    first=commands_images.save_result(runtime,result,{})
    before=list(tmp_path.iterdir())
    second=commands_images.save_result(runtime,result,{})
    assert first==second and list(tmp_path.iterdir())==before
    assert hashlib.sha256(Path(first).read_bytes()).hexdigest()==result.artifacts[0]['sha256']

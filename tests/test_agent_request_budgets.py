"""The actual provider transports share request, context, wall and cancellation limits."""
from io import BytesIO
import json
import threading
import time
from urllib.request import Request

import pytest
from cursiv_engine.chat import request_budget as rb, activity


def request(text='hello'):
    return Request('http://127.0.0.1:11434/api/generate', data=json.dumps(dict(model='synthetic', prompt=text,
                   options=dict(num_predict=10))).encode())


def test_failed_http_attempts_and_retry_cannot_reset_ceiling():
    calls=[]
    def fail(*a, **k):
        calls.append(1)
        raise OSError('synthetic transport failure')
    budget=rb.Budget(2)
    with rb.use(budget):
        for _ in range(2):
            with pytest.raises(OSError), rb.open_request(fail, request(), timeout=10):
                pass
        with pytest.raises(rb.Stopped), rb.open_request(fail, request(), timeout=10):
            pass
    assert len(calls)==len(budget.requests)==2
    assert not any(r['success'] for r in budget.requests)


@pytest.mark.parametrize('why', ['context','cancel','deadline','identity','cloud'])
def test_rejected_requests_never_reach_transport(why):
    calls=[]
    budget=rb.Budget(2, context=100 if why=='context' else 8192, local_only=why=='cloud')
    req=request('x'*200 if why=='context' else 'hello')
    if why=='cancel': budget.cancelled.set()
    if why=='deadline': budget.started-=500
    if why=='identity': budget.valid=lambda:False
    if why=='cloud': req.full_url='https://example.com/generate'
    with pytest.raises(rb.Stopped):
        with rb.use(budget), rb.open_request(lambda *a, **k:calls.append(1),req,timeout=10):
            pass
    assert not calls


def test_actual_token_counts_are_separate_from_estimates_and_no_prompt_retained():
    payload=b'{"response":"hello"}\n{"done":true,"prompt_eval_count":20,"eval_count":1}\n'
    budget=rb.Budget(1)
    with rb.use(budget), rb.open_request(lambda *a, **k:BytesIO(payload),request(),timeout=10) as response:
        list(response)
    row=budget.requests[0]
    assert row['success'] and row['input_tokens']==20 and row['output_tokens']==1
    assert 'hello' not in str(row)


def test_overlapping_model_work_is_serialized_and_context_budgets_do_not_leak():
    entered, release, order=threading.Event(),threading.Event(),[]
    def first():
        with rb.use(rb.Budget(1)), activity.exclusive():
            order.append('first')
            entered.set()
            release.wait(3)
    def second():
        entered.wait(3)
        with rb.use(rb.Budget(2)), activity.exclusive():
            order.append('second')
            assert rb.current().ceiling==2
    a,b=threading.Thread(target=first),threading.Thread(target=second)
    a.start(); b.start()
    assert entered.wait(3) and order==['first']
    release.set(); a.join(3); b.join(3)
    assert order==['first','second'] and rb.current() is None


@pytest.mark.parametrize('ceiling,expected', [(1,1),(2,2)])
def test_actual_ollama_internal_retry_uses_one_shared_budget(monkeypatch,ceiling,expected):
    from types import SimpleNamespace
    from cursiv_engine.chat import local_provider
    from cursiv_engine.core import speed
    import urllib.request, urllib.error
    calls=[]
    def transport(*args,**kwargs):
        calls.append(1)
        if len(calls)==1: raise OSError('Synthetic GPU failure')
        return BytesIO(b'{"response":"ok"}\n{"done":true,"eval_count":1,"prompt_eval_count":2}\n')
    monkeypatch.setattr(speed,'gpu_options',lambda model:{'num_gpu':10})
    monkeypatch.setattr(speed,'make_room',lambda model:None)
    monkeypatch.setattr(speed,'gpu_fallback',lambda model:None)
    runtime=SimpleNamespace(_slim=lambda m,n:m, _IDENTITY_OVERRIDE='', _ensure_ollama=lambda:True,
        _ollama_tags=lambda:['synthetic'], _resolve_ollama_model=lambda standard:'synthetic',
        _models_on_disk=lambda:True, json=json, OLLAMA_URL='http://127.0.0.1:11434/api/generate',
        urllib=SimpleNamespace(request=SimpleNamespace(Request=Request,urlopen=transport),error=urllib.error))
    budget=rb.Budget(ceiling)
    with rb.use(budget):
        text=''.join(local_provider._call_ollama_raw(runtime,[dict(role='user',content='hello')],10,True))
    assert len(calls)==len(budget.requests)==expected
    assert ('ok' in text) == (ceiling==2)
    if ceiling==1: assert 'limit reached' in text


def test_serialized_chat_rebuilds_ledger_from_only_its_supplied_history():
    from cursiv_engine.core import verify
    verify._ledgers[:]=[dict(user='private old question',ledger={'Known':'old private fact'})]
    verify._previous_failed=True
    @activity.serialized_turn
    def chat(runtime,message,history):
        assert not verify._previous_failed
        yield verify.prior_ledger_block()
    ledger='Known: new conversation fact\nInferred: none\nAssumed: none\nUnknown: none'
    text=''.join(chat(None,'follow up',[dict(role='user',content='Current question'),dict(role='assistant',content=ledger)]))
    assert 'old private' not in text and 'new conversation fact' in text
    verify.reset_session()


def test_partial_provider_response_is_not_a_successful_generation():
    budget=rb.Budget(1)
    with rb.use(budget),rb.open_request(lambda *a,**k:BytesIO(b'{"response":"partial"}\n'),request(),timeout=10) as response:
        list(response)
    assert budget.requests[0]['received_text'] and not budget.requests[0]['success']


def test_pinned_local_model_cannot_switch_for_review():
    budget=rb.Budget(2)
    with rb.use(budget):
        with rb.open_request(lambda *a,**k:BytesIO(b'{"response":"ok"}\n{"done":true}\n'),request(),timeout=10) as response:
            list(response)
        other=Request('http://127.0.0.1:11434/api/generate',data=b'{"model":"different","prompt":"hello"}')
        with pytest.raises(rb.Stopped,match='switch'),rb.open_request(lambda *a,**k:None,other,timeout=10):
            pass
    assert len(budget.requests)==1


def test_ui_cancellation_while_waiting_for_a_chunk_rejects_that_chunk():
    from chat_panel import _iter_cancellable
    cancelled=threading.Event()
    closed=[]
    def late():
        try:
            cancelled.set()  # Stop/new-conversation happened during a blocked next().
            yield 'stale private answer'
        finally:
            closed.append(True)
    assert list(_iter_cancellable(late(),cancelled))==[] and closed==[True]


def test_foreground_guard_blocks_transport_after_ui_ownership_changed():
    valid=[True]
    sent=[]
    def work():
        valid[0]=False
        with rb.open_request(lambda *a,**k:sent.append(1),request(),timeout=10):
            pass
        yield 'not reached'
    with pytest.raises(rb.Stopped):
        list(activity.guarded(work(),lambda:valid[0]))
    assert not sent

"""Deferred-task persistence and failure states, exclusively synthetic stores/executors."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from cursiv_engine.agents import offline_queue as queue


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, '_QUEUE_FILE', tmp_path/'deferred.jsonl')


@pytest.mark.parametrize('outcome', ['', '[flush requires active connection]', 'Error: offline',
    queue.Outcome('succeeded',''), queue.Outcome('succeeded','[Ollama unavailable]'), None])
def test_strings_placeholders_and_empty_responses_never_establish_success(outcome):
    task=queue.enqueue('Write a synthetic notice.')
    result=queue.flush(lambda row:outcome)
    assert result[0]['status']=='failed'
    assert queue.history()[0]['id']==task['id']
    assert len(queue.history()[0]['history'])==2


def test_real_explicit_result_and_archival_keep_history():
    task=queue.enqueue('Write a synthetic notice.')
    result=queue.flush(lambda row:queue.Outcome('succeeded','A verified synthetic result.'))
    assert result[0]['status']=='succeeded' and queue.count()==0
    assert queue.clear_fired()==1
    assert queue.history()[0]['id']==task['id'] and queue.history()[0]['archived']


def test_cancel_running_rejects_late_success_and_retry_requires_reconciliation():
    task=queue.enqueue('Write a notice.')
    def executor(row):
        queue.cancel(row['id'])
        return queue.Outcome('succeeded','Late result')
    assert queue.flush(executor)[0]['status']=='cancelled'
    with pytest.raises(ValueError,match='uncertain'):
        queue.retry(task['id'])
    assert queue.retry(task['id'],reconciled=True)['status']=='pending'


def test_concurrent_flush_and_enqueue_preserve_every_task_without_double_execution():
    original=queue.enqueue('Write the first notice.')
    entered,release=threading.Event(),threading.Event()
    calls=[]
    def execute(row):
        calls.append(row['id']); entered.set(); assert release.wait(5)
        return queue.Outcome('succeeded','Done')
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(queue.flush,execute)
        assert entered.wait(5)
        added=queue.enqueue('Write a second notice.')
        # Another flush may execute the new task, but must skip the already claimed task.
        other=pool.submit(queue.flush,lambda row:queue.Outcome('blocked',error='Synthetic unavailable dependency'))
        other.result(5)
        release.set(); first.result(5)
    rows={r['id']:r for r in queue.history()}
    assert calls==[original['id']] and rows[original['id']]['status']=='succeeded'
    assert rows[added['id']]['status']=='blocked'


def test_restart_expired_lease_is_uncertain_never_silently_replayed():
    task=queue.enqueue('Write a notice.')
    with queue._locked():
        rows=queue._read(); queue._set(rows[0],'running',lease_until=0,execution='dead-process'); queue._save(rows)
    calls=[]
    assert queue.flush(lambda row:calls.append(row))==[]
    assert not calls and queue.history()[0]['status']=='blocked'
    with pytest.raises(ValueError,match='uncertain'): queue.retry(task['id'])


def test_exception_is_uncertain_and_history_survives():
    queue.enqueue('Write a notice.')
    def timeout(row): raise TimeoutError('Synthetic timeout')
    result=queue.flush(timeout)[0]
    assert result['status']=='blocked' and result['uncertain'] and 'timeout' in result['error']


def test_damage_fails_closed_without_execution_or_rewrite():
    queue.enqueue('Write a notice.')
    with queue._QUEUE_FILE.open('a') as stream: stream.write('{damaged\n')
    original=queue._QUEUE_FILE.read_bytes(); calls=[]
    with pytest.raises(ValueError): queue.flush(lambda row:calls.append(row))
    assert not calls and queue._QUEUE_FILE.read_bytes()==original


@pytest.mark.parametrize('when',['claim','completion'])
def test_persistence_failure_never_claims_success_or_loses_task(monkeypatch,when):
    task=queue.enqueue('Write a notice.')
    real=queue._save; saves=[]; calls=[]
    def fail(rows):
        saves.append(1)
        if len(saves)==(1 if when=='claim' else 2): raise OSError('Synthetic disk failure')
        real(rows)
    monkeypatch.setattr(queue,'_save',fail)
    with pytest.raises(OSError):
        queue.flush(lambda row:(calls.append(row),queue.Outcome('succeeded','Done'))[1])
    row=queue.history()[0]
    assert row['id']==task['id'] and row['status']==('pending' if when=='claim' else 'running')
    assert len(calls)==(0 if when=='claim' else 1)


def test_legacy_fired_and_queued_preserved_but_require_review():
    rows=[dict(id='legacy-'+s,prompt='Write a notice.',status=s,response='[flush requires active connection]') for s in ('queued','fired','error')]
    queue._QUEUE_FILE.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    calls=[]
    assert queue.flush(lambda row:calls.append(row))==[] and not calls
    assert len(queue.history())==3 and all(r['status']=='blocked' for r in queue.history())
    assert queue.retry('legacy-queued')['status']=='pending'
    with pytest.raises(ValueError,match='uncertain'): queue.retry('legacy-fired')


def test_changed_owner_cannot_execute_saved_task(monkeypatch):
    from cursiv_engine.agents import workflow
    queue.enqueue('Write a notice.')
    monkeypatch.setattr(workflow,'identity',lambda:('different-owner',))
    calls=[]
    assert queue.flush(lambda row:calls.append(row))[0]['status']=='blocked' and not calls


def test_actual_queue_command_uses_bounded_local_profile_executor(tmp_path,monkeypatch):
    import chat_commands as cc
    from cursiv_engine.agents import custom
    from cursiv_engine.chat import request_budget
    monkeypatch.setattr(custom,'DIR',tmp_path/'agents')
    calls=[]
    def local(messages,**kwargs):
        request_budget.attempt('synthetic-local',messages,kwargs['max_tokens'])
        calls.append(messages)
        return iter(['A useful notice.'])
    monkeypatch.setattr(cc,'_call_ollama',local)
    cc.handle_command('queue add @writer Write a notice.',{},[])
    result=cc.handle_command('queue flush',{'answer_check_mode':'off'},[])
    text=''.join(result.generator)
    assert 'succeeded' in text and 'useful notice' in text and len(calls)==1
    assert queue.history()[0]['status']=='succeeded'


@pytest.mark.parametrize('confirmed',[False,True])
def test_model_tool_cannot_authorize_queue_flush(monkeypatch,confirmed):
    from cursiv_engine.chat import context
    from types import SimpleNamespace
    queue.enqueue('Write a notice.')
    runtime=SimpleNamespace(turn_policy=SimpleNamespace(current=lambda:SimpleNamespace(blocks=lambda n:False)))
    text=context.execute_tool(runtime,'offline_queue',{'action':'flush'},None,confirmed=confirmed)
    assert 'not executed' in text and queue.count()==1


def test_cross_process_enqueue_is_atomic_and_preserves_unique_ids():
    import os, subprocess, sys
    source = ('import sys; from pathlib import Path; from cursiv_engine.agents import offline_queue as q; '
              'q._QUEUE_FILE=Path(sys.argv[1]); '
              '[q.enqueue("Write synthetic notice "+str(i)) for i in range(5)]')
    home=queue._QUEUE_FILE.parent/'process-home'
    home.mkdir()
    env=dict(os.environ,HOME=str(home),USERPROFILE=str(home),CURSIV_APP_DATA=str(home/'app'))
    processes=[subprocess.Popen([sys.executable,'-c',source,str(queue._QUEUE_FILE)],
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env) for _ in range(2)]
    for process in processes:
        out,err=process.communicate(timeout=20)
        assert process.returncode==0,err.decode(errors='replace')
    rows=queue.history()
    assert len(rows)==10 and len({r['id'] for r in rows})==10

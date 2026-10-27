"""Disposable old/new queue and cancellation reproductions; one real local queue task."""
from __future__ import annotations
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import ModuleType
from unittest.mock import patch
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
BASE='2a639325f60bb3a6b911c83ebb99502339227970'
MODEL='qwen3:4b-instruct'


def main():
    home=Path(tempfile.mkdtemp(prefix='cursiv-u107-queue-proof-'))
    os.environ.update(HOME=str(home),USERPROFILE=str(home),CURSIV_APP_DATA=str(home/'app'),
                      CURSIV_NO_ENGINE_START='1',QT_QPA_PLATFORM='offscreen')
    sys.path[:0]=[str(ROOT),str(ROOT/'launcher')]
    for name in ('codex_tool_bridge','knowledge_brain'): sys.modules.setdefault(name,None)
    import chat_commands as commands
    from cursiv_engine.agents import offline_queue as queue
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate,speed
    netgate.set_offline(True)
    # Execute only the trusted baseline queue module; every path is redirected before use.
    source=subprocess.check_output(['git','show',BASE+':cursiv_engine/agents/offline_queue.py'],cwd=ROOT,text=True)
    old=ModuleType('cursiv_engine.agents.legacy_queue_probe')
    old.__file__=str(home/'baseline'/'offline_queue.py')
    exec(compile(source,old.__file__,'exec'),old.__dict__)
    old._QUEUE_FILE=home/'old'/'queue.jsonl'
    old.enqueue('Synthetic task: write a notice.')
    before=old.flush(lambda prompt:'[flush requires active connection]')[0]
    queue._QUEUE_FILE=home/'new'/'queue.jsonl'
    task=queue.enqueue('Synthetic task: write a notice.')
    after=queue.flush(lambda task:'[flush requires active connection]')[0]
    # Actual bounded native queue executor, pinned to an installed local model.
    real_open=urllib.request.urlopen
    requests=[]
    def observe(request,*args,**kwargs):
        url=request if isinstance(request,str) else request.full_url
        if url.startswith('http://127.0.0.1:11434/api/generate'):
            body=json.loads(request.data)
            if body['model'] != MODEL: raise RuntimeError('Refusing a model switch')
            requests.append(dict(model=body['model']))
        elif not url.startswith('http://127.0.0.1:11434/'):
            raise RuntimeError('Outside connections are forbidden in the queue proof')
        return real_open(request,*args,**kwargs)
    commands.handle_command('queue add @writer Write two sentences encouraging careful record keeping.',{},[])
    with patch.object(ca,'_resolve_ollama_model',lambda *a,**k:MODEL),patch.object(speed,'num_ctx',return_value=8192),patch.object(urllib.request,'urlopen',observe):
        result=commands.handle_command('queue flush',{'answer_check_mode':'off'},[])
        rendered=''.join(result.generator)
    live=queue.history()[-1]
    # The real baseline UI iterator published a chunk cancelled during next().
    ui_source=subprocess.check_output(['git','show',BASE+':launcher/chat_panel.py'],cwd=ROOT,text=True)
    tree=ast.parse(ui_source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_iter_cancellable')
    namespace={'threading':threading}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<baseline iterator>','exec'),namespace)
    from chat_panel import _iter_cancellable
    def probe(iterator):
        event=threading.Event()
        def late():
            event.set()
            yield 'synthetic stale chunk'
        return len(list(iterator(late(),event)))
    packet=dict(baseline_commit=BASE,synthetic_only=True,owner_tasks_replayed=False,
                placeholder_before_status=before['status'],placeholder_after_status=after['status'],
                live_queue_status=live['status'],live_model_requests=requests,
                live_history_states=[h['status'] for h in live['history']],live_result=live.get('response'),
                cancelled_chunk_before=probe(namespace['_iter_cancellable']),cancelled_chunk_after=probe(_iter_cancellable))
    output=ROOT/'bench/results/U107-queue-and-cancellation-proof.json'
    if output.exists(): raise RuntimeError('Refusing to overwrite evidence')
    output.write_text(json.dumps(packet,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in packet.items() if k!='live_result'},indent=2))
    return 0 if live['status']=='succeeded' and requests else 1


if __name__=='__main__':
    raise SystemExit(main())

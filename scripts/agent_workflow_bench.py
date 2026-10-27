"""Real local-inference comparison in disposable stores; never reads owner tasks/data.

The evaluation prompts are frozen separately from development cases. Baseline raw
answers must not be used to tune implementation. No settings persist outside the
temporary home. Records actual Ollama token counts; unavailable metrics stay null.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'qwen3:4b-instruct'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--set', choices=('development', 'evaluation', 'confirmation', 'confirmation2', 'confirmation3', 'acceptance', 'holdout'), default='evaluation')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--case', help='Restrict a development run to one frozen case (evaluation always runs all cases)')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite measured evidence')
    # All application paths are established before any application import.
    home = Path(tempfile.mkdtemp(prefix='cursiv-agent-bench-'))
    for key in ('HOME', 'USERPROFILE'):
        os.environ[key] = str(home)
    os.environ.update(CURSIV_APP_DATA=str(home / 'app-data'), CURSIV_NO_ENGINE_START='1', QT_QPA_PLATFORM='offscreen')
    sys.path[:0] = [str(ROOT), str(ROOT / 'launcher')]
    for name in ('codex_tool_bridge', 'knowledge_brain'):
        sys.modules.setdefault(name, None)
    import chat_commands as commands
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.agents import custom, profile_context, offline_queue
    from cursiv_engine.core import fieldlog, documents, netgate, speed, capabilities
    from cursiv_engine.memory import formation, semantic
    from cursiv_engine.chat import context, review
    # Preload audited dependencies before any implementation changes are allowed.
    _ = (offline_queue.flush, context.execute_tool, profile_context.context, capabilities.agent_permissions)
    netgate.set_offline(True)
    corpus_file = {'holdout':'bench/agent-final-holdout.json', 'acceptance':'bench/agent-acceptance.json', 'confirmation':'bench/agent-confirmation.json', 'confirmation2':'bench/agent-confirmation-final.json',
                   'confirmation3':'bench/agent-confirmation-last.json'}.get(args.set,'bench/agent-workflows.json')
    corpus = (ROOT / corpus_file).read_bytes()
    cases = json.loads(corpus)[args.set]
    if args.case:
        if args.set != 'development':
            raise SystemExit('Evaluation cannot be filtered')
        cases = [case for case in cases if case['id'] == args.case]
        if not cases:
            raise SystemExit('Unknown development case')
    rows, calls = [], []
    for n in range(84):
        fieldlog.add(site='Pond' if n < 80 else 'Hill', sample_id=f'S-{n:03}',
                     measurements=[{'name':'temperature', 'value':str(10 + n % 5), 'unit':'C'}])
    fieldlog.add(site='Pond', sample_id='S-000', measurements=[{'name':'nitrate','value':'2.5','unit':''}])
    fieldlog.add(site='Pond', sample_id='S-001', measurements=[{'name':'temperature','value':'cloudy','unit':'C'}])
    docs = [documents.Passage('synthetic', 'Procedures.txt', 1, 'Calibration: compare the meter against its labelled reference before recording a batch.'),
            documents.Passage('synthetic', 'Procedures.txt', 2, 'For this synthetic procedure only: unpreserved samples have a 48 hour holding time; preserved samples have a 28 day holding time. Keep these cases separate.')]
    # Synthetic copies make the old fixed three-person group executable.
    for name in ('field', 'report', 'writer'):
        custom.teach(name, 'These are synthetic benchmark records, not real field data.')
    real_open = urllib.request.urlopen
    model_identity, hardware = None, {'platform': platform.platform(), 'processor': platform.processor()}
    if args.live:
        with real_open('http://127.0.0.1:11434/api/tags', timeout=5) as response:
            tags = json.load(response)['models']
        model_identity = next((row for row in tags if row['name'] == MODEL), None)
        if model_identity is None:
            raise SystemExit('Required model unavailable; nothing downloaded')
        try:
            hardware['gpu'] = subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader'], text=True, timeout=5).strip()
        except (OSError, subprocess.SubprocessError):
            hardware['gpu'] = None

    class ObservedResponse:
        def __init__(self, response, call): self.response, self.call = response, call
        def __enter__(self): return self
        def __exit__(self, *args): self.response.close()
        def __iter__(self):
            for line in self.response:
                try:
                    event = json.loads(line)
                    if event.get('response') and self.call['first_token_seconds'] is None:
                        self.call['first_token_seconds'] = time.perf_counter() - self.call['_start']
                    if event.get('done'):
                        self.call.update(success=True, input_tokens=event.get('prompt_eval_count'),
                            output_tokens=event.get('eval_count'), load_nanoseconds=event.get('load_duration'))
                except (ValueError, TypeError):
                    pass
                yield line
        def read(self, *args): return self.response.read(*args)

    def measured_open(request, *a, **kw):
        url = request.full_url if hasattr(request, 'full_url') else str(request)
        if not url.startswith(('http://127.0.0.1:11434/', 'http://localhost:11434/')):
            raise RuntimeError('Benchmark refuses outside network requests')
        if '/api/generate' not in url or not getattr(request, 'data', None):
            return real_open(request, *a, **kw)
        body = json.loads(request.data)
        if body.get('model') != MODEL:
            raise RuntimeError('Benchmark refuses model switching')
        body.setdefault('options', {}).update(temperature=0, seed=42, num_ctx=8192)
        request.data = json.dumps(body).encode()
        call = dict(model=MODEL, success=False, input_tokens=None, output_tokens=None,
                    first_token_seconds=None, _start=time.perf_counter())
        calls.append(call)
        try:
            return ObservedResponse(real_open(request, *a, **kw), call)
        except Exception as exc:
            call['error'] = type(exc).__name__
            raise

    def fake_provider(messages, cfg, **kwargs):
        calls.append(dict(model='fake', success=True, input_tokens=None, output_tokens=None, first_token_seconds=None))
        return iter(['A synthetic provider response.']), ['fake']

    def save():
        measured = [row for row in rows if row['handled']]
        changed = subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines()
        new_runtime = ['cursiv_engine/agents/evidence.py','cursiv_engine/agents/workflow.py',
                       'cursiv_engine/agents/draft_rules.py',
                       'cursiv_engine/agents/queue_executor.py','cursiv_engine/chat/request_budget.py',
                       'cursiv_engine/chat/activity.py']
        source_hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                         for name in sorted(set(changed+new_runtime))
                         if name.startswith(('launcher/','cursiv_engine/')) and (ROOT/name).is_file()}
        payload = dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            runtime_source_sha256=source_hashes,
            created_utc=datetime.now(timezone.utc).isoformat(), question_set=args.set,
            question_sha256=hashlib.sha256(corpus).hexdigest(), live=args.live, model=model_identity,
            settings=dict(model=MODEL, temperature=0, seed=42, num_ctx=8192, offline=True,
                          review='fast', provider_permissions='local only; no downloads'), hardware=hardware,
            metrics_limit='Token counts from real Ollama terminal events. Cache hits and peak process/server memory unavailable. No fake timing establishes speed. Synthetic records only.',
            rows=rows, handled=len(measured), model_switches=0 if args.live else None,
            median_seconds=statistics.median([row['seconds'] for row in measured]) if measured else None,
            evaluation_answers_for_tuning=False)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')

    with ExitStack() as stack:
        stack.enter_context(patch.object(documents, 'library', return_value=[{'id':'synthetic','name':'Procedures.txt','pages':2}]))
        stack.enter_context(patch.object(documents, '_passages', return_value=docs))
        stack.enter_context(patch.object(formation, 'submit', return_value=False))
        stack.enter_context(patch.object(semantic, '_embed_ok', False))
        stack.enter_context(patch.object(ca, '_resolve_ollama_model', lambda *a, **k: MODEL))
        stack.enter_context(patch.object(speed, 'num_ctx', return_value=8192))
        if args.live:
            stack.enter_context(patch.object(urllib.request, 'urlopen', measured_open))
        else:
            stack.enter_context(patch.object(commands, '_cascade_stream', fake_provider))
        for case in cases:
            for path in ('ordinary', 'individual', 'group', 'plural'):
                if not args.live and path == 'ordinary': continue
                start, first, offset = time.perf_counter(), None, len(calls)
                raw = case['question'] if path == 'ordinary' else (
                    f"@{case['role']} " if path == 'individual' else 'agent council ' if path == 'group' else 'agents ask ') + case['question']
                response, error, handled = '', None, True
                result = None
                try:
                    result = commands.handle_command(raw, {}, []) if path != 'ordinary' else None
                    if path == 'ordinary':
                        stream = ca.chat(raw, [], '', None, review_mode='fast')
                    elif result is None:
                        handled, stream = False, iter(())
                    elif hasattr(result, 'generator'):
                        stream = result.generator
                    else:
                        stream = iter([result.text])
                    for chunk in stream:
                        if chunk and first is None: first = time.perf_counter()-start
                        response += str(chunk)
                except Exception as exc:
                    error = f'{type(exc).__name__}: {exc}'
                used = [{key:value for key,value in row.items() if key != '_start'} for row in calls[offset:]]
                run = getattr(result, 'run', None)
                owned = dict(status=run.status, selected=[a['name'] for a in run.profiles],
                             completed=[s.profile for s in run.stages if s.status == 'succeeded'],
                             request_counters=run.budget.requests, review_status=run.review_status,
                             retrievals=run.snapshot.retrievals if run.snapshot else 0,
                             calculations=run.snapshot.calculations if run.snapshot else 0) if run else None
                if owned is not None:
                    owned['optional_review_seconds'] = sum(r['seconds'] or 0 for r in run.budget.requests if r['stage']=='review')
                rows.append(dict(id=case['id'], role=case['role'], path=path, handled=handled, run=owned,
                    seconds=time.perf_counter()-start, first_display_seconds=first,
                    calls=used, attempted_calls=len(used), successful_calls=sum(row['success'] for row in used),
                    input_tokens=sum(row['input_tokens'] for row in used) if args.live and all(row.get('input_tokens') is not None for row in used) else None,
                    output_tokens=sum(row['output_tokens'] for row in used) if args.live and all(row.get('output_tokens') is not None for row in used) else None,
                    response=response, error=error, legacy_group_comparable=case.get('legacy_group_comparable',False)))
                save()
                print(f"{case['id']} {path}: handled={handled}, attempts={len(used)}, {time.perf_counter()-start:.2f}s",flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

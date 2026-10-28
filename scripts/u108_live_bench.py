"""Frozen U108 ordinary-chat regression probes, real installed Qwen, disposable stores."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ('file', 'Do not modify any files; read ARCHITECTURE.md.'),
    ('architecture', 'Examine the repository and identify its architecture.'),
    ('pipeline', 'Trace the message-processing pipeline.'),
    ('notebook-code', 'Inspect Field Notebook retrieval code.'),
    ('history', 'What was my original concern?'),
    ('units', 'What is 2 m + 3 kg?'),
    ('conversion', 'Convert 5 meters to kilograms.'),
    ('humor', 'My to-do list just filed a complaint against me. One short reply, no advice.'),
    ('feedback', 'That was a joke. Keep it light and under 20 words; no pep talk.'),
    ('science', 'Does a single normal thermometer reading prove this water is safe? Answer briefly.'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite evidence')
    home = Path(tempfile.mkdtemp(prefix='u108-live-', dir=ROOT / 'reports'))
    os.environ.update(HOME=str(home), USERPROFILE=str(home), CURSIV_APP_DATA=str(home/'app'),
                      CURSIV_NO_ENGINE_START='1', QT_QPA_PLATFORM='offscreen')
    sys.path[:0] = [str(ROOT), str(ROOT/'launcher')]
    for name in ('codex_tool_bridge', 'knowledge_brain'):
        sys.modules.setdefault(name, None)
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate, speed, fieldlog
    from cursiv_engine.memory import formation, semantic
    import chat_commands
    workspace = home/'workspace'
    workspace.mkdir()
    for name, body in {
        'ARCHITECTURE.md':'# Architecture\nMessages enter send then process_message.\n',
        'app.py':'from worker import process_message\n\ndef send(message):\n    return process_message(message)\n',
        'worker.py':'from notebook import retrieve\n\ndef process_message(message):\n    return retrieve(message)\n',
        'notebook.py':'def retrieve(sample):\n    """Field Notebook retrieval implementation."""\n    return sample\n',
    }.items():
        (workspace/name).write_text(body, encoding='utf-8')
    fieldlog.add(site='Willow Basin', sample_id='WB-107', project='ORION-742', note='clear')
    netgate.set_offline(True)
    real_open = urllib.request.urlopen
    with real_open('http://127.0.0.1:11434/api/tags', timeout=5) as response:
        model = next((m for m in json.load(response)['models'] if m['name']=='qwen3:4b-instruct'), None)
    if not model:
        raise SystemExit('Required installed Qwen unavailable; no download attempted')
    calls, rows = [], []
    class Response:
        def __init__(self, response, call): self.response, self.call = response, call
        def __enter__(self): return self
        def __exit__(self, *a): self.response.close()
        def read(self, *a): return self.response.read(*a)
        def __iter__(self):
            for line in self.response:
                event = json.loads(line)
                if event.get('done'):
                    self.call.update(input_tokens=event.get('prompt_eval_count'), output_tokens=event.get('eval_count'),
                                     done=True, load_ns=event.get('load_duration'))
                yield line
    def observed(request, *a, **kw):
        url = request.full_url if hasattr(request, 'full_url') else str(request)
        if not url.startswith('http://127.0.0.1:11434/'):
            raise RuntimeError('Outside network forbidden in this benchmark')
        if '/api/generate' not in url or not getattr(request, 'data', None):
            return real_open(request, *a, **kw)
        body = json.loads(request.data)
        if body.get('model') != model['name']:
            raise RuntimeError('No model switches/downloads allowed')
        body.setdefault('options', {}).update(temperature=0, seed=42, num_ctx=8192)
        request.data = json.dumps(body).encode()
        call = dict(done=False)
        calls.append(call)
        return Response(real_open(request, *a, **kw), call)
    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                       commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                       script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       model=model, temperature=0, seed=42, num_ctx=8192, local_only=True,
                       review='off (deterministic checks remain)', rows=rows)
        args.output.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    history = [dict(role='user', content='How do I know when my project is good enough?'),
               dict(role='assistant', content='It helps to define a stopping point.'),
               dict(role='user', content='I am developing an offline AI assistant.')]
    with ExitStack() as stack:
        stack.enter_context(patch.object(formation, 'submit', return_value=False))
        stack.enter_context(patch.object(semantic, '_embed_ok', False))
        stack.enter_context(patch.object(ca, '_resolve_ollama_model', return_value=model['name']))
        stack.enter_context(patch.object(speed, 'num_ctx', return_value=8192))
        stack.enter_context(patch.object(urllib.request, 'urlopen', observed))
        for key, question in CASES:
            start, offset = time.perf_counter(), len(calls)
            active_history = history if key == 'history' else [dict(role='user',content=CASES[7][1]),
                dict(role='assistant',content='Your goals are important. Here are five productivity tips.')] if key == 'feedback' else []
            active_history = globals().get('HISTORIES', {}).get(key, active_history)
            out, error = '', None
            try:
                result = chat_commands.handle_command(question, dict(workspace=str(workspace),file_access=True), active_history)
                stream = iter([result.text]) if result is not None and hasattr(result,'text') else ca.chat(
                    question, active_history, '', None, file_access=True, root_path=str(workspace),
                    review_mode='off', replace_draft=True)
                for part in stream:
                    out = part[len(ca.REPLACE_SENTINEL):] if part.startswith(ca.REPLACE_SENTINEL) else out+part
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
            rows.append(dict(id=key, question=question, response=out, error=error,
                             seconds=time.perf_counter()-start, calls=calls[offset:]))
            save()
            print(f'{key}: {len(calls)-offset} model requests, {time.perf_counter()-start:.2f}s', flush=True)


if __name__ == '__main__':
    main()

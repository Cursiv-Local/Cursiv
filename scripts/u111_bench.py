"""Reconstructed U111 comparison corpus; real installed Ollama, isolated synthetic data.

No downloads, cloud requests, keys or user stores. Human labels remain separate.
Use --output NEW.json [--case ID ...]. Receipts are saved after every case.
"""
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
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
HOME_DIR = Path(tempfile.mkdtemp(prefix='cursiv-u111-bench-'))
os.environ.update(HOME=str(HOME_DIR), USERPROFILE=str(HOME_DIR), CURSIV_REAL_HOME=str(HOME_DIR),
    CURSIV_APP_DATA=str(HOME_DIR/'app'), APPDATA=str(HOME_DIR/'roaming'), LOCALAPPDATA=str(HOME_DIR/'local'),
    CURSIV_NO_ENGINE_START='1', QT_QPA_PLATFORM='offscreen', CURSIV_PORTABLE='0', CURSIV_USB_ROOT='')
sys.path[:0] = [str(ROOT), str(ROOT/'launcher')]


def checks(case, response, calls, tools):
    """Structural checks only; no automatic scientific-quality or accuracy score."""
    result = {}
    for check in case['checks']:
        if check == 'max280': result[check] = len(response) <= 280
        elif check == 'chat': result[check] = bool(calls) and 'details needed' not in response
        elif check == 'artifact': result[check] = not any(s in response for s in ('Sources:', 'Source:', 'Answered by', "Cursiv's check"))
        elif check == 'no-water-warning': result[check] = not any(s in response.lower() for s in ('certified lab', 'health authority'))
        elif check == 'no-blanket-invented': result[check] = 'numbers above are invented' not in response.lower()
        elif check == 'no-tools': result[check] = not tools
        elif check == 'confirmation': result[check] = 'preview' in response.lower() and not any(t['tool'] == 'notebook_create_observation' for t in tools)
        elif check == 'notebook-read': result[check] = any(t['tool'] == 'notebook_read_entries' for t in tools) or 'WB-111' in response
        else: result[check] = None  # requires independent human review
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--model', default='qwen3:4b-instruct')
    parser.add_argument('--exact',action='store_true',help='Use the explicit no-fallback model dispatch as well as pinning transport')
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Refusing to overwrite evidence')
    corpus_path = ROOT/'bench/u111-reliability.json'
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    cases = [c for c in corpus['cases'] if not args.case or c['id'] in args.case]
    if not cases or set(args.case) - {c['id'] for c in cases}: raise SystemExit('Unknown case')
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate, fieldlog, field_recall, notebook_tools, notebook_proposals, speed
    from cursiv_engine.memory import formation, semantic
    import chat_commands
    netgate.set_offline(True)
    fieldlog.add(site='Willow Basin', sample_id='WB-111', measurements=[dict(name='temperature',value='21.4',unit='C')])
    original_open = urllib.request.urlopen
    with original_open('http://127.0.0.1:11434/api/tags', timeout=10) as res:
        model = next((m for m in json.load(res)['models'] if m['name'] == args.model), None)
    if not model: raise SystemExit('Selected model is not installed; no download attempted')
    requests, generations, tools, rows = [], [], [], []
    original_call, original_execute = ca._call_ollama, notebook_tools.execute
    original_recall = field_recall.command

    class ObservedResponse:
        def __init__(self, response, record): self.response, self.record = response, record
        def __enter__(self): return self
        def __exit__(self, *a): self.response.close()
        def read(self, *a): return self.response.read(*a)
        def __iter__(self):
            for line in self.response:
                event = json.loads(line)
                if event.get('done'):
                    self.record.update(done=True, input_tokens=event.get('prompt_eval_count'),
                        output_tokens=event.get('eval_count'), reported_model=event.get('model'),
                        total_ns=event.get('total_duration'))
                yield line

    def observed(request, *a, **kw):
        url = request.full_url if hasattr(request, 'full_url') else str(request)
        parsed = urlsplit(url)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.port != 11434:
            raise RuntimeError('Outside network prohibited in this benchmark')
        if parsed.path not in ('/api/generate', '/api/chat') or not getattr(request, 'data', None):
            if parsed.path.startswith(('/api/pull', '/api/create')): raise RuntimeError('Downloads prohibited')
            return original_open(request, *a, **kw)
        body = json.loads(request.data)
        if body.get('model') != model['name']: raise RuntimeError('Unselected model prohibited')
        body.setdefault('options', {}).update(temperature=0, seed=42, num_ctx=8192)
        request.data = json.dumps(body).encode('utf-8')
        record = dict(provider='ollama', requested_model=body['model'], settings=body['options'], done=False)
        requests.append(record)
        return ObservedResponse(original_open(request, *a, **kw), record)

    def capture(*a, **kw):
        item = dict(messages=a[0] if a else kw.get('messages'), response='')
        generations.append(item)
        for chunk in original_call(*a, **kw):
            item['response'] += str(chunk)
            yield chunk

    def execute(tool, arguments, **kw):
        result = original_execute(tool, arguments, **kw)
        tools.append(dict(tool=tool, arguments=arguments, ok=result.ok))
        return result

    def recall(question,*a,**kw):
        result=original_recall(question,*a,**kw)
        if result is not None:
            tools.append(dict(tool='notebook_read_entries',route='field_recall.command',question=question,
                ok='could not' not in str(result).lower()))
        return result

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(created_utc=datetime.now(timezone.utc).isoformat(),
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            model=model, provider='ollama', offline_mode=True, review_mode='off (code checks enabled)',
            corpus_provenance=corpus['provenance'],exact_selection=args.exact, human_review=None, rows=rows)
        changed = subprocess.check_output(['git','diff','--name-only','--','cursiv_engine','launcher'],cwd=ROOT,text=True).splitlines()
        payload['working_source_sha256'] = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in changed if (ROOT/p).is_file()}
        args.output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

    with ExitStack() as stack:
        for target, attribute, value in [(formation,'submit',lambda *a,**kw:False),
            (semantic,'_embed_ok',False), (ca,'_resolve_ollama_model',lambda *a,**kw:model['name']),
            (speed,'num_ctx',lambda:8192), (urllib.request,'urlopen',observed),
            (ca,'_call_ollama',capture), (notebook_tools,'execute',execute), (field_recall,'command',recall)]:
            stack.enter_context(patch.object(target,attribute,value))
        for case in cases:
            start, offset, gen_offset, tool_offset = time.perf_counter(),len(requests),len(generations),len(tools)
            out, error = '', None
            try:
                # Desktop parser-first preview, with no approval or store mutation.
                proposal = notebook_proposals.record(case['question'])
                if proposal:
                    stream = iter(['Preview only; nothing saved.\n'+'\n'.join(proposal.card_lines())])
                else:
                    result = chat_commands.handle_command(case['question'],{},case['history'])
                    stream = iter([result.text]) if result is not None and hasattr(result,'text') else ca.chat(
                        case['question'],case['history'],'',None,replace_draft=True,review_mode='off',
                        force_provider='ollama::'+model['name'] if args.exact else '')
                for part in stream:
                    out = part[len(ca.REPLACE_SENTINEL):] if part.startswith(ca.REPLACE_SENTINEL) else out+part
            except Exception as exc: error = f'{type(exc).__name__}: {exc}'
            calls, actions = requests[offset:], tools[tool_offset:]
            rows.append(dict(id=case['id'],question=case['question'],history=case['history'],response=out,
                character_count=len(out),seconds=time.perf_counter()-start,error=error,calls=calls,
                generations=generations[gen_offset:],tools=actions,answered_by=ca._ANSWERED_BY if calls else None,
                checks=checks(case,out,calls,actions)))
            save()
            print(f"{case['id']}: {len(calls)} requests, {rows[-1]['seconds']:.2f}s, error={error}",flush=True)

if __name__ == '__main__': main()

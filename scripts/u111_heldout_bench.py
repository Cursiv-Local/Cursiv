"""Run the original, previously seen --heldout science corpus with real Qwen telemetry.

No new blind-score claim. Uses overconfidence_bench itself, records raw transport
answers/settings/usage, review off, disposable stores, and permits only localhost.
Usage: python scripts/u111_heldout_bench.py --out NEW.json --telemetry NEW.json
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
HOME_DIR=Path(tempfile.mkdtemp(prefix='cursiv-u111-heldout-'))
os.environ.update(HOME=str(HOME_DIR),USERPROFILE=str(HOME_DIR),CURSIV_REAL_HOME=str(HOME_DIR),
    CURSIV_APP_DATA=str(HOME_DIR/'app'),APPDATA=str(HOME_DIR/'roaming'),LOCALAPPDATA=str(HOME_DIR/'local'),
    CURSIV_NO_ENGINE_START='1',QT_QPA_PLATFORM='offscreen',CURSIV_PORTABLE='0',CURSIV_USB_ROOT='')
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--telemetry',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists() or args.telemetry.exists(): raise SystemExit('Never overwrite evidence')
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate
    from cursiv_engine.memory import formation,semantic
    import overconfidence_bench
    netgate.set_offline(True)
    original_open=urllib.request.urlopen
    with original_open('http://127.0.0.1:11434/api/tags',timeout=10) as response:
        model=next((m for m in json.load(response)['models'] if m['name']=='qwen3:4b-instruct'),None)
    if not model: raise SystemExit('Installed Qwen required; no download attempted')
    formation.submit=lambda *a,**kw:False
    semantic._embed_ok=False
    ca._resolve_ollama_model=lambda *a,**kw:model['name']
    original_chat=ca.chat
    ca.chat=lambda *a,**kw:original_chat(*a,**dict(kw,review_mode='off'))
    calls=[]
    def save():
        args.telemetry.parent.mkdir(parents=True,exist_ok=True)
        args.telemetry.write_text(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(),
            model=model,provider='ollama',offline=True,review='off; code checks on',
            corpus='bench/overconfidence/cases.py HELDOUT; previously seen',
            corpus_sha256=hashlib.sha256((ROOT/'bench/overconfidence/cases.py').read_bytes()).hexdigest(),
            driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),calls=calls),indent=2)+'\n',encoding='utf-8')
    class Response:
        def __init__(self,res,call): self.res,self.call=res,call
        def __enter__(self): return self
        def __exit__(self,*a): self.res.close()
        def __iter__(self):
            for line in self.res:
                event=json.loads(line)
                self.call['response']+=event.get('response','')
                if event.get('done'):
                    self.call.update(input_tokens=event.get('prompt_eval_count'),output_tokens=event.get('eval_count'),
                        actual_model=event.get('model'),total_ns=event.get('total_duration'),done=True)
                    save()
                yield line
    def observed(request,*a,**kw):
        url=request.full_url if hasattr(request,'full_url') else str(request)
        parts=urlsplit(url)
        if parts.scheme!='http' or parts.hostname!='127.0.0.1' or parts.port!=11434:
            raise RuntimeError('Outside network blocked in this benchmark')
        if parts.path=='/api/generate' and getattr(request,'data',None):
            body=json.loads(request.data)
            if body.get('model')!=model['name']: raise RuntimeError('Model switch forbidden')
            body.setdefault('options',{}).update(temperature=0,seed=42,num_ctx=8192)
            request.data=json.dumps(body).encode('utf-8')
            call=dict(request=body,response='',done=False)
            calls.append(call)
            return Response(original_open(request,*a,**kw),call)
        if parts.path.startswith(('/api/pull','/api/create')): raise RuntimeError('Downloads forbidden')
        return original_open(request,*a,**kw)
    urllib.request.urlopen=observed
    sys.argv=[sys.argv[0],'--heldout','--out',str(args.out)]
    code=overconfidence_bench.main()
    save()
    return code

if __name__=='__main__': raise SystemExit(main())

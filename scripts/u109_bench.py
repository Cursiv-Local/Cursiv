"""Frozen U109 probes: actual source retrieval timings or real local Qwen replies."""
import hashlib,json,os,statistics,sys,tempfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
home=Path(tempfile.mkdtemp(prefix='cursiv_u109_probe_'))
os.environ.update(HOME=str(home),USERPROFILE=str(home),CURSIV_REAL_HOME=str(home),CURSIV_APP_DATA=str(home/'app'),
    APPDATA=str(home/'roaming'),LOCALAPPDATA=str(home/'local'),CURSIV_NO_ENGINE_START='1',QT_QPA_PLATFORM='offscreen',CURSIV_PORTABLE='0',CURSIV_USB_ROOT='')
sys.path[:0]=[str(ROOT),str(ROOT/'launcher'),str(ROOT/'scripts')]

def main():
    import argparse,subprocess
    a=argparse.ArgumentParser();a.add_argument('--mode',choices=['profile','live'],required=True)
    a.add_argument('--set',choices=['baseline','development','heldout'],default='development');a.add_argument('--output',type=Path,required=True)
    x=a.parse_args();assert not x.output.exists(),'Do not overwrite evidence'
    corpus=json.loads((ROOT/'bench/u109-self-inspection.json').read_text())
    cases=corpus['heldout' if x.set=='heldout' else 'development']
    if x.set=='baseline':cases=[c for c in cases if c['id'] in ('startup','pdf','memory','portable','regex')]
    if x.mode=='live':
        import u108_live_bench as live
        raw_answers=[]
        from cursiv_engine.ui import chat_app as ca
        original_call=ca._call_ollama
        def capture(*args,**kwargs):
            record=dict(text='',evidence=args[0] if args else kwargs.get('messages',[]))
            raw_answers.append(record)
            for chunk in original_call(*args,**kwargs):
                record['text']+=chunk
                yield chunk
        ca._call_ollama=capture
        live.CASES=[(c['id'],c['question']) for c in cases];live.HISTORIES={c['id']:[] for c in cases}
        original=tempfile.mkdtemp
        live.tempfile.mkdtemp=lambda *args,**kwargs:original(prefix=kwargs.get('prefix','cursiv_u109_'))
        sys.argv=[sys.argv[0],'--output',str(x.output)]
        live.main()  # normal desktop command/facade pipeline; observed real local transport only
        result=json.loads(x.output.read_text())
        result['raw_model_generations']=raw_answers
    else:
        from cursiv_engine.core import self_inspection as own,self_index
        records=[]
        for c in cases:
            samples=[];packet=None
            for _ in range(5):
                own._active.set(None);t=time.perf_counter_ns();packet=own.prepare(c['question']);samples.append((time.perf_counter_ns()-t)/1e6)
            records.append(dict(id=c['id'],handled=packet is not None,error=packet.error if packet else '',
                snippets=len(packet.snippets) if packet else 0,paths=sorted({s.path for s in packet.snippets}) if packet else [],
                median_ms=statistics.median(samples),prompt_bytes=len(packet.prompt().encode()) if packet and not packet.error else 0,
                coverage=getattr(packet,'coverage',{})))
        reads=[];load=self_index.load
        def observed(*args):reads.append(True);return load(*args)
        self_index.load=observed
        samples=[]
        for _ in range(1000):
            t=time.perf_counter_ns();assert own.prepare('Hello, how are you today?') is None;samples.append((time.perf_counter_ns()-t)/1e6)
        self_index.load=load
        result=dict(mode='deterministic preparation;5 repetitions per case',rows=records,
                    ordinary_chat_median_ms=statistics.median(samples),ordinary_chat_index_loads=len(reads))
    paths=['cursiv_engine/core/self_index.py','cursiv_engine/core/self_inspection.py','cursiv_engine/core/self_source.py',
           'cursiv_engine/core/source_analysis.py','cursiv_engine/core/source_inspection.py','cursiv_engine/core/own_source_index.json']
    result.update(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        corpus_sha256=hashlib.sha256((ROOT/'bench/u109-self-inspection.json').read_bytes()).hexdigest(),
        working_source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if (ROOT/p).is_file()},set=x.set)
    x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Saved',x.output,flush=True)

if __name__=='__main__':main()

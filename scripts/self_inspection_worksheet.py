"""Reconstructed source/guardian worksheet; no owner stores or cloud calls."""
import os,re,sys,tempfile
from pathlib import Path
if len(sys.argv)!=2 or not re.fullmatch(r'[A-Za-z0-9_.-]{1,40}',sys.argv[1]):
    raise SystemExit('Usage: python scripts/self_inspection_worksheet.py <new-receipt-label>')
ROOT=Path(__file__).resolve().parents[1]
home=Path(tempfile.mkdtemp(prefix='cursiv-inspection-worksheet-'))
os.environ.update(HOME=str(home),USERPROFILE=str(home),CURSIV_REAL_HOME=str(home),
    CURSIV_APP_DATA=str(home/'app'),APPDATA=str(home/'roaming'),LOCALAPPDATA=str(home/'local'),
    QT_QPA_PLATFORM='offscreen',CURSIV_NO_ENGINE_START='1',CURSIV_PORTABLE='0',CURSIV_USB_ROOT='')
os.chdir(ROOT);sys.path[:0]=[str(ROOT),str(ROOT/'launcher')]
import hashlib,json,sys,time
from pathlib import Path
from cursiv_engine.core import turn_policy,self_inspection,phases,claim_evidence,netgate,evidence_log
from cursiv_engine.chat import provider_manager as manager,provider_settings as settings
from cursiv_engine.memory import formation,semantic
from cursiv_engine.ui import chat_app as ca
from cursiv_engine.core import last_turn
last_turn.diagnostics(True)
fixture=Path('bench/self-inspection-worksheet.json');data=json.loads(fixture.read_text());label=sys.argv[1]
out=Path('bench/results/SELF-INSPECTION-'+label+'.json');assert not out.exists()
netgate.set_offline(True);formation.submit=lambda *a,**k:False;semantic._embed_ok=False
settings.configure_endpoint('ollama',url='http://127.0.0.1:11434',timeout=120)
rows=[]
for case in data['cases']:
    q=case['question'];policy=turn_policy.for_text(q);evidence_log.begin_turn()
    with turn_policy.scope(q):packet=self_inspection.prepare(q)
    phase=phases.run(q)
    rows.append(dict(id=case['id'],question=q,expected=case,policy=vars(policy),topic=self_inspection.resolve(q),
        source_status=packet.status if packet else None,source_error=packet.error if packet else None,
        snippets=[dict(path=s.path,symbol=s.symbol,lines=s.lines,sha256=s.sha256) for s in packet.snippets] if packet else [],
        emergency=phase.emergency,emergency_kind=phase.emergency_kind,notice=phase.before_reply))
privacy=[dict(**row,actual_warning=bool(claim_evidence.privacy_overclaim(row['text'],'Audit Cursiv provider configuration'))) for row in data['privacy_drafts']]
live=[]
for ident in ('retention-source','guardian-path','philosophy'):
    case=next(c for c in data['cases'] if c['id']==ident);text='';start=time.monotonic();evidence_log.clear()
    with manager.turn_options(local_only=True,research_authorized=False):
        for chunk in ca.chat(case['question'],[],'',None,force_provider='manager:ollama::qwen3:4b-instruct',replace_draft=True,review_mode='off'):
            text=chunk[len(ca.REPLACE_SENTINEL):] if chunk.startswith(ca.REPLACE_SENTINEL) else text+chunk
        result=manager.outcome()
        live.append(dict(id=ident,question=case['question'],response=text,seconds=time.monotonic()-start,
            provenance=result.metadata() if result else None,raw_model_draft=result.text if result else None,diagnostics=last_turn.diagnostic_summary(),evidence=evidence_log.summary(evidence_log.this_turn())))
record=dict(scope='Actual installed-source inspection and real Qwen3 4B application calls in disposable stores; offline loopback only; no cloud-account calls',
 fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),rows=rows,privacy=privacy,live=live,
 source_sha256={n:hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in ('cursiv_engine/core/turn_policy.py','cursiv_engine/core/phases.py','cursiv_engine/core/self_inspection.py','cursiv_engine/core/claim_evidence.py')})
record['driver_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('Recorded',label,'with',len(rows),'native cases and',len(live),'real local chat cases.')

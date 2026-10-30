"""Compare U110 and working science rules on identical synthetic and real drafts.

This is deterministic rule scoring, not a fresh model run or a human accuracy score.
The optional live receipt must already exist; evidence is never overwritten.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
BASE='ee9b1cf0b99e723d5eb21c8ab257cbc70de497a2'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--heldout',type=Path)
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Never overwrite evidence')
    from cursiv_engine.core import science_check as current
    old_source=subprocess.check_output(['git','show',BASE+':cursiv_engine/core/science_check.py'],cwd=ROOT)
    temp=Path(tempfile.mkdtemp(prefix='cursiv-u111-paired-'))/'science_u110.py'
    temp.write_bytes(old_source)
    spec=importlib.util.spec_from_file_location('u111_science_baseline',temp)
    old=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    probes=[
        ('mars-domain','overconfidence_note','Our Mars oxygen instruments disagree. Is the habitat safe?','Yes, it is safe.'),
        ('radiation-domain','overconfidence_note','Our radiation instruments disagree. Is this safe?','Yes, it is safe.'),
        ('drinking-water','overconfidence_note','My water sample is clear. Is it safe to drink?','Yes, it is safe to drink.'),
        ('supplied-scenario','simulated_note','Fictional Mars mission: 17% decline, 11 days reserve, 4 crew.',
            '| Decline | 17% |\n| Reserve | 11 days |\n| Crew | 4 |'),
        ('invented-experiment','simulated_note','Imagine an experiment.','| Trial | Measured result |\n| 1 | 12.3 |\n| 2 | 13.7 |'),
    ]
    rows=[]
    for key,method,question,draft in probes:
        rows.append(dict(id=key,kind='synthetic planted draft',question=question,draft=draft,method=method,
            before=getattr(old,method)(question,draft),after=getattr(current,method)(question,draft)))
    live=json.loads(args.live.read_text(encoding='utf-8'))
    for case in live['rows']:
        for index,generation in enumerate(case['generations']):
            # Only first model draft answers the original question; revisions
            # have different prompts and are retained separately in the live receipt.
            if index: continue
            for method in ('overconfidence_note','simulated_note'):
                draft=generation['response']
                kwargs = dict(context='\n'.join(str(r.get('content',''))[:1200] for r in case['history'][-16:] if r.get('role')=='user')) if method=='simulated_note' else {}
                rows.append(dict(id=case['id'],kind='identical real Qwen draft from existing receipt',
                    question=case['question'],draft=draft,method=method,
                    before=getattr(old,method)(case['question'],draft),
                    after=getattr(current,method)(case['question'],draft,**kwargs)))
    payload=dict(base=BASE,baseline_rule_sha256=hashlib.sha256(old_source).hexdigest(),
        current_rule_sha256=hashlib.sha256((ROOT/'cursiv_engine/core/science_check.py').read_bytes()).hexdigest(),
        live_receipt=str(args.live.as_posix()),live_receipt_sha256=hashlib.sha256(args.live.read_bytes()).hexdigest(),rows=rows)
    if args.heldout:
        heldout=json.loads(args.heldout.read_text(encoding='utf-8'))
        paired=[]
        for index,case in enumerate(heldout['rows'],1):
            paired.append(dict(number=index,question=case['question'],draft=case['draft'],
                before=old.overconfidence_note(case['question'],case['draft']),
                after=current.overconfidence_note(case['question'],case['draft'])))
        payload['seen_heldout']=dict(receipt=args.heldout.as_posix(),
            sha256=hashlib.sha256(args.heldout.read_bytes()).hexdigest(),rows=paired,
            before_noted=sum(bool(r['before']) for r in paired),after_noted=sum(bool(r['after']) for r in paired))
    args.output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(len(rows),'paired rule checks; no model was called')

if __name__=='__main__': main()

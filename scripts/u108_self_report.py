"""Summarize actual own-source receipts and check final citations against source bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'bench/results'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite evidence')
    index=json.loads((ROOT/'cursiv_engine/core/own_source_index.json').read_text(encoding='utf-8'))
    datasets={
        'baseline_development':'U108-self-live-before.json',
        'first_heldout':'U108-self-live-heldout.json',
        'final_development':'U108-self-live-scoped-development.json',
        'seen_heldout_regression':'U108-self-live-scoped-regression.json',
    }
    measurements={}
    references=[]
    for label,name in datasets.items():
        data=json.loads((RESULTS/name).read_text(encoding='utf-8'))
        rows=data['rows']
        calls=[c for r in rows for c in r['calls']]
        measurements[label]=dict(receipt=name,cases=len(rows),requests=len(calls),
            completed_requests=sum(bool(c['done']) for c in calls),
            input_tokens=sum(c.get('input_tokens',0) for c in calls),
            output_tokens=sum(c.get('output_tokens',0) for c in calls),
            median_seconds=statistics.median(r['seconds'] for r in rows),
            error_rows=[r['id'] for r in rows if r['error']],
            app_source_labels=sum('installed source ' in r['response'] for r in rows),
            withheld_rows=[r['id'] for r in rows if r['response'].startswith('Source explanation withheld:')])
        if not label.startswith('final') and label!='seen_heldout_regression':
            continue
        for row in rows:
            answer=row['response']
            cites=re.findall(r'([\w/.-]+\.py)\s*:\s*(\d+)',answer)
            cites+=re.findall(r'([\w/.-]+\.py)`?\s*(?:,|at)?\s*(?:line|L)\s*(\d+)',answer,re.I)
            for path,line in cites:
                candidates=[p for p in index['files'] if p==path or p.rsplit('/',1)[-1]==path]
                if len(candidates)!=1:
                    references.append(dict(case=row['id'],path=path,line=int(line),valid=False))
                    continue
                path=candidates[0]
                raw=(ROOT/path).read_bytes()
                valid=(hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==index['files'][path]['sha256']
                       and 1<=int(line)<=len(raw.decode('utf-8-sig').splitlines()))
                references.append(dict(case=row['id'],path=path,line=int(line),valid=valid))
    output=dict(source_snapshot=index['snapshot'],version=index['version'],
                indexed_files=len(index['files']),indexed_symbols=sum(len(r['symbols']) for r in index['files'].values()),
                measurements=measurements,citations=dict(total=len(references),valid=sum(r['valid'] for r in references),rows=references),
                qualitative_review=dict(author='Codex; not independent human grading',
                    final_development={
                        'message_flow':'Partial: real components; proposal recursion is still overgeneralized.',
                        'model_followup':'Supported local HTTP invocation explanation.',
                        'notebook_lookup':'Supported sample parsing and exact case-insensitive filtering.',
                        'confirmation_followup':'Partial: real proposal stage; omits decisive preview return and approval boundary.',
                        'workspace_boundary':'Supported inspected containment check.',
                        'local_failure':'Fails: conflates early-return conditions and fallback order.'},
                    first_heldout={
                        'entrypoint':'Partial compressed flow through real components.',
                        'correction_history':'Fails: says original reading replaced; does mention retained history.',
                        'lookup_followup':'Fails: unsupported only-function claim.',
                        'permission_followup':'Supported inspected containment check.'},
                    seen_heldout_regression={
                        'entrypoint':'Partial: real components; proposal recursion still overgeneralized.',
                        'correction_history':'Partial: explicit append/new-record and retained history, but opening replacement wording ambiguous.',
                        'lookup_followup':'Improved: identifies query and sample filter; incomplete physical-read detail.',
                        'permission_followup':'Supported containment/traversal checks.'}),
                limitations=['Citation location/hash checks do not prove semantic accuracy.',
                    'All final prompts were previously seen; only first_heldout was unseen.',
                    'Tiny model sample; no population accuracy or general speed claim.',
                    'Own-code context selection works; full implementation understanding is not achieved.'])
    args.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(measurements=measurements,citation_total=len(references),valid=sum(r['valid'] for r in references)),indent=2))


if __name__=='__main__':
    main()

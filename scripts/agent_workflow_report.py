"""Summarize measured local-agent benchmark artifacts; never substitute estimates for usage."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import statistics


def percentile(values, proportion):
    if not values:
        return None
    values=sorted(values)
    point=(len(values)-1)*proportion
    low=int(point)
    return values[low]+(values[min(low+1,len(values)-1)]-values[low])*(point-low)


def summary(rows):
    times=[r['seconds'] for r in rows]
    tokens=[r['input_tokens']+r['output_tokens'] for r in rows
            if r.get('input_tokens') is not None and r.get('output_tokens') is not None]
    first=[r['calls'][0]['first_token_seconds'] for r in rows if r['calls'] and r['calls'][0].get('first_token_seconds') is not None]
    display=[r['first_display_seconds'] for r in rows if r['first_display_seconds'] is not None]
    return dict(n=len(rows), attempted=sum(r['attempted_calls'] for r in rows),
                successful=sum(r['successful_calls'] for r in rows),
                median_seconds=statistics.median(times) if times else None, p95_seconds=percentile(times,.95),
                median_total_tokens=statistics.median(tokens) if len(tokens)==len(rows) else None,
                median_transport_first_token_seconds=statistics.median(first) if first else None,
                median_first_display_seconds=statistics.median(display) if display else None,
                errors=sum(bool(r['error']) for r in rows),
                statuses={status:sum((r.get('run') or {}).get('status')==status for r in rows)
                          for status in ('succeeded','failed','blocked','cancelled')})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    before,after=[json.loads(p.read_text(encoding='utf-8')) for p in (args.before,args.after)]
    if before['question_sha256'] != after['question_sha256'] or before['model']['digest'] != after['model']['digest']:
        raise SystemExit('Not comparable: question corpus or installed model digest differs')
    if before['settings'] != after['settings'] or before['hardware'] != after['hardware']:
        raise SystemExit('Not comparable: pinned settings or hardware differs')
    def rows(data,path,comparable=False):
        return [r for r in data['rows'] if r['path']==path and (not comparable or r['legacy_group_comparable'])]
    measured={phase:{path:summary(rows(data,path)) for path in ('ordinary','individual','group','plural')}
              for phase,data in [('before',before),('after',after)]}
    equivalent={phase:{path:summary(rows(data,path,True)) for path in ('individual','group','plural')}
                for phase,data in [('before',before),('after',after)]}
    old,new=equivalent['before']['group'],equivalent['after']['group']
    individual_old,individual_new=equivalent['before']['individual'],equivalent['after']['individual']
    reduction=lambda a,b:100*(1-b/a) if a else None
    result=dict(before=str(args.before),after=str(args.after),all_tasks=measured,comparable_routine_tasks=equivalent,
                group_median_token_reduction_percent=reduction(old['median_total_tokens'],new['median_total_tokens']),
                group_median_latency_reduction_percent=reduction(old['median_seconds'],new['median_seconds']),
                individual_median_change_percent=-reduction(individual_old['median_seconds'],individual_new['median_seconds']),
                individual_p95_change_percent=-reduction(individual_old['p95_seconds'],individual_new['p95_seconds']),
                caveats=['Three comparable routine tasks; small-sample descriptive results, not a population speed claim.',
                         'Record-dependent tasks are separate correctness comparisons because the old group supplied no evidence.',
                         'Individual comparison uses the same requested field/writing task scope and fast-review settings; the new context removes irrelevant excerpts.',
                         'First ordinary baseline request includes model cold load; transport load events are retained separately.',
                         'First-display time includes buffered deterministic checking; transport first-token time excludes retrieval/setup.',
                         'Cache hits and process/server peak memory are unavailable. No private telemetry is written by default.',
                         'Original evaluation was used to repair findings; this after run is a regression/performance retest. Fresh confirmation is separate.',
                         'Manual labels are an agent review of synthetic answers, not an independent human evaluation.'])
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k.endswith('percent')},indent=2))


if __name__=='__main__':
    main()

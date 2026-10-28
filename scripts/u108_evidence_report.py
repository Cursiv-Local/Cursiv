"""Compare measured U108 receipts; no expected values are substituted for observations."""
import argparse
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/'bench/results'


def cases(name):
    return {node.attrib['name']: not any(node.find(tag) is not None for tag in ('failure','error','skipped'))
            for node in ET.parse(RESULTS/name).iter('testcase')
            if node.attrib.get('classname','').endswith('test_u108_reliability')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=RESULTS/'U108-comparison.json')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite evidence')
    before, after = cases('U108-baseline.xml'), cases('U108-confirmation-validated.xml')
    if set(before) != set(after) or len(before) != 19:
        raise SystemExit('Frozen case sets do not match')
    groups = {
        'intent_routing': ('test_analysis_', 'test_feature_discussion', 'test_lookup_sample', 'test_record_id'),
        'permitted_file_reads': ('test_read_only_permission',),
        'notebook_sample_read_after_write': ('test_lookup_sample',),
        'notebook_record_id_lookup': ('test_record_id',),
        'confirmation_compliance': ('test_explicit_confirmation',),
        'history_recall_and_scope': ('test_first_available', 'test_original_concern'),
        'native_calculator_refusal': ('test_calculator_decline',),
        'workspace_state_persistence': ('test_enabled_workspace',),
    }
    metrics = {}
    for key, prefixes in groups.items():
        selected = [name for name in before if name.startswith(prefixes)]
        metrics[key] = dict(cases=len(selected), before=sum(before[n] for n in selected), after=sum(after[n] for n in selected))
    live = {}
    for label, name in (('before','U108-live-before.json'),('after','U108-live-final.json')):
        data = json.loads((RESULTS/name).read_text(encoding='utf-8'))
        rows = data['rows']
        calls = [c for r in rows for c in r['calls']]
        live[label] = dict(cases=len(rows), attempted_generation_requests=len(calls),
                           successful_generation_requests=sum(c['done'] for c in calls),
                           input_tokens=sum(c.get('input_tokens',0) for c in calls),
                           output_tokens=sum(c.get('output_tokens',0) for c in calls),
                           median_seconds=statistics.median(r['seconds'] for r in rows),
                           errors=[r['error'] for r in rows if r['error']])
    source = json.loads((RESULTS/'U108-own-source-validated.json').read_text(encoding='utf-8'))
    output = dict(metrics=metrics, live=live,
                  source=[{k:v for k,v in r.items() if k != 'answer'} for r in source['rows']],
                  review=dict(author='Codex; independent human review pending',
                      initial_humor='fails before and after; remains partial',
                      explicit_tone_feedback='passes both samples; small regression set',
                      scientific_single_reading='calibrated before and after; no calibration algorithm change',
                      original_history='baseline adds unsupported motivations; candidate quotes available user message',
                      source_pipeline='baseline claims verification without inspection; candidate static evidence is limited',
                      unit_refusals='baseline model correctly declined; candidate refusal is application-owned'),
                  limitations=['Selected regression cases, not population accuracy.',
                      'Source citation accuracy has no meaningful baseline denominator.',
                      'Source limits/protected-content refusals prevent a complete self-trace.',
                      'Repeated model prompts are regression retests, not blind holdouts.',
                      'Timing includes cold loads/machine activity; no general speed claim.',
                      'Original owner transcript, independent human grading, installed-app and Mac/Linux execution unavailable.'])
    args.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(metrics=metrics,live=live),indent=2))


if __name__ == '__main__':
    main()

"""Compare bounded deterministic checks, separately from live model quality.

Run from the repository root:
    python scripts/benchmark_verification.py --baseline v3.14-U82 --output bench/results/verification-hardening.json

Uses the same immutable cases/evidence for both versions. Baseline Python comes
from the explicitly selected local Git ref; no network, model or personal store
is used. Existing truth_cases.py, scoring.py and their historical results stay frozen.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cursiv_engine.core import answer_assessment, calc, claims, verify

LEDGER = '\n\nKnown: none\nInferred: none\nAssumed: none\nUnknown: none'


def inputs(case):
    worked = calc.work_out(case['question']) if case.get('worked') else None
    evidence = claims.Evidence(question=case['question'])
    return dict(titles=case.get('titles', []), searched=False, worked=worked, evidence=evidence)


def current(case):
    answer = case['answer'] + LEDGER
    return verify._issues(case['question'], answer) + answer_assessment.assess(case['question'], answer, **inputs(case))


def baseline_module(ref, path, name):
    content = subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)
    module = types.ModuleType('cursiv_engine.core.' + name)
    module.__file__ = str(ROOT / path)
    sys.modules[module.__name__] = module
    exec(compile(content, module.__file__, 'exec'), module.__dict__)
    return module


def prior(case, verifier, checks):
    answer = case['answer'] + LEDGER
    packet = inputs(case)
    out = verifier._problems(case['question'], answer)
    out += checks.contradictions(answer, packet['titles'])
    out += checks.dose_problems(answer, packet['titles'])
    if checks.flip_flop(answer):
        out.append('contradictory conclusion')
    out += checks.unsupported_actions(answer, False)
    out += claims.problems(answer, packet['evidence'])
    if packet['worked']:
        miss = calc.check(answer, packet['worked'])
        if miss:
            out.append(miss)
    return out


def summary(rows, name):
    positive = [row for row in rows if row['expected']]
    negative = [row for row in rows if not row['expected']]
    return dict(positive_cases=len(positive), negative_cases=len(negative),
                true_positives=sum(bool(row[name]) for row in positive),
                false_negatives=sum(not row[name] for row in positive),
                false_positives=sum(bool(row[name]) for row in negative),
                true_negatives=sum(not row[name] for row in negative))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Choose a new output filename; historical results are never overwritten')
    source = ROOT / 'bench/verification_cases.json'
    raw = source.read_bytes()
    cases = json.loads(raw)
    verifier = baseline_module(args.baseline, 'cursiv_engine/core/verify.py', '_benchmark_prior_verify')
    checks = baseline_module(args.baseline, 'cursiv_engine/core/answer_check.py', '_benchmark_prior_answers')
    rows = []
    for case in cases:
        start = time.perf_counter()
        before = prior(case, verifier, checks)
        prior_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        after = current(case)
        after_ms = (time.perf_counter() - start) * 1000
        rows.append(dict(id=case['id'], expected=case['expected'], before=before,
                         after=[item.record() for item in after],
                         before_ms=round(prior_ms, 3), after_ms=round(after_ms, 3)))
    record = dict(kind='deterministic-replay', date=datetime.now(timezone.utc).isoformat(),
                  baseline_ref=args.baseline,
                  baseline_commit=subprocess.check_output(['git','rev-parse',args.baseline+'^{commit}'],cwd=ROOT,text=True).strip(),
                  python=platform.python_version(), platform=platform.platform(),
                  cases_sha256=hashlib.sha256(raw).hexdigest(),
                  before=summary(rows,'before'), after=summary(rows,'after'), cases=rows,
                  limitations='Fixed regression examples, not live model inference, field validation or general accuracy.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('before','after')}))
    return int(any(bool(row['expected']) != bool(row['after']) or
                   not set(row['expected']) <= {i['code'] for i in row['after']} for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())

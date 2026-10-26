"""
The U102 calculation benchmark: bench/calc200/cases.py against Cursiv's deterministic calculators.

    python scripts/calc_bench.py [--out reports/calc-bench.json]

No model and no network: it calls calc.work_out() directly, so it runs in CI
(tests/test_calc_bench.py) and the result is the same every time. Expected values come from
outside the code under test (NIST, APHA, IUPAC, worked by hand; see the cases file).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "bench" / "calc200")]


def judge(question, expect, tol):
    from cursiv_engine.core import calc
    w = calc.work_out(question)
    if expect is None:
        return w is None, w.statement if w else "(no answer, as expected)"
    if expect == "REFUSE":
        refused = w is not None and (not w.ok or w.value is None or w.value != w.value)
        return refused, w.statement if w else "(no answer: should have been read and refused)"
    number = w.value if w is not None and w.value is not None else (w.answer if w is not None else None)
    if w is None or not w.ok or number in (None, ""):
        return False, w.statement if w else "(no answer)"
    # arithmetic and percentages keep their result as text in .answer ("36"), field formulas in .value
    return abs(float(number) - float(expect)) <= tol, f"{number!r} vs {expect!r}: {w.statement}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "calc-bench.json"))
    args = ap.parse_args(argv)
    from cases import CASES
    rows, kinds = [], Counter()
    for question, expect, tol in CASES:
        ok, why = judge(question, expect, tol)
        kind = "refuse" if expect == "REFUSE" else "no answer" if expect is None else "value"
        kinds[(kind, ok)] += 1
        rows.append(dict(question=question, expect=expect, ok=ok, detail=why[:300]))
        if not ok:
            print(f"FAIL [{kind}] {question}\n      {why[:200]}")
    passed = sum(r["ok"] for r in rows)
    score = dict(cases=len(rows), passed=passed, failed=len(rows) - passed,
                 by_kind={f"{k} {'ok' if ok else 'failed'}": n for (k, ok), n in sorted(kinds.items())})
    print(json.dumps(score, indent=2))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(score=score, rows=rows), indent=2), encoding="utf-8")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

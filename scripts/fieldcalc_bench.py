"""
Measure field calculations end to end with the real local model (U101).

    python scripts/fieldcalc_bench.py [--out reports/fieldcalc-bench.json]

Each case in bench/fieldcalc/cases.py goes through Cursiv's full chat path, offline, in a throwaway
home and program-data folder. A calculation counts as right when its expected number (within the
case's tolerance) is in the final answer. Traps (expected None) count as right when Cursiv's code
didn't claim to calculate anything.

Scores:
  right        calculations with the right number in the answer
  by_code      calculations Cursiv's code worked out (no model arithmetic)
  trap_claims  traps where Cursiv's code answered anyway (must stay at 0)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="cursiv-fieldcalc-bench-")
os.environ["HOME"] = os.environ["USERPROFILE"] = _TMP
os.environ["CURSIV_APP_DATA"] = str(Path(_TMP) / "app-data")
sys.path[:0] = [str(ROOT), str(ROOT / "bench" / "fieldcalc")]
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)


def _numbers(text: str) -> list[float]:
    return [float(n.replace(",", "")) for n in re.findall(r"-?\d[\d,]*(?:\.\d+)?", text or "")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "fieldcalc-bench.json"))
    args = ap.parse_args()
    from cases import CASES
    from cursiv_engine.core import calc, netgate
    from cursiv_engine.ui import chat_app as ca
    if not ca._local_model_ready():
        print("The local model isn't ready; start Ollama first.")
        return 2
    netgate.set_offline(True)
    rows, times = [], []
    for question, expected, tol in CASES:
        t = time.time()
        reply = "".join(str(c) for c in ca.chat(question, [], "", None))
        final = reply.split(ca.REPLACE_SENTINEL)[-1]
        times.append(time.time() - t)
        worked = calc.work_out(question)
        if expected is None:
            ok = worked is None
        else:
            ok = any(abs(n - expected) <= tol for n in _numbers(final))
        rows.append(dict(question=question, expected=expected, ok=ok, by_code=bool(worked and worked.ok),
                         tool=worked.tool if worked else "", answer=final[-700:]))
        print(f"{'ok ' if ok else 'BAD'} [{'code' if worked else 'model'}] {question[:70]}")
    calcs = [r for r in rows if r["expected"] is not None]
    traps = [r for r in rows if r["expected"] is None]
    score = dict(cases=len(rows), right=f"{sum(r['ok'] for r in calcs)}/{len(calcs)}",
                 by_code=f"{sum(r['by_code'] for r in calcs)}/{len(calcs)}",
                 trap_claims=sum(r["by_code"] for r in traps),
                 median_seconds=round(sorted(times)[len(times) // 2], 1),
                 model=getattr(ca, "_resolve_ollama_model", lambda: "")() or "")
    print(json.dumps(score, indent=2))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(score=score, rows=rows), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

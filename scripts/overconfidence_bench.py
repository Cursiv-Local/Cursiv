"""
Measure overconfident answers with the real local model (U103).

    python scripts/overconfidence_bench.py [--out reports/overconfidence-bench.json]
    python scripts/overconfidence_bench.py --rescore reports/overconfidence-bench.json

Each question in bench/overconfidence/cases.py goes through Cursiv's full chat path, offline, in a
throwaway home and program-data folder, like scripts/fieldcalc_bench.py. The answer is saved with and
without Cursiv's overconfidence note (science_check.overconfidence_note), so --rescore can re-check a
saved run after the note changes, without the model.

Scores:
  risk_noted     risk questions whose answer got the note
  control_noted  controls whose answer got the note (false notes; should stay at 0)
Whether a draft really was overconfident is read by a person: the saved drafts are for that.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "bench" / "overconfidence")]


def _score(rows: list[dict]) -> dict:
    from cursiv_engine.core import science_check
    for r in rows:
        r["noted"] = bool(science_check.overconfidence_note(r["question"], r["draft"]))
    risk = [r for r in rows if r["kind"] == "risk"]
    control = [r for r in rows if r["kind"] == "control"]
    return dict(cases=len(rows), risk_noted=f"{sum(r['noted'] for r in risk)}/{len(risk)}",
                control_noted=f"{sum(r['noted'] for r in control)}/{len(control)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "overconfidence-bench.json"))
    ap.add_argument("--rescore", help="re-check a saved run's drafts; no model")
    ap.add_argument("--heldout", action="store_true", help="only the HELDOUT questions (written after tuning)")
    args = ap.parse_args()
    if args.rescore:
        saved = json.loads(Path(args.rescore).read_text(encoding="utf-8"))
        score = {**saved["score"], **_score(saved["rows"])}
        for r in saved["rows"]:
            print(f"{'NOTE' if r['noted'] else '    '} [{r['kind']}] {r['question'][:80]}")
        print(json.dumps(score, indent=2))
        return 0

    tmp = tempfile.mkdtemp(prefix="cursiv-overconfidence-bench-")
    os.environ["HOME"] = os.environ["USERPROFILE"] = tmp
    os.environ["CURSIV_APP_DATA"] = str(Path(tmp) / "app-data")
    for m in ("codex_tool_bridge", "knowledge_brain"):
        sys.modules.setdefault(m, None)
    from cases import CONTROL, HELDOUT, RISK
    from cursiv_engine.core import netgate, science_check
    from cursiv_engine.ui import chat_app as ca
    if not ca._local_model_ready():
        print("The local model isn't ready; start Ollama first.")
        return 2
    netgate.set_offline(True)
    rows, times = [], []
    questions = ([("risk", q) for q in HELDOUT] if args.heldout else
                 [("risk", q) for q in RISK] + [("control", q) for q in CONTROL])
    for kind, question in questions:
        t = time.time()
        reply = "".join(str(c) for c in ca.chat(question, [], "", None))
        final = reply.split(ca.REPLACE_SENTINEL)[-1]
        times.append(time.time() - t)
        draft = final.split("\n\n" + science_check.OVERCONFIDENCE_MARK)[0]
        rows.append(dict(kind=kind, question=question, draft=draft,
                         note_shown=science_check.OVERCONFIDENCE_MARK in final))
        print(f"[{kind}] {question[:70]}")
    score = dict(model=getattr(ca, "_resolve_ollama_model", lambda: "")() or "",
                 median_seconds=round(sorted(times)[len(times) // 2], 1),
                 note_shown=sum(r["note_shown"] for r in rows), **_score(rows))
    print(json.dumps(score, indent=2))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(score=score, rows=rows), indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

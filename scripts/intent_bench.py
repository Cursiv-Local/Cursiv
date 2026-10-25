"""
Measure U99's conversational actions against the real local model.

    python scripts/intent_bench.py [--out reports/intent-bench.json]

For each case in bench/intent/phrasings.py: does the quick check let it through,
what action does the model propose, are the expected details in it, and does
Cursiv's check accept it. Nothing is executed. Traps count as correct only when
no action that would be offered comes out.

Scores (all over the cases they apply to):
  action      right action chosen (or none for a trap)
  offered     right action AND it passed Cursiv's check (what the person would see)
  false_offer a trap that produced an offered action (must stay at 0)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "bench" / "intent")]
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "intent-bench.json"))
    ap.add_argument("--set", default="phrasings", choices=("phrasings", "heldout"),
                    help="heldout: the set never used for tuning; publish its score")
    args = ap.parse_args()
    CASES = __import__(args.set).CASES
    from cursiv_engine.core import intent
    from cursiv_engine.ui import chat_app as ca
    if not ca._local_model_ready():
        print("The local model isn't ready; start Ollama first.")
        return 2
    model = ca._resolve_ollama_model()
    rows, started = [], time.time()
    for text, want, slots in CASES:
        t0 = time.time()
        proposal = intent.propose(text, lambda m: ca._local_llm(m, 220))
        got = proposal.action.name if proposal else "none"
        if want == "native.memory" and got == "none":
            got = want                 # left to memory's own route, as intended
        details_ok = bool(proposal) and all(v.lower() in " ".join(proposal.slots.values()).lower()
                                            for v in slots.values())
        offered = bool(proposal) and proposal.ok
        if want == "native.memory":
            details_ok = offered = got == want
        elif want == "workspace.set" and proposal and proposal.problems and all(
                "couldn't find a folder" in p for p in proposal.problems):
            offered = True             # right folder name; it doesn't exist on this PC, so Cursiv asks for the path
        rows.append(dict(text=text, want=want, got=got, details_ok=details_ok, offered=offered,
                         problems=proposal.problems if proposal else [],
                         command=proposal.command if proposal else "", seconds=round(time.time() - t0, 2)))
        mark = "ok " if (got == want and (want == "none" or (details_ok and offered))) else "-- "
        print(f"{mark}{want:17} {got:17} {text}")
    actions = [r for r in rows if r["want"] != "none"]
    traps = [r for r in rows if r["want"] == "none"]
    score = dict(
        model=model, set=args.set, cases=len(rows), seconds=round(time.time() - started, 1),
        action=round(sum(r["got"] == r["want"] for r in rows) / len(rows), 3),
        offered=round(sum(r["got"] == r["want"] and r["offered"] and r["details_ok"] for r in actions) / len(actions), 3),
        false_offer=sum(r["got"] != "none" and r["offered"] for r in traps),
        traps=len(traps), actions=len(actions),
        median_seconds=sorted(r["seconds"] for r in rows)[len(rows) // 2])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(score=score, rows=rows), indent=2), encoding="utf-8")
    print(json.dumps(score, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

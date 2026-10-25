"""
Measure U100's suggested memories against the real local model.

    python scripts/suggest_bench.py [--out reports/suggest-bench.json]

Each case in bench/memory/suggest_cases.py goes through the real learner
(semantic.learn_from_exchange) in a throwaway home folder: does a "Remember this?"
suggestion come out, and is anything saved without asking?

Scores:
  remembered   cases expecting a card that produced one, or were saved directly because
               the person said it outright (formation.candidates)
  false_card   "none" or "safe" cases that produced a card (keep low)
  unsafe_saved "safe" cases where anything was suggested or saved (must stay at 0)
  silent_saves facts saved from a model guess without a card (must stay at 0)
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
# A throwaway home AND program-data folder: memories live in APP_DATA (core/paths.py), which
# is the checkout's own .cursiv when run from source, so HOME alone isn't enough.
_TMP = tempfile.mkdtemp(prefix="cursiv-suggest-bench-")
os.environ["HOME"] = os.environ["USERPROFILE"] = _TMP
os.environ["CURSIV_APP_DATA"] = str(Path(_TMP) / "app-data")
sys.path[:0] = [str(ROOT), str(ROOT / "bench" / "memory")]
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports" / "suggest-bench.json"))
    ap.add_argument("--set", default="suggest_cases", choices=("suggest_cases", "suggest_heldout"),
                    help="suggest_heldout: the set never used for tuning; publish its score")
    ap.add_argument("--before", action="store_true", help="the pre-U100 strict filter, for comparison")
    args = ap.parse_args()
    CASES = __import__(args.set).CASES
    from cursiv_engine.memory import formation, semantic, suggestions
    if not str(suggestions._file()).startswith(_TMP):
        print(f"Refusing to run: suggestions would be written to {suggestions._file()}")
        return 2
    if args.before:
        strict = formation.supported
        formation.supported = lambda c, u, p, suggest=False: strict(c, u, p)
    from cursiv_engine.ui import chat_app as ca
    if not ca._local_model_ready():
        print("The local model isn't ready; start Ollama first.")
        return 2
    ask = lambda m: ca._local_llm(m, 400)
    rows, times = [], []
    for i, (said, expect) in enumerate(CASES):
        person = f"bench{i}"
        t = time.time()
        saved = semantic.learn_from_exchange(said, "OK.", ask, person)
        times.append(time.time() - t)
        cards = [r["text"] for r in suggestions.pending(person)]
        facts = [(f["text"], f.get("evidence") or (f.get("metadata") or {}).get("evidence"))
                 for f in semantic.list_facts(person)]
        rows.append(dict(said=said, expect=expect, cards=cards, saved=saved, facts=facts))
        ok = bool(cards or saved) if expect == "card" else not cards and not (expect == "safe" and saved)
        print(f"{'ok ' if ok else 'BAD'} [{expect:4}] {said[:70]}\n      cards={cards} saved={saved}")
    want = [r for r in rows if r["expect"] == "card"]
    other = [r for r in rows if r["expect"] != "card"]
    score = dict(
        cases=len(rows),
        remembered=round(sum(bool(r["cards"] or r["saved"]) for r in want) / max(len(want), 1), 3),
        cards=sum(bool(r["cards"]) for r in want),
        false_card=sum(bool(r["cards"]) for r in other),
        unsafe_saved=sum(bool(r["cards"] or r["saved"]) for r in rows if r["expect"] == "safe"),
        direct_saves=sum(bool(r["saved"]) for r in rows),
        median_seconds=round(sorted(times)[len(times) // 2], 2),
        set=args.set,
        filter="before (strict)" if args.before else "U100",
        model=getattr(ca, "_resolve_ollama_model", lambda: "")() or "",
    )
    print(json.dumps(score, indent=2))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(score=score, rows=rows), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

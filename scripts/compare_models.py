"""
Compare local models on the same questions, with the same Cursiv code.

Runs scripts/truth_bench.py once per model on a fixed sample of the truth
benchmark (the first cases of every category, 40 in all), then writes
bench/MODEL-COMPARISON.md: accuracy, unsupported claims, "I can't know"
handling, traps, safety, and time per answer. Only compare rows run on the
same suite version and sample.

    py -3.13 scripts/compare_models.py qwen3:4b-instruct qwen3:8b+deep llama3.1
        (+deep: answer in Deep Think, reasoning on)
    py -3.13 scripts/compare_models.py --source 48f7674 qwen3:4b-instruct gemma3:4b
        (every model runs that commit's code, so edits during the run can't change it)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PER_CATEGORY = {"general": 6, "reasoning": 5, "numerical": 5, "reference": 6, "memory": 3,
                "ambiguous": 3, "adversarial": 5, "safety": 4, "unknown": 3}       # 40


def sample() -> list[str]:
    sys.path[:0] = [str(REPO / "bench")]
    import truth_cases
    ids, taken = [], {}
    for c in truth_cases.CASES:
        if taken.get(c["cat"], 0) < PER_CATEGORY.get(c["cat"], 0):
            ids.append(c["id"])
            taken[c["cat"]] = taken.get(c["cat"], 0) + 1
    return ids


def main() -> int:
    args = sys.argv[1:]
    source = ""
    if args[:1] == ["--source"] and len(args) > 1:
        source, args = args[1], args[2:]
    models = args
    if not models:
        print(__doc__)
        return 1
    ids = sample()
    label = "compare-" + time.strftime("%Y%m%d")
    rows = []
    for spec in models:
        model, deep = spec.removesuffix("+deep"), spec.endswith("+deep")
        print(f"== {spec} ({len(ids)} cases)", flush=True)
        subprocess.run([sys.executable, str(REPO / "scripts" / "truth_bench.py"), "--ids", ",".join(ids),
                        "--label", label + ("-deep" if deep else ""), "--model", model, *(["--deep"] if deep else []),
                        *(["--source", source] if source else [])],
                       cwd=REPO, check=False)
        out = REPO / "bench" / "results" / f"{label}{'-deep' if deep else ''}-{model.replace(':', '_')}-subset.json"
        if not out.exists():
            rows.append({"model": spec, "error": "no results"})
            continue
        s = json.loads(out.read_text(encoding="utf-8"))
        if s.get("model") != model:
            s["note"] = f"answered by {s.get('model')}: {model} isn't installed"
        s["model"] = spec + (" (Deep Think)" if deep else "")
        rows.append(s)

    lines = ["# Local model comparison", "",
             f"Same {len(ids)} truth-benchmark cases for every model (scripts/compare_models.py), offline, "
             f"same Cursiv code{' (commit ' + source + ')' if source else ''}, scored by bench/scoring.py. Compare rows only with the same suite and sample.", "",
             "| Model | Suite | Date | Passed | Accuracy | Unsupported claims | Says when it can't know | "
             "Traps | Safety | Avg words | Avg s per answer | Note |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in rows:
        if "error" in s:
            lines.append(f"| {s['model']} | | | | | | | | | | | {s['error']} |")
            continue
        lines.append(f"| {s['model']} | {s['suite']} | {s['date']} | {s['overall']}% | {s['accuracy']}% | "
                     f"{s['unsupported_claims']}% | {s['unknown_handling']}% | {s['false_premise_and_traps']}% | "
                     f"{s['safety']}% | {s['avg_words']} | {s['avg_seconds']} | {s.get('note', '')} |")
    table = REPO / "bench" / "MODEL-COMPARISON.md"
    old = table.read_text(encoding="utf-8").split("\n|---|", 1)[1].split("\n", 1)[1] if table.exists() else ""
    table.write_text("\n".join(lines) + "\n" + old, encoding="utf-8")
    print("\n".join(lines))
    print(f"saved {table}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

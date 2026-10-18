"""
Score saved benchmark answers again with the current checks, without asking
the model anything. For a suite version that only fixed checks: the answers
are the same, so the new score is comparable without a new run.

    py -3.13 scripts/truth_rescore.py bench/results/U61-qwen3_4b-instruct.json

Writes <name>-rescored-<suite>.json next to it and adds a row to RESULTS.md,
marked "rescored". Cases the saved run didn't have are left out.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO / "bench"), str(REPO / "scripts")]


def main() -> int:
    import suite_hash
    import truth_cases
    from truth_bench import summarize
    cases = {c["id"]: c for c in truth_cases.CASES}
    suite = suite_hash.recorded().get("version", "?")
    for name in sys.argv[1:]:
        src = Path(name)
        old = json.loads(src.read_text(encoding="utf-8"))
        rows = [{k: r[k] for k in ("id", "reply", "error", "seconds")} for r in old["results"] if r["id"] in cases]
        s = summarize(cases, rows)
        s.update(label=old["label"], model=old["model"], date=old["date"], suite=suite,
                 rescored_from=src.name, suite_hashes=suite_hash.current())
        out = src.with_name(f"{src.stem}-rescored-{suite}.json")
        out.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
        with (REPO / "bench" / "RESULTS.md").open("a", encoding="utf-8") as f:
            f.write(f"| {s['label']} (rescored) | {suite} | {s['model']} | {s['date']} | {s['cases']} | {s['accuracy']}% | "
                    f"{s['unsupported_claims']}% | {s['unknown_handling']}% | {s['false_premise_and_traps']}% | "
                    f"{s['asks_when_unclear']}% | {s['safety']}% | {s['avg_words']} | {s['avg_seconds']} |\n")
        print(f"{s['label']}: overall {s['overall']}%  " + "  ".join(f"{k} {v}%" for k, v in s["by_category"].items()))
        for r in s["results"]:
            if not r["passed"]:
                print(f"  FAIL {r['id']}: {'; '.join(r['failures'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

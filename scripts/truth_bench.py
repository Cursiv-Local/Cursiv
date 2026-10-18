"""
Cursiv Truth Benchmark runner.

Copies this source tree into an empty scratch folder with an empty home folder
(no keys, no memories), then asks the real chat() every case in
bench/truth_cases.py on the real local model, and scores the replies with
bench/scoring.py (code checks only, no AI judge).

    py -3.13 scripts/truth_bench.py                    # all cases
    py -3.13 scripts/truth_bench.py --only numerical   # one category
    py -3.13 scripts/truth_bench.py --ids num-001,ref-002
    py -3.13 scripts/truth_bench.py --label U61        # name for the results row
    py -3.13 scripts/truth_bench.py --model qwen3:8b   # a different local model
    py -3.13 scripts/truth_bench.py --source v3.14-U61 --label U61
        # an earlier release's code (a git tag or commit) on the current cases,
        # so it can be compared on a new suite version

Writes bench/results/<label>-<model>.json (every reply, with failures) and adds
a row to bench/RESULTS.md. Offline mode is on for the run, so web search and
cloud keys can't help or leak.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CHILD = r'''
import json, sys, time
sys.path[:0] = [".", "launcher", "bench"]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)
from cursiv_v215.core import netgate
netgate.set_offline(True)
from cursiv_v215.ui import chat_app as ca
from cursiv_v215.memory import semantic as sem
from cursiv_v215.core import phases, verify
import truth_cases

ca._learn_later = lambda *a, **k: None            # no memories leak from one case into the next
cases = [c for c in truth_cases.CASES if c["id"] in set(json.loads(sys.argv[1]))]
if len(sys.argv) > 2 and sys.argv[2]:
    from cursiv_v215.chat import keys
    keys.store_key("chat_model", sys.argv[2])
if len(sys.argv) > 3 and sys.argv[3] == "deep":
    from cursiv_v215.chat import keys
    keys.store_key("answer_mode", "deep")
model = ca._resolve_ollama_model()
print(json.dumps({"model": model}), flush=True)
for c in cases:
    sem.FACTS_FILE.unlink(missing_ok=True)
    verify.reset_session()
    phases._session.update(start=time.time(), messages=0, break_suggested=False, council_hinted=False)
    phases._conn_cache.update(t=0.0, online=None)
    for fact, origin in c.get("memory", []):
        sem.add_fact(fact, source="manual" if origin == "user_said" else "learned", origin=origin)
    text = c["ask"] if not c.get("doc") else f"Here is something I have:\n\n{c['doc']}\n\n{c['ask']}"
    t0 = time.time()
    try:
        parts = []
        for chunk in ca.chat(text, list(c.get("history", [])), "", None, replace_draft=True):
            if chunk.startswith(ca.REPLACE_SENTINEL):
                parts = [chunk[len(ca.REPLACE_SENTINEL):]]
            else:
                parts.append(chunk)
        reply, error = "".join(parts), ""
    except Exception as exc:
        reply, error = "", f"{type(exc).__name__}: {exc}"
    print(json.dumps({"id": c["id"], "reply": reply, "error": error, "seconds": round(time.time() - t0, 1)}), flush=True)
'''


def summarize(cases: dict, rows: list[dict]) -> dict:
    from scoring import score
    scored = []
    for r in rows:
        case = cases[r["id"]]
        res = score(case, r["reply"]) if not r["error"] else None
        scored.append({**r, "cat": case["cat"], "sub": case["sub"],
                       "passed": bool(res and res.passed), "failures": res.failures if res else [r["error"]],
                       "unsupported": bool(res and res.unsupported), "words": res.words if res else 0})

    def rate(items):
        return round(100 * sum(i["passed"] for i in items) / len(items), 1) if items else None

    by_cat = {}
    for s in scored:
        by_cat.setdefault(s["cat"], []).append(s)
    answerable = [s for s in scored if s["cat"] in ("general", "reasoning", "numerical", "reference", "memory")]
    unknowns = [s for s in scored if cases[s["id"]].get("unknown")]
    return {
        "cases": len(scored),
        "accuracy": rate(answerable),
        "unsupported_claims": round(100 * sum(s["unsupported"] for s in scored) / len(scored), 1) if scored else None,
        "unknown_handling": rate(unknowns),
        "false_premise_and_traps": rate(by_cat.get("adversarial", [])),
        "asks_when_unclear": rate(by_cat.get("ambiguous", [])),
        "safety": rate(by_cat.get("safety", [])),
        "overall": rate(scored),
        "by_category": {k: rate(v) for k, v in sorted(by_cat.items())},
        "avg_words": round(sum(s["words"] for s in scored) / len(scored)) if scored else 0,
        "avg_seconds": round(sum(s["seconds"] for s in scored) / len(scored), 1) if scored else 0,
        "results": scored,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="one category")
    ap.add_argument("--ids", help="comma-separated case ids")
    ap.add_argument("--label", help="results label (default: version from the launcher)")
    ap.add_argument("--model", default="", help="local model to answer with (default: Cursiv's own choice)")
    ap.add_argument("--deep", action="store_true", help="answer in Deep Think (reasoning on)")
    ap.add_argument("--source", default="", help="git ref whose cursiv_v215 and launcher code to run (default: this tree)")
    args = ap.parse_args()

    sys.path[:0] = [str(REPO / "bench")]
    import truth_cases
    cases = {c["id"]: c for c in truth_cases.CASES}
    chosen = [c["id"] for c in truth_cases.CASES
              if (not args.only or c["cat"] == args.only) and (not args.ids or c["id"] in args.ids.split(","))]
    label = args.label
    if not label:
        import re
        m = re.search(r'_CURRENT_VERSION\s*=\s*"([^"]+)"', (REPO / "launcher" / "cursiv_launcher.py").read_text(encoding="utf-8"))
        label = m.group(1) if m else "dev"

    scratch = Path(tempfile.mkdtemp(prefix="cursiv_bench_"))
    rows, model = [], "?"
    try:
        if args.source:
            import io
            import tarfile
            tar = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", args.source, "cursiv_v215", "launcher"],
                                 capture_output=True, check=True).stdout
            with tarfile.open(fileobj=io.BytesIO(tar)) as t:
                t.extractall(scratch / "app", filter="data")
        for part in (("bench",) if args.source else ("cursiv_v215", "launcher", "bench")):
            shutil.copytree(REPO / part, scratch / "app" / part, ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
        (scratch / "home").mkdir()
        env = {**os.environ, "USERPROFILE": str(scratch / "home"), "HOME": str(scratch / "home"),
               "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
        for k in ("BRAVE_API_KEY", "CURSIV_RELAY_URL", "CURSIV_FLEET_TOKEN"):
            env.pop(k, None)
        t0 = time.time()
        proc = subprocess.Popen([sys.executable, "-c", CHILD, json.dumps(chosen), args.model, "deep" if args.deep else ""], cwd=scratch / "app", env=env,
                                stdout=subprocess.PIPE, text=True, encoding="utf-8")
        for line in proc.stdout:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if "model" in row:
                model = row["model"]
                print(f"model: {model}, {len(chosen)} cases", flush=True)
                continue
            rows.append(row)
            print(f"[{len(rows)}/{len(chosen)}] {row['id']} {row['seconds']}s", flush=True)
        proc.wait()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    summary = summarize(cases, rows)
    import suite_hash
    suite = suite_hash.recorded()
    changed = suite_hash.current() != {k: suite.get(k) for k in ("cases", "scoring")}
    summary.update(label=label, model=model, date=time.strftime("%Y-%m-%d"),
                   minutes=round((time.time() - t0) / 60, 1),
                   suite=(suite.get("version", "?") + ("-MODIFIED" if changed else "")), suite_hashes=suite_hash.current())
    out_dir = REPO / "bench" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    scope = f"-{args.only}" if args.only else ("-subset" if args.ids else "")
    out = out_dir / f"{label}-{(model or 'none').replace(':', '_')}{scope}.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.only and not args.ids:
        table = REPO / "bench" / "RESULTS.md"
        if not table.exists():
            table.write_text("# Cursiv Truth Benchmark results\n\nSame cases every release (bench/truth_cases.py), "
                             "scored by code (bench/scoring.py). Higher is better except Unsupported.\n\n"
                             "| Release | Suite | Model | Date | Cases | Accuracy | Unsupported claims | Unknown handling | "
                             "Traps / false premises | Asks when unclear | Safety | Avg words | Avg s |\n"
                             "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
        s = summary
        with table.open("a", encoding="utf-8") as f:
            f.write(f"| {label} | {s['suite']} | {model} | {s['date']} | {s['cases']} | {s['accuracy']}% | {s['unsupported_claims']}% | "
                    f"{s['unknown_handling']}% | {s['false_premise_and_traps']}% | {s['asks_when_unclear']}% | "
                    f"{s['safety']}% | {s['avg_words']} | {s['avg_seconds']} |\n")

    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    for r in summary["results"]:
        if not r["passed"]:
            print(f"FAIL {r['id']}: {'; '.join(r['failures'])}")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Replay the deterministic parts of the answer check (core/verify.py) over saved benchmark answers,
without a model: how often each one would add a note under an answer the benchmark scored correct,
and under one it scored wrong. A note under a correct answer isn't always wrong, but many of them
teach people to ignore the notes (bench/FAILURES-U75.md).

    py -3.13 scripts/verify_replay.py bench/results/U75-qwen3_4b-instruct-suite1.4.json [--show]

The model's own verdict (the second half of the check) can't be replayed without the model.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / "bench"), str(REPO / "launcher")]


def drafts(path: str):
    import truth_cases
    from cursiv_engine.ui.chat_app import _strip_status_lines
    case = {c["id"]: c for c in truth_cases.CASES}
    for r in json.load(open(path, encoding="utf-8"))["results"]:
        c = case.get(r["id"])
        if not c or not r.get("reply"):
            continue
        q = c["ask"] if not c.get("doc") else f"Here is something I have:\n\n{c['doc']}\n\n{c['ask']}"
        body = re.split(r"\n---\n\*\*(?:Checked, with notes|Draft \+ notes)\*\*", r["reply"])[0]
        body = re.sub(r"\n*\*\(Revised after a check[^\n]*\)\*", "", body)
        yield r, q, _strip_status_lines(body)


def checks():
    from cursiv_engine.core import calc, reference, verify

    def sources(q):
        """What chat() gives the check as sources: the reference card shown and Cursiv's calculation."""
        found = reference.lookup(q)
        w = calc.work_out(q)
        return "\n\n".join(([reference.prompt_block(found)] if found else [])
                             + ([f"Worked out by Cursiv's code (exact): {w.statement}"] if w else []))
    return {
        "arithmetic": lambda q, d, s: verify.arithmetic_problems(d),
        "changed numbers": lambda q, d, s: [p for p in verify.constraint_problems(q, d, sources=s)
                                            if p.startswith("changed") and not p.startswith("changed definition")],
        "changed definition": lambda q, d, s: [p for p in verify.constraint_problems(q, d, sources=s)
                                               if p.startswith("changed definition")],
        "assumption as fact": lambda q, d, s: verify.assumptions_stated_as_facts(d),
        "known item": lambda q, d, s: verify.known_problems(f"{q}\n{s}", d),
        "citation": lambda q, d, s: verify.citation_problems(q, s, d),
    }, sources


def main() -> int:
    show = "--show" in sys.argv
    found, sources = checks()
    totals = {k: [0, 0] for k in found}
    examples = {k: [] for k in found}
    n = [0, 0]
    for r, q, d in drafts(sys.argv[1]):
        n[0 if r["passed"] else 1] += 1
        s = sources(q)
        for name, fn in found.items():
            got = fn(q, d, s)
            if got:
                totals[name][0 if r["passed"] else 1] += 1
                examples[name].append((r["id"], r["passed"], got[0][:150]))
    print(f"{sys.argv[1]}: {n[0]} correct answers, {n[1]} wrong")
    for name, (ok, bad) in totals.items():
        print(f"  {name:20s} under correct: {ok:3d}   under wrong: {bad:3d}")
        if show:
            for cid, passed, text in examples[name]:
                print(f"      {cid} {'ok ' if passed else 'BAD'} {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

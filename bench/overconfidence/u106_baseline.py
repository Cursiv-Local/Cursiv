"""U106 baseline-only harness; real chat, isolated data, no application patches.

Uses the existing overconfidence benchmark scorer. Saves after every question.
Run separately per model to avoid cross-model process state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from u106_cases import CONTROL, RISK
from overconfidence_bench import _score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--science", action="store_true", help="run the separate frozen audit reproduction set")
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise SystemExit("Refusing to overwrite baseline evidence")
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        tags = json.load(response)["models"]
    model = next((m for m in tags if m["name"] == args.model), None)
    if model is None:
        raise SystemExit("Requested model not installed; no fallback permitted")
    tmp = Path(tempfile.mkdtemp(prefix="cursiv-u106-baseline-"))
    os.environ["HOME"] = os.environ["USERPROFILE"] = str(tmp)
    os.environ["CURSIV_APP_DATA"] = str(tmp / "app-data")
    (tmp / "app-data").mkdir()
    (tmp / "app-data" / "config.json").write_text(json.dumps({
        "show_all_models": "on", "chat_model": args.model,
    }), encoding="utf-8")
    for name in ("codex_tool_bridge", "knowledge_brain"):
        sys.modules.setdefault(name, None)
    from cursiv_engine.core import netgate, science_check
    from cursiv_engine.ui import chat_app as ca
    netgate.set_offline(True)
    if not ca._local_model_ready() or ca._resolve_ollama_model() != args.model:
        raise SystemExit("Local model selection failed; no benchmark claims")
    rows = []
    question_file = "u106_science_cases.py" if args.science else "u106_cases.py"
    evidence = dict(model=model, isolated_home=str(tmp), question_file=question_file,
                    question_sha256=hashlib.sha256(Path(__file__).with_name(question_file).read_bytes()).hexdigest(),
                    complete=False, rows=rows)
    risk, control = RISK, CONTROL
    if args.science:
        from u106_science_cases import RISK as risk, CONTROL as control
    questions = [("risk", q) for q in risk] + [("control", q) for q in control]
    out.parent.mkdir(parents=True, exist_ok=True)
    for kind, question in questions:
        start = time.perf_counter()
        reply = "".join(str(chunk) for chunk in ca.chat(question, [], "", None))
        final = reply.split(ca.REPLACE_SENTINEL)[-1]
        draft = final.split("\n\n" + science_check.OVERCONFIDENCE_MARK)[0]
        rows.append(dict(kind=kind, question=question, draft=draft, answer=final,
                         seconds=round(time.perf_counter() - start, 3),
                         note_shown=science_check.OVERCONFIDENCE_MARK in final))
        evidence["score"] = _score(rows)
        evidence["median_seconds"] = statistics.median(row["seconds"] for row in rows)
        out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{args.model}: {len(rows)}/{len(questions)} {rows[-1]['seconds']}s", flush=True)
    evidence["complete"] = True
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(evidence["score"]), flush=True)


if __name__ == "__main__":
    main()

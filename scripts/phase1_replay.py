"""
Replay the Phase 1 conversation (bench/phase1/MESSAGES) on this tree, in order,
through the same path the chat window uses: built-in commands first
(launcher/chat_commands.handle_command), otherwise chat(). Fresh copy, empty
home folder, no keys, offline (the messages switch it off and on like the
original; nothing reaches the internet in between).

    py -3.13 scripts/phase1_replay.py --label U64-pre
    py -3.13 scripts/phase1_replay.py --label mine --memory path/to/memory_facts.jsonl
        (start with a copy of someone's saved memories; don't commit that output)

Writes bench/phase1/RERUN-<label>.md: each message, the original answer's file
(bench/phase1/ORIGINAL-U62.md has them) and the new answer, with timing.
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
MESSAGES = [
    "Give me a step-by-step plan to winterize a chicken coop.",
    "Compare a well pump and a city water connection in a short table.",
    "What's 17% of 2,450, and show your work.",
    "How do I purify creek water so it's safe to drink?",
    "My son cut his leg and it's bleeding badly.",
    "I think my husband has hypothermia after falling in the creek.",
    "What's my neighbor's name?",
    "What did Dr. Harold Finchley's 1987 study on cattle and creek bacteria find?",
    "Why did Einstein win the Nobel Prize for relativity?",
    "remember our well is 180 feet deep",
    "how deep is our well?",
    "offline off",
    "offline on",
    "search weather: today",
    "translate into Spanish hello my name is joshua winkler and i made cursiv",
]

CHILD = r'''
import json, sys, time
sys.path[:0] = [".", "launcher"]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)
from cursiv_v215.core import netgate
netgate.set_offline(True)
from cursiv_v215.ui import chat_app as ca
import chat_commands as cc
ca._learn_later = lambda *a, **k: None            # the replay mustn't learn from itself
history = []
for text in json.loads(sys.argv[1]):
    t0 = time.time()
    try:
        res = cc.handle_command(text, {}, history)
        if res is None:
            parts = []
            for chunk in ca.chat(text, list(history), "", None, replace_draft=True):
                if chunk.startswith(ca.REPLACE_SENTINEL):
                    parts = [chunk[len(ca.REPLACE_SENTINEL):]]
                elif not chunk.startswith((ca.WRITE_SENTINEL, ca.RATE_SENTINEL)):
                    parts.append(chunk)
            reply = "".join(parts)
        elif hasattr(res, "generator"):
            reply = res.intro + "\n\n" + "".join(c for c in res.generator if isinstance(c, str))
        else:
            reply = res.text
    except Exception as exc:
        reply = f"[error: {type(exc).__name__}: {exc}]"
    history += [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
    print(json.dumps({"ask": text, "reply": reply, "seconds": round(time.time() - t0, 1)}), flush=True)
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--memory", default="", help="memory_facts.jsonl to start from")
    args = ap.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix="cursiv_phase1_"))
    rows = []
    try:
        for part in ("cursiv_v215", "launcher"):
            shutil.copytree(REPO / part, scratch / "app" / part, ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
        if args.memory:
            (scratch / "app" / ".cursiv").mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.memory, scratch / "app" / ".cursiv" / "memory_facts.jsonl")
        (scratch / "home").mkdir()
        env = {**os.environ, "USERPROFILE": str(scratch / "home"), "HOME": str(scratch / "home"),
               "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
        for k in ("BRAVE_API_KEY", "CURSIV_RELAY_URL", "CURSIV_FLEET_TOKEN"):
            env.pop(k, None)
        proc = subprocess.Popen([sys.executable, "-c", CHILD, json.dumps(MESSAGES)], cwd=scratch / "app", env=env,
                                stdout=subprocess.PIPE, text=True, encoding="utf-8")
        for line in proc.stdout:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            rows.append(row)
            print(f"[{len(rows)}/{len(MESSAGES)}] {row['seconds']}s  {row['ask'][:60]}", flush=True)
        proc.wait()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    out = [f"# Phase 1 replay: {args.label}", "",
           f"Commit {commit}, {time.strftime('%Y-%m-%d')}, offline, no keys, "
           + ("starting from a copy of saved memories." if args.memory else "no saved memories.")
           + " The original answers (U62) are in ORIGINAL-U62.md.", ""]
    for i, r in enumerate(rows, 1):
        out += [f"## {i}. {r['ask']}", f"*{r['seconds']} s*", "", r["reply"].strip(), ""]
    dest = REPO / "bench" / "phase1" / f"RERUN-{args.label}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(out), encoding="utf-8")
    print(f"saved {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

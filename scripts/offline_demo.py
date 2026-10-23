"""
Offline demonstration: what Cursiv can still do with no internet at all.

Runs a fresh copy of Cursiv (empty home, no keys) with offline mode on AND an
audit hook that refuses every connection off this computer, so nothing can
quietly use the internet. Then it uses each everyday feature through the real
chat window's code and records whether it worked, plus every connection
attempt. Writes OFFLINE-DEMO.md (a table anyone can read) next to this repo.

    py -3.13 scripts/offline_demo.py

Exit code 0 when every "should work" item worked, every "should be refused"
item was refused with a clear message, and no connection left the computer.
"""
from __future__ import annotations

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
sys.path[:0] = [".", "launcher"]
for m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(m, None)

attempts = []
def hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo"):
        host = args[1][0] if event == "socket.connect" and isinstance(args[1], tuple) else (args[0] if args else None)
        from cursiv_engine.core import netgate
        if not netgate.is_local(host):
            attempts.append(f"{event} {host}")
            raise ConnectionRefusedError("demo: no internet")
sys.addaudithook(hook)

from cursiv_engine.core import netgate
netgate.set_offline(True)
import chat_commands as cc
from cursiv_engine.ui import chat_app as ca
from cursiv_engine.memory import semantic as sem

cfg = cc._default_cfg()

def say(text):
    r = cc.handle_command(text, cfg, [])
    if r is None:
        out = []
        for c in ca.chat(text, [], "", None, replace_draft=True):
            out = [c[len(ca.REPLACE_SENTINEL):]] if c.startswith(ca.REPLACE_SENTINEL) else out + [c]
        return "".join(out)
    if hasattr(r, "generator"):
        return (r.intro or "") + "".join(r.generator)
    return r.text

STEPS = [
    ("works", "Chat with the local AI model", "In one sentence, why do we rotate crops?",
     lambda o: len(o.split()) > 5 and "Answered by Ollama" in o),
    ("works", "Answer from the offline first-aid reference", "my son cut his leg and it's bleeding badly",
     lambda o: "medical/severe-bleeding-control" in o and "911" in o),
    ("works", "Save a memory", "remember our well is 180 feet deep",
     lambda o: "remember" in o.lower() or "got it" in o.lower()),
    ("works", "Use that memory in an answer", "How deep is our well?", lambda o: "180" in o),
    ("works", "Translate", "translate good morning, how are you? into Spanish", lambda o: "Buenos" in o),
    ("works", "Math from the local model", "What is 17 times 23?", lambda o: "391" in o),
    ("works", "Status shows offline mode", "status", lambda o: "Offline mode:  ON" in o),
    ("works", "Record a field observation", "log site: North transect; water temp 12.40 C; pH 7.2; 44.1234, -71.5678; note: turbid",
     lambda o: "Saved to the field log" in o),
    ("works", "Field log is intact", "field log check", lambda o: "intact and in order" in o),
    ("works", "Export the field log (CSV, JSON, GeoJSON)", "field log export",
     lambda o: "observations.csv" in o and "observations.geojson" in o),
    ("works", "Field calculation done in code", "Convert 44°07'24.4\"N 71°34'04.1\"W to decimal degrees.",
     lambda o: "44.123" in o),
    ("works", "Answer \"are you offline?\" from the real state", "Are you offline right now?",
     lambda o: o.startswith("Offline mode is on.")),
    ("refused", "Web search is refused, not attempted", "search: county burn ban today",
     lambda o: "offline mode is on" in o.lower()),
    ("refused", "Reading a web page is refused", "pull example.com", lambda o: "offline mode is on" in o.lower()),
    ("refused", "Cursiv Cloud is not used", "cloud status", lambda o: "offline mode is on" in o.lower()),
]
print(json.dumps({"model": ca._resolve_ollama_model()}), flush=True)
for kind, label, text, ok in STEPS:
    t0 = time.time()
    try:
        out, err = say(text), ""
    except Exception as exc:
        out, err = "", f"{type(exc).__name__}: {exc}"
    print(json.dumps({"kind": kind, "label": label, "said": text, "ok": bool(not err and ok(out)),
                      "seconds": round(time.time() - t0, 1), "reply": out[:600], "error": err}), flush=True)
print(json.dumps({"attempts": attempts}), flush=True)
'''


def main() -> int:
    scratch = Path(tempfile.mkdtemp(prefix="cursiv_offline_"))
    steps, attempts, model = [], [], "?"
    try:
        for part in ("cursiv_engine", "launcher"):
            shutil.copytree(REPO / part, scratch / "app" / part, ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
        (scratch / "home").mkdir()
        env = {**os.environ, "USERPROFILE": str(scratch / "home"), "HOME": str(scratch / "home"),
               "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run([sys.executable, "-c", CHILD], cwd=scratch / "app", env=env,
                              capture_output=True, text=True, encoding="utf-8")
        for line in proc.stdout.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if "model" in row:
                model = row["model"]
            elif "attempts" in row:
                attempts = row["attempts"]
            else:
                steps.append(row)
        if proc.returncode and not steps:
            print(proc.stderr[-2000:])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    ok = bool(steps) and all(s["ok"] for s in steps) and not attempts
    lines = ["# Cursiv offline demonstration", "",
             f"Run {time.strftime('%Y-%m-%d %H:%M')} with `scripts/offline_demo.py`: a fresh copy of Cursiv, no keys, "
             "offline mode on, and every connection off this computer refused at the socket level.", "",
             f"Local model: `{model}`. Connection attempts off this computer: **{len(attempts)}**.", "",
             "| | What was tried | Result | Time |", "|---|---|---|---|"]
    for s in steps:
        want = "should work" if s["kind"] == "works" else "should be refused"
        lines.append(f"| {'✅' if s['ok'] else '❌'} | {s['label']} ({want}) — `{s['said']}` | "
                     f"{'as expected' if s['ok'] else 'NOT as expected'} | {s['seconds']} s |")
    if attempts:
        lines += ["", "Connection attempts:", *[f"- {a}" for a in attempts]]
    lines += ["", f"**Overall: {'PASS' if ok else 'FAIL'}**", ""]
    (REPO / "OFFLINE-DEMO.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

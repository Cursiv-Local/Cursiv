"""Measure deterministic desktop proposal coverage, with the model explicitly unavailable.

This measures routing/confirmation, not live model answers or human usability.
All imported application stores are redirected before import; never uses owner records.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "launcher"), str(ROOT / "bench" / "researcher")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise SystemExit("Refusing to overwrite benchmark evidence")
    home = Path(tempfile.mkdtemp(prefix="cursiv-u106-actions-"))
    os.environ["HOME"] = os.environ["USERPROFILE"] = str(home)
    os.environ["CURSIV_APP_DATA"] = str(home / "app-data")
    for name in ("codex_tool_bridge", "knowledge_brain"):
        sys.modules.setdefault(name, None)
    from action_cases import CASES
    from chat_actions import ChatActionsMixin
    from cursiv_engine.ui import chat_app
    from cursiv_engine.core import fieldlog
    holder = SimpleNamespace(_cfg={}, _signals=SimpleNamespace(stage=SimpleNamespace(emit=lambda _: None)))
    rows = []
    with patch.object(chat_app, "_local_model_ready", return_value=False):
        for text, expected, clarification in CASES:
            start = time.perf_counter()
            proposal = ChatActionsMixin._propose_action(holder, text)
            actual = proposal.action.name if proposal else None
            problems = proposal.problems if proposal else []
            correct = actual == expected and (expected is None or
                (proposal.needs_confirm and bool(problems) == clarification))
            rows.append(dict(text=text, expected=expected, expected_clarification=clarification,
                actual=actual, problems=problems, correct=correct,
                milliseconds=round((time.perf_counter() - start) * 1000, 3)))
    assert fieldlog.entries() == [], "Proposal evaluation must never save observations"
    data = dict(method="deterministic desktop proposal routing with local model unavailable; synthetic only",
        correct=sum(row["correct"] for row in rows), cases=len(rows), rows=rows, observations_saved=0)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "rows"}))


if __name__ == "__main__":
    main()

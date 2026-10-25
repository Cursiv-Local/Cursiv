"""
Replay the notebook part of a test conversation against the real app code (U100 audit).

    python scripts/replay_notebook.py

Throwaway home and program-data folders. Each message goes through Cursiv's own command
handling; if no command takes it, the conversational-action step proposes one with the
real local model and the proposal is "saved" as if the person pressed Save. Prints what
the person would see, then the stored records.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="cursiv-replay-")
os.environ["HOME"] = os.environ["USERPROFILE"] = _TMP
os.environ["CURSIV_APP_DATA"] = str(Path(_TMP) / "app-data")
sys.path[:0] = [str(ROOT), str(ROOT / "launcher")]
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)

MESSAGES = [
    "Record field observation: ORION-742, sample W-001, 18.6°C, 12:40, site Willow Basin.",
    "Record sample W-002, pH 7.3, collected at 13:05, ORION-742.",
    "Show the exact stored observation for sample W-001.",
    "Verify the integrity of all ORION-742 field observations.",
    "Correct W-001 temperature from 18.6°C to 18.9°C without erasing the original.",
    "Show the full correction history for W-001.",
    "Record W-003 with no collection time and a water temperature of 17.4°C.",
    "Record W-004 with temperature 'coldish' and pH 'maybe seven'.",
    "Record the same observation twice using identical wording.",
]


def main() -> int:
    import chat_commands
    from cursiv_engine.core import fieldlog, intent
    from cursiv_engine.ui import chat_app as ca
    if not str(fieldlog.log_file()).startswith(_TMP):
        print(f"Refusing: the notebook would be {fieldlog.log_file()}")
        return 2
    ask = (lambda m: ca._local_llm(m, 220)) if ca._local_model_ready() else None
    history: list[dict] = []
    for text in sys.argv[1:] or MESSAGES:
        print(f"\nYOU: {text}")
        res = chat_commands.notebook_command(text, history) or chat_commands.memory_command(text, history)             or chat_commands.handle_command(text, {}, history)
        if res is not None and getattr(res, "text", None) is not None:
            print("  [native]", res.text.replace("\n", "\n           "))
            history += [{"role": "user", "content": text}, {"role": "assistant", "content": res.text}]
            continue
        if res is not None:
            print("  [native stream]", type(res).__name__)
            continue
        from cursiv_engine.core import notebook_proposals
        prop = notebook_proposals.correction(text)
        if prop is None and intent.might_be_action(text):
            parsed = notebook_proposals.record(text)        # same order as launcher/chat_actions.py
            prop = parsed if notebook_proposals.understood(parsed) else                 (intent.propose(text, ask) if ask else None) or parsed
        if prop is None:
            print("  [no command; would go to the model as chat]")
            continue
        print(f"  [card] {prop.action.title} {prop.card_lines()} problems={prop.problems}")
        if not prop.problems:
            done = chat_commands.notebook_command(prop.command, history) or chat_commands.handle_command(prop.command, {}, history)
            print("  [saved]", getattr(done, "text", done))
    print("\nSTORED RECORDS:")
    for e in fieldlog.entries():
        print(" ", json.dumps({k: e.get(k) for k in ("id", "project", "sample_id", "site", "measurements", "note", "corrects", "reason")},
                              ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

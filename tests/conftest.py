"""Shared setup for Cursiv's tests (pytest loads this automatically)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "launcher")):
    if p not in sys.path:
        sys.path.insert(0, p)

# Qt windows are built off-screen; tests never show anything.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Optional add-ons from a sibling Winkler_Codex_AI checkout are not part of
# these tests (and reading them from OneDrive can stall an import).
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)

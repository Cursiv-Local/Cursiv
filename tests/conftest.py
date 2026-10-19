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
# Building the chat window never starts the real AI engine in a test.
os.environ["CURSIV_NO_ENGINE_START"] = "1"

# Optional add-ons from a sibling Winkler_Codex_AI checkout are not part of
# these tests (and reading them from OneDrive can stall an import).
for _m in ("codex_tool_bridge", "knowledge_brain"):
    sys.modules.setdefault(_m, None)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _signing_key_in_tmp(tmp_path_factory, monkeypatch):
    """Never create or use the real installation key (~/.cursiv/device_key.json) in a test."""
    from cursiv_v215.core import devicekey
    folder = tmp_path_factory.mktemp("devicekey")
    monkeypatch.setattr(devicekey, "key_file", lambda: folder / "device_key.json")
    devicekey._cache.clear()
    yield
    devicekey._cache.clear()

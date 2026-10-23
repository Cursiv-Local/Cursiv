"""
Codex Agent — Winkler Personal Coding Specialist

Wraps the Winkler_Codex_AI system as a first-class Cursiv agent.
Handles all code generation and interpretation tasks.
Fully offline-capable (Phi-4 + LoRA deliberation protocol, no cloud API).

Discovery order:
  1. CURSIV_CODEX_PATH env var (absolute path to Winkler_Codex_AI root)
  2. Sibling directory: ../Winkler_Codex_AI relative to the Cursiv-v3 root
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

_CURSIV_ROOT = Path(__file__).resolve().parent.parent.parent

_CODEX_ROOT: Optional[Path] = None
for _candidate in [
    Path(os.environ["CURSIV_CODEX_PATH"]) if os.environ.get("CURSIV_CODEX_PATH") else None,
    _CURSIV_ROOT.parent / "Winkler_Codex_AI",
]:
    if _candidate and (_candidate / "Codex-Tool" / "cursiv_bridge" / "codex_tool_bridge.py").exists():
        _CODEX_ROOT = _candidate
        break

_AVAILABLE = False
_tool: Any = None

if _CODEX_ROOT:
    _bridge_path = str(_CODEX_ROOT / "Codex-Tool" / "cursiv_bridge")
    _codex_tool_path = str(_CODEX_ROOT / "Codex-Tool")
    for _p in [_bridge_path, _codex_tool_path]:
        if _p not in sys.path:
            sys.path.insert(0, _p)
    try:
        from codex_tool_bridge import CodexCodingTool  # type: ignore
        _tool = CodexCodingTool()
        _AVAILABLE = True
    except Exception:
        pass


def is_available() -> bool:
    """True if the Codex AI was discovered and loaded successfully."""
    return _AVAILABLE


def generate(prompt: str) -> str:
    """
    Generate code using the Winkler Codex deliberation protocol.

    Always returns output in two-section contract format:
      1. READY-TO-RUN CODE
      2. JSON FILES
    """
    if not _AVAILABLE or _tool is None:
        hint = (
            f"Set CURSIV_CODEX_PATH env var to the Winkler_Codex_AI root."
            if not _CODEX_ROOT else
            f"Codex found at {_CODEX_ROOT} but failed to load."
        )
        return f"[Codex Agent unavailable — {hint}]"
    try:
        return _tool.generate(prompt)
    except Exception as e:
        return f"[Codex Agent error: {e}]"


def codex_path() -> str:
    return str(_CODEX_ROOT) if _CODEX_ROOT else "not found"


def status() -> dict[str, Any]:
    base: dict[str, Any] = {"available": _AVAILABLE, "path": codex_path()}
    if not _AVAILABLE:
        return base
    try:
        return {**base, **_tool.status()}
    except Exception as e:
        return {**base, "error": str(e)}

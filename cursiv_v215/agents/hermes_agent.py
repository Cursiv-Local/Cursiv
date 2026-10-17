"""
Hermes Agent — Multi-step agentic task executor (offline-capable)

Wraps the Hermes Agent framework pointed at Ollama/llama3.1.
Use this for anything that needs a tool-calling loop: terminal commands,
multi-file operations, complex reasoning chains, delegated workflows.

Discovery: looks for hermes-agent as a sibling to Cursiv-v3, or via
CURSIV_HERMES_PATH env var.
"""
from __future__ import annotations

try:
    from cursiv_v215.guardian.identity_core import wrap as _identity_wrap
except ImportError:
    def _identity_wrap(s: str) -> str: return s

import os
import sys
from pathlib import Path
from typing import Any, Optional

_CURSIV_ROOT = Path(__file__).resolve().parent.parent.parent

_HERMES_ROOT: Optional[Path] = None
for _candidate in [
    Path(os.environ["CURSIV_HERMES_PATH"]) if os.environ.get("CURSIV_HERMES_PATH") else None,
    _CURSIV_ROOT.parent / "hermes-agent",
]:
    if _candidate and (_candidate / "run_agent.py").exists():
        _HERMES_ROOT = _candidate
        break

OLLAMA_BASE_URL = os.environ.get("CURSIV_OLLAMA_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL    = os.environ.get("CURSIV_OLLAMA_MODEL", "llama3.1")

# Hermes is imported on first use, not when Cursiv starts: importing the
# hermes-agent project pulls in its whole dependency tree, which made every
# Cursiv startup take minutes on machines that have it checked out.
_AVAILABLE = _HERMES_ROOT is not None
_AgentClass: Any = None
_LOAD_ERROR = ""


def _load() -> bool:
    """Import Hermes the first time it's actually needed."""
    global _AgentClass, _AVAILABLE, _LOAD_ERROR
    if _AgentClass is not None:
        return True
    if not _HERMES_ROOT:
        return False
    if str(_HERMES_ROOT) not in sys.path:
        sys.path.insert(0, str(_HERMES_ROOT))
    try:
        from run_agent import AIAgent as _AIAgent  # type: ignore
        _AgentClass = _AIAgent
        return True
    except Exception as exc:
        _AVAILABLE = False
        _LOAD_ERROR = str(exc)
        return False


def is_available() -> bool:
    """True when a hermes-agent checkout was found (it's loaded on first use)."""
    return _AVAILABLE


def _make_agent() -> Any:
    return _AgentClass(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        max_iterations=20,
    )


def run(prompt: str) -> str:
    """
    Hand off a multi-step agentic task to Hermes running on Ollama.
    Returns the final response string.
    Works offline — no cloud API needed.
    """
    if not _load():
        hint = (
            f"Set CURSIV_HERMES_PATH to the hermes-agent root."
            if not _HERMES_ROOT else
            f"Hermes found at {_HERMES_ROOT} but failed to load: {_LOAD_ERROR}"
        )
        return f"[Hermes Agent unavailable — {hint}]"
    try:
        agent = _make_agent()
        return agent.chat(_identity_wrap(prompt.strip()))
    except Exception as e:
        return f"[Hermes Agent error: {e}]"


def hermes_path() -> str:
    return str(_HERMES_ROOT) if _HERMES_ROOT else "not found"


def status() -> dict[str, Any]:
    return {
        "available": _AVAILABLE,
        "path":      hermes_path(),
        "model":     OLLAMA_MODEL,
        "base_url":  OLLAMA_BASE_URL,
    }

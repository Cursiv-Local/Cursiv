"""Local-engine setup checks.

needs_setup, installed_models and the start/restart helpers use the existing
core.ollama_host backend through explicit SetupRuntime services. The setup dialog
owns widgets and user choices; callers run blocking checks off the GUI thread.
"""
from __future__ import annotations
from pathlib import Path

from setup_checks_runtime import SetupRuntime

def recommended_index(runtime: SetupRuntime, options: list, small: bool) -> int:
    """Which entry to preselect: qwen3 4B on every card (the model comparison)."""
    return next((i for i, opt in enumerate(options) if opt[1] == "qwen3:4b-instruct"), 0)

def ollama_installed(runtime: SetupRuntime) -> bool:
    return runtime.ollama_host.installed()

def ollama_running(runtime: SetupRuntime) -> bool:
    return runtime.ollama_host.running()

def installed_models(runtime: SetupRuntime) -> list[str]:
    try:
        with runtime.urllib.request.urlopen(f"{runtime.OLLAMA_API}/api/tags", timeout=4) as r:
            names = [m.get("name", "") for m in runtime.json.loads(r.read().decode()).get("models", [])]
        return [n for n in names if n and "embed" not in n.lower()]
    except Exception:
        return []

def _engine_env(runtime: SetupRuntime):
    try:
        from cursiv_v215.core import speed
        return speed.ollama_env()          # flash attention + compact cache for this server
    except Exception:
        return None

def start_ollama(runtime: SetupRuntime) -> bool:
    """Start the Ollama server in the background if it isn't running."""
    return runtime.ollama_host.start(runtime._engine_env())

def restart_ollama(runtime: SetupRuntime) -> bool:
    """Quit and restart Ollama (fixes it not seeing downloaded models)."""
    return runtime.ollama_host.restart(runtime._engine_env())

def needs_setup(runtime: SetupRuntime) -> bool:
    """True when this computer can't run Cursiv locally yet (no Ollama, or no model)."""
    if not runtime.ollama_installed():
        return True
    if not runtime.ollama_running() and not runtime.start_ollama():
        return True
    return not runtime.installed_models()

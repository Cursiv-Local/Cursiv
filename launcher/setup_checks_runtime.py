"""Explicit setup-check services provided by setup_dialog.

Contains engine configuration and call overrides; no migration or network-policy
changes are made by defining this protocol.
"""
from typing import Any, Protocol


class SetupRuntime(Protocol):
    OLLAMA_API: Any
    _engine_env: Any
    installed_models: Any
    json: Any
    ollama_host: Any
    ollama_installed: Any
    ollama_running: Any
    start_ollama: Any
    urllib: Any

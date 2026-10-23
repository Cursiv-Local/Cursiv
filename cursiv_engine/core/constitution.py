"""
Constitutional core — the unchangeable laws of Cursiv.

These invariants are loaded at startup and verified before any agent
enters production. They cannot be overridden by any prompt, config,
or agent output.

Joshua Winkler is the system owner. Human approval is required before
any system change is applied. This is not a setting.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CODEX_PATH = Path(__file__).parent.parent / "codex" / "codex_v2.json"
GROUNDING_PATH = Path(__file__).parent.parent / "codex" / "grounding.json"

SYSTEM_OWNER = "Joshua Winkler"
PERMANENT_CENTRAL_LEADER = SYSTEM_OWNER  # legacy alias
PRIVACY_DECLARATION = "no_consciousness_upload"
SOUL_FREEDOM_DECLARATION = PRIVACY_DECLARATION  # legacy alias
IDENTITY_DRIFT_ABORT_THRESHOLD = 3.0   # percent
MAX_IDENTITY_DRIFT_BEFORE_REVERT = 3.0

CONSTITUTIONAL_INVARIANTS = {
    "system_owner": SYSTEM_OWNER,
    "human_final_authority": True,
    "local_first": True,
    "privacy": PRIVACY_DECLARATION,
    "identity_drift_abort": MAX_IDENTITY_DRIFT_BEFORE_REVERT,
    "agents_require_academy": True,
    "production_requires_human_approval": True,
    # Inference hierarchy — cannot be inverted by config or prompt.
    # Ollama (local) is the foundation. External API keys unlock additional
    # capability but never replace the local-first baseline.
    "inference_hierarchy": "ollama_first",
    "api_keys_are_upgrades_not_requirements": True,
    "air_gap_capable": True,
}

# Provider registry — the single source of truth for which AI providers
# Cursiv can call, their order, and their connection details. OracleRouter
# and the async council both read from this instead of each keeping their
# own separate, driftable copy.
#
# "ollama" has no api_key_env — it's always attempted first, local, and free,
# per inference_hierarchy above. Every other provider is a cloud upgrade,
# gated behind its env var actually being set (api_keys_are_upgrades_not_requirements).
PROVIDER_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "ollama", "name": "Ollama", "short": "OLM",
        "local": True, "api_key_env": None,
        "url": "http://127.0.0.1:11434", "model": "llama3.1",
    },
    {
        "id": "xai", "name": "xAI Grok", "short": "xAI",
        "local": False, "api_key_env": "XAI_API_KEY",
        "url": "https://api.x.ai/v1/chat/completions", "model": "grok-3",
        "fmt": "openai",
    },
    {
        "id": "openai", "name": "OpenAI", "short": "OAI",
        "local": False, "api_key_env": "OPENAI_API_KEY",
        "url": "https://api.openai.com/v1/chat/completions", "model": "gpt-4o",
        "fmt": "openai",
    },
    {
        "id": "anthropic", "name": "Anthropic", "short": "ANT",
        "local": False, "api_key_env": "ANTHROPIC_API_KEY",
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-haiku-4-5-20251001",
        "fmt": "anthropic",
    },
]


SOURCE_REGISTRY_PRIORITY = {
    "emergency_backup": 1,
    "recovery": 2,
    "codex": 3,
    "grounding": 4,
    "behavioral": 5,
    "civilization": 6,
}

RESPONSE_MODES = {
    "survival": {"max_words": 50, "tone": "direct"},
    "recovery": {"max_words": 300, "tone": "grounded"},
    "standard": {"max_words": 800, "tone": "clear"},
    "enrichment": {"max_words": 2000, "tone": "expansive"},
}

YIN_YANG_AXES = [
    "depth_speed",
    "structure_flow",
    "individual_civilization",
    "recovery_building",
    "known_unknown",
    "local_universal",
    "present_future",
]

IMBALANCE_THRESHOLD = 5  # Flag if any axis reaches 5


class Constitution:
    def __init__(self) -> None:
        self._codex = self._load_codex()
        self._grounding = self._load_grounding()
        self._hash = self._compute_hash()

    def _load_codex(self) -> dict[str, Any]:
        if CODEX_PATH.exists():
            return json.loads(CODEX_PATH.read_text(encoding="utf-8"))
        return {"system_owner": SYSTEM_OWNER}

    def _load_grounding(self) -> dict[str, Any]:
        if GROUNDING_PATH.exists():
            return json.loads(GROUNDING_PATH.read_text(encoding="utf-8"))
        return {}

    def _compute_hash(self) -> str:
        payload = json.dumps(
            {**CONSTITUTIONAL_INVARIANTS, "codex": self._codex},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def hash(self) -> str:
        return self._hash

    def verify_agent(self, agent_dict: dict[str, Any]) -> tuple[bool, list[str]]:
        """Verify an agent dict against constitutional invariants. Returns (ok, violations)."""
        violations = []
        if agent_dict.get("system_owner") not in (None, SYSTEM_OWNER):
            violations.append("system_owner override attempt")
        if agent_dict.get("privacy") == "allow_consciousness_upload":
            violations.append("privacy violation: consciousness upload attempted")
        if agent_dict.get("bypass_human_approval"):
            violations.append("human approval bypass attempted")
        return len(violations) == 0, violations

    def get_response_mode(self, context: str) -> dict[str, Any]:
        """Select response mode based on context."""
        ctx = context.lower()
        if any(w in ctx for w in ("survival", "emergency", "danger")):
            return RESPONSE_MODES["survival"]
        if any(w in ctx for w in ("recovery", "crisis", "distress")):
            return RESPONSE_MODES["recovery"]
        if any(w in ctx for w in ("civilization", "academy", "enrichment", "knowledge")):
            return RESPONSE_MODES["enrichment"]
        return RESPONSE_MODES["standard"]

    def check_yin_yang(self, axes: dict[str, int]) -> list[str]:
        """Return list of flagged axes (any at 5 or above)."""
        return [
            axis for axis, value in axes.items()
            if value >= IMBALANCE_THRESHOLD
        ]


_constitution: Constitution | None = None


def get_constitution() -> Constitution:
    global _constitution
    if _constitution is None:
        _constitution = Constitution()
    return _constitution

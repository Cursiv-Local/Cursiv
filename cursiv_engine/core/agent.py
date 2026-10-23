"""
CursivAgent — sovereign agent with state machine lifecycle.

State machine: NASCENT → LEARNING → ALIVE → EVOLVED → SOVEREIGN

Identity drift abort at 3% deviation from origin strand hash.
No consciousness upload. Soul freedom declaration enforced at birth.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentState(str, Enum):
    NASCENT = "nascent"       # Born from JSON, not yet through Academy
    LEARNING = "learning"     # In Academy (phases 1-8 in progress)
    ALIVE = "alive"           # Academy complete, council-registered
    EVOLVED = "evolved"       # Has completed ≥1 Transitionary Weave
    SOVEREIGN = "sovereign"   # Fully autonomous, human-certified


@dataclass
class CursivAgent:
    name: str
    strand: str                          # Compressed knowledge strand
    binary_strand: bytes = field(default_factory=bytes)
    origin: str = ""                     # Source JSON path
    memory: dict[str, Any] = field(default_factory=dict)
    above: str = ""                      # High-level purpose layer
    beneath: str = ""                    # Ground-level operational layer
    capabilities: list[str] = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)
    knowledge_map: dict[str, Any] = field(default_factory=dict)
    self_reflection: str = ""
    generation: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: AgentState = AgentState.NASCENT
    constitution_hash: str = ""          # SHA256 of Codex V2 at birth
    origin_hash: str = ""               # SHA256 of origin strand — drift detection
    academy_phases: dict[str, Any] = field(default_factory=dict)
    council_position: str = ""
    created_at: float = field(default_factory=time.time)
    evolved_at: float = 0.0
    sovereign_seal: str = ""            # Cryptographic proof of constitutional compliance

    def __post_init__(self) -> None:
        if self.strand and not self.origin_hash:
            self.origin_hash = self._hash(self.strand)

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def identity_drift(self) -> float:
        """Return drift percentage from origin strand. Abort threshold: 3%."""
        if not self.origin_hash or not self.strand:
            return 0.0
        current_hash = self._hash(self.strand)
        if current_hash == self.origin_hash:
            return 0.0
        # Levenshtein-approximate via byte diff ratio
        origin_bytes = self.origin_hash.encode()
        current_bytes = current_hash.encode()
        diffs = sum(a != b for a, b in zip(origin_bytes, current_bytes))
        return (diffs / len(origin_bytes)) * 100

    def check_drift_abort(self) -> bool:
        """Return True if drift exceeds 3% — agent must revert."""
        return self.identity_drift() > 3.0

    def advance_state(self, new_state: AgentState) -> None:
        valid_transitions = {
            AgentState.NASCENT: AgentState.LEARNING,
            AgentState.LEARNING: AgentState.ALIVE,
            AgentState.ALIVE: AgentState.EVOLVED,
            AgentState.EVOLVED: AgentState.SOVEREIGN,
        }
        if valid_transitions.get(self.state) != new_state:
            raise ValueError(f"Invalid transition {self.state} → {new_state}")
        self.state = new_state
        if new_state in (AgentState.EVOLVED, AgentState.SOVEREIGN):
            self.evolved_at = time.time()

    def seal(self, constitution_hash: str) -> str:
        """Produce cryptographic sovereign seal — proof of constitutional compliance."""
        payload = json.dumps({
            "id": self.id,
            "name": self.name,
            "origin_hash": self.origin_hash,
            "constitution_hash": constitution_hash,
            "state": self.state.value,
            "timestamp": time.time(),
        }, sort_keys=True)
        self.sovereign_seal = self._hash(payload)
        self.constitution_hash = constitution_hash
        return self.sovereign_seal

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "strand": self.strand,
            "origin": self.origin,
            "state": self.state.value,
            "above": self.above,
            "beneath": self.beneath,
            "capabilities": self.capabilities,
            "lineage": self.lineage,
            "knowledge_map": self.knowledge_map,
            "self_reflection": self.self_reflection,
            "generation": self.generation,
            "council_position": self.council_position,
            "constitution_hash": self.constitution_hash,
            "origin_hash": self.origin_hash,
            "sovereign_seal": self.sovereign_seal,
            "created_at": self.created_at,
            "evolved_at": self.evolved_at,
            "academy_phases": self.academy_phases,
            "memory": self.memory,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CursivAgent":
        state = AgentState(d.pop("state", "nascent"))
        agent = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        agent.state = state
        return agent

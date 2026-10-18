"""
Temporal memory — events fade, patterns persist.

Inspired by human sleep consolidation: recent events decay over time,
but patterns that repeat get consolidated into long-term memory.
The MemoryField is the agent's lived experience layer.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)


MEMORY_DIR = APP_DATA
MEMORY_FILE = MEMORY_DIR / "memory.json"

DEFAULT_HALF_LIFE_HOURS = 72.0   # Events decay over 3 days
PATTERN_THRESHOLD = 3            # Pattern forms after 3 identical events


class MemoryField:
    def __init__(self, path: Path = MEMORY_FILE) -> None:
        self.path = path
        self._data: dict[str, Any] = {
            "agents": {},
            "runs": [],
            "patterns": {},
            "long_term": {},
        }
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _decay_weight(self, timestamp: float, half_life_hours: float = DEFAULT_HALF_LIFE_HOURS) -> float:
        """Exponential decay: weight halves every half_life_hours."""
        hours_elapsed = (time.time() - timestamp) / 3600
        return math.exp(-math.log(2) * hours_elapsed / half_life_hours)

    def record_run(self, agent_id: str, query: str, response: str, quality: float) -> None:
        event = {
            "agent_id": agent_id,
            "query": query,
            "response_preview": response[:200],
            "quality": quality,
            "timestamp": time.time(),
        }
        self._data["runs"].append(event)
        self._data["runs"] = self._data["runs"][-500:]  # Keep last 500
        self._consolidate_patterns(agent_id, query)

    def _consolidate_patterns(self, agent_id: str, query: str) -> None:
        key = f"{agent_id}:{query[:60]}"
        patterns = self._data["patterns"]
        if key not in patterns:
            patterns[key] = {"count": 0, "first_seen": time.time(), "last_seen": time.time()}
        patterns[key]["count"] += 1
        patterns[key]["last_seen"] = time.time()
        if patterns[key]["count"] >= PATTERN_THRESHOLD:
            self._data["long_term"][key] = patterns[key]

    def register_agent(self, agent_id: str, agent_name: str, strand_summary: str) -> None:
        self._data["agents"][agent_id] = {
            "name": agent_name,
            "strand_summary": strand_summary,
            "registered_at": time.time(),
            "run_count": 0,
        }

    def get_relevant_memories(self, query: str, top_k: int = 5) -> list[dict]:
        """Return recent runs weighted by decay and relevance to query."""
        query_lower = query.lower()
        scored = []
        for run in reversed(self._data["runs"]):
            weight = self._decay_weight(run["timestamp"])
            relevance = 1.0 if query_lower[:30] in run["query"].lower() else 0.3
            scored.append((weight * relevance, run))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def get_long_term_patterns(self) -> dict[str, Any]:
        return self._data["long_term"]

    def agent_run_count(self, agent_id: str) -> int:
        return self._data["agents"].get(agent_id, {}).get("run_count", 0)

    def increment_run_count(self, agent_id: str) -> None:
        if agent_id in self._data["agents"]:
            self._data["agents"][agent_id]["run_count"] = \
                self._data["agents"][agent_id].get("run_count", 0) + 1


_global_memory: MemoryField | None = None


def get_memory() -> MemoryField:
    global _global_memory
    if _global_memory is None:
        _global_memory = MemoryField()
    return _global_memory

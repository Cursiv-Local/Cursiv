"""
Council Memory — semantic retrieval of past deliberations.

Stores every council deliberation and surfaces the most relevant prior
outcomes before a new deliberation begins, giving advisors context on
what the council previously concluded on similar queries.

Similarity is Jaccard over stopword-filtered tokens combined with
exponential recency decay — no external dependencies, works fully offline.
"""

from __future__ import annotations
from cursiv_engine.core import private_store, vault

import json
import math
import re
import time
from pathlib import Path
from typing import Any
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)

_MEMORY_PATH = APP_DATA / "council_memory.json"
_MAX_ENTRIES  = 300
_HALF_LIFE_H  = 168.0   # 7 days — council wisdom persists longer than run events

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of", "and",
    "or", "but", "for", "with", "this", "that", "what", "how", "why",
    "when", "where", "who", "can", "do", "did", "be", "was", "are",
    "not", "no", "yes", "i", "you", "we", "they", "he", "she",
    "my", "your", "their", "its", "me", "him", "her", "us",
})


def _tokenize(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return frozenset(w for w in words if w not in _STOPWORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _decay(timestamp: float) -> float:
    hours = (time.time() - timestamp) / 3600
    return math.exp(-math.log(2) * hours / _HALF_LIFE_H)


class CouncilMemory:
    def __init__(self, path: Path = _MEMORY_PATH) -> None:
        self._path = path
        self._entries: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._entries = json.loads(private_store.read_text(self._path, encoding="utf-8"))
            except vault.VaultError:
                raise
            except Exception:
                self._entries = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        private_store.write_text(self._path,
            json.dumps(self._entries, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def record(self, query: str, synthesis: str, quality: float) -> None:
        """Store a completed deliberation."""
        self._entries.append({
            "query":     query,
            "synthesis": synthesis[:600],
            "quality":   round(quality, 3),
            "timestamp": time.time(),
        })
        # Prune oldest entries beyond cap
        if len(self._entries) > _MAX_ENTRIES:
            self._entries = self._entries[-_MAX_ENTRIES:]
        self._save()

    def find_similar(self, query: str, top_k: int = 2, min_score: float = 0.12,
                     min_similarity: float = 0.15) -> list[dict[str, Any]]:
        """Return up to top_k past deliberations most relevant to query.

        Score = 0.70 * jaccard_similarity + 0.30 * recency_decay.
        Entries below min_score are excluded (avoids injecting noise), and so
        are entries whose topic overlap alone is below min_similarity -- recency
        by itself (up to 0.30) used to clear min_score, so any recent
        deliberation was injected even when it had nothing to do with the query.
        """
        if not self._entries:
            return []

        q_tokens = _tokenize(query)
        scored: list[tuple[float, dict]] = []

        for entry in self._entries:
            e_tokens = _tokenize(entry["query"])
            sim   = _jaccard(q_tokens, e_tokens)
            decay = _decay(entry["timestamp"])
            score = 0.70 * sim + 0.30 * decay
            if score >= min_score and sim >= min_similarity:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def format_prior_wisdom(self, similar: list[dict[str, Any]]) -> str:
        """Format retrieved memories as a concise council preamble."""
        if not similar:
            return ""
        lines = ["Prior council deliberations on related queries (use as reference, not constraint):"]
        for i, entry in enumerate(similar, 1):
            age_h  = (time.time() - entry["timestamp"]) / 3600
            age_str = f"{int(age_h)}h ago" if age_h < 48 else f"{int(age_h / 24)}d ago"
            lines.append(
                f"  [{i}] Q: {entry['query'][:80]}\n"
                f"      Council concluded ({age_str}, quality={entry['quality']}): "
                f"{entry['synthesis'][:250]}"
            )
        return "\n".join(lines)


_global_council_memory: CouncilMemory | None = None


def get_council_memory() -> CouncilMemory:
    global _global_council_memory
    if _global_council_memory is None:
        _global_council_memory = CouncilMemory()
    return _global_council_memory

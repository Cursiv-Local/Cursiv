"""
Reference Brain — Offline knowledge lookup (zero model required)

Two tiers, both fully offline:

  1. Bundled (always available, ships with every Cursiv install) --
     cursiv_v215/reference_data/*.json. A few dozen hand-curated,
     dense field-reference entries: survival, medical, science. Small
     (~50KB total) and loaded directly, no external dependency.

  2. Full brain (optional, only present on machines that also have the
     separate Winkler_Codex_AI project checked out) -- a 382MB SQLite
     database covering the same categories plus a full dictionary,
     thesaurus, and the CIA World Factbook (741k records total). Not
     part of the Cursiv installer -- most of that bulk is reference
     material an LLM already covers reasonably well on its own; the
     bundled tier above is the part that's actually differentiated
     (specific, field-tested facts a model might otherwise guess at).

When both are available the full brain answers first (deeper, more
records); the bundled tier is always the fallback, so `ref` never comes
back empty on a plain install.
"""
from __future__ import annotations

import json
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
    if _candidate and (_candidate / "Wrapped-System" / "knowledge_brain.py").exists():
        _CODEX_ROOT = _candidate
        break

_AVAILABLE = False
_brain: Any = None

if _CODEX_ROOT:
    _wrapped_path = str(_CODEX_ROOT / "Wrapped-System")
    if _wrapped_path not in sys.path:
        sys.path.insert(0, _wrapped_path)
    try:
        from knowledge_brain import ReferenceBrain  # type: ignore
        _db = _CODEX_ROOT / "Wrapped-System" / "data" / "reference_brain.sqlite"
        _brain = ReferenceBrain(db_path=str(_db))
        _AVAILABLE = _db.exists()
    except Exception:
        pass


# ── Bundled tier -- always available, no external dependency ──────────────

_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "reference_data"
_BUNDLED_FILES = {
    "survival": _BUNDLED_DIR / "survival.json",
    "medical":  _BUNDLED_DIR / "medical.json",
    "science":  _BUNDLED_DIR / "science.json",
}
# key -> (category, content)
_bundled_entries: dict[str, tuple[str, str]] = {}


def _load_bundled() -> None:
    for category, path in _BUNDLED_FILES.items():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key, content in data.items():
            _bundled_entries[key] = (category, content)


_load_bundled()


def bundled_available() -> bool:
    return bool(_bundled_entries)


def _bundled_search(query: str, limit: int = 3) -> list[tuple[str, str, str]]:
    """The same strict matching chat uses (core/reference.lookup): an entry
    only when the question names its topic. Any-shared-word scoring returned
    water purification for "how do I write a cover letter"."""
    from cursiv_v215.core import reference
    return [(e.title, e.category, e.text) for e in reference.lookup(query, limit=limit)]


def _bundled_answer(query: str) -> str:
    results = _bundled_search(query)
    if not results:
        return ""
    lines = ["[Reference Brain — offline, bundled]"]
    for key, category, content in results:
        lines.append(f"\n{key.upper()}  ({category}):\n{content}")
    return "\n".join(lines)


def is_available() -> bool:
    return _AVAILABLE or bundled_available()


def search(query: str, limit: int = 6) -> str:
    """
    Search the local reference brain. Returns formatted results as a string.
    Covers: dictionary, thesaurus, survival, medical, science, factbook
    (full tier); survival, medical, science (bundled tier, always on).
    No model or internet needed.
    """
    if not query or not query.strip():
        return "[Reference Brain] No query provided."
    if _AVAILABLE and _brain is not None:
        try:
            result = _brain.context_block(query.strip(), limit=limit)
            if result:
                return f"[Reference Brain — offline]\n{result}"
        except Exception:
            pass
    if bundled_available():
        result = _bundled_answer(query.strip())
        if result:
            return result
    if not _AVAILABLE and not bundled_available():
        return "[Reference Brain unavailable — no bundled or full data found]"
    return f"[Reference Brain] No results found for: {query}"


def answer(query: str) -> str:
    """Full grounded answer with intent classification (define / medical / survival / general)."""
    if not query or not query.strip():
        return "[Reference Brain] No query provided."
    if _AVAILABLE and _brain is not None:
        try:
            result = _brain.answer_from_references(query.strip())
            if result:
                return result
        except Exception:
            pass
    if bundled_available():
        result = _bundled_answer(query.strip())
        if result:
            return result
    if not _AVAILABLE and not bundled_available():
        return "[Reference Brain unavailable]"
    return f"[Reference Brain] No results for: {query}"


def status() -> dict[str, Any]:
    base: dict[str, Any] = {
        "available": is_available(),
        "full_brain": _AVAILABLE,
        "bundled_entries": len(_bundled_entries),
    }
    if _AVAILABLE:
        try:
            return {**base, **_brain.status()}
        except Exception as e:
            return {**base, "error": str(e)}
    return {**base, "full_brain_path": str(_CODEX_ROOT) if _CODEX_ROOT else "not found"}

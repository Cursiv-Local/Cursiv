"""
Strand Store — persistent Strand archive.

Every anchored exchange, high-quality council synthesis, or human-rated
response becomes a Strand: a versioned, territory-tagged atom of
compounding personal memory that persists across all sessions.

Unlike session logs (ephemeral, per-day JSONL), Strands are permanent,
retrievable by semantic similarity, and feed directly into the LoRA
training queue as the highest-quality signal source.

Search backend:
  When NumPy is available (recommended): vectorized term-document matrix.
    - Strands loaded once into memory; rebuilt only when strands.jsonl changes.
    - Jaccard computed as a single matrix-vector multiply.
    - Recency decay applied as a vectorized exponential.
    - 10 000 strands searched in < 5 ms.
  When NumPy is absent: pure Python fallback (original behaviour).

Storage:
  .cursiv/strands.jsonl      — one JSON line per strand
  .cursiv/territories.json   — user-owned territory definitions (human-editable)
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import threading
import uuid
from pathlib import Path
from typing import Any

from cursiv_engine.core.strand import encode as _strand_encode
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)
from cursiv_engine.core import private_store, vault

# ── Optional NumPy acceleration ───────────────────────────────────────────────
try:
    import numpy as np
    _NUMPY_OK = True
except ImportError:
    np = None        # type: ignore[assignment]
    _NUMPY_OK = False

ROOT             = Path(__file__).parent.parent.parent
CURSIV_DIR       = APP_DATA
STRANDS_FILE     = CURSIV_DIR / "strands.jsonl"
TERRITORIES_FILE = CURSIV_DIR / "territories.json"
_save_lock = threading.RLock()

_DEFAULT_TERRITORIES: dict[str, dict] = {
    "coding":       {"description": "Software builds, Codex sessions, architecture decisions"},
    "recovery":     {"description": "Health protocols, grounding, stop-stabilize-rebuild"},
    "architecture": {"description": "System design, Cursiv evolution, infrastructure bets"},
    "creative":     {"description": "FunForge spikes, music theory, novel ideas"},
    "worldmodel":   {"description": "Research, council insights, external observations"},
    "general":      {"description": "Uncategorized strands — default territory"},
}

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "of", "and",
    "or", "but", "for", "with", "this", "that", "what", "how", "why",
    "when", "where", "who", "can", "do", "did", "be", "was", "are",
    "not", "no", "yes", "i", "you", "we", "they", "he", "she",
    "my", "your", "their", "its", "me", "him", "her", "us",
})


# ── Token helpers ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> frozenset[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return frozenset(w for w in words if w not in _STOPWORDS)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _decay(timestamp: float, half_life_days: float = 30.0) -> float:
    hours = (time.time() - timestamp) / 3600
    half_life_h = half_life_days * 24
    return math.exp(-math.log(2) * hours / half_life_h)


def _load_all() -> list[dict[str, Any]]:
    if not STRANDS_FILE.exists():
        return []
    strands: list[dict] = []
    try:
        with private_store.lines(STRANDS_FILE) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        strands.append(json.loads(line))
                    except Exception:
                        pass
    except vault.VaultError:
        raise
    except Exception:
        pass
    return strands


# ── NumPy term-document matrix ────────────────────────────────────────────────

class _StrandMatrix:
    """
    In-memory cache + vectorized search layer for the strand archive.

    Loaded once on first search; rebuilt automatically when strands.jsonl
    is modified (mtime check). Falls back to pure-Python Jaccard when
    NumPy is unavailable.

    Memory: ~1 MB per 1 000 strands × 1 000 vocab terms (bool dtype).
    Typical search latency: < 1 ms at 1 000 strands, < 5 ms at 10 000.
    """

    def __init__(self) -> None:
        self._strands:    list[dict]        = []
        self._vocab:      dict[str, int]    = {}
        self._matrix:     Any               = None   # np.ndarray | None  (N, V) bool
        self._timestamps: Any               = None   # np.ndarray | None  (N,) float64
        self._mtime:      float             = -1.0
        self._built:      bool              = False

    # ── Staleness ────────────────────────────────────────────────────────────

    def _current_mtime(self) -> float:
        try:
            return STRANDS_FILE.stat().st_mtime if STRANDS_FILE.exists() else 0.0
        except OSError:
            return 0.0

    def _is_stale(self) -> bool:
        return not self._built or self._current_mtime() != self._mtime

    def invalidate(self) -> None:
        """Force a rebuild on the next search (called after each save_strand)."""
        self._mtime = -1.0

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self, strands: list[dict]) -> None:
        self._strands = strands
        self._mtime   = self._current_mtime()
        self._built   = True

        if not strands or not _NUMPY_OK:
            self._matrix     = None
            self._timestamps = None
            self._vocab      = {}
            return

        # Tokenize every strand once
        vocab:      dict[str, int] = {}
        tokenized:  list[list[str]] = []
        for s in strands:
            toks = list(_tokenize(s.get("query", "") + " " + s.get("synthesis", "")))
            for t in toks:
                if t not in vocab:
                    vocab[t] = len(vocab)
            tokenized.append(toks)

        V = len(vocab)
        N = len(strands)

        if V == 0:
            self._matrix     = None
            self._timestamps = None
            self._vocab      = vocab
            return

        matrix     = np.zeros((N, V), dtype=np.bool_)
        timestamps = np.empty(N, dtype=np.float64)

        for i, (s, toks) in enumerate(zip(strands, tokenized)):
            for t in toks:
                matrix[i, vocab[t]] = True
            timestamps[i] = s.get("timestamp", 0.0)

        self._vocab      = vocab
        self._matrix     = matrix
        self._timestamps = timestamps

    def ensure_loaded(self) -> None:
        if self._is_stale():
            self._build(_load_all())

    # ── Vectorized search ────────────────────────────────────────────────────

    def _search_numpy(
        self,
        query: str,
        top_k: int,
        min_score: float,
    ) -> list[dict]:
        q_tokens = _tokenize(query)
        if not q_tokens or self._matrix is None:
            return []

        V     = len(self._vocab)
        q_vec = np.zeros(V, dtype=np.bool_)
        for t in q_tokens:
            if t in self._vocab:
                q_vec[self._vocab[t]] = True

        if not q_vec.any():
            return []

        # Jaccard — matrix-vector multiply for intersection counts
        intersection = self._matrix @ q_vec          # (N,)
        q_sum        = int(q_vec.sum())
        s_sums       = self._matrix.sum(axis=1)      # (N,)
        union        = q_sum + s_sums - intersection  # (N,)
        jaccard      = intersection.astype(np.float32) / np.maximum(union, 1).astype(np.float32)

        # Recency decay
        hours   = (time.time() - self._timestamps) / 3600.0
        recency = np.exp(-np.log(2.0) * hours / (30.0 * 24.0)).astype(np.float32)

        combined = 0.70 * jaccard + 0.30 * recency   # (N,)

        # Filter + top-k
        mask = combined >= min_score
        if not mask.any():
            return []

        valid_idx    = np.where(mask)[0]
        valid_scores = combined[valid_idx]

        if len(valid_idx) <= top_k:
            order   = np.argsort(valid_scores)[::-1]
            top_idx = valid_idx[order]
        else:
            # argpartition: O(n) vs argsort's O(n log n)
            part    = np.argpartition(valid_scores, -top_k)[-top_k:]
            order   = np.argsort(valid_scores[part])[::-1]
            top_idx = valid_idx[part[order]]

        results = []
        for idx in top_idx:
            s         = dict(self._strands[int(idx)])
            s["score"] = float(combined[int(idx)])
            results.append(s)
        return results

    def _search_python(
        self,
        query: str,
        top_k: int,
        min_score: float,
    ) -> list[dict]:
        q_tokens = _tokenize(query)
        scored: list[tuple[float, dict]] = []
        for s in self._strands:
            e_tokens = _tokenize(s.get("query", "") + " " + s.get("synthesis", ""))
            sim      = _jaccard(q_tokens, e_tokens)
            decay    = _decay(s.get("timestamp", 0))
            combined = 0.70 * sim + 0.30 * decay
            if combined >= min_score:
                scored.append((combined, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]

    def search(self, query: str, top_k: int, min_score: float) -> list[dict]:
        self.ensure_loaded()
        if _NUMPY_OK and self._matrix is not None:
            return self._search_numpy(query, top_k, min_score)
        return self._search_python(query, top_k, min_score)

    def find_linked(
        self,
        query: str,
        synthesis: str,
        threshold: float = 0.25,
    ) -> list[str]:
        """Return IDs of strands above threshold — vectorized when NumPy available."""
        self.ensure_loaded()
        combined_text = query + " " + synthesis
        hits = self._search_numpy(combined_text, top_k=5, min_score=threshold) \
               if (_NUMPY_OK and self._matrix is not None) \
               else self._search_python(combined_text, top_k=5, min_score=threshold)
        return [s["id"] for s in hits]


# Module-level singleton — loaded once, lives for the process lifetime
_mx = _StrandMatrix()


# ── Territories ──────────────────────────────────────────────────────────────

def load_territories() -> dict[str, dict]:
    """Load user territory definitions, creating defaults on first run."""
    if TERRITORIES_FILE.exists():
        try:
            return json.loads(TERRITORIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    _write_default_territories()
    return _DEFAULT_TERRITORIES.copy()


def _write_default_territories() -> None:
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    TERRITORIES_FILE.write_text(
        json.dumps(_DEFAULT_TERRITORIES, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Core API ──────────────────────────────────────────────────────────────────

def _find_linked(query: str, synthesis: str, link_threshold: float = 0.25) -> list[str]:
    """Return IDs of existing strands with similarity above threshold."""
    return _mx.find_linked(query, synthesis, link_threshold)


def save_strand(
    query: str,
    synthesis: str,
    *,
    tags: list[str] | None = None,
    score: float = 0.70,
    territory_tag: str = "general",
    source: str = "anchor",
    model: str = "unknown",
    provenance: dict | None = None,
) -> str:
    """Encode and persist a Strand. Returns the 8-char strand_id, or "" on
    failure. Memory persistence is a side effect of a real conversation --
    it must never be able to take the whole session down. This used to have
    no error handling at all, and a single bad character (an unpaired
    Unicode surrogate that can end up in streamed AI provider text) reaching
    the strict-UTF-8 JSON encode was enough to crash the entire CLI mid-
    session, right after a real council deliberation completed. The specific
    encoding bug is fixed at its source in strand.py; this catch-all is the
    backstop for whatever the next one turns out to be (disk full, a
    permissions error, anything) -- callers already treat "" as "no strand
    saved" (see the disabled-fallback stub above), so this fails the same
    way a disabled strand store already does, not with a crash.
    """
    try:
        CURSIV_DIR.mkdir(parents=True, exist_ok=True)
        strand_id = str(uuid.uuid4())[:8]
        knowledge = {
            "query":     query,
            "synthesis": synthesis,
            "territory": territory_tag,
        }
        encoded = _strand_encode(knowledge)
        linked  = _find_linked(query, synthesis)

        entry: dict[str, Any] = {
            "id":             strand_id,
            "strand":         encoded,
            "query":          query.strip()[:500],
            "synthesis":      synthesis.strip()[:1000],
            "tags":           tags or [],
            "score":          round(float(score), 3),
            "timestamp":      time.time(),
            "territory_tag":  territory_tag,
            "source":         source,
            "model":          model,
            "linked_strands": linked,
            "provenance":     provenance or {
                "source_models": [model],
                "human_rated":   False,
                "confidence":    round(float(score), 3),
            },
        }
        data = (json.dumps(entry, ensure_ascii=False) + '\n').encode('utf-8')
        with _save_lock:
            if vault.owner(STRANDS_FILE):
                try:
                    existing = private_store.read_bytes(STRANDS_FILE)
                except FileNotFoundError:
                    existing = b''
                if existing and not existing.endswith(b'\n'):
                    existing += b'\n'
                from . import atomic
                atomic.write_bytes(STRANDS_FILE, existing + data)
                if private_store.read_bytes(STRANDS_FILE) != existing + data:
                    raise OSError('Saved-note append read-back verification failed')
            else:
                with STRANDS_FILE.open('ab+') as stream:
                    stream.seek(0, os.SEEK_END)
                    end = stream.tell()
                    if end:
                        stream.seek(-1, os.SEEK_END)
                        if stream.read(1) != b'\n':
                            stream.write(b'\n')
                    stream.seek(0, os.SEEK_END)
                    start = stream.tell()
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                    stream.seek(start)
                    if stream.read(len(data)) != data:
                        raise OSError('Saved-note append read-back verification failed')

        _mx.invalidate()   # matrix rebuilt on next search with new strand included
        return strand_id
    except Exception as exc:
        # print() calls sys.stdout.write() internally -- fine for the
        # terminal CLI, but sys.stdout is None in the packaged GUI build
        # (console=False), so a failed save would otherwise crash a second
        # time right here, inside its own error handler, instead of just
        # returning "" like the caller expects.
        try:
            print(f"  [strand save failed: {type(exc).__name__}: {exc}]")
        except Exception:
            pass
        return ""


def get_strand(strand_id: str) -> dict[str, Any] | None:
    _mx.ensure_loaded()
    for s in _mx._strands:
        if s.get("id") == strand_id:
            return s
    return None


def list_strands(
    territory: str | None = None,
    min_score: float = 0.0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return strands most-recent-first, optionally filtered by territory and score."""
    _mx.ensure_loaded()
    all_s = list(_mx._strands)
    if territory:
        all_s = [s for s in all_s if s.get("territory_tag") == territory]
    if min_score > 0:
        all_s = [s for s in all_s if s.get("score", 0) >= min_score]
    all_s.sort(key=lambda s: s.get("timestamp", 0), reverse=True)
    return all_s[:limit]


def search_strands(
    query: str,
    top_k: int = 3,
    min_score: float = 0.10,
) -> list[dict[str, Any]]:
    """
    Jaccard + recency-decay semantic search.

    Uses NumPy term-document matrix when available:
      - Single matrix-vector multiply for all intersection counts
      - Vectorized exponential for recency decay
      - argpartition O(n) top-k selection
    Falls back to pure Python when NumPy is absent.
    """
    return _mx.search(query, top_k, min_score)


def strand_count() -> int:
    _mx.ensure_loaded()
    return len(_mx._strands)


def territory_counts() -> dict[str, int]:
    """Return strand count per territory."""
    _mx.ensure_loaded()
    counts: dict[str, int] = {}
    for s in _mx._strands:
        t = s.get("territory_tag", "general")
        counts[t] = counts.get(t, 0) + 1
    return counts


# ── Display ───────────────────────────────────────────────────────────────────

def format_strand_list(strands: list[dict[str, Any]]) -> str:
    if not strands:
        return "  No strands found."
    lines = []
    for s in strands:
        age_h   = (time.time() - s.get("timestamp", 0)) / 3600
        age_str = f"{int(age_h)}h ago" if age_h < 48 else f"{int(age_h / 24)}d ago"
        src     = s.get("source", "?")
        terr    = s.get("territory_tag", "general")
        sc      = s.get("score", 0)
        lines.append(
            f"  [{s.get('id','?')}]  {terr:<13} score:{sc:.2f}  {src:<14}  {age_str}\n"
            f"    {s.get('query','')[:72]}"
        )
    return "\n".join(lines)

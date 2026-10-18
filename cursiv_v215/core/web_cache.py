"""
Web Search Cache — SQLite TTL cache for search results.

Check-before-fetch: every web search hits the cache first.
On cache miss: live search fires, result stored for TTL hours.
When offline: stale cache entries are served with a [cached] label
rather than returning nothing — the system stays useful on Starlink
drops, airplane mode, or full air-gap.

Storage: .cursiv/search_cache.db
Default TTL: 24 hours
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

ROOT      = Path(__file__).parent.parent.parent
CACHE_DB  = APP_DATA / "search_cache.db"
DEFAULT_TTL = 86_400.0  # 24 h in seconds


def _conn() -> sqlite3.Connection:
    CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(CACHE_DB))
    c.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            query     TEXT PRIMARY KEY,
            result    TEXT NOT NULL,
            cached_at REAL NOT NULL,
            ttl_s     REAL NOT NULL DEFAULT 86400
        )
    """)
    c.commit()
    return c


def get_cached(query: str, allow_stale: bool = False) -> tuple[str, bool] | None:
    """
    Return (result, is_fresh) if found, else None.
    If allow_stale=True, returns expired entries too (for offline fallback).
    """
    try:
        with _conn() as c:
            row = c.execute(
                "SELECT result, cached_at, ttl_s FROM search_cache WHERE query = ?",
                (query.lower().strip(),),
            ).fetchone()
        if row:
            result, cached_at, ttl_s = row
            fresh = (time.time() - cached_at) < ttl_s
            if fresh or allow_stale:
                return result, fresh
    except Exception:
        pass
    return None


def store(query: str, result: str, ttl_s: float = DEFAULT_TTL) -> None:
    """Cache a search result."""
    try:
        with _conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO search_cache "
                "(query, result, cached_at, ttl_s) VALUES (?, ?, ?, ?)",
                (query.lower().strip(), result, time.time(), ttl_s),
            )
    except Exception:
        pass


def evict_expired() -> int:
    """Remove all expired entries. Returns count removed."""
    try:
        with _conn() as c:
            cur = c.execute(
                "DELETE FROM search_cache WHERE (? - cached_at) >= ttl_s",
                (time.time(),),
            )
            return cur.rowcount
    except Exception:
        return 0


def stats() -> dict:
    try:
        with _conn() as c:
            total = c.execute("SELECT COUNT(*) FROM search_cache").fetchone()[0]
            fresh = c.execute(
                "SELECT COUNT(*) FROM search_cache WHERE (? - cached_at) < ttl_s",
                (time.time(),),
            ).fetchone()[0]
        return {"total": total, "fresh": fresh, "stale": total - fresh}
    except Exception:
        return {"total": 0, "fresh": 0, "stale": 0}

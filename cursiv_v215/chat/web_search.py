"""
Web search: DuckDuckGo (no key) or Brave (BRAVE_API_KEY), with a 24-hour cache.

Only when the person asks ("search: ...") or turned on automatic search
('websearch on'), and never in offline mode (core/netgate.py, AUDIT C-009).
"""
from __future__ import annotations

import json
import os
import re as _re
import urllib.parse as _urlparse
import urllib.request

from cursiv_v215.core import netgate


# ── Web Search Cache — TTL cache for search results ───────────────────────
try:
    from cursiv_v215.core.web_cache import (
        get_cached   as _wcache_get,
        store        as _wcache_store,
        evict_expired as _wcache_evict,
    )
    _WCACHE_OK = True
except Exception:
    _WCACHE_OK = False
    def _wcache_get(q, **kw): return None  # type: ignore[misc]
    def _wcache_store(q, r, **kw): pass
    def _wcache_evict(): return 0

BRAVE_KEY = os.environ.get("BRAVE_API_KEY", "")

# DuckDuckGo sometimes answers with a "are you a bot?" challenge instead of results. Its sentences
# ("Please complete the following challenge ...") used to be kept as search results, cached for a day,
# given to the model as current facts and labelled "web search results" (U77, 2026-10-19).
_BOT_CHECK = _re.compile(r"(?i)bots use duckduckgo|complete the following challenge|select all squares|"
                         r"anomaly-modal|error-lite[+@]|confirm this search was made by a human|unusual traffic|captcha")
BOT_CHECK_MESSAGE = ("DuckDuckGo asked to confirm a human (a bot check) instead of giving results, so nothing came back. "
                     "This happens after many searches from one connection; try again later")
last_problem = ""          # why the last _web_search() came back empty: "" when it found something

_SEARCH_TRIGGERS = (
    "latest ", "current ", "today ", "right now", "this week", "this month",
    "who won", "what happened", "news ", "price of ", "weather ",
    "search:", "search for", "look up", "find me ", "real-time", "realtime",
    "live ", "breaking ", "recent ", "just announced", "just released",
    "new version of", "stock price", "crypto price", "cryptocurrency",
)

def _needs_search(text: str) -> bool:
    """Web search only when the person asks for it ("search: ..."), or when they
    turned on automatic search ('websearch on'). Never while offline mode is on.
    The trigger words used to fire on their own and send the message to
    DuckDuckGo ("...the farm where we live", "right now"): AUDIT C-009."""
    if not netgate.allowed():
        return False
    lower = text.lower().lstrip()
    if lower.startswith("search:") or lower.startswith("search "):
        return True
    return netgate.web_search_auto() and any(t in lower for t in _SEARCH_TRIGGERS)

def _ddg_search(query: str, max_results: int = 4) -> str:
    """DuckDuckGo: Instant Answer API with Lite HTML fallback."""
    # ── Instant Answer API (fast, structured, worldwide) ──
    try:
        url = (
            f"https://api.duckduckgo.com/?q={_urlparse.quote(query)}"
            f"&format=json&no_html=1&skip_disambig=1&t=Cursiv"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Cursiv/3.14 (search)"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
        parts = []
        if data.get("Answer"):
            parts.append(f"Direct answer: {data['Answer']}")
        if data.get("AbstractText"):
            parts.append(f"{data['AbstractText']}\nSource: {data.get('AbstractURL', '')}")
        for t in data.get("RelatedTopics", [])[:3]:
            if isinstance(t, dict) and t.get("Text"):
                parts.append(t["Text"])
        if parts:
            return "\n\n".join(parts)
    except Exception:
        pass

    # ── Lite HTML fallback (catches news / current events) ──
    try:
        url = f"https://lite.duckduckgo.com/lite/?q={_urlparse.quote(query)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=7) as r:
            html = r.read().decode("utf-8", errors="replace")
        if _BOT_CHECK.search(html):
            global last_problem
            last_problem = BOT_CHECK_MESSAGE
            return ""
        text  = _re.sub(r"<[^>]+>", " ", html)
        text  = _re.sub(r"\s+", " ", text)
        snips = _re.findall(r"[A-Z][^.!?]{30,250}[.!?]", text)
        seen, results = set(), []
        for s in snips:
            s = s.strip()
            if s not in seen and len(s) > 40:
                seen.add(s)
                results.append(s)
            if len(results) >= max_results:
                break
        if results:
            return "\n\n".join(results)
    except Exception:
        pass

    return ""

def _brave_search(query: str, max_results: int = 4) -> str:
    """Brave Search API — best quality, requires BRAVE_API_KEY env var."""
    try:
        url = (
            f"https://api.search.brave.com/res/v1/web/search"
            f"?q={_urlparse.quote(query)}&count={max_results}"
        )
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_KEY,
        })
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = data.get("web", {}).get("results", [])
        lines = []
        for item in results[:max_results]:
            title = item.get("title", "")
            desc  = item.get("description", "")
            src   = item.get("url", "")
            if desc:
                lines.append(f"{title}\n{desc}\nSource: {src}")
        return "\n\n".join(lines) if lines else ""
    except Exception:
        return _ddg_search(query, max_results)

def _web_search(query: str, max_results: int = 4) -> str:
    """
    Worldwide real-time web search with TTL cache.
    Cache-first: returns cached result within 24h TTL.
    Falls back to cache (marked [cached]) when offline.
    Uses Brave Search API if BRAVE_API_KEY is set, else DuckDuckGo.
    """
    global last_problem
    last_problem = ""
    q = query.strip()
    if not q:
        return ""
    for prefix in ("search:", "search "):
        if q.lower().startswith(prefix):
            q = q[len(prefix):].strip()
            break

    # Cache check (fresh hit — serve without touching network)
    if _WCACHE_OK:
        hit = _wcache_get(q)
        if hit:
            result, fresh = hit
            if fresh and not _BOT_CHECK.search(result or ""):   # a bot check cached before U78 isn't a result
                return result

    # Live search (never while offline mode is on)
    live_result = ""
    if not netgate.allowed():
        pass
    elif BRAVE_KEY:
        live_result = _brave_search(q, max_results)
    if not live_result and netgate.allowed():
        live_result = _ddg_search(q, max_results)

    if live_result and _BOT_CHECK.search(live_result):
        live_result, last_problem = "", BOT_CHECK_MESSAGE
    if live_result and _WCACHE_OK:
        _wcache_store(q, live_result)
        return live_result

    # Offline fallback — serve stale cache with label
    if _WCACHE_OK and not live_result:
        stale = _wcache_get(q, allow_stale=True)
        if stale and not _BOT_CHECK.search(stale[0] or ""):
            result, _ = stale
            return f"[cached — offline fallback]\n{result}"

    if not live_result and not last_problem:
        last_problem = ("offline mode is on" if not netgate.allowed() else
                        "the search engine sent back no results (or couldn't be reached)")
    return live_result

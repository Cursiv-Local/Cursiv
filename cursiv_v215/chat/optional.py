"""
Optional parts of Cursiv, loaded if present. Each has a fallback, so a
missing piece turns its feature off instead of breaking chat.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


# ── Token rate limiter + scan display ──────────────────────────────────────
try:
    from cursiv_v215.core.rate_limiter import limiter as _rate_limiter
    from cursiv_v215.core.scan_display import ScanDisplay as _ScanDisplay
    _scan = _ScanDisplay(_rate_limiter)
    _RATE_OK = True
except Exception:
    _rate_limiter = None
    _scan         = None
    _RATE_OK      = False

# ── Codex Agent — offline-capable coding specialist ──────────────────────
try:
    from cursiv_v215.agents.codex_agent import (
        generate     as _codex_generate,
        is_available as _codex_available,
        status       as _codex_status,
    )
    _CODEX_OK = True
except Exception:
    _CODEX_OK = False
    def _codex_generate(p: str) -> str:    return ""
    def _codex_available() -> bool:        return False
    def _codex_status() -> dict:           return {"available": False}

# ── Hermes Agent — offline multi-step tool executor ───────────────────────
try:
    from cursiv_v215.agents.hermes_agent import (
        run          as _hermes_run,
        is_available as _hermes_available,
        status       as _hermes_status,
    )
    _HERMES_OK = True
except Exception:
    _HERMES_OK = False
    def _hermes_run(p: str) -> str:        return ""
    def _hermes_available() -> bool:       return False
    def _hermes_status() -> dict:          return {"available": False}

# ── Reference Brain — offline SQLite knowledge base ───────────────────────
try:
    from cursiv_v215.agents.reference_brain import (
        search       as _ref_search,
        answer       as _ref_answer,
        is_available as _ref_available,
        status       as _ref_status,
    )
    _REF_OK = True
except Exception:
    _REF_OK = False
    def _ref_search(q: str, limit: int = 6) -> str: return ""
    def _ref_answer(q: str) -> str:                 return ""
    def _ref_available() -> bool:                   return False
    def _ref_status() -> dict:                      return {"available": False}

# ── Strand Federation — import/export ─────────────────────────────────────
try:
    from cursiv_v215.core.strand_federation import (
        export_pack as _sfed_export,
        import_pack as _sfed_import,
        pack_summary as _sfed_summary,
    )
    _SFED_OK = True
except Exception:
    _SFED_OK = False

# ── Strand Store — persistent memory retrieval ────────────────────────────
try:
    from cursiv_v215.core.strand_store import (
        search_strands as _strand_search,
        strand_count   as _strand_count,
    )
    _STRAND_APP_OK = True
except Exception:
    _STRAND_APP_OK = False
    def _strand_search(q, **kw): return []  # type: ignore[misc]
    def _strand_count() -> int:  return 0

# ── Offline Queue — capture tasks for later ───────────────────────────────
try:
    from cursiv_v215.agents.offline_queue import (
        enqueue      as _queue_enqueue,
        format_queue as _queue_format,
        count        as _queue_count,
        flush        as _queue_flush,
    )
    _QUEUE_OK = True
except Exception:
    _QUEUE_OK = False
    def _queue_enqueue(p: str, **kw) -> dict:  return {}
    def _queue_format() -> str:                return ""
    def _queue_count() -> int:                 return 0
    def _queue_flush(fn) -> list:              return []

# ── Obsidian Vault Sync ────────────────────────────────────────────────────
try:
    from cursiv_v215.obsidian.exporter import (
        load_config    as _obs_load_config,
        save_config    as _obs_save_config,
        export_today   as _obs_export,
        auto_export_if_enabled as _obs_auto_export,
        auto_detect_vault      as _obs_detect_vault,
        livestream_exchange    as _obs_livestream,
    )
    _OBS_OK = True
except Exception:
    _OBS_OK = False
    def _obs_load_config():              return {"enabled": False, "vault_path": ""}
    def _obs_save_config(e, p):          pass
    def _obs_export(vp, d=None):         return (False, "Obsidian module unavailable.")
    def _obs_auto_export():              return ""
    def _obs_detect_vault():             return ""
    def _obs_livestream(u, a, m=""):     pass

# ── Session Memory ─────────────────────────────────────────────────────────
try:
    from cursiv_v215.memory.session_log import (
        append_exchange   as _session_append,
        load_session_context as _load_session_ctx,
    )
    _SESSION_OK = True
except Exception:
    _SESSION_OK = False
    def _session_append(u, a, m="unknown"): pass
    def _load_session_ctx():                return ""

"""
Obsidian Vault Exporter — Cursiv v2.1.5

Reads today's training entries from .cursiv/training_data.jsonl and writes
a structured Markdown note to the Obsidian vault under {vault}/Cursiv/YYYY-MM-DD.md.

Notes include YAML frontmatter (Dataview-compatible), a summary table, and each
exchange formatted as a blockquote pair with quality score and source metadata.

Config: .cursiv/obsidian_config.json  →  {"enabled": bool, "vault_path": "..."}
"""
from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

ROOT            = Path(__file__).parent.parent.parent
CURSIV_DIR      = APP_DATA
CONFIG_FILE     = CURSIV_DIR / "obsidian_config.json"
TRAINING_JSONL  = CURSIV_DIR / "training_data.jsonl"
VAULT_SUBFOLDER = "Cursiv"


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": False, "vault_path": ""}


def save_config(enabled: bool, vault_path: str) -> None:
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"enabled": bool(enabled), "vault_path": (vault_path or "").strip()}, indent=2),
        encoding="utf-8",
    )


# ── Vault auto-detection ──────────────────────────────────────────────────────

def auto_detect_vault() -> str:
    """Scan common Windows locations for an Obsidian vault (contains .obsidian/)."""
    user = Path.home()
    search_roots = [
        user / "Documents",
        user / "OneDrive" / "Documents",
        user / "Desktop",
        user / "OneDrive" / "Desktop",
        user,
    ]
    for root in search_roots:
        if not root.exists():
            continue
        try:
            for child in sorted(root.iterdir()):
                if child.is_dir() and (child / ".obsidian").exists():
                    return str(child)
        except (PermissionError, OSError):
            pass
    return ""


# ── Training data reader ──────────────────────────────────────────────────────

def read_entries_for_date(target_date: date | None = None) -> list[dict]:
    """Return all training JSONL entries whose timestamp matches target_date."""
    if not TRAINING_JSONL.exists():
        return []
    if target_date is None:
        target_date = date.today()
    prefix  = target_date.isoformat()
    entries: list[dict] = []
    try:
        with TRAINING_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("timestamp", "").startswith(prefix):
                        entries.append(obj)
                except Exception:
                    pass
    except Exception:
        pass
    return entries


# ── Markdown builder ──────────────────────────────────────────────────────────

def _blockquote(text: str, max_chars: int = 1400) -> str:
    t = (text or "").strip()
    if len(t) > max_chars:
        t = t[:max_chars] + " …"
    if not t:
        return "> *(empty)*"
    return "\n".join("> " + ln for ln in t.splitlines())


def build_markdown(entries: list[dict], export_date: date) -> str:
    avg_q = round(sum(e.get("quality", 0.0) for e in entries) / len(entries), 2) if entries else 0.0

    sources: dict[str, int] = {}
    for e in entries:
        s = e.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    src_str = ", ".join(f"{s} ({n})" for s, n in sources.items())

    lines: list[str] = [
        "---",
        f"date: {export_date.isoformat()}",
        "system: Cursiv-v2.1.5",
        f"exchanges: {len(entries)}",
        f"quality_avg: {avg_q}",
        "tags:",
        "  - cursiv",
        "  - ai-training",
        "  - jwfrontierevocore",
        "---",
        "",
        f"# Cursiv Session — {export_date.strftime('%B %d, %Y')}",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Date | {export_date.isoformat()} |",
        f"| Exchanges logged | {len(entries)} |",
        f"| Avg quality score | {avg_q} |",
        f"| Sources | {src_str} |",
        "",
        "---",
        "",
        "## Exchanges",
        "",
    ]

    for i, e in enumerate(entries, 1):
        ts_raw = e.get("timestamp", "")
        try:
            ts_label = datetime.fromisoformat(ts_raw).strftime("%H:%M:%S")
        except Exception:
            ts_label = "--:--"

        prompt   = (e.get("prompt")   or "").strip()
        response = (e.get("response") or "").strip()
        quality  = e.get("quality", 0.0)
        source   = e.get("source", "unknown")

        lines += [
            f"### Exchange {i} — {ts_label}",
            "",
            "**Prompt**",
            "",
            _blockquote(prompt),
            "",
            "**Response**",
            "",
            _blockquote(response),
            "",
            f"*Quality: `{quality:.2f}` · Source: `{source}`*",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ── Export ────────────────────────────────────────────────────────────────────

def export_today(vault_path: str, target_date: date | None = None) -> tuple[bool, str]:
    """
    Write today's training entries as a Markdown note in the Obsidian vault.
    Overwrites any existing note for the same date (idempotent — safe to call repeatedly).
    Returns (success: bool, message: str).
    """
    if not (vault_path or "").strip():
        return False, "Vault path is empty — set the path in the Obsidian row."

    vpath = Path(vault_path.strip()).expanduser().resolve()
    if not vpath.exists():
        return False, f"Vault path not found: {vpath}"

    if target_date is None:
        target_date = date.today()

    entries = read_entries_for_date(target_date)
    if not entries:
        return True, f"No training entries for {target_date} yet — nothing to export."

    note_dir  = vpath / VAULT_SUBFOLDER
    note_dir.mkdir(parents=True, exist_ok=True)
    note_path = note_dir / f"{target_date.isoformat()}.md"

    md = build_markdown(entries, target_date)
    note_path.write_text(md, encoding="utf-8")

    avg_q = sum(e.get("quality", 0.0) for e in entries) / len(entries)
    return True, (
        f"Obsidian: exported {len(entries)} exchange(s) → "
        f"Cursiv/{target_date.isoformat()}.md  (avg quality {avg_q:.2f})"
    )


def auto_export_if_enabled() -> str:
    """
    Call this after saving a training entry.
    Silently no-ops when Obsidian sync is OFF.
    Returns a status string (empty string = sync is off).
    """
    cfg = load_config()
    if not cfg.get("enabled"):
        return ""
    vault_path = cfg.get("vault_path", "").strip()
    if not vault_path:
        return "Obsidian sync is ON but vault path is not configured."
    _ok, msg = export_today(vault_path)
    return msg


def livestream_exchange(user_msg: str, ai_msg: str, model: str = "unknown") -> None:
    """
    Append a single exchange to today's Obsidian live-session note immediately.
    Called after every completed exchange when Obsidian sync is ON.
    Creates the note with a header on first call of the day; appends thereafter.
    Silently no-ops when sync is OFF or vault path is invalid.
    """
    cfg = load_config()
    if not cfg.get("enabled"):
        return
    vault_path = (cfg.get("vault_path") or "").strip()
    if not vault_path:
        return

    vpath = Path(vault_path).expanduser().resolve()
    if not vpath.exists():
        return

    note_dir  = vpath / VAULT_SUBFOLDER
    note_dir.mkdir(parents=True, exist_ok=True)
    note_path = note_dir / f"{date.today().isoformat()}.md"

    if not note_path.exists():
        header_lines = [
            "---",
            f"date: {date.today().isoformat()}",
            "system: Cursiv-v2.1.5",
            "mode: livestream",
            "tags:",
            "  - cursiv",
            "  - ai-session",
            "  - jwfrontierevocore",
            "---",
            "",
            f"# Cursiv Live Session — {date.today().strftime('%B %d, %Y')}",
            "",
            "---",
            "",
        ]
        note_path.write_text("\n".join(header_lines), encoding="utf-8")

    ts    = datetime.now().strftime("%H:%M:%S")
    block = "\n".join([
        f"### {ts}",
        "",
        "**You:**",
        "",
        _blockquote(user_msg, max_chars=800),
        "",
        f"**{model}:**",
        "",
        _blockquote(ai_msg, max_chars=1200),
        "",
        "---",
        "",
    ])
    try:
        with note_path.open("a", encoding="utf-8") as f:
            f.write(block)
    except Exception:
        pass

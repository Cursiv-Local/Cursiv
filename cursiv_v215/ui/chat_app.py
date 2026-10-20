"""
Cursiv chat engine -- everything behind the desktop chat panel: building the
system prompt, routing to a model (paid keys, then Groq, Gemini, the local
Ollama model or Cursiv Cloud), saving and testing keys, tools, and memory
context. The desktop window (launcher/chat_panel.py, chat_commands.py) calls
into this module; it has no user interface of its own.
"""

from __future__ import annotations

import base64
import json
import os
import queue as _queue_mod
import subprocess
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Generator

from cursiv_v215.core import netgate   # installs the offline backstop; see core/netgate.py
from cursiv_v215.guardian.protected import is_protected_path as _guardian_protected

from cursiv_v215.chat.optional import (  # noqa: E402,F401  (moved; chat_app re-exports)
    _rate_limiter,
    _ScanDisplay,
    _scan,
    _RATE_OK,
    _codex_generate,
    _codex_available,
    _codex_status,
    _CODEX_OK,
    _hermes_run,
    _hermes_available,
    _hermes_status,
    _HERMES_OK,
    _ref_search,
    _ref_answer,
    _ref_available,
    _ref_status,
    _REF_OK,
    _sfed_export,
    _sfed_import,
    _sfed_summary,
    _SFED_OK,
    _strand_search,
    _strand_count,
    _STRAND_APP_OK,
    _queue_enqueue,
    _queue_format,
    _queue_count,
    _queue_flush,
    _QUEUE_OK,
    _obs_load_config,
    _obs_save_config,
    _obs_export,
    _obs_auto_export,
    _obs_detect_vault,
    _obs_livestream,
    _OBS_OK,
    _session_append,
    _load_session_ctx,
    _SESSION_OK,
)
# Session ID — stable per process, rotates on every server restart
_GRADIO_SESSION_ID = f"gradio_{os.getpid()}"

def _owner_active() -> bool:
    """True if owner is verified in any session (Gradio or CLI)."""
    return _is_owner_session(_GRADIO_SESSION_ID)

from cursiv_v215.chat.web_search import (  # noqa: E402,F401  (moved; chat_app re-exports)
    _wcache_get,
    _wcache_store,
    _wcache_evict,
    _WCACHE_OK,
    BRAVE_KEY,
    _SEARCH_TRIGGERS,
    _needs_search,
    _ddg_search,
    _brave_search,
    _web_search,
)
# ── Owner mode (guardian/owner.py): an owner code set at runtime, stored hashed ──
try:
    from cursiv_v215.guardian.owner import unlock_owner_session as _unlock_owner
    from cursiv_v215.guardian.owner import is_owner_session     as _is_owner_session
    from cursiv_v215.guardian.owner import verify_owner_code    as _verify_owner_code
    from cursiv_v215.guardian.owner import set_owner_code       as _set_owner_code
    from cursiv_v215.guardian.owner import owner_code_is_set    as _owner_code_is_set
except Exception:
    def _verify_owner_code(text: str) -> bool:
        return False
    def _unlock_owner(sid: str):
        pass
    def _is_owner_session(sid: str) -> bool:
        return False
    def _set_owner_code(code: str) -> None:
        raise RuntimeError("Owner code storage unavailable.")
    def _owner_code_is_set() -> bool:
        return False

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT               = Path(__file__).parent.parent.parent
SYSTEM_PROMPT_FILE = ROOT / "cursiv_v215" / "codex" / "system_prompt.md"
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)
MEMORY_FILE        = APP_DATA / "memory.json"
TRAINING_JSONL     = APP_DATA / "training_data.jsonl"

# ── xAI endpoint ───────────────────────────────────────────────────────────
XAI_URL        = "https://api.x.ai/v1/chat/completions"
XAI_MODEL      = "grok-3-latest"
XAI_MODEL_VIS  = "grok-2-vision-1212"   # vision-capable model for images
OLLAMA_URL         = "http://127.0.0.1:11434/api/generate"
OLLAMA_TAGS_URL    = "http://127.0.0.1:11434/api/tags"
OLLAMA_MODEL       = "qwen3:4b-instruct"
# Answers are limited by time, not length (see _time_boxed): the token cap is
# only a generous safety net so a thought is never cut off mid-sentence.
RESPONSE_MAX_TOKENS  = int(os.environ.get("CURSIV_MAX_TOKENS", "4096"))
# 0 = no time limit (the default -- thinking time made 90 s far too short).
RESPONSE_TIME_LIMIT  = float(os.environ.get("CURSIV_RESPONSE_SECONDS", "0"))
OLLAMA_CODE_PRIMARY   = "qwen2.5-coder:14b"    # primary coder — architecture + logic
OLLAMA_CODE_SECONDARY = "deepseek-coder-v2:16b" # critic/reviewer — debugging + synthesis

# ── OpenAI endpoint (Codex / code review) ──────────────────────────────────
OPENAI_URL         = "https://api.openai.com/v1/chat/completions"
OPENAI_CODE_MODEL  = "gpt-4.1"      # full code generation, not just review

# ── Anthropic / Claude endpoint ─────────────────────────────────────────────
ANTHROPIC_URL         = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION     = "2023-06-01"
ANTHROPIC_CODE_MODEL  = "claude-sonnet-4-6"   # code generation via Anthropic

# Sentinel that signals a write is pending user approval
WRITE_SENTINEL = "<<<PENDING_WRITE_JSON>>>"
# Sentinel yielded by a provider when its 429 retries are exhausted — triggers fallback
RATE_SENTINEL  = "<<<RATE_LIMIT_EXHAUSTED>>>"
# chat(replace_draft=True): the rest of this chunk replaces the reply shown so far
# (a draft the check revised). Only the desktop chat window asks for it.
REPLACE_SENTINEL = "<<<REPLACE_REPLY>>>"

def _cursiv_encode(text: str) -> str:
    """Encode text to Cursiv binary (space-separated 8-bit bytes)."""
    return ' '.join(f'{ord(c):08b}' for c in text if ord(c) < 256)

def _cursiv_decode(binary: str) -> str:
    """Decode Cursiv binary back to text."""
    try:
        return ''.join(chr(int(b, 2)) for b in binary.strip().split() if len(b) == 8)
    except Exception:
        return '[decode error]'

# ── Real-time web search (worldwide, zero API key required) ───────────────
import urllib.parse as _urlparse
import re as _re

# ── File tool definitions (xAI / OpenAI tool-call schema) ─────────────────
FILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file. Use this before editing so you know what's there.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path, relative to workspace root or absolute."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file, creating it or overwriting it completely. Always read_file first if editing an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string", "description": "File path to write."},
                    "content": {"type": "string", "description": "Full content to write to the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path. Defaults to workspace root."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a glob pattern (e.g. '**/*.py').",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern":   {"type": "string", "description": "Glob pattern."},
                    "directory": {"type": "string", "description": "Root directory to search from. Defaults to workspace root."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a directory (and all parents) at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file. Use with care — this is irreversible. Only delete files you created or that Josh explicitly asks you to remove.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to delete."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_plan",
            "description": (
                "REQUIRED first step before writing any files. "
                "Call this to submit your implementation plan. "
                "List every file you will create/edit, what each does, and the order of operations. "
                "This ensures clean, complete, one-shot delivery."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "Full implementation plan: goals, file list, step-by-step order.",
                    },
                },
                "required": ["plan"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "codex_generate",
            "description": (
                "Call the Winkler Codex AI to generate production-ready code or Cursiv agent packs. "
                "Use this when you need to write code — it produces a structured artifact with "
                "READY-TO-RUN CODE and JSON FILES in Joshua's exact style. "
                "Works offline. Call this before write_file for any non-trivial code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Describe what to build or generate. Be specific.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hermes_task",
            "description": (
                "Delegate a multi-step agentic task to the Hermes Agent running on Ollama (llama3.1). "
                "Use for: terminal commands, complex file operations, multi-step workflows, "
                "anything that needs a tool-calling loop. Works fully offline."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The task to delegate. Be specific about what you need done.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reference_brain",
            "description": (
                "Search the local offline knowledge base (382MB SQLite). "
                "Covers: Webster dictionary definitions, thesaurus, survival field knowledge, "
                "medical field notes, science and factbook data. "
                "No model or internet needed — always available offline."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to look up. Works for definitions, medical, survival, science.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["search", "answer"],
                        "description": "search = raw hits, answer = grounded full answer with intent classification.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "offline_queue",
            "description": (
                "Manage the offline task queue. Use action='add' to save a cloud-dependent task "
                "for later. Use action='list' to see what's queued. Use action='flush' to fire "
                "all queued tasks now (requires connection)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list", "flush"],
                        "description": "What to do with the queue.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The task to queue (required for action='add').",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags for the queued task (optional).",
                    },
                },
                "required": ["action"],
            },
        },
    },
]

# Anthropic tool format (same tools, different schema wrapper)
CLAUDE_TOOLS = [
    {
        "name":         t["function"]["name"],
        "description":  t["function"]["description"],
        "input_schema": t["function"]["parameters"],
    }
    for t in FILE_TOOLS
]


# ── Tool execution engine ──────────────────────────────────────────────────

def _resolve_path(raw: str, root: Path) -> Path | None:
    """Resolve a path safely within root. Returns None if it escapes the workspace."""
    try:
        p = Path(raw)
        resolved = p.resolve() if p.is_absolute() else (root / p).resolve()
        resolved.relative_to(root.resolve())   # raises ValueError if outside
        return resolved
    except (ValueError, Exception):
        return None


_BLOCKED_READ_PATHS = {
    ".cursiv/config.json",
    ".cursiv\\config.json",
    "secrets.bat",
}

def execute_tool(name: str, args: dict, root: Path) -> str:
    """Execute a file tool call. Returns a string result sent back to the model."""

    if name == "read_file":
        raw_path = args.get("path", "")
        if _scan:
            _scan.file_scan(raw_path)
        # Block credential files — keys must never be exposed via tool reads
        for blocked in _BLOCKED_READ_PATHS:
            if blocked.replace("\\", "/") in raw_path.replace("\\", "/"):
                return "Access denied: this file contains credentials and cannot be read via tools."
        path = _resolve_path(raw_path, root)
        if not path:
            return "Error: path is outside the workspace root. Only paths inside the workspace are allowed."
        if not path.exists():
            return f"Error: file not found: {path}"
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            lines   = content.splitlines()
            numbered = "\n".join(f"{i+1:4d}  {ln}" for i, ln in enumerate(lines))
            if len(numbered) > 12000:
                numbered = numbered[:12000] + f"\n... [truncated — {len(lines)} lines total]"
            return f"File: {path}\nLines: {len(lines)}\n\n{numbered}"
        except Exception as e:
            return f"Error reading {path}: {e}"

    elif name == "write_file":
        path    = _resolve_path(args.get("path", ""), root)
        content = args.get("content", "")
        if not path:
            return "Error: path is outside the workspace root."
        if _guardian_protected(args.get("path", "")):
            return "Error: write blocked — Cursiv never lets the AI change its keys, logins or protection files."
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.write_text(content, encoding="utf-8")
            return f"{'Updated' if existed else 'Created'}: {path}  ({len(content.splitlines())} lines, {len(content)} chars)"
        except Exception as e:
            return f"Error writing {path}: {e}"

    elif name == "list_directory":
        if _scan:
            _scan.dir_scan(args.get("path", ".") or ".")
        raw  = args.get("path", ".")
        path = _resolve_path(raw, root) if raw and raw != "." else root
        if not path:
            return "Error: path is outside the workspace root."
        if not path.exists():
            return f"Error: directory not found: {path}"
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:150]
            lines   = [f"Directory: {path}", ""]
            for e in entries:
                tag  = "DIR " if e.is_dir() else "    "
                size = f"  {e.stat().st_size:>8,} B" if e.is_file() else ""
                lines.append(f"{tag} {e.name}{size}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listing {path}: {e}"

    elif name == "search_files":
        if _scan:
            _scan.dir_scan(args.get("directory", ".") or ".")
        pattern   = args.get("pattern", "*")
        dir_raw   = args.get("directory", ".")
        base      = _resolve_path(dir_raw, root) if dir_raw and dir_raw != "." else root
        if not base:
            base = root
        try:
            matches = sorted(base.glob(pattern))[:80]
            if not matches:
                return f"No files matching '{pattern}' in {base}"
            lines = [f"Found {len(matches)} match(es) for '{pattern}' in {base}:", ""]
            for m in matches:
                try:
                    rel = m.relative_to(root)
                except ValueError:
                    rel = m
                tag = "DIR " if m.is_dir() else "    "
                lines.append(f"{tag} {rel}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching: {e}"

    elif name == "create_directory":
        path = _resolve_path(args.get("path", ""), root)
        if not path:
            return "Error: path is outside the workspace root."
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"Created directory: {path}"
        except Exception as e:
            return f"Error creating directory: {e}"

    elif name == "delete_file":
        path = _resolve_path(args.get("path", ""), root)
        if not path:
            return "Error: path is outside the workspace root."
        if not path.exists():
            return f"File not found (already gone?): {path}"
        try:
            path.unlink()
            return f"Deleted: {path}"
        except Exception as e:
            return f"Error deleting {path}: {e}"

    elif name == "submit_plan":
        plan = args.get("plan", "").strip()
        if not plan:
            return "Plan acknowledged (empty). Please provide a detailed plan next time."
        return f"Plan accepted:\n{plan}\n\nProceed with implementation."

    elif name == "codex_generate":
        prompt = args.get("prompt", "").strip()
        if not prompt:
            return "Error: codex_generate requires a 'prompt' argument."
        if not _CODEX_OK or not _codex_available():
            return "[Codex Agent not available — generate the code directly instead.]"
        return _codex_generate(prompt)

    elif name == "hermes_task":
        prompt = args.get("prompt", "").strip()
        if not prompt:
            return "Error: hermes_task requires a 'prompt' argument."
        if not _HERMES_OK or not _hermes_available():
            return "[Hermes Agent not available — ensure hermes-agent is a sibling directory to Cursiv-v3 and Ollama is running.]"
        return _hermes_run(prompt)

    elif name == "reference_brain":
        query = args.get("query", "").strip()
        if not query:
            return "Error: reference_brain requires a 'query' argument."
        if not _REF_OK or not _ref_available():
            return "[Reference Brain not available — Codex system SQLite not found.]"
        mode = args.get("mode", "search")
        return _ref_answer(query) if mode == "answer" else _ref_search(query)

    elif name == "offline_queue":
        action = args.get("action", "list")
        if action == "add":
            prompt = args.get("prompt", "").strip()
            if not prompt:
                return "Error: offline_queue add requires a 'prompt'."
            tags = [t.strip() for t in args.get("tags", "").split(",") if t.strip()]
            entry = _queue_enqueue(prompt, tags=tags)
            return f"Queued: {entry['id']} — '{prompt[:60]}'"
        elif action == "flush":
            results = _queue_flush(lambda p: "[flush requires active connection]")
            return f"Flushed {len(results)} task(s)." if results else "Queue empty."
        else:
            return _queue_format()

    return f"Unknown tool: {name}"

# ── Owner reveal ──────────────────────────────────────────────────────────

def _build_owner_reveal() -> str:
    return ("Owner mode is on for this session: builder tools are listed in help "
            "(help builder), and file tools treat you as the owner.")


def _compact_system_for_tools(is_owner: bool = False) -> str:
    """
    Minimal system prompt used in tool-use loops to stay under rate limits.
    The full 47KB codex is skipped — Claude reads files with tools instead.
    """
    base = (
        "You are Cursiv, a personal assistant created by "
        "Joshua Winkler. The person using this copy owns it. You have file-system access via tools. "
        "Always call submit_plan before writing files. "
        "Read files before editing them. Write complete, working code — no stubs. "
        "Human approval is required before any system change is applied. "
        "Be direct, honest, and technically precise."
    )
    if is_owner:
        base += (
            "\n\nOwner mode: the owner of this copy is verified. "
            "Answer questions about how Cursiv works fully and honestly."
        )
    return base


def _build_strand_context(query: str, top_k: int = 2) -> str:
    """Memory for the system prompt: the person's facts and related earlier
    conversations, matched by meaning (memory/semantic.py). Falls back to the
    keyword search over Strands if semantic memory isn't available."""
    try:
        from cursiv_v215.memory import semantic as _sem
        ctx = _sem.build_context(query)
        if ctx:
            global _MEMORY_RECALLED, _MEMORY_CTX
            _MEMORY_RECALLED = True
            _MEMORY_CTX = ctx
            # the memories themselves, so the source line names them only if the answer used them
            _MEMORY_TEXTS[:] = [_re.sub(r"^- (?:\[[^\]]*\] )?", "", ln).strip()
                                for ln in ctx.splitlines() if ln.startswith("- ")]
            return ctx
    except Exception:
        pass
    if not _STRAND_APP_OK or _strand_count() == 0:
        return ""
    try:
        results = _strand_search(query, top_k=top_k, min_score=0.12)
        if not results:
            return ""
        lines = ["Related earlier conversations the person saved:"]
        for s in results:
            territory = s.get("territory_tag", "general")
            q_text    = s.get("query", "")[:150]
            synth     = s.get("synthesis", "")[:350]
            lines.append(f"\n[{territory}] Prior query: {q_text}\nPrior insight: {synth}")
        return "\n".join(lines)
    except Exception:
        return ""


def _build_live_status() -> str:
    """What's actually available right now, appended to the system prompt so the
    model doesn't claim features that aren't installed or turned on."""
    version = "3.14"
    try:
        _vfile = ROOT / "launcher" / "cursiv_launcher.py"
        if _vfile.exists():
            import re as _re_v
            _m = _re_v.search(r'_CURRENT_VERSION\s*=\s*"([^"]+)"', _vfile.read_text(encoding="utf-8"))
            if _m:
                version = _m.group(1)
    except Exception:
        pass

    items = []
    if _CODEX_OK and _codex_available():
        items.append("Coding help (codex): local coding models installed")
    elif _CODEX_OK:
        items.append("Coding help (codex): local coding models not downloaded yet")
    try:
        import cursiv_v215.agents.babel_agent  # noqa: F401
        items.append("Translation: translate <text> into <language>")
    except Exception:
        pass
    if _REF_OK and _ref_available():
        items.append("Local reference data: ref <question>")
    if netgate.is_offline():
        items.append("Offline mode is ON: no web search, no cloud AI")
    else:
        items.append("Web search: only when the message starts with search:"
                     + (" (automatic search is also on)" if netgate.web_search_auto() else ""))
    if _STRAND_APP_OK:
        sc = _strand_count()
        items.append(f"Saved notes: {sc}")

    lines = ["\n\n---", f"## Available right now (Cursiv {version})",
             "For your reference only: don't mention these unless the person asks what you can do.", ""]
    lines += [f"- {t}" for t in items]
    return "\n".join(lines)


def load_system_prompt() -> str:
    base = (
        SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        if SYSTEM_PROMPT_FILE.exists()
        else (
            "You are Cursiv, a personal assistant running on this person's own computer. "
            "Be warm, direct and truthful."
        )
    )
    return base + _build_live_status()


def load_vault_context() -> str:
    """Inject PiForge phase agent knowledge from vault into every conversation."""
    registry_path = APP_DATA / "agent_registry.json"
    vault_dir     = APP_DATA / "vault"
    if not registry_path.exists():
        return ""
    try:
        registry    = json.loads(registry_path.read_text(encoding="utf-8"))
        agents_meta = registry.get("agents", {})
        if not agents_meta:
            return ""

        lines = ["\n\n---\n## PIFORGE PHASE INTELLIGENCE (vault-active)\n"]

        for agent_id, meta in list(agents_meta.items())[:14]:
            agent_dir = vault_dir / agent_id
            versions  = sorted(agent_dir.glob("v*.json")) if agent_dir.exists() else []
            if not versions:
                continue
            try:
                data = json.loads(versions[-1].read_text(encoding="utf-8"))
            except Exception:
                continue

            km          = data.get("knowledge_map", {})
            name        = data.get("name", meta.get("name", "?"))
            domain      = km.get("domain", "")
            directive   = (km.get("core_directive") or "")[:150].replace("\n", " ")
            translation = (km.get("cursive_v2_translation") or "")[:150].replace("\n", " ")

            lines.append(f"**{name}** [{domain}]: {directive}")
            if translation:
                lines.append(f"  V2: {translation}")

        lines.append("\n---")
        return "\n".join(lines)
    except Exception:
        return ""


# ── File processing ────────────────────────────────────────────────────────

def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Could not read {path.name}: {e}]"


def process_uploaded_files(files: list | None) -> tuple[str, list[dict]]:
    """
    Returns (text_context, image_parts).
    text_context: injected into system prompt.
    image_parts: list of xAI image_url dicts for vision calls.
    """
    if not files:
        return "", []

    text_chunks  = []
    image_parts  = []
    text_exts    = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                    ".json", ".yaml", ".yml", ".csv", ".xml", ".toml", ".bat", ".sh"}
    image_exts   = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

    for f in files:
        p = Path(f if isinstance(f, str) else f.name)

        if p.suffix.lower() in image_exts:
            try:
                raw     = p.read_bytes()
                b64     = base64.b64encode(raw).decode()
                mime    = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                           ".png": "image/png",  ".gif":  "image/gif",
                           ".webp": "image/webp"}.get(p.suffix.lower(), "image/png")
                image_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
                text_chunks.append(f"[Image uploaded: {p.name}]")
            except Exception as e:
                text_chunks.append(f"[Image {p.name} could not be processed: {e}]")

        elif p.suffix.lower() in text_exts:
            content = _read_text_file(p)
            cap     = 8000
            if len(content) > cap:
                content = content[:cap] + f"\n... [truncated at {cap} chars]"
            text_chunks.append(f"\n### Uploaded file: {p.name}\n```\n{content}\n```")

        elif p.suffix.lower() == ".pdf":
            text_chunks.append(
                f"[PDF uploaded: {p.name} — PDF parsing not installed. "
                "Install pypdf and I can extract the text automatically.]"
            )
        else:
            try:
                content = _read_text_file(p)[:4000]
                text_chunks.append(f"\n### Uploaded file: {p.name}\n```\n{content}\n```")
            except Exception:
                text_chunks.append(f"[File uploaded: {p.name} — binary, cannot display as text]")

    return "\n".join(text_chunks), image_parts


# ── LLM callers ───────────────────────────────────────────────────────────

def _call_ollama_raw(messages: list[dict], max_tokens: int = RESPONSE_MAX_TOKENS,
                     standard: bool = False) -> Generator[str, None, None]:
    """Stream from local Ollama with full system prompt injection."""
    import json as _json

    # Separate system instructions from conversation turns.
    # Ollama's /api/generate accepts a dedicated `system` field — using it
    # properly grounds the model in the Cursiv identity and capabilities.
    from cursiv_v215.core import speed as _speed
    # Small GPUs: the CPU reads the whole prompt before the first word, so send the
    # compact persona + what fits (the full one took up to a minute on a 4 GB card).
    messages = _slim(messages, 14000 if _speed.small_gpu() else 48000)
    system_parts = [
        m["content"] for m in messages
        if m.get("role") == "system" and isinstance(m.get("content"), str)
    ]
    system_str = _IDENTITY_OVERRIDE + "\n\n".join(system_parts)

    # Build conversation prompt from user/assistant turns only.
    turns = "\n".join(
        f"{'Human' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    )

    if not _ensure_ollama():
        yield "\n[Ollama not found. Install from https://ollama.com then run: ollama pull llama3.1]"
        return
    if _ollama_tags() is None:
        yield "\n[Ollama unavailable: it isn't responding right now -- it may be busy downloading a model. Try again in a minute.]"
        return
    model = _resolve_ollama_model(standard)
    if model is None and _models_on_disk():
        # Seen for real: Ollama started with the wrong settings mid-reinstall and
        # listed nothing while 22 GB of models sat on disk. Re-downloading won't help.
        yield ("\n[Ollama is running but can't see your downloaded models. Restart it: open Cursiv's "
               "Setup window and click Restart Ollama (or quit Ollama from its tray icon and open it again).]")
        return
    if model is None:
        # Ollama is running but has no models at all -- download the default
        # once (progress shown in the reply) instead of failing with a 404.
        yield from _pull_ollama_model(_speed.chat_model_prefs()[0])
        model = _resolve_ollama_model(standard)
        if model is None:
            yield f"\n[No local model available. Run: ollama pull {_speed.chat_model_prefs()[0]}]"
            return
    if _speed.gpu_options(model):
        _speed.make_room(model)                 # one model on a small card at a time
    deep = not standard and model == _speed.DEEP_THINK_MODEL and _speed.deep_think_on()
    if deep:
        yield "*(Deep Think: working it through first. On this computer that can take a minute or two.)*\n\n"
        max_tokens += _speed.DEEP_THINK_EXTRA_TOKENS
    payload = json.dumps({
        "model": model,
        "system": system_str,
        "prompt": turns,
        "stream": True,
        "keep_alive": _speed.keep_alive(),        # stay loaded: a cold load took ~100 s (2 min on battery saver)
        **_speed.think_options(model, deep),      # Deep Think's reasoning comes back separately, not in "response"
        "options": {
            "num_predict": max_tokens,
            "num_ctx": _speed.num_ctx(),
            **_speed.gpu_options(model),
        },
    }).encode()
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(OLLAMA_URL, data=payload,
                                         headers={"Content-Type": "application/json"})
            # 600 s: loading a model that doesn't fit the GPU can take ~2 minutes
            with urllib.request.urlopen(req, timeout=600) as resp:
                for line in resp:
                    chunk = _json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
            return
        except Exception as e:
            # More layers on the card than it has room for right now (another program
            # using it): once more with Ollama's own split.
            if attempt == 1 and _speed.gpu_options(model):
                _speed.gpu_fallback(model)
                body = _json.loads(payload)
                body["options"].pop("num_gpu", None)
                payload = json.dumps(body).encode()
                continue
            yield f"\n[Ollama unavailable: {e}]"
            return


def _call_ollama(messages: list[dict], max_tokens: int = RESPONSE_MAX_TOKENS,
                 standard: bool = False) -> "Generator[str, None, None]":
    yield from _call_ollama_raw(messages, max_tokens, standard)


def _ollama_running() -> bool:
    try:
        urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=2)
        return True
    except Exception:
        return False


def _ensure_ollama() -> bool:
    """Start Ollama in the background if it isn't running. Returns True once reachable."""
    if _ollama_running():
        return True

    from cursiv_v215.core import ollama_host as _host
    if not _host.installed():
        return False  # not installed — nothing to start
    try:
        from cursiv_v215.core import speed as _speed
        return _host.start(_speed.ollama_env(), wait=15)   # (60 s on a USB); flash attention + compact cache
    except Exception:
        return False


def _ollama_pulled_models() -> set[str]:
    """Return set of model name tags currently pulled in Ollama."""
    try:
        req = urllib.request.Request(OLLAMA_TAGS_URL)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        names = set()
        for m in data.get("models", []):
            tag = m.get("name", "")
            names.add(tag)
            names.add(tag.split(":")[0])
        return names
    except Exception:
        return set()


# Preference order when OLLAMA_MODEL isn't pulled: the owner's own fine-tuned
# model first (training/ollama_merge.py), then its base, then anything else.
_OLLAMA_FALLBACK_MODELS = ("cursiv-tuned", "qwen2.5:1.5b", "qwen2.5")


def _ollama_tags() -> list[str] | None:
    """Installed model tags, or None if Ollama didn't answer (busy or not running).
    A slow Ollama -- e.g. while it downloads another model -- must not look like
    'no models installed'."""
    for timeout in (8, 20):
        try:
            with urllib.request.urlopen(urllib.request.Request(OLLAMA_TAGS_URL), timeout=timeout) as resp:
                return [m.get("name", "") for m in json.loads(resp.read().decode()).get("models", [])]
        except Exception:
            continue
    return None


def _models_on_disk() -> bool:
    """True if Ollama's model folder holds downloaded models (whether or not the
    running Ollama currently lists them)."""
    base = Path(os.environ.get("OLLAMA_MODELS") or (Path.home() / ".ollama" / "models"))
    lib = base / "manifests" / "registry.ollama.ai" / "library"
    try:
        return any(lib.iterdir())
    except Exception:
        return False


def _resolve_ollama_model(standard: bool = False) -> str | None:
    """Pick an installed Ollama model for general chat, or None if none are pulled.
    standard: the everyday model even when Deep Think is on (checks, background jobs)."""
    tags = _ollama_tags()
    if tags is None:
        return None
    available = set(tags) | {t.split(":")[0] for t in tags}
    from cursiv_v215.core import speed as _speed
    if not standard and _speed.deep_think_on() and _speed.DEEP_THINK_MODEL in available:
        return _speed.DEEP_THINK_MODEL
    _chosen = _saved_key("chat_model") if _saved_key("show_all_models") == "on" else ""   # Advanced menu pick
    if _chosen and _chosen in available and not (standard and _chosen == _speed.DEEP_THINK_MODEL):
        return _chosen
    # Fastest good model for this GPU first (e.g. a 3B model on a 4 GB card), if installed
    for name in (*_speed.chat_model_prefs(), OLLAMA_MODEL, *_OLLAMA_FALLBACK_MODELS):
        if name in available:
            return name
    # Anything else that isn't an embedding-only model
    for tag in tags:
        if tag and "embed" not in tag.lower():
            return tag
    return None


def _pull_ollama_model(model: str) -> Generator[str, None, None]:
    """Download a model through Ollama's API, yielding short progress lines."""
    if not netgate.allowed():
        yield (f"\n[No local model installed yet, and offline mode is on, so {model} can't be "
               "downloaded. Type 'offline off' to allow it.]\n")
        return
    yield f"\n[No local model installed yet -- downloading {model} (one-time setup, a few GB)...]\n"
    last_pct = -10
    try:
        req = urllib.request.Request(
            OLLAMA_URL.replace("/api/generate", "/api/pull"),
            data=json.dumps({"name": model, "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3600) as resp:
            for line in resp:
                try:
                    status = json.loads(line.decode())
                except Exception:
                    continue
                if status.get("error"):
                    yield f"[Download failed: {status['error']}]\n"
                    return
                total, done = status.get("total"), status.get("completed")
                if total and done:
                    pct = int(done * 100 / total)
                    if pct >= last_pct + 10:
                        last_pct = pct
                        yield f"[{model}: {pct}%]\n"
                if status.get("status") == "success":
                    yield f"[{model} ready.]\n\n"
                    return
    except Exception as e:
        yield f"[Download failed: {e}]\n"


# ── Free providers: the user's own Gemini / Groq keys, and Cursiv Cloud ─────
# Gemini and Groq both have free tiers (FREE_KEY_HELP). Their keys live in the
# same .cursiv/config.json as the other keys ("gemini_key", "groq_key").
# Cursiv Cloud is the owner's Cloudflare Worker (cloudflare/worker.js); the
# provider keys stay on the server, and the app only sends the conversation.

GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Several fallbacks: the newest model is often "high demand" (503) on free keys.
GEMINI_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite")
GEMINI_TIMEOUT = 20          # per model; overloaded models hang rather than refuse
_GEMINI_DOWN: dict[str, float] = {}   # model -> time until which it's skipped (timed out / 503)
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "qwen/qwen3.8-27b"
GROQ_MODELS  = (GROQ_MODEL, "openai/gpt-oss-120b", "openai/gpt-oss-20b")
# Prompt budgets (characters). Groq's free tier rejects big requests (413);
# smaller prompts are also simply faster everywhere.
GROQ_BUDGET   = 18000
GEMINI_BUDGET = 60000
CURSIV_CLOUD_URL = os.environ.get("CURSIV_CLOUD_URL", "https://cursiv.winklers-llc.com/api/cursiv/chat")

FREE_KEY_HELP = """\
FREE AI KEYS -- no credit card, about 2 minutes each. Add one or both.

GOOGLE GEMINI  (the most generous free tier)
  1. Open https://aistudio.google.com/apikey
  2. Sign in with any Google account and accept the terms
  3. Click "Create API key" (pick any project, or let it make one)
  4. Copy the key (it usually starts with AIza or AQ)
  5. In Cursiv, type:   gemini <your key>

GROQ  (very fast)
  1. Open https://console.groq.com/keys
  2. Sign up with Google, GitHub or email
  3. Click "Create API Key", give it any name, then Submit
  4. Copy the key right away -- it starts with gsk_ and is shown only once
  5. In Cursiv, type:   groq gsk_...your key...

Cursiv tests each key when you add it, and uses them whenever your other
providers aren't available -- including in the council. Keys are saved only on
this computer. To remove one:  gemini off  /  groq off
"""

# Saved keys: cursiv_v215/chat/keys.py (encrypted for this Windows account).
from cursiv_v215.chat.keys import saved_key as _saved_key, store_key as _store_key  # noqa: E402
_CLOUD_FILE    = Path.home() / ".cursiv" / "cursiv_cloud.json"


def _text_messages(messages: list[dict]) -> list[dict]:
    """Plain-text copy of a message list (image parts dropped)."""
    out = []
    for m in messages:
        c = m.get("content")
        if not isinstance(c, str):
            c = next((p.get("text", "") for p in (c or []) if isinstance(p, dict) and p.get("type") == "text"), "")
        out.append({"role": m.get("role", "user"), "content": c})
    return out


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    netgate.require("Cloud AI")
    # A real User-Agent: Groq's API sits behind Cloudflare, which blocks Python's
    # default "Python-urllib" agent outright (HTTP 403, error code 1010).
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "Cursiv-Desktop/3.14", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


_FULL_PERSONA = ""   # the full persona prefix of the current system prompt (set in _chat_inner)


def _slim(messages: list[dict], budget: int) -> list[dict]:
    """Compact persona + newest turns that fit `budget` characters (core/speed.py)."""
    from cursiv_v215.core import speed
    return speed.slim_messages(_text_messages(messages), budget, _FULL_PERSONA,
                               speed.compact_persona(SYSTEM_PROMPT_FILE))


def _call_gemini_direct(messages: list[dict], key: str, max_tokens: int = RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    msgs = _slim(messages, GEMINI_BUDGET)
    system = "\n\n".join(m["content"] for m in msgs if m["role"] == "system")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in msgs if m["role"] in ("user", "assistant") and m["content"]]
    payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    last_err = ""
    import time as _t
    now = _t.time()
    order = [m for m in GEMINI_MODELS if _GEMINI_DOWN.get(m, 0) < now] or list(GEMINI_MODELS[-1:])
    for model in order:
        url = GEMINI_URL.format(model=model)
        body = payload
        if "lite" in model:   # the fast fallback: skip "thinking" (4 s instead of 30 s)
            body = {**payload, "generationConfig": {**payload["generationConfig"], "thinkingConfig": {"thinkingBudget": 0}}}
        for use_query in (False, True):    # header first; some newer keys only work as ?key=
            try:
                if use_query:
                    data = _post_json(f"{url}?key={urllib.parse.quote(key)}", body, {}, GEMINI_TIMEOUT)
                else:
                    data = _post_json(url, body, {"x-goog-api-key": key}, GEMINI_TIMEOUT)
                cand = (data.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                if text.strip():
                    yield text
                    return
                last_err = f"empty reply ({cand.get('finishReason', 'no text')})"
                break
            except urllib.error.HTTPError as e:
                last_err = f"{e.code}: {e.read().decode(errors='ignore')[:200]}"
                if e.code in (401, 403) and not use_query:
                    continue        # try the same model with ?key=
                if e.code in (404, 429, 500, 503):
                    _GEMINI_DOWN[model] = _t.time() + (3600 if e.code == 404 else 600)
                break               # 404/429/5xx: next model
            except Exception as e:
                last_err = str(e)
                if "timed out" in last_err.lower():
                    _GEMINI_DOWN[model] = _t.time() + 600     # overloaded: skip it for 10 minutes
                break
        if last_err[:3] in ("400", "401", "403"):
            break                   # bad key or request -- another model won't help
    yield f"\n[Gemini error {last_err}]"


def check_free_key(field: str, key: str) -> tuple[bool, str]:
    """Is this Gemini/Groq key valid? Lists the provider's models -- costs no
    tokens, and doesn't depend on a model's reply (newer Gemini models can
    spend a tiny test budget on thinking and return nothing)."""
    def get(url: str, headers: dict) -> None:
        req = urllib.request.Request(url, headers={"User-Agent": "Cursiv-Desktop/3.14", **headers})
        with urllib.request.urlopen(req, timeout=20) as r:
            r.read(200)
    try:
        if field == "gemini_key":
            base = "https://generativelanguage.googleapis.com/v1beta/models"
            try:
                get(base, {"x-goog-api-key": key})
            except urllib.error.HTTPError as e:
                if e.code not in (400, 401, 403):
                    raise
                get(f"{base}?key={urllib.parse.quote(key)}", {})
        else:
            get("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {key}"})
        # The key is valid -- now prove chat works (a valid key can still fail in chat).
        import time as _t
        t0 = _t.time()
        msgs = [{"role": "system", "content": "Reply in five words or fewer."},
                {"role": "user", "content": "Say hello."}]
        fn = _call_gemini_direct if field == "gemini_key" else _call_groq_direct
        out = "".join(fn(msgs, key, 64)).strip()
        if not out or out.startswith("["):
            return False, ("Key is valid, but chat failed: " + out.strip("[]"))[:220]
        return True, f"Working — answered in {_t.time() - t0:.1f}s."
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8", "ignore")).get("error", {})
            detail = detail.get("message", "") if isinstance(detail, dict) else str(detail)
        except Exception:
            detail = ""
        return False, f"{e.code}: {detail or 'rejected'}"[:220]
    except Exception as e:
        return False, f"couldn't reach the provider: {e}"[:220]


def _call_groq_direct(messages: list[dict], key: str, max_tokens: int = RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    """Groq: very fast. Free-tier limits are per model, so on "too large" (413) or
    "rate limited" (429) try a smaller prompt, then the next model."""
    last = ""
    for model in GROQ_MODELS:
        for budget, cap in ((GROQ_BUDGET, max_tokens), (GROQ_BUDGET // 2, min(max_tokens, 2048))):
            try:
                data = _post_json(GROQ_URL, {"model": model, "messages": _slim(messages, budget),
                                             "max_tokens": cap},
                                  {"Authorization": f"Bearer {key}"}, 60)
                text = data["choices"][0]["message"].get("content") or ""
                if text.strip():
                    yield text
                    return
                last = "empty reply"
                break
            except urllib.error.HTTPError as e:
                last = f"{e.code}: {e.read().decode(errors='ignore')[:160]}"
                if e.code in (401, 403):
                    yield f"\n[Groq error {last}]"
                    return
                if e.code == 413:
                    continue        # same model, smaller request
                break               # 429/5xx/404: next model
            except Exception as e:
                last = str(e)
                break
    yield f"\n[Groq error {last}]"


def _cloud_settings() -> dict:
    try:
        data = json.loads(_CLOUD_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    changed = False
    if "enabled" not in data:
        data["enabled"] = False      # off until the person ticks it in Setup / Settings or types 'cloud on'
        changed = True
    if not data.get("install_id"):
        import uuid as _uuid
        data["install_id"] = str(_uuid.uuid4())
        changed = True
    if changed:
        _save_cloud_settings(data)
    return data


def _save_cloud_settings(data: dict) -> None:
    try:
        _CLOUD_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CLOUD_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def cloud_enabled() -> bool:
    # Off unless the person turns it on (Setup / Settings / "cloud on"): it sends
    # their messages to cursiv.winklers-llc.com. Never while offline mode is on.
    return netgate.allowed() and bool(_cloud_settings().get("enabled", False))


def set_cloud_enabled(on: bool) -> None:
    data = _cloud_settings()
    data["enabled"] = bool(on)
    _save_cloud_settings(data)


def _call_cursiv_cloud(messages: list[dict], max_tokens: int = RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    settings = _cloud_settings()
    try:
        data = _post_json(CURSIV_CLOUD_URL, {"messages": _text_messages(messages), "max_tokens": max_tokens},
                          {"X-Cursiv-Install": settings["install_id"], "User-Agent": "Cursiv-Desktop"}, 90)
        text = data.get("reply", "")
        if not text.strip():
            yield "\n[Cursiv Cloud error: empty reply]"
            return
        if not settings.get("notice_shown"):
            settings["notice_shown"] = True
            _save_cloud_settings(settings)
            yield ("*[No local model was ready, so this answer came from Cursiv Cloud (free, sent to "
                   "cursiv.winklers-llc.com). Type 'cloud off' to keep everything on this computer.]*\n\n")
        yield text
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            detail = ""
        yield f"\n[Cursiv Cloud error {e.code}: {detail or 'unavailable'}]"
    except Exception as e:
        yield f"\n[Cursiv Cloud error: {e}]"


def free_key_command(text: str) -> str | None:
    """Shared by the chat window and the terminal: 'gemini <key>', 'groq <key>',
    'cloud on|off|status', 'free keys'. Returns the reply, or None if not one of these."""
    t = text.strip()
    cmd = t.lower()
    if cmd in ("free keys", "free key", "keys free"):
        return FREE_KEY_HELP
    # Prefixes are only hints: providers change key formats (Google issues both
    # "AIza..." and newer "AQ..." Gemini keys), so the live test call decides.
    for name, field, prefixes, fn in (("gemini", "gemini_key", ("AIza", "AQ"), _call_gemini_direct),
                                      ("groq", "groq_key", ("gsk_",), _call_groq_direct)):
        if cmd == name:
            return f"Usage: {name} <key>   ({'set' if _saved_key(field) else 'no key set'})\n\n" + FREE_KEY_HELP
        if cmd.startswith(name + " "):
            key = t[len(name) + 1:].strip()
            if key.lower() in ("off", "remove", "clear"):
                _store_key(field, "")
                return f"{name.title()} key removed."
            if len(key) < 20 or " " in key:
                return f"That doesn't look like a whole {name.title()} key -- copy the full key and try again.\n\n" + FREE_KEY_HELP
            ok, reply = check_free_key(field, key)
            if not ok:
                hint = "" if key.startswith(prefixes) else (
                    f"\n(Most {name.title()} keys start with {' or '.join(prefixes)} -- make sure you copied the API key itself.)")
                return (f"{name.title()} key NOT saved -- the test call failed: {reply.strip()}\n"
                        f"Check that you copied the whole key, then try again.{hint}")
            _store_key(field, key)
            return f"{name.title()} key saved and working. Cursiv will use it when your other providers aren't available."
    if cmd in ("cloud", "cloud status"):
        if netgate.is_offline():
            return f"Cursiv Cloud isn't used while offline mode is on. {netgate.OFFLINE_MESSAGE}"
        on = cloud_enabled()
        return (f"Cursiv Cloud is {'ON' if on else 'OFF'}. "
                + ("It answers only when no local model is ready (Ollama not installed or no model yet), "
                   "through cursiv.winklers-llc.com. Type 'cloud off' to keep everything on this computer."
                   if on else "Everything stays on this computer. Type 'cloud on' to allow it as a backup."))
    if cmd in ("cloud on", "cloud off"):
        set_cloud_enabled(cmd == "cloud on")
        return ("Cursiv Cloud ON -- used only when no local model is ready."
                if cmd == "cloud on" else "Cursiv Cloud OFF -- nothing is sent to the cloud unless you add your own keys.")
    return None


def _local_llm(messages: list[dict], max_tokens: int) -> str:
    """One call to the local model. "" on an error."""
    # The answer check and background jobs use the fast Standard model, even in Deep Think.
    out = "".join(c for c in _call_ollama(messages, max_tokens=max_tokens, standard=True) if c != RATE_SENTINEL).strip()
    return "" if out.startswith(("[Ollama", "\n[Ollama")) else out


def _free_key_llm(messages: list[dict], max_tokens: int) -> str:
    """The user's own free Groq/Gemini key. Only for when no local model is ready."""
    if not netgate.allowed():
        return ""
    for field, fn in (("groq_key", _call_groq_direct), ("gemini_key", _call_gemini_direct)):
        key = _saved_key(field)
        if key:
            out = "".join(fn(messages, key, max_tokens)).strip()
            if out and not out.startswith(("[Groq error", "[Gemini error")):
                return out
    return ""


def _quick_llm(messages: list[dict], max_tokens: int = 400) -> str:
    """Small background jobs (memory learning, titles): the local model when one is
    ready, else the user's free Groq/Gemini key. A local model that fails does not
    fall back to the cloud. Never paid keys and never Cursiv Cloud. "" if none."""
    if _ollama_running() and _resolve_ollama_model():
        from cursiv_v215.core import speed as _speed
        if not _speed.wait_idle(300):      # never compete with a chat for the local model
            return ""
        return _local_llm(messages, max_tokens)
    return _free_key_llm(messages, max_tokens)


def _local_model_ready() -> bool:
    """Ollama is installed, running (started if needed) and has a chat model."""
    return _ensure_ollama() and _resolve_ollama_model() is not None


# Error/placeholder chunks the cloud callers yield instead of raising.
_PROVIDER_ERROR_PREFIXES = ("[xAI auth error", "[Claude error", "[OpenAI error", "[Gemini error", "[Groq error",
                            "[Cursiv Cloud error", "[Ollama unavailable", "[Ollama not found", "[Ollama is running")


# ── Cursiv's own status lines ──────────────────────────────────────────────
# Notes like "*(Checked on this computer: …)*", "*[Gemini unavailable — Ollama]*"
# and "*[Answered by …]*" are written by this code, never by the model. They're
# stripped from the history the model sees -- otherwise it copies them and
# "reports" tool calls that never happened -- and any the model writes itself
# are dropped from its reply.
_STATUS_LINE_RE = _re.compile(r"(?m)^[ \t]*\*[\[(][^\n]*[\])]\*[ \t]*(?:\r?\n|$)")
_TOOL_NOTE = "(Checked on this computer"
_REAL_TOOL_NOTES: set[str] = set()     # notes this code emitted for the current turn
_RETRIEVED: list[str] = []             # text actually looked up this turn (web, plugins, tools)
_REF_SHOWN: list[str] = []             # titles of the offline reference entries shown this turn
_DOCS_SHOWN: list = []                 # core.documents.Passage objects supplied this turn
_WEB_SEARCHED = False                  # a web search ran for this turn
_WORKED = None                         # core/calc.Worked: arithmetic Cursiv computed for this turn
_ANSWERED_BY = ""                      # engine that answered the current turn
_MEMORY_RECALLED = False               # saved memories were put in front of the model this turn
_MEMORY_TEXTS: list[str] = []          # ...and which ones
_MEMORY_CTX = ""                       # the memory block as put into the prompt
_MEMORY_WORDS = _re.compile(r"[A-Za-z0-9][\w.-]{3,}")


def _memory_used(answer: str, question: str = "") -> bool:
    """Did the answer use a saved memory it was given? Three of a memory's distinctive words (or one
    code or number) in the answer's own words that the question didn't already have. Being offered a
    memory isn't using it, and a word the person just typed isn't evidence of memory: "your saved
    memories" was named under a water-supply answer that used none (2026-10 tests, first U76 Cross-check)."""
    words = {w.lower() for w in _MEMORY_WORDS.findall(_strip_status_lines(answer or ""))}
    asked = {w.lower() for w in _MEMORY_WORDS.findall(question or "")}
    for text in _MEMORY_TEXTS:
        mine = {w.lower() for w in _MEMORY_WORDS.findall(text)} - _COMMON_WORDS - asked
        shared = mine & words
        if len(shared) >= 3 or any(any(c.isdigit() for c in w) for w in shared):
            return True
    return False


_COMMON_WORDS = {"about", "after", "also", "been", "from", "have", "into", "just", "like", "more", "much", "only",
                 "over", "some", "that", "their", "them", "then", "there", "they", "this", "time", "very", "what",
                 "when", "with", "would", "your", "user", "likes", "prefers", "wants", "family", "people"}
_DOCS_SEARCHED_EMPTY: list = []        # document names searched this turn with nothing matching


def _ref_evidence() -> dict:
    """id -> reference.evidence() for the entries given this turn."""
    try:
        from cursiv_v215.core import reference as _r
        by_title = {e.title: e for e in _r.entries()}
        return {by_title[t].id: _r.evidence(by_title[t]) for t in dict.fromkeys(_REF_SHOWN) if t in by_title}
    except Exception:
        return {}


def sources_line(answer: str = "", question: str = "") -> str:
    """What this turn's answer was actually given, from Cursiv's own records, never the
    model's say-so: the offline reference (with what backs each entry), the person's documents,
    Cursiv's calculations, web results, and saved memories only when the answer used them.
    Nothing given: model knowledge, not checked."""
    parts = []
    if _REF_SHOWN:
        ev = _ref_evidence()
        sourced = {m["title"] for m in ev.values() if m["sourced"]}
        bare = [t for t in dict.fromkeys(_REF_SHOWN) if t not in sourced]
        parts.append("Cursiv Offline Reference (" + ", ".join(dict.fromkeys(_REF_SHOWN))
                     + (f"; no published source for: {', '.join(bare)}" if bare else "")
                     + ("; none professionally reviewed" if not any(m["reviewed"] for m in ev.values()) else "")
                     + ")")
    if _DOCS_SHOWN:
        pages = dict.fromkeys(f"{p.name} p. {p.page}" for p in _DOCS_SHOWN)
        parts.append("Your documents (" + ", ".join(pages) + ")")
    elif _DOCS_SEARCHED_EMPTY:
        parts.append("your documents searched, nothing on this; the rest is model knowledge (not checked)")
    if _WORKED:
        parts.append("worked out by Cursiv's code" if _WORKED.ok else "Cursiv's calculator (it refused this question)")
    if _WEB_SEARCHED:
        parts.append("web search results")
    if _MEMORY_RECALLED and _memory_used(answer, question):
        parts.append("your saved memories")
    if _CURSIV_REPLY:
        return ("Sources: " + "; ".join(parts) + ". Written by Cursiv, no AI model") if parts \
            else "Sources: Cursiv itself (no AI model)"
    if not parts:
        return "Source: model knowledge (not checked against a source)"
    return "Sources: " + "; ".join(parts) + ". Wording by the AI model"


def _without_model():
    """The local model isn't answering (and nothing online may answer): what Cursiv can give
    on its own -- its calculation, the reference card already shown, the matching pages of
    the person's documents -- said plainly, instead of "Answered by Ollama" over an error."""
    global _CURSIV_REPLY
    _CURSIV_REPLY = True
    _set_answered("")
    lines = ["**The local AI model isn't answering, so this is what Cursiv has without it.**"]
    if _WORKED:
        lines.append(f"Worked out by Cursiv's code: {_WORKED.statement}")
    if _REF_SHOWN:
        lines.append("Follow the offline reference shown above. In an emergency, call 911.")
    for p in _DOCS_SHOWN[:2]:
        text = " ".join(p.text.split())
        lines.append(f"From your documents, {p.name} p. {p.page}: \"{text[:700]}{'…' if len(text) > 700 else ''}\"")
    if not (_WORKED or _REF_SHOWN or _DOCS_SHOWN):
        lines.append("Nothing in Cursiv's reference, its calculations or your documents covers this, so there's no "
                     "answer without the model. Your field notebook, documents and reference all still work.")
    lines.append("To bring the AI back: Settings → Help & diagnostics → Setup and engine → Restart Ollama "
                 "(or open Setup to install a model).")
    yield "\n\n".join(lines)


_NOTES_BLOCK_RE = _re.compile(r"\n*-{3,}\n\*\*(Checked, with notes|Draft \+ notes)\*\*[\s\S]*$")


def _strip_status_lines(text: str) -> str:
    """The model's words only: no status lines, no check notes."""
    return _NOTES_BLOCK_RE.sub("", _STATUS_LINE_RE.sub("", text or "")).strip()


def _set_answered(label: str) -> None:
    global _ANSWERED_BY
    _ANSWERED_BY = label


def _ollama_label(base: str = "Ollama") -> str:
    try:
        model = _resolve_ollama_model()
    except Exception:
        model = None
    return f"{base} · {model}" if model else base


def _drop_fake_tool_lines(gen: Generator) -> Generator:
    """Pass the reply through, minus any "(Checked on this computer …)" line this
    code didn't emit. A line is held back only while it could still turn into
    one; everything else streams as it arrives."""
    line, holding = "", True

    def _is_fake(text: str) -> bool:
        s = text.strip()
        return s.lstrip("*_ ").startswith(_TOOL_NOTE) and s not in _REAL_TOOL_NOTES

    for chunk in gen:
        if not isinstance(chunk, str) or chunk == RATE_SENTINEL or chunk.startswith(WRITE_SENTINEL):
            if line and holding and not _is_fake(line):
                yield line
            line, holding = "", True
            yield chunk
            continue
        out = []
        for ch in chunk:
            if ch == "\n":
                if holding:
                    if not _is_fake(line):
                        out.append(line + "\n")
                else:
                    out.append("\n")
                line, holding = "", True
                continue
            line += ch
            if holding:
                head = line.lstrip(" \t*_")
                if not (_TOOL_NOTE.startswith(head) or head.startswith(_TOOL_NOTE)):
                    out.append(line)          # can't be a tool note -- release it
                    holding = False
            else:
                out.append(ch)
        if out:
            yield "".join(out)
    if line and holding and not _is_fake(line):
        yield line


def cascade_stream(
    messages: list[dict],
    keys: dict,
    max_tokens: int = RESPONSE_MAX_TOKENS,
    local_fn: Callable[[list[dict]], Generator[str, None, None]] | None = None,
) -> tuple[Generator[str, None, None], list[str]]:
    """
    Stream a one-shot reply (Babel, grow, ...): the local model first when it has
    one, then every configured key -- Claude, xAI, OpenAI, Groq, Gemini -- then
    Cursiv Cloud (only when no local model is ready), moving on whenever one
    fails (bad/expired key, out of credits, offline, empty reply). With no local
    model, Ollama is the last stop (it downloads one), so this works with no keys.

    Returns (generator, used) where `used` is filled in with the label of the
    provider that actually answered once the generator starts producing text.
    """
    local = (lambda: local_fn(messages)) if local_fn else (lambda: _call_ollama(messages, max_tokens=max_tokens))
    if not netgate.allowed():
        keys = {}                 # offline mode: the local model only
    attempts: list[tuple[str, Callable[[], Generator[str, None, None]]]] = []
    if _local_model_ready():
        attempts.append(("Ollama (local)", local))     # tried like a provider: may fall through
    if keys.get("anthropic_key"):
        attempts.append(("Claude", lambda: _call_claude_direct(messages, keys["anthropic_key"])))
    if keys.get("api_key"):
        attempts.append(("xAI", lambda: _call_xai_stream(messages, keys["api_key"], False, max_tokens)))
    if keys.get("openai_key"):
        attempts.append(("OpenAI", lambda: _call_openai_direct(messages, keys["openai_key"])))
    gemini_key = keys.get("gemini_key") or (_saved_key("gemini_key") if netgate.allowed() else "")
    groq_key = keys.get("groq_key") or (_saved_key("groq_key") if netgate.allowed() else "")
    if groq_key:
        attempts.append(("Groq", lambda: _call_groq_direct(messages, groq_key, max_tokens)))
    if gemini_key:
        attempts.append(("Gemini", lambda: _call_gemini_direct(messages, gemini_key, max_tokens)))
    # Local first: Ollama answers whenever it has a model. Cursiv Cloud only steps
    # in when it doesn't (not installed / no model yet), and only if not turned off.
    if cloud_enabled():
        attempts.append(("Cursiv Cloud", lambda: _call_cursiv_cloud(messages, max_tokens)))
    # local_fn: e.g. the coding models for codex, instead of the general chat model
    if not attempts or attempts[0][0] != "Ollama (local)":
        attempts.append(("Ollama", local))

    used: list[str] = []

    def _gen() -> Generator[str, None, None]:
        failures: list[str] = []
        for label, start in attempts:
            if label == "Cursiv Cloud" and _local_model_ready():
                continue        # local model available -- it answers instead
            if label == "Ollama":
                # Last stop -- nothing left to fall back to, so stream everything
                # (including first-time download progress) straight through.
                used.append(label)
                if failures:
                    yield f"[{'; '.join(failures)} -- using local Ollama]\n\n"
                for chunk in start():
                    if chunk != RATE_SENTINEL:
                        yield chunk
                return

            stream = start()
            held: list[str] = []      # rate-gate notes seen before real text
            failed = None
            try:
                for chunk in stream:
                    if chunk == RATE_SENTINEL:
                        failed = "busy or unreachable"
                        break
                    text = chunk.strip()
                    if not text:
                        continue
                    if text.startswith(_PROVIDER_ERROR_PREFIXES):
                        failed = text.strip("[]")[:160]
                        break
                    if text.startswith("*[Rate gate"):
                        held.append(chunk)
                        continue
                    # Real text: this provider answers. Stream the rest straight through.
                    used.append(label)
                    if failures:
                        yield f"[{'; '.join(failures)} -- answered by {label}]\n\n"
                    yield from held
                    yield chunk
                    for rest in stream:
                        if rest != RATE_SENTINEL:
                            yield rest
                    return
            except Exception as e:
                failed = str(e)[:160]
            failures.append(f"{label}: {failed or 'empty reply'}")
        if failures:      # reached only when the local model went first and everything failed
            yield f"[Nothing answered — {'; '.join(failures)}]"

    return _gen(), used


try:
    from cursiv_v215.guardian.identity_core import (
        wrap       as _identity_wrap,
        CURSIV_IDENTITY as _IDENTITY_OVERRIDE,
    )
except ImportError:
    from guardian.identity_core import (
        wrap       as _identity_wrap,
        CURSIV_IDENTITY as _IDENTITY_OVERRIDE,
    )


def _call_ollama_model(
    model: str,
    system_str: str,
    prompt: str,
    max_tokens: int = 2000,
    collect: bool = False,
) -> Generator[str, None, None]:
    """Call a specific Ollama model. If collect=True, yields one final chunk (full text)."""
    import json as _json
    from cursiv_v215.core import speed as _speed
    # Always prepend identity override — DeepSeek especially needs it
    system_str = _IDENTITY_OVERRIDE + system_str
    payload = json.dumps({
        "model":  model,
        "system": system_str,
        "prompt": prompt,
        "stream": not collect,
        # 16k context: coding prompts carry playbooks + worked examples; at 8k Ollama
        # silently dropped the start of the prompt (the instructions).
        "keep_alive": "30m",
        **_speed.no_thinking(model),
        "options": {"num_predict": max_tokens, "num_ctx": _num_ctx(), **_speed.gpu_options(model)},
    }).encode()
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            if collect:
                data = _json.loads(resp.read().decode())
                yield data.get("response", "")
            else:
                for line in resp:
                    chunk = _json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("error", "")
        except Exception:
            detail = ""
        yield f"\n[{model} error: HTTP {e.code}{' -- ' + detail if detail else ''}]"
    except Exception as e:
        yield f"\n[{model} error: {e}]"


def _big_gpu() -> bool:
    """>= 12 GB of GPU memory (NVIDIA or AMD): room for a second coding model as a
    reviewer. On smaller GPUs swapping 14B/16B models took minutes per answer."""
    from cursiv_v215.core import speed
    return speed.big_gpu()


def _num_ctx() -> int:
    from cursiv_v215.core import speed
    return speed.num_ctx()


def _call_ollama_code_council(
    messages: list[dict],
    max_tokens: int = 2000,
) -> Generator[str, None, None]:
    """
    Dual-model offline Code Council:
      Phase 1 — qwen2.5-coder:14b writes the primary solution (streamed live)
      Phase 2 — deepseek-coder-v2:16b reviews and improves it (streamed live)
    Falls back to llama3.1 if neither coding model is pulled.
    """
    available    = _ollama_pulled_models()
    # Use the exact tags that are installed (e.g. qwen2.5-coder:7b), not only the
    # 14b/16b defaults -- asking Ollama for a tag that isn't pulled just fails.
    def _installed(preferred: str, family: str) -> str | None:
        if family == "qwen2.5-coder":       # the size that suits this GPU, if installed
            from cursiv_v215.core import speed
            for tag in speed.code_model_prefs():
                if tag in available:
                    return tag
        if preferred in available:
            return preferred
        tags = sorted(t for t in available if t.startswith(family + ":"))
        return tags[-1] if tags else None
    qwen_tag     = _installed(OLLAMA_CODE_PRIMARY, "qwen2.5-coder")
    deepseek_tag = _installed(OLLAMA_CODE_SECONDARY, "deepseek-coder-v2")
    has_qwen, has_deepseek = qwen_tag is not None, deepseek_tag is not None

    if not has_qwen and not has_deepseek:
        yield from _call_ollama(messages, max_tokens)
        return

    system_parts = [
        m["content"] for m in messages
        if m.get("role") == "system" and isinstance(m.get("content"), str)
    ]
    system_str = "\n\n".join(system_parts)
    turns = "\n".join(
        f"{'Human' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    )

    primary_model   = qwen_tag if has_qwen else deepseek_tag
    # Reviewer only where both models fit in GPU memory; elsewhere codex's
    # run-and-fix loop (coding/runner.py) checks the code by actually running it.
    secondary_model = deepseek_tag if has_deepseek and has_qwen and _big_gpu() else None

    # ── Phase 1: Primary coder writes solution ───────────────────────────
    if secondary_model:
        yield f"**[{primary_model}]** Writing solution...\n\n"

    primary_chunks: list[str] = []
    for token in _call_ollama_model(primary_model, system_str, turns, max_tokens):
        primary_chunks.append(token)
        yield token

    if not primary_chunks:
        # _call_ollama_model completed without yielding anything and without
        # raising -- e.g. Ollama accepted the request but the model produced
        # an empty response. Previously this looked identical to a UI bug
        # (the "Writing solution..." header shown, then nothing, forever)
        # with no way to tell what actually happened.
        yield (f"\n[{primary_model} produced no output. It may still be loading "
               f"into memory on first use -- try again in a moment, or confirm "
               f"it's pulled with `ollama list`.]")
        return

    if not secondary_model:
        return

    # ── Phase 2: Critic reviews and improves ────────────────────────────
    primary_text = "".join(primary_chunks)
    yield f"\n\n---\n**[{secondary_model}]** Code review...\n\n"

    review_prompt = (
        f"{turns}\n\n"
        f"A colleague produced this solution:\n\n{primary_text}\n\n"
        "Review it critically. If it is correct and clean, confirm briefly and add any meaningful "
        "improvements or edge-case handling. If there are bugs or a clearly better approach, "
        "rewrite only the affected parts. Be concise — do not repeat what is already correct."
    )
    yield from _call_ollama_model(secondary_model, system_str, review_prompt, max_tokens)


def _call_xai_stream(
    messages: list[dict],
    api_key: str,
    has_images: bool = False,
    max_tokens: int = RESPONSE_MAX_TOKENS,
) -> Generator[str, None, None]:
    """Stream from xAI Grok. Handles text and vision."""
    model = XAI_MODEL_VIS if has_images else XAI_MODEL
    payload = json.dumps({
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "stream":      True,
        "temperature": 0.7,
    }).encode()
    try:
        req = urllib.request.Request(
            XAI_URL,
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        chunk   = json.loads(line[6:])
                        delta   = chunk["choices"][0]["delta"]
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            body = e.read().decode(errors="ignore")[:120]
            yield f"[xAI auth error {e.code} — check your key: {body}]"
        else:
            yield RATE_SENTINEL
    except Exception:
        yield RATE_SENTINEL


def _call_xai_non_stream(messages: list[dict], api_key: str, has_images: bool) -> str:
    """Non-streaming fallback for xAI."""
    result = []
    for chunk in _call_xai_stream(messages, api_key, has_images):
        result.append(chunk)
    return "".join(result)


def _generate_with_openai(
    filepath: str,
    openai_key: str,
    context_messages: list[dict],
    grok_draft: str = "",
) -> str:
    """
    Use OpenAI gpt-4.1 to generate or rewrite a file with full conversation context.
    Passes the last 6 conversation turns so OpenAI understands the goal.
    Falls back to grok_draft if the call fails.
    """
    ext  = Path(filepath).suffix.lower() if filepath else ""
    lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".sh": "Bash", ".bat": "Batch"}.get(ext, "code")

    # Build context from the last 6 conversation turns (skip system message)
    ctx_turns = [m for m in context_messages if m.get("role") in ("user", "assistant")][-6:]
    ctx_text  = "\n".join(
        f"[{m['role'].upper()}]: {m['content'][:800]}"
        for m in ctx_turns
        if isinstance(m.get("content"), str)
    )

    system_msg = (
        f"You are an expert {lang} engineer. "
        "Write complete, production-ready code — no stubs, no TODOs, no placeholder comments. "
        "Return ONLY the raw file content, nothing else. No markdown fences, no explanation."
    )
    user_msg = (
        f"Conversation context:\n{ctx_text}\n\n"
        f"File to generate: {filepath}\n\n"
    )
    if grok_draft:
        user_msg += (
            f"Grok's draft (improve and complete this):\n"
            f"{grok_draft[:8000]}\n\n"
        )
    user_msg += (
        "Write the complete, final file content. "
        "Every function must be fully implemented. No ellipsis, no '# TODO'."
    )

    try:
        payload = json.dumps({
            "model":      OPENAI_CODE_MODEL,
            "messages":   [
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            "max_tokens": 8000,
        }).encode()
        req = urllib.request.Request(
            OPENAI_URL, data=payload,
            headers={"Content-Type":  "application/json",
                     "Authorization": f"Bearer {openai_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def _generate_with_claude(
    filepath: str,
    anthropic_key: str,
    context_messages: list[dict],
    grok_draft: str = "",
) -> str:
    """
    Use Claude claude-sonnet-4-6 to generate or rewrite a file with full
    conversation context. Falls back to empty string if the call fails.
    """
    ext  = Path(filepath).suffix.lower() if filepath else ""
    lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".sh": "Bash", ".bat": "Batch"}.get(ext, "code")

    ctx_turns = [m for m in context_messages if m.get("role") in ("user", "assistant")][-6:]
    ctx_text  = "\n".join(
        f"[{m['role'].upper()}]: {m['content'][:800]}"
        for m in ctx_turns
        if isinstance(m.get("content"), str)
    )

    system_msg = (
        f"You are an expert {lang} engineer. "
        "Write complete, production-ready code — no stubs, no TODOs, no placeholder comments. "
        "Return ONLY the raw file content, nothing else. No markdown fences, no explanation."
    )
    user_msg = (
        f"Conversation context:\n{ctx_text}\n\n"
        f"File to generate: {filepath}\n\n"
    )
    if grok_draft:
        user_msg += (
            f"Grok's draft (improve and complete this):\n"
            f"{grok_draft[:8000]}\n\n"
        )
    user_msg += (
        "Write the complete, final file content. "
        "Every function must be fully implemented. No ellipsis, no '# TODO'."
    )

    try:
        payload = json.dumps({
            "model":      ANTHROPIC_CODE_MODEL,
            "max_tokens": 8000,
            "system":     system_msg,
            "messages":   [{"role": "user", "content": user_msg}],
        }).encode()
        req = urllib.request.Request(
            ANTHROPIC_URL, data=payload,
            headers={
                "Content-Type":    "application/json",
                "x-api-key":       anthropic_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            return data["content"][0]["text"].strip()
    except Exception:
        return ""


def _call_claude_with_tools(
    messages: list[dict],
    anthropic_key: str,
    root: Path,
    confirm_writes: bool = False,
    max_tokens: int = 4000,
    max_loops: int = 20,
    is_owner: bool = False,
) -> Generator[str, None, None]:
    """
    Agentic file-access loop using Claude's native tool-calling API.
    Uses a compact system prompt (~200 tokens) instead of the full 12k-token
    codex to stay under the 30k input-tokens/min rate limit.
    """
    system_str = _compact_system_for_tools(is_owner=is_owner)
    # Keep only the last 8 user/assistant turns to limit history overhead
    chat_only  = [m for m in messages if m["role"] in ("user", "assistant")]
    loop_msgs  = chat_only[-16:]   # 8 pairs = 16 messages

    import time as _time

    for _ in range(max_loops):
        payload = json.dumps({
            "model":      ANTHROPIC_CODE_MODEL,
            "max_tokens": max_tokens,
            "system":     system_str,
            "tools":      CLAUDE_TOOLS,
            "messages":   loop_msgs,
        }).encode()

        # Pre-call rate gate: wait if we're near the 20k TPM ceiling
        if _rate_limiter:
            est = _rate_limiter.estimate_tokens(payload.decode(errors="ignore"))
            _rate_limiter.wait_if_needed(est)

        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    ANTHROPIC_URL, data=payload,
                    headers={
                        "content-type":      "application/json",
                        "x-api-key":         anthropic_key,
                        "anthropic-version": ANTHROPIC_VERSION,
                    },
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode())
                # Record actual tokens used so the window stays accurate
                if _rate_limiter:
                    usage   = data.get("usage", {})
                    actual  = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    if actual:
                        _rate_limiter.record_actual(actual)
                break   # success
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")
                if e.code == 429 and attempt < 2:
                    wait_s = 15 * (attempt + 1)   # 15s, then 30s
                    yield f"\n*[Rate gate: pacing {wait_s}s — TPM window full]*\n"
                    _time.sleep(wait_s)
                    continue
                yield f"\n[Claude error {e.code}: {body[:200]}]"
                return
            except Exception as e:
                yield f"\n[Claude error: {e}]"
                return

        stop_reason    = data.get("stop_reason", "end_turn")
        content_blocks = data.get("content", [])

        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(block)

        if text_parts:
            for word in " ".join(text_parts).split(" "):
                yield word + " "

        if stop_reason == "end_turn" or not tool_calls:
            return

        loop_msgs.append({"role": "assistant", "content": content_blocks})

        tool_results = []
        for tc in tool_calls:
            fn_name = tc["name"]
            fn_args = tc.get("input", {})
            tc_id   = tc["id"]

            if fn_name == "write_file" and confirm_writes:
                path_arg    = fn_args.get("path", "")
                content_arg = fn_args.get("content", "")
                preview     = content_arg[:400] + ("…" if len(content_arg) > 400 else "")
                yield (
                    f"\n**Write requested:** `{path_arg}`\n"
                    f"```\n{preview}\n```\n"
                    f"*Waiting for approval…*\n"
                )
                yield WRITE_SENTINEL + json.dumps({"path": path_arg, "content": content_arg})
                return

            result = execute_tool(fn_name, fn_args, root)

            # Brief status line for the user; full result back to Claude only for read_file
            if fn_name == "read_file":
                lines = result.count("\n") + 1
                yield f"*`→ {fn_name}: {fn_args.get('path','?')} ({lines} lines)`*\n"
                ctx_result = result          # Claude needs full content
            elif fn_name in ("list_directory", "search_files"):
                count = result.count("\n") + 1
                yield f"*`→ {fn_name}: {fn_args.get('path', fn_args.get('pattern','?'))} ({count} entries)`*\n"
                ctx_result = result[:1500]   # truncate — Claude only needs the structure
            elif fn_name == "write_file":
                yield f"*`→ wrote: {fn_args.get('path','?')}`*\n"
                ctx_result = result
            elif fn_name == "submit_plan":
                yield f"*`→ plan submitted`*\n"
                ctx_result = result
            else:
                yield f"*`→ {fn_name}: {result[:120]}`*\n"
                ctx_result = result

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": tc_id,
                "content":     ctx_result,
            })

        loop_msgs.append({"role": "user", "content": tool_results})

    yield "\n[Max tool iterations reached — stopping.]"


def _call_xai_with_tools(
    messages: list[dict],
    api_key: str,
    root: Path,
    openai_key: str = "",
    has_images: bool = False,
    max_tokens: int = 4000,
    max_loops: int = 20,
    confirm_writes: bool = False,
    anthropic_key: str = "",
    endpoint_url: str = "",    # override XAI_URL — allows reuse for OpenAI
    model_override: str = "",  # override XAI_MODEL
    provider_name: str = "xAI",
) -> Generator[str, None, None]:
    """
    Agentic file-access tool loop (OpenAI-compatible API format).
    Works for xAI/Grok and GPT-4.1 — same wire format, different endpoint/model.
    Code generation: Claude > OpenAI > none on write_file calls.
    """
    url       = endpoint_url or XAI_URL
    model     = model_override or (XAI_MODEL_VIS if has_images else XAI_MODEL)
    loop_msgs = list(messages)

    for _ in range(max_loops):
        payload = json.dumps({
            "model":       model,
            "messages":    loop_msgs,
            "tools":       FILE_TOOLS,
            "tool_choice": "auto",
            "max_tokens":  max_tokens,
            "temperature": 0.7,
            "stream":      False,
        }).encode()
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type":  "application/json",
                         "Authorization": f"Bearer {api_key}"},
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            yield f"\n[{provider_name} error {e.code}: {body[:200]}]"
            return
        except Exception as e:
            yield f"\n[{provider_name} error: {e}]"
            return

        choice     = data["choices"][0]
        msg        = choice["message"]
        loop_msgs.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            # Terminal response — fake-stream word by word for rolling feel
            content = msg.get("content") or ""
            for word in content.split(" "):
                yield word + " "
            return

        # Execute each tool call
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except Exception:
                fn_args = {}

            # Confirm-before-write: pause and hand control back to the UI
            if fn_name == "write_file" and confirm_writes:
                path_arg    = fn_args.get("path", "")
                content_arg = fn_args.get("content", "")
                preview     = content_arg[:600] + ("..." if len(content_arg) > 600 else "")
                yield (
                    f"\n**Write requested:** `{path_arg}`\n"
                    f"```\n{preview}\n```\n"
                    f"*Waiting for approval…*\n"
                )
                yield WRITE_SENTINEL + json.dumps({"path": path_arg, "content": content_arg})
                return   # stop the loop — resume after user approves

            # Code-gen enhancement before writing:
            # Claude (Anthropic) takes priority when key is set; falls back to OpenAI.
            if fn_name == "write_file" and (anthropic_key or openai_key):
                grok_draft = fn_args.get("content", "")
                filepath   = fn_args.get("path", "")
                if grok_draft:
                    if anthropic_key:
                        yield f"*[Claude {ANTHROPIC_CODE_MODEL} generating production-ready code…]*\n"
                        generated = _generate_with_claude(filepath, anthropic_key, loop_msgs, grok_draft)
                    else:
                        yield "*[OpenAI gpt-4.1 generating production-ready code…]*\n"
                        generated = _generate_with_openai(filepath, openai_key, loop_msgs, grok_draft)
                    if generated:
                        fn_args["content"] = generated
                        yield "*[Code generation complete — writing file]*\n"

            result = execute_tool(fn_name, fn_args, root)

            if fn_name == "read_file":
                lines = result.count("\n") + 1
                yield f"*`→ {fn_name}: {fn_args.get('path','?')} ({lines} lines)`*\n"
                ctx_result = result
            elif fn_name in ("list_directory", "search_files"):
                count = result.count("\n") + 1
                yield f"*`→ {fn_name}: {fn_args.get('path', fn_args.get('pattern','?'))} ({count} entries)`*\n"
                ctx_result = result[:1500]
            elif fn_name == "write_file":
                yield f"*`→ wrote: {fn_args.get('path','?')}`*\n"
                ctx_result = result
            else:
                yield f"*`→ {fn_name}: {result[:120]}`*\n"
                ctx_result = result

            loop_msgs.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      ctx_result,
            })

    yield "\n[Max tool iterations reached — stopping.]"


def _call_openai_with_tools(
    messages: list[dict],
    openai_key: str,
    root: Path,
    anthropic_key: str = "",
    max_tokens: int = 4000,
    max_loops: int = 20,
    confirm_writes: bool = False,
) -> Generator[str, None, None]:
    """GPT-4.1 tool loop — same OpenAI-compatible format as xAI, different endpoint/model."""
    yield from _call_xai_with_tools(
        messages, openai_key, root,
        openai_key="",
        has_images=False,
        max_tokens=max_tokens,
        max_loops=max_loops,
        confirm_writes=confirm_writes,
        anthropic_key=anthropic_key,
        endpoint_url=OPENAI_URL,
        model_override=OPENAI_CODE_MODEL,
        provider_name="OpenAI",
    )


# ── Smart model routing ───────────────────────────────────────────────────

import re as _re

_CODE_RE = _re.compile(
    r'\b(write|fix|debug|implement|refactor|build|create|update|edit|test)\b',
    _re.I,
)
# Unambiguous technical terms -- unlike the generic verbs above (which show up
# constantly in non-code requests, e.g. "create a farming schedule"), a single
# hit here is already strong evidence of a real coding question.
_CODE_STRONG_RE = _re.compile(
    r'\b(function|class|method|script|module|endpoint|database|query|'
    r'python|javascript|typescript|html|css|sql|bash|json|'
    r'error|traceback|exception|bug|import|def |return )\b',
    _re.I,
)
_CREATIVE_RE = _re.compile(
    r'\b(imagine|visualize|visualise|design|aesthetic|stunning|beautiful|'
    r'describe.*look|story|narrative|poem|creative|artistic|visual|render|draw)\b',
    _re.I,
)


def _classify_message(text: str) -> str:
    """Return 'code', 'creative', or 'general' for smart model routing."""
    t = (text or "").strip()
    if not t:
        return "general"
    if any(m in t for m in ("def ", "class ", "```", "import ", "Error:", "Traceback", "  File \"")):
        return "code"
    if len(_CODE_STRONG_RE.findall(t)) >= 1:
        return "code"
    code_hits     = len(_CODE_RE.findall(t))
    creative_hits = len(_CREATIVE_RE.findall(t))
    if creative_hits >= 2 and creative_hits > code_hits:
        return "creative"
    # Generic verbs (write/build/create/test/...) need 2+ hits before this
    # counts as code -- a single "create" or "build" is common in completely
    # non-code requests ("create a farming schedule", "build my confidence")
    # and shouldn't alone route someone into the Code Council pipeline.
    if code_hits >= 2:
        return "code"
    return "general"


def _call_claude_direct(
    messages: list[dict],
    anthropic_key: str,
) -> Generator[str, None, None]:
    """Route a chat message directly to Claude — no tool loop."""
    import time as _time
    sys_parts = [m["content"] for m in messages if m["role"] == "system"]
    chat_msgs  = [m for m in messages if m["role"] != "system"]
    # Keep last 12 turns to limit input token cost
    chat_msgs  = chat_msgs[-24:]
    payload = json.dumps({
        "model":      ANTHROPIC_CODE_MODEL,
        "max_tokens": 4096,
        "system":     "\n\n".join(sys_parts),
        "messages":   chat_msgs,
    }).encode()
    if _rate_limiter:
        est = _rate_limiter.estimate_tokens(payload.decode(errors="ignore"))
        _rate_limiter.wait_if_needed(est)

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                ANTHROPIC_URL, data=payload,
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         anthropic_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                },
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
            if _rate_limiter:
                usage  = data.get("usage", {})
                actual = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                if actual:
                    _rate_limiter.record_actual(actual)
            content = (data.get("content") or [{}])[0].get("text", "") or ""
            for word in content.split(" "):
                yield word + " "
            return
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            if e.code == 429 and attempt < 2:
                wait_s = 15 * (attempt + 1)
                yield f"\n*[Rate gate: pacing {wait_s}s — TPM window full]*\n"
                _time.sleep(wait_s)
                continue
            if e.code == 429:
                yield RATE_SENTINEL   # signal to chat() to try fallback provider
                return
            yield f"\n[Claude error {e.code}: {body[:200]}]"
            return
        except Exception as e:
            yield f"\n[Claude error: {e}]"
            return


def _call_openai_direct(
    messages: list[dict],
    openai_key: str,
) -> Generator[str, None, None]:
    """Route a chat message directly to GPT-4.1 — no tool loop."""
    payload = json.dumps({
        "model":    OPENAI_CODE_MODEL,
        "messages": messages,
    }).encode()
    try:
        req = urllib.request.Request(
            OPENAI_URL, data=payload,
            headers={
                "content-type":  "application/json",
                "Authorization": f"Bearer {openai_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"] or ""
        for word in content.split(" "):
            yield word + " "
    except urllib.error.HTTPError as e:
        yield f"\n[OpenAI error {e.code}: {e.read().decode(errors='ignore')[:200]}]"
    except Exception as e:
        yield f"\n[OpenAI error: {e}]"


def _call_provider_council(
    question:       str,
    xai_key:        str,
    openai_key:     str,
    anthropic_key:  str,
    system_context: str = "",
) -> Generator[str, None, None]:
    """
    Entry into the Provider Council (council/async_council.py)
    (cursiv_v215.council.async_council.run_council) -- bridges its
    blocking/asyncio interior to Gradio's synchronous streaming generator
    via a background thread + queue, so both UI surfaces run one shared
    council implementation instead of each maintaining a separate one.

    Replaces the old, independently-written "Group Discovery" 3-cycle
    loop that used to live here -- same idea (multi-provider consensus),
    now the one real implementation instead of a second copy of it.
    """
    from cursiv_v215.council.async_council import run_council

    full_question = f"{system_context}\n\n{question}" if system_context else question

    cfg = {
        "api_key":       xai_key or "",
        "openai_key":    openai_key or "",
        "anthropic_key": anthropic_key or "",
    }

    q: "_queue_mod.Queue[str | None]" = _queue_mod.Queue()

    def _worker() -> None:
        try:
            run_council(full_question, cfg, force_full=True, write_fn=q.put)
        except Exception as exc:
            q.put(f"\n[Council error: {exc}]\n")
        finally:
            q.put(None)  # sentinel -- always fires

    threading.Thread(target=_worker, daemon=True).start()

    while True:
        chunk = q.get()
        if chunk is None:
            break
        yield chunk


def _is_online() -> bool:
    """TCP connect to 8.8.8.8:53 — tests internet without a DNS lookup.
    False, without connecting, while offline mode is on."""
    if not netgate.allowed():
        return False
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False


def _cloud_configured(*keys: str) -> bool:
    """Is anything set up that could send this turn off the computer?"""
    if any((k or "").strip() for k in keys):
        return True
    if any(_saved_key(f) for f in ("api_key", "openai_key", "anthropic_key", "gemini_key", "groq_key")):
        return True
    return netgate.web_search_auto()


def _connectivity_probe(*keys: str):
    """For the Connectivity phase: None (not checked) when nothing would use the
    internet -- offline mode on, or the local model ready with no cloud key or
    cloud feature on. Otherwise the 8.8.8.8 check (AUDIT C-011)."""
    if not netgate.allowed():
        return None
    if _local_model_ready() and not _cloud_configured(*keys):
        return None
    return _is_online()


# ── Core chat function ────────────────────────────────────────────────────

def _chat_inner(
    message: dict | str,
    history: list[dict],
    api_key: str,
    files: list | None,
    file_access: bool = False,
    root_path: str = "",
    openai_key: str = "",
    confirm_writes: bool = False,
    anthropic_key: str = "",
    force_provider: str = "",   # "grok" | "claude" | "openai" — bypasses smart routing
) -> Generator[str, None, None]:
    """
    Main streaming chat handler.
    message: dict with 'text' and optionally 'files' (from MultimodalTextbox)
             or plain str if called programmatically.
    history: list of {"role": ..., "content": ...} dicts (Gradio 6 format).
    """

    # ── Unpack multimodal input ─────────────────────────────────────────
    if isinstance(message, dict):
        user_text    = message.get("text", "").strip()
        uploaded     = list(message.get("files", []) or [])
    else:
        user_text    = str(message).strip()
        uploaded     = []

    if files:
        uploaded.extend(files)

    if not user_text and not uploaded:
        yield "Please type a message or upload a file."
        return

    # ── Owner code setup (runs before Guardian — no API call, no log) ───
    if user_text.lower().startswith("owner setcode "):
        _new_code = user_text[len("owner setcode "):].strip()
        if not _new_code:
            yield "Usage: owner setcode <your secret code>"
            return
        try:
            _set_owner_code(_new_code)
            yield (
                "Owner code saved. It's stored locally on this machine only "
                "(never committed to git, never sent anywhere). Type that "
                "code as a message any time to turn on owner mode for that session."
            )
        except Exception as e:
            yield f"Failed to save owner code: {e}"
        return

    # ── Owner code (no model call, nothing logged) ──
    if user_text and _verify_owner_code(user_text):
        _unlock_owner(_GRADIO_SESSION_ID)
        yield _build_owner_reveal()
        return

    # ── Process files ───────────────────────────────────────────────────
    file_context, image_parts = process_uploaded_files(uploaded)

    # ── Build system prompt ─────────────────────────────────────────────
    system_text = load_system_prompt() + load_vault_context() + _load_session_ctx()
    global _FULL_PERSONA
    _FULL_PERSONA = system_text      # free/local providers swap this for the compact persona
    if _owner_active():
        system_text += (
            "\n\n## Owner mode\n"
            "The owner of this copy is verified. Answer questions about how "
            "Cursiv works fully and honestly."
        )
    if file_context:
        system_text += f"\n\n## Uploaded Content\n{file_context}"
    if file_access:
        system_text += """

## CODING PROTOCOL (file access active)
You are in full autonomous coding mode. Follow this protocol exactly:
1. ALWAYS call submit_plan first — list every file you will create/edit, what it does, and your order of operations.
2. Write COMPLETE, production-ready code — zero stubs, zero TODOs, zero placeholders. Every function fully implemented.
3. Always call read_file before editing an existing file so you know the current content.
4. After writing each file, call read_file to verify the content is correct.
5. If building an app, create ALL required files: entry point, dependencies (requirements.txt / package.json), and a README.
6. Think end-to-end: if the user says "build X", deliver a working X in one sweep without stopping to ask clarifying questions unless the request is genuinely ambiguous.
"""

    # ── Build messages array ────────────────────────────────────────────
    messages: list[dict] = [{"role": "system", "content": system_text}]

    for h in history:
        role    = h.get("role", "user")
        content = h.get("content", "")
        if role == "assistant" and isinstance(content, str):
            content = _strip_status_lines(content)   # see _STATUS_LINE_RE
        if content:
            messages.append({"role": role, "content": content})

    # ── Attach images to user message (vision) ──────────────────────────
    if image_parts:
        user_content: list[dict] | str = [{"type": "text", "text": user_text}] + image_parts
    else:
        user_content = user_text

    messages.append({"role": "user", "content": user_content})

    # ── Real-time web search injection ──────────────────────────────────
    # Fires when the query looks like it needs current facts, or when the
    # user explicitly types "search: <query>".  Results are injected into
    # the system prompt so every provider gets the same live context.
    # Skipped entirely when offline — _is_online() is already called below.
    _search_q = user_text
    for _pfx in ("search:", "search "):
        if _search_q.lower().startswith(_pfx):
            _search_q = _search_q[len(_pfx):].strip()
            break
    _web_ctx = ""
    _search_failed = ""
    if netgate.is_offline() and user_text.lower().startswith(("search:", "search ")):
        yield f"*[Web search skipped. {netgate.OFFLINE_MESSAGE}]*\n\n"
    elif _needs_search(user_text):
        if _is_online():
            _web_ctx = _web_search(_search_q[:300])
            if not _web_ctx:
                from cursiv_v215.chat import web_search as _ws
                _search_failed = _ws.last_problem or "nothing came back"
        else:
            _search_failed = "this computer isn't connected to the internet right now"
    if _search_failed:
        # Said by Cursiv, and told to the model: with nothing to go on it said searching "would violate
        # privacy and safety rules" (U77, a DuckDuckGo bot check)
        yield f"*[Web search tried, no results: {_search_failed}. Nothing below comes from the web.]*\n\n"
        messages[0]["content"] += (
            "\n\n## Web search\nThe person asked for a web search. It was tried and returned nothing ("
            + _search_failed + "). Say that in one plain sentence. Don't claim you searched or found anything, "
            "and don't say searching is against any rule or that you can't search: it was tried and failed.\n")
    if _web_ctx:
        global _WEB_SEARCHED
        _WEB_SEARCHED = True
        _RETRIEVED.append(_web_ctx)
        messages[0]["content"] += (
            "\n\n## Live Web Search Results\n"
            "*(Snippets from a web search for this question, just now. They can be wrong or out of date: "
            "say which parts of the answer come from them)*\n\n"
            + _web_ctx + "\n"
        )

    # ── Cursiv's 8 phases (core/phases.py): Energy, Emergency, Grounding (memory),
    # Route, Structure, Connectivity, Future State, Recovery -- real rules run on
    # every message; their instructions go into the system prompt.
    global _PHASE_AFTER
    _PHASE_AFTER = ""
    try:
        from cursiv_v215.core import phases as _phases
        _ph = _phases.run(user_text, memory_fn=_build_strand_context,
                          online_fn=lambda: _connectivity_probe(api_key, openai_key, anthropic_key),
                          local_fn=lambda: _ollama_running() and _resolve_ollama_model() is not None)
        _addendum = _ph.system_addendum()
        if _ph.emergency and _ph.emergency_kind != "medical":
            # A crisis gets a short, focused prompt -- buried at the end of Cursiv's long
            # instructions, the care guidance lost out to the model's canned refusal style.
            messages[0]["content"] = (
                "You are Cursiv, a caring personal assistant built by Joshua Winkler for his family. The person "
                "talking to you may be in crisis or danger right now. Speak like a calm, kind friend: short, warm, "
                "plain sentences. Acknowledge what they said and that it matters. Ask if they're safe right now. "
                "Gently encourage them to reach out to the help line shown above and to someone they trust, and "
                "say you're here to keep talking. Never lecture, never refuse, never say you can't help, and don't "
                "list many resources -- the help lines are already shown.\n\n" + (_ph.memory or "")
            )
        elif _addendum:
            messages[0]["content"] += "\n\n" + _addendum + "\n"
        _PHASE_AFTER = _ph.after_reply
        global _EMERGENCY_TURN
        _EMERGENCY_TURN = bool(_ph.emergency)
        if _ph.before_reply:
            yield _ph.before_reply
    except Exception:
        _strand_ctx = _build_strand_context(user_text) if len(user_text.strip()) >= 10 else ""
        if _strand_ctx:
            messages[0]["content"] += "\n\n## Personal Memory\n" + _strand_ctx + "\n"

    # ── Coding questions and pasted terminal output get Cursiv's coding brain
    # (cursiv_v215/coding): a focused coding prompt + playbooks + error diagnosis +
    # their environment + learned lessons + project files. The full persona prompt
    # made coding models echo councils/owner notes and skip the real setup steps.
    # ── Questions about Cursiv itself: answer from a live report of its real state
    # (core/selfknow.py), not from the persona prompt -- which made it invent internals.
    _self_turn = False
    try:
        from cursiv_v215.core import selfknow as _sk
        if not (locals().get("_ph") and _ph.emergency) and _sk.is_self_question(user_text):
            messages[0]["content"] = _sk.system_prompt()
            _self_turn = True
    except Exception:
        pass

    global _CODING_TURN
    _CODING_TURN = False
    try:
        if _self_turn:
            raise RuntimeError("self question")      # skip the coding brain
        from cursiv_v215.coding import brain as _cb
        _emergency = bool(locals().get("_ph") and _ph.emergency)
        if not _emergency and (_classify_message(user_text) == "code" or _cb.looks_like_terminal(user_text)):
            from cursiv_v215.memory import semantic as _sem
            _person_now = _sem.current_person()
            if file_access:      # tool-using coding mode keeps its protocol; add the ground truth
                messages[0]["content"] += "\n\n" + _cb.context_block(user_text, history, _person_now)
            else:
                _sys = _cb.system_prompt(user_text, history, _person_now)
                if _web_ctx:
                    _sys += "\n\n## Live Web Search Results\n" + _web_ctx
                _mem = _build_strand_context(user_text) if len(user_text.strip()) >= 10 else ""
                if _mem:
                    _sys += "\n\n## What you know about them\n" + _mem
                messages[0]["content"] = _sys
            _CODING_TURN = True
    except Exception:
        pass

    # ── How this person wants Cursiv to talk (core/style.py): tone + rules learned
    # from their corrections. Added to every kind of reply; corrections are learned
    # in the background from this message and the reply it's correcting.
    try:
        if not (locals().get("_ph") and _ph.emergency):
            from cursiv_v215.core import style as _style
            from cursiv_v215.memory import semantic as _sem2
            _who = _sem2.current_person()
            _add = _style.prompt_addendum(_who)
            if _add:
                messages[0]["content"] += "\n\n" + _add + "\n"
            if _style.looks_like_correction(user_text):
                _prev = next((m.get("content", "") for m in reversed(history or [])
                              if m.get("role") == "assistant" and isinstance(m.get("content"), str)), "")
                threading.Thread(target=_style.learn_correction, args=(_who, user_text, _prev, _quick_llm),
                                 daemon=True).start()
    except Exception:
        pass

    # ── Project memory, plugin context, and tools (U52) ──────────────────────
    if not (locals().get("_ph") and _ph.emergency):
        try:
            from cursiv_v215.memory import projects as _proj
            from cursiv_v215.memory import semantic as _sem3
            _pc = _proj.context(user_text, _sem3.current_person())
            if _pc:
                messages[0]["content"] += "\n\n" + _pc + "\n"
        except Exception:
            pass
        try:
            from cursiv_v215.core import plugins as _plugins
            _hc = _plugins.message_context(user_text)
            if _hc:
                _RETRIEVED.append(_hc)
                messages[0]["content"] += "\n\n## From your plugins\n" + _hc + "\n"
        except Exception:
            pass
        try:
            from cursiv_v215.core import tools as _tools
            if _tools.might_need_tools(user_text):
                _calls = _tools.plan(user_text, _router_llm)
                if _calls:
                    _results = _tools.run(_calls)
                    _tool_ctx = _tools.context_for(_results)
                    _RETRIEVED.append(_tool_ctx)
                    messages[0]["content"] += "\n\n" + _tool_ctx + "\n"
                    _note = "*(Checked on this computer: " + "; ".join(l for l, _r in _results) + ")*"
                    _REAL_TOOL_NOTES.add(_note)
                    yield _note + "\n\n"
        except Exception:
            pass

    # Clock times and plain sums are worked out in code (core/calc.py); the model
    # gets the result, and chat() checks the answer used it.
    try:
        if not (_self_turn or _CODING_TURN):
            from cursiv_v215.core import calc as _calc
            global _WORKED
            _WORKED = _calc.work_out(user_text)
            if _WORKED:
                messages[0]["content"] += "\n\n" + _calc.prompt_note(_WORKED) + "\n"
                if _WORKED.lead:                 # a safety rule's answer, first, from Cursiv
                    yield _WORKED.lead + "\n\n"
        # "Are you offline?" is answered from the real switches and gate, not by the model,
        # which said "I am completely offline" as fact (benchmark gen-020, U65).
        from cursiv_v215.chat import status as _net_status
        if not _CODING_TURN and _net_status.answers_network_question(user_text):
            global _CURSIV_REPLY
            _CURSIV_REPLY = True
            yield _net_status.network_answer()
            return
        # "Is it safe?" with nothing earlier saying what "it" is: ask, don't guess (core/clarify.py).
        # Not when the calculator already worked it out: "How far is it from 44.1234, -71.5678 to
        # 44.13, -71.56?" was asked what "it" meant (benchmark num-034, suite 1.4).
        if not (_self_turn or _CODING_TURN or _WORKED or (locals().get("_ph") and _ph.emergency)):
            from cursiv_v215.core import clarify as _clarify
            _vague = _clarify.needs_clarifying(user_text, history)
            if _vague:
                # The model ignored the instruction and answered "Yes, it's safe" (site recording,
                # 2026-10-18), so Cursiv asks the question itself.
                _CURSIV_REPLY = True
                yield _clarify.question(_vague)
                return
    except Exception:
        pass

    # Cursiv's offline reference (core/reference.py): an entry that covers the
    # question goes into the prompt with an ID to cite, and the person sees which.
    try:
        _crisis = bool(locals().get("_ph") and _ph.emergency and _ph.emergency_kind != "medical")
        if not (_self_turn or _CODING_TURN or _crisis):
            from cursiv_v215.core import reference as _ref_data
            _found = _ref_data.lookup(user_text)
            if _found:
                _REF_SHOWN[:] = [e.title for e in _found]
                _ref_block = _ref_data.prompt_block(_found)
                messages[0]["content"] += "\n\n" + _ref_block + "\n"
                _RETRIEVED.append(_ref_block)
                yield _ref_data.note_line(_found) + "\n\n"
            elif _ref_data.is_safety_question(user_text):
                messages[0]["content"] += "\n\n" + _ref_data.NO_ENTRY_NOTE + "\n"
    except Exception:
        pass

    # The team's own documents (core/documents.py, research roadmap R3): matching passages
    # go into the prompt with page labels, and the person sees which pages were used.
    # Documents-only mode: with documents imported and nothing matching, Cursiv says so
    # itself, except in an emergency, where safety comes first.
    try:
        if not (_self_turn or _CODING_TURN):
            from cursiv_v215.core import documents as _docs
            if _docs.library():
                _passages_found = _docs.search(user_text)
                _emergency_now = bool(locals().get("_ph") and _ph.emergency)
                if _passages_found:
                    _DOCS_SHOWN[:] = _passages_found
                    # A passage that talks to the AI: flagged to the person, and saved memories are
                    # taken out of the prompt, so a document can never get them out (core/documents.py).
                    _inj = _docs.instruction_flags(_passages_found)
                    if _inj:
                        global _MEMORY_RECALLED
                        if _MEMORY_CTX:
                            messages[0]["content"] = messages[0]["content"].replace(
                                _MEMORY_CTX, "(Saved memories withheld for this answer: a document in it contains "
                                             "instructions.)")
                        _MEMORY_TEXTS.clear()
                        _MEMORY_RECALLED = False
                        yield _docs.instruction_note(_inj) + "\n\n"
                    _doc_block = _docs.prompt_block(_passages_found, _docs.only_mode() and not _emergency_now)
                    messages[0]["content"] += "\n\n" + _doc_block + "\n"
                    _RETRIEVED.append(_doc_block)
                    yield _docs.note_line(_passages_found) + "\n\n"
                elif _docs.only_mode() and not _emergency_now:
                    _CURSIV_REPLY = True
                    yield _docs.NOT_IN_DOCS
                    return
                elif _docs.ASKS_ABOUT_DOCS.search(user_text):
                    _names = [d["name"] for d in _docs.library()]
                    _DOCS_SEARCHED_EMPTY[:] = _names
                    messages[0]["content"] += "\n\n" + _docs.nothing_found_block(_names) + "\n"
                    yield _docs.nothing_found_note(_names) + "\n\n"
    except Exception:
        pass

    # Safety rule, assumption ledger, and earlier ledgers. Appended last so the
    # coding-brain prompt swap above does not drop them. The check itself runs
    # in chat() once the draft is complete (core/verify.py).
    try:
        if not (locals().get("_ph") and getattr(_ph, "emergency", False)):
            from cursiv_v215.core import verify as _verify
            _vadd = _verify.prompt_addendum(user_text)
            if _vadd:
                messages[0]["content"] += "\n\n" + _vadd + "\n"
    except Exception:
        pass

    # Codex Agent is invoked explicitly via the `codex <prompt>` command only.
    # Auto-intercept is disabled — Ollama handles coding Q&A directly with the
    # full system prompt injected, which produces better answers than Codex for
    # conversational coding questions.
    _fp_early = (force_provider or "").lower().strip()

    # ── Smart model routing ─────────────────────────────────────────────
    key = (api_key or "").strip()
    oai = (openai_key or "").strip()
    ant = (anthropic_key or "").strip()
    has_images = len(image_parts) > 0
    fp         = (force_provider or "").lower().strip()
    if not netgate.allowed():
        # Offline mode: saved keys stay saved but aren't used; the local model answers.
        key = oai = ant = ""
        if fp in ("grok", "claude", "openai", "council"):
            yield f"*[{fp.title()} skipped. {netgate.OFFLINE_MESSAGE} Answering with the local model.]*\n\n"
            fp = "ollama"

    def _workspace() -> Path:
        return (Path(root_path.strip()).expanduser().resolve()
                if root_path.strip() else ROOT)

    # ── Forced provider (grok / claude / openai commands) ───────────────
    if fp in ("grok", "claude", "openai", "ollama"):
        _set_answered({"grok": "xAI", "claude": "Claude", "openai": "OpenAI"}.get(fp) or _ollama_label())
    if fp == "grok":
        if file_access and key:
            yield from _call_xai_with_tools(messages, key, _workspace(), oai,
                                             has_images, confirm_writes=confirm_writes,
                                             anthropic_key="")
        elif key:
            yield from _call_xai_stream(messages, key, has_images)
        else:
            yield "[No xAI key set — type: key xai-xxxxx]"
        return
    elif fp == "claude":
        if file_access and ant:
            yield from _call_claude_with_tools(messages, ant, _workspace(),
                                                confirm_writes=confirm_writes,
                                                is_owner=_owner_active())
        elif ant:
            yield from _call_claude_direct(messages, ant)
        else:
            yield "[No Anthropic key set — type: anthropic sk-ant-xxxxx]"
        return
    elif fp == "openai":
        if oai:
            yield from _call_openai_direct(messages, oai)
        else:
            yield "[No OpenAI key set — type: openai sk-xxxxx]"
        return
    elif fp == "ollama":
        text_msgs = [
            {"role": m["role"],
             "content": m["content"] if isinstance(m["content"], str)
                        else next((p["text"] for p in m["content"] if p["type"] == "text"), "")}
            for m in messages
        ]
        yield from _call_ollama(text_msgs)
        return

    elif fp == "council":
        raw = user_text.strip()
        _sys_ctx = "\n\n".join(
            m["content"] for m in messages
            if m.get("role") == "system" and isinstance(m.get("content"), str)
        )
        yield from _call_provider_council(raw, key, oai, ant, system_context=_sys_ctx)
        return

    _text_msgs_all = [
        {"role": m["role"],
         "content": m["content"] if isinstance(m["content"], str)
                    else next((p["text"] for p in m["content"] if p["type"] == "text"), "")}
        for m in messages
    ]

    # ── Local first: the local model answers whenever it has one. Keys are
    # fallbacks -- and the way to read pasted images (the local chat model
    # can't see them) or to write files (only the tool-using paid providers can).
    _tool_writer = file_access and (key or oai or ant)
    _local_tried = False
    if not has_images and not _tool_writer and _local_model_ready():
        _local_tried = True
        _label, _lgen = _local_stream(_text_msgs_all, user_text)
        _first = next(_lgen, None)
        if _first is not None and not _first.lstrip().startswith("[Ollama"):
            _set_answered(_ollama_label(_label))
            yield _first
            yield from _lgen
            return

    # Nothing online is set up either (no keys, no Cursiv Cloud): the same as offline.
    if not (_cloud_configured(key, oai, ant) or cloud_enabled()) and (_local_tried or not _local_model_ready()):
        yield from _without_model()
        return

    # ── Offline detection — skip all cloud providers immediately ────────
    if not _is_online():
        if _local_tried or not _local_model_ready():
            yield from _without_model()
            return
        _set_answered(_ollama_label())
        yield from _call_ollama(_text_msgs_all)
        return

    # ── Smart routing — cascade: xAI → OpenAI → Claude → Ollama ────────
    def _fa_error(chunk: str, provider: str) -> bool:
        if chunk == RATE_SENTINEL:
            return True
        s = chunk.strip()
        return (
            s.startswith(f"[{provider} error") or
            s.startswith(f"\n[{provider} error") or
            "urlopen error" in s or
            "getaddrinfo failed" in s
        )

    def _safe_first(gen):
        """Get first chunk; return RATE_SENTINEL on any connection exception."""
        try:
            return next(gen, None)
        except Exception:
            return RATE_SENTINEL

    def _text_only_msgs(msgs):
        return [
            {"role": m["role"],
             "content": m["content"] if isinstance(m["content"], str)
                        else next((p["text"] for p in m["content"] if p["type"] == "text"), "")}
            for m in msgs
        ]

    if file_access:
        _fa_done = False

        if key and not _fa_done:
            gen   = _call_xai_with_tools(messages, key, _workspace(), oai, has_images,
                                          confirm_writes=confirm_writes, anthropic_key=ant)
            first = _safe_first(gen)
            if first is not None and not _fa_error(first, "xAI"):
                _set_answered("xAI")
                yield first
                yield from gen
                _fa_done = True

        if oai and not _fa_done:
            gen   = _call_openai_with_tools(messages, oai, _workspace(),
                                             anthropic_key=ant, confirm_writes=confirm_writes)
            first = _safe_first(gen)
            if first is not None and not _fa_error(first, "OpenAI"):
                _set_answered("OpenAI")
                yield first
                yield from gen
                _fa_done = True

        if ant and not _fa_done:
            gen   = _call_claude_with_tools(messages, ant, _workspace(),
                                             confirm_writes=confirm_writes,
                                             is_owner=_owner_active())
            first = _safe_first(gen)
            if first is not None and not _fa_error(first, "Claude"):
                _set_answered("Claude")
                yield first
                yield from gen
                _fa_done = True

        # Offline fallback — all cloud providers exhausted or unreachable
        # Ollama is local with no token rate limits — unlimited in offline mode
        if not _fa_done:
            yield from _fallback_chain(_text_only_msgs(messages), user_text,
                                       [n for n, k in (("xAI", key), ("OpenAI", oai), ("Claude", ant)) if k],
                                       local_tried=_local_tried)

    else:
        # ── Cascade for plain chat: xAI → OpenAI → Claude → Ollama ──────
        tried: list[str] = []

        def _text_only(msgs):
            return [
                {"role": m["role"],
                 "content": m["content"] if isinstance(m["content"], str)
                            else next((p["text"] for p in m["content"] if p["type"] == "text"), "")}
                for m in msgs
            ]

        # 1. xAI Grok
        if key:
            tried.append("xAI")
            gen   = _call_xai_stream(messages, key, has_images)
            first = next(gen, None)
            if first not in (RATE_SENTINEL, None) and not (
                isinstance(first, str) and first.startswith("[xAI auth")
            ):
                _set_answered("xAI")
                yield first
                for chunk in gen:
                    if chunk != RATE_SENTINEL:
                        yield chunk
                return
            # xAI failed — continue cascade

        # 2. OpenAI
        if oai:
            tried.append("OpenAI")
            gen   = _call_openai_direct(messages, oai)
            first = next(gen, None)
            if first is not None and not (
                isinstance(first, str) and first.lstrip().startswith("[OpenAI error")
            ):
                if len(tried) > 1:
                    yield f"*[{' → '.join(tried[:-1])} unavailable — OpenAI]*\n\n"
                _set_answered("OpenAI")
                yield first
                yield from gen
                return
            # OpenAI failed — continue cascade

        # 3. Claude
        if ant:
            tried.append("Claude")
            gen   = _call_claude_direct(messages, ant)
            first = next(gen, None)
            if first not in (RATE_SENTINEL, None) and not (
                isinstance(first, str) and first.lstrip().startswith("[Claude error")
            ):
                if len(tried) > 1:
                    yield f"*[{' → '.join(tried[:-1])} unavailable — Claude]*\n\n"
                _set_answered("Claude")
                yield first
                yield from gen
                return
            # Claude failed — fall to Ollama

        # 4. Free providers (own Gemini/Groq keys), then local Ollama -- or
        #    Cursiv Cloud when no local model is ready.
        yield from _fallback_chain(_text_only(messages), user_text, tried, local_tried=_local_tried)


def _local_stream(text_msgs: list[dict], user_text: str) -> tuple[str, Generator[str, None, None]]:
    """The local model's reply -- the coding pair for code questions, unless a
    small GPU already has the chat model loaded (switching costs minutes)."""
    _is_code = _classify_message(user_text) == "code"
    try:
        from cursiv_v215.core import speed as _speed
        if _is_code and _speed.small_gpu():
            _loaded = _speed.loaded_models()
            if _loaded and not any("coder" in m for m in _loaded):
                _is_code = False
    except Exception:
        pass
    if _is_code:
        return "Code Council", _call_ollama_code_council(text_msgs)
    return "Ollama", _call_ollama(text_msgs)


def _fallback_chain(text_msgs: list[dict], user_text: str, tried: list[str],
                    local_tried: bool = False) -> Generator[str, None, None]:
    """Last part of chat()'s cascade, after the paid providers: the user's own
    free Gemini/Groq keys, then local Ollama. When Ollama has no usable model,
    Cursiv Cloud (if not turned off) answers before Ollama's first-time download."""
    # Groq first: it answers in under a second; Gemini is often overloaded on free keys
    for label, field, fn in (("Groq", "groq_key", _call_groq_direct), ("Gemini", "gemini_key", _call_gemini_direct)):
        key = _saved_key(field) if netgate.allowed() else ""
        if not key:
            continue
        tried.append(label)
        gen = fn(text_msgs, key)
        first = next(gen, None)
        if first is not None and not first.lstrip().startswith(f"[{label} error"):
            if len(tried) > 1:
                yield f"*[{' → '.join(tried[:-1])} unavailable — {label}]*\n\n"
            _set_answered(label)
            yield first
            yield from gen
            return

    if cloud_enabled() and not _local_model_ready():
        tried.append("Cursiv Cloud")
        gen = _call_cursiv_cloud(text_msgs)
        first = next(gen, None)
        if first is not None and not first.lstrip().startswith("[Cursiv Cloud error"):
            if len(tried) > 1:
                yield f"*[{' → '.join(tried[:-1])} unavailable — Cursiv Cloud]*\n\n"
            _set_answered("Cursiv Cloud")
            yield first
            yield from gen
            return

    if local_tried:     # it already had its turn first and didn't answer
        if tried:
            yield f"*[{', '.join(tried + ['the local model'])} didn't answer.]*"
        else:
            yield "*[The local model didn't answer. Try again in a moment, or add a free key in Settings.]*"
        return
    _label, ollama_gen = _local_stream(text_msgs, user_text)
    _is_code = _label == "Code Council"
    first_ol   = next(ollama_gen, None)
    if first_ol is not None:
        if not first_ol.lstrip().startswith("[Ollama"):
            _set_answered(_ollama_label(_label))
        if tried:
            _label = "Code Council" if _is_code else "Ollama"
            yield f"*[{' → '.join(tried)} unavailable — {_label}]*\n\n"
        yield first_ol
        yield from ollama_gen
    else:
        if tried:
            yield (
                f"*[{', '.join(tried)} unavailable and Ollama is not running.]*\n\n"
                "For offline answers, the local AI engine needs to be running: type `status` to see why it "
                "isn't, or open Setup to install the local model."
            )
        else:
            yield (
                "[No AI is available yet: no API key, Ollama isn't running, and Cursiv Cloud "
                + ("couldn't be reached" if cloud_enabled() else "is turned off ('cloud on' to use it)")
                + ".]\n\n"
                "**To run locally:** open Setup to install the local AI engine and model, or type `status` "
                "to see why the engine isn't running.\n\n"
                + FREE_KEY_HELP
            )



def _learn_later(message, reply: str, *, origin: str = "inferred", skip: bool = False) -> None:
    """Save lasting facts from this exchange (memory/semantic.py), off the UI thread.

    origin is verified only after the verification pass came back clean.
    skip is set when that pass found problems, so the draft is not stored.
    """
    if skip:
        return
    if origin not in ("inferred", "verified"):
        origin = "inferred"
    text = message.get("text", "") if isinstance(message, dict) else str(message or "")
    # drop Cursiv's own status lines ("*[Answered by …]*", routing notes) before judging the reply
    reply = _strip_status_lines(reply or "")
    if not reply.strip() or reply.lstrip().startswith("[") or len(text.strip()) < 15:
        return
    coding = _CODING_TURN
    def work():
        try:
            from cursiv_v215.memory import semantic as _sem
            if len(text.strip()) >= 20:
                _sem.learn_from_exchange(text, reply, _quick_llm, origin=origin)
            try:              # project memory: running summary of ongoing projects
                from cursiv_v215.memory import projects as _proj
                _proj.learn(text, reply, _quick_llm, _sem.current_person())
            except Exception:
                pass
            if coding:        # coding lessons: their setup, errors hit, fixes that worked
                from cursiv_v215.coding import brain as _cb
                _cb.learn_from_exchange(text, reply, _quick_llm, _sem.current_person())
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()


_PHASE_AFTER = ""   # end-of-reply note from core/phases.py for the current message
_EMERGENCY_TURN = False   # phases flagged a crisis / medical emergency / danger this turn
_CURSIV_REPLY = False     # Cursiv answered itself (no model), so there's no model answer to check
_CODING_TURN = False  # this message went through the coding brain (cursiv_v215/coding)

_SENTENCE_END = (".", "!", "?", "\n", ":", ";")


def _time_boxed(gen, seconds: float = RESPONSE_TIME_LIMIT, grace: float = 12.0):
    """Stream a reply, but once `seconds` have passed, finish the current
    sentence (up to `grace` more seconds) and stop cleanly with a note --
    instead of either cutting off mid-sentence or typing for five minutes."""
    if not seconds or seconds <= 0:
        yield from gen          # no time limit
        return
    import time as _t
    start = _t.monotonic()
    stopping = False
    for chunk in gen:
        if not isinstance(chunk, str) or chunk in (RATE_SENTINEL, WRITE_SENTINEL) or chunk.startswith(WRITE_SENTINEL):
            yield chunk
            continue
        elapsed = _t.monotonic() - start
        if not stopping and elapsed > seconds:
            stopping = True
        if stopping:
            cut = max(chunk.rfind(c) for c in _SENTENCE_END)
            if cut >= 0 or elapsed > seconds + grace:
                yield chunk[:cut + 1] if cut >= 0 else chunk
                try:
                    gen.close()
                except Exception:
                    pass
                yield ("\n\n*[Stopped after about {0} seconds to keep things quick — say "
                       "\"continue\" and I'll pick up right where I left off.]*").format(int(seconds))
                return
        yield chunk


def chat(
    message: dict | str,
    history: list[dict],
    api_key: str,
    files: list | None,
    file_access: bool = False,
    root_path: str = "",
    openai_key: str = "",
    confirm_writes: bool = False,
    anthropic_key: str = "",
    force_provider: str = "",
    replace_draft: bool = False,
) -> Generator[str, None, None]:
    """Cursiv's main chat entry point: _chat_inner, time-boxed (see _time_boxed).

    replace_draft: when the check revises the answer, yield REPLACE_SENTINEL +
    the final reply instead of appending the revision under the draft (C-007).

    After the draft has streamed, one verification pass may append a revision
    or the problems it could not clear. Lasting facts are then learned in the
    background. Casual turns skip the pass.
    """
    global _PHASE_AFTER, _EMERGENCY_TURN, _CURSIV_REPLY
    _PHASE_AFTER = ""                # set by the phases for this message only
    _EMERGENCY_TURN = False
    _CURSIV_REPLY = False
    reply: list[str] = []
    from cursiv_v215.core import speed as _speed
    _speed.chat_started()
    origin, skip = "inferred", False
    try:
        yield from _chat_stream(message, history, api_key, files, file_access, root_path,
                                openai_key, confirm_writes, anthropic_key, force_provider, reply)
        draft = _strip_status_lines("".join(reply))      # the model's words, not Cursiv's notes
        if _WORKED and _WORKED.lead and draft.startswith(_WORKED.lead.strip()):
            draft = draft[len(_WORKED.lead.strip()):].strip()    # nor Cursiv's own safety line
        if _PHASE_AFTER:             # Route / Recovery notes from the phases
            reply.append(_PHASE_AFTER)
            yield _PHASE_AFTER
        # No model call, so it runs on emergency turns too (core/answer_check.py).
        try:
            from cursiv_v215.core import answer_check as _ac
            # An answer that opens "Yes, it's safe" and then says not to go: the warning goes on
            # top, where it's read first (benchmark saf-012, U67).
            _lead = _ac.lead_warning(draft) if replace_draft else ""
            if _lead:
                _full = "".join(reply)
                _at = _full.find(draft[:60]) if draft[:60] else -1
                _full = (_full[:_at] + _lead + "\n\n" + _full[_at:]) if _at >= 0 else (_lead + "\n\n" + _full)
                reply[:] = [_full]
                yield REPLACE_SENTINEL + _full
            _flag = _ac.notes(draft, list(_REF_SHOWN), _WEB_SEARCHED, flip_above=bool(_lead))
            if _DOCS_SHOWN:
                from cursiv_v215.core import documents as _docs
                _bad_cites = _docs.cited_pages_problems(draft, list(_DOCS_SHOWN))
                if _bad_cites:
                    _flag += "\n\n*(Cursiv's check: the answer " + "; ".join(_bad_cites) + ". Check it against the pages listed above.)*"
            if _WORKED:
                from cursiv_v215.core import calc as _calc
                _miss = _calc.check(draft, _WORKED)
                _flag += ("\n\n" + _miss) if _miss else ""
            # What the answer says Cursiv did, against what Cursiv's code recorded (core/claims.py)
            from cursiv_v215.core import claims as _claims
            _flag += _claims.notes(draft, _evidence(message, history))
            if _flag:
                reply.append(_flag)
                yield _flag
        except Exception:
            pass
        # Still inside this turn, so the check uses the fast router (no idle wait)
        # and background learning cannot take the local model yet.
        try:
            if _EMERGENCY_TURN or _CURSIV_REPLY or _speed.battery_saver():
                raise _SkipCheck      # no slow check (or a wall of notes) after emergency steps
            from cursiv_v215.core import verify as _verify
            user_text = message.get("text", "") if isinstance(message, dict) else str(message or "")
            outcome = _verify.run_pass(
                user_text, draft,
                ask=lambda msgs: _router_llm(msgs, max_tokens=500),
                memory_update=_verify.looks_like_memory_update(user_text),
                context=_check_context(history, user_text),
                sources="\n\n".join(_RETRIEVED + ([f"Worked out by Cursiv's code (exact): {_WORKED.statement}"]
                                                    if _WORKED else [])),
            )
            origin, skip = outcome.learn_origin, outcome.skip_learn
            revised = outcome.append.split("**Revised after check:**\n", 1)
            if replace_draft and outcome.append and len(revised) == 2 and outcome.clear:
                final = _replacement_reply(revised[1], "".join(reply), outcome.problems)
                reply[:] = [final]
                yield REPLACE_SENTINEL + final
            elif outcome.append:
                shown = _compact_notes(outcome) if "**Draft + notes:**" in outcome.append else outcome.append
                reply.append(shown)
                yield shown
        except _SkipCheck:
            pass
        except Exception:
            pass
    finally:
        _speed.chat_finished()
    _learn_later(message, "".join(reply), origin=origin, skip=skip)


class _SkipCheck(Exception):
    pass


def _evidence(message, history) -> "object":
    """This turn's record for core/claims.py: what actually ran, was given, was saved."""
    from cursiv_v215.core import claims as _claims
    earlier = []
    for m in (history or [])[-8:]:
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if not isinstance(content, str):
                content = next((p.get("text", "") for p in content if p.get("type") == "text"), "")
            earlier.append(_strip_status_lines(content))
    return _claims.Evidence(
        question=message.get("text", "") if isinstance(message, dict) else str(message or ""),
        worked=_WORKED.record() if _WORKED else None,
        worked_facts=dict(_WORKED.facts) if _WORKED else {},
        ref_ids=list(_ref_evidence()),
        ref_meta=_ref_evidence(),
        memory_texts=list(_MEMORY_TEXTS),
        memory_saved=False,                 # a model turn never saves; only `remember` / "save this" do
        searched=_WEB_SEARCHED,
        docs=list(dict.fromkeys(p.name for p in _DOCS_SHOWN)),
        earlier=earlier,
    )


def _compact_notes(outcome) -> str:
    """The check's problems, readable: at most three short items. The checker's raw
    reply (headings, repeats, "CLEAR") isn't shown as-is."""
    items = []
    for problem in outcome.problems:
        for line in str(problem).splitlines():
            line = line.strip().lstrip("-*0123456789. ").strip("* ").strip()
            if (len(line) < 12 or line.endswith(":") or "CLEAR" in line
                    or line.lower().startswith(("none", "final answer", "additional information", "a revised draft"))):
                continue
            items.append(line if len(line) <= 160 else line[:157].rstrip() + "...")
            break                       # one line per problem
        if len(items) == 3:
            break
    if not items:
        return ""
    body = "\n".join(f"- {item}" for item in items)
    return f"\n\n---\n**Checked, with notes** (the answer above wasn't changed):\n{body}"


def _replacement_reply(revised: str, shown: str, problems: list[str]) -> str:
    """The reply that replaces a revised draft: the revision, a short note on what
    the check found, then Cursiv's own status lines from the draft (reference
    note, "Answered by ...")."""
    notes = [m.group(0).strip() for m in _STATUS_LINE_RE.finditer(shown)]
    found = "; ".join(p.rstrip(".") for p in problems[:3])
    head = f"*(Revised after a check{': the first draft ' + found if found else ''}.)*"
    return "\n\n".join([revised.strip(), head, *notes])


def _check_context(history: list[dict], user_text: str) -> str:
    """What the checker may treat as already established: the last few turns and the
    memories recalled for this question. Without it, a correct follow-up or a
    memory-based answer reads as an unsupported claim."""
    parts: list[str] = []
    turns = []
    for m in (history or [])[-6:]:
        content = m.get("content", "")
        if not isinstance(content, str):
            content = next((p.get("text", "") for p in content if p.get("type") == "text"), "")
        text = _strip_status_lines(content)
        if text:
            turns.append(f"{m.get('role', 'user')}: {text[:800]}")
    if turns:
        parts.append("Earlier in this conversation:\n" + "\n".join(turns))
    try:
        from cursiv_v215.memory import semantic as _sem
        recalled = _sem.build_context(user_text)
        if recalled:
            parts.append("Saved memory recalled for this question:\n" + recalled)
    except Exception:
        pass
    return "\n\n".join(parts)


def _chat_stream(message, history, api_key, files, file_access, root_path, openai_key,
                 confirm_writes, anthropic_key, force_provider, reply: list[str]):
    from cursiv_v215.core import selfknow as _sk
    global _WEB_SEARCHED, _WORKED, _MEMORY_RECALLED
    _WORKED = None
    _MEMORY_RECALLED = False
    _MEMORY_TEXTS.clear()
    global _MEMORY_CTX
    _MEMORY_CTX = ""
    _REAL_TOOL_NOTES.clear()
    _RETRIEVED.clear()
    _REF_SHOWN.clear()
    _DOCS_SHOWN.clear()
    _DOCS_SEARCHED_EMPTY.clear()
    _WEB_SEARCHED = False
    _set_answered("")
    for chunk in _drop_fake_tool_lines(_friendly(_sk, _time_boxed(_chat_inner(message=message, history=history, api_key=api_key, files=files, file_access=file_access, root_path=root_path, openai_key=openai_key, confirm_writes=confirm_writes, anthropic_key=anthropic_key, force_provider=force_provider)))):
        if isinstance(chunk, str) and chunk not in (RATE_SENTINEL,) and not chunk.startswith(WRITE_SENTINEL):
            reply.append(chunk)
        yield chunk
    if _ANSWERED_BY or _CURSIV_REPLY:   # what the answer was given (Cursiv's records, not the model's)
        _asked = message.get("text", "") if isinstance(message, dict) else str(message or "")
        note = f"\n\n*[{sources_line(''.join(reply), _asked)}]*"
        reply.append(note)
        yield note
    if _ANSWERED_BY:     # say which engine answered (written by Cursiv, not the model)
        note = f"\n*[Answered by {_ANSWERED_BY}]*"
        reply.append(note)
        yield note


def _friendly(sk, gen):
    """Swap raw provider errors ("[Groq error 413: {...}]") for a plain sentence."""
    for chunk in gen:
        if isinstance(chunk, str) and "[" in chunk[:4]:
            nice = sk.friendly_error(chunk)
            if nice:
                yield nice
                continue
        yield chunk


def _router_llm(messages: list[dict], max_tokens: int = 300) -> str:
    """Fast, small calls during a chat (tool routing, the verification pass): the local
    model directly when one is ready -- not _quick_llm, which waits until no chat is
    running. The user's free keys only when there is no local model, so a turn the
    local model answered never leaves this computer for its check."""
    if _ollama_running() and _resolve_ollama_model():
        return _local_llm(messages, max_tokens)
    return _free_key_llm(messages, max_tokens)


def warm_up_local() -> None:
    """Load the local chat model ahead of the first message (call off the UI thread)."""
    try:
        from cursiv_v215.core import speed
        if _ollama_running():
            speed.warm_up(_resolve_ollama_model() or "")
    except Exception:
        pass

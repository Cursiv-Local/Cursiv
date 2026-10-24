"""
Cursiv chat engine -- everything behind the desktop chat panel: building the
system prompt, routing to a model (paid keys, then Groq, Gemini, the local
Ollama model or Cursiv Cloud), saving and testing keys, tools, and memory
context. The desktop window (launcher/chat_panel.py, chat_commands.py) calls
into this module; it has no user interface of its own.
"""

from __future__ import annotations

import sys as _sys
from typing import cast as _cast
from cursiv_engine.chat.runtime import ChatRuntime
from cursiv_engine.chat import cloud_providers as _cloud_providers
from cursiv_engine.chat import completion as _completion
from cursiv_engine.chat import context as _context
from cursiv_engine.chat import conversation as _conversation
from cursiv_engine.chat import local_provider as _local_provider
from cursiv_engine.chat import provider_tools as _provider_tools
from cursiv_engine.chat import routing as _routing
from cursiv_engine.chat import streaming as _streaming
from cursiv_engine.chat import uploads as _uploads


def _runtime() -> ChatRuntime:
    """Explicit compatibility services: callables and per-turn records live here."""
    return _cast(ChatRuntime, _sys.modules[__name__])

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

from cursiv_engine.core import netgate   # installs the offline backstop; see core/netgate.py
from cursiv_engine.core import turn_policy
from cursiv_engine.core import grounding
from cursiv_engine.guardian.protected import is_protected_path as _guardian_protected

from cursiv_engine.chat.optional import (  # noqa: E402,F401  (moved; chat_app re-exports)
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
    """Compatibility entry point; implementation in chat.context."""
    return _context._owner_active(_runtime())


from cursiv_engine.chat.web_search import (  # noqa: E402,F401  (moved; chat_app re-exports)
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
    from cursiv_engine.guardian.owner import unlock_owner_session as _unlock_owner
    from cursiv_engine.guardian.owner import is_owner_session     as _is_owner_session
    from cursiv_engine.guardian.owner import verify_owner_code    as _verify_owner_code
    from cursiv_engine.guardian.owner import set_owner_code       as _set_owner_code
    from cursiv_engine.guardian.owner import owner_code_is_set    as _owner_code_is_set
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
SYSTEM_PROMPT_FILE = ROOT / "cursiv_engine" / "codex" / "system_prompt.md"
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)
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
    """Compatibility entry point; implementation in chat.context."""
    return _context._cursiv_encode(_runtime(), text)


def _cursiv_decode(binary: str) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._cursiv_decode(_runtime(), binary)


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
                "Call the Cursiv Codex coding specialist to generate production-ready code or Cursiv agent packs. "
                "Use this when you need to write code — it produces a structured artifact with "
                "READY-TO-RUN CODE and JSON FILES in the project's own style. "
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

def _existing_file(args: dict, root: Path) -> bool:
    """Compatibility entry point; implementation in chat.context."""
    return _context._existing_file(_runtime(), args, root)



def _pending_file(args: dict, root: Path) -> dict:
    """Compatibility entry point; implementation in chat.context."""
    return _context._pending_file(_runtime(), args, root)



def _file_tool_result(name: str, args: dict, root: Path | None, *, confirmed: bool=False):
    """Compatibility entry point; implementation in chat.context."""
    return _context._file_tool_result(_runtime(), name, args, root, confirmed=confirmed)



def execute_tool(name: str, args: dict, root: Path, *, confirmed: bool=False) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context.execute_tool(_runtime(), name, args, root, confirmed=confirmed)


# ── Owner reveal ──────────────────────────────────────────────────────────

def _build_owner_reveal() -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._build_owner_reveal(_runtime())



def _compact_system_for_tools(is_owner: bool=False) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._compact_system_for_tools(_runtime(), is_owner)



def _build_strand_context(query: str, top_k: int=2) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._build_strand_context(_runtime(), query, top_k)



def _build_live_status() -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._build_live_status(_runtime())



def load_system_prompt() -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context.load_system_prompt(_runtime())



def load_vault_context() -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context.load_vault_context(_runtime())



# ── File processing ────────────────────────────────────────────────────────

def _read_text_file(path: Path) -> str:
    """Compatibility entry point; implementation in chat.uploads."""
    return _uploads._read_text_file(_runtime(), path)



def process_uploaded_files(files: list | None) -> tuple[str, list[dict]]:
    """Compatibility entry point; implementation in chat.uploads."""
    return _uploads.process_uploaded_files(_runtime(), files)



# ── LLM callers ───────────────────────────────────────────────────────────

def _call_ollama_raw(messages: list[dict], max_tokens: int=RESPONSE_MAX_TOKENS, standard: bool=False) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._call_ollama_raw(_runtime(), messages, max_tokens, standard)



def _call_ollama(messages: list[dict], max_tokens: int=RESPONSE_MAX_TOKENS, standard: bool=False) -> 'Generator[str, None, None]':
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._call_ollama(_runtime(), messages, max_tokens, standard)



def _ollama_running() -> bool:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._ollama_running(_runtime())



def _ensure_ollama() -> bool:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._ensure_ollama(_runtime())



def _ollama_pulled_models() -> set[str]:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._ollama_pulled_models(_runtime())



# Preference order when OLLAMA_MODEL isn't pulled: the owner's own fine-tuned
# model first (training/ollama_merge.py), then its base, then anything else.
_OLLAMA_FALLBACK_MODELS = ("cursiv-tuned", "qwen2.5:1.5b", "qwen2.5")


def _ollama_tags() -> list[str] | None:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._ollama_tags(_runtime())



def _models_on_disk() -> bool:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._models_on_disk(_runtime())



def _resolve_ollama_model(standard: bool=False) -> str | None:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._resolve_ollama_model(_runtime(), standard)



def _pull_ollama_model(model: str) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._pull_ollama_model(_runtime(), model)



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

# Saved keys: cursiv_engine/chat/keys.py (encrypted for this Windows account).
from cursiv_engine.chat.keys import saved_key as _saved_key, store_key as _store_key  # noqa: E402
_CLOUD_FILE    = Path.home() / ".cursiv" / "cursiv_cloud.json"


def _text_messages(messages: list[dict]) -> list[dict]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._text_messages(_runtime(), messages)



def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._post_json(_runtime(), url, payload, headers, timeout)



_FULL_PERSONA = ""   # the full persona prefix of the current system prompt (set in _chat_inner)


def _slim(messages: list[dict], budget: int) -> list[dict]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._slim(_runtime(), messages, budget)



def _call_gemini_direct(messages: list[dict], key: str, max_tokens: int=RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_gemini_direct(_runtime(), messages, key, max_tokens)



def check_free_key(field: str, key: str) -> tuple[bool, str]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers.check_free_key(_runtime(), field, key)



def _call_groq_direct(messages: list[dict], key: str, max_tokens: int=RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_groq_direct(_runtime(), messages, key, max_tokens)



def _cloud_settings() -> dict:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._cloud_settings(_runtime())



def _save_cloud_settings(data: dict) -> None:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._save_cloud_settings(_runtime(), data)



def cloud_enabled() -> bool:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers.cloud_enabled(_runtime())



def set_cloud_enabled(on: bool) -> None:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers.set_cloud_enabled(_runtime(), on)



def _call_cursiv_cloud(messages: list[dict], max_tokens: int=RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_cursiv_cloud(_runtime(), messages, max_tokens)



def free_key_command(text: str) -> str | None:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers.free_key_command(_runtime(), text)



def _local_llm(messages: list[dict], max_tokens: int) -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._local_llm(_runtime(), messages, max_tokens)



def _free_key_llm(messages: list[dict], max_tokens: int) -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._free_key_llm(_runtime(), messages, max_tokens)



def _quick_llm(messages: list[dict], max_tokens: int=400) -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._quick_llm(_runtime(), messages, max_tokens)



def _memory_llm(messages: list[dict], max_tokens: int=400) -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._memory_llm(_runtime(), messages, max_tokens)



def _local_model_ready() -> bool:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._local_model_ready(_runtime())



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


def _memory_used(answer: str, question: str='') -> bool:
    """Compatibility entry point; implementation in chat.context."""
    return _context._memory_used(_runtime(), answer, question)



_COMMON_WORDS = {"about", "after", "also", "been", "from", "have", "into", "just", "like", "more", "much", "only",
                 "over", "some", "that", "their", "them", "then", "there", "they", "this", "time", "very", "what",
                 "when", "with", "would", "your", "user", "likes", "prefers", "wants", "family", "people"}
_DOCS_SEARCHED_EMPTY: list = []        # document names searched this turn with nothing matching


def _ref_evidence() -> dict:
    """Compatibility entry point; implementation in chat.context."""
    return _context._ref_evidence(_runtime())



def sources_line(answer: str='', question: str='') -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context.sources_line(_runtime(), answer, question)



def _without_model():
    """Compatibility entry point; implementation in chat.context."""
    return _context._without_model(_runtime())



_NOTES_BLOCK_RE = _re.compile(r"\n*-{3,}\n\*\*(Checked, with notes|Draft \+ notes)\*\*[\s\S]*$")


def _strip_status_lines(text: str) -> str:
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._strip_status_lines(_runtime(), text)



def _set_answered(label: str) -> None:
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._set_answered(_runtime(), label)



def _ollama_label(base: str='Ollama') -> str:
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._ollama_label(_runtime(), base)



def _drop_fake_tool_lines(gen: Generator) -> Generator:
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._drop_fake_tool_lines(_runtime(), gen)



def cascade_stream(messages: list[dict], keys: dict, max_tokens: int=RESPONSE_MAX_TOKENS, local_fn: Callable[[list[dict]], Generator[str, None, None]] | None=None) -> tuple[Generator[str, None, None], list[str]]:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing.cascade_stream(_runtime(), messages, keys, max_tokens, local_fn)



try:
    from cursiv_engine.guardian.identity_core import (
        wrap       as _identity_wrap,
        CURSIV_IDENTITY as _IDENTITY_OVERRIDE,
    )
except ImportError:
    from guardian.identity_core import (
        wrap       as _identity_wrap,
        CURSIV_IDENTITY as _IDENTITY_OVERRIDE,
    )


def _call_ollama_model(model: str, system_str: str, prompt: str, max_tokens: int=2000, collect: bool=False) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._call_ollama_model(_runtime(), model, system_str, prompt, max_tokens, collect)



def _big_gpu() -> bool:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._big_gpu(_runtime())



def _num_ctx() -> int:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._num_ctx(_runtime())



def _call_ollama_code_council(messages: list[dict], max_tokens: int=2000) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.local_provider."""
    return _local_provider._call_ollama_code_council(_runtime(), messages, max_tokens)



def _call_xai_stream(messages: list[dict], api_key: str, has_images: bool=False, max_tokens: int=RESPONSE_MAX_TOKENS) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_xai_stream(_runtime(), messages, api_key, has_images, max_tokens)



def _call_xai_non_stream(messages: list[dict], api_key: str, has_images: bool) -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_xai_non_stream(_runtime(), messages, api_key, has_images)



def _generate_with_openai(filepath: str, openai_key: str, context_messages: list[dict], grok_draft: str='') -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._generate_with_openai(_runtime(), filepath, openai_key, context_messages, grok_draft)



def _generate_with_claude(filepath: str, anthropic_key: str, context_messages: list[dict], grok_draft: str='') -> str:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._generate_with_claude(_runtime(), filepath, anthropic_key, context_messages, grok_draft)



def _call_claude_with_tools(messages: list[dict], anthropic_key: str, root: Path, confirm_writes: bool=False, max_tokens: int=4000, max_loops: int=20, is_owner: bool=False, on_action=None) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.provider_tools."""
    return _provider_tools._call_claude_with_tools(_runtime(), messages, anthropic_key, root, confirm_writes, max_tokens, max_loops, is_owner, on_action)



def _call_xai_with_tools(messages: list[dict], api_key: str, root: Path, openai_key: str='', has_images: bool=False, max_tokens: int=4000, max_loops: int=20, confirm_writes: bool=False, anthropic_key: str='', endpoint_url: str='', model_override: str='', provider_name: str='xAI', on_action=None) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.provider_tools."""
    return _provider_tools._call_xai_with_tools(_runtime(), messages, api_key, root, openai_key, has_images, max_tokens, max_loops, confirm_writes, anthropic_key, endpoint_url, model_override, provider_name, on_action)



def _call_openai_with_tools(messages: list[dict], openai_key: str, root: Path, anthropic_key: str='', max_tokens: int=4000, max_loops: int=20, confirm_writes: bool=False, on_action=None) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.provider_tools."""
    return _provider_tools._call_openai_with_tools(_runtime(), messages, openai_key, root, anthropic_key, max_tokens, max_loops, confirm_writes, on_action)



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
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._classify_message(_runtime(), text)



def _call_claude_direct(messages: list[dict], anthropic_key: str, max_tokens: int = 4096) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_claude_direct(_runtime(), messages, anthropic_key, max_tokens)



def _call_openai_direct(messages: list[dict], openai_key: str, max_tokens: int | None = None) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.cloud_providers."""
    return _cloud_providers._call_openai_direct(_runtime(), messages, openai_key, max_tokens)



def _call_provider_council(question: str, xai_key: str, openai_key: str, anthropic_key: str, system_context: str='') -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._call_provider_council(_runtime(), question, xai_key, openai_key, anthropic_key, system_context)



def _is_online() -> bool:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._is_online(_runtime())



def _cloud_configured(*keys: str) -> bool:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._cloud_configured(_runtime(), *keys)



def _connectivity_probe(*keys: str):
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._connectivity_probe(_runtime(), *keys)



# ── Core chat function ────────────────────────────────────────────────────

@turn_policy.scoped
def _chat_inner(message: dict | str, history: list[dict], api_key: str, files: list | None, file_access: bool=False, root_path: str='', openai_key: str='', confirm_writes: bool=False, anthropic_key: str='', force_provider: str='', on_action=None) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.conversation."""
    return _conversation._chat_inner(_runtime(), message, history, api_key, files, file_access, root_path, openai_key, confirm_writes, anthropic_key, force_provider, on_action)



def _local_stream(text_msgs: list[dict], user_text: str) -> tuple[str, Generator[str, None, None]]:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._local_stream(_runtime(), text_msgs, user_text)



def _fallback_chain(text_msgs: list[dict], user_text: str, tried: list[str], local_tried: bool=False) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._fallback_chain(_runtime(), text_msgs, user_text, tried, local_tried)




def _learn_later(message, reply: str, *, origin: str='inferred', skip: bool=False, person: str | None=None, event_id: str='') -> None:
    """Compatibility entry point; implementation in chat.completion."""
    return _completion._learn_later(_runtime(), message, reply, origin=origin, skip=skip, person=person, event_id=event_id)



_PHASE_AFTER = ""   # end-of-reply note from core/phases.py for the current message
_EMERGENCY_TURN = False   # phases flagged a crisis / medical emergency / danger this turn
_CURSIV_REPLY = False     # Cursiv answered itself (no model), so there's no model answer to check
_CODING_TURN = False  # this message went through the coding brain (cursiv_engine/coding)

_SENTENCE_END = (".", "!", "?", "\n", ":", ";")


def _time_boxed(gen, seconds: float=RESPONSE_TIME_LIMIT, grace: float=12.0):
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._time_boxed(_runtime(), gen, seconds, grace)



@turn_policy.scoped
@grounding.scoped
def chat(message: dict | str, history: list[dict], api_key: str, files: list | None, file_access: bool=False, root_path: str='', openai_key: str='', confirm_writes: bool=False, anthropic_key: str='', force_provider: str='', replace_draft: bool=False, on_stage: Callable[[str], None] | None=None, notebook_scope: str='', on_action=None, on_review=None, review_mode=None) -> Generator[str, None, None]:
    """Compatibility entry point; implementation in chat.completion."""
    return _completion.chat(_runtime(), message, history, api_key, files, file_access, root_path, openai_key, confirm_writes, anthropic_key, force_provider, replace_draft, on_stage, notebook_scope, on_action, on_review, review_mode)



class _SkipCheck(Exception):
    pass


def _evidence(message, history) -> 'object':
    """Compatibility entry point; implementation in chat.context."""
    return _context._evidence(_runtime(), message, history)



def _compact_notes(outcome) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._compact_notes(_runtime(), outcome)



def _replacement_reply(revised: str, shown: str, problems: list[str]) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._replacement_reply(_runtime(), revised, shown, problems)



def _check_context(history: list[dict], user_text: str) -> str:
    """Compatibility entry point; implementation in chat.context."""
    return _context._check_context(_runtime(), history, user_text)



def _chat_stream(message, history, api_key, files, file_access, root_path, openai_key, confirm_writes, anthropic_key, force_provider, reply: list[str], on_action=None):
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._chat_stream(_runtime(), message, history, api_key, files, file_access, root_path, openai_key, confirm_writes, anthropic_key, force_provider, reply, on_action)



def _friendly(sk, gen):
    """Compatibility entry point; implementation in chat.streaming."""
    return _streaming._friendly(_runtime(), sk, gen)



def _router_llm(messages: list[dict], max_tokens: int=300) -> str:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing._router_llm(_runtime(), messages, max_tokens)



def warm_up_local() -> None:
    """Compatibility entry point; implementation in chat.routing."""
    return _routing.warm_up_local(_runtime())

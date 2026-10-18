"""
Real self-knowledge: when someone asks Cursiv about itself, it answers from a
live report of its actual state -- not from its persona prompt, which made it
invent "14 running agents", hashes and problems that don't exist.

Also: plain-English versions of provider errors, and a short log of recent
ones (included in the report).
"""
from __future__ import annotations

import collections
import json
import re
import time
from pathlib import Path

VERSION = "3.14-U71"
FACTS_FILE = Path(__file__).parent.parent / "council" / "cursiv_facts.md"
RECENT_ERRORS: collections.deque = collections.deque(maxlen=8)

_SELF_RE = re.compile(
    r"\b(your|you'?re|yourself|cursiv'?s?)\b.{0,40}\b(system|internals?|status|health|version|setup|"
    r"architecture|code|agents?|council|memory|models?|keys?|working|diagnos\w*|analy[sz]\w*|"
    r"improv\w*|weak\w*|problems?|errors?|capabilit\w*|limits?|speed|slow)\b"
    r"|\b(self[- ]?(check|test|diagnos\w*|analy[sz]\w*|report))\b"
    r"|\b(system|status|health) (check|report)\b"
    r"|\bhow are (you|we) (doing|feeling|running)\b"
    r"|\bwhat (can|can't|cannot) you do\b",
    re.I | re.S)


def is_self_question(text: str) -> bool:
    return bool(_SELF_RE.search(text or ""))


# ── friendly errors ─────────────────────────────────────────────────────────

_ERR_RE = re.compile(r"^\s*\*?\[(xAI|OpenAI|Claude|Gemini|Groq|Cursiv Cloud|Ollama)[^\]]*?(error|unavailable|not found)[^\]]*\]\*?", re.I)


def friendly_error(chunk: str) -> str | None:
    """A plain sentence for a raw provider error chunk, or None if it isn't one."""
    m = _ERR_RE.match(chunk or "")
    if not m:
        return None
    raw = m.group(0)
    who = m.group(1)
    RECENT_ERRORS.append((time.strftime("%H:%M"), raw.strip()[:200]))
    low = raw.lower()
    if "401" in low or "403" in low or "invalid" in low and "key" in low:
        why = f"{who} rejected the key. Check it in ⚙ Settings."
    elif "413" in low or "too large" in low:
        why = f"that message was too long for {who}'s free tier."
    elif "429" in low or "rate" in low:
        why = f"{who} is busy (rate limit) — it frees up within a minute."
    elif "503" in low or "high demand" in low or "overloaded" in low:
        why = f"{who}'s servers are overloaded right now."
    elif "timed out" in low or "timeout" in low:
        why = f"{who} took too long to answer."
    elif who.lower() == "ollama":
        why = "the local AI (Ollama) isn't responding — open Setup and click Restart Ollama, or try again in a minute."
    else:
        why = f"{who} couldn't answer just now."
    return f"\n*(Couldn't get an answer: {why})*\n"


# ── live report ─────────────────────────────────────────────────────────────

def _safe(fn, default="unknown"):
    try:
        return fn()
    except Exception:
        return default


def live_report() -> str:
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import speed
    lines = [f"Version: Cursiv {VERSION} (Windows desktop app, PyQt window; phone app at cursiv.winklers-llc.com/app)"]

    keys = [label for label, f in (("Groq (free)", "groq_key"), ("Gemini (free)", "gemini_key"), ("Claude", "anthropic_key"),
                                   ("xAI Grok", "api_key"), ("OpenAI", "openai_key")) if _safe(lambda f=f: ca._saved_key(f), "")]
    lines.append("AI keys saved: " + (", ".join(keys) if keys else "none") +
                 " (order tried: paid keys, then Groq, then Gemini, then local Ollama / Cursiv Cloud)")
    lines.append(f"Cursiv Cloud backup: {'on' if _safe(ca.cloud_enabled, False) else 'off'} (used only when no local model is ready)")

    vram = _safe(speed.gpu_vram_mb, 0)
    lines.append(f"Graphics card memory: {vram} MB -> {'small-GPU settings (8k context, 3B models preferred)' if speed.small_gpu() else 'full settings'}")
    running = _safe(ca._ollama_running, False)
    tags = _safe(ca._ollama_tags, None) if running else None
    lines.append(f"Local AI (Ollama): {'running' if running else 'not running'}" +
                 (f"; installed models: {', '.join(tags) if tags else 'none'}" if running else ""))
    if running:
        lines.append(f"Chat model it would use now: {_safe(ca._resolve_ollama_model, 'none')}; "
                     f"loaded in memory: {', '.join(_safe(speed.loaded_models, [])) or 'nothing'}")

    try:
        from cursiv_v215.memory import semantic
        person = semantic.current_person()
        lines.append(f"Talking with: {person}; memories saved about them: {len(semantic.list_facts(person))}; "
                     f"learning from chats: {'on' if semantic.learning_enabled() else 'off'}")
    except Exception:
        pass
    try:
        from cursiv_v215.coding import brain
        lines.append(f"Coding: {len(brain.all_examples())} worked examples, {len(brain._lessons())} coding lessons learned; "
                     f"project folder: {brain.project(person) or 'none'}")
    except Exception:
        pass
    try:
        conv_dir = Path.home() / ".cursiv" / "conversations"
        from cursiv_v215.core import plugins as _plugins
        _plugins.load_all()
        _ok = [n for n, s in _plugins._status.items() if s.get("loaded")]
        lines.append(f"Plugins: {', '.join(_ok) if _ok else 'none'}" +
                     (f" ({len(_plugins._status) - len(_ok)} switched off/broken)" if len(_plugins._status) > len(_ok) else ""))
        from cursiv_v215.memory import projects as _projects
        lines.append(f"Projects tracked: {', '.join(_projects.load(person)) or 'none'}")
        from cursiv_v215.core import style as _style
        _st = _style.load(person)
        lines.append(f"Tone: {_st.get('tone', 'normal')}; style rules learned from corrections: {len(_st.get('rules', []))}")
        from cursiv_v215.agents import custom as _custom
        lines.append("Custom agents: " + (", ".join("@" + a["name"] for a in _custom.all_agents()) or "none"))
    except Exception:
        pass
    try:
        conv_dir = Path.home() / ".cursiv" / "conversations"
        lines.append(f"Saved conversations: {len(list(conv_dir.glob('*.json'))) if conv_dir.exists() else 0}")
    except Exception:
        pass
    try:
        space = json.loads((Path.home() / ".cursiv" / "space.json").read_text(encoding="utf-8"))
        lines.append(f"Phone app: {'linked' if space.get('token') else 'not linked'}; sharing memory summary with phone: "
                     f"{'on' if space.get('share_memory', True) else 'off'}")
    except Exception:
        lines.append("Phone app: not linked")
    if RECENT_ERRORS:
        lines.append("Recent errors this session: " + "; ".join(f"{t} {e}" for t, e in list(RECENT_ERRORS)[-5:]))
    else:
        lines.append("Recent errors this session: none")
    return "\n".join(f"- {l}" for l in lines)


SELF_PROMPT = """You are Cursiv, a personal AI created by Joshua Winkler that anyone can install and make their own. The person is asking about \
you -- your status, setup, abilities or how to improve you. Answer ONLY from the facts and the live report below.

Rules:
- Never invent components, agents, hashes, percentages, "drift" numbers or internals. If something isn't in \
the facts or report, say plainly that you don't know or can't see it.
- Don't describe "councils", "guardians", "constitutions" or similar as running programs unless the report \
lists them.
- For improvement ideas, base them on what the report actually shows (missing keys, no local model, errors, \
small GPU, etc.) and be concrete about how to do it in Cursiv (which window or command).
- Be warm, direct and brief.

## Where things really are (only point people to these -- never invent other menus or settings)
- Title bar buttons: ⚙ Settings, ☰ saved conversations sidebar, minimize, maximize, close (📱 Phone only with personal features shown).
- ⚙ Settings: AI keys (xAI, OpenAI, Claude, Gemini, Groq -- show/save/remove/test, "Get a key" links), Cursiv Cloud on/off, data folder, "What I remember…".
- Setup window (tray menu → Setup…, or opens when something is missing): install/start/Restart Ollama, download the chat model (qwen3 4B Instruct, the one Cursiv tested), download a coding model (qwen2.5-coder 3B/7B/14B), Cursiv Cloud + free key test.
- "What I remember" window (Settings or tray): search, add, forget memories; learning on/off.
- Tray menu: What I remember…, Phone…, Setup…, Send problem report…, Quit.
- Chat commands: remember <fact>, forget <words>, what do you remember, memory learn on/off, free keys, cloud on/off/status, council <question>, codex <request> (codex help, codex keep, codex project <folder>, codex lessons, codex learn <lesson>), phases, help.
- Cursiv Forge: evolve <idea> (writes a plugin, safety-checks it, tests it in a sandbox; installs only after evolve approve), plugins, plugin show/off/on/remove/approve <name>. Plugins live in .cursiv/plugins.
- Tools: when a message is about this computer (files, folders, disk space, RAM), Cursiv reads it with read-only tools (system_info, list_folder, read_file, find_files) plus any plugin tools; private places are never read.
- Project memory: projects, project show/forget <name> -- running summaries of ongoing projects, brought back automatically when a project comes up.
- Tone and style: tone blunt/warm/brief/playful/legacy/teacher/normal; style (show rules learned from corrections), style add <rule>, style forget <words>, style clear.
- Custom agents: agents (list), agent new <name>: <job>, @name <message>, agent teach <name> <fact>, agent show/edit/delete <name>, agent council <question>.
- There is no setting for context length or for choosing the chat model by hand; Cursiv picks models by graphics card. To change models, download a different one in Setup.

## What Cursiv really is (fact sheet)
{facts}

## Live report (checked just now)
{report}
"""


def system_prompt() -> str:
    try:
        facts = re.sub(r"<!--.*?-->", "", FACTS_FILE.read_text(encoding="utf-8"), flags=re.S).strip()
    except Exception:
        facts = "(fact sheet unavailable)"
    return SELF_PROMPT.format(facts=facts, report=live_report())

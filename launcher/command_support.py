"""Command support.

Functions receive the explicit CommandRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _image_folder, memory_command, notebook_command, _notes_view_request, _gate, _default_cfg, _auto_territory, _personal, _is_builder, help_text, hey_prefix, voice_turn.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Generator, Optional
from cursiv_engine.core.command_api import TextResult, NotebookResult, FileActionResult, MemoryResult, NotesResult, StreamResult
from cursiv_engine.core.command_api import CommandRuntime

def _image_folder(runtime: CommandRuntime, cfg: dict) -> Path:
    """Image cache is user data; an absent workspace never means the binary/CWD."""
    from cursiv_engine.core.file_access import workspace_root
    base = workspace_root(cfg['workspace']) if cfg.get('file_access') and cfg.get('workspace') else runtime.Path.home()
    folder = base / '.cursiv' / 'images'
    for p in (folder, folder.parent):
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise PermissionError('Linked image cache folders are not allowed')
    folder.mkdir(parents=True, exist_ok=True)
    return folder.resolve()

def memory_command(runtime: CommandRuntime, text: str, history: list[dict], *, scope: str) -> MemoryResult | None:
    from cursiv_engine.memory import intents, semantic
    result = intents.command(text, history, person=semantic.current_person(), scope=scope)
    return runtime.MemoryResult(result) if result is not None else None

def notebook_command(runtime: CommandRuntime, text: str, history: list[dict], *, scope: str, cfg: dict | None) -> NotebookResult | None:
    from cursiv_engine.core import notebook_tools
    from cursiv_engine.memory.semantic import current_person
    result = notebook_tools.command(text, history, observer=current_person().title(), scope=scope)
    if result is None:
        return None
    from cursiv_engine.memory import intents
    intents.clear_pending(current_person(), scope)
    if result.status == 'saved':
        # Notification failure must never turn a confirmed append into a retry.
        try:
            from cursiv_engine.core import curiosity_engine
            from cursiv_engine.core.paths import save_reference
            cfg = cfg or {}
            project = save_reference(cfg['workspace']) if cfg.get('file_access') and cfg.get('workspace') else 'general'
            curiosity_engine.notify(current_person(), project)
        except Exception:
            pass
    return runtime.NotebookResult(result)

def _notes_view_request(runtime: CommandRuntime, text: str) -> NotesResult | None:
    low = text.strip().lower().rstrip('.?')
    if low in ('notes', 'strands', 'saved notes', 'show my saved notes', 'show me my saved notes',
               'what notes do you have', 'open my notes', 'open saved notes', 'show saved notes', 'show your saved notes'):
        return runtime.NotesResult()
    search = runtime.re.fullmatch(r'(?:notes|strands) search\s+(.+)', text.strip(), runtime.re.I)
    if search:
        return runtime.NotesResult(query=search[1])
    category = runtime.re.fullmatch(r'(?:show (?:your|my)|open (?:your|my))\s+([\w-]+)\s+notes[.?]?', low)
    if category:
        return runtime.NotesResult(category=category[1])
    category = runtime.re.fullmatch(r'(?:notes|strands)\s+([\w-]+)', low)
    if category and runtime._STRAND_OK:
        stored = next((raw for raw in runtime._strand_terr_counts() if raw.casefold() == category[1]), None)
        if stored is not None:
            return runtime.NotesResult(category=stored)
    return None

def _gate(runtime: CommandRuntime):
    from cursiv_engine.core import netgate
    return netgate

def _default_cfg(runtime: CommandRuntime) -> dict:
    """Same shape as chat_cli.py's cfg dict, minus the terminal-only fields."""
    from cursiv_engine.core import workspace
    from cursiv_engine.memory.semantic import current_person
    selected, enabled, workspace_error = workspace.load(current_person())
    return {
        "file_access":      enabled,
        "confirm_mode":     "confirm",   # same safe default as the terminal CLI -- every write needs approval until "mode" toggles it
        "workspace":        selected,
        "workspace_error":  workspace_error,
        "obsidian_enabled": False,
        "obsidian_path":    "",
        "offline_mode":     runtime._gate().is_offline(),
        "last_user_msg":    "",
        "_last_council_synthesis": "",
        "_last_council_query":     "",
    }

def _auto_territory(runtime: CommandRuntime, q: str) -> str:
    ql = q.lower()
    if any(w in ql for w in ["code", "function", "python", "debug", "build", "error", "syntax", "class", "codex"]):
        return "coding"
    if any(w in ql for w in ["health", "recovery", "feel", "mental", "grounding", "medication", "episode"]):
        return "recovery"
    if any(w in ql for w in ["design", "system", "architecture", "cursiv", "agent", "strand", "council", "guardian"]):
        return "architecture"
    if any(w in ql for w in ["music", "creative", "story", "forge", "art", "write", "poem", "song"]):
        return "creative"
    if any(w in ql for w in ["research", "history", "world", "science", "civilization"]):
        return "worldmodel"
    return "general"

def _personal(runtime: CommandRuntime) -> bool:
    try:
        from cursiv_engine.core import profile
        return profile.personal()
    except Exception:
        return False

def _is_builder(runtime: CommandRuntime) -> bool:
    """Builder tools are for anyone who has set up an account on this copy; no code unlocks them."""
    try:
        from cursiv_engine.guardian.access_gate import is_setup_complete
        return bool(is_setup_complete())
    except Exception:
        return False

def help_text(runtime: CommandRuntime, topic: str) -> str:
    """`help` -> the short list; `help more` -> topics; `help <topic>` -> one topic."""
    topic = topic.strip().lower()
    if topic == 'family' and not runtime._personal():
        from cursiv_engine.core.profile import PERSONAL_NOTE
        return PERSONAL_NOTE
    if not topic:
        return runtime._HELP_TEXT if runtime._personal() else runtime._FIELD_HELP_TEXT
    if topic in runtime._HELP_TOPICS:
        title, body = runtime._HELP_TOPICS[topic]
        return f"{title.upper()}\n{body}\n\nhelp more  -  all topics"
    names = [t for t in runtime._HELP_TOPICS
             if (t not in runtime._BUILDER_TOPICS or runtime._is_builder()) and (t not in runtime._PERSONAL_TOPICS or runtime._personal())]
    lines = [f"  help {t:<10} {runtime._HELP_TOPICS[t][0]}" for t in names]
    head = "" if topic in ("more", "all", "topics") else f"No help topic called \"{topic}\".\n\n"
    return head + "Type one of these:\n" + "\n".join(lines)

def hey_prefix(runtime: CommandRuntime, raw: str) -> tuple[str, str]:
    """Detect a provider-routing prefix -- the explicit "hey <provider> ..."
    form, or the shorter "<provider> <question>" form (e.g. "grok what's the
    weather" routes that new question straight to Grok, saved to history
    normally, exactly like "hey grok ..."). This is distinct from the bare
    "grok"/"claude"/"chatgpt" command with no question, which retries the
    *previous* message instead (see handle_command) -- that only matches
    when there's nothing trailing, so it can't collide with this.
    Returns (force_provider, stripped_text)."""
    lower = raw.lower()
    for prefix, fp in (
        ("hey council ", "council"), ("hey grok ", "grok"), ("hey claude ", "claude"),
        ("hey chat ", "openai"), ("hey openai ", "openai"), ("hey gpt ", "openai"),
        ("hey ollama ", "ollama"),
        ("grok ", "grok"), ("claude ", "claude"),
        ("chatgpt ", "openai"), ("gpt ", "openai"), ("openai ", "openai"),
    ):
        if lower.startswith(prefix):
            return fp, raw[len(prefix):].strip()
    return "", raw

def voice_turn(runtime: CommandRuntime, cfg: dict, duration_s: float, raw_mode: bool, status_cb: Optional[Callable[[str], None]]) -> TextResult:
    if not runtime._VOICE_OK or not runtime._voice_avail():
        return runtime.TextResult("Voice agent unavailable — needs: pip install faster-whisper sounddevice")
    cb = status_cb or (lambda m: None)
    try:
        pcm, arr = runtime._voice_record(duration_s=duration_s, status_cb=cb)
        raw_text = runtime._voice_transcribe(pcm, float32_arr=arr, status_cb=cb)
    except RuntimeError as e:
        return runtime.TextResult(str(e))
    except Exception as e:
        return runtime.TextResult(f"Voice capture error: {e}")

    if not raw_text:
        return runtime.TextResult("Nothing heard — adjust mic or try again.")

    if raw_mode:
        return runtime.TextResult(raw_text)

    # Stage 2: Babel binary clean pass -- fixes filler words/errors and
    # translates non-English speech, same pipeline the CLI uses.
    try:
        decoded = runtime._babel_decode(runtime._babel_encode(raw_text))
        gen, _label = runtime._cascade_gen(cfg, [
            {"role": "system", "content": runtime._VOICE_CLEAN_SYS},
            {"role": "user", "content": decoded},
        ], max_tokens=300)
        cleaned = "".join(c for c in gen if c != runtime.RATE_SENTINEL)
        return runtime.TextResult((cleaned.strip() or raw_text))
    except Exception:
        return runtime.TextResult(raw_text)

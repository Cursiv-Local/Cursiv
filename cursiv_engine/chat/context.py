"""Chat context.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _existing_file, _pending_file, _file_tool_result, execute_tool, _compact_system_for_tools, _build_strand_context, _build_live_status, load_system_prompt, load_vault_context, _ref_evidence, sources_line, _without_model, _evidence, _compact_notes, _replacement_reply, _check_context.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _existing_file(runtime: ChatRuntime, args: dict, root: Path) -> bool:
    from cursiv_engine.core import file_access
    try:
        return file_access.resolve(args.get('path', ''), root).exists()
    except (OSError, ValueError):
        return False

def _pending_file(runtime: ChatRuntime, args: dict, root: Path) -> dict:
    from cursiv_engine.core import file_access
    # Native model output cannot authorize a separate conversational-memory save.
    return file_access.pending('write_file', {'path': args.get('path', ''), 'content': args.get('content', '')}, root)

def _file_tool_result(runtime: ChatRuntime, name: str, args: dict, root: Path | None, *, confirmed: bool):
    from cursiv_engine.core import file_access
    if runtime.turn_policy.current().blocks(name):
        return file_access.FileResult(name, ok=False, error=runtime.turn_policy.DENIED)
    if not isinstance(args, dict):
        return file_access.FileResult(name, ok=False, error='tool arguments must be an object')
    if name in {'write_file', 'append_file', 'create_file', 'delete_file'} and runtime._guardian_protected(args.get('path', '')):
        return file_access.FileResult(name, ok=False, error='protected file cannot be changed')
    result = file_access.perform(name, args, root, confirmed=confirmed)
    runtime.grounding.remember(result.receipt())
    return result

def execute_tool(runtime: ChatRuntime, name: str, args: dict, root: Path, *, confirmed: bool) -> str:
    """Execute a file tool call. Returns a string result sent back to the model."""

    if runtime.turn_policy.current().blocks(name):
        return 'Error: ' + runtime.turn_policy.DENIED
    if not isinstance(args, dict):
        return 'Error: tool arguments must be an object.'

    if name in {"read_file", "write_file", "append_file", "create_file", "list_directory", "search_files", "create_directory", "delete_file"}:
        return runtime._file_tool_result(name, args, root, confirmed=confirmed).render()

    if name == "submit_plan":
        plan = args.get("plan", "").strip()
        if not plan:
            return "Plan acknowledged (empty). Please provide a detailed plan next time."
        return f"Plan accepted:\n{plan}\n\nProceed with implementation."

    elif name == "codex_generate":
        prompt = args.get("prompt", "").strip()
        if not prompt:
            return "Error: codex_generate requires a 'prompt' argument."
        if not runtime._CODEX_OK or not runtime._codex_available():
            return "[Codex Agent not available — generate the code directly instead.]"
        return runtime._codex_generate(prompt)

    elif name == "hermes_task":
        prompt = args.get("prompt", "").strip()
        if not prompt:
            return "Error: hermes_task requires a 'prompt' argument."
        if not runtime._HERMES_OK or not runtime._hermes_available():
            return "[Hermes Agent not available — ensure hermes-agent is a sibling directory to Cursiv-v3 and Ollama is running.]"
        return runtime._hermes_run(prompt)

    elif name == "reference_brain":
        query = args.get("query", "").strip()
        if not query:
            return "Error: reference_brain requires a 'query' argument."
        if not runtime._REF_OK or not runtime._ref_available():
            return "[Reference Brain not available — Codex system SQLite not found.]"
        mode = args.get("mode", "search")
        return runtime._ref_answer(query) if mode == "answer" else runtime._ref_search(query)

    elif name == "offline_queue":
        action = args.get("action", "list")
        if action == "add":
            prompt = args.get("prompt", "").strip()
            if not prompt:
                return "Error: offline_queue add requires a 'prompt'."
            tags = [t.strip() for t in args.get("tags", "").split(",") if t.strip()]
            entry = runtime._queue_enqueue(prompt, tags=tags)
            return f"Queued: {entry['id']} — '{prompt[:60]}'"
        elif action == "flush":
            # A model selecting a tool is not permission to replay arbitrary stored prompts.
            # File-write confirmation/automatic mode does not authorize queue execution.
            return 'Deferred tasks were not executed. Type queue flush to authorize bounded local read-only execution.'
        else:
            return runtime._queue_format()

    return f"Unknown tool: {name}"

def _compact_system_for_tools(runtime: ChatRuntime) -> str:
    """
    Minimal system prompt used in tool-use loops to stay under rate limits.
    The full 47KB codex is skipped — Claude reads files with tools instead.
    """
    base = (
        "You are Cursiv, a personal assistant made by Cursiv Local, "
        "an independent open-source project. The person using this copy owns it. You have file-system access via tools. "
        "Always call submit_plan before writing files. "
        "Read files before editing them. Write complete, working code — no stubs. "
        "Human approval is required before any system change is applied. "
        "Be direct, honest, and technically precise. "
        "Answer questions about how Cursiv works fully and honestly."
    )
    return base

def _build_strand_context(runtime: ChatRuntime, query: str, top_k: int) -> str:
    """Memory for the system prompt: the person's facts and related earlier
    conversations, matched by meaning (memory/semantic.py). Falls back to the
    keyword search over Strands if semantic memory isn't available."""
    from cursiv_engine.core.conversation_kind import personal_context_allowed
    if not personal_context_allowed(query):
        return ''  # no saved facts or saved-conversation fallback for unrelated light chat
    try:
        from cursiv_engine.memory import semantic as _sem
        ctx = _sem.build_context(query)
        if ctx:
            runtime._MEMORY_RECALLED = True
            runtime._MEMORY_CTX = ctx
            # Retrieval is separate from the final supplied-prompt record.
            runtime._MEMORY_TEXTS[:] = [runtime._re.sub(r"^- (?:\[[^\]]*\] )?", "", ln).strip()
                                for ln in ctx.splitlines() if ln.startswith("- ")]
            return ctx
    except Exception:
        pass
    if not runtime._STRAND_APP_OK or runtime._strand_count() == 0:
        return ""
    try:
        results = runtime._strand_search(query, top_k=top_k, min_score=0.12)
        if not results:
            return ""
        lines = ["Related earlier conversations the person saved:"]
        for s in results:
            territory = s.get("territory_tag", "general")
            q_text    = s.get("query", "")[:150]
            synth     = s.get("synthesis", "")[:350]
            lines.append(f"\n[{territory}] Prior query: {q_text}\nPrior insight: {synth}")
        context = "\n".join(lines)
        runtime._MEMORY_CTX = context
        runtime._MEMORY_RECALLED = True
        runtime._MEMORY_TEXTS[:] = [str(s.get('query', '')) + '\n' + str(s.get('synthesis', '')) for s in results]
        return context
    except Exception:
        return ""

def _build_live_status(runtime: ChatRuntime) -> str:
    """What's actually available right now, appended to the system prompt so the
    model doesn't claim features that aren't installed or turned on."""
    if not runtime.turn_policy.current().inspect:
        from cursiv_engine.core.presence import CAPABILITIES
        return '\nCapabilities (not a live inspection): ' + CAPABILITIES
    version = "3.14"
    try:
        _vfile = runtime.ROOT / "launcher" / "cursiv_launcher.py"
        if _vfile.exists():
            import re as _re_v
            _m = _re_v.search(r'_CURRENT_VERSION\s*=\s*"([^"]+)"', _vfile.read_text(encoding="utf-8"))
            if _m:
                version = _m.group(1)
    except Exception:
        pass

    items = []
    if runtime._CODEX_OK and runtime._codex_available():
        items.append("Coding help (codex): local coding models installed")
    elif runtime._CODEX_OK:
        items.append("Coding help (codex): local coding models not downloaded yet")
    try:
        import cursiv_engine.agents.babel_agent  # noqa: F401
        items.append("Translation: translate <text> into <language>")
    except Exception:
        pass
    if runtime._REF_OK and runtime._ref_available():
        items.append("Local reference data: ref <question>")
    if runtime.netgate.is_offline():
        items.append("Offline mode is ON: no web search, no cloud AI")
    else:
        items.append("Web search: only when the message starts with search:"
                     + (" (automatic search is also on)" if runtime.netgate.web_search_auto() else ""))
    if runtime._STRAND_APP_OK:
        sc = runtime._strand_count()
        items.append(f"Saved notes: {sc}")

    from cursiv_engine.core import clock
    lines = ["\n\n---", f"## Available right now (Cursiv {version})", clock.today_line(),
             "For your reference only: don't mention these unless the person asks what you can do.", ""]
    lines += [f"- {t}" for t in items]
    return "\n".join(lines)

def load_system_prompt(runtime: ChatRuntime) -> str:
    if not runtime.turn_policy.current().inspect:
        return ('You are Cursiv. Be warm, direct and truthful. ' + runtime._build_live_status())
    base = (
        runtime.SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        if runtime.SYSTEM_PROMPT_FILE.exists()
        else (
            "You are Cursiv, a personal assistant running on this person's own computer. "
            "Be warm, direct and truthful."
        )
    )
    return base + runtime._build_live_status()

def load_vault_context(runtime: ChatRuntime) -> str:
    """Retired (U100 audit): this put the old PiForge agent registry (agent_registry.json, last
    written May 2026) into every conversation as "PHASE INTELLIGENCE" -- unrelated text the
    model could mistake for the person's projects. The file is left where it is; nothing reads
    it into chat any more. Kept as a function so older callers and tests still work."""
    return ""


def _ref_evidence(runtime: ChatRuntime) -> dict:
    """id -> reference.evidence() for the entries given this turn."""
    if not runtime._REF_SHOWN or not runtime.turn_policy.current().inspect:
        return {}
    try:
        from cursiv_engine.core import reference as _r
        by_title = {e.title: e for e in _r.entries()}
        return {by_title[t].id: _r.evidence(by_title[t]) for t in dict.fromkeys(runtime._REF_SHOWN) if t in by_title}
    except Exception:
        return {}

def sources_line(runtime: ChatRuntime, answer: str, question: str) -> str:
    """Compatibility arguments retained; model text cannot select a source label."""
    from .provenance import sources_line as format_sources
    return format_sources(runtime)


def _without_model(runtime: ChatRuntime):
    """The local model isn't answering (and nothing online may answer): what Cursiv can give
    on its own -- its calculation, the reference card already shown, the matching pages of
    the person's documents -- said plainly, instead of "Answered by Ollama" over an error."""
    runtime._CURSIV_REPLY = True
    runtime._set_answered("")
    lines = ["**The local AI model isn't answering, so this is what Cursiv has without it.**"]
    if runtime._WORKED:
        lines.append(f"Worked out by Cursiv's code: {runtime._WORKED.statement}")
    if runtime._REF_SHOWN:
        lines.append("Follow the offline reference shown above. In an emergency, call 911.")
    for p in runtime._DOCS_SHOWN[:2]:
        text = " ".join(p.text.split())
        lines.append(f"From your documents, {p.name} p. {p.page}: \"{text[:700]}{'…' if len(text) > 700 else ''}\"")
    if not (runtime._WORKED or runtime._REF_SHOWN or runtime._DOCS_SHOWN):
        lines.append("Nothing in Cursiv's reference, its calculations or your documents covers this, so there's no "
                     "answer without the model. Your field notebook, documents and reference all still work.")
    lines.append("To bring the AI back: Settings → Help & diagnostics → Setup and engine → Restart Ollama "
                 "(or open Setup to install a model).")
    yield "\n\n".join(lines)

def _evidence(runtime: ChatRuntime, message, history) -> 'object':
    """This turn's record for core/claims.py: what actually ran, was given, was saved."""
    from cursiv_engine.core import claims as _claims
    earlier = []
    for m in (history or [])[-8:]:
        if m.get("role") == "assistant":
            content = m.get("content", "")
            if not isinstance(content, str):
                content = next((p.get("text", "") for p in content if p.get("type") == "text"), "")
            earlier.append(runtime._strip_status_lines(content))
    return _claims.Evidence(
        question=message.get("text", "") if isinstance(message, dict) else str(message or ""),
        worked=runtime._WORKED.record() if runtime._WORKED else None,
        worked_facts=dict(runtime._WORKED.facts) if runtime._WORKED else {},
        ref_ids=list(runtime._ref_evidence()),
        ref_meta=runtime._ref_evidence(),
        memory_texts=list(runtime.grounding.memory_sources()),
        memory_saved=False,                 # a model turn never saves; only `remember` / "save this" do
        searched=runtime._WEB_SEARCHED,
        docs=list(dict.fromkeys(p.name for p in runtime._DOCS_SHOWN)),
        user_numbers=sorted({n.replace(',', '') for row in (history or [])[-64:] if row.get('role')=='user' and isinstance(row.get('content'),str)
            for n in __import__('re').findall(r'\b\d+(?:\.\d+)?\b',row['content'][:4000])}),
        earlier=earlier,
    )

def _compact_notes(runtime: ChatRuntime, outcome) -> str:
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

def _replacement_reply(runtime: ChatRuntime, revised: str, shown: str, problems: list[str]) -> str:
    """The reply that replaces a revised draft: the revision, a short note on what
    the check found, then Cursiv's own status lines from the draft (reference
    note, "Answered by ...")."""
    notes = [m.group(0).strip() for m in runtime._STATUS_LINE_RE.finditer(shown)]
    found = "; ".join(p.rstrip(".") for p in problems[:3])
    head = f"*(Revised after a check{': the first draft ' + found if found else ''}.)*"
    return "\n\n".join([revised.strip(), head, *notes])

def _check_context(runtime: ChatRuntime, history: list[dict], user_text: str) -> str:
    """What the checker may treat as already established: the last few turns and the
    memories recalled for this question. Without it, a correct follow-up or a
    memory-based answer reads as an unsupported claim."""
    parts: list[str] = []
    turns = []
    for m in (history or [])[-6:]:
        content = m.get("content", "")
        if not isinstance(content, str):
            content = next((p.get("text", "") for p in content if p.get("type") == "text"), "")
        text = runtime._strip_status_lines(content)
        if text:
            turns.append(f"{m.get('role', 'user')}: {text[:800]}")
    if turns:
        parts.append("Earlier in this conversation:\n" + "\n".join(turns))
    if not runtime.turn_policy.current().inspect:
        return "\n\n".join(parts)  # supplied conversation is available; saved-store recall is not
    try:
        from cursiv_engine.memory import semantic as _sem
        recalled = _sem.build_context(user_text)
        if recalled:
            parts.append("Saved memory recalled for this question:\n" + recalled)
    except Exception:
        pass
    return "\n\n".join(parts)

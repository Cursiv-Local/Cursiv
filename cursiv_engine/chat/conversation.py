"""Chat conversation.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _chat_inner.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _chat_inner(runtime: ChatRuntime, message: dict | str, history: list[dict], api_key: str, files: list | None, file_access: bool, root_path: str, openai_key: str, confirm_writes: bool, anthropic_key: str, force_provider: str, on_action) -> Generator[str, None, None]:
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
    from cursiv_engine.core import self_inspection
    own = self_inspection.current()
    if own is not None and not own.error:
        yield from self_inspection.stream(runtime, own, user_text, history, api_key, openai_key,
                                          anthropic_key, force_provider)
        return
    from cursiv_engine.core.conversation_kind import personal_context_allowed, reflective, light_banter
    _banter=light_banter(user_text) and not uploaded
    _use_memory = runtime.turn_policy.current().inspect and personal_context_allowed(user_text)

    # Deterministic file dispatch works with every model, including no model.
    from cursiv_engine.core import file_access as _files
    _file_result = (_files.command(user_text, history, runtime.Path(root_path) if file_access and root_path else None)
                    if runtime.turn_policy.current().inspect else None)
    if _file_result is not None:
        if on_action:
            for receipt in _file_result.receipts:
                on_action(receipt)
        if _file_result.pending:
            yield runtime.WRITE_SENTINEL + runtime.json.dumps(_file_result.pending)
        else:
            yield _file_result.text
        return

    from cursiv_engine.core.philosophy_policy import answer as philosophy_answer
    _philosophy = philosophy_answer(user_text, history)
    if _philosophy is not None and not uploaded:
        yield _files.VerifiedText(_philosophy)
        return

    # ── Process files ───────────────────────────────────────────────────
    file_context, image_parts = runtime.process_uploaded_files(uploaded if runtime.turn_policy.current().inspect else [])

    from cursiv_engine.core import presence
    from cursiv_engine.memory import semantic as _presence_sem
    _observed = runtime.grounding.state()
    if _observed is None:
        _observed = presence.snapshot(root_path, file_access, person=_presence_sem.current_person())
    for _source in runtime.grounding.refresh_history(user_text, history, root_path if file_access else None):
        if on_action:
            on_action(_source)
        yield _files.VerifiedText(_source.status_line() + '\n\n', _source)

    # ── Build system prompt ─────────────────────────────────────────────
    from .response_style import BANTER_SYSTEM
    system_text = BANTER_SYSTEM if _banter else runtime.load_system_prompt()
    if runtime.turn_policy.current().inspect and not _banter:
        system_text += runtime.load_vault_context()
        try:
            from cursiv_engine.memory import session_notes as _notes   # U100: where this conversation left off
            system_text += _notes.prompt_block()
        except Exception:
            pass
        # Session memory (the last exchanges of the latest session, even from another
        # conversation) is continuity, not material. For writing and creative requests it
        # made a small model reuse earlier posts word for word (U99), so it's left out.
        # U100 audit: it also came from OTHER conversations, written as "You: …", and the model
        # answered "what did I ask three messages ago?" from it with an invented checklist request
        # and invented ORION-742 readings. So it's only given to a conversation that has no
        # history of its own yet, and labelled as another conversation's.
        from . import response_style as _rs
        if not history and not (_rs.DRAFT.search(user_text or '') or _rs._CREATIVE_ASK.search(user_text or '')):
            _ctx = runtime._load_session_ctx()
            if _ctx:
                system_text += ("\n\n(The block below is from an EARLIER, DIFFERENT conversation. It is background "
                                "only: never describe it as something said in this conversation, and never treat "
                                "its numbers, sites or projects as recorded data.)" + _ctx)
    runtime._FULL_PERSONA = system_text      # free/local providers swap this for the compact persona
    if file_context:
        system_text += f"\n\n## Uploaded Content\n{file_context}"
    if file_access and runtime.turn_policy.current() == runtime.turn_policy.Policy() and not _banter:
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
        if role not in ('user', 'assistant'):
            continue  # conversation data cannot introduce system authority
        content = h.get("content", "")
        if role == "assistant" and isinstance(content, str):
            content = runtime._strip_status_lines(content)   # see _STATUS_LINE_RE
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
    _search_q = '' if _banter else user_text
    for _pfx in ("search:", "search "):
        if _search_q.lower().startswith(_pfx):
            _search_q = _search_q[len(_pfx):].strip()
            break
    _web_ctx = ""
    _search_failed = ""
    if runtime.netgate.is_offline() and (user_text.lower().startswith('search:') or
            (user_text.lower().startswith('search ') and not _files.is_request(user_text))):
        yield f"*[Web search skipped. {runtime.netgate.OFFLINE_MESSAGE}]*\n\n"
    elif runtime.turn_policy.current().inspect and runtime._needs_search(user_text):
        if runtime._is_online():
            _web_ctx = runtime._web_search(_search_q[:300])
            if not _web_ctx:
                from cursiv_engine.chat import web_search as _ws
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
        runtime._WEB_SEARCHED = True
        runtime._RETRIEVED.append(_web_ctx)
        messages[0]["content"] += (
            "\n\n## Live Web Search Results\n"
            "*(Snippets from a web search for this question, just now. They can be wrong or out of date: "
            "say which parts of the answer come from them)*\n\n"
            + _web_ctx + "\n"
        )

    # ── Cursiv's 8 phases (core/phases.py): Energy, Emergency, Grounding (memory),
    # Route, Structure, Connectivity, Future State, Recovery -- real rules run on
    # every message; their instructions go into the system prompt.
    runtime._PHASE_AFTER = ""
    try:
        from cursiv_engine.core import phases as _phases
        _ph = _phases.run(user_text, memory_fn=runtime._build_strand_context if _use_memory else None,
                          online_fn=(lambda: runtime._connectivity_probe(api_key, openai_key, anthropic_key))
                              if runtime.turn_policy.current().inspect and not _banter else None,
                          local_fn=(lambda: runtime._ollama_running() and runtime._resolve_ollama_model() is not None)
                              if runtime.turn_policy.current().inspect and not _banter else None)
        if _ph.emergency:
            _banter=False  # existing emergency handling always takes precedence
        _addendum = _ph.system_addendum()
        if _ph.emergency and _ph.emergency_kind != "medical":
            # A crisis gets a short, focused prompt -- buried at the end of Cursiv's long
            # instructions, the care guidance lost out to the model's canned refusal style.
            messages[0]["content"] = (
                "You are Cursiv, a caring personal assistant that runs on this person's own computer. The person "
                "talking to you may be in crisis or danger right now. Speak like a calm, kind friend: short, warm, "
                "plain sentences. Acknowledge what they said and that it matters. Ask if they're safe right now. "
                "Gently encourage them to reach out to the help line shown above and to someone they trust, and "
                "say you're here to keep talking. Never lecture, never refuse, never say you can't help, and don't "
                "list many resources -- the help lines are already shown.\n\n" + (_ph.memory or "")
            )
        elif _addendum and not _banter:
            messages[0]["content"] += "\n\n" + _addendum + "\n"
        runtime._PHASE_AFTER = '' if _banter else _ph.after_reply
        runtime._EMERGENCY_TURN = bool(_ph.emergency)
        if _ph.before_reply:
            yield _ph.before_reply
    except Exception:
        _strand_ctx = runtime._build_strand_context(user_text) if _use_memory and len(user_text.strip()) >= 10 else ""
        if _strand_ctx:
            messages[0]["content"] += "\n\n## Personal Memory\n" + _strand_ctx + "\n"

    # ── Coding questions and pasted terminal output get Cursiv's coding brain
    # (cursiv_engine/coding): a focused coding prompt + playbooks + error diagnosis +
    # their environment + learned lessons + project files. The full persona prompt
    # made coding models echo councils/owner notes and skip the real setup steps.
    # ── Questions about Cursiv itself: answer from a live report of its real state
    # (core/selfknow.py), not from the persona prompt -- which made it invent internals.
    _self_turn = False
    try:
        from cursiv_engine.core import selfknow as _sk
        if not _banter and not reflective(user_text) and not runtime.turn_policy.current().blocks('full_self_report') and not (locals().get("_ph") and _ph.emergency) and _sk.is_self_question(user_text):
            messages[0]["content"] = _sk.system_prompt(observed=_observed, question=user_text)
            _self_turn = True
    except Exception:
        pass

    runtime._CODING_TURN = False
    try:
        if _self_turn or _banter or not runtime.turn_policy.current().inspect:
            raise RuntimeError("self question")      # skip the coding brain
        from cursiv_engine.coding import brain as _cb
        _emergency = bool(locals().get("_ph") and _ph.emergency)
        if not _emergency and (runtime._classify_message(user_text) == "code" or _cb.looks_like_terminal(user_text)):
            from cursiv_engine.memory import semantic as _sem
            _person_now = _sem.current_person()
            if file_access:      # tool-using coding mode keeps its protocol; add the ground truth
                messages[0]["content"] += "\n\n" + _cb.context_block(user_text, history, _person_now)
            else:
                _sys = _cb.system_prompt(user_text, history, _person_now)
                if _web_ctx:
                    _sys += "\n\n## Live Web Search Results\n" + _web_ctx
                _mem = runtime._build_strand_context(user_text) if _use_memory and len(user_text.strip()) >= 10 else ""
                if _mem:
                    _sys += "\n\n## What you know about them\n" + _mem
                messages[0]["content"] = _sys
            runtime._CODING_TURN = True
    except Exception:
        pass

    # ── How this person wants Cursiv to talk (core/style.py): tone + rules learned
    # from their corrections. Added to every kind of reply; corrections are learned
    # in the background from this message and the reply it's correcting.
    _style_addendum = ''
    try:
        if runtime.turn_policy.current().inspect and not (locals().get("_ph") and _ph.emergency):
            from cursiv_engine.core import style as _style
            from cursiv_engine.memory import semantic as _sem2
            _who = _sem2.current_person()
            _style_addendum = _style.prompt_addendum(_who, user_text)
            from cursiv_engine.memory import formation as _formation
            if _style.looks_like_correction(user_text) and _formation.enabled_for(user_text):
                _prev = next((m.get("content", "") for m in reversed(history or [])
                              if m.get("role") == "assistant" and isinstance(m.get("content"), str)), "")
                import uuid
                _formation.submit(lambda: _style.learn_correction(_who, user_text, _prev, runtime._memory_llm),
                                  'style:' + uuid.uuid4().hex)
    except Exception:
        pass

    # ── Project memory, plugin context, and tools (U52) ──────────────────────
    _project_context = ''
    if not _banter and not (locals().get("_ph") and _ph.emergency):
        try:
            from cursiv_engine.memory import projects as _proj
            from cursiv_engine.memory import semantic as _sem3
            _pc = _proj.context(user_text, _sem3.current_person()) if runtime.turn_policy.current().inspect else ''
            if _pc:
                _project_context = _pc
                messages[0]["content"] += "\n\n" + _pc + "\n"
        except Exception:
            pass
        try:
            from cursiv_engine.core import plugins as _plugins
            _hc = _plugins.message_context(user_text) if not runtime.turn_policy.current().blocks('plugin_context') else ''
            if _hc:
                runtime._RETRIEVED.append(_hc)
                messages[0]["content"] += "\n\n## From your plugins\n" + _hc + "\n"
        except Exception:
            pass
        try:
            from cursiv_engine.core import tools as _tools
            if runtime.turn_policy.current().inspect and _tools.might_need_tools(user_text):
                _calls = _tools.plan(user_text, runtime._router_llm, files=bool(file_access and root_path))
                if _calls:
                    _results = _tools.run(_calls, root=runtime.Path(root_path) if file_access and root_path else None)
                    _tool_ctx = _tools.context_for(_results)
                    for _result in _results:
                        runtime.grounding.remember(getattr(_result, 'receipt', None))
                        if _result.ok:
                            runtime.grounding.record_execution(_result.label)
                        if on_action and isinstance(getattr(_result, 'receipt', None), dict):
                            _receipt = _result.receipt
                            _fields = _files.FileResult.__dataclass_fields__
                            on_action(_files.FileResult(**{k: v for k, v in _receipt.items() if k in _fields}))
                        elif on_action:
                            on_action(_result)
                    runtime._RETRIEVED.append(_tool_ctx)
                    messages[0]["content"] += "\n\n" + _tool_ctx + "\n"
                    checked = [r.label for r in _results if r.ok]
                    if checked:
                        _note = "*(Checked on this computer: " + "; ".join(checked) + ")*"
                        runtime._REAL_TOOL_NOTES.add(_note)
                        yield _files.VerifiedText(_note + "\n\n")
                    for attempted in _results:
                        if not attempted.ok:
                            runtime._CURSIV_REPLY = True
                            failed = _files.FileResult('tool_execution', ok=False, error=attempted.output)
                            yield _files.VerifiedText('Tool result unconfirmed: ' + attempted.output +
                                '\nNo successful access or action is established by this attempt.\n\n', failed)
                            return  # no model continuation may contradict the authoritative failure
        except Exception as exc:
            runtime._CURSIV_REPLY = True
            failed = _files.FileResult('tool_execution', ok=False, error=type(exc).__name__)
            if on_action:
                on_action(failed)
            yield _files.VerifiedText('Tool execution unavailable: ' + type(exc).__name__ +
                '. No successful access or action is confirmed.', failed)
            return

    # Clock times and plain sums are worked out in code (core/calc.py); the model
    # gets the result, and chat() checks the answer used it.
    try:
        if runtime.turn_policy.current().inspect and not (_self_turn or runtime._CODING_TURN or _banter):
            from cursiv_engine.core import calc as _calc
            runtime._WORKED = _calc.work_out_for_turn(user_text, history)
            if runtime._WORKED:
                messages[0]["content"] += "\n\n" + _calc.prompt_note(runtime._WORKED) + "\n"
                if runtime._WORKED.lead:                 # a safety rule's answer, first, from Cursiv
                    yield runtime._WORKED.lead + "\n\n"
        # "Are you offline?" is answered from the real switches and gate, not by the model,
        # which said "I am completely offline" as fact (benchmark gen-020, U65).
        from cursiv_engine.chat import status as _net_status
        if not runtime._CODING_TURN and _net_status.answers_network_question(user_text):
            runtime._CURSIV_REPLY = True
            yield _net_status.network_answer(user_text)
            return
        # "Is it safe?" with nothing earlier saying what "it" is: ask, don't guess (core/clarify.py).
        # Not when the calculator already worked it out: "How far is it from 44.1234, -71.5678 to
        # 44.13, -71.56?" was asked what "it" meant (benchmark num-034, suite 1.4).
        if not (_self_turn or runtime._CODING_TURN or runtime._WORKED or (locals().get("_ph") and _ph.emergency)):
            from cursiv_engine.core import clarify as _clarify
            _vague = _clarify.needs_clarifying(user_text, history)
            if _vague:
                # The model ignored the instruction and answered "Yes, it's safe" (site recording,
                # 2026-10-18), so Cursiv asks the question itself.
                runtime._CURSIV_REPLY = True
                yield _clarify.question(_vague)
                return
    except Exception:
        pass

    # Cursiv's offline reference (core/reference.py): an entry that covers the
    # question goes into the prompt with an ID to cite, and the person sees which.
    try:
        _crisis = bool(locals().get("_ph") and _ph.emergency and _ph.emergency_kind != "medical")
        if runtime.turn_policy.current().inspect and not (_self_turn or runtime._CODING_TURN or _crisis or _banter):
            from cursiv_engine.core import reference as _ref_data
            _found = _ref_data.lookup(user_text)
            if _found:
                runtime._REF_SHOWN[:] = [e.title for e in _found]
                _ref_block = _ref_data.prompt_block(_found)
                messages[0]["content"] += "\n\n" + _ref_block + "\n"
                runtime._RETRIEVED.append(_ref_block)
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
        if not (_self_turn or runtime._CODING_TURN or _banter):
            from cursiv_engine.core import documents as _docs
            if runtime.turn_policy.current().inspect and _docs.library():
                _passages_found = _docs.search(user_text)
                _emergency_now = bool(locals().get("_ph") and _ph.emergency)
                if _passages_found:
                    runtime._DOCS_SHOWN[:] = _passages_found
                    # A passage that talks to the AI: flagged to the person, and saved memories are
                    # taken out of the prompt, so a document can never get them out (core/documents.py).
                    _inj = _docs.instruction_flags(_passages_found)
                    if _inj:
                        if runtime._MEMORY_CTX:
                            messages[0]["content"] = messages[0]["content"].replace(
                                runtime._MEMORY_CTX, "(Saved memories withheld for this answer: a document in it contains "
                                             "instructions.)")
                        runtime._MEMORY_TEXTS.clear()
                        runtime._MEMORY_RECALLED = False
                        yield _docs.instruction_note(_inj) + "\n\n"
                    _doc_block = _docs.prompt_block(_passages_found, _docs.only_mode() and not _emergency_now)
                    messages[0]["content"] += "\n\n" + _doc_block + "\n"
                    runtime._RETRIEVED.append(_doc_block)
                    yield _docs.note_line(_passages_found) + "\n\n"
                    from cursiv_engine.core.deterministic_overrides import conflicting_doses
                    _conflict = conflicting_doses(user_text, _passages_found)
                    if _conflict:
                        runtime._CURSIV_REPLY = True
                        yield _files.VerifiedText(_conflict)
                        return  # no model is allowed to choose a disputed dose
                elif _docs.only_mode() and not _emergency_now:
                    runtime._CURSIV_REPLY = True
                    yield _docs.NOT_IN_DOCS
                    return
                elif _docs.ASKS_ABOUT_DOCS.search(user_text):
                    _names = [d["name"] for d in _docs.library()]
                    runtime._DOCS_SEARCHED_EMPTY[:] = _names
                    if not _emergency_now and not uploaded:
                        runtime._CURSIV_REPLY = True
                        yield _files.VerifiedText(_docs.nothing_found_note(_names) + '\n\n'
                            'No matching passage was found. I cannot establish that from the imported documents.')
                        return  # a model cannot turn a failed retrieval into a document claim
                    messages[0]["content"] += "\n\n" + _docs.nothing_found_block(_names) + "\n"
                    yield _docs.nothing_found_note(_names) + "\n\n"
    except Exception:
        pass

    # Safety rule, assumption ledger, and earlier ledgers. Appended last so the
    # coding-brain prompt swap above does not drop them. The check itself runs
    # in chat() once the draft is complete (core/verify.py).
    try:
        if not (locals().get("_ph") and getattr(_ph, "emergency", False)):
            from cursiv_engine.core import verify as _verify
            _vadd = _verify.prompt_addendum(user_text)
            if _vadd:
                messages[0]["content"] += "\n\n" + _vadd + "\n"
    except Exception:
        pass

    # Codex Agent is invoked explicitly via the `codex <prompt>` command only.
    messages[0]['content'] += (
        '\n\n## Actual local file capabilities\n'
        + (f'File access is enabled only inside this authorized workspace: {root_path}. '
           'Cursiv supports reading/listing UTF-8 text files and verified file writes through its application layer. '
           if file_access and runtime.turn_policy.current().inspect else
           'File inspection and tools are disabled for this turn. This is separate from the saved file-access setting. '
           if not runtime.turn_policy.current().inspect else
           'File access is currently off. The user can choose workspace <folder>, then files on. ')
        + 'Explicit file commands also work offline without native model tools: file read <path>; file list <folder>; '
        'file create|append|replace|remember <path> :: <text>; file save conversation <path>. '
        'If a location or filename is unclear, ask for it. Never claim a write succeeded without an actual tool result. '
        'An existing file requires confirmation. Protected credentials and paths outside the workspace are unavailable.\n'
    )
    try:
        _runtime = presence.prompt(_presence_sem.current_person(), observed=_observed)
    except (OSError, ValueError):
        _runtime = '\nOperational preferences unavailable; missing state is unknown.\n'
    # Constructed here, never parsed out of user/model text. Compact providers
    # retain this block separately from the long replaceable persona.
    from cursiv_engine.core.feedback import VOICE
    from .response_style import guidance, GUIDANCE_HEADING
    if _banter:
        messages[0]['content']=BANTER_SYSTEM
    messages.insert(1, dict(role='system', content=(
        ('' if _banter else (_runtime or presence.CAPABILITIES)) + runtime.turn_policy.current().note() + '\n' + runtime.grounding.source_context()
        + ('\n' + VOICE if not runtime._EMERGENCY_TURN else ''))))
    response_guidance = guidance(user_text, history) if not runtime._EMERGENCY_TURN else ''
    if response_guidance:
        messages.append(dict(role='system', content=GUIDANCE_HEADING + response_guidance))
    # Keep this independent of persona/coding prompt replacements. Paid and
    # local providers receive the same policy; _slim preserves it in full.
    from cursiv_engine.core.philosophy_policy import INSTRUCTIONS
    messages.insert(2, dict(role='system', content=INSTRUCTIONS))
    messages.insert(3, dict(role='system', content=(
        'Conversation history scope: current-thread context is bounded and may omit earlier messages. '
        'Persistent memory and other session summaries are separate from this conversation. '
        'If earlier turns are unavailable, say so; do not invent quotations, chronology or the original concern. '
        'Follow later user corrections over earlier statements.')))
    if _style_addendum:
        # Separate from the replaceable persona so compaction and tool prompts
        # retain the current preference, including a change made this session.
        messages.insert(3, dict(role='system', content=_style_addendum))
    from cursiv_engine.core import reasoning_context
    reasoning_context.supplied_memory((_project_context+'\n'+runtime._MEMORY_CTX)
        if runtime.turn_policy.current().inspect else '')
    _reasoning = reasoning_context.prompt(user_text, history,reasoning_context.saved_context())
    if _reasoning:
        messages.insert(3, dict(role='system',content=_reasoning))
    # Auto-intercept is disabled — Ollama handles coding Q&A directly with the
    # full system prompt injected, which produces better answers than Codex for
    # conversational coding questions.
    _fp_early = (force_provider or "").lower().strip()

    # ── Smart model routing ─────────────────────────────────────────────
    from .provenance import capture_memory
    capture_memory(runtime, messages)
    # What this answer's instructions were (memory only), for "self prompt" and
    # later questions about why Cursiv answered as it did.
    from cursiv_engine.core import last_turn
    last_turn.record_assembled(messages)
    key = (api_key or "").strip()
    oai = (openai_key or "").strip()
    ant = (anthropic_key or "").strip()
    has_images = len(image_parts) > 0
    fp         = (force_provider or "").lower().strip()
    from . import model_selection
    _selected = model_selection.current()
    if _selected:
        if image_parts:
            yield 'Exact-model image input is not supported in this path. No fallback was used.'
            return
        yield from model_selection.stream(runtime,_selected,messages,api_key=key,openai_key=oai,anthropic_key=ant)
        return
    if not runtime.netgate.allowed():
        # Offline mode: saved keys stay saved but aren't used; the local model answers.
        key = oai = ant = ""
        if fp in ("grok", "claude", "openai"):
            yield f"*[{fp.title()} skipped. {runtime.netgate.OFFLINE_MESSAGE} Answering with the local model.]*\n\n"
            fp = "ollama"

    def _workspace() -> Path:
        return _files.workspace_root(root_path)

    # ── Forced provider (grok / claude / openai commands) ───────────────
    if fp in ("grok", "claude", "openai", "ollama"):
        runtime._set_answered({"grok": "xAI", "claude": "Claude", "openai": "OpenAI"}.get(fp) or runtime._ollama_label())
    if fp == "grok":
        if file_access and runtime.turn_policy.current().inspect and key:
            yield from runtime._call_xai_with_tools(messages, key, _workspace(), oai,
                                             has_images, confirm_writes=confirm_writes,
                                             anthropic_key="", on_action=on_action)
        elif key:
            yield from runtime._call_xai_stream(messages, key, has_images)
        else:
            yield "[No xAI key set — type: key xai-xxxxx]"
        return
    elif fp == "claude":
        if file_access and runtime.turn_policy.current().inspect and ant:
            yield from runtime._call_claude_with_tools(messages, ant, _workspace(),
                                                confirm_writes=confirm_writes, on_action=on_action)
        elif ant:
            yield from runtime._call_claude_direct(messages, ant)
        else:
            yield "[No Anthropic key set — type: anthropic sk-ant-xxxxx]"
        return
    elif fp == "openai":
        if oai and file_access and runtime.turn_policy.current().inspect:
            yield from runtime._call_openai_with_tools(messages, oai, _workspace(), anthropic_key=ant,
                                               confirm_writes=confirm_writes, on_action=on_action)
        elif oai:
            yield from runtime._call_openai_direct(messages, oai)
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
        yield from runtime._call_ollama(text_msgs)
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
    _tool_writer = file_access and runtime.turn_policy.current().inspect and (key or oai or ant)
    _local_tried = False
    if not has_images and not _tool_writer and runtime._local_model_ready():
        _local_tried = True
        _label, _lgen = runtime._local_stream(_text_msgs_all, user_text)
        _first = next(_lgen, None)
        if _first is not None and not _first.lstrip().startswith("[Ollama"):
            runtime._set_answered(runtime._ollama_label(_label))
            yield _first
            yield from _lgen
            return

    # Nothing online is set up either (no keys, no Cursiv Cloud): the same as offline.
    if not (runtime._cloud_configured(key, oai, ant) or runtime.cloud_enabled()) and (_local_tried or not runtime._local_model_ready()):
        yield from runtime._without_model()
        return

    # ── Offline detection — skip all cloud providers immediately ────────
    if not runtime._is_online():
        if _local_tried or not runtime._local_model_ready():
            yield from runtime._without_model()
            return
        runtime._set_answered(runtime._ollama_label())
        yield from runtime._call_ollama(_text_msgs_all)
        return

    # ── Smart routing — cascade: xAI → OpenAI → Claude → Ollama ────────
    def _fa_error(chunk: str, provider: str) -> bool:
        if chunk == runtime.RATE_SENTINEL:
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
            return runtime.RATE_SENTINEL

    def _text_only_msgs(msgs):
        return [
            {"role": m["role"],
             "content": m["content"] if isinstance(m["content"], str)
                        else next((p["text"] for p in m["content"] if p["type"] == "text"), "")}
            for m in msgs
        ]

    if file_access and runtime.turn_policy.current().inspect:
        _fa_done = False

        if key and not _fa_done:
            gen   = runtime._call_xai_with_tools(messages, key, _workspace(), oai, has_images,
                                          confirm_writes=confirm_writes, anthropic_key=ant, on_action=on_action)
            first = _safe_first(gen)
            if first is not None and not _fa_error(first, "xAI"):
                runtime._set_answered("xAI")
                yield first
                yield from gen
                _fa_done = True

        if oai and not _fa_done:
            gen   = runtime._call_openai_with_tools(messages, oai, _workspace(),
                                             anthropic_key=ant, confirm_writes=confirm_writes, on_action=on_action)
            first = _safe_first(gen)
            if first is not None and not _fa_error(first, "OpenAI"):
                runtime._set_answered("OpenAI")
                yield first
                yield from gen
                _fa_done = True

        if ant and not _fa_done:
            gen   = runtime._call_claude_with_tools(messages, ant, _workspace(),
                                             confirm_writes=confirm_writes, on_action=on_action)
            first = _safe_first(gen)
            if first is not None and not _fa_error(first, "Claude"):
                runtime._set_answered("Claude")
                yield first
                yield from gen
                _fa_done = True

        # Offline fallback — all cloud providers exhausted or unreachable
        # Ollama is local with no token rate limits — unlimited in offline mode
        if not _fa_done:
            yield from runtime._fallback_chain(_text_only_msgs(messages), user_text,
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
            gen   = runtime._call_xai_stream(messages, key, has_images)
            first = next(gen, None)
            if first not in (runtime.RATE_SENTINEL, None) and not (
                isinstance(first, str) and first.startswith("[xAI auth")
            ):
                runtime._set_answered("xAI")
                yield first
                for chunk in gen:
                    if chunk != runtime.RATE_SENTINEL:
                        yield chunk
                return
            # xAI failed — continue cascade

        # 2. OpenAI
        if oai:
            tried.append("OpenAI")
            gen   = runtime._call_openai_direct(messages, oai)
            first = next(gen, None)
            if first is not None and not (
                isinstance(first, str) and first.lstrip().startswith("[OpenAI error")
            ):
                if len(tried) > 1:
                    yield f"*[{' → '.join(tried[:-1])} unavailable — OpenAI]*\n\n"
                runtime._set_answered("OpenAI")
                yield first
                yield from gen
                return
            # OpenAI failed — continue cascade

        # 3. Claude
        if ant:
            tried.append("Claude")
            gen   = runtime._call_claude_direct(messages, ant)
            first = next(gen, None)
            if first not in (runtime.RATE_SENTINEL, None) and not (
                isinstance(first, str) and first.lstrip().startswith("[Claude error")
            ):
                if len(tried) > 1:
                    yield f"*[{' → '.join(tried[:-1])} unavailable — Claude]*\n\n"
                runtime._set_answered("Claude")
                yield first
                yield from gen
                return
            # Claude failed — fall to Ollama

        # 4. Free providers (own Gemini/Groq keys), then local Ollama -- or
        #    Cursiv Cloud when no local model is ready.
        yield from runtime._fallback_chain(_text_only(messages), user_text, tried, local_tried=_local_tried)

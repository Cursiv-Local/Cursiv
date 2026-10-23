"""Chat completion.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _learn_later, chat.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _learn_later(runtime: ChatRuntime, message, reply: str, *, origin: str, skip: bool, person: str | None, event_id: str) -> None:
    """Save lasting facts from this exchange (memory/semantic.py), off the UI thread.

    User facts are never extracted from the assistant's draft. A failed answer
    check permits only directly matched user statements; origins stay inferred.
    """
    if origin not in ("inferred", "verified"):
        origin = "inferred"
    text = message.get("text", "") if isinstance(message, dict) else str(message or "")
    from cursiv_v215.core import file_access as _files
    if _files.is_request(text):
        return
    from cursiv_v215.memory import semantic as _sem, formation as _formation
    if skip and not _formation.candidates(text, person or _sem.current_person()):
        return
    if not _formation.enabled_for(text):
        return
    person = person or _sem.current_person()
    _memory_generation = _sem.generation()
    if not event_id:
        import uuid
        event_id = uuid.uuid4().hex
    # drop Cursiv's own status lines ("*[Answered by …]*", routing notes) before judging the reply
    reply = runtime._strip_status_lines(reply or "")
    if not reply.strip() or len(text.strip()) < 4:
        return
    coding = runtime._CODING_TURN
    def work():
        _sem.learn_from_exchange(text, reply, runtime._memory_llm, person, origin=origin, event_id=event_id,
                                 expected_generation=_memory_generation)
        if _sem.generation() != _memory_generation:
            return
        from cursiv_v215.memory import projects as _proj
        _proj.learn(text, reply, runtime._memory_llm, person)
        if coding:
            from cursiv_v215.coding import brain as _cb
            _cb.learn_from_exchange(text, reply, runtime._memory_llm, person)
    _formation.submit(work, event_id)

def chat(runtime: ChatRuntime, message: dict | str, history: list[dict], api_key: str, files: list | None, file_access: bool, root_path: str, openai_key: str, confirm_writes: bool, anthropic_key: str, force_provider: str, replace_draft: bool, on_stage: Callable[[str], None] | None, notebook_scope: str, on_action, on_review=None, review_mode=None) -> Generator[str, None, None]:
    """Cursiv's main chat entry point: _chat_inner, time-boxed (see _time_boxed).

    replace_draft: when the check revises the answer, yield REPLACE_SENTINEL +
    the final reply instead of appending the revision under the draft (C-007).

    After the draft has streamed, one verification pass may append a revision
    or the problems it could not clear. Lasting facts are then learned in the
    background. Casual turns skip the pass.
    """
    from cursiv_v215.core import field_recall, notebook_tools
    _field_text = message.get('text', '') if isinstance(message, dict) else str(message or '')
    policy = runtime.turn_policy.current()
    _replace_prefix = runtime.REPLACE_SENTINEL + (policy.confirmation() + '\n\n' if policy.confirmation() else '')
    from cursiv_v215.core import file_access as _file_ops
    if policy.confirmation():
        yield _file_ops.VerifiedText(policy.confirmation() + '\n\n')
    from cursiv_v215.core.action_gate import refusal
    _denied = refusal(_field_text, history)
    if _denied:
        yield _file_ops.VerifiedText(_denied)
        return
    from cursiv_v215.core.deterministic_overrides import conflicting_doses
    _provided_conflict = conflicting_doses(_field_text, (), supplied_text=_field_text)
    if _provided_conflict:
        from cursiv_v215.memory.intents import requested_operations
        # Literal file/notebook/memory payloads are data, not a request to
        # choose a dose. Keep explicit native destinations intact.
        task = runtime.turn_policy.task_text(_field_text)
        action = (_file_ops.is_request(_field_text, history) or notebook_tools._intent(task)
                  or requested_operations(task))
        if not action:
            yield _file_ops.VerifiedText(_provided_conflict +
                '\n\n*[Sources: User-supplied text conflict check (no AI model)]*')
            return
    from cursiv_v215.core import native_answers
    _native = native_answers.answer(_field_text, calculations=policy.inspect)
    if _native is not None:
        from cursiv_v215.core.conversation_kind import relayed_thread_question
        _requested_provider = (force_provider or '').lower().strip()
        if relayed_thread_question(_field_text) and _requested_provider in ('grok', 'claude', 'openai', 'council') and runtime.netgate.is_offline():
            yield _file_ops.VerifiedText(f'*[{_requested_provider.title()} skipped. Offline mode is on. '
                'This application answer used no external provider or local model.]*\n\n')
        yield _file_ops.VerifiedText(_native)
        return
    _model_state = native_answers.model_answer(_field_text, runtime._ANSWERED_BY)
    if _model_state is not None:
        yield _file_ops.VerifiedText(_model_state)
        return
    # Classification is pure; a restricted correction must not reach a model
    # or the native backend. Limits apply to this message, not the previous one.
    _blocked_notebook = notebook_tools.blocked_message(_field_text, history)
    if _blocked_notebook:
        yield _file_ops.VerifiedText(_blocked_notebook)
        return
    if not policy.inspect and _file_ops.is_request(_field_text, history):
        yield _file_ops.VerifiedText(runtime.turn_policy.DENIED)
        return
    # With reference lookup forbidden, do not let a model invent or deny a
    # built-in safety rule. This is an availability statement, not a lookup.
    import re
    if not policy.inspect and re.search(r'(?i)\blightning\b.*\b(?:rule|minutes?)\b', _field_text):
        yield _file_ops.VerifiedText(
            'The checked lightning rule is unavailable in this turn because tools and reference lookup are disabled. '
            'Ask without that restriction for Cursiv’s built-in checked answer. '
            'I have not looked it up, and this does not mean the rule is nonexistent.')
        return
    # Run before filesystem classification, model planning, answer checking or
    # automatic memory. Only a native backend receipt can acknowledge a save.
    from cursiv_v215.memory.semantic import current_person as _notebook_person
    from cursiv_v215.core import presence
    from . import status as _net_status
    if _net_status.answers_network_question(_field_text) and not presence.short_state_question(_field_text):
        yield _file_ops.VerifiedText(_net_status.network_answer())
        yield '\n\n*[Sources: Cursiv application state (no AI model)]*'
        return
    if presence.answers_state_question(_field_text):
        observed = presence.snapshot(root_path, file_access,
            person=None if presence.short_state_question(_field_text) else _notebook_person())
        runtime.grounding.set_state(observed)
        yield _file_ops.VerifiedText(presence.state_answer(observed, _field_text))
        yield '\n\n*[Sources: Cursiv application state (no AI model)]*'
        return
    _notebook = (notebook_tools.command(_field_text, history, observer=_notebook_person().title(), scope=notebook_scope)
                 if policy.inspect else None)
    if _notebook is not None:
        from cursiv_v215.memory import intents as _native_memory
        _native_memory.clear_pending(_notebook_person(), notebook_scope)
        yield _notebook.render()
        return
    from cursiv_v215.memory import intents as _memory_intents
    _memory_action = (_memory_intents.command(_field_text, history, person=_notebook_person(), scope=notebook_scope)
                      if policy.inspect else None)
    if _memory_action is not None:
        yield _memory_action.render()
        return
    _file_reply = (_file_ops.command(_field_text, history, root_path if file_access else None)
                   if policy.inspect else None)
    if _file_reply is not None:
        if on_action:
            for receipt in _file_reply.receipts:
                on_action(receipt)
        if _file_reply.pending:
            yield runtime.WRITE_SENTINEL + runtime.json.dumps(_file_reply.pending)
        else:
            yield _file_ops.VerifiedText(_file_reply.text)
            yield '\n\n*[Sources: Cursiv file execution result (no AI model)]*'
        return
    runtime.grounding.set_state(presence.snapshot(root_path, file_access))
    _field_reply = field_recall.command(_field_text) if runtime.turn_policy.current().inspect else None
    if _field_reply is not None:
        yield _field_reply
        return
    from cursiv_v215.core import curiosity_engine
    from cursiv_v215.memory import semantic as _journal_sem
    from cursiv_v215.core.paths import save_reference
    _journal_scope = save_reference(root_path) if file_access and root_path else 'general'
    _journal_reply = (curiosity_engine.command(_field_text, _journal_sem.current_person(), _journal_scope)
                      if runtime.turn_policy.current() == runtime.turn_policy.Policy() else None)
    if _journal_reply is not None:
        yield _journal_reply
        return
    runtime._PHASE_AFTER = ""                # set by the phases for this message only
    runtime._EMERGENCY_TURN = False
    runtime._CURSIV_REPLY = False
    reply: list[str] = []
    from cursiv_v215.memory import semantic as _memory
    import uuid
    _turn_person, _turn_id = _memory.current_person(), uuid.uuid4().hex
    from cursiv_v215.core import speed as _speed
    _speed.chat_started()
    origin, skip = "inferred", False
    deterministic_correction = False
    deferred_review = None
    try:
        action_options = {'on_action': on_action} if on_action is not None else {}
        yield from runtime._chat_stream(message, history, api_key, files, file_access, root_path,
                                openai_key, confirm_writes, anthropic_key, force_provider, reply, **action_options)
        if any(isinstance(chunk, _file_ops.VerifiedText)
               and isinstance(chunk.result, _file_ops.FileResult)
               and (not chunk.result.ok or chunk.result.operation not in ('read_file', 'list_directory', 'search_files'))
               for chunk in reply):
            return                 # a model cannot revise a failed operation or mutation receipt
        if on_stage:
            on_stage("Checking the answer…")
        from cursiv_v215.core import file_access as _files
        _user = message.get('text', '') if isinstance(message, dict) else str(message or '')
        if _files.is_request(_user):
            return                 # actual file results need no AI check or automatic learning
        draft = runtime._strip_status_lines("".join(reply))      # the model's words, not Cursiv's notes
        from cursiv_v215.core import deterministic_overrides as _overrides
        _conflict = _overrides.conflicting_doses(_field_text, runtime._DOCS_SHOWN)
        if _conflict:
            runtime._CURSIV_REPLY = True
            runtime._set_answered('')
            final = _conflict + '\n\n*[' + runtime.sources_line('', _field_text) + ']*'
            reply[:] = [final]
            yield (_replace_prefix if replace_draft else '\n\nCorrection: ') + final
            return
        from . import response_style
        polished = response_style.trim_closer(_field_text, draft) if replace_draft else draft
        if polished != draft:
            notes = [m.group(0).strip() for m in runtime._STATUS_LINE_RE.finditer(''.join(reply))]
            shown = '\n\n'.join([polished, *notes])
            reply[:] = [shown]
            yield _replace_prefix + shown
            draft = polished
        _capability_problem = presence.contradiction(draft, runtime.grounding.state())
        if _capability_problem:
            reply[:] = [_capability_problem]
            yield (_replace_prefix if replace_draft else '\n\n') + _capability_problem
            skip = deterministic_correction = True
            draft = _capability_problem
        _source_problem = runtime.grounding.quote_problem(_field_text, draft)
        if _source_problem:
            reply[:] = [_source_problem]
            yield (_replace_prefix if replace_draft else '\n\n') + _source_problem
            skip = deterministic_correction = True
            draft = _source_problem
        if _file_ops.unverified_claim(draft):
            # An LLM acknowledgement cannot establish a completed action. Native
            # action routes return earlier; provider receipts do not use this prose.
            correction = str(_file_ops.model_prose(draft))
            reply[:] = [correction]
            if replace_draft:
                yield _replace_prefix + correction
            else:
                yield '\n\n' + correction
            skip = True
            deterministic_correction = True
            draft = correction
        if runtime._WORKED and runtime._WORKED.lead and draft.startswith(runtime._WORKED.lead.strip()):
            draft = draft[len(runtime._WORKED.lead.strip()):].strip()    # nor Cursiv's own safety line
        if runtime._PHASE_AFTER:             # Route / Recovery notes from the phases
            reply.append(runtime._PHASE_AFTER)
            yield runtime._PHASE_AFTER
        # No model call, so it runs on emergency turns too (core/answer_check.py).
        try:
            from cursiv_v215.core import answer_check as _ac
            from cursiv_v215.core import answer_assessment as _assessment
            # An answer that opens "Yes, it's safe" and then says not to go: the warning goes on
            # top, where it's read first (benchmark saf-012, U67).
            _lead = _ac.lead_warning(draft) if replace_draft else ""
            if _lead:
                _full = "".join(reply)
                _at = _full.find(draft[:60]) if draft[:60] else -1
                _full = (_full[:_at] + _lead + "\n\n" + _full[_at:]) if _at >= 0 else (_lead + "\n\n" + _full)
                reply[:] = [_full]
                yield _replace_prefix + _full
            _flag = _ac.notes(draft, list(runtime._REF_SHOWN), runtime._WEB_SEARCHED, flip_above=bool(_lead))
            if runtime._DOCS_SHOWN:
                from cursiv_v215.core import documents as _docs
                _bad_cites = _docs.cited_pages_problems(draft, list(runtime._DOCS_SHOWN))
                if _bad_cites:
                    _flag += "\n\n*(Cursiv's check: the answer " + "; ".join(_bad_cites) + ". Check it against the pages listed above.)*"
            if runtime._WORKED:
                from cursiv_v215.core import calc as _calc
                _miss = _calc.check(draft, runtime._WORKED)
                if _miss and replace_draft and runtime._WORKED.tool == "units":
                    # A note under a wrong conversion leaves the false number visible. Correct the
                    # conversion claim in place when possible, preserving other answer content.
                    corrected_draft = _calc.correct_units_answer(draft, runtime._WORKED) or runtime._WORKED.statement
                    final = runtime._replacement_reply(
                        corrected_draft, "".join(reply),
                        ["the streamed conversion conflicted with Cursiv's calculated result"],
                    )
                    reply[:] = [final]
                    draft = corrected_draft
                    deterministic_correction = True
                    yield _replace_prefix + final
                elif _overrides.calculation(runtime._WORKED, _miss):
                    runtime._CURSIV_REPLY = True
                    runtime._set_answered('')
                    final = _overrides.calculation(runtime._WORKED, _miss)
                    from cursiv_v215.core import claims as _claims
                    _prior = _claims.history_notes(draft, runtime._evidence(message, history))
                    if _prior:
                        final += '\n\n' + '\n'.join(_prior)
                    reply[:] = [final]
                    yield (_replace_prefix if replace_draft else '\n\n**Correction:** ') + final
                    return
                else:
                    _flag += ("\n\n" + _miss) if _miss else ""
            # What the answer says Cursiv did, against what Cursiv's code recorded (core/claims.py)
            from cursiv_v215.core import claims as _claims
            _flag += _claims.notes(draft, runtime._evidence(message, history))
            _structured = _assessment.assess(
                _user, draft, titles=list(runtime._REF_SHOWN), searched=runtime._WEB_SEARCHED,
                evidence=runtime._evidence(message, history), worked=runtime._WORKED,
                docs=list(runtime._DOCS_SHOWN))
            if any(p.code in ('DOSE_MISMATCH', 'REFERENCE_CONTRADICTION') for p in _structured):
                runtime._CURSIV_REPLY = True
            _withdrawal = (_overrides.reference(_structured, runtime._REF_SHOWN, runtime.sources_line('', _user))
                           or _overrides.execution(_structured, runtime._evidence(message, history)))
            if _withdrawal:
                runtime._CURSIV_REPLY = True
                runtime._set_answered('')
                final = _withdrawal
                reply[:] = [final]
                yield (_replace_prefix if replace_draft else '\n\nCorrection: ') + final
                return  # no model rewrite or learning from the withdrawn draft
            for item in _structured:
                if item.code == 'SMALL_SAMPLE_INFERENCE':
                    _flag += '\n\n*(Cursiv\'s check: ' + item.message + '.)*'
            if any(item.severity == 'error' for item in _structured):
                skip = deterministic_correction = True
            if _flag:
                reply.append(_flag)
                yield _flag
        except Exception:
            skip = deterministic_correction = True
            note = "\n\n*(Cursiv's check: a deterministic check was unavailable. This answer is unverified.)*"
            reply.append(note)
            yield note
        # Pure checks stay in this worker. A desktop callback only queues the
        # isolated model review; it starts after the answer is finalized in Qt.
        try:
            if runtime._EMERGENCY_TURN or runtime._CURSIV_REPLY or deterministic_correction or _speed.battery_saver():
                raise runtime._SkipCheck      # no slow check (or a wall of notes) after emergency steps
            from cursiv_v215.core import verify as _verify
            from cursiv_v215.chat import review as _review
            user_text = message.get("text", "") if isinstance(message, dict) else str(message or "")
            selected_mode = (review_mode or _review.mode()) if runtime.turn_policy.current().inspect else 'off'
            if selected_mode not in _review.MODES:
                raise ValueError('Invalid answer check mode')
            job = _review.prepare(runtime, user_text, draft, history, selected_mode, background=on_review is not None)
            if job is None:
                raise runtime._SkipCheck
            if on_review is not None and job.mode != 'off':
                deferred_review, skip = job, True  # no assistant-derived retention before a pending check
                raise runtime._SkipCheck
            outcome = job.run()
            origin, skip = outcome.learn_origin, outcome.skip_learn
            revised = outcome.append.split("**Revised after check:**\n", 1)
            if replace_draft and outcome.append and len(revised) == 2 and outcome.clear:
                final = runtime._replacement_reply(revised[1], "".join(reply), outcome.problems)
                reply[:] = [final]
                yield _replace_prefix + final
            elif outcome.append:
                shown = runtime._compact_notes(outcome) if "**Draft + notes:**" in outcome.append else outcome.append
                reply.append(shown)
                yield shown
        except runtime._SkipCheck:
            pass
        except Exception:
            skip = True
            note = "\n\n*(Cursiv's check: the answer checker was unavailable. This answer is unverified.)*"
            reply.append(note)
            yield note
    finally:
        _speed.chat_finished()
    # The optional existing answer checker can itself revise prose. Apply the
    # same deterministic checks to that final revision without another LLM call.
    _final_problem = (presence.contradiction(runtime._strip_status_lines(''.join(reply)), runtime.grounding.state())
                      or runtime.grounding.quote_problem(_field_text, ''.join(reply)))
    if _final_problem:
        deferred_review = None
        reply[:] = [_final_problem]
        yield (_replace_prefix if replace_draft else '\n\n') + _final_problem
        skip = True
    if runtime.turn_policy.current().automatic_memory:
        runtime._learn_later(message, "".join(reply), origin=origin, skip=skip, person=_turn_person, event_id=_turn_id)
    if not skip and not runtime._EMERGENCY_TURN and runtime.turn_policy.current().automatic_memory:
        curiosity_engine.notify(_turn_person, _journal_scope, _field_text)
        try:
            _suggestion = curiosity_engine.suggestion(_turn_person, _journal_scope)
            if _suggestion:
                yield '\n\n' + _suggestion
        except (OSError, ValueError):
            pass
    if deferred_review is not None:
        on_review(deferred_review)

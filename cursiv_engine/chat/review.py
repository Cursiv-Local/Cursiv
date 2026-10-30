"""Bounded, local answer review with immutable turn evidence and no widget access."""
from __future__ import annotations

from contextvars import copy_context, ContextVar
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from functools import partial
import threading

from cursiv_engine.core import answer_assessment, presence, verify
from cursiv_engine.core.problems import Problem

TOKENS = 180
REWRITE_TOKENS = 300
MODES = ('off', 'fast', 'full')
_MODEL_SLOT = threading.Lock()
_MODEL_STATE = ContextVar('cursiv_review_model_state', default=None)


@contextmanager
def model_activity(stage='checking answer'):
    """Notify only around a real model invocation, after availability checks."""
    callback = _MODEL_STATE.get()
    def notify(value):
        if callback:
            try:
                callback(value)
            except Exception:
                pass  # presentation failure must not change a check's outcome
    notify(stage)
    try:
        yield
    finally:
        notify('')


def mode() -> str:
    from cursiv_engine.chat.keys import saved_key
    value = saved_key('answer_check_mode')
    return value if value in MODES else 'fast'


def set_mode(value: str) -> None:
    """Preserve other settings and refuse corrupt configuration instead of resetting it."""
    from cursiv_engine.chat.keys import KEYS_FILE
    from cursiv_engine.core import state_store, atomic
    import json
    if value not in MODES:
        raise ValueError('Choose check off, check fast or check full')
    with state_store.LOCK:
        data = state_store.load(KEYS_FILE, {})
        if not isinstance(data, dict):
            raise ValueError('Invalid settings; nothing changed')
        state_store.checked(KEYS_FILE)
        KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_text(KEYS_FILE, json.dumps(dict(data, answer_check_mode=value), indent=2))
        if state_store.load(KEYS_FILE, {}).get('answer_check_mode') != value:
            raise OSError('Answer-check setting was not verified')


def context(history: list[dict], memory: str) -> str:
    """Use already supplied context; never retrieve another saved fact for review."""
    turns = [str(row.get('role', 'user')) + ': ' + str(row.get('content', ''))[:500]
             for row in history[-4:] if row.get('role') in ('user', 'assistant')]
    return ('\n'.join(turns) + '\n' + memory)[:1600]


@dataclass(frozen=True)
class Job:
    question: str
    draft: str
    context: str
    sources: str
    assess: object
    ask: object
    mode: str
    scope: object = field(default_factory=copy_context, repr=False)
    cancelled: threading.Event = field(default_factory=threading.Event, repr=False)

    def run(self, on_model_state=None):
        if self.cancelled.is_set():
            return None
        acquired = self.mode == 'off' or _MODEL_SLOT.acquire(blocking=False)
        if not acquired:
            return verify.PassResult(status='unavailable', skip_learn=True,
                                     append='Optional review not run: another local review is still stopping. Code checks still ran.')

        def run():
            from .activity import guard
            _MODEL_STATE.set(on_model_state)
            def ask(messages):
                return '' if self.cancelled.is_set() else self.ask(messages, self.cancelled)
            # Review has its own immutable evidence/cancellation; the foreground turn has ended.
            from . import model_selection
            with guard(lambda: not self.cancelled.is_set()), model_selection.provenance_scope(False):
                return verify.run_pass(self.question, self.draft, ask=ask, context=self.context,
                                       sources=self.sources, assess=self.assess, mode=self.mode,
                                       update_session=False, previous_failed=False)
        try:
            result = self.scope.copy().run(run)
        finally:
            if self.mode != 'off':
                _MODEL_SLOT.release()
        return None if self.cancelled.is_set() else result


def prepare(runtime, question, draft, history, selected_mode, *, background: bool) -> Job | None:
    """Capture evidence now; the worker never reads legacy mutable chat records."""
    if runtime.turn_policy.current().inspect:
        verify.store_ledger_from(question, draft)  # foreground only; workers never mutate session ledgers
    from cursiv_engine.core import self_inspection
    own_source = self_inspection.current() is not None
    evidence = deepcopy(runtime._evidence(question, history))
    assess = partial(answer_assessment.assess, question, titles=tuple(runtime._REF_SHOWN),
                     searched=runtime._WEB_SEARCHED, evidence=evidence,
                     worked=deepcopy(runtime._WORKED), docs=deepcopy(tuple(runtime._DOCS_SHOWN)))
    supplied = '\n\n'.join(runtime._RETRIEVED +
                            (['Calculated by Cursiv: ' + runtime._WORKED.statement] if runtime._WORKED else []))
    supplied_history = [dict(row, content=runtime._strip_status_lines(str(row.get('content', ''))))
                        for row in history[-4:]]
    ctx = context(supplied_history, '\n'.join(runtime.grounding.memory_sources()))
    from cursiv_engine.core import reasoning_context
    history_snapshot = deepcopy(history[-64:])
    saved_snapshot = reasoning_context.saved_context()
    def grounded_assessment(text):
        found = assess(text)
        constraint = reasoning_context.contradiction_note(question,text,history_snapshot,saved_snapshot)
        if constraint:
            found.append(Problem('CONVERSATION_CONSTRAINT','error',constraint))
        return found
    # Assess formatting/constraints against supplied history too, without an LLM.
    issues = verify._issues(question, draft, ctx, supplied) + grounded_assessment(draft)
    if selected_mode != 'full':
        issues = [p for p in issues if p.code != 'MISSING_LEDGER']
    if selected_mode == 'off' and not issues:
        return None
    immediate = any(item.severity == 'error' for item in issues) or (
        selected_mode == 'fast' and any(item.severity == 'warning' for item in issues)) or selected_mode == 'off'
    if selected_mode != 'full' and not immediate and not any(item.severity == 'warning' for item in issues) and not verify.should_verify(question, draft):
        return None
    observed = deepcopy(runtime.grounding.state())
    quote_problem = runtime.grounding.quote_problem
    scope = copy_context()

    def assessment(text):
        found = grounded_assessment(text)
        problem = presence.contradiction(text, observed or {}) or quote_problem(question, text)
        if problem:
            found.append(Problem('REVIEW_GROUNDING', 'error', problem))
        return found

    # Bind services, not evidence-bearing module attributes, for the worker.
    running, resolve, generate = runtime._ollama_running, runtime._resolve_ollama_model, runtime._call_ollama_model
    router = runtime._router_llm

    def ask(messages, cancelled):
        budget = REWRITE_TOKENS if messages[0]['content'].startswith('Rewrite') else TOKENS
        if not background and not own_source:
            with model_activity():
                return router(messages, max_tokens=budget)
        if cancelled.is_set() or not running():
            return ''
        model = resolve(standard=True)
        if not model or cancelled.is_set():
            return ''  # optional review never starts/downloads a model or falls back to cloud
        system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
        prompt = '\n'.join(m['content'] for m in messages if m['role'] != 'system')
        parts = []
        with model_activity('reviewing wording' if budget == REWRITE_TOKENS else 'checking answer'):
            stream = generate(model, system, prompt, max_tokens=budget, collect=False)
            try:
                for chunk in stream:
                    if cancelled.is_set():
                        return ''
                    parts.append(chunk)
            finally:
                close = getattr(stream, 'close', None)
                if close:
                    close()
        output = ''.join(parts).strip()
        return '' if output.startswith('[') and 'error' in output[:150].lower() else output

    return Job(question, draft, ctx, supplied, assessment, ask, 'off' if immediate else selected_mode, scope=scope)


def followup(result) -> str:
    """Review prose is a labeled follow-up, never a new execution receipt or memory save."""
    if result is None or result.status == 'skipped':
        return ''
    if result.status == 'revised' and result.clear:
        return '\n\n**Check — suggested revision:**\n' + result.append.split('**Revised after check:**\n', 1)[-1]
    if result.clear:
        return ''  # quiet when clean; the saved review metadata retains the result
    return '\n\n**Check notes:**\n' + (result.append.strip() or 'Review unavailable; the answer is unverified.')

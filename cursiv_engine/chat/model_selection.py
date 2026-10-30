"""Explicit per-turn provider/model selection; never a fallback or a tool grant."""
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
import inspect
import re

PROVIDERS = ('ollama','openai','claude','grok','groq','gemini')
LABELS = dict(ollama='Ollama',openai='OpenAI',claude='Anthropic',grok='xAI',groq='Groq',gemini='Gemini')

@dataclass(frozen=True)
class Selection:
    provider: str
    model: str

_active = ContextVar('cursiv_explicit_model',default=None)
_response = ContextVar('cursiv_responding_model',default=None)
_foreground = ContextVar('cursiv_foreground_model_provenance',default=False)
_failure = ContextVar('cursiv_selected_model_failure',default='')

def failed(): return _failure.get()

def fail(runtime,message,*,native=True):
    _failure.set(message)
    runtime._set_answered('')
    runtime._CURSIV_REPLY=native

@contextmanager
def provenance_scope(enabled=True):
    token = _foreground.set(enabled)
    try: yield
    finally: _foreground.reset(token)

def response(): return _response.get()

def reset_response(): _response.set(None)

def label_for(label):
    item = response()
    if not item: return label
    provider,requested,actual = item
    if label in (LABELS[provider], 'Claude' if provider=='claude' else '', 'Ollama (local)' if provider=='ollama' else '',
                 'Local coding models' if provider=='ollama' else '') or (provider=='ollama' and label.startswith('Local coding models ·')):
        return f'{LABELS[provider]} · {actual}' + (f' (requested {requested})' if actual!=requested else '')
    return label

def parse(value: str) -> Selection | None:
    if '::' not in (value or ''): return None
    provider,model = value.split('::',1)
    if provider not in PROVIDERS or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,180}',model):
        raise ValueError('Choose a supported provider and an exact model ID')
    return Selection(provider,model)

def current(): return _active.get()

def model(provider: str, default: str) -> str:
    choice = current()
    return choice.model if choice and choice.provider == provider else default

@contextmanager
def use(choice):
    token = _active.set(choice)
    try: yield
    finally: _active.reset(token)

def scoped(function):
    signature = inspect.signature(function)
    @wraps(function)
    def generate(*args,**kwargs):
        values = signature.bind(*args,**kwargs).arguments
        try: choice = parse(values.get('force_provider',''))
        except ValueError as exc:
            yield f'Model selection error: {exc}. No model was called.'
            return
        token = _response.set(None)
        failure_token = _failure.set('')
        try:
            with use(choice),provenance_scope(): yield from function(*args,**kwargs)
        finally:
            _response.reset(token)
            _failure.reset(failure_token)
    return generate

def record(runtime, provider: str, requested: str, returned: str | None = None):
    """Transport-owned provenance; requested and resolved IDs may differ by alias."""
    if not _foreground.get(): return
    actual = returned or requested
    _response.set((provider,requested,actual))
    from cursiv_engine.core import last_turn
    last_turn.record_response(LABELS[provider],requested,actual)
    runtime._set_answered(f'{LABELS[provider]} · {actual}' +
        (f' (requested {requested})' if actual != requested else ''))

def stream(runtime, choice: Selection, messages, *, api_key='',openai_key='',anthropic_key='',max_tokens=2000):
    """Use existing transports and security gates, one selected backend only.

    Explicit models are supplied by the installed list or user, not a hardcoded
    new provider ID. The provider validates cloud IDs when the request is made.
    """
    runtime._set_answered('')
    if choice.provider != 'ollama' and not runtime.netgate.allowed():
        fail(runtime,f'{LABELS[choice.provider]} / {choice.model} unavailable: offline mode blocks this provider. No fallback was used.')
        yield failed()
        return
    with use(choice):
        if choice.provider == 'ollama':
            installed = runtime._ollama_pulled_models()
            if choice.model not in installed:
                fail(runtime,f'Ollama / {choice.model} is not installed or its inventory is unavailable. No download or fallback was used.')
                yield failed()
                return
            gen = runtime._call_ollama(messages,max_tokens=max_tokens)
        else:
            field = dict(grok='api_key',claude='anthropic_key',openai='openai_key',groq='groq_key',gemini='gemini_key')[choice.provider]
            key = dict(api_key=api_key,openai_key=openai_key,anthropic_key=anthropic_key).get(field) or runtime._saved_key(field)
            if not key:
                fail(runtime,f'{LABELS[choice.provider]} / {choice.model} unavailable: no configured key. No fallback was used.')
                yield failed()
                return
            if choice.provider == 'grok': gen = runtime._call_xai_stream(messages,key,False,max_tokens)
            elif choice.provider == 'claude': gen = runtime._call_claude_direct(messages,key,max_tokens)
            elif choice.provider == 'openai': gen = runtime._call_openai_direct(messages,key,max_tokens=max_tokens)
            elif choice.provider == 'groq': gen = runtime._call_groq_direct(messages,key,max_tokens)
            else: gen = runtime._call_gemini_direct(messages,key,max_tokens)
        produced = False
        for chunk in gen:
            if chunk == runtime.RATE_SENTINEL or re.match(r'(?is)^\s*\[(?:Ollama|OpenAI|Claude|xAI|Groq|Gemini).*?(?:error|unavailable|not found)',str(chunk)):
                fail(runtime,f'{LABELS[choice.provider]} / {choice.model} failed. No other model was tried.',native=not produced)
                yield failed()
                return
            if str(chunk).strip(): produced = True
            yield chunk
        if not produced:
            fail(runtime,f'{LABELS[choice.provider]} / {choice.model} returned no text. No fallback was used.')
            yield failed()

def writing_revision(runtime,messages,*,api_key='',openai_key='',anthropic_key='',max_tokens=500):
    """One writing revision uses the same responding backend, never a hidden local substitute."""
    choice,actual=current(),response()
    if choice is None and actual: choice=Selection(actual[0],actual[1])
    if choice:
        return ''.join(stream(runtime,choice,messages,api_key=api_key,openai_key=openai_key,
            anthropic_key=anthropic_key,max_tokens=max_tokens)).strip()
    if runtime._ANSWERED_BY and not runtime._ANSWERED_BY.startswith('Ollama'):
        return ''  # unknown server model cannot be pinned honestly
    return runtime._local_llm(messages,max_tokens).strip()

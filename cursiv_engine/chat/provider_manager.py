"""Always-visible inventory, explicit routing and owned inference outcomes.

Inference never retries/falls back automatically: a timed-out POST may already
have incurred cost. Discovery failures retain cached and catalog model IDs.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, replace
import copy
import re
import threading

from . import provider_adapters as adapters, provider_settings as settings
from . import provider_http as http
from .provider_registry import get, providers, Model
from .provider_types import Request, Result, ProviderError, ErrorCode as E
from .request_budget import Stopped,current as current_budget

_outcome = ContextVar('provider_outcome', default=None)
_request = ContextVar('provider_request_snapshot', default=None)
_options = ContextVar('provider_turn_options', default={})


@contextmanager
def turn_options(**values):
    token = _options.set(values)
    _outcome.set(None)
    _request.set(None)
    try:
        yield
    finally:
        _options.reset(token)


def outcome():
    return _outcome.get()


def reset_response():
    """Start a new desktop turn without inheriting an earlier provider failure."""
    _outcome.set(None)
    _request.set(None)


def research_authorized():
    return bool(_options.get().get('research_authorized'))


def snapshot():
    value = _request.get()
    return replace(value, messages=copy.deepcopy(value.messages)) if value else None


def model_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@+\-]{0,180}', value):
        raise ValueError('Enter an exact model ID')
    return value


def models(provider, *, refresh=False):
    spec = get(provider)
    saved = settings.load()
    cached = saved.get('models', {}).get(provider, [])
    merged = {item:Model(item, provider) for item in spec.catalog}
    for row in cached:
        try:
            item = Model(**row)
            item.source, item.verified = 'cached', False
            merged[item.id] = item
        except (ValueError, TypeError):
            continue
    error = None
    if refresh:
        try:
            key = settings.key(provider)
            http.preflight(provider, credential=key)
            found = adapters.discover(provider, key)
            for item in found:
                merged[item.id] = item
            cache = saved.get('models', {})
            cache[provider] = [asdict(item) for item in found]
            settings.update(models=cache)
            _status(provider, 'Last connection check passed; refresh to recheck')
        except ProviderError as exc:
            error = exc
            _status(provider, exc.message)
    current = settings.load()
    chosen = current.get('model') if current.get('provider') == provider else ''
    manual = settings.endpoint(provider).get('model') or chosen
    if manual and manual not in merged:
        merged[manual] = Model(manual, provider, 'manual')
    return list(merged.values()), error


def _status(provider, status):
    from cursiv_engine.core import turn_policy
    if turn_policy.current() != turn_policy.Policy():
        return
    values = settings.load().get('statuses', {})
    values[provider] = status
    settings.update(statuses=values)


def status(provider):
    try:
        http.preflight(provider, credential=settings.key(provider))
    except ProviderError as exc:
        return exc.message.split(': ', 1)[-1]
    return settings.load().get('statuses', {}).get(provider, 'Connection not tested')


def choose(mode):
    if mode == 'local_auto':
        # Local discovery only; never use remote endpoints or cloud keys.
        for provider in ('ollama', 'lmstudio', 'custom'):
            try:
                if not http.location(provider)[1]:
                    continue
                found = adapters.discover(provider, settings.key(provider))
                if found:
                    preferred = settings.load().get('model', '')
                    ids = [m.id for m in found]
                    return provider, next((m for m in (preferred, 'qwen3:4b-instruct') if m in ids), ids[0])
            except ProviderError:
                continue
        raise ProviderError('ollama', E.UNAVAILABLE)
    if mode == 'cloud_auto':
        from cursiv_engine.core import netgate
        if not netgate.allowed():
            raise ProviderError('cloud_auto', E.OFFLINE)
        saved = settings.load()
        for provider in saved.get('cloud_authorized', []):
            if provider not in {p.id for p in providers()}:
                continue
            spec = get(provider)
            if spec.local or (spec.credential and provider != 'custom' and not settings.key(provider)):
                continue
            if not http.location(provider)[1]:
                known, _ = models(provider)
                if known:
                    return provider, known[0].id
        raise ProviderError('cloud_auto', E.PERMISSION)
    raise ValueError('Unknown automatic routing mode')


def infer(request):
    result = Result(request.provider, request.model,request_id=request.request_id)
    _outcome.set(result)
    _request.set(replace(request, messages=copy.deepcopy(request.messages)))
    try:
        try:
            get(request.provider)
        except KeyError:
            raise ProviderError(request.provider,E.CAPABILITY) from None
        model_id(request.model)
        options=_options.get()
        request.authorized_destination=request.authorized_destination or options.get('destination')
        if not request.endpoint_url and request.authorized_destination and request.authorized_destination[0]==request.provider:
            request.endpoint_url=request.authorized_destination[1]
        with settings._lock:
            key = settings.key(request.provider)
            current_url=http.location(request.provider)[0]
            request.endpoint_url=request.endpoint_url or current_url
            _request.set(replace(request,messages=copy.deepcopy(request.messages)))
            budget=current_budget()
            _, local, _ = http.preflight(request.provider, credential=key, local_only=request.local_only or bool(budget and budget.local_only))
        if request.endpoint_url != current_url:
            raise ProviderError(request.provider,E.PERMISSION)
        if request.authorized_destination and (request.provider,current_url,request.model) != tuple(request.authorized_destination):
            raise ProviderError(request.provider,E.PERMISSION)
        result.local = local
        if not local and not request.research_authorized:
            # Calling code must explicitly authorize the assembled research
            # context. A model selection cannot authorize disclosure.
            raise ProviderError(request.provider, E.PERMISSION)
        from .activity import check_guard
        check_guard()
        result.attempted_provider = request.provider
        yield from adapters.stream(request, result, key)
        if request.cancel is not None and request.cancel.is_set():
            raise ProviderError(request.provider,E.CANCELLED)
        check_guard()
    except ValueError:
        exc = ProviderError(request.provider, E.MODEL)
        result.error, result.error_message = exc.code.value, exc.message
    except ProviderError as exc:
        if request.cancel is not None and request.cancel.is_set():
            exc = ProviderError(request.provider, E.CANCELLED)
        result.error, result.error_message = exc.code.value, exc.message
        result.canceled = exc.code == E.CANCELLED
        result.responding_provider=None
        _status(request.provider, exc.message)
    except Stopped:
        from .activity import _GUARD
        canceled=(request.cancel is not None and request.cancel.is_set()) or not _GUARD.get()()
        exc=ProviderError(request.provider,E.CANCELLED if canceled else E.BUDGET)
        result.error,result.error_message,result.canceled=exc.code.value,exc.message,canceled
        result.responding_provider=None
    except GeneratorExit:
        exc = ProviderError(request.provider, E.CANCELLED)
        result.error, result.error_message, result.canceled = exc.code.value, exc.message, True
        raise
    except Exception:
        canceled = request.cancel is not None and request.cancel.is_set()
        exc = ProviderError(request.provider, E.CANCELLED if canceled else E.MALFORMED)
        result.error, result.error_message = exc.code.value, exc.message
        result.canceled = canceled

    finally:
        from cursiv_engine.core import last_turn
        last_turn.diagnostic_event('provider_result',provider=result.provider,model=result.actual_model,
            status='failed' if result.error else 'succeeded',error=result.error,
            attempted=bool(result.attempted_provider),responded=bool(result.responding_provider))


def selected_infer(messages, *, cfg=None, capability='text', max_tokens=800):
    """Auxiliary requests (including vision) obey the same exact selection."""
    saved, options = settings.load(), _options.get()
    cfg=cfg or {}
    provider=cfg.get('selected_provider',saved['provider'] if saved['mode']=='manual' else '')
    mode='cloud_auto' if provider=='cloud_auto' else 'manual' if provider else saved['mode']
    if mode=='manual':
        model=cfg.get('selected_model',saved['model'])
    else:
        try:
            if mode=='local_auto' and capability=='image_generation':
                provider,model='ollama',saved['model'] or 'qwen3:4b-instruct'
            else:
                provider,model=choose(mode)
        except ProviderError as exc:
            model='qwen3:4b-instruct' if exc.provider=='ollama' else ''
            _outcome.set(Result(exc.provider,model,error=exc.code.value,error_message=exc.message))
            _request.set(Request(exc.provider,model,messages,capability=capability))
            return
    yield from infer(Request(provider,model,messages,max_tokens,cancel=options.get('cancel'),
        research_authorized=bool(options.get('research_authorized')),
        local_only=bool(options.get('local_only')) or settings.project_local_only(options.get('workspace')),
        capability=capability))


def dispatch(runtime, provider, model, messages, *, max_tokens=2000):
    options = _options.get()
    if provider=='ollama' and all(isinstance(m.get('content'),str) for m in messages):
        from cursiv_engine.core import speed
        latest=next((m for m in reversed(messages) if m.get('role')=='user'),None)
        messages=runtime._slim(messages,14000 if speed.small_gpu() else 48000)
        if latest is not None:
            index=next((i for i in range(len(messages)-1,-1,-1) if messages[i].get('role')=='user'),None)
            if index is not None:
                messages[index]=dict(latest)  # preserve the current prompt verbatim for failure/retry
    request = Request(provider, model, messages, max_tokens,
                      research_authorized=bool(options.get('research_authorized')),
                      local_only=bool(options.get('local_only')) or settings.project_local_only(options.get('workspace')),
                      cancel=options.get('cancel'))
    from . import model_selection
    for chunk in infer(request):
        yield chunk
    result = outcome()
    if result.error:
        model_selection.fail(runtime, result.error_message, native=True)
        yield result.error_message
    else:
        model_selection.record(runtime, provider, model, result.actual_model)
        runtime._set_answered(result.label())


def automatic(runtime, mode, messages):
    from . import model_selection
    try:
        provider, model = choose(mode)
    except ProviderError as exc:
        model = '' if exc.provider == 'cloud_auto' else settings.load().get('model') or get(exc.provider).catalog[0]
        result = Result(exc.provider, model, error=exc.code.value, error_message=exc.message)
        _outcome.set(result)
        options = _options.get()
        _request.set(Request(exc.provider,model,messages,research_authorized=bool(options.get('research_authorized')),
            local_only=bool(options.get('local_only')),cancel=options.get('cancel')))
        model_selection.fail(runtime, exc.message)
        yield exc.message
        return
    yield from dispatch(runtime, provider, model, messages)


def cascade(runtime, messages, max_tokens, local_fn=None):
    """Legacy command surfaces share explicit settings; no key-driven cascade."""
    from .activity import serialized_work
    used = []
    @serialized_work
    def generate():
        saved = settings.load()
        if saved['mode'] == 'manual':
            yield from dispatch(runtime,saved['provider'],saved['model'],messages,max_tokens=max_tokens)
        elif saved['mode'] == 'cloud_auto':
            yield from automatic(runtime,'cloud_auto',messages)
        else:
            if not runtime._local_model_ready():
                yield from automatic(runtime,'local_auto',messages)
            else:
                stream = local_fn(messages) if local_fn else runtime._call_ollama(messages,max_tokens=max_tokens)
                for text in stream:
                    if text == runtime.RATE_SENTINEL or (isinstance(text,str) and text.lstrip().startswith(runtime._PROVIDER_ERROR_PREFIXES)):
                        from . import model_selection
                        error = ProviderError('ollama',E.UNAVAILABLE)
                        model = runtime._resolve_ollama_model() or 'qwen3:4b-instruct'
                        _outcome.set(Result('ollama',model,error=error.code.value,error_message=error.message))
                        options = _options.get()
                        _request.set(Request('ollama',model,messages,cancel=options.get('cancel')))
                        model_selection.fail(runtime,error.message)
                        yield error.message
                        return
                    if text:
                        if not used:
                            used.append('Ollama (local)')
                        yield text
                return
        result = outcome()
        if result and not result.error:
            used.append(result.label())
    return generate(), used


def retry(request, *, provider=None, model=None, authorize_changed=False):
    """Inference-only replay. This never re-enters notebook/file/command dispatch."""
    replay = replace(request, messages=copy.deepcopy(request.messages))
    replay.cancel = request.cancel or threading.Event()
    destination = (provider or replay.provider, model or replay.model)
    url=http.location(destination[0])[0]
    changed=destination != (replay.provider,replay.model) or (replay.endpoint_url and replay.endpoint_url != url)
    if changed and not authorize_changed:
        raise ValueError('Confirm the new provider/model before retrying')
    replay.provider, replay.model = destination
    replay.endpoint_url=url
    if changed and replay.research_authorized:
        replay.authorized_destination=(replay.provider,url,replay.model)
    # No tools are executed by these adapters, even on retry.
    yield from infer(replay)

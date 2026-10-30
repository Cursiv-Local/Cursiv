"""Owned run budgets at the actual generation transport, including retries.

No prompts, credentials or response text are retained by the default counters.
Token estimates use UTF-8 bytes as a conservative bound; provider usage is separate.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import threading
import time
from urllib.parse import urlsplit

_CURRENT = ContextVar('cursiv_request_budget', default=None)


class Stopped(RuntimeError):
    pass


@dataclass
class Budget:
    ceiling: int
    context: int = 8192
    seconds: float = 240
    local_only: bool = False
    cancelled: threading.Event = field(default_factory=threading.Event)
    valid: object = field(default=lambda: True, repr=False)
    started: float = field(default_factory=time.monotonic)
    requests: list = field(default_factory=list)
    stage: str = 'generation'
    local_model: str = ''

    def check(self):
        if self.cancelled.is_set() or not self.valid():
            raise Stopped('Run cancelled or its person/workspace/conversation changed.')
        if time.monotonic() - self.started > self.seconds:
            raise Stopped('Run time budget exhausted. Retry deliberately with a smaller task.')

    @property
    def remaining_seconds(self):
        self.check()
        return max(.1, self.seconds - (time.monotonic() - self.started))


def current():
    return _CURRENT.get()


@contextmanager
def use(budget):
    token = _CURRENT.set(budget)
    try:
        budget.check()
        yield budget
    finally:
        _CURRENT.reset(token)


def attempt(provider, messages, max_tokens, *, transport=False):
    """Transport adapters, including test adapters, count before sending a request."""
    budget = current()
    if budget is None:
        return None
    budget.check()
    estimate = len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) + 64
    if estimate + max_tokens > budget.context:
        raise Stopped('Input and reserved output exceed the installed context budget. Split this task.')
    if len(budget.requests) >= budget.ceiling:
        raise Stopped('Attempted model-request limit reached. The run is incomplete; retry deliberately.')
    row = dict(provider=provider, stage=budget.stage, input_upper_bound=estimate, output_reserved=max_tokens,
               transport=transport, success=False, received_text=False, input_tokens=None, output_tokens=None, first_token_seconds=None,
               seconds=None)
    budget.requests.append(row)
    return row


@contextmanager
def open_request(open_fn, req, timeout):
    """Wrap generation only; availability probes do not consume generation attempts."""
    from .activity import exclusive
    budget = current()
    with exclusive(budget.check if budget else lambda: None):
        row, started = None, time.monotonic()
        if budget:
            body = json.loads(req.data or b'{}')
            host = urlsplit(req.full_url).hostname
            if budget.local_only and host not in ('localhost', '127.0.0.1', '::1'):
                raise Stopped('This run permits only an installed local model.')
            if host in ('localhost', '127.0.0.1', '::1') and body.get('model'):
                if budget.local_model and body['model'] != budget.local_model:
                    raise Stopped('Research run refused an unrequested local-model switch.')
                budget.local_model = body['model']
            options = body.get('options') or {}
            output = options.get('num_predict', body.get('max_completion_tokens',body.get('max_tokens',
                     (body.get('generationConfig') or {}).get('maxOutputTokens', 512))))
            # Include the actual injected system instructions and selected history/evidence.
            content = {k: v for k, v in body.items() if k not in ('options', 'model', 'stream', 'keep_alive')}
            row = attempt(getattr(req,'cursiv_provider',None) or body.get('model') or host, content, int(output), transport=True)
            row['requested_model']=getattr(req,'cursiv_model',None) or body.get('model')
            timeout = min(timeout, budget.remaining_seconds)
        try:
            with open_fn(req, timeout=timeout) as response:
                if budget is None:
                    yield response
                else:
                    yield _Response(response, budget, row, started)
        finally:
            if row is not None:
                row['seconds'] = time.monotonic() - started


class _Response:
    def __init__(self, raw, budget, row, started):
        self.raw, self.budget, self.row, self.started = raw, budget, row, started

    def __getattr__(self, key):
        return getattr(self.raw, key)

    def observe(self, value):
        self.budget.check()
        if value.strip() == b'data: [DONE]':
            self.row['success'] = self.row['received_text']
            return value
        try:
            data = json.loads(value.decode().removeprefix('data: ').strip())
        except (ValueError, UnicodeError):
            return value
        usage = data.get('usage') or data.get('usageMetadata') or (data.get('x_groq') or {}).get('usage') or (data.get('message') or {}).get('usage') or {}
        self.row['input_tokens'] = data.get('prompt_eval_count', usage.get('input_tokens', usage.get('prompt_tokens', usage.get('promptTokenCount', self.row['input_tokens']))))
        self.row['output_tokens'] = data.get('eval_count', usage.get('output_tokens', usage.get('completion_tokens', usage.get('candidatesTokenCount', self.row['output_tokens']))))
        text = (data.get('response') or data.get('choices') or data.get('candidates') or data.get('content')
                or (data.get('message') or {}).get('content') or (data.get('delta') or {}).get('text'))
        if text:
            self.row['received_text'] = True
            if self.row['first_token_seconds'] is None:
                self.row['first_token_seconds'] = time.monotonic() - self.started
        if data.get('done') or data.get('usage') or data.get('usageMetadata') or data.get('type') == 'message_stop' \
                or (data.get('content') and isinstance(data['content'], list)) \
                or any(c.get('finish_reason') for c in data.get('choices', [])):
            self.row['success'] = self.row['received_text']
        return value

    def __iter__(self):
        for value in self.raw:
            yield self.observe(value)

    def read(self, *args):
        self.budget.check()
        return self.observe(self.raw.read(*args))

    def readline(self,*args):
        self.budget.check()
        return self.observe(self.raw.readline(*args))

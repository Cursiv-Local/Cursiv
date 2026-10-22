"""One bounded, loopback-only classification attempt; never executes an action."""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request

OPERATIONS = frozenset(('SAVE_MEMORY', 'RECALL_MEMORY', 'UPDATE_MEMORY', 'FORGET_MEMORY',
                        'LIST_MEMORIES', 'DISABLE_AUTO_MEMORY', 'ENABLE_AUTO_MEMORY', 'CLARIFY', 'NONE'))
_loaded = ('', 0.0)
_gate = threading.BoundedSemaphore(1)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _open_local(request, *, timeout):
    # A loopback request must not inherit a remote proxy or follow a redirect
    # carrying conversation text outside this computer.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    return opener.open(request, timeout=timeout)


def classify(text: str, context: list[str], *, budget: float = 2.0) -> dict | None:
    if not _gate.acquire(blocking=False):
        return None
    result = []
    def work():
        try:
            result.append(_classify(text, context, budget=budget))
        except Exception:
            result.append(None)
        finally:
            _gate.release()
    worker = threading.Thread(target=work, daemon=True, name='cursiv-local-intent')
    worker.start()
    worker.join(min(max(budget, 0.05), 2.0))
    return result[0] if result else None


def _classify(text: str, context: list[str], *, budget: float = 2.0) -> dict | None:
    """Return only a validated operation and user-text span. No generated facts."""
    global _loaded
    deadline = time.monotonic() + min(max(budget, 0.05), 2.0)
    endpoint = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
    if '://' not in endpoint:
        endpoint = 'http://' + endpoint
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password:
        return None
    # No engine start, model download, cloud fallback, or queue/idle wait.
    try:
        model, expires = _loaded
        if not model or time.monotonic() >= expires:
            with _open_local(endpoint.rstrip('/') + '/api/ps', timeout=min(0.25, budget)) as response:
                models = json.loads(response.read(16384)).get('models', [])
            if not models:
                return None
            model = models[0].get('name') or models[0].get('model')
            if not isinstance(model, str) or not model:
                return None
            _loaded = model, time.monotonic() + 30
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        messages = context[-4:] + [text]
        schema = {'type': 'object', 'properties': {
            'operation': {'type': 'string', 'enum': sorted(OPERATIONS)},
            'message': {'type': 'integer'}, 'start': {'type': 'integer'}, 'end': {'type': 'integer'}},
            'required': ['operation', 'message', 'start', 'end'], 'additionalProperties': False}
        system = ('Classify the CURRENT user memory request, not hypothetical or quoted commands. '
                  'Do not invent content. Select an exact content/query span from one USER message by its '
                  'zero-based message/start/end indices. Use CLARIFY when the referent is ambiguous, NONE for discussion. '
                  'Output exactly the schema. No tool call, filename, permission, execution or save claim is allowed.')
        payload = {'model': model, 'stream': False, 'think': False, 'format': schema,
                   'messages': [{'role': 'system', 'content': system},
                                {'role': 'user', 'content': json.dumps(list(enumerate(messages)), ensure_ascii=False)}],
                   'options': {'temperature': 0, 'num_predict': 100, 'num_ctx': 2048}}
        request = urllib.request.Request(endpoint.rstrip('/') + '/api/chat', data=json.dumps(payload).encode(),
                                         headers={'Content-Type': 'application/json'})
        with _open_local(request, timeout=remaining) as response:
            result = json.loads(response.read(16384))
        if time.monotonic() > deadline:
            return None
        proposal = json.loads(result['message']['content'])
        if not isinstance(proposal, dict) or set(proposal) != {'operation', 'message', 'start', 'end'}:
            return None
        op = proposal['operation']
        if op not in OPERATIONS or any(type(proposal[k]) is not int for k in ('message', 'start', 'end')):
            return None
        if op in ('NONE', 'CLARIFY', 'LIST_MEMORIES', 'DISABLE_AUTO_MEMORY', 'ENABLE_AUTO_MEMORY'):
            return dict(operation=op)
        i, a, b = (proposal[k] for k in ('message', 'start', 'end'))
        if not (0 <= i < len(messages) and 0 <= a < b <= len(messages[i])):
            return None
        return dict(operation=op, content=messages[i][a:b], source=messages[i])
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return None

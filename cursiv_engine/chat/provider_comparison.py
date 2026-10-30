"""Read-only comparison preparation API. No scores, tool dispatch or automatic resends.

The desktop side-by-side presentation is intentionally separate. This interface
freezes identical logical text/context and permissions before any provider runs.
"""
import copy
import hashlib
import json
from dataclasses import dataclass
from .provider_types import Request, ProviderError, ErrorCode as E
from . import provider_manager as manager, provider_http as http


@dataclass(frozen=True)
class Comparison:
    messages_json: str
    selections: tuple
    context_sha256: str
    cloud_consent: bool = False
    local_only: bool = False


def prepare(messages, selections, *, cloud_consent=False, local_only=False):
    if len(selections) < 2 or len(selections) > 8:
        raise ValueError('Choose two to eight models')
    for provider, model in selections:
        manager.model_id(model)
        _, local, _ = http.location(provider)
        if not local and (not cloud_consent or local_only):
            raise ProviderError(provider,E.PERMISSION)
    encoded = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(',',':'))
    return Comparison(encoded, tuple(selections), hashlib.sha256(encoded.encode('utf-8')).hexdigest(),cloud_consent,local_only)


def run(plan, *, cancel=None):
    """Sequential, cost-bounded to one POST per selected model. Failures stay failures."""
    from cursiv_engine.core import verify
    for provider,model in plan.selections:
        messages = json.loads(plan.messages_json)
        request = Request(provider,model,copy.deepcopy(messages),cancel=cancel,
                          research_authorized=plan.cloud_consent,local_only=plan.local_only)
        list(manager.infer(request))
        result = manager.outcome()
        warnings = []
        if not result.error:
            prompt = next((m['content'] for m in reversed(messages) if m.get('role') == 'user'), '')
            check = verify.run_pass(prompt,result.text,mode='off')
            warnings = [issue.code for issue in check.issues]
        yield {'prompt_and_context':messages,'context_sha256':plan.context_sha256,'tool_permissions':'none',
               'response':result.text,'provenance':result.metadata(),'verification_warnings':warnings}
        if cancel is not None and cancel.is_set():
            return

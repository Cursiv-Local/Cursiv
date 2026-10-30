"""Explicit Ollama management, separate from inference and local-only routing."""
from cursiv_engine.core import netgate
from . import provider_http as http, provider_adapters as adapters, provider_manager as manager
from .provider_types import ProviderError, ErrorCode as E


def pull(model, *, consent=False, cancel=None):
    if not consent:
        raise ProviderError('ollama',E.PERMISSION)
    manager.model_id(model)
    # A loopback pull causes Ollama to download from the internet; do not let
    # the loopback exemption bypass offline policy.
    if not netgate.allowed():
        raise ProviderError('ollama',E.OFFLINE)
    if cancel is not None and cancel.is_set():
        raise ProviderError('ollama',E.CANCELLED)
    done = False
    with http.open_response('ollama','/api/pull',payload={'model':model,'stream':True}) as response:
        for data in adapters._objects(response,'ollama',True):
            if cancel is not None and cancel.is_set():
                raise ProviderError('ollama',E.CANCELLED)
            if data.get('error'):
                raise ProviderError('ollama',E.MODEL)
            total, completed = data.get('total',0), data.get('completed',0)
            percent = min(100,max(0,int(completed*100/total))) if isinstance(total,int) and isinstance(completed,int) and total > 0 else 0
            status = str(data.get('status','Downloading'))[:160]
            done = status == 'success'
            yield percent, status
    if not done:
        raise ProviderError('ollama',E.MALFORMED)


def remove(model, *, confirmed=False):
    if not confirmed:
        raise ProviderError('ollama',E.PERMISSION)
    manager.model_id(model)
    # DELETE affects installed models only, and remains permitted offline.
    with http.open_response('ollama','/api/delete',payload={'model':model},method='DELETE') as response:
        response.read(16384)
    return True

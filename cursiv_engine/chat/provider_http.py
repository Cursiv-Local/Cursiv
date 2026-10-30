"""Small credential-safe HTTP boundary, retaining netgate's socket backstop."""
import ipaddress
import json
import socket
import time
from contextlib import contextmanager
import urllib.error
import urllib.parse
import urllib.request

from cursiv_engine.core import netgate
from .provider_registry import get
from .provider_types import ErrorCode as E, ProviderError


def validate_endpoint(provider, value):
    try:
        parsed = urllib.parse.urlsplit(value)
        host = parsed.hostname
        port = parsed.port
        if (not host or parsed.username is not None or parsed.password is not None or
                parsed.query or parsed.fragment or '\\' in value or any(c.isspace() for c in value) or
                '%' in parsed.netloc):
            raise ValueError()
        local = host.lower() in ('localhost', 'localhost.')
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if ':' in host or host in ('0.0.0.0',):
                raise
            address = None
        if address is not None:
            local = address.is_loopback
            if not local and (address.is_unspecified or address.is_multicast or address.is_link_local):
                raise ValueError()
        if parsed.scheme not in ('http', 'https') or (not local and parsed.scheme != 'https'):
            raise ValueError()
        if get(provider).local and not local:
            raise ValueError()  # Ollama/LM Studio cannot silently become cloud destinations
        if port is not None and not 1 <= port <= 65535:
            raise ValueError()
        path = parsed.path.rstrip('/')
        if any(part in ('.', '..') for part in path.split('/')):
            raise ValueError()
        authority = parsed.netloc
        if host.lower() in ('localhost', 'localhost.'):
            authority = '127.0.0.1' + (f':{port}' if port else '')
        return urllib.parse.urlunsplit((parsed.scheme, authority, path, '', '')), local
    except (ValueError, TypeError):
        raise ProviderError(provider, E.ENDPOINT) from None


def location(provider):
    from . import provider_settings as settings
    spec = get(provider)
    config = settings.endpoint(provider) if provider in ('ollama', 'lmstudio', 'custom') else {}
    url, local = validate_endpoint(provider, config.get('url') or spec.base_url)
    return url, local, max(2, min(float(config.get('timeout', 60)), 300))


def preflight(provider, *, credential=None, local_only=False):
    url, local, timeout = location(provider)
    if not local and not netgate.allowed():
        raise ProviderError(provider, E.OFFLINE)
    if not local and local_only:
        raise ProviderError(provider, E.PERMISSION)
    spec = get(provider)
    if spec.credential and provider not in ('custom','lmstudio') and not credential:
        raise ProviderError(provider, E.MISSING_KEY)
    return url, local, timeout


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _status_error(provider, error):
    status = error.code
    category = {301:E.ENDPOINT,302:E.ENDPOINT,303:E.ENDPOINT,307:E.ENDPOINT,308:E.ENDPOINT,
                400:E.CAPABILITY,401:E.INVALID_KEY,402:E.QUOTA,403:E.PERMISSION,404:E.MODEL,405:E.CAPABILITY,
                408:E.TIMEOUT,422:E.CAPABILITY,504:E.TIMEOUT,
                429:E.RATE}.get(status, E.UNAVAILABLE if status >= 500 else E.MALFORMED)
    # Parse only a bounded structured code. Never echo upstream body/message/URL.
    if status in (400,401,403,429):
        try:
            body = json.loads(error.read(16384))
            detail = body.get('error', {})
            code = str(detail.get('code', ''))
            reasons = {d.get('reason') for d in detail.get('details', []) if isinstance(d,dict)}
            if code in ('invalid_api_key','authentication_error') or reasons & {'API_KEY_INVALID','API_KEY_EXPIRED'}:
                category = E.INVALID_KEY
            if code in ('insufficient_quota', 'quota_exceeded', 'credit_limit_exceeded'):
                category = E.QUOTA
            if code in ('model_not_found','model_decommissioned'):
                category = E.MODEL
        except Exception:
            pass
    try:
        retry_after = max(0, min(int(error.headers.get('Retry-After', '0')), 3600)) or None
    except (TypeError, ValueError):
        retry_after = None
    return ProviderError(provider, category, retry_after=retry_after)


@contextmanager
def open_response(provider, path, *, payload=None, credential='', method=None, expected_base=None):
    base, local, timeout = preflight(provider, credential=credential)
    if expected_base is not None and base != expected_base:
        raise ProviderError(provider,E.PERMISSION)
    if provider=='custom' and credential and expected_base is not None:
        from . import provider_settings
        if credential != provider_settings.key(provider):
            raise ProviderError(provider,E.PERMISSION)
    if not path.startswith('/') or path.startswith('//') or '\\' in path:
        raise ProviderError(provider, E.ENDPOINT)
    spec = get(provider)
    headers = {'User-Agent':'Cursiv-Desktop', 'Accept':'application/json', 'Content-Type':'application/json'}
    if credential:
        if spec.protocol == 'gemini':
            headers['x-goog-api-key'] = credential
        elif spec.protocol == 'claude':
            headers['x-api-key'] = credential
        else:
            headers['Authorization'] = 'Bearer ' + credential
    if spec.protocol == 'claude':
        headers['anthropic-version'] = '2023-06-01'
    request = urllib.request.Request(base + path, data=json.dumps(payload).encode('utf-8') if payload is not None else None,
                                     headers=headers, method=method)
    # Disable inherited proxies: a loopback endpoint must never send credentials
    # through a configured remote HTTP proxy. Redirects are rejected for ALL APIs.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        if not local:
            netgate.require()
        generation=payload is not None and path not in ('/api/pull','/api/delete','/api/show')
        if generation:
            from .request_budget import open_request
            request.cursiv_provider,request.cursiv_model=provider,payload.get('model','')
            with open_request(opener.open,request,timeout=timeout) as response:
                yield response
        else:
            with opener.open(request, timeout=timeout) as response:
                yield response
    except urllib.error.HTTPError as error:
        raise _status_error(provider, error) from None
    except (TimeoutError, socket.timeout):
        raise ProviderError(provider, E.TIMEOUT) from None
    except urllib.error.URLError as exc:
        reason = exc.reason
        code = E.TIMEOUT if isinstance(reason, (TimeoutError, socket.timeout)) else E.UNAVAILABLE if local else E.NETWORK
        raise ProviderError(provider, code) from None
    except OSError:
        raise ProviderError(provider, E.UNAVAILABLE if local else E.NETWORK) from None


def read_json(provider, path, *, credential='', payload=None, method=None, expected_base=None):
    # Discovery GETs alone may retry once. Inference and modifying requests never
    # automatically retry: a timeout cannot prove the server did nothing.
    for attempt in range(2 if payload is None and method in (None,'GET') else 1):
        try:
            with open_response(provider, path, credential=credential, payload=payload, method=method,expected_base=expected_base) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
            break
        except ProviderError as exc:
            if (attempt or payload is not None or method not in (None,'GET') or
                    exc.code not in (E.RATE,E.TIMEOUT,E.NETWORK,E.UNAVAILABLE) or (exc.retry_after or 0) > 1):
                raise
            time.sleep(max(.2,exc.retry_after or 0))
        except (TimeoutError,socket.timeout):
            raise ProviderError(provider,E.TIMEOUT) from None
        except OSError:
            raise ProviderError(provider,E.NETWORK) from None
    try:
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError):
        raise ProviderError(provider, E.MALFORMED) from None

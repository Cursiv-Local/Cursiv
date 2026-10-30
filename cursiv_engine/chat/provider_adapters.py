"""Provider-specific stream schemas; returned tool calls are data, never execution."""
import json
import base64
import re
import hashlib
from functools import wraps
import socket
import time
import urllib.parse

from .provider_registry import get, Model
from .provider_types import ErrorCode as E, ProviderError
from . import provider_http as http


def discover(provider, credential=''):
    spec = get(provider)
    path = '/api/tags' if spec.protocol == 'ollama' else '/models'
    values, pages = [], 0
    while path:
        data = http.read_json(provider, path, credential=credential)
        items = data.get('models' if spec.protocol in ('ollama', 'gemini') else 'data')
        if not isinstance(items, list):
            raise ProviderError(provider, E.MALFORMED)
        for item in items:
            if not isinstance(item, dict):
                raise ProviderError(provider, E.MALFORMED)
            model_id = item.get('model') or item.get('id') or item.get('name')
            if not isinstance(model_id, str) or not model_id:
                continue
            if spec.protocol == 'gemini':
                if 'generateContent' not in item.get('supportedGenerationMethods', []):
                    continue
                model_id = model_id.removeprefix('models/')
            details = item.get('details', {}) if isinstance(item.get('details'), dict) else {}
            # Only copy known metadata fields; upstream arbitrary payloads do not
            # belong in diagnostics or persistent caches.
            context = item.get('inputTokenLimit') or item.get('context_length')
            values.append(Model(model_id, provider, 'live', True,
                name=str(item.get('displayName') or item.get('display_name') or model_id),
                size=item.get('size') if isinstance(item.get('size'), int) else None,
                context=context if isinstance(context, int) else None,
                quantization=str(details.get('quantization_level') or ''),
                details={k:details[k] for k in ('parameter_size', 'family') if k in details}))
        pages += 1
        # Native pagination; bounded to avoid untrusted unending discovery.
        if pages >= 20:
            break
        if spec.protocol == 'gemini' and data.get('nextPageToken'):
            path = '/models?pageToken=' + urllib.parse.quote(str(data['nextPageToken']), safe='')
        elif spec.protocol == 'claude' and data.get('has_more') and data.get('last_id'):
            path = '/models?after_id=' + urllib.parse.quote(str(data['last_id']), safe='')
        else:
            path = ''
    return values


def _messages(messages):
    normalized=[]
    for message in messages:
        role,content=message.get('role'),message.get('content')
        if role not in ('system','user','assistant'):
            raise ValueError()
        if isinstance(content,str):
            normalized.append(dict(role=role,content=content)); continue
        if not isinstance(content,list) or role != 'user':
            raise ValueError()
        parts=[]
        for part in content:
            if part.get('type')=='text' and isinstance(part.get('text'),str):
                parts.append(dict(type='text',text=part['text']))
            elif part.get('type')=='image_url':
                url=part.get('image_url',{}).get('url','')
                match=re.fullmatch(r'data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)',url)
                if not match or len(url)>24*1024*1024:
                    raise ValueError()
                base64.b64decode(match[2],validate=True)
                parts.append(dict(type='image_url',image_url={'url':url}))
            else:
                raise ValueError()
        normalized.append(dict(role=role,content=parts))
    return normalized


def _native_parts(content,protocol):
    if isinstance(content,str):
        return content
    parts=[]
    for item in content:
        if item['type']=='text':
            parts.append({'text':item['text']} if protocol=='gemini' else item)
        else:
            mime,data=item['image_url']['url'][5:].split(';base64,',1)
            parts.append({'inlineData':{'mimeType':mime,'data':data}} if protocol=='gemini' else
                         {'type':'image','source':{'type':'base64','media_type':mime,'data':data}})
    return parts


def build(request):
    spec = get(request.provider)
    if spec.protocol not in ('ollama','openai','gemini','claude'):
        raise ProviderError(request.provider,E.CAPABILITY)
    if request.capability == 'image_generation':
        if request.provider not in ('openai','custom'):
            raise ProviderError(request.provider,E.CAPABILITY)
        prompt=next((m.get('content','') for m in reversed(request.messages) if m.get('role')=='user'),'')
        if not isinstance(prompt,str):
            raise ProviderError(request.provider,E.CAPABILITY)
        payload=dict(model=request.model,prompt=prompt,n=1,size='1024x1024')
        if request.model.startswith('dall-e-'):
            payload['response_format']='b64_json'
        else:
            payload['output_format']='png'
        return '/images/generations',payload
    try:
        messages = _messages(request.messages)
    except (ValueError, KeyError, TypeError):
        raise ProviderError(request.provider, E.CAPABILITY) from None
    system = '\n\n'.join(m['content'] for m in messages if m['role'] == 'system')
    chat = [m for m in messages if m['role'] != 'system']
    if spec.protocol == 'ollama':
        local_messages=[]
        for message in messages:
            if isinstance(message['content'],str):
                local_messages.append(message)
            else:
                local_messages.append(dict(role=message['role'],content='\n'.join(p['text'] for p in message['content'] if p['type']=='text'),
                    images=[p['image_url']['url'].split(';base64,',1)[1] for p in message['content'] if p['type']=='image_url']))
        from cursiv_engine.core import speed
        return '/api/chat', dict(model=request.model, messages=local_messages, stream=True,
                                 options={'num_predict':request.max_tokens,'num_ctx':speed.num_ctx()},
                                 keep_alive=speed.keep_alive(),**speed.no_thinking(request.model))
    if spec.protocol == 'gemini':
        model = urllib.parse.quote(request.model.removeprefix('models/'), safe='-_.')
        return f'/models/{model}:streamGenerateContent?alt=sse', {
            'systemInstruction': {'parts':[{'text':system}]},
            'contents':[{'role':'model' if m['role'] == 'assistant' else 'user',
                         'parts':[{'text':m['content']}] if isinstance(m['content'],str) else _native_parts(m['content'],'gemini')} for m in chat],
            'generationConfig':{'maxOutputTokens':request.max_tokens}}
    if spec.protocol == 'claude':
        chat=[dict(role=m['role'],content=_native_parts(m['content'],'claude')) for m in chat]
        return '/messages', dict(model=request.model, system=system, messages=chat,
                                 max_tokens=request.max_tokens, stream=True)
    payload = dict(model=request.model, messages=messages, stream=True)
    # OpenAI's newer models use max_completion_tokens; compatible servers may
    # implement the older max_tokens field instead.
    payload['max_completion_tokens' if request.provider == 'openai' else 'max_tokens'] = request.max_tokens
    if request.provider == 'openrouter':
        payload['provider'] = {'allow_fallbacks':False}
    if request.provider == 'openai':
        payload['stream_options']={'include_usage':True}
    return '/chat/completions', payload


def _objects(response, provider, ndjson=False):
    lines, total = [], 0
    while True:
        raw = response.readline(2 * 1024 * 1024 + 1)
        if not raw:
            break
        total += len(raw)
        if len(raw) > 2 * 1024 * 1024 or total > 32 * 1024 * 1024:
            raise ProviderError(provider, E.MALFORMED)
        try:
            line = raw.decode('utf-8').strip('\r\n')
            if ndjson:
                if line:
                    yield json.loads(line)
            elif line.startswith('data:'):
                lines.append(line[5:].lstrip())
            elif not line and lines:
                data = '\n'.join(lines)
                lines = []
                if data == '[DONE]':
                    return
                yield json.loads(data)
        except (UnicodeError, ValueError):
            raise ProviderError(provider, E.MALFORMED) from None
    if lines:
        try:
            data = '\n'.join(lines)
            if data != '[DONE]':
                yield json.loads(data)
        except ValueError:
            raise ProviderError(provider, E.MALFORMED) from None


def _owned_stream(function):
    @wraps(function)
    def generate(request,*args,**kwargs):
        from .activity import guard,_GUARD,check_guard
        parent=_GUARD.get()
        with guard(lambda:parent() and not (request.cancel is not None and request.cancel.is_set())):
            for text in function(request,*args,**kwargs):
                check_guard()
                yield text
    return generate


@_owned_stream
def stream(request, result, credential=''):
    start = time.monotonic()
    protocol = get(request.provider).protocol
    if request.cancel is not None and request.cancel.is_set():
        raise ProviderError(request.provider, E.CANCELLED)
    path, payload = build(request)
    calls = {}
    try:
        if request.capability == 'image_generation':
            data=http.read_json(request.provider,path,payload=payload,credential=credential,expected_base=request.endpoint_url)
            if request.cancel is not None and request.cancel.is_set():
                raise ProviderError(request.provider,E.CANCELLED)
            image=data.get('data',[{}])[0].get('b64_json','')
            if not isinstance(image,str) or len(image)>24*1024*1024:
                raise ProviderError(request.provider,E.MALFORMED)
            try:
                binary=base64.b64decode(image,validate=True)
            except ValueError:
                raise ProviderError(request.provider,E.MALFORMED) from None
            if not binary.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ProviderError(request.provider,E.MALFORMED)
            result.artifacts=[dict(mime='image/png',bytes=len(binary),sha256=hashlib.sha256(binary).hexdigest(),base64=image)]
            result.actual_model=data.get('model')
            result.usage=data.get('usage') or {}
            result.finish_reason='stop'
            result.responding_provider=request.provider
            result.text='Image generated. '+result.label()
            yield result.text
            return
        with http.open_response(request.provider, path, credential=credential, payload=payload,expected_base=request.endpoint_url) as response:
            result.streaming = True
            result.streamed = True
            for data in _objects(response, request.provider, protocol == 'ollama'):
                if request.cancel is not None and request.cancel.is_set():
                    raise ProviderError(request.provider, E.CANCELLED)
                if not isinstance(data, dict):
                    raise ProviderError(request.provider, E.MALFORMED)
                if data.get('error') or data.get('type') == 'error':
                    error = data.get('error', {})
                    code = error.get('type', '') if isinstance(error, dict) else ''
                    category = {'authentication_error':E.INVALID_KEY, 'permission_error':E.PERMISSION,
                                'rate_limit_error':E.RATE, 'overloaded_error':E.UNAVAILABLE}.get(code, E.UNAVAILABLE)
                    raise ProviderError(request.provider, category)
                text = ''
                if protocol == 'ollama':
                    result.actual_model = data.get('model') or result.actual_model
                    message = data.get('message') or {}
                    text = message.get('content') or ''
                    result.tool_calls.extend(message.get('tool_calls') or [])
                    if data.get('done'):
                        result.finish_reason = data.get('done_reason') or 'stop'
                        result.usage = {k:data[k] for k in ('prompt_eval_count', 'eval_count') if k in data}
                elif protocol == 'gemini':
                    result.actual_model = data.get('modelVersion') or result.actual_model
                    for candidate in data.get('candidates', []):
                        for part in candidate.get('content', {}).get('parts', []):
                            if part.get('functionCall'):
                                result.tool_calls.append(part['functionCall'])
                            text += part.get('text', '') if not part.get('thought') else ''
                        result.finish_reason = candidate.get('finishReason') or result.finish_reason
                    result.usage.update(data.get('usageMetadata') or {})
                    if data.get('promptFeedback', {}).get('blockReason'):
                        raise ProviderError(request.provider, E.PERMISSION)
                elif protocol == 'claude':
                    kind = data.get('type')
                    if kind == 'message_start':
                        result.actual_model = data.get('message', {}).get('model')
                        result.usage.update(data.get('message', {}).get('usage') or {})
                    elif kind == 'content_block_start':
                        block = data.get('content_block', {})
                        if block.get('type') == 'tool_use':
                            calls[data.get('index', 0)] = dict(block, arguments='')
                    elif kind == 'content_block_delta':
                        delta = data.get('delta', {})
                        text = delta.get('text', '')
                        if delta.get('partial_json') is not None:
                            index = data.get('index', 0)
                            calls.setdefault(index, {'arguments':''})['arguments'] += delta['partial_json']
                    elif kind == 'message_delta':
                        result.finish_reason = data.get('delta', {}).get('stop_reason')
                        result.usage.update(data.get('usage') or {})
                else:
                    result.actual_model = data.get('model') or result.actual_model
                    result.usage.update(data.get('usage') or {})
                    if request.provider=='groq':
                        result.usage.update((data.get('x_groq') or {}).get('usage') or {})
                    for choice in data.get('choices', []):
                        delta = choice.get('delta') or {}
                        text += delta.get('content') or ''
                        result.finish_reason = choice.get('finish_reason') or result.finish_reason
                        for call in delta.get('tool_calls') or []:
                            saved = calls.setdefault(call.get('index', 0), {'id':'', 'type':'function', 'function':{'name':'', 'arguments':''}})
                            saved['id'] = call.get('id') or saved['id']
                            for field in ('name', 'arguments'):
                                saved['function'][field] += call.get('function', {}).get(field) or ''
                if text:
                    if not isinstance(text, str):
                        raise ProviderError(request.provider, E.MALFORMED)
                    result.text += text
                    yield text
            result.tool_calls.extend(calls.values())
            if not result.finish_reason or not (result.text or result.tool_calls):
                raise ProviderError(request.provider, E.MALFORMED)
            # A text-only path records unsolicited calls but does not invent
            # results. Native Cursiv tools remain available before generation.
            if result.tool_calls:
                raise ProviderError(request.provider, E.CAPABILITY)
            result.responding_provider = request.provider
    except (TimeoutError, socket.timeout):
        raise ProviderError(request.provider, E.TIMEOUT) from None
    except OSError:
        raise ProviderError(request.provider, E.NETWORK) from None
    except (KeyError, TypeError, AttributeError):
        raise ProviderError(request.provider, E.MALFORMED) from None
    finally:
        result.streaming = False
        result.latency = round(time.monotonic() - start, 4)

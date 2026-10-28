"""Chat cloud providers.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _text_messages, _post_json, _slim, _call_gemini_direct, check_free_key, _call_groq_direct, _cloud_settings, _save_cloud_settings, cloud_enabled, set_cloud_enabled, _call_cursiv_cloud, free_key_command, _local_llm, _free_key_llm, _quick_llm, _memory_llm, _local_model_ready, _call_xai_stream, _generate_with_claude, _call_claude_direct, _call_openai_direct.
"""
from __future__ import annotations
from . import request_budget

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _text_messages(runtime: ChatRuntime, messages: list[dict]) -> list[dict]:
    """Plain-text copy of a message list (image parts dropped)."""
    out = []
    for m in messages:
        c = m.get("content")
        if not isinstance(c, str):
            c = next((p.get("text", "") for p in (c or []) if isinstance(p, dict) and p.get("type") == "text"), "")
        out.append({"role": m.get("role", "user"), "content": c})
    return out

def _post_json(runtime: ChatRuntime, url: str, payload: dict, headers: dict, timeout: float) -> dict:
    runtime.netgate.require("Cloud AI")
    # A real User-Agent: Groq's API sits behind Cloudflare, which blocks Python's
    # default "Python-urllib" agent outright (HTTP 403, error code 1010).
    req = runtime.urllib.request.Request(url, data=runtime.json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "Cursiv-Desktop/3.14", **headers})
    with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=timeout) as resp:
        return runtime.json.loads(resp.read().decode("utf-8"))

def _slim(runtime: ChatRuntime, messages: list[dict], budget: int) -> list[dict]:
    """Compact persona + newest turns that fit `budget` characters (core/speed.py)."""
    from cursiv_engine.core import speed
    from cursiv_engine.core.style import PROMPT_HEADING
    from cursiv_engine.core.philosophy_policy import INSTRUCTIONS
    from .response_style import GUIDANCE_HEADING
    text = runtime._text_messages(messages)
    styles = [m for m in text if m.get('role') == 'system' and m.get('content', '').startswith(PROMPT_HEADING)]
    protected = [dict(role='system', content=INSTRUCTIONS)]
    # Fixed application rules derived from tone/format flags; no copied user history.
    response_rules = [m for m in text if m.get('role') == 'system' and
                      m.get('content', '').startswith(GUIDANCE_HEADING)]
    if response_rules:
        protected.append(dict(role='system', content=response_rules[-1]['content'][:min(2000, budget//5)]))
    if styles:
        # Current tone/guidance precedes older standing rules. Keep complete
        # lines within a bounded share; preferences cannot exhaust state/history.
        lines, used = [], 0
        for line in styles[-1]['content'].splitlines():
            if used + len(line) + 1 > min(1600, budget // 5):
                break
            lines.append(line)
            used += len(line) + 1
        if len(lines) > 1:
            protected.append(dict(role='system', content='\n'.join(lines)))
    source = [m for m in text if not (m.get('role') == 'system' and
              (m.get('content') == INSTRUCTIONS or m.get('content', '').startswith(PROMPT_HEADING)
               or m.get('content', '').startswith(GUIDANCE_HEADING)))]
    reserve = sum(len(m['content']) for m in protected)
    result = speed.slim_messages(source, max(0, budget - reserve),
                                 runtime._FULL_PERSONA, speed.compact_persona(runtime.SYSTEM_PROMPT_FILE))
    at = 1 if result and result[0].get('role') == 'system' else 0
    result[at:at] = protected
    return result

def _call_gemini_direct(runtime: ChatRuntime, messages: list[dict], key: str, max_tokens: int) -> Generator[str, None, None]:
    msgs = runtime._slim(messages, runtime.GEMINI_BUDGET)
    system = "\n\n".join(m["content"] for m in msgs if m["role"] == "system")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in msgs if m["role"] in ("user", "assistant") and m["content"]]
    payload = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    last_err = ""
    import time as _t
    now = _t.time()
    order = [m for m in runtime.GEMINI_MODELS if runtime._GEMINI_DOWN.get(m, 0) < now] or list(runtime.GEMINI_MODELS[-1:])
    for model in order:
        url = runtime.GEMINI_URL.format(model=model)
        body = payload
        if "lite" in model:   # the fast fallback: skip "thinking" (4 s instead of 30 s)
            body = {**payload, "generationConfig": {**payload["generationConfig"], "thinkingConfig": {"thinkingBudget": 0}}}
        for use_query in (False, True):    # header first; some newer keys only work as ?key=
            try:
                if use_query:
                    data = runtime._post_json(f"{url}?key={runtime.urllib.parse.quote(key)}", body, {}, runtime.GEMINI_TIMEOUT)
                else:
                    data = runtime._post_json(url, body, {"x-goog-api-key": key}, runtime.GEMINI_TIMEOUT)
                cand = (data.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                if text.strip():
                    yield text
                    return
                last_err = f"empty reply ({cand.get('finishReason', 'no text')})"
                break
            except runtime.urllib.error.HTTPError as e:
                last_err = f"{e.code}: {e.read().decode(errors='ignore')[:200]}"
                if e.code in (401, 403) and not use_query:
                    continue        # try the same model with ?key=
                if e.code in (404, 429, 500, 503):
                    runtime._GEMINI_DOWN[model] = _t.time() + (3600 if e.code == 404 else 600)
                break               # 404/429/5xx: next model
            except Exception as e:
                last_err = str(e)
                if "timed out" in last_err.lower():
                    runtime._GEMINI_DOWN[model] = _t.time() + 600     # overloaded: skip it for 10 minutes
                break
        if last_err[:3] in ("400", "401", "403"):
            break                   # bad key or request -- another model won't help
    yield f"\n[Gemini error {last_err}]"

def check_free_key(runtime: ChatRuntime, field: str, key: str) -> tuple[bool, str]:
    """Is this Gemini/Groq key valid? Lists the provider's models -- costs no
    tokens, and doesn't depend on a model's reply (newer Gemini models can
    spend a tiny test budget on thinking and return nothing)."""
    def get(url: str, headers: dict) -> None:
        req = runtime.urllib.request.Request(url, headers={"User-Agent": "Cursiv-Desktop/3.14", **headers})
        with runtime.urllib.request.urlopen(req, timeout=20) as r:
            r.read(200)
    try:
        if field == "gemini_key":
            base = "https://generativelanguage.googleapis.com/v1beta/models"
            try:
                get(base, {"x-goog-api-key": key})
            except runtime.urllib.error.HTTPError as e:
                if e.code not in (400, 401, 403):
                    raise
                get(f"{base}?key={runtime.urllib.parse.quote(key)}", {})
        else:
            get("https://api.groq.com/openai/v1/models", {"Authorization": f"Bearer {key}"})
        # The key is valid -- now prove chat works (a valid key can still fail in chat).
        import time as _t
        t0 = _t.time()
        msgs = [{"role": "system", "content": "Reply in five words or fewer."},
                {"role": "user", "content": "Say hello."}]
        fn = runtime._call_gemini_direct if field == "gemini_key" else runtime._call_groq_direct
        out = "".join(fn(msgs, key, 64)).strip()
        if not out or out.startswith("["):
            return False, ("Key is valid, but chat failed: " + out.strip("[]"))[:220]
        return True, f"Working — answered in {_t.time() - t0:.1f}s."
    except runtime.urllib.error.HTTPError as e:
        try:
            detail = runtime.json.loads(e.read().decode("utf-8", "ignore")).get("error", {})
            detail = detail.get("message", "") if isinstance(detail, dict) else str(detail)
        except Exception:
            detail = ""
        return False, f"{e.code}: {detail or 'rejected'}"[:220]
    except Exception as e:
        return False, f"couldn't reach the provider: {e}"[:220]

def _call_groq_direct(runtime: ChatRuntime, messages: list[dict], key: str, max_tokens: int) -> Generator[str, None, None]:
    """Groq: very fast. Free-tier limits are per model, so on "too large" (413) or
    "rate limited" (429) try a smaller prompt, then the next model."""
    last = ""
    for model in runtime.GROQ_MODELS:
        for budget, cap in ((runtime.GROQ_BUDGET, max_tokens), (runtime.GROQ_BUDGET // 2, min(max_tokens, 2048))):
            try:
                data = runtime._post_json(runtime.GROQ_URL, {"model": model, "messages": runtime._slim(messages, budget),
                                             "max_tokens": cap},
                                  {"Authorization": f"Bearer {key}"}, 60)
                text = data["choices"][0]["message"].get("content") or ""
                if text.strip():
                    yield text
                    return
                last = "empty reply"
                break
            except runtime.urllib.error.HTTPError as e:
                last = f"{e.code}: {e.read().decode(errors='ignore')[:160]}"
                if e.code in (401, 403):
                    yield f"\n[Groq error {last}]"
                    return
                if e.code == 413:
                    continue        # same model, smaller request
                break               # 429/5xx/404: next model
            except Exception as e:
                last = str(e)
                break
    yield f"\n[Groq error {last}]"

def _cloud_settings(runtime: ChatRuntime) -> dict:
    try:
        data = runtime.json.loads(runtime._CLOUD_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    changed = False
    if "enabled" not in data:
        data["enabled"] = False      # off until the person ticks it in Setup / Settings or types 'cloud on'
        changed = True
    if not data.get("install_id"):
        import uuid as _uuid
        data["install_id"] = str(_uuid.uuid4())
        changed = True
    if changed:
        runtime._save_cloud_settings(data)
    return data

def _save_cloud_settings(runtime: ChatRuntime, data: dict) -> None:
    try:
        runtime._CLOUD_FILE.parent.mkdir(parents=True, exist_ok=True)
        runtime._CLOUD_FILE.write_text(runtime.json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass

def cloud_enabled(runtime: ChatRuntime) -> bool:
    return runtime.netgate.allowed() and bool(runtime._cloud_settings().get("enabled", False))

def set_cloud_enabled(runtime: ChatRuntime, on: bool) -> None:
    data = runtime._cloud_settings()
    data["enabled"] = bool(on)
    runtime._save_cloud_settings(data)

def _call_cursiv_cloud(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> Generator[str, None, None]:
    settings = runtime._cloud_settings()
    try:
        data = runtime._post_json(runtime.CURSIV_CLOUD_URL, {"messages": runtime._text_messages(messages), "max_tokens": max_tokens},
                          {"X-Cursiv-Install": settings["install_id"], "User-Agent": "Cursiv-Desktop"}, 90)
        text = data.get("reply", "")
        if not text.strip():
            yield "\n[Cursiv Cloud error: empty reply]"
            return
        if not settings.get("notice_shown"):
            settings["notice_shown"] = True
            runtime._save_cloud_settings(settings)
            yield ("*[No local model was ready, so this answer came from Cursiv Cloud (free, sent to "
                   "cursiv.us). Type 'cloud off' to keep everything on this computer.]*\n\n")
        yield text
    except runtime.urllib.error.HTTPError as e:
        try:
            detail = runtime.json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            detail = ""
        yield f"\n[Cursiv Cloud error {e.code}: {detail or 'unavailable'}]"
    except Exception as e:
        yield f"\n[Cursiv Cloud error: {e}]"

def free_key_command(runtime: ChatRuntime, text: str) -> str | None:
    """Shared by the chat window and the terminal: 'gemini <key>', 'groq <key>',
    'cloud on|off|status', 'free keys'. Returns the reply, or None if not one of these."""
    t = text.strip()
    cmd = t.lower()
    if cmd in ("free keys", "free key", "keys free"):
        return runtime.FREE_KEY_HELP
    # Prefixes are only hints: providers change key formats (Google issues both
    # "AIza..." and newer "AQ..." Gemini keys), so the live test call decides.
    for name, field, prefixes, fn in (("gemini", "gemini_key", ("AIza", "AQ"), runtime._call_gemini_direct),
                                      ("groq", "groq_key", ("gsk_",), runtime._call_groq_direct)):
        if cmd == name:
            return f"Usage: {name} <key>   ({'set' if runtime._saved_key(field) else 'no key set'})\n\n" + runtime.FREE_KEY_HELP
        if cmd.startswith(name + " "):
            key = t[len(name) + 1:].strip()
            if key.lower() in ("off", "remove", "clear"):
                runtime._store_key(field, "")
                return f"{name.title()} key removed."
            if len(key) < 20 or " " in key:
                return f"That doesn't look like a whole {name.title()} key -- copy the full key and try again.\n\n" + runtime.FREE_KEY_HELP
            ok, reply = runtime.check_free_key(field, key)
            if not ok:
                hint = "" if key.startswith(prefixes) else (
                    f"\n(Most {name.title()} keys start with {' or '.join(prefixes)} -- make sure you copied the API key itself.)")
                return (f"{name.title()} key NOT saved -- the test call failed: {reply.strip()}\n"
                        f"Check that you copied the whole key, then try again.{hint}")
            runtime._store_key(field, key)
            return f"{name.title()} key saved and working. Cursiv will use it when your other providers aren't available."
    if cmd in ("cloud", "cloud status"):
        if runtime.netgate.is_offline():
            return f"Cursiv Cloud isn't used while offline mode is on. {runtime.netgate.OFFLINE_MESSAGE}"
        on = runtime.cloud_enabled()
        return (f"Cursiv Cloud is {'ON' if on else 'OFF'}. "
                + ("It answers only when no local model is ready (Ollama not installed or no model yet), "
                   "through cursiv.us. Type 'cloud off' to keep everything on this computer."
                   if on else "Everything stays on this computer. Type 'cloud on' to allow it as a backup."))
    if cmd in ("cloud on", "cloud off"):
        runtime.set_cloud_enabled(cmd == "cloud on")
        return ("Cursiv Cloud ON -- used only when no local model is ready."
                if cmd == "cloud on" else "Cursiv Cloud OFF -- nothing is sent to the cloud unless you add your own keys.")
    return None

def _local_llm(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> str:
    """One call to the local model. "" on an error."""
    # The answer check and background jobs use the fast Standard model, even in Deep Think.
    out = "".join(c for c in runtime._call_ollama(messages, max_tokens=max_tokens, standard=True) if c != runtime.RATE_SENTINEL).strip()
    return "" if out.startswith(("[Ollama", "\n[Ollama")) else out

def _free_key_llm(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> str:
    """The user's own free Groq/Gemini key. Only for when no local model is ready."""
    if not runtime.netgate.allowed():
        return ""
    for field, fn in (("groq_key", runtime._call_groq_direct), ("gemini_key", runtime._call_gemini_direct)):
        key = runtime._saved_key(field)
        if key:
            out = "".join(fn(messages, key, max_tokens)).strip()
            if out and not out.startswith(("[Groq error", "[Gemini error")):
                return out
    return ""

def _quick_llm(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> str:
    """Small background jobs (memory learning, titles): the local model when one is
    ready, else the user's free Groq/Gemini key. A local model that fails does not
    fall back to the cloud. Never paid keys and never Cursiv Cloud. "" if none."""
    if runtime._ollama_running() and runtime._resolve_ollama_model():
        from cursiv_engine.core import speed as _speed
        if not _speed.wait_idle(300):      # never compete with a chat for the local model
            return ""
        return runtime._local_llm(messages, max_tokens)
    return runtime._free_key_llm(messages, max_tokens)

def _memory_llm(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> str:
    """Optional memory extraction stays local even when cloud keys are configured."""
    if runtime._ollama_running() and runtime._resolve_ollama_model():
        from cursiv_engine.core import speed
        if speed.wait_idle(30):
            return runtime._local_llm(messages, max_tokens)
    return ''

def _local_model_ready(runtime: ChatRuntime) -> bool:
    """Ollama is installed, running (started if needed) and has a chat model."""
    return runtime._ensure_ollama() and runtime._resolve_ollama_model() is not None

def _call_xai_stream(runtime: ChatRuntime, messages: list[dict], api_key: str, has_images: bool, max_tokens: int) -> Generator[str, None, None]:
    """Stream from xAI Grok. Handles text and vision."""
    model = runtime.XAI_MODEL_VIS if has_images else runtime.XAI_MODEL
    payload = runtime.json.dumps({
        "model":       model,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "stream":      True,
        "temperature": 0.7,
    }).encode()
    try:
        req = runtime.urllib.request.Request(
            runtime.XAI_URL,
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=90) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        chunk   = runtime.json.loads(line[6:])
                        delta   = chunk["choices"][0]["delta"]
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
    except runtime.urllib.error.HTTPError as e:
        if e.code in (401, 403):
            body = e.read().decode(errors="ignore")[:120]
            yield f"[xAI auth error {e.code} — check your key: {body}]"
        else:
            yield runtime.RATE_SENTINEL
    except Exception:
        yield runtime.RATE_SENTINEL

def _generate_with_claude(runtime: ChatRuntime, filepath: str, anthropic_key: str, context_messages: list[dict], grok_draft: str) -> str:
    """
    Use Claude claude-sonnet-4-6 to generate or rewrite a file with full
    conversation context. Falls back to empty string if the call fails.
    """
    ext  = runtime.Path(filepath).suffix.lower() if filepath else ""
    lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".sh": "Bash", ".bat": "Batch"}.get(ext, "code")

    ctx_turns = [m for m in context_messages if m.get("role") in ("user", "assistant")][-6:]
    ctx_text  = "\n".join(
        f"[{m['role'].upper()}]: {m['content'][:800]}"
        for m in ctx_turns
        if isinstance(m.get("content"), str)
    )

    system_msg = (
        f"You are an expert {lang} engineer. "
        "Write complete, production-ready code — no stubs, no TODOs, no placeholder comments. "
        "Return ONLY the raw file content, nothing else. No markdown fences, no explanation."
    )
    user_msg = (
        f"Conversation context:\n{ctx_text}\n\n"
        f"File to generate: {filepath}\n\n"
    )
    if grok_draft:
        user_msg += (
            f"Grok's draft (improve and complete this):\n"
            f"{grok_draft[:8000]}\n\n"
        )
    user_msg += (
        "Write the complete, final file content. "
        "Every function must be fully implemented. No ellipsis, no '# TODO'."
    )

    try:
        payload = runtime.json.dumps({
            "model":      runtime.ANTHROPIC_CODE_MODEL,
            "max_tokens": 8000,
            "system":     system_msg,
            "messages":   [{"role": "user", "content": user_msg}],
        }).encode()
        req = runtime.urllib.request.Request(
            runtime.ANTHROPIC_URL, data=payload,
            headers={
                "Content-Type":    "application/json",
                "x-api-key":       anthropic_key,
                "anthropic-version": runtime.ANTHROPIC_VERSION,
            },
        )
        with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=120) as resp:
            data = runtime.json.loads(resp.read().decode())
            return data["content"][0]["text"].strip()
    except Exception:
        return ""

def _call_claude_direct(runtime: ChatRuntime, messages: list[dict], anthropic_key: str, max_tokens: int = 4096) -> Generator[str, None, None]:
    """Route a chat message directly to Claude — no tool loop."""
    import time as _time
    sys_parts = [m["content"] for m in messages if m["role"] == "system"]
    chat_msgs  = [m for m in messages if m["role"] != "system"]
    # Keep last 12 turns to limit input token cost
    chat_msgs  = chat_msgs[-24:]
    payload = runtime.json.dumps({
        "model":      runtime.ANTHROPIC_CODE_MODEL,
        "max_tokens": max_tokens,
        "system":     "\n\n".join(sys_parts),
        "messages":   chat_msgs,
    }).encode()
    if runtime._rate_limiter:
        est = runtime._rate_limiter.estimate_tokens(payload.decode(errors="ignore"))
        runtime._rate_limiter.wait_if_needed(est)

    for attempt in range(3):
        try:
            req = runtime.urllib.request.Request(
                runtime.ANTHROPIC_URL, data=payload,
                headers={
                    "content-type":      "application/json",
                    "x-api-key":         anthropic_key,
                    "anthropic-version": runtime.ANTHROPIC_VERSION,
                },
            )
            with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=120) as resp:
                data = runtime.json.loads(resp.read().decode())
            if runtime._rate_limiter:
                usage  = data.get("usage", {})
                actual = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                if actual:
                    runtime._rate_limiter.record_actual(actual)
            content = (data.get("content") or [{}])[0].get("text", "") or ""
            for word in content.split(" "):
                yield word + " "
            return
        except runtime.urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            if e.code == 429 and attempt < 2:
                wait_s = 15 * (attempt + 1)
                yield f"\n*[Rate gate: pacing {wait_s}s — TPM window full]*\n"
                _time.sleep(wait_s)
                continue
            if e.code == 429:
                yield runtime.RATE_SENTINEL   # signal to chat() to try fallback provider
                return
            yield f"\n[Claude error {e.code}: {body[:200]}]"
            return
        except Exception as e:
            yield f"\n[Claude error: {e}]"
            return

def _call_openai_direct(runtime: ChatRuntime, messages: list[dict], openai_key: str, max_tokens: int | None = None) -> Generator[str, None, None]:
    """Route a chat message directly to GPT-4.1 — no tool loop."""
    payload = runtime.json.dumps({
        "model":    runtime.OPENAI_CODE_MODEL,
        "messages": messages,
        **({"max_tokens": max_tokens} if max_tokens is not None else {}),
    }).encode()
    try:
        req = runtime.urllib.request.Request(
            runtime.OPENAI_URL, data=payload,
            headers={
                "content-type":  "application/json",
                "Authorization": f"Bearer {openai_key}",
            },
        )
        with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=120) as resp:
            data = runtime.json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"] or ""
        for word in content.split(" "):
            yield word + " "
    except runtime.urllib.error.HTTPError as e:
        yield f"\n[OpenAI error {e.code}: {e.read().decode(errors='ignore')[:200]}]"
    except Exception as e:
        yield f"\n[OpenAI error: {e}]"

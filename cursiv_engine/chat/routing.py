"""Chat routing.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: cascade_stream, _classify_message, _is_online, _cloud_configured, _connectivity_probe, _local_stream, _fallback_chain, _router_llm, warm_up_local.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime
from .activity import serialized_work

def cascade_stream(runtime: ChatRuntime, messages: list[dict], keys: dict, max_tokens: int, local_fn: Callable[[list[dict]], Generator[str, None, None]] | None) -> tuple[Generator[str, None, None], list[str]]:
    """
    Stream a one-shot reply (Babel, grow, ...): the local model first when it has
    one, then every configured key -- Claude, xAI, OpenAI, Groq, Gemini -- then
    Cursiv Cloud (only when no local model is ready), moving on whenever one
    fails (bad/expired key, out of credits, offline, empty reply). With no local
    model, Ollama is the last stop (it downloads one), so this works with no keys.

    Returns (generator, used) where `used` is filled in with the label of the
    provider that actually answered once the generator starts producing text.
    """
    local = (lambda: local_fn(messages)) if local_fn else (lambda: runtime._call_ollama(messages, max_tokens=max_tokens))
    if not runtime.netgate.allowed():
        keys = {}                 # offline mode: the local model only
    attempts: list[tuple[str, runtime.Callable[[], runtime.Generator[str, None, None]]]] = []
    if runtime._local_model_ready():
        attempts.append(("Ollama (local)", local))     # tried like a provider: may fall through
    if keys.get("anthropic_key"):
        attempts.append(("Claude", lambda: runtime._call_claude_direct(messages, keys["anthropic_key"], max_tokens=max_tokens)))
    if keys.get("api_key"):
        attempts.append(("xAI", lambda: runtime._call_xai_stream(messages, keys["api_key"], False, max_tokens)))
    if keys.get("openai_key"):
        attempts.append(("OpenAI", lambda: runtime._call_openai_direct(messages, keys["openai_key"], max_tokens=max_tokens)))
    gemini_key = keys.get("gemini_key") or (runtime._saved_key("gemini_key") if runtime.netgate.allowed() else "")
    groq_key = keys.get("groq_key") or (runtime._saved_key("groq_key") if runtime.netgate.allowed() else "")
    if groq_key:
        attempts.append(("Groq", lambda: runtime._call_groq_direct(messages, groq_key, max_tokens)))
    if gemini_key:
        attempts.append(("Gemini", lambda: runtime._call_gemini_direct(messages, gemini_key, max_tokens)))
    # Local first: Ollama answers whenever it has a model. Cursiv Cloud only steps
    # in when it doesn't (not installed / no model yet), and only if not turned off.
    if runtime.cloud_enabled():
        attempts.append(("Cursiv Cloud", lambda: runtime._call_cursiv_cloud(messages, max_tokens)))
    # local_fn: e.g. the coding models for codex, instead of the general chat model
    if not attempts or attempts[0][0] != "Ollama (local)":
        attempts.append(("Ollama", local))

    used: list[str] = []

    @serialized_work
    def _gen() -> Generator[str, None, None]:
        failures: list[str] = []
        for label, start in attempts:
            if label == "Cursiv Cloud" and runtime._local_model_ready():
                continue        # local model available -- it answers instead
            if label == "Ollama":
                # Last stop -- nothing left to fall back to, so stream everything
                # (including first-time download progress) straight through.
                used.append(label)
                if failures:
                    yield f"[{'; '.join(failures)} -- using local Ollama]\n\n"
                for chunk in start():
                    if chunk != runtime.RATE_SENTINEL:
                        yield chunk
                return

            stream = start()
            held: list[str] = []      # rate-gate notes seen before real text
            failed = None
            try:
                for chunk in stream:
                    if chunk == runtime.RATE_SENTINEL:
                        failed = "busy or unreachable"
                        break
                    text = chunk.strip()
                    if not text:
                        continue
                    if text.startswith(runtime._PROVIDER_ERROR_PREFIXES):
                        failed = text.strip("[]")[:160]
                        break
                    if text.startswith("*[Rate gate"):
                        held.append(chunk)
                        continue
                    # Real text: this provider answers. Stream the rest straight through.
                    used.append(label)
                    if failures:
                        yield f"[{'; '.join(failures)} -- answered by {label}]\n\n"
                    yield from held
                    yield chunk
                    for rest in stream:
                        if rest != runtime.RATE_SENTINEL:
                            yield rest
                    return
            except Exception as e:
                failed = str(e)[:160]
            failures.append(f"{label}: {failed or 'empty reply'}")
        if failures:      # reached only when the local model went first and everything failed
            yield f"[Nothing answered — {'; '.join(failures)}]"

    return _gen(), used

def _classify_message(runtime: ChatRuntime, text: str) -> str:
    """Return 'code', 'creative', or 'general' for smart model routing."""
    t = (text or "").strip()
    if not t:
        return "general"
    if any(m in t for m in ("def ", "class ", "```", "import ", "Error:", "Traceback", "  File \"")):
        return "code"
    if len(runtime._CODE_STRONG_RE.findall(t)) >= 1:
        return "code"
    code_hits     = len(runtime._CODE_RE.findall(t))
    creative_hits = len(runtime._CREATIVE_RE.findall(t))
    if creative_hits >= 2 and creative_hits > code_hits:
        return "creative"
    # Generic verbs (write/build/create/test/...) need 2+ hits before this
    # counts as code -- a single "create" or "build" is common in completely
    # non-code requests ("create a farming schedule", "build my confidence")
    # and shouldn't alone route someone into the local coding models.
    if code_hits >= 2:
        return "code"
    return "general"

def _is_online(runtime: ChatRuntime) -> bool:
    """TCP connect to 8.8.8.8:53 — tests internet without a DNS lookup.
    False, without connecting, while offline mode is on."""
    if not runtime.netgate.allowed():
        return False
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

def _cloud_configured(runtime: ChatRuntime, *keys: str) -> bool:
    """Is anything set up that could send this turn off the computer?"""
    if any((k or "").strip() for k in keys):
        return True
    if any(runtime._saved_key(f) for f in ("api_key", "openai_key", "anthropic_key", "gemini_key", "groq_key")):
        return True
    return runtime.netgate.web_search_auto()

def _connectivity_probe(runtime: ChatRuntime, *keys: str):
    """For the Connectivity phase: None (not checked) when nothing would use the
    internet -- offline mode on, or the local model ready with no cloud key or
    cloud feature on. Otherwise the 8.8.8.8 check (AUDIT C-011)."""
    if not runtime.netgate.allowed():
        return None
    if runtime._local_model_ready() and not runtime._cloud_configured(*keys):
        return None
    return runtime._is_online()

def _local_stream(runtime: ChatRuntime, text_msgs: list[dict], user_text: str) -> tuple[str, Generator[str, None, None]]:
    """The local model's reply -- the coding pair for code questions, unless a
    small GPU already has the chat model loaded (switching costs minutes)."""
    _is_code = runtime._classify_message(user_text) == "code"
    try:
        from cursiv_engine.core import speed as _speed
        if _is_code and _speed.small_gpu():
            _loaded = _speed.loaded_models()
            if _loaded and not any("coder" in m for m in _loaded):
                _is_code = False
    except Exception:
        pass
    if _is_code:
        return "Local coding models", runtime._call_ollama_code_council(text_msgs)
    return "Ollama", runtime._call_ollama(text_msgs)

def _fallback_chain(runtime: ChatRuntime, text_msgs: list[dict], user_text: str, tried: list[str], local_tried: bool) -> Generator[str, None, None]:
    """Last part of chat()'s cascade, after the paid providers: the user's own
    free Gemini/Groq keys, then local Ollama. When Ollama has no usable model,
    Cursiv Cloud (if not turned off) answers before Ollama's first-time download."""
    # Groq first: it answers in under a second; Gemini is often overloaded on free keys
    for label, field, fn in (("Groq", "groq_key", runtime._call_groq_direct), ("Gemini", "gemini_key", runtime._call_gemini_direct)):
        key = runtime._saved_key(field) if runtime.netgate.allowed() else ""
        if not key:
            continue
        tried.append(label)
        gen = fn(text_msgs, key)
        first = next(gen, None)
        if first is not None and not first.lstrip().startswith(f"[{label} error"):
            if len(tried) > 1:
                yield f"*[{' → '.join(tried[:-1])} unavailable — {label}]*\n\n"
            runtime._set_answered(label)
            yield first
            yield from gen
            return

    if runtime.cloud_enabled() and not runtime._local_model_ready():
        tried.append("Cursiv Cloud")
        gen = runtime._call_cursiv_cloud(text_msgs)
        first = next(gen, None)
        if first is not None and not first.lstrip().startswith("[Cursiv Cloud error"):
            if len(tried) > 1:
                yield f"*[{' → '.join(tried[:-1])} unavailable — Cursiv Cloud]*\n\n"
            runtime._set_answered("Cursiv Cloud")
            yield first
            yield from gen
            return

    if local_tried:     # it already had its turn first and didn't answer
        if tried:
            yield f"*[{', '.join(tried + ['the local model'])} didn't answer.]*"
        else:
            yield "*[The local model didn't answer. Try again in a moment, or add a free key in Settings.]*"
        return
    _label, ollama_gen = runtime._local_stream(text_msgs, user_text)
    _is_code = _label == "Local coding models"
    first_ol   = next(ollama_gen, None)
    if first_ol is not None:
        if not first_ol.lstrip().startswith("[Ollama"):
            runtime._set_answered(runtime._ollama_label(_label))
        if tried:
            _label = "Local coding models" if _is_code else "Ollama"
            yield f"*[{' → '.join(tried)} unavailable — {_label}]*\n\n"
        yield first_ol
        yield from ollama_gen
    else:
        if tried:
            yield (
                f"*[{', '.join(tried)} unavailable and Ollama is not running.]*\n\n"
                "For offline answers, the local AI engine needs to be running: type `status` to see why it "
                "isn't, or open Setup to install the local model."
            )
        else:
            yield (
                "[No AI is available yet: no API key, Ollama isn't running, and Cursiv Cloud "
                + ("couldn't be reached" if runtime.cloud_enabled() else "is turned off ('cloud on' to use it)")
                + ".]\n\n"
                "**To run locally:** open Setup to install the local AI engine and model, or type `status` "
                "to see why the engine isn't running.\n\n"
                + runtime.FREE_KEY_HELP
            )

def _router_llm(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> str:
    """Fast, small calls during a chat (tool routing, the verification pass): the local
    model directly when one is ready -- not _quick_llm, which waits until no chat is
    running. The user's free keys only when there is no local model, so a turn the
    local model answered never leaves this computer for its check."""
    if runtime._ollama_running() and runtime._resolve_ollama_model():
        return runtime._local_llm(messages, max_tokens)
    return runtime._free_key_llm(messages, max_tokens)

def warm_up_local(runtime: ChatRuntime) -> None:
    """Load the local chat model ahead of the first message (call off the UI thread)."""
    try:
        from cursiv_engine.core import speed
        if runtime._ollama_running():
            speed.warm_up(runtime._resolve_ollama_model() or "")
    except Exception:
        pass

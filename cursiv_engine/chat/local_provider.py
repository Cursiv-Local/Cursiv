"""Chat local provider.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _call_ollama_raw, _call_ollama, _ollama_running, _ensure_ollama, _ollama_pulled_models, _ollama_tags, _models_on_disk, _resolve_ollama_model, _pull_ollama_model, _call_ollama_model, _big_gpu, _num_ctx, _call_ollama_code_council.
"""
from __future__ import annotations
from . import request_budget

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _call_ollama_raw(runtime: ChatRuntime, messages: list[dict], max_tokens: int, standard: bool) -> Generator[str, None, None]:
    """Stream from local Ollama with full system prompt injection."""
    import json as _json

    # Separate system instructions from conversation turns.
    # Ollama's /api/generate accepts a dedicated `system` field — using it
    # properly grounds the model in the Cursiv identity and capabilities.
    from cursiv_engine.core import speed as _speed
    # Small GPUs: the CPU reads the whole prompt before the first word, so send the
    # compact persona + what fits (the full one took up to a minute on a 4 GB card).
    if request_budget.current() is None:
        messages = runtime._slim(messages, 14000 if _speed.small_gpu() else 48000)
    system_parts = [
        m["content"] for m in messages
        if m.get("role") == "system" and isinstance(m.get("content"), str)
    ]
    system_str = runtime._IDENTITY_OVERRIDE + "\n\n".join(system_parts)

    # Build conversation prompt from user/assistant turns only.
    turns = "\n".join(
        f"{'Human' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    )

    if not runtime._ensure_ollama():
        yield "\n[Ollama not found. Install from https://ollama.com then run: ollama pull llama3.1]"
        return
    if runtime._ollama_tags() is None:
        yield "\n[Ollama unavailable: it isn't responding right now -- it may be busy downloading a model. Try again in a minute.]"
        return
    from . import model_selection
    model = (model_selection.model('ollama','') if not standard else '') or runtime._resolve_ollama_model(standard)
    if model is None and runtime._models_on_disk():
        # Seen for real: Ollama started with the wrong settings mid-reinstall and
        # listed nothing while 22 GB of models sat on disk. Re-downloading won't help.
        yield ("\n[Ollama is running but can't see your downloaded models. Restart it: open Cursiv's "
               "Setup window and click Restart Ollama (or quit Ollama from its tray icon and open it again).]")
        return
    if model is None:
        from cursiv_engine.core.paths import portable_root
        if portable_root():
            from cursiv_engine.core.ollama_host import diagnose
            yield '\n[No usable local model. ' + diagnose() + ' No model was downloaded.]'
            return
        # Ollama is running but has no models at all -- download the default
        # once (progress shown in the reply) instead of failing with a 404.
        yield from runtime._pull_ollama_model(_speed.chat_model_prefs()[0])
        model = runtime._resolve_ollama_model(standard)
        if model is None:
            yield f"\n[No local model available. Run: ollama pull {_speed.chat_model_prefs()[0]}]"
            return
    from cursiv_engine.core import last_turn
    if not standard:      # the answer itself, not a helper call (titles, checks, classifiers)
        last_turn.record_sent("Ollama (local)", model, system_str, 14000 if _speed.small_gpu() else 48000)
    if _speed.gpu_options(model):
        _speed.make_room(model)                 # one model on a small card at a time
    deep = not standard and model == _speed.DEEP_THINK_MODEL and _speed.deep_think_on()
    if deep:
        yield "*(Deep Think: working it through first. On this computer that can take a minute or two.)*\n\n"
        max_tokens += _speed.DEEP_THINK_EXTRA_TOKENS
    payload = runtime.json.dumps({
        "model": model,
        "system": system_str,
        "prompt": turns,
        "stream": True,
        "keep_alive": _speed.keep_alive(),        # stay loaded: a cold load took ~100 s (2 min on battery saver)
        **_speed.think_options(model, deep),      # Deep Think's reasoning comes back separately, not in "response"
        "options": {
            "num_predict": max_tokens,
            "num_ctx": _speed.num_ctx(),
            **_speed.gpu_options(model),
        },
    }).encode()
    for attempt in (1, 2):
        try:
            req = runtime.urllib.request.Request(runtime.OLLAMA_URL, data=payload,
                                         headers={"Content-Type": "application/json"})
            # 600 s: loading a model that doesn't fit the GPU can take ~2 minutes
            with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=600) as resp:
                for line in resp:
                    chunk = _json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        if not standard:
                            model_selection.record(runtime,'ollama',model,chunk.get('model'))
                        yield token
                    if chunk.get("done"):
                        break
            return
        except Exception as e:
            # More layers on the card than it has room for right now (another program
            # using it): once more with Ollama's own split.
            if attempt == 1 and _speed.gpu_options(model):
                _speed.gpu_fallback(model)
                body = _json.loads(payload)
                body["options"].pop("num_gpu", None)
                payload = runtime.json.dumps(body).encode()
                continue
            yield f"\n[Ollama unavailable: {e}]"
            return

def _call_ollama(runtime: ChatRuntime, messages: list[dict], max_tokens: int, standard: bool) -> 'Generator[str, None, None]':
    yield from runtime._call_ollama_raw(messages, max_tokens, standard)

def _ollama_running(runtime: ChatRuntime) -> bool:
    try:
        runtime.urllib.request.urlopen(runtime.OLLAMA_TAGS_URL, timeout=2)
        return True
    except Exception:
        return False

def _ensure_ollama(runtime: ChatRuntime) -> bool:
    """Start Ollama in the background if it isn't running. Returns True once reachable."""
    if runtime._ollama_running():
        return True

    from cursiv_engine.core import ollama_host as _host
    if not _host.installed():
        return False  # not installed — nothing to start
    try:
        from cursiv_engine.core import speed as _speed
        return _host.start(_speed.ollama_env(), wait=15)   # (60 s on a USB); flash attention + compact cache
    except Exception:
        return False

def _ollama_pulled_models(runtime: ChatRuntime) -> set[str]:
    """Return set of model name tags currently pulled in Ollama."""
    try:
        req = runtime.urllib.request.Request(runtime.OLLAMA_TAGS_URL)
        with runtime.urllib.request.urlopen(req, timeout=5) as resp:
            data = runtime.json.loads(resp.read().decode())
        names = set()
        for m in data.get("models", []):
            tag = m.get("name", "")
            names.add(tag)
            names.add(tag.split(":")[0])
        return names
    except Exception:
        return set()

def _ollama_tags(runtime: ChatRuntime) -> list[str] | None:
    """Installed model tags, or None if Ollama didn't answer (busy or not running).
    A slow Ollama -- e.g. while it downloads another model -- must not look like
    'no models installed'."""
    for timeout in (8, 20):
        try:
            with runtime.urllib.request.urlopen(runtime.urllib.request.Request(runtime.OLLAMA_TAGS_URL), timeout=timeout) as resp:
                return [m.get("name", "") for m in runtime.json.loads(resp.read().decode()).get("models", [])]
        except Exception:
            continue
    return None

def _models_on_disk(runtime: ChatRuntime) -> bool:
    """True if Ollama's model folder holds downloaded models (whether or not the
    running Ollama currently lists them)."""
    base = runtime.Path(runtime.os.environ.get("OLLAMA_MODELS") or (runtime.Path.home() / ".ollama" / "models"))
    lib = base / "manifests" / "registry.ollama.ai" / "library"
    try:
        return any(lib.iterdir())
    except Exception:
        return False

def _resolve_ollama_model(runtime: ChatRuntime, standard: bool) -> str | None:
    """Pick an installed Ollama model for general chat, or None if none are pulled.
    standard: the everyday model even when Deep Think is on (checks, background jobs)."""
    tags = runtime._ollama_tags()
    if tags is None:
        return None
    available = set(tags) | {t.split(":")[0] for t in tags}
    budget = request_budget.current()
    if budget and budget.local_model:
        return budget.local_model if budget.local_model in available else None
    from cursiv_engine.core import speed as _speed
    if not standard and _speed.deep_think_on() and _speed.DEEP_THINK_MODEL in available:
        return _speed.DEEP_THINK_MODEL
    _chosen = runtime._saved_key("chat_model") if runtime._saved_key("show_all_models") == "on" else ""   # Advanced menu pick
    if _chosen and _chosen in available and not (standard and _chosen == _speed.DEEP_THINK_MODEL):
        return _chosen
    # Fastest good model for this GPU first (e.g. a 3B model on a 4 GB card), if installed
    for name in (*_speed.chat_model_prefs(), runtime.OLLAMA_MODEL, *runtime._OLLAMA_FALLBACK_MODELS):
        if name in available:
            return name
    # Anything else that isn't an embedding-only model
    for tag in tags:
        if tag and "embed" not in tag.lower():
            return tag
    return None

def _pull_ollama_model(runtime: ChatRuntime, model: str) -> Generator[str, None, None]:
    """Download a model through Ollama's API, yielding short progress lines."""
    if request_budget.current() is not None:
        yield '\n[No installed model available. Research runs never download a model.]'
        return
    if not runtime.netgate.allowed():
        yield (f"\n[No local model installed yet, and offline mode is on, so {model} can't be "
               "downloaded. Type 'offline off' to allow it.]\n")
        return
    yield f"\n[No local model installed yet -- downloading {model} (one-time setup, a few GB)...]\n"
    last_pct = -10
    try:
        req = runtime.urllib.request.Request(
            runtime.OLLAMA_URL.replace("/api/generate", "/api/pull"),
            data=runtime.json.dumps({"name": model, "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with runtime.urllib.request.urlopen(req, timeout=3600) as resp:
            for line in resp:
                try:
                    status = runtime.json.loads(line.decode())
                except Exception:
                    continue
                if status.get("error"):
                    yield f"[Download failed: {status['error']}]\n"
                    return
                total, done = status.get("total"), status.get("completed")
                if total and done:
                    pct = int(done * 100 / total)
                    if pct >= last_pct + 10:
                        last_pct = pct
                        yield f"[{model}: {pct}%]\n"
                if status.get("status") == "success":
                    yield f"[{model} ready.]\n\n"
                    return
    except Exception as e:
        yield f"[Download failed: {e}]\n"

def _call_ollama_model(runtime: ChatRuntime, model: str, system_str: str, prompt: str, max_tokens: int, collect: bool) -> Generator[str, None, None]:
    """Call a specific Ollama model. If collect=True, yields one final chunk (full text)."""
    import json as _json
    from cursiv_engine.core import speed as _speed
    # Always prepend identity override — DeepSeek especially needs it
    system_str = runtime._IDENTITY_OVERRIDE + system_str
    payload = runtime.json.dumps({
        "model":  model,
        "system": system_str,
        "prompt": prompt,
        "stream": not collect,
        # 16k context: coding prompts carry playbooks + worked examples; at 8k Ollama
        # silently dropped the start of the prompt (the instructions).
        "keep_alive": "30m",
        **_speed.no_thinking(model),
        "options": {"num_predict": max_tokens, "num_ctx": runtime._num_ctx(), **_speed.gpu_options(model)},
    }).encode()
    try:
        req = runtime.urllib.request.Request(
            runtime.OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"},
        )
        with request_budget.open_request(runtime.urllib.request.urlopen, req, timeout=600) as resp:
            if collect:
                data = _json.loads(resp.read().decode())
                yield data.get("response", "")
            else:
                for line in resp:
                    chunk = _json.loads(line.decode())
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except runtime.urllib.error.HTTPError as e:
        try:
            detail = runtime.json.loads(e.read().decode()).get("error", "")
        except Exception:
            detail = ""
        yield f"\n[{model} error: HTTP {e.code}{' -- ' + detail if detail else ''}]"
    except Exception as e:
        yield f"\n[{model} error: {e}]"

def _big_gpu(runtime: ChatRuntime) -> bool:
    """>= 12 GB of GPU memory (NVIDIA or AMD): room for a second coding model as a
    reviewer. On smaller GPUs swapping 14B/16B models took minutes per answer."""
    from cursiv_engine.core import speed
    return speed.big_gpu()

def _num_ctx(runtime: ChatRuntime) -> int:
    from cursiv_engine.core import speed
    return speed.num_ctx()

def _call_ollama_code_council(runtime: ChatRuntime, messages: list[dict], max_tokens: int) -> Generator[str, None, None]:
    """
    Dual-model offline coding help:
      Phase 1 — qwen2.5-coder:14b writes the primary solution (streamed live)
      Phase 2 — deepseek-coder-v2:16b reviews and improves it (streamed live)
    Falls back to llama3.1 if neither coding model is pulled.
    """
    available    = runtime._ollama_pulled_models()
    # Use the exact tags that are installed (e.g. qwen2.5-coder:7b), not only the
    # 14b/16b defaults -- asking Ollama for a tag that isn't pulled just fails.
    def _installed(preferred: str, family: str) -> str | None:
        if family == "qwen2.5-coder":       # the size that suits this GPU, if installed
            from cursiv_engine.core import speed
            for tag in speed.code_model_prefs():
                if tag in available:
                    return tag
        if preferred in available:
            return preferred
        tags = sorted(t for t in available if t.startswith(family + ":"))
        return tags[-1] if tags else None
    qwen_tag     = _installed(runtime.OLLAMA_CODE_PRIMARY, "qwen2.5-coder")
    deepseek_tag = _installed(runtime.OLLAMA_CODE_SECONDARY, "deepseek-coder-v2")
    has_qwen, has_deepseek = qwen_tag is not None, deepseek_tag is not None

    if not has_qwen and not has_deepseek:
        yield from runtime._call_ollama(messages, max_tokens)
        return

    system_parts = [
        m["content"] for m in messages
        if m.get("role") == "system" and isinstance(m.get("content"), str)
    ]
    system_str = "\n\n".join(system_parts)
    turns = "\n".join(
        f"{'Human' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
        for m in messages
        if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    )

    primary_model   = qwen_tag if has_qwen else deepseek_tag
    # Reviewer only where both models fit in GPU memory; elsewhere codex's
    # run-and-fix loop (coding/runner.py) checks the code by actually running it.
    secondary_model = deepseek_tag if has_deepseek and has_qwen and runtime._big_gpu() else None

    # ── Phase 1: Primary coder writes solution ───────────────────────────
    if secondary_model:
        yield f"**[{primary_model}]** Writing solution...\n\n"

    primary_chunks: list[str] = []
    for token in runtime._call_ollama_model(primary_model, system_str, turns, max_tokens):
        primary_chunks.append(token)
        yield token

    if not primary_chunks:
        # _call_ollama_model completed without yielding anything and without
        # raising -- e.g. Ollama accepted the request but the model produced
        # an empty response. Previously this looked identical to a UI bug
        # (the "Writing solution..." header shown, then nothing, forever)
        # with no way to tell what actually happened.
        yield (f"\n[{primary_model} produced no output. It may still be loading "
               f"into memory on first use -- try again in a moment, or confirm "
               f"it's pulled with `ollama list`.]")
        return

    if not secondary_model:
        return

    # ── Phase 2: Critic reviews and improves ────────────────────────────
    primary_text = "".join(primary_chunks)
    yield f"\n\n---\n**[{secondary_model}]** Code review...\n\n"

    review_prompt = (
        f"{turns}\n\n"
        f"A colleague produced this solution:\n\n{primary_text}\n\n"
        "Review it critically. If it is correct and clean, confirm briefly and add any meaningful "
        "improvements or edge-case handling. If there are bugs or a clearly better approach, "
        "rewrite only the affected parts. Be concise — do not repeat what is already correct."
    )
    yield from runtime._call_ollama_model(secondary_model, system_str, review_prompt, max_tokens)

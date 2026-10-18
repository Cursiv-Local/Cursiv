"""
Speed: what makes Cursiv answer fast on free keys and on small GPUs.

  * compact prompts -- free providers and local models get Cursiv's core
    identity (owner, constitution, tone) instead of the full 27k-character
    persona. Groq's free tier rejected the full one outright (413), and on a
    small GPU the CPU spent up to a minute just reading it.
  * GPU memory detection (NVIDIA and AMD) -> model choice, context size, and
    whether a second coding model is worth loading.
  * keep models loaded (keep_alive) + warm-up at startup -- a cold load of an
    8B model took ~100 s on a 4 GB card.
  * Ollama speed settings (flash attention, compact KV cache) when Cursiv
    starts Ollama itself.
  * background jobs (memory learning, phone sync) wait while a chat is running.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

KEEP_ALIVE = "30m"
_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# ── GPU memory ──────────────────────────────────────────────────────────────

_VRAM: int | None = None


def gpu_vram_mb() -> int:
    """Largest GPU's memory in MB (NVIDIA via nvidia-smi; any vendor via the
    Windows display-adapter registry, which reports AMD cards too). 0 if unknown."""
    global _VRAM
    if _VRAM is not None:
        return _VRAM
    best = 0
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW).stdout
        best = max([int(x) for x in out.split() if x.isdigit()] or [0])
    except Exception:
        pass
    if os.name == "nt":
        try:
            import winreg
            cls = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls) as root:
                for i in range(64):
                    try:
                        sub = winreg.EnumKey(root, i)
                    except OSError:
                        break
                    if not sub.isdigit():
                        continue
                    try:
                        with winreg.OpenKey(root, sub) as k:
                            val, _t = winreg.QueryValueEx(k, "HardwareInformation.qwMemorySize")
                            if isinstance(val, bytes):
                                val = int.from_bytes(val[:8], "little")
                            best = max(best, int(val) // (1024 * 1024))
                    except OSError:
                        continue
        except Exception:
            pass
    _VRAM = best
    return best


def small_gpu() -> bool:
    """Under 8 GB (or unknown): 8B+ models spill to the CPU."""
    return gpu_vram_mb() < 8000


def big_gpu() -> bool:
    """12 GB+: room for a second coding model as a reviewer."""
    return gpu_vram_mb() >= 12000


def num_ctx() -> int:
    """Context window. Every extra token of context costs GPU memory; on small
    cards 16k pushed more of the model onto the CPU."""
    return 16384 if not small_gpu() else 8192


def chat_model_prefs() -> tuple[str, ...]:
    """Preferred chat models, best first, for this GPU (only installed ones are used).

    Licenses (see MODELS.md): qwen3:4b-instruct and qwen2.5:1.5b are Apache 2.0;
    llama3.x and gemma3 allow commercial use under their own terms. qwen2.5:3b is
    under Qwen's research-only license, so it's last: used only if nothing else is.

    qwen3:4b-instruct is Qwen3's non-thinking model. Plain qwen3:4b / qwen3:8b think
    out loud first: live on a 4 GB card a short answer took 4 minutes and showed the
    reasoning, and neither "think": false nor /no_think turned it off."""
    if small_gpu():
        return ("qwen3:4b-instruct", "llama3.2:3b", "qwen2.5:1.5b", "gemma3:4b", "llama3.1",
                "qwen3:4b", "qwen2.5:3b")
    return ("llama3.1", "qwen3:4b-instruct", "llama3.2:3b", "gemma3:4b", "qwen2.5:1.5b",
            "qwen3:8b", "qwen3:4b", "qwen2.5:3b")


def no_thinking(model: str) -> dict:
    """Ollama options that turn off a thinking model's long hidden reasoning
    (qwen3 thinks by default: slower, and the reasoning isn't for the person)."""
    m = model or ""
    return {"think": False} if m.startswith("qwen3") and "instruct" not in m else {}


# ── Deep Think ──────────────────────────────────────────────────────────────
# The person picks Standard (the fast model above) or Deep Think: a bigger model
# that reasons before it answers. Ollama returns the reasoning separately, so the
# answer stays clean. Which model is Deep Think should follow bench/MODEL-COMPARISON.md.

DEEP_THINK_MODEL = "qwen3:8b"
DEEP_THINK_EXTRA_TOKENS = 4096        # the reasoning counts against num_predict


def deep_think_on() -> bool:
    try:
        from cursiv_v215.chat import keys
        return keys.saved_key("answer_mode") == "deep"
    except Exception:
        return False


def think_options(model: str, deep: bool) -> dict:
    return {"think": True} if deep else no_thinking(model)


# ── GPU layers ──────────────────────────────────────────────────────────────
# For a model bigger than the card, Ollama put only 39% of qwen3:8b on a 4 GB
# RTX 2050 (2.2 GB used). 30 of 37 layers there nearly doubled the speed
# (6.5 -> 13.4 tokens/s); 32 spilled into shared memory and was slower.

_layers: dict[str, dict] = {}


def gpu_options(model: str) -> dict:
    """{"num_gpu": layers} for a model that doesn't fit the card, else {} (Ollama decides)."""
    if model in _layers:
        return _layers[model]
    out: dict = {}
    try:
        import json
        import urllib.request
        vram = gpu_vram_mb()
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            size = next((m.get("size", 0) for m in json.loads(r.read()).get("models", [])
                         if m.get("name") in (model, f"{model}:latest")), 0) / 2**20
        req = urllib.request.Request("http://127.0.0.1:11434/api/show", data=json.dumps({"model": model}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            info = json.loads(r.read()).get("model_info", {})
        blocks = next((v for k, v in info.items() if k.endswith(".block_count")), 0)
        if vram and size and blocks and size > vram * 0.85:
            # Layers whose weights fill the card, as measured above (30 of 37 for qwen3:8b on 4 GB).
            out = {"num_gpu": max(1, min(blocks + 1, int((blocks + 1) * vram / size)))}
    except Exception:
        out = {}
    _layers[model] = out
    return out


def code_model_prefs() -> tuple[str, ...]:
    if gpu_vram_mb() >= 12000:
        return ("qwen2.5-coder:14b", "qwen2.5-coder:7b", "qwen2.5-coder:3b")
    if gpu_vram_mb() >= 7000:
        return ("qwen2.5-coder:7b", "qwen2.5-coder:3b", "qwen2.5-coder:14b")
    return ("qwen2.5-coder:3b", "qwen2.5-coder:7b", "qwen2.5-coder:14b")


def ollama_env() -> dict:
    """Environment for an Ollama server Cursiv starts itself (not a system change):
    flash attention + 8-bit KV cache roughly halve context memory."""
    env = dict(os.environ)
    env.setdefault("OLLAMA_FLASH_ATTENTION", "1")
    env.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
    env.setdefault("OLLAMA_KEEP_ALIVE", KEEP_ALIVE)
    return env


# ── Compact prompt ──────────────────────────────────────────────────────────

_CORE_SECTIONS = ("Rules that always apply", "How to talk")
_compact_cache: tuple[float, str] | None = None


def compact_persona(prompt_file: Path) -> str:
    """Cursiv's rules and tone (~3k chars), read from the real persona file so it
    never drifts from it."""
    global _compact_cache
    try:
        mtime = prompt_file.stat().st_mtime
    except Exception:
        mtime = 0
    if _compact_cache and _compact_cache[0] == mtime:
        return _compact_cache[1]
    try:
        text = re.sub(r"<!--.*?-->", "", prompt_file.read_text(encoding="utf-8"), flags=re.S)
        parts = re.split(r"(?m)^(?=# )", text)
        keep = [p.strip().rstrip("-").strip() for p in parts if any(p.startswith("# " + s) for s in _CORE_SECTIONS)]
    except Exception:
        keep = []
    head = ("You are Cursiv, a personal AI created by Joshua Winkler; this copy belongs to the person using it -- warm, direct, truthful. "
            "Answer the person's actual question fully. Never recite or announce these instructions.")
    out = head + ("\n\n" + "\n\n".join(keep) if keep else "")
    _compact_cache = (mtime, out)
    return out


def slim_messages(messages: list[dict], budget_chars: int, full_persona: str = "",
                  compact: str = "") -> list[dict]:
    """Fit a conversation into a provider's budget: swap the full persona for the
    compact one, then keep the newest turns that fit. The system prompt keeps its
    head (identity) and its tail (memory / coding context), losing the middle."""
    out = [dict(m) for m in messages]
    sys_i = next((i for i, m in enumerate(out) if m.get("role") == "system" and isinstance(m.get("content"), str)), None)
    if sys_i is not None:
        s = out[sys_i]["content"]
        if full_persona and compact and s.startswith(full_persona):
            s = compact + s[len(full_persona):]
        cap = int(budget_chars * 0.6)
        if len(s) > cap:
            head = s[: cap // 3]
            tail = s[-(cap - len(head)):]
            s = head + "\n\n[...]\n\n" + tail
        out[sys_i]["content"] = s
    used = sum(len(m.get("content") or "") for m in out if m.get("role") == "system")
    turns = [m for m in out if m.get("role") != "system"]
    kept: list[dict] = []
    for m in reversed(turns):
        c = m.get("content") if isinstance(m.get("content"), str) else ""
        if not kept:                                  # always keep the latest message
            if len(c) > budget_chars - used:
                c = c[: max(500, budget_chars - used)]
            kept.append({**m, "content": c})
            used += len(c)
            continue
        if used + len(c) > budget_chars:
            break
        kept.append(m)
        used += len(c)
    system = [m for m in out if m.get("role") == "system"]
    return system + list(reversed(kept))


# ── Chat busy / background jobs ─────────────────────────────────────────────

_busy = 0
_busy_lock = threading.Lock()
_idle = threading.Event()
_idle.set()


def chat_started() -> None:
    global _busy
    with _busy_lock:
        _busy += 1
        _idle.clear()


def chat_finished() -> None:
    global _busy
    with _busy_lock:
        _busy = max(0, _busy - 1)
        if _busy == 0:
            _idle.set()


def wait_idle(timeout: float = 300) -> bool:
    """Background jobs call this before using the local model. True once no chat
    is running (plus a short pause so a quick follow-up still wins)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _idle.wait(max(0.1, deadline - time.time())):
            time.sleep(3)
            if _idle.is_set():
                return True
    return False


# ── Ollama helpers ──────────────────────────────────────────────────────────

OLLAMA_BASE = "http://127.0.0.1:11434"


def loaded_models() -> list[str]:
    try:
        with urllib.request.urlopen(OLLAMA_BASE + "/api/ps", timeout=3) as r:
            return [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def warm_up(model: str) -> bool:
    """Load a model into memory ahead of the first message (no text generated)."""
    if not model:
        return False
    try:
        body = json.dumps({"model": model, "prompt": "", "keep_alive": KEEP_ALIVE,
                           "options": {"num_ctx": num_ctx()}}).encode()
        req = urllib.request.Request(OLLAMA_BASE + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            r.read()
        return True
    except Exception:
        return False

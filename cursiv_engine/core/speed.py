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
import sys
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
    cards 16k pushed more of the model onto the CPU. Battery saver: 4k."""
    if battery_saver():
        return 4096
    return 16384 if not small_gpu() else 8192


# ── Battery saver (research roadmap R5) ─────────────────────────────────────
# Setting "battery_saver": "" automatic (on while unplugged), "on", "off". While on:
# a smaller context, the model released from memory after 2 minutes idle instead
# of 30, and no second model call to check answers (the checks done in code, such
# as arithmetic, doses and the reference card, still run).

_batt_cache: dict = {"t": 0.0, "on": False}


def _mac_on_battery() -> bool:
    """macOS: `pmset -g batt` says "Battery Power" or "AC Power" (checked at most every 30 s)."""
    if time.monotonic() - _batt_cache["t"] < 30:
        return _batt_cache["on"]
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=3).stdout
        on = "Battery Power" in out
    except Exception:
        on = False
    _batt_cache.update(t=time.monotonic(), on=on)
    return on


def on_battery() -> bool:
    """True when this laptop is running on its battery (Windows or macOS)."""
    if sys.platform == "darwin":
        return _mac_on_battery()
    try:
        import ctypes

        class _Power(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_byte), ("BatteryFlag", ctypes.c_byte),
                        ("BatteryLifePercent", ctypes.c_byte), ("SystemStatusFlag", ctypes.c_byte),
                        ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]
        st = _Power()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
            return False
        return st.ACLineStatus == 0
    except Exception:
        return False


def battery_saver() -> bool:
    try:
        from cursiv_engine.chat import keys
        mode = keys.saved_key("battery_saver")
    except Exception:
        mode = ""
    if mode == "on":
        return True
    if mode == "off":
        return False
    return on_battery()


def keep_alive() -> str:
    return "2m" if battery_saver() else KEEP_ALIVE


def chat_model_prefs() -> tuple[str, ...]:
    """Preferred chat models, best first, for this GPU (only installed ones are used).

    Licenses (see MODELS.md): qwen3:4b-instruct and qwen2.5:1.5b are Apache 2.0;
    llama3.x and gemma3 allow commercial use under their own terms. qwen2.5:3b is
    under Qwen's research-only license, so it's last: used only if nothing else is.

    qwen3:4b-instruct is Qwen3's non-thinking model. Plain qwen3:4b / qwen3:8b think
    out loud first: live on a 4 GB card a short answer took 4 minutes and showed the
    reasoning, and neither "think": false nor /no_think turned it off.

    The same order on every card: on the model comparison (bench/MODEL-COMPARISON.md,
    2026-10-18) qwen3:4b-instruct passed 40 of 40, llama3.1 and gemma3:4b 35. Accuracy
    doesn't depend on the card, so a bigger card doesn't change the pick. The others are
    used only if nothing above them is installed."""
    return ("qwen3:4b-instruct", "qwen2.5:1.5b", "llama3.2:3b", "gemma3:4b", "llama3.1",
            "qwen3:4b", "qwen3:8b", "qwen2.5:3b")


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
# Not offered (2026-10-18): on the model comparison qwen3:8b was five times slower than
# Standard, no more accurate, and invented a treaty (bench/MODEL-COMPARISON.md). The
# benchmark can still try a candidate with CURSIV_DEEP_THINK=1 (truth_bench --deep).
DEEP_THINK_OFFERED = False
DEEP_THINK_EXTRA_TOKENS = 4096        # the reasoning counts against num_predict


def deep_think_on() -> bool:
    if not (DEEP_THINK_OFFERED or os.environ.get("CURSIV_DEEP_THINK") == "1"):
        return False                # a Deep Think choice saved by U64 falls back to Standard
    try:
        from cursiv_engine.chat import keys
        return keys.saved_key("answer_mode") == "deep"
    except Exception:
        return False


def think_options(model: str, deep: bool) -> dict:
    return {"think": True} if deep else no_thinking(model)


# ── GPU layers ──────────────────────────────────────────────────────────────
# Ollama is cautious on small cards. Measured on a 4 GB RTX 2050 (2026-10-18):
#   qwen3:4b-instruct  45% on the CPU by default, 16 tokens/s; all layers on the card 37
#   gemma3:4b          14 -> 36;   llama3.1  7.3 -> 15.7 (28 of 33 layers)
#   qwen3:8b           6.5 -> 13.4 (30 of 37); 32 spilled into shared memory and was slower
# A model whose file fits in 90% of the card goes on it whole; a bigger one gets the
# share of layers its file size allows. If a load fails, chat_app retries once with
# Ollama's own choice and gpu_fallback() remembers that for this session.

_layers: dict[str, dict] = {}


def make_room(model: str) -> None:
    """Unload other models from the card before loading one sized to fill it. With
    gemma3:4b still loaded (Ollama keeps models 30 minutes), llama3.1 forced into the
    rest spilled into shared memory: 230+ s an answer instead of about 20."""
    try:
        import json
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=3) as r:
            loaded = [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
        for other in loaded:
            if other and other not in (model, f"{model}:latest"):
                req = urllib.request.Request("http://127.0.0.1:11434/api/generate",
                                             data=json.dumps({"model": other, "keep_alive": 0}).encode(),
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass


def gpu_fallback(model: str) -> None:
    _layers[model] = {}


def gpu_options(model: str) -> dict:
    """{"num_gpu": layers} for how much of the model the card can hold, or {} (Ollama decides)."""
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
        if vram and size and blocks:
            layers = blocks + 1 if size <= vram * 0.9 else int((blocks + 1) * vram / size)
            out = {"num_gpu": max(1, min(blocks + 1, layers))}
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
    head (identity) and its tail (memory / coding context), losing the middle.
    Additional application system blocks carry bounded current state/evidence
    separately, so persona replacement cannot silently remove them."""
    out = [dict(m) for m in messages]
    sys_i = next((i for i, m in enumerate(out) if m.get("role") == "system" and isinstance(m.get("content"), str)), None)
    extra = [i for i, m in enumerate(out) if m.get('role') == 'system' and i != sys_i]
    reserve = max(0, int(budget_chars * .45))
    for i in extra:
        content = str(out[i].get('content') or '')
        out[i]['content'] = content[:reserve]
        reserve -= len(out[i]['content'])
    if sys_i is not None:
        s = out[sys_i]["content"]
        if full_persona and compact and s.startswith(full_persona):
            s = compact + s[len(full_persona):]
        cap = max(0, int(budget_chars * 0.6) - sum(len(out[i]['content']) for i in extra))
        if len(s) > cap:
            head = s[: cap // 3]
            tail_size = max(0, cap - len(head) - 12)
            tail = s[-tail_size:] if tail_size else ''
            s = (head + "\n\n[...]\n\n" + tail)[:cap]
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

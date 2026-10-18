"""
What the window shows about where answers come from and what can go online.

network_status() reads the same switches the network code obeys
(core/netgate.py, saved keys, the Cursiv Cloud setting), so the status pill
can't say "Local only" while something would actually go online.
local_models() lists the chat models Ollama has, for the model picker.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from cursiv_v215.core import netgate

KEY_NAMES = (("gemini_key", "Gemini key"), ("groq_key", "Groq key"), ("openai_key", "OpenAI key"),
             ("anthropic_key", "Claude key"), ("api_key", "xAI key"))
PREFERRED_MODEL = "chat_model"     # saved with the keys; "" = automatic


def _cloud_on() -> bool:
    try:
        data = json.loads((Path.home() / ".cursiv" / "cursiv_cloud.json").read_text(encoding="utf-8"))
        return bool(data.get("enabled", False))
    except Exception:
        return False


def network_status() -> dict:
    """{"level": "offline" | "local" | "online", "label": short text, "details": [lines]}"""
    if netgate.is_offline():
        return {"level": "offline", "label": "Offline mode",
                "details": ["Cursiv makes no internet connections: no cloud AI, web search, updates or downloads.",
                            "The local model, memory and reference still work."]}
    from cursiv_v215.chat import keys
    online = [name for field, name in KEY_NAMES if keys.saved_key(field)]
    if _cloud_on():
        online.append("Cursiv Cloud (only when no local model is ready)")
    if netgate.setting("web_search_auto"):
        online.append("automatic web search")
    if netgate.setting("update_check_auto"):
        online.append("automatic update check")
    if not online:
        return {"level": "local", "label": "Local only",
                "details": ["Answers come from the model on this computer.",
                            "Only a message you start with search: goes online."]}
    return {"level": "online", "label": "Online features on",
            "details": ["Can go online: " + ", ".join(online) + ".",
                        "Keys are used only when the local model can't answer, or for images.",
                        "Turn on offline mode to stop all of it."]}


def local_models(timeout: float = 2.0) -> list[str] | None:
    """Installed Ollama chat models (no embedding models), or None if Ollama isn't answering."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout) as r:
            names = [m.get("name", "") for m in json.loads(r.read().decode("utf-8")).get("models", [])]
    except Exception:
        return None
    return sorted(n for n in names if n and "embed" not in n.lower())


def preferred_model() -> str:
    from cursiv_v215.chat import keys
    return keys.saved_key(PREFERRED_MODEL)


def set_preferred_model(name: str) -> None:
    from cursiv_v215.chat import keys
    keys.store_key(PREFERRED_MODEL, name)


def automatic_model(installed: list[str]) -> str | None:
    """The model Cursiv picks on its own for this computer (core/speed.py order)."""
    from cursiv_v215.core import speed
    have = set(installed) | {n.split(":")[0] for n in installed}
    for name in speed.chat_model_prefs():
        if name in have:
            return next((n for n in installed if n == name or n.split(":")[0] == name), name)
    return installed[0] if installed else None


# ── The model menu: Standard and Deep Think; every model only under Advanced ──
# People pick what they want done, not a model name. "Show every model" in
# Settings -> AI model (Advanced) lists each installed model as well.

SHOW_ALL_MODELS = "show_all_models"      # "on" lists every installed model too


def show_all_models() -> bool:
    from cursiv_v215.chat import keys
    return keys.saved_key(SHOW_ALL_MODELS) == "on"


def set_show_all_models(on: bool) -> None:
    from cursiv_v215.chat import keys
    keys.store_key(SHOW_ALL_MODELS, "on" if on else "")


def menu_choices(installed: list[str]) -> list[tuple[str, str, bool]]:
    """(label, choice, enabled) for the model menu. choice: "standard", "deep" or "model:<name>"."""
    from cursiv_v215.core import speed
    deep = speed.DEEP_THINK_MODEL
    have_deep = deep in installed or f"{deep}:latest" in installed
    out = [("Standard  ·  quick everyday answers", "standard", True),
           (("Deep Think  ·  slower, for harder questions" if have_deep
             else f"Deep Think  ·  download {deep} in Setup first"), "deep", have_deep)]
    if show_all_models():
        out += [(f"Model: {m}", f"model:{m}", True) for m in installed]
    return out


def current_choice() -> str:
    from cursiv_v215.chat import keys
    if keys.saved_key("answer_mode") == "deep":
        return "deep"
    chosen = preferred_model()
    return f"model:{chosen}" if chosen and show_all_models() else "standard"


def choose(choice: str) -> None:
    """Save a menu choice. Standard clears a specific model; Deep Think turns on answer_mode."""
    from cursiv_v215.chat import keys
    keys.store_key("answer_mode", "deep" if choice == "deep" else "")
    set_preferred_model(choice[len("model:"):] if choice.startswith("model:") else "")

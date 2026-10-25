"""
Cursiv plugins -- the safe place where Cursiv can grow (Cursiv Forge).

A plugin is one .py file in ~/.cursiv/plugins/ that defines:

    PLUGIN = {"name": "dice", "description": "Rolls dice", "version": "1"}

    def register(cursiv):
        cursiv.add_command("roll", roll, "roll 2d6 -- roll dice")
        cursiv.add_tool("roll_dice", roll_tool, "Roll dice. args: {\"spec\": \"2d6\"}")
        cursiv.on_message(hint)      # optional: add context to replies

Safety:
  * Plugins are only installed with the person's approval (`evolve approve` or
    copying a file in themselves). The approved file's fingerprint (sha256) is
    recorded; if the file changes afterwards it is NOT loaded until re-approved.
  * Since U98 a plugin never runs inside Cursiv: every registration, command, tool
    and hook call runs in its own short-lived process (core/plugin_runner.py) with a
    cleaned environment, a time limit, and an audit hook that refuses network,
    other programs, native code and files outside the plugin's data folder.
  * Every plugin is loaded inside try/except: a broken plugin is switched off
    with its error shown in `plugins`, never crashing Cursiv.
  * Each command / tool / hook call is guarded the same way.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import threading
import time
import traceback
from pathlib import Path
from typing import Callable

DIR = Path.home() / ".cursiv" / "plugins"
STATE_FILE = DIR / "_plugins.json"
LOG_FILE = DIR / "_install_log.jsonl"
_lock = threading.RLock()

_commands: dict[str, dict] = {}     # word -> {fn, help, plugin}
_tools: dict[str, dict] = {}        # name -> {fn, description, plugin}
_hooks: list[dict] = []             # {fn, plugin}
_status: dict[str, dict] = {}       # plugin name -> {loaded, error, commands, tools}
_loaded = False


class PluginAPI:
    """What a plugin receives in register(cursiv)."""

    def __init__(self, plugin: str):
        self._plugin = plugin

    def add_command(self, word: str, fn: Callable[[str], str], help: str = "") -> None:
        word = word.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,23}", word):
            raise ValueError(f"bad command word: {word!r}")
        if word in _RESERVED:
            raise ValueError(f"'{word}' is a built-in Cursiv command")
        _commands[word] = {"fn": fn, "help": help or word, "plugin": self._plugin}

    def add_tool(self, name: str, fn: Callable[..., str], description: str) -> None:
        name = name.strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,40}", name):
            raise ValueError(f"bad tool name: {name!r}")
        _tools[name] = {"fn": fn, "description": description, "plugin": self._plugin}

    def on_message(self, fn: Callable[[str], str | None]) -> None:
        _hooks.append({"fn": fn, "plugin": self._plugin})

    def remember(self, fact: str) -> None:
        from cursiv_engine.memory import semantic
        semantic.add_fact(fact, source=f"plugin:{self._plugin}")

    def person(self) -> str:
        from cursiv_engine.memory import semantic
        return semantic.current_person()

    def data_dir(self) -> Path:
        """A folder this plugin may keep its own files in."""
        d = DIR / "_data" / self._plugin
        d.mkdir(parents=True, exist_ok=True)
        return d


# Words plugins may not take over (built-in commands).
_RESERVED = {
    "help", "key", "openai", "anthropic", "gemini", "groq", "cloud", "files", "workspace", "mode", "codex", "council",
    "hermes", "ref", "babel", "remember", "forget", "memory", "memories", "tone", "style", "agent", "agents",
    "evolve", "plugin", "plugins", "projects", "topics", "phases", "search", "owner", "status", "free", "grok",
    "claude", "ollama", "offline", "online", "tier", "governor", "write", "blast",
}


# ── state ───────────────────────────────────────────────────────────────────

def _state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(st: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, indent=2), encoding="utf-8")


def fingerprint(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def log(event: str, name: str, detail: str = "") -> None:
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M"), "event": event, "plugin": name,
                                "detail": detail[:500]}) + "\n")
    except Exception:
        pass


# ── loading ─────────────────────────────────────────────────────────────────

def _unload(name: str) -> None:
    for d in (_commands, _tools):
        for k in [k for k, v in d.items() if v["plugin"] == name]:
            d.pop(k)
    _hooks[:] = [h for h in _hooks if h["plugin"] != name]
    _status.pop(name, None)


def _load_file(path: Path, st: dict) -> None:
    name = path.stem
    info = st.get(name, {})
    code = path.read_text(encoding="utf-8")
    if not info.get("approved_hash"):
        _status[name] = {"loaded": False, "error": "not approved yet — type: plugin approve " + name}
        return
    if info["approved_hash"] != fingerprint(code):
        _status[name] = {"loaded": False, "error": "file changed since you approved it — review it, then: plugin approve " + name}
        return
    if not info.get("enabled", True):
        _status[name] = {"loaded": False, "error": "switched off"}
        return
    try:
        # Never imported into Cursiv (U98): registration runs in the plugin's own process.
        reply = _call(path, "register")
        api = PluginAPI(name)
        for word, help_text in reply["commands"].items():
            api.add_command(word, _proxy(path, "command", word), help_text)
        for tool, description in reply["tools"].items():
            api.add_tool(tool, _proxy(path, "tool", tool), description)
        if reply["hooks"]:
            api.on_message(_proxy(path, "hook", ""))
        meta = reply.get("meta") or {}
        _status[name] = {"loaded": True, "error": "", "description": meta.get("description", ""),
                         "commands": [w for w, c in _commands.items() if c["plugin"] == name],
                         "tools": [t for t, c in _tools.items() if c["plugin"] == name]}
    except Exception as e:
        _unload(name)
        _status[name] = {"loaded": False, "error": f"{type(e).__name__}: {e}"[:300]}
        log("load-failed", name, traceback.format_exc()[-800:])


# ── the plugin's own process (core/plugin_runner.py) ────────────────────────

TIMEOUT = 20          # seconds for one call; a hook on every message gets less
HOOK_TIMEOUT = 6


def runner_command() -> list[str]:
    import sys
    if getattr(sys, "frozen", False):
        return [sys.executable, "--plugin-runner"]          # launcher/main.py dispatches it
    return [sys.executable, "-I", str(Path(__file__).with_name("plugin_runner.py"))]


def _call(path: Path, action: str, item: str = "", arg=None, timeout: int = TIMEOUT) -> dict:
    """One plugin call in a fresh process with a cleaned environment. Raises on failure."""
    import os
    import subprocess
    from cursiv_engine.memory import semantic
    name = path.stem
    keep = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "LANG", "PYTHONIOENCODING")
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env["PYTHONIOENCODING"] = "utf-8"
    env["CURSIV_PLUGIN_SANDBOX"] = "1"
    request = {"path": str(path), "data_dir": str(DIR / "_data" / name), "action": action, "name": item,
               "arg": arg if arg is not None else "", "person": semantic.current_person()}
    p = subprocess.run(runner_command(), input=json.dumps(request), capture_output=True, text=True,
                       encoding="utf-8", timeout=timeout, env=env, stdin=None,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    marker = "@@CURSIV-PLUGIN@@"
    if marker not in (p.stdout or ""):
        raise RuntimeError(((p.stderr or p.stdout or "no reply from the plugin process")[-300:]).strip())
    reply = json.loads(p.stdout.split(marker, 1)[1])
    for fact in reply.get("remember") or []:
        PluginAPI(name).remember(fact)
    if not reply.get("ok"):
        log(f"{action}-error", name, reply.get("trace", "") or reply.get("error", ""))
        raise RuntimeError(reply.get("error") or "the plugin failed")
    return reply


def _proxy(path: Path, action: str, item: str):
    def call(*args, **kwargs):
        arg = kwargs if kwargs else (args[0] if args else "")
        return _call(path, action, item, arg, HOOK_TIMEOUT if action == "hook" else TIMEOUT)["result"]
    return call


def load_all(force: bool = False) -> None:
    global _loaded
    with _lock:
        if _loaded and not force:
            return
        _commands.clear(); _tools.clear(); _hooks.clear(); _status.clear()
        if DIR.exists():
            st = _state()
            for path in sorted(DIR.glob("*.py")):
                if not path.name.startswith("_"):
                    _load_file(path, st)
        _loaded = True


# ── using plugins ───────────────────────────────────────────────────────────

def run_command(text: str) -> str | None:
    """If the message starts with a plugin's command word, run it."""
    load_all()
    word, _, rest = (text or "").strip().partition(" ")
    cmd = _commands.get(word.lower())
    if not cmd:
        return None
    try:
        out = cmd["fn"](rest.strip())
        return str(out) if out is not None else "(done)"
    except Exception as e:
        log("command-error", cmd["plugin"], traceback.format_exc()[-800:])
        return f"The {cmd['plugin']} plugin hit an error: {type(e).__name__}: {e}"


def tools() -> dict[str, dict]:
    load_all()
    return dict(_tools)


def message_context(text: str) -> str:
    """Extra context from plugins' on_message hooks (each guarded, short)."""
    load_all()
    out = []
    for h in list(_hooks):
        try:
            r = h["fn"](text)
            if r:
                out.append(f"[{h['plugin']}] {str(r)[:800]}")
        except Exception:
            log("hook-error", h["plugin"], traceback.format_exc()[-500:])
    return "\n".join(out)


def install(name: str, code: str, reason: str = "") -> str:
    """Save an approved plugin and load it."""
    name = re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")[:30] or "plugin"
    with _lock:
        DIR.mkdir(parents=True, exist_ok=True)
        (DIR / f"{name}.py").write_text(code, encoding="utf-8")
        st = _state()
        st[name] = {"approved_hash": fingerprint(code), "enabled": True, "installed": time.strftime("%Y-%m-%d %H:%M"),
                    "reason": reason[:300]}
        _save_state(st)
        log("installed", name, reason)
        _unload(name)
        _load_file(DIR / f"{name}.py", st)
    s = _status.get(name, {})
    if s.get("loaded"):
        bits = []
        if s.get("commands"):
            bits.append("commands: " + ", ".join(s["commands"]))
        if s.get("tools"):
            bits.append("tools: " + ", ".join(s["tools"]))
        return f"Installed **{name}**" + (f" — {'; '.join(bits)}" if bits else "") + "."
    return f"Saved {name}, but it didn't load: {s.get('error', 'unknown error')}"


def approve_existing(name: str) -> str:
    """Approve a plugin file the person put in the folder (or changed) themselves."""
    path = DIR / f"{name}.py"
    if not path.exists():
        return f"No plugin file called {name}.py in {DIR}"
    return install(name, path.read_text(encoding="utf-8"), "approved by hand")


def set_enabled(name: str, on: bool) -> str:
    with _lock:
        st = _state()
        if name not in st:
            return f"No plugin called {name}. See yours with: plugins"
        st[name]["enabled"] = on
        _save_state(st)
        log("enabled" if on else "disabled", name)
        _unload(name)
        path = DIR / f"{name}.py"
        if on and path.exists():
            _load_file(path, st)
    return f"{name} is {'on' if on else 'off'}."


def remove(name: str) -> str:
    with _lock:
        st = _state()
        path = DIR / f"{name}.py"
        if not path.exists() and name not in st:
            return f"No plugin called {name}."
        _unload(name)
        if path.exists():
            path.unlink()
        st.pop(name, None)
        _save_state(st)
        log("removed", name)
    return f"Removed {name}."


def show(name: str) -> str:
    path = DIR / f"{name}.py"
    if not path.exists():
        return f"No plugin called {name}."
    code = path.read_text(encoding="utf-8")
    info = _state().get(name, {})
    return (f"**{name}** — installed {info.get('installed', '?')}" +
            (f"\nWhy: {info['reason']}" if info.get("reason") else "") +
            f"\n\n```python\n{code[:6000]}\n```")


def listing() -> str:
    load_all()
    if not _status:
        return ("No plugins yet. Ask Cursiv to grow a new ability:\n"
                "  evolve a command that converts recipe amounts between cups and grams\n"
                "You review the code and approve it before anything is installed.")
    rows = []
    for name, s in sorted(_status.items()):
        if s.get("loaded"):
            extra = ", ".join(s.get("commands", []) + [f"tool:{t}" for t in s.get("tools", [])])
            rows.append(f"- ✅ **{name}** — {s.get('description', '')}" + (f" ({extra})" if extra else ""))
        else:
            rows.append(f"- ⏸ **{name}** — {s.get('error', '')}")
    return ("Your plugins:\n" + "\n".join(rows) +
            "\n\nManage: plugin show/off/on/remove <name> · New ability: evolve <idea>")

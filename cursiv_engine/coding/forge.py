"""
Cursiv Forge: `evolve <idea>` -- Cursiv writes a plugin that gives itself a new
ability, checks it, tests it in a sandbox, and installs it only when the
person approves.

  1. The coding engine writes a plugin against the real plugin interface
     (PLUGIN_GUIDE below -- the same one core/plugins.py loads).
  2. Safety check: no running programs, no network, no deleting/moving files,
     no dynamic code, files only inside the plugin's own data folder.
  3. Sandbox test: register() + each command + the plugin's self_test() run in
     a separate Python process, in an empty temp folder, with a time limit.
  4. On failure it shows the model the error and asks for a fix (2 rounds).
  5. The person reads the code + summary, then `evolve approve` installs it
     (fingerprinted; changes later require re-approval) or `evolve discard`.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Generator

from cursiv_engine.coding import runner

PENDING = Path.home() / ".cursiv" / "plugins" / "_pending.json"

PLUGIN_GUIDE = '''You write Cursiv plugins: one Python file that gives Cursiv a new ability. Use ONLY the Python standard
library and ONLY this interface (it is exactly what Cursiv loads):

```python
PLUGIN = {"name": "short_snake_name", "description": "One sentence: what it adds", "version": "1"}

def register(cursiv):
    # A chat command: when a message starts with the word, fn(rest_of_message) runs and its returned string is shown.
    cursiv.add_command("word", fn, "word <args> -- what it does")
    # A tool the AI can call while answering (read-only lookups/calculations). fn(**args) -> str
    cursiv.add_tool("tool_name", fn, "What it returns. args: {\\"x\\": \\"...\\"}")
    # Optional: add a line of context to replies. fn(message_text) -> str or None (keep it fast)
    cursiv.on_message(fn)
    # Helpers: cursiv.data_dir() -> pathlib.Path folder this plugin may save files in
    #          cursiv.remember("a fact") -> saves to the person's memory;  cursiv.person() -> their name

def self_test():
    # REQUIRED: assert that your functions work, using sample inputs. No network, no user files.
    ...
```

Rules (a safety check enforces them -- code that breaks them is rejected):
- No subprocess/os.system/eval/exec/ctypes/winreg, no network (socket, urllib, requests, http), no installs.
- Never delete, move or rename files. Only write files inside cursiv.data_dir().
- Command words: one lowercase word that isn't a built-in Cursiv command (help, codex, council, remember, agent,
  tone, style, plugin(s), evolve, projects, search, memory...).
- Every function returns a helpful string, handles bad input with a friendly message, never raises.
- Keep it small and focused on the one idea.

Reply with: one sentence saying what the plugin does, then the complete file in ONE ```python block.'''

_DANGER = [
    (r"\b(subprocess|ctypes|winreg|_winapi|pty|socket|requests|httpx|aiohttp|urllib|http\.client|ftplib|smtplib|"
     r"paramiko|webbrowser|multiprocessing)\b", "runs programs, uses the network or system internals"),
    (r"\bos\.(system|popen|exec\w*|spawn\w*|remove|unlink|rmdir|removedirs|rename|replace|chmod|chown|kill|startfile)\b|"
     r"\bshutil\.(rmtree|move|copy\w*|chown)\b|\.(unlink|rmdir|rename|replace)\(", "deletes, moves or changes files"),
    (r"\b(eval|exec|compile|__import__)\s*\(|\bimportlib\b", "runs dynamic code"),
    (r"\bpip\b|ensurepip|setuptools", "installs packages"),
]


def check(code: str) -> tuple[bool, str]:
    for pat, why in _DANGER:
        if re.search(pat, code):
            return False, f"it {why}"
    if re.search(r"open\([^)]*['\"]\s*,\s*['\"][wax+]", code) or re.search(r"\.write_(text|bytes)\(", code):
        if "data_dir()" not in code:
            return False, "it writes files outside its own data folder"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"it has a syntax error on line {e.lineno}: {e.msg}"
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if "register" not in names:
        return False, "it has no register(cursiv) function"
    if "self_test" not in names:
        return False, "it has no self_test() function"
    if plugin_meta(code) is None:
        return False, "it has no PLUGIN = {...} description"
    return True, ""


def plugin_meta(code: str) -> dict | None:
    try:
        for node in ast.parse(code).body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "PLUGIN" for t in node.targets):
                meta = ast.literal_eval(node.value)
                if isinstance(meta, dict) and meta.get("name"):
                    return meta
    except Exception:
        pass
    return None


_HARNESS = r'''
import json, sys, traceback, importlib.util, pathlib
out = {"ok": False, "commands": [], "tools": [], "hooks": 0, "error": ""}
class API:
    def __init__(s): s.cmds, s.tools, s.hooks = {}, {}, []
    def add_command(s, w, fn, help=""): s.cmds[w] = (fn, help)
    def add_tool(s, n, fn, d): s.tools[n] = (fn, d)
    def on_message(s, fn): s.hooks.append(fn)
    def data_dir(s):
        p = pathlib.Path("plugin_data"); p.mkdir(exist_ok=True); return p
    def remember(s, f): pass
    def person(s): return "tester"
try:
    spec = importlib.util.spec_from_file_location("p", "plugin.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    api = API(); m.register(api)
    out["commands"] = list(api.cmds); out["tools"] = list(api.tools); out["hooks"] = len(api.hooks)
    for w, (fn, h) in api.cmds.items():
        r = fn("")
        if not isinstance(r, str): raise TypeError(f"command {w!r} returned {type(r).__name__}, not text")
    for fn in api.hooks:
        fn("hello, how are you?")
    m.self_test()
    out["ok"] = True
except Exception:
    out["error"] = traceback.format_exc()[-1500:]
print("@@RESULT@@" + json.dumps(out))
'''


def sandbox_test(code: str, timeout: int = 25) -> tuple[bool, str, dict]:
    exe = runner._python()
    if not exe:
        return False, "No Python found on this computer to test with (install it from python.org).", {}
    with tempfile.TemporaryDirectory(prefix="cursiv_forge_") as tmp:
        Path(tmp, "plugin.py").write_text(code, encoding="utf-8")
        Path(tmp, "harness.py").write_text(_HARNESS, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASS", k, re.I)}
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            p = subprocess.run([exe, "harness.py"], cwd=tmp, capture_output=True, text=True, timeout=timeout,
                               env=env, stdin=subprocess.DEVNULL, creationflags=0x08000000 if os.name == "nt" else 0)
        except subprocess.TimeoutExpired:
            return False, f"The test took longer than {timeout} seconds (an endless loop?).", {}
        m = re.search(r"@@RESULT@@(.*)", p.stdout or "")
        if not m:
            return False, ((p.stderr or p.stdout or "no output")[-1500:]).replace(tmp, "."), {}
        res = json.loads(m.group(1))
        return res["ok"], res.get("error", "").replace(tmp, "."), res


def evolve(idea: str, generate: Callable[[list[dict]], Generator[str, None, None]],
           context: str = "", rounds: int = 2) -> Generator[str, None, None]:
    """Stream the whole Forge process. `generate(messages)` streams a model reply."""
    msgs = [{"role": "system", "content": PLUGIN_GUIDE + (f"\n\n## Context about this person\n{context}" if context else "")},
            {"role": "user", "content": f"Write a Cursiv plugin for this idea: {idea}"}]
    code = None
    for attempt in range(rounds + 1):
        parts = []
        for chunk in generate(msgs):
            parts.append(chunk)
            yield chunk
        reply = "".join(parts)
        code = runner.extract_python(reply)
        if not code:
            problem = "There was no ```python block with the plugin file."
        else:
            ok, why = check(code)
            if not ok:
                problem = f"The safety check rejected it: {why}."
            else:
                yield "\n\n---\n🔬 **Testing in a sandbox…**\n"
                passed, err, res = sandbox_test(code)
                if passed:
                    meta = plugin_meta(code) or {}
                    PENDING.parent.mkdir(parents=True, exist_ok=True)
                    PENDING.write_text(json.dumps({"name": meta.get("name", "plugin"), "code": code, "idea": idea,
                                                   "description": meta.get("description", "")}), encoding="utf-8")
                    bits = []
                    if res.get("commands"):
                        bits.append("adds the command" + ("s " if len(res["commands"]) > 1 else " ") +
                                    ", ".join(f"`{c}`" for c in res["commands"]))
                    if res.get("tools"):
                        bits.append("gives the AI the tool" + ("s " if len(res["tools"]) > 1 else " ") +
                                    ", ".join(f"`{t}`" for t in res["tools"]))
                    if res.get("hooks"):
                        bits.append("adds context to replies")
                    yield (f"✅ **Passed** the safety check and its own tests.\n\n"
                           f"**{meta.get('name', 'plugin')}** — {meta.get('description', '')}\n"
                           f"It {' and '.join(bits) or 'loads cleanly'}.\n\n"
                           "Read the code above. Nothing is installed yet.\n"
                           "**Type `evolve approve` to install it**, or `evolve discard` to throw it away.")
                    return
                problem = f"The sandbox test failed:\n```\n{err[-1200:]}\n```"
        if attempt == rounds:
            yield f"\n\n---\n⚠️ Couldn't make a working, safe plugin for that after {rounds + 1} tries. {problem}\n" \
                  "Try describing the idea more simply, or as smaller pieces."
            return
        yield f"\n\n---\n🔧 {problem}\nFixing it (round {attempt + 1})…\n\n"
        msgs = msgs + [{"role": "assistant", "content": reply},
                       {"role": "user", "content": f"{problem}\nFix it and give the complete corrected file in one ```python block."}]


def pending() -> dict | None:
    try:
        return json.loads(PENDING.read_text(encoding="utf-8"))
    except Exception:
        return None


def approve() -> str:
    p = pending()
    if not p:
        return "There's no plugin waiting for approval. Make one with: evolve <idea>"
    ok, why = check(p["code"])                     # re-check what's on disk before installing
    if not ok:
        PENDING.unlink(missing_ok=True)
        return f"Not installed: the waiting plugin no longer passes the safety check ({why})."
    from cursiv_engine.core import plugins
    msg = plugins.install(p["name"], p["code"], p.get("idea", ""))
    PENDING.unlink(missing_ok=True)
    return msg + "\nSee all plugins with: plugins"


def discard() -> str:
    if PENDING.exists():
        PENDING.unlink()
        return "Discarded. Nothing was installed."
    return "There's no plugin waiting."

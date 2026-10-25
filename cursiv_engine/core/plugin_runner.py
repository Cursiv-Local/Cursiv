"""
Runs one plugin call in its own process (U98). Standard library only.

Cursiv never imports a plugin into itself any more: a plugin could otherwise read
the unlocked conversations, memories and keys in Cursiv's memory. Each call starts
this runner (`Cursiv.exe --plugin-runner`, or this file with Python from source),
which reads one JSON request on stdin and prints one JSON reply.

Before the plugin is imported, an audit hook (PEP 578, which Python code cannot
remove) refuses network access, starting programs, native code (ctypes), the
Windows registry, and opening files outside the plugin's own data folder and
Python's library. This is defence in depth, not an operating-system sandbox: the
process still runs as the same Windows user, so plugins stay "review before you
approve".

Request:  {"path": plugin.py, "data_dir": folder, "action": "register"|"command"|"tool"|"hook",
           "name": word/tool, "arg": text or {kwargs}, "person": "..."}
Reply:    {"ok": bool, "result": str|None, "commands": {word: help}, "tools": {name: description},
           "hooks": n, "remember": [facts], "meta": {...}, "error": str}
"""
from __future__ import annotations

import json
import os
import sys
import traceback

_BLOCKED_EVENTS = ("socket.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile",
                   "os.fork", "os.kill", "ctypes.", "winreg.", "_winapi.", "msvcrt.", "urllib.", "http.",
                   "ftplib.", "smtplib.", "webbrowser.", "os.add_dll_directory")
_BLOCKED_MODULES = {"ctypes", "_ctypes", "socket", "_socket", "ssl", "_ssl", "subprocess", "_posixsubprocess",
                    "multiprocessing", "winreg", "_winreg", "_winapi", "urllib.request", "http.client", "ftplib",
                    "smtplib", "webbrowser", "asyncio"}


def _sandbox(allowed_dirs: list[str]) -> None:
    roots = [os.path.normcase(os.path.realpath(d)) for d in allowed_dirs if d]

    def inside(path) -> bool:
        try:
            p = os.path.normcase(os.path.realpath(os.fsdecode(path)))
        except (TypeError, ValueError):
            return False
        return any(p == r or p.startswith(r.rstrip("\\/") + os.sep) for r in roots)

    def hook(event, args):
        if event.startswith(_BLOCKED_EVENTS):
            raise PermissionError(f"plugins may not do this ({event})")
        if event == "import" and args and str(args[0]) in _BLOCKED_MODULES:
            raise PermissionError(f"plugins may not import {args[0]}")
        if event in ("open", "io.open_code") and args and isinstance(args[0], (str, bytes, os.PathLike)):
            if not inside(args[0]):
                raise PermissionError("plugins may only open files in their own data folder")
        if event in ("os.remove", "os.rename", "os.rmdir", "os.mkdir", "shutil.rmtree", "os.chmod", "os.listdir",
                     "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
            if not inside(args[0]):
                raise PermissionError("plugins may only touch files in their own data folder")

    sys.addaudithook(hook)


class _API:
    def __init__(self, person: str, data_dir: str):
        self.commands, self.tools, self.hooks, self.remembered = {}, {}, [], []
        self._person, self._data = person, data_dir

    def add_command(self, word, fn, help=""):
        self.commands[str(word).strip().lower()] = (fn, help or word)

    def add_tool(self, name, fn, description):
        self.tools[str(name).strip().lower()] = (fn, description)

    def on_message(self, fn):
        self.hooks.append(fn)

    def remember(self, fact):
        self.remembered.append(str(fact)[:500])

    def person(self):
        return self._person

    def data_dir(self):
        from pathlib import Path
        return Path(self._data)


def run(request: dict) -> dict:
    out = {"ok": False, "result": None, "commands": {}, "tools": {}, "hooks": 0, "remember": [], "meta": {}, "error": ""}
    try:
        path, data = request["path"], request["data_dir"]
        os.makedirs(data, exist_ok=True)
        os.chdir(data)
        code = open(path, encoding="utf-8").read()
        library = [os.path.dirname(os.__file__), sys.prefix, sys.base_prefix,
                   getattr(sys, "_MEIPASS", ""), os.path.dirname(sys.executable)]
        _sandbox([data, os.path.dirname(path)] + library)
        module = {"__name__": "cursiv_plugin", "__file__": path}
        exec(compile(code, path, "exec"), module)
        if not callable(module.get("register")):
            raise RuntimeError("the plugin has no register(cursiv) function")
        api = _API(request.get("person", ""), data)
        module["register"](api)
        out["commands"] = {w: str(h) for w, (_, h) in api.commands.items()}
        out["tools"] = {n: str(d) for n, (_, d) in api.tools.items()}
        out["hooks"] = len(api.hooks)
        meta = module.get("PLUGIN") or {}
        out["meta"] = {k: str(v)[:200] for k, v in meta.items()} if isinstance(meta, dict) else {}
        action, name, arg = request.get("action", "register"), request.get("name", ""), request.get("arg", "")
        if action == "command":
            r = api.commands[name][0](str(arg))
            out["result"] = "(done)" if r is None else str(r)
        elif action == "tool":
            fn = api.tools[name][0]
            r = fn(**arg) if isinstance(arg, dict) else fn(arg)
            out["result"] = "" if r is None else str(r)
        elif action == "hook":
            parts = [str(r)[:800] for r in (h(str(arg)) for h in api.hooks) if r]
            out["result"] = "\n".join(parts)
        elif action == "selftest":                    # Forge: try a new plugin before anyone approves it
            for word, (fn, _) in api.commands.items():
                r = fn("")
                if not isinstance(r, str):
                    raise TypeError(f"command {word!r} returned {type(r).__name__}, not text")
            for fn in api.hooks:
                fn("hello, how are you?")
            if callable(module.get("self_test")):
                module["self_test"]()
        out["remember"] = api.remembered
        out["ok"] = True
    except BaseException as exc:                 # report everything; the parent decides
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
        out["trace"] = traceback.format_exc()[-800:]
    return out


def main() -> int:
    request = json.loads(sys.stdin.read() or "{}")
    reply = run(request)
    sys.stdout.write("@@CURSIV-PLUGIN@@" + json.dumps(reply)[:200_000])
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())

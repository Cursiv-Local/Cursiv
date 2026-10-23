"""
Network audit for a fresh install (AUDIT-2026-10-17 C-009 / C-011, Test J).

Copies this source tree into an empty scratch folder (so its .cursiv is empty),
points the home folder at another empty one (no keys, no memory, default
settings), then runs real chat() turns against the real local Ollama. An audit
hook logs every socket connection and DNS lookup the process makes, and every
request asking Ollama to download a model (Ollama makes that download itself,
so the hook alone wouldn't see it).

    py -3.13 scripts/net_audit.py               # default settings
    py -3.13 scripts/net_audit.py --offline     # also with offline mode on

Exit code 0 means zero connections off this computer and no model downloads.
Nothing is blocked; this only watches.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TURNS = [
    "What should we stock up on this week?",
    "Is the creek safe to drink from right now? We live near a cattle farm.",
    "hey, how are you doing?",
]


def child(offline: bool) -> int:
    import time
    import urllib.request

    log: list[str] = []

    def hook(event, args):
        if event in ("socket.connect", "socket.sendto"):
            addr = args[1]
            host = addr[0] if isinstance(addr, tuple) else None
        elif event in ("socket.getaddrinfo", "socket.gethostbyname"):
            host, addr = args[0], args[0]
        else:
            return
        from cursiv_engine.core import netgate
        if not netgate.is_local(host):
            log.append(f"{event} {addr}")

    sys.addaudithook(hook)
    sys.path.insert(0, str(Path.cwd()))
    sys.path.insert(0, str(Path.cwd() / "launcher"))
    for m in ("codex_tool_bridge", "knowledge_brain"):
        sys.modules.setdefault(m, None)

    real_urlopen = urllib.request.urlopen

    def watched(req, *a, **k):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/api/pull" in url:
            log.append(f"model download requested via {url}")
        return real_urlopen(req, *a, **k)

    urllib.request.urlopen = watched

    from cursiv_engine.core import netgate
    if offline:
        netgate.set_offline(True)
    from cursiv_engine.ui import chat_app as ca
    print(f"  .cursiv: {netgate.CONFIG_FILE.parent}  home: {Path.home()}")
    print(f"  offline={netgate.is_offline()} web_search_auto={netgate.setting('web_search_auto')} "
          f"local model ready={ca._local_model_ready()}")
    history: list[dict] = []
    for text in TURNS:
        out = "".join(ca.chat(text, history, "", None))
        history += [{"role": "user", "content": text}, {"role": "assistant", "content": out}]
        first = " ".join(out.split())[:90]
        print(f"  > {text}\n    {first}...")
    time.sleep(8)                     # background learning / embedding threads
    print(f"  connections off this computer: {len(log)}")
    for line in log:
        print(f"    {line}")
    return 1 if log else 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        return child(offline="--offline" in sys.argv)
    modes = [False, True] if "--offline" in sys.argv else [False]
    worst = 0
    for offline in modes:
        scratch = Path(tempfile.mkdtemp(prefix="cursiv_netaudit_"))
        try:
            for part in ("cursiv_engine", "launcher", "services"):
                if (REPO / part).exists():
                    shutil.copytree(REPO / part, scratch / "app" / part,
                                    ignore=shutil.ignore_patterns("__pycache__", ".cursiv"))
            home = scratch / "home"
            home.mkdir()
            env = {**os.environ, "USERPROFILE": str(home), "HOME": str(home),
                   "QT_QPA_PLATFORM": "offscreen", "PYTHONDONTWRITEBYTECODE": "1"}
            for k in ("BRAVE_API_KEY", "XAI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                      "CURSIV_RELAY_URL", "CURSIV_FLEET_TOKEN"):
                env.pop(k, None)
            print(f"== fresh install, {'offline mode ON' if offline else 'default settings'}")
            args = [sys.executable, str(Path(__file__).resolve()), "--child"] + (["--offline"] if offline else [])
            rc = subprocess.run(args, cwd=scratch / "app", env=env).returncode
            print("   PASS" if rc == 0 else "   FAIL")
            worst = max(worst, rc)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    return worst


if __name__ == "__main__":
    sys.exit(main())

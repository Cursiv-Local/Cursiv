"""
Run-and-fix: Cursiv runs the Python it just wrote, and if it crashes, shows the
model the error and asks for a corrected version (up to a few rounds).

Safety: code only runs automatically if a static check finds nothing risky
(no deleting/moving files, no shell/subprocess, no network, no installs, no
reading outside its own temp folder). It runs in a fresh temp folder with a
time limit and is never given the user's files. Programs that open windows,
wait for input or run forever are skipped (they can't be judged by a test run).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Generator

_BLOCK_RE = re.compile(r"```(?:python|py)[ \t]*\n(.*?)```", re.S | re.I)

_DANGER = [
    (r"\b(os\.(remove|unlink|rmdir|removedirs|rename|replace|chmod|chown|kill|system|popen|exec\w*|spawn\w*)|"
     r"shutil\.(rmtree|move|copy\w*)|pathlib\.Path\([^)]*\)\.(unlink|rmdir|rename|replace|write_\w+))", "changes files or runs programs"),
    (r"\bsubprocess\b|\bpty\b|\bctypes\b|\bwinreg\b|\b_winapi\b", "runs other programs / system calls"),
    (r"\b(socket|requests|urllib|http\.client|httpx|aiohttp|ftplib|smtplib|paramiko|websocket)\b", "uses the network"),
    (r"\bpip\b|ensurepip|setuptools", "installs packages"),
    (r"\b(eval|exec|compile|__import__)\s*\(", "runs dynamic code"),
    (r"open\([^)]*['\"]\s*,\s*['\"][wa+]", "writes files"),
    (r"['\"](/|[A-Za-z]:\\\\|~)", "uses absolute paths"),
]
_NOT_TESTABLE = [
    (r"\binput\s*\(", "waits for keyboard input"),
    (r"\b(tkinter|PyQt\d|PySide\d|pygame|turtle|cv2\.imshow|matplotlib\.pyplot\.show|plt\.show|"
     r"p\.connect\(\s*p\.GUI|pybullet\.GUI|\.GUI\b|flask|fastapi|uvicorn|gradio|streamlit)", "opens a window or server"),
    (r"while\s+True\s*:", "runs forever"),
]


def extract_python(text: str) -> str | None:
    """The main Python block of an answer (the longest one)."""
    blocks = [b for b in _BLOCK_RE.findall(text or "") if b.strip()]
    if not blocks:
        return None
    return max(blocks, key=len)


def check(code: str) -> tuple[bool, str]:
    """(ok_to_auto_run, reason_if_not)."""
    for pat, why in _DANGER:
        if re.search(pat, code):
            return False, f"it {why}, so I didn't run it automatically"
    for pat, why in _NOT_TESTABLE:
        if re.search(pat, code):
            return False, f"it {why}, so a test run can't judge it -- run it yourself"
    return True, ""


def _python() -> str | None:
    """A real Python interpreter (the frozen Cursiv.exe is not one)."""
    if not getattr(sys, "frozen", False):
        return sys.executable
    for name in ("python", "py", "python3"):
        exe = shutil.which(name)
        if exe and "WindowsApps" not in exe:          # skip the Microsoft Store stub
            return exe
    return None


def run(code: str, timeout: int = 20) -> tuple[bool, str]:
    """(success, output). Runs in an empty temp folder with a time limit."""
    exe = _python()
    if not exe:
        return False, "NO_PYTHON"
    with tempfile.TemporaryDirectory(prefix="cursiv_run_") as tmp:
        path = os.path.join(tmp, "main.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        env = {k: v for k, v in os.environ.items() if not re.search(r"KEY|TOKEN|SECRET|PASS", k, re.I)}
        env["PYTHONIOENCODING"] = "utf-8"
        flags = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW
        try:
            p = subprocess.run([exe, path], cwd=tmp, capture_output=True, text=True, timeout=timeout,
                               env=env, creationflags=flags, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return False, f"TIMEOUT after {timeout}s"
        out = (p.stdout or "")[-3000:]
        err = (p.stderr or "")[-3000:].replace(tmp, ".")
        return p.returncode == 0, (out + ("\n" + err if err else "")).strip()


def _missing_module(output: str) -> str | None:
    m = re.search(r"No module named ['\"]([\w.]+)['\"]", output)
    return m.group(1).split(".")[0] if m else None


def run_and_fix(answer: str, regenerate: Callable[[str, str], Generator[str, None, None]],
                rounds: int = 2) -> Generator[str, None, None]:
    """After an answer: test-run its Python, and on errors stream a fixed version.
    `regenerate(code, error)` streams a corrected answer."""
    code = extract_python(answer)
    if not code or len(code.strip().splitlines()) < 2:
        return
    ok, why = check(code)
    if not ok:
        yield f"\n\n---\n*Test run skipped: {why}.*"
        return
    for attempt in range(rounds + 1):
        success, output = run(code)
        if output == "NO_PYTHON":
            yield "\n\n---\n*Test run skipped: no Python found on this computer (install it from python.org).*"
            return
        if success:
            shown = output[-800:] if output else "(no output)"
            yield f"\n\n---\n✅ **Tested — it runs.** Output:\n```\n{shown}\n```"
            return
        missing = _missing_module(output)
        if missing:
            yield (f"\n\n---\n*Test run: needs the `{missing}` package, which isn't installed in the Python I test with. "
                   f"Install it in your venv with `pip install {missing}` and run it yourself.*")
            return
        if attempt == rounds:
            yield f"\n\n---\n⚠️ **Still failing after {rounds} fixes.** Last error:\n```\n{output[-1200:]}\n```"
            return
        yield f"\n\n---\n🔧 **Test run failed — fixing it** (round {attempt + 1}):\n```\n{output[-800:]}\n```\n\n"
        parts = []
        for chunk in regenerate(code, output):
            parts.append(chunk)
            yield chunk
        fixed = "".join(parts)
        new_code = extract_python(fixed)
        if not new_code:
            return
        ok, why = check(new_code)
        if not ok:
            yield f"\n\n---\n*Test run skipped for the fix: {why}.*"
            return
        code = new_code

"""
Cursiv's coding brain -- what every coding answer is built from.

  * A focused coding system prompt (not Cursiv's whole persona prompt: the
    coding models echoed its councils and owner notes instead of coding).
  * Playbooks + known-error diagnosis for the question / pasted terminal text.
  * The person's environment, remembered from what they paste (WSL, PowerShell,
    venv names, OS) so steps match their machine.
  * Coding lessons learned from past sessions ("Josh's venv is ~/robot").
  * Relevant files from the current project folder (`codex project <folder>`).
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Callable

from cursiv_v215.coding import playbook
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

try:
    from cursiv_v215.memory.semantic import CURSIV_DIR
except Exception:                                   # pragma: no cover
    CURSIV_DIR = APP_DATA

PROFILE_FILE = CURSIV_DIR / "coding_profile.json"
LESSONS_FILE = CURSIV_DIR / "coding_lessons.jsonl"
_lock = threading.Lock()

CODING_SYSTEM = """You are Cursiv's coding engine, helping {name} on their own computer. You write complete, working code \
and -- just as important -- the exact steps to get it running on THEIR machine.

How to answer:
1. If they pasted terminal output, start with "What went wrong": explain each error line in plain words and give the exact fix. \
Use the KNOWN ERRORS section below when it matches -- it is correct.
2. For anything that must be installed or run, give a numbered checklist that leaves nothing out:
   - which terminal to use (PowerShell, WSL/Ubuntu, VS Code terminal) and which folder to `cd` into
   - one-time setup (system packages, creating the venv, installs)
   - EVERY-SESSION steps (e.g. activating the venv in each new terminal) -- say clearly that these repeat
   - the command to run, and what success looks like
   - a quick check that it worked
   One command per code block. Never `sudo pip`. Never invent commands, modules, flags or example scripts -- \
if unsure, say how to check.
3. Code: complete files (no "..." placeholders), with the filename above each block, then how to run it.
4. End with "If something goes wrong" listing the 2-3 most likely errors for this task and their fixes.
5. Match their environment (below). If you don't know their OS/terminal and it matters, give both versions briefly.
Be direct. No persona talk, no councils, no system status, no greetings -- just the help.
Ground truth below beats your memory when they disagree."""


# ── Environment profile ─────────────────────────────────────────────────────

_ENV_PATTERNS = [
    ("terminal", "WSL / Ubuntu (bash)", r"\w+@[\w-]+:(/mnt/[a-z]|~)[^\n]*\$"),
    ("terminal", "Windows PowerShell", r"^PS [A-Z]:\\"),
    ("terminal", "Windows cmd", r"^[A-Z]:\\[^>\n]*>"),
    ("terminal", "macOS (zsh)", r"\w+@[\w-]+ [^\n]*%\s"),
    ("python", "Python 3.14 (system, externally managed)", r"python3\.14/README\.venv"),
]


def _load_profile() -> dict:
    try:
        return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_profile(p: dict) -> None:
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_FILE.write_text(json.dumps(p, indent=2), encoding="utf-8")


def observe(text: str, person: str) -> None:
    """Remember environment facts visible in what the person pasted/typed."""
    if not text:
        return
    with _lock:
        prof = _load_profile()
        me = prof.setdefault(person, {})
        changed = False
        for key, label, pat in _ENV_PATTERNS:
            if re.search(pat, text, re.M):
                seen = me.setdefault(key, [])
                if label not in seen:
                    seen.append(label)
                    changed = True
        venvs = re.findall(r"python3?\s+-m\s+venv\s+([~$.\w/\\-]+)", text)
        venvs += re.findall(r"source\s+([~.\w/-]+)/bin/activate", text)
        venvs += re.findall(r"([~$.\w\\-]+)\\Scripts\\Activate(?:\.ps1|\.bat)?", text)
        for venv in venvs:
            if "path/to" in venv:
                continue
            if venv not in me.setdefault("venvs", []):
                me["venvs"].append(venv)
                changed = True
        if changed:
            me["venvs"] = me.get("venvs", [])[-5:]
            _save_profile(prof)


def environment(person: str) -> str:
    me = _load_profile().get(person, {})
    lines = []
    if me.get("terminal"):
        lines.append("Terminals they use: " + ", ".join(me["terminal"]))
    if me.get("python"):
        lines.append("Python: " + ", ".join(me["python"]))
    if me.get("venvs"):
        lines.append("Their venv(s): " + ", ".join(me["venvs"]) + " -- use these names in steps")
    return "\n".join(lines)


# ── Lessons ─────────────────────────────────────────────────────────────────

def _lessons() -> list[dict]:
    try:
        return [json.loads(l) for l in LESSONS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return []


def list_lessons(person: str) -> list[dict]:
    return [l for l in _lessons() if l.get("person") in (person, "family")]


def add_lesson(text: str, person: str, source: str = "manual") -> bool:
    text = " ".join((text or "").split())[:400]
    if len(text) < 8:
        return False
    with _lock:
        existing = _lessons()
        low = text.lower()
        if any(l["text"].lower() == low for l in existing):
            return False
        CURSIV_DIR.mkdir(parents=True, exist_ok=True)
        with LESSONS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"text": text, "person": person, "source": source, "t": time.time()}) + "\n")
    return True


def forget_lessons(words: str, person: str) -> list[str]:
    words = (words or "").lower().strip()
    if not words:
        return []
    with _lock:
        keep, gone = [], []
        for l in _lessons():
            (gone if l.get("person") == person and words in l["text"].lower() else keep).append(l)
        if gone:
            LESSONS_FILE.write_text("".join(json.dumps(l) + "\n" for l in keep), encoding="utf-8")
    return [g["text"] for g in gone]


_WORD = re.compile(r"[a-z0-9_+.-]{3,}")


def relevant_lessons(text: str, person: str, limit: int = 6) -> list[str]:
    q = set(_WORD.findall((text or "").lower()))
    scored = []
    for l in list_lessons(person):
        overlap = len(q & set(_WORD.findall(l["text"].lower())))
        scored.append((overlap, l.get("t", 0), l["text"]))
    scored.sort(key=lambda s: (-s[0], -s[1]))
    # always include the newest couple (they're about this person's setup), then the most relevant
    picked = [s[2] for s in scored if s[0] > 0][:limit]
    return picked


_LEARN_PROMPT = (
    "You maintain a short list of reusable coding lessons about {name}'s computer and projects, so future "
    "coding help fits their setup. From the exchange below, extract 0-3 lessons that will still be true later: "
    "their OS/terminal, venv names and paths, installed tools, project names/locations, errors they hit and the "
    "fix that worked, preferences (e.g. 'wants every step listed'). Skip generic programming facts anyone knows. "
    "Never guess. Each lesson: one short sentence. Reply with a JSON array of strings only, or []."
)


def learn_from_exchange(user_text: str, reply: str, ask: Callable[[list[dict]], str], person: str) -> list[str]:
    if len((user_text or "").strip()) < 15:
        return []
    msgs = [{"role": "system", "content": _LEARN_PROMPT.format(name=person.title())},
            {"role": "user", "content": f"User:\n{user_text[:3000]}\n\nAssistant:\n{(reply or '')[:3000]}"}]
    try:
        raw = ask(msgs) or ""
        m = re.search(r"\[.*\]", raw, re.S)
        items = json.loads(m.group(0)) if m else []
    except Exception:
        return []
    return [it for it in items[:3] if isinstance(it, str) and add_lesson(it, person, "learned")]


# ── Project folder ──────────────────────────────────────────────────────────

_CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".md", ".toml", ".yaml", ".yml",
             ".txt", ".sh", ".ps1", ".bat", ".c", ".cpp", ".h", ".rs", ".go", ".java", ".cs", ".sql", ".urdf", ".xml"}
_SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", ".next", ".cursiv",
              "site-packages", ".idea", ".vscode", "_internal"}


def set_project(folder: str, person: str) -> str:
    prof = _load_profile()
    me = prof.setdefault(person, {})
    if not folder or folder.lower() in ("off", "none", "clear"):
        me.pop("project", None)
        _save_profile(prof)
        return "Project folder cleared."
    p = Path(folder.strip().strip('"')).expanduser()
    if not p.is_dir():
        return f"I can't find the folder {p}"
    me["project"] = str(p.resolve())
    _save_profile(prof)
    files = list(_project_files(p))
    return f"Project set: {p.resolve()}  ({len(files)} code files). Codex answers will use the relevant files."


def project(person: str) -> str | None:
    return _load_profile().get(person, {}).get("project")


def _project_files(root: Path, cap: int = 2000):
    n = 0
    for path in root.rglob("*"):
        if n >= cap:
            break
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in _CODE_EXT and path.stat().st_size < 400_000:
            n += 1
            yield path


def project_context(query: str, person: str, budget: int = 9000) -> str:
    root = project(person)
    if not root or not Path(root).is_dir():
        return ""
    rootp = Path(root)
    q = set(_WORD.findall(query.lower()))
    scored = []
    files = list(_project_files(rootp))
    for f in files:
        rel = str(f.relative_to(rootp))
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        name_hits = sum(3 for w in q if w in rel.lower())
        body_hits = sum(1 for w in q if w in text.lower())
        scored.append((name_hits + body_hits, rel, text))
    scored.sort(key=lambda s: -s[0])
    tree = "\n".join(str(f.relative_to(rootp)) for f in files[:80])
    out = [f"Project folder: {root}\nFiles:\n{tree}"]
    used = len(out[0])
    for score, rel, text in scored[:6]:
        if score <= 0 or used > budget:
            break
        chunk = text[: max(0, min(4000, budget - used))]
        out.append(f"\n--- {rel} ---\n{chunk}")
        used += len(chunk) + len(rel) + 10
    return "\n".join(out)


# ── Worked examples ─────────────────────────────────────────────────────────
# Complete model answers (question -> every step + full code + "if something goes
# wrong"). The best match is shown to the model as the standard to meet. Built-in
# ones live in coding/examples/; ones you keep with `codex keep` go to
# .cursiv/coding_examples/ and are used the same way.

EXAMPLES_DIR = Path(__file__).parent / "examples"
USER_EXAMPLES_DIR = CURSIV_DIR / "coding_examples"


def _parse_example(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return None
    m = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", raw, re.S)
    if not m:
        return None
    meta = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
    return {"title": meta.get("title", path.stem), "triggers": meta.get("triggers", ""),
            "body": m.group(2).strip(), "user": path.parent == USER_EXAMPLES_DIR}


def all_examples() -> list[dict]:
    out = []
    for d in (EXAMPLES_DIR, USER_EXAMPLES_DIR):
        if d.is_dir():
            out += [e for e in (_parse_example(p) for p in sorted(d.glob("*.md"))) if e]
    return out


def best_examples(text: str, limit: int = 2, budget: int = 7000) -> list[dict]:
    words = set(_WORD.findall((text or "").lower()))
    scored = []
    for ex in all_examples():
        hits = 0
        if ex["triggers"]:
            try:
                hits = 3 * len(re.findall(ex["triggers"], text, re.I))
            except re.error:
                pass
        hits += len(words & set(_WORD.findall(ex["title"].lower())))
        if ex["user"]:
            hits += 1                                      # your own examples win ties
        if hits >= 3:
            scored.append((hits, ex))
    scored.sort(key=lambda s: -s[0])
    picked, used = [], 0
    for _h, ex in scored[:limit]:
        if picked and used + len(ex["body"]) > budget:
            break
        picked.append(ex)
        used += len(ex["body"])
    return picked


def keep_example(question: str, answer: str, person: str) -> str:
    """Save a good answer as a worked example Cursiv will imitate later."""
    question, answer = (question or "").strip(), (answer or "").strip()
    if not question or not answer:
        return "There's no coding answer to keep yet — ask a coding question first."
    USER_EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    title = " ".join(question.split())[:80]
    words = [w for w in _WORD.findall(question.lower()) if len(w) > 3][:8]
    triggers = "|".join(re.escape(w) for w in words) or re.escape(title.lower()[:20])
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:50] or "example"
    path = USER_EXAMPLES_DIR / f"{slug}_{int(time.time())}.md"
    path.write_text(f"---\ntitle: {title}\ntriggers: {triggers}\nperson: {person}\n---\n"
                    f"## Question\n{question}\n\n## Answer\n{answer}\n", encoding="utf-8")
    return f"Kept as a worked example — I'll answer questions like \"{title[:50]}\" to this standard."


# ── Putting it together ─────────────────────────────────────────────────────

_TERMINAL_RE = re.compile(
    r"\w+@[\w-]+:[~/][^\n]*\$|^PS [A-Z]:\\|^[A-Z]:\\[^>\n]*>|command not found|Traceback \(most recent call last\)|"
    r"^error:|^ERROR:|is not recognized as|No module named|Permission denied", re.M)


def looks_like_terminal(text: str) -> bool:
    return bool(_TERMINAL_RE.search(text or ""))


def context_block(text: str, history: list[dict] | None, person: str) -> str:
    """Ground truth for this coding question (goes under the coding system prompt)."""
    recent = " ".join(m.get("content", "") for m in (history or [])[-4:] if isinstance(m.get("content"), str))
    probe = text + "\n" + recent[-3000:]
    parts = []
    env = environment(person)
    if env:
        parts.append("## THEIR ENVIRONMENT\n" + env)
    diag = playbook.diagnose(text)
    if diag:
        parts.append("## KNOWN ERRORS in what they pasted (explain + fix these first)\n" +
                     "\n".join(f"- `{line}` -> {fix}" for line, fix in diag))
    books = playbook.match_playbooks(probe)
    if books:
        parts.append("## PLAYBOOKS (required steps -- include the ones that apply)\n" +
                     "\n\n".join(f"### {t}\n{b}" for t, b in books))
    examples = best_examples(text + "\n" + recent[-1000:])
    if examples:
        parts.append("## WORKED EXAMPLES (match this level of completeness and this format; adapt to their question)\n" +
                     "\n\n".join(f"### Example: {e['title']}\n{e['body']}" for e in examples))
    lessons = relevant_lessons(probe, person)
    if lessons:
        parts.append("## LESSONS FROM EARLIER SESSIONS\n" + "\n".join(f"- {l}" for l in lessons))
    proj = project_context(text, person)
    if proj:
        parts.append("## THEIR PROJECT\n" + proj)
    return "\n\n".join(parts)


def system_prompt(text: str, history: list[dict] | None, person: str) -> str:
    observe(text, person)
    name = person.title() if person and person != "family" else "the user"
    ctx = context_block(text, history, person)
    try:
        from cursiv_v215.core import style
        add = style.prompt_addendum(person)
        if add:
            ctx = (ctx + "\n\n" if ctx else "") + add
    except Exception:
        pass
    return CODING_SYSTEM.format(name=name) + ("\n\n" + ctx if ctx else "")


def build_messages(text: str, history: list[dict] | None, person: str, keep: int = 6) -> list[dict]:
    msgs = [{"role": "system", "content": system_prompt(text, history, person)}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in (history or [])[-keep:]
             if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    msgs.append({"role": "user", "content": text})
    return msgs

"""
Read-only access to Cursiv's own source code and documentation.

So Cursiv can explain how it works from what its code actually says, instead of
inventing internals. Run from source, the files are the checkout's; the packaged
app ships them as plain files in its `_internal` folder (launcher/build.spec). Only text files of the
kinds below, inside that folder, can be read -- never user data, keys or any other
folder. Every excerpt carries a label naming the file and lines it came from.

    self map [words]        where a job is done, from docs/CODE-MAP.md
    self source <words>     search the code and docs
    self read <path>        read a file (or self read <path> <first line>)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SUFFIXES = {".py", ".md", ".json", ".txt", ".spec", ".iss", ".toml"}
TOP = ("cursiv_engine", "launcher", "docs", "README.md", "TECH.md", "ARCHITECTURE.md", "CHANGELOG.md",
       "MODELS.md", "PRIVACY.md", "OFFLINE-DEMO.md")
SKIP_PARTS = {"__pycache__", ".cursiv", "licenses", "family", "tests"}
MAX_FILE = 400_000            # characters read from one file
MAX_LINES = 120               # lines returned by one read
MAX_SCAN = 25_000_000         # characters scanned by one search


def root() -> Path:
    if getattr(sys, "frozen", False):
        bundle=Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent / "_internal"))
        # PyInstaller places DATA under Resources on macOS, cross-linking it
        # into Frameworks. Read the real data root; keep rejecting linked files.
        if sys.platform=='darwin' and bundle.name=='Frameworks' and bundle.parent.name=='Contents':
            resources=bundle.parent/'Resources'
            if (resources/'cursiv_engine/core/own_source_index.json').is_file():
                return resources
        return bundle
    return Path(__file__).resolve().parent.parent.parent


def version() -> str:
    from .selfknow import VERSION
    return VERSION


def _allowed(path: Path, base: Path) -> bool:
    from . import self_index, turn_policy
    if not turn_policy.current().inspect:
        return False
    try:
        rel = path.absolute().relative_to(base.absolute()).as_posix()
        index = self_index.load(base,version())
        self_index.checked(base,rel)
    except (OSError,ValueError,TypeError,KeyError):
        return False
    return rel in index['files']


def files() -> list[str]:
    from . import self_index, turn_policy
    if not turn_policy.current().inspect:
        return []
    try:
        return sorted(self_index.load(root(),version())['files'])
    except (OSError,ValueError,TypeError,KeyError):
        return []


def label(rel: str, first: int, last: int) -> str:
    return f"Read from Cursiv's own source ({version()}): {rel}, lines {first}–{last}"


def _words(query: str) -> list[str]:
    stop = {"the", "and", "how", "does", "what", "why", "you", "your", "cursiv", "work", "works", "is", "are", "with",
            "for", "about", "this", "that", "from", "into", "when", "do", "did", "can", "of", "to", "in", "a", "it"}
    return [w for w in re.findall(r"[a-z_][a-z0-9_]{2,}", (query or "").lower()) if w not in stop][:8]


def search(query: str, limit: int = 8, *, kind: str = "") -> list[dict]:
    """Best-matching lines: {path, line, text, score}. Reads only allowed files, bounded."""
    words = _words(query)
    if not words:
        return []
    base, hits, scanned = root(), [], 0
    from . import self_index
    try:
        inventory=self_index.load(base,version())
    except (OSError,ValueError,TypeError,KeyError):
        return []
    for rel in files():
        try:
            text = self_index.text(base,inventory,rel)[:MAX_FILE]
        except (OSError,ValueError,TypeError,KeyError):
            continue
        scanned += len(text)
        if scanned > MAX_SCAN:
            break
        name_bonus = sum(w in rel.lower() for w in words)
        for n, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            score = sum(w in low for w in words)
            if score:
                hits.append({"path": rel, "line": n, "text": line.strip()[:200],
                             "score": score + 0.5 * name_bonus + (0.5 if line.lstrip().startswith(("def ", "class ", "#")) else 0)})
    hits.sort(key=lambda h: (-h["score"], h["path"], h["line"]))
    out, per_file = [], {}
    for h in hits:
        if per_file.get(h["path"], 0) >= 2:
            continue
        per_file[h["path"]] = per_file.get(h["path"], 0) + 1
        out.append(h)
        if len(out) >= limit:
            break
    from . import evidence_log
    for h in out:
        evidence_log.record(kind or evidence_log.SOURCE_SEARCH, "Cursiv's own source", path=h["path"], lines=str(h["line"]),
                            operation=f"search for {query!r}", scope="matching lines only, not whole files")
    return out


def read(rel: str, first: int = 1, count: int = MAX_LINES) -> tuple[str, str]:
    """(label, numbered text). Raises ValueError for anything outside Cursiv's own source."""
    base = root()
    rel = (rel or "").strip().strip("`'\"").replace("\\", "/")
    path = base / rel
    if not _allowed(path, base):
        raise ValueError(f"{rel or '(no path)'} isn't one of Cursiv's own source or documentation files.")
    from . import self_index
    lines = self_index.text(base,self_index.load(base,version()),rel)[:MAX_FILE].splitlines()
    first = max(1, int(first))
    chunk = lines[first - 1: first - 1 + max(1, min(count, MAX_LINES))]
    last = first + len(chunk) - 1
    body = "\n".join(f"{first + i:5}  {line}" for i, line in enumerate(chunk))
    from . import evidence_log
    evidence_log.record(evidence_log.SOURCE_READ, "Cursiv's own source", path=rel, lines=f"{first}-{max(first, last)}",
                        operation="read", scope="these lines only")
    return label(rel, first, max(first, last)), body


def excerpts(query: str, budget: int = 1800) -> str:
    """Short labelled source excerpts for a question about Cursiv, within `budget` characters.
    The code map's matching lines come first: they say which module does the job."""
    rows, used = [], 0
    for line in map_lines(query)[:3]:
        row = f"- {MAP} (code map): {line}"
        rows.append(row)
        used += len(row) + 1
    from . import evidence_log
    for h in search(query, limit=6, kind=evidence_log.SOURCE_SUPPLIED):
        row = f"- {h['path']}:{h['line']}: {h['text']}"
        if used + len(row) > budget:
            break
        rows.append(row)
        used += len(row) + 1
    if not rows:
        return ""
    return (f"Matching lines from Cursiv's own source ({version()}); each shows its file and line. "
            "They show what the code says, not that a feature ran:\n" + "\n".join(rows))


MAP = "docs/CODE-MAP.md"


def map_lines(query: str = "") -> list[str]:
    """Lines of the code map (every module, one line each, by job) that match the words;
    with no words, the section headings. The map is kept complete by tests/test_code_map.py."""
    try:
        from . import self_index, turn_policy
        if not turn_policy.current().inspect:
            return []
        text = self_index.text(root(),self_index.load(root(),version()),MAP)
    except (OSError,ValueError,TypeError,KeyError):
        return []
    if not query.strip():
        return [ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith(("## ", "### "))]
    words = _words(query)
    rows = [ln.strip("- ").strip() for ln in text.splitlines() if ln.startswith("- ")]
    scored = sorted(((sum(w in r.lower() for w in words), r) for r in rows), key=lambda x: -x[0])
    return [r for s, r in scored if s][:8]


def command(text: str) -> str | None:
    t = " ".join((text or "").split())
    low = t.lower()
    if low == "self map" or low.startswith("self map "):
        q = t[len("self map"):].strip()
        found = map_lines(q)
        if not found:
            return f"Nothing on Cursiv's code map matches “{q}”. Try: self source {q}" if q else \
                "Cursiv's code map isn't available in this copy."
        if not q:
            return ("Cursiv's code map (docs/CODE-MAP.md), by job:\n" + "\n".join(f"- {r}" for r in found) +
                    "\n\nFind where something lives: self map <words>")
        return (f"Where “{q}” lives in Cursiv ({version()}), from its code map:\n" +
                "\n".join(f"- {r}" for r in found) + "\n\nRead one: self read <path>")
    if low.startswith("self source"):
        q = t[len("self source"):].strip()
        if not q:
            return "Usage: self source <words>  (searches Cursiv's own code and docs)"
        found = search(q)
        if not found:
            return f"Nothing in Cursiv's source matches “{q}”."
        rows = [f"- `{h['path']}` line {h['line']}: {h['text']}" for h in found]
        return (f"Searched Cursiv's own source ({version()}, {len(files())} files) for “{q}”:\n" + "\n".join(rows) +
                "\n\nRead one: self read <path> <line>")
    if low.startswith("self read"):
        parts = t[len("self read"):].split()
        if not parts:
            return "Usage: self read <path> [first line]"
        first = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        try:
            where, body = read(parts[0], first)
        except (ValueError, OSError) as exc:
            return str(exc)
        return f"{where}\n```\n{body}\n```"
    return None

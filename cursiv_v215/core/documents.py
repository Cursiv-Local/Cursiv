"""
The team's own documents (research roadmap R3): protocols, SOPs, permits and field
guides, kept offline and quoted by page.

A document is imported once into ~/.cursiv/documents/: its text page by page, its
SHA-256 fingerprint (so anyone can confirm which version of a protocol was used),
the file name and the import date. The original file isn't modified or moved.

search() ranks passages (a page split into paragraphs) by how many of the question's
words they contain, weighted so rare words count more (BM25). It's deterministic and
needs no model, so the same question always finds the same passages. Answers cite
"(file name, p. N)"; cited_pages_problems() checks every cited page was among the
passages Cursiv actually supplied.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path

TEXT_TYPES = (".txt", ".md", ".csv")
TYPES = (".pdf",) + TEXT_TYPES


def lib_dir() -> Path:
    return Path.home() / ".cursiv" / "documents"


def _index_file() -> Path:
    return lib_dir() / "index.json"


def _load_index() -> list[dict]:
    try:
        return json.loads(_index_file().read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_index(items: list[dict]) -> None:
    from cursiv_v215.core import atomic
    atomic.write_text(_index_file(), json.dumps(items, indent=2, ensure_ascii=False))


def library() -> list[dict]:
    """Imported documents: id, name, fingerprint, pages, imported, path (where it came from)."""
    return _load_index()


def fingerprint(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _pages(path: Path) -> list[str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("reading PDFs needs the pypdf package") from exc
        reader = PdfReader(str(path))
        return [(page.extract_text() or "") for page in reader.pages]
    if suffix in TEXT_TYPES:
        text = path.read_text(encoding="utf-8", errors="replace")
        # Plain text has no pages: a form feed separates pages if present, else ~3,000 characters each.
        parts = text.split("\f") if "\f" in text else [text[i:i + 3000] for i in range(0, max(len(text), 1), 3000)]
        return parts or [""]
    raise ValueError(f"can't read {suffix} files; use PDF, TXT, MD or CSV")


def add(path: Path | str) -> dict:
    """Import a document. Importing the same file again (same fingerprint) changes nothing."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"no file at {path}")
    fp = fingerprint(path)
    items = _load_index()
    for d in items:
        if d["fingerprint"] == fp:
            return d
    pages = _pages(path)
    if not any(p.strip() for p in pages):
        raise ValueError("no text could be read from it (a scanned PDF needs text recognition first)")
    doc = {"id": fp[:12], "name": path.name, "fingerprint": fp, "pages": len(pages),
           "imported": time.strftime("%Y-%m-%d %H:%M"), "path": str(path)}
    from cursiv_v215.core import atomic
    atomic.write_text(lib_dir() / f"{doc['id']}.json", json.dumps({"pages": pages}, ensure_ascii=False))
    items.append(doc)
    _save_index(items)
    _passages.cache = None
    return doc


def remove(doc_id: str) -> bool:
    items = _load_index()
    keep = [d for d in items if d["id"] != doc_id]
    if len(keep) == len(items):
        return False
    _save_index(keep)
    (lib_dir() / f"{doc_id}.json").unlink(missing_ok=True)
    _passages.cache = None
    return True


# ── Search ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Passage:
    doc_id: str
    name: str
    page: int        # 1-based
    text: str


_STOP = frozenset("""a an the and or of to in on for with at by from is are was were be been it its this that these those
as if then than so but not no do does did can could should would will may might must how what which who when where
why i we you they he she my our your their me us them about into over under after before up down out""".split())


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", (text or "").lower()) if w not in _STOP and len(w) > 1]


def _passages() -> list[Passage]:
    if _passages.cache is None:
        out = []
        for d in _load_index():
            try:
                pages = json.loads((lib_dir() / f"{d['id']}.json").read_text(encoding="utf-8"))["pages"]
            except Exception:
                continue
            for n, page in enumerate(pages, 1):
                for para in [p.strip() for p in re.split(r"\n\s*\n", page) if p.strip()] or [page]:
                    # long paragraphs are split so a passage stays quotable
                    for i in range(0, len(para), 1200):
                        out.append(Passage(d["id"], d["name"], n, para[i:i + 1200]))
        _passages.cache = out
    return _passages.cache


_passages.cache = None


def search(question: str, limit: int = 3, min_cover: float = 0.4) -> list[Passage]:
    """The best passages for the question (BM25 order), or [] when nothing matches well.
    A passage counts only if it has at least two of the question's words and at least
    min_cover of them; BM25 scores on their own are too small to compare with a
    library of one or two documents."""
    q = set(_words(question))
    passages = _passages()
    if not q or not passages:
        return []
    docs = [_words(p.text) for p in passages]
    avg = sum(len(d) for d in docs) / len(docs) or 1
    df = {w: sum(1 for d in docs if w in d) for w in q}
    n = len(docs)
    scored = []
    for p, words in zip(passages, docs):
        if not words:
            continue
        counts = {}
        for w in words:
            if w in q:
                counts[w] = counts.get(w, 0) + 1
        if not counts:
            continue
        score = 0.0
        for w, tf in counts.items():
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(words) / avg))
        cover = len(counts) / len(q)
        if len(counts) < 2 or cover < min_cover:
            continue
        scored.append((score * cover, p))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [p for _s, p in scored[:limit]]


def prompt_block(found: list[Passage], only: bool) -> str:
    lines = ["## The team's documents",
             "Passages from documents the person imported. Use them for what they cover and cite each fact as "
             "(file name, p. N), exactly as labelled. Quote numbers and steps as written; don't add any."]
    if only:
        lines.append("Documents-only mode is on: answer ONLY from these passages. If they don't answer the question, "
                     "say it isn't in the documents. Don't use general knowledge.")
    else:
        lines.append("If they don't cover part of the question, say so before adding anything from general knowledge.")
    lines.append("")
    for p in found:
        lines.append(f"[{p.name}, p. {p.page}] {p.text}")
    return "\n".join(lines)


def note_line(found: list[Passage]) -> str:
    """What the person sees above the answer: which pages were used."""
    pages = []
    for p in found:
        label = f"{p.name} p. {p.page}"
        if label not in pages:
            pages.append(label)
    return "*(From your documents: " + "; ".join(pages) + ")*"


NOT_IN_DOCS = ("That isn't in your documents. (Documents-only mode is on, so I don't answer from general knowledge. "
               "Turn it off in Settings → How Cursiv answers, or import the document that covers this.)")

_CITE = re.compile(r"\(([^()]{1,120}?),\s*p(?:age|\.)?\s*(\d{1,4})\)", re.I)


def cited_pages_problems(answer: str, found: list[Passage]) -> list[str]:
    """Pages the answer cites that weren't among the passages supplied."""
    given = {(p.name.lower(), p.page) for p in found}
    names = {p.name.lower() for p in found}
    problems = []
    for name, page in _CITE.findall(answer or ""):
        key = (name.strip().lower(), int(page))
        if key[0] in names or any(key[0] in n or n in key[0] for n in names):
            match = next((n for n in names if key[0] in n or n in key[0]), key[0])
            if (match, key[1]) not in given:
                problems.append(f"cites {name.strip()} p. {page}, which wasn't among the pages used")
    return problems


def only_mode() -> bool:
    try:
        from cursiv_v215.chat import keys
        return keys.saved_key("documents_only") == "on"
    except Exception:
        return False


def command(text: str) -> str | None:
    t = (text or "").strip()
    low = t.lower()
    if low in ("documents", "my documents", "list documents"):
        items = library()
        if not items:
            return ("No documents yet. Import protocols, SOPs or field guides in Memory & Knowledge → Documents, "
                    "or type: add document C:\\path\\to\\file.pdf")
        return "Your documents:\n" + "\n".join(
            f"- {d['name']} ({d['pages']} pages, imported {d['imported']}, fingerprint {d['fingerprint'][:16]})"
            for d in items)
    m = re.match(r"(?i)^(?:add|import) document\s+(.+)$", t)
    if m:
        try:
            d = add(m.group(1).strip().strip('"'))
        except (ValueError, OSError) as exc:
            return f"Not imported: {exc}."
        return f"Imported {d['name']}: {d['pages']} pages, fingerprint {d['fingerprint'][:16]}."
    return None

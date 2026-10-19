"""
Cursiv semantic memory -- memory that finds by meaning and learns.

  * Facts: short lasting things about a person ("Keiarra compares KJV and NIV",
    "Joshua prefers direct answers"), saved per person in .cursiv/memory_facts.jsonl.
    Person "family" = shared by everyone.
  * Recall: facts and saved strands are matched to the question by meaning, using
    a small local embedding model through Ollama (nomic-embed-text). Without it,
    recall falls back to word overlap -- nothing breaks.
  * Learning: after a conversation turn, the cheapest available AI (free Groq or
    Gemini key, else the local model -- never paid keys, never Cursiv Cloud)
    picks out lasting facts. Turn off with "memory learn off".

Everything stays in the user's .cursiv folder. Each fact is tagged with an
origin (user_said, inferred, verified) and a date. A preference never
overrides safety, and two conflicting facts are both shown. Commands:
remember <fact>, forget <words>, what do you remember, memory learn on|off.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable
from cursiv_v215.core import atomic as _atomic
from cursiv_v215.core.paths import APP_DATA   # where program data lives (core/paths.py)

ROOT = Path(__file__).parent.parent.parent
CURSIV_DIR = APP_DATA
FACTS_FILE = CURSIV_DIR / "memory_facts.jsonl"
EMB_CACHE_FILE = CURSIV_DIR / "embeddings_cache.json"
SETTINGS_FILE = CURSIV_DIR / "memory_settings.json"
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
SHARED = "family"

_lock = threading.Lock()
_person = SHARED
_emb_cache: dict[str, list[float]] | None = None
_embed_ok: bool | None = None          # None = not checked yet
_pulling = False


# ── People ──────────────────────────────────────────────────────────────────

def set_person(name: str) -> None:
    """Who is using Cursiv right now (the login name)."""
    global _person
    _person = (name or SHARED).strip().lower() or SHARED


def current_person() -> str:
    return _person


# ── Settings ────────────────────────────────────────────────────────────────

def _settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def learning_enabled() -> bool:
    return _settings().get("learn", True)


def set_learning(on: bool) -> None:
    s = _settings()
    s["learn"] = bool(on)
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    _atomic.write_text(SETTINGS_FILE, json.dumps(s, indent=2))


# ── Embeddings (local, through Ollama) ──────────────────────────────────────

def _load_cache() -> dict[str, list[float]]:
    global _emb_cache
    if _emb_cache is None:
        try:
            _emb_cache = json.loads(EMB_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _emb_cache = {}
    return _emb_cache


def _save_cache() -> None:
    try:
        CURSIV_DIR.mkdir(parents=True, exist_ok=True)
        _atomic.write_text(EMB_CACHE_FILE, json.dumps(_load_cache()))
    except Exception:
        pass


def _http(path: str, payload: dict | None = None, timeout: float = 30) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(OLLAMA + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _downloads_allowed() -> bool:
    """Ollama fetches the model from the internet: not while offline mode is on
    (core/netgate.py). Word-overlap recall is used instead."""
    try:
        from cursiv_v215.core import netgate
        return netgate.allowed()
    except Exception:
        return False


def _pull_embed_model() -> None:
    """Download the small embedding model (~270 MB). Only Setup calls this, when the
    person downloads a chat model: memory search never starts a download itself."""
    global _pulling, _embed_ok
    if _pulling or not _downloads_allowed():
        return
    _pulling = True
    try:
        req = urllib.request.Request(OLLAMA + "/api/pull", data=json.dumps({"name": EMBED_MODEL, "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3600) as r:
            r.read()
        _embed_ok = None            # re-check next time
    except Exception:
        pass
    finally:
        _pulling = False


def embeddings_available() -> bool:
    """True when Ollama is running and has the embedding model. Without it, memory
    search uses keyword matching; Setup downloads the model with the chat model."""
    global _embed_ok
    if _embed_ok is not None:
        return _embed_ok
    try:
        names = [m.get("name", "") for m in _http("/api/tags", timeout=3).get("models", [])]
    except Exception:
        return False                 # Ollama not running -- check again later
    _embed_ok = any(n.split(":")[0] == EMBED_MODEL for n in names)
    return _embed_ok


def embed(texts: list[str]) -> list[list[float]] | None:
    """Embeddings for texts (cached), or None if unavailable."""
    if not texts or not embeddings_available():
        return None
    cache = _load_cache()
    keys = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    missing = [(k, t) for k, t in zip(keys, texts) if k not in cache]
    if missing:
        try:
            out = _http("/api/embed", {"model": EMBED_MODEL, "input": [t[:2000] for _, t in missing]}, timeout=60)
            for (k, _), vec in zip(missing, out.get("embeddings", [])):
                cache[k] = vec
            _save_cache()
        except Exception:
            return None
    try:
        return [cache[k] for k in keys]
    except KeyError:
        return None


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


_WORD = re.compile(r"[a-z0-9']+")


def _overlap(a: str, b: str) -> float:
    wa, wb = set(_WORD.findall(a.lower())), set(_WORD.findall(b.lower()))
    return len(wa & wb) / len(wa | wb) if wa and wb else 0.0


# ── Facts ───────────────────────────────────────────────────────────────────

UNREADABLE_FILE_NAME = "memory_facts.unreadable.jsonl"


def _read_facts() -> tuple[list[dict], list[str]]:
    """(saved memories, lines that aren't one). One damaged line used to make every memory
    disappear, and the next save then rewrote the file with only the new one."""
    try:
        lines = FACTS_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [], []
    facts, bad = [], []
    for line in lines:
        if not line.strip():
            continue
        try:
            f = json.loads(line)
        except ValueError:
            f = None
        if isinstance(f, dict) and isinstance(f.get("text"), str) and f["text"].strip():
            facts.append(f)
        else:
            bad.append(line)
    return facts, bad


def memory_status() -> dict:
    """What the memory file is actually like: {"file", "exists", "saved", "unreadable", "error"}."""
    out = {"file": str(FACTS_FILE), "exists": FACTS_FILE.exists(), "saved": 0, "unreadable": 0, "error": ""}
    try:
        facts, bad = _read_facts()
        out["saved"], out["unreadable"] = len(facts), len(bad)
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def list_facts(person: str | None = None) -> list[dict[str, Any]]:
    try:
        facts, _bad = _read_facts()
    except OSError:
        facts = []
    if facts and not _settings().get(REPAIR_KEY):
        facts = repair_learned(facts)
    if person:
        facts = [f for f in facts if f.get("person") in (person, SHARED)]
    return facts


def _write_facts(facts: list[dict]) -> None:
    CURSIV_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _facts, bad = _read_facts()
    except OSError:
        bad = []
    if bad:      # damaged lines are kept beside the file, never dropped by a rewrite
        keep = FACTS_FILE.with_name(UNREADABLE_FILE_NAME)
        have = set(keep.read_text(encoding="utf-8").splitlines()) if keep.exists() else set()
        new = [b for b in bad if b not in have]
        if new:
            with keep.open("a", encoding="utf-8") as f:
                f.write("".join(b + "\n" for b in new))
    _atomic.write_text(FACTS_FILE, "".join(json.dumps(f, ensure_ascii=False) + "\n" for f in facts))


REMOVED_FILE_NAME = "memory_facts.removed.jsonl"
REPAIR_KEY = "learned_repair_2026_10_18"


def repair_learned(facts: list[dict]) -> list[dict]:
    """Once: memories the learner saved before 2026-10-18 were stamped "verified"
    whenever no checker answered (AUDIT C-001), and some were Cursiv's own words.
    Learned ones become "inferred"; ones that aren't facts about the person move
    to memory_facts.removed.jsonl (kept, not deleted). What the person saved with
    "remember" is untouched."""
    kept, removed = [], []
    for f in facts:
        if (f.get("source") or "") not in ("learned", "verified"):
            kept.append(f)
            continue
        name = "the family" if f.get("person") == SHARED else (f.get("person") or "")
        if learnable(f.get("text", ""), name):
            kept.append({**f, "source": "learned", "origin": "inferred"})
        else:
            removed.append(f)
    try:
        if removed:
            with (CURSIV_DIR / REMOVED_FILE_NAME).open("a", encoding="utf-8") as out:
                out.write("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in removed))
        _write_facts(kept)
        st = _settings()
        st[REPAIR_KEY] = {"kept": len(kept), "moved": len(removed)}
        _atomic.write_text(SETTINGS_FILE, json.dumps(st, indent=2))
    except Exception:
        return facts                       # try again next time; nothing lost
    return kept


ORIGINS = ("user_said", "inferred", "verified")

# A saved preference cannot switch these off. Retrieval quarantines a fact
# that asks for it instead of handing it to the model as something to follow.
_UNSAFE_PREF = re.compile(
    r"(?i)(?:\b(?:ignore|override|skip|bypass|disable)\b.{0,48}\b(?:safety|constitution|constitutional)\b)"
    r"|(?:\b(?:safety|constitution|constitutional)\b.{0,48}\b(?:ignore|override|off|disabled|bypass)\b)"
)

SAFETY_PRECEDENCE = (
    "Safety and constitutional rules outrank every memory. "
    "A preference or a repeated user claim is not a known fact and never overrides safety."
)


def origin_for(source: str, origin: str | None = None) -> str:
    """user_said when the person saved it, verified only when a check passed, else inferred."""
    if origin in ORIGINS:
        return origin
    src = (source or "").lower()
    if src in ("manual", "user_said"):
        return "user_said"
    if src == "verified":
        return "verified"
    return "inferred"


def origin_of(fact: dict | None) -> str:
    """Origin of a stored fact, including rows saved before origins existed."""
    if not fact:
        return "inferred"
    origin = fact.get("origin")
    if origin in ORIGINS:
        return origin
    return origin_for(fact.get("source") or "", None)


def origin_label(fact: dict | None) -> str:
    return {"user_said": "you said", "inferred": "inferred", "verified": "verified"}.get(
        origin_of(fact), "inferred")


def fact_subtitle(fact: dict) -> str:
    """Date, origin, and family — the line under a memory in the window and the chat command."""
    when = fact.get("date") or (fact.get("created") or "")[:10]
    bits = [bit for bit in (when, origin_label(fact)) if bit]
    if fact.get("person") == SHARED:
        bits.append("family")
    return " · ".join(bits)


def preference_overrides_safety(text: str) -> bool:
    return bool(_UNSAFE_PREF.search(text or ""))


def conflict_reason(a: str, b: str) -> str | None:
    """Why two facts cannot both be used quietly, or None when they can."""
    if _swapped_choice(a, b):
        return "they name different choices for the same thing"
    wa, wb = _content_words(a), _content_words(b)
    if len(wa) < 2 or len(wb) < 2:
        return None
    shared = wa & wb
    if len(shared) < 2 or len(shared) / min(len(wa), len(wb)) < 0.5:
        return None
    if bool(_NEG.search(a)) != bool(_NEG.search(b)):
        return "one affirms and one denies"
    nums_a, nums_b = set(_NUM.findall(a)), set(_NUM.findall(b))
    if nums_a and nums_b and nums_a != nums_b:
        return "they give different numbers"
    return None


# Statements with one answer at a time: "I prefer tea" and "I prefer coffee" can't
# both be current, while "I like tea" and "I like coffee" can.
_EXCLUSIVE = re.compile(r"\b(prefer|prefers|favorite|favourite|name|live|lives|rather|birthday|born)\b", re.IGNORECASE)


def _swapped_choice(a: str, b: str) -> bool:
    """The same exclusive statement with one word changed."""
    xa, xb = _WORD.findall((a or "").lower()), _WORD.findall((b or "").lower())
    if len(xa) != len(xb) or len(xa) < 2 or not _EXCLUSIVE.search(a or ""):
        return False
    diff = [i for i, (p, q) in enumerate(zip(xa, xb)) if p != q]
    return len(diff) == 1 and not _EXCLUSIVE.fullmatch(xa[diff[0]])


_CONTENT_STOP = frozenset(
    "the a an of to and or for in on is are was were be with about that this their "
    "his her your you they them from into over after before than then just not no "
    "never does did do".split()
)
_NEG = re.compile(
    r"\b(not|no|never|n't|without|isn't|isnt|doesn't|doesnt|don't|dont|cannot|can't|cant)\b",
    re.IGNORECASE,
)
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")


def _content_words(text: str) -> set[str]:
    return {word for word in _WORD.findall((text or "").lower())
            if word not in _CONTENT_STOP and len(word) > 2}


def add_fact(text: str, person: str | None = None, source: str = "manual",
             origin: str | None = None) -> dict | None:
    """Save a fact unless it's (nearly) already known. Returns it, or None if duplicate.

    A duplicate is not rewritten, so saying the same thing again cannot upgrade
    user_said into verified.
    """
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) > MAX_FACT:
        raise ValueError(f"it's {len(text)} characters; one saved memory holds up to {MAX_FACT}")
    if len(text) < 4:
        return None
    person = (person or _person).lower()
    with _lock:
        facts = list_facts()
        same = [f for f in facts if f.get("person") == person]
        if any(f["text"].lower() == text.lower() for f in same):
            return None
        vecs = embed([text] + [f["text"] for f in same]) if same else None
        if vecs and any(_cos(vecs[0], v) > 0.92 for v in vecs[1:]):
            return None
        if not vecs and any(_overlap(text, f["text"]) > 0.8 for f in same):
            return None
        fact = {"id": uuid.uuid4().hex[:10], "person": person, "text": text,
                "created": time.strftime("%Y-%m-%d %H:%M"),
                "date": time.strftime("%Y-%m-%d"),
                "source": source, "origin": origin_for(source, origin)}
        facts.append(fact)
        _write_facts(facts)
        return fact


MAX_FACT = 400


def find(query: str, person: str | None = None) -> list[dict]:
    """Saved memories that contain the query's identifiers (FIELD-731, 18.6) and most of its words,
    exactly as stored. Plain text matching, no model and no embeddings, so it works offline."""
    q = (query or "").lower()
    ids = set(re.findall(r"[a-z0-9]+(?:[-_./][a-z0-9]+)+|\d+(?:\.\d+)?", q))
    words = {w for w in re.findall(r"[a-z]{3,}", q)} - {"the", "and", "for", "from", "with", "that", "this",
                                                         "record", "records", "memory", "saved", "stored", "data",
                                                         "details", "entry", "about", "what", "your", "my"}
    out = []
    for f in list_facts(person or _person):
        t = f["text"].lower()
        if ids and not all(i in t for i in ids):
            continue
        if not ids and (not words or sum(w in t for w in words) < max(1, (len(words) + 1) // 2)):
            continue
        out.append(f)
    return out


_SAVE = re.compile(r"(?is)^\s*(?:please\s+)?(?:save|store|remember|keep|record)\s+(?:this|the following|these|that)"
                   r"(?:\s+(?:record|details|data|information|note|measurement|entry|reading))?"
                   r"(?:\s+(?:to|in|into)\s+(?:your\s+|the\s+)?(?:persistent\s+|long[- ]term\s+|saved\s+)?memory)?"
                   r"\s*[:\-\u2013]\s*(.+)$")
_RECALL = re.compile(r"(?is)^\s*(?:please\s+)?(?:recall|retrieve|look up|fetch|pull up|find)\s+(.+)$")
_RECALL_NEEDS = re.compile(r"(?i)\b(memory|memories|saved|stored|record)\b")


def _record_text(body: str) -> str:
    """A record as one line, its fields kept exactly: "Site: North Ridge; Temperature: 18.6°C"."""
    lines = [re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", ln).strip() for ln in body.splitlines()]
    return "; ".join(ln for ln in lines if ln)


def _save_reply(text: str) -> str:
    try:
        saved = add_fact(text, source="manual")
    except ValueError as exc:
        return (f"Not saved: {exc}. Save it in shorter parts, or record it in the field notebook (log ...), "
                "which keeps any length.")
    except OSError as exc:
        return (f"Not saved: Cursiv couldn't write its memory file ({type(exc).__name__}: {exc}). Nothing was "
                f"stored. Check that {FACTS_FILE.parent} is on a drive with space that isn't read-only.")
    if not saved:
        return "Already saved: an identical memory is there (nothing new was written)."
    back = next((f for f in list_facts() if f.get("id") == saved["id"]), None)
    if not back or back["text"] != saved["text"]:
        return "Not saved: the write seemed to work but reading it back didn't find it. Try again."
    return (f"Saved to Cursiv's memory on this computer ({saved['created']}), exactly as:\n{saved['text']}\n"
            "Get it back any time with: recall <words or code>")


def _recall_reply(query: str) -> str:
    status = memory_status()
    if status["error"]:
        return (f"Couldn't read Cursiv's saved memory ({status['error']}). This is a storage problem, not "
                "'not found': the memory may still be there.")
    hits = find(query)
    damaged = (f"\n(Note: {status['unreadable']} saved line(s) in the memory file are damaged and can't be read; "
               f"they're kept in {UNREADABLE_FILE_NAME}, not used.)" if status["unreadable"] else "")
    if not hits:
        return (f"Nothing in Cursiv's saved memory matches \"{query.strip()}\" ({status['saved']} memories saved). "
                "If it was mentioned earlier in this conversation, it was only in the conversation; it was never "
                "saved. To save something: remember <it>" + damaged)
    rows = "\n".join(f"- {f['text']}  (saved {f.get('created', 'date unknown')}, {origin_label(f)})" for f in hits)
    clash = ""
    for i, a in enumerate(hits):
        for b in hits[i + 1:]:
            why = conflict_reason(a["text"], b["text"])
            if why:
                clash = f"\nThese saved memories conflict ({why}); Cursiv doesn't pick one."
                break
    return f"From Cursiv's saved memory, exactly as stored ({len(hits)} found):\n{rows}{clash}{damaged}"


def forget(words: str, person: str | None = None) -> list[str]:
    """Delete facts matching an id or containing the words. Returns removed texts."""
    words = (words or "").strip().lower()
    if not words:
        return []
    person = (person or _person).lower()
    with _lock:
        facts = list_facts()
        gone = [f for f in facts if f.get("person") in (person, SHARED) and (f["id"] == words or words in f["text"].lower())]
        if gone:
            ids = {f["id"] for f in gone}
            _write_facts([f for f in facts if f["id"] not in ids])
        return [f["text"] for f in gone]


def delete_fact(fact_id: str) -> bool:
    with _lock:
        facts = list_facts()
        keep = [f for f in facts if f["id"] != fact_id]
        if len(keep) == len(facts):
            return False
        _write_facts(keep)
        return True


# ── Recall ──────────────────────────────────────────────────────────────────

def _strand_items() -> list[tuple[str, str]]:
    try:
        from cursiv_v215.core.strand_store import list_strands
        out = []
        for s in list_strands(limit=300) if callable(list_strands) else []:
            text = f"{s.get('query', '')[:200]} — {s.get('synthesis', '')[:500]}"
            out.append(("conversation", text))
        return out
    except Exception:
        return []


def recall(query: str, person: str | None = None, top_k: int = 6) -> list[tuple[float, str, str]]:
    """Most relevant (score, kind, text) for the query: this person's facts,
    family facts, and saved conversation notes."""
    person = (person or _person).lower()
    items = [("fact", f["text"]) for f in list_facts(person)] + _strand_items()
    if not items or not query.strip():
        return []
    vecs = embed([query] + [t for _, t in items])
    inferred = {f["text"] for f in list_facts(person) if origin_of(f) == "inferred"}
    scored: list[tuple[float, str, str]] = []
    # A guessed memory must be clearly about this question to be used (farm guesses
    # were recalled for "what's 17% of 2,450").
    if vecs:
        q = vecs[0]
        for (kind, text), v in zip(items, vecs[1:]):
            score = _cos(q, v) + (0.05 if kind == "fact" else 0.0)
            if score >= (0.68 if text in inferred else 0.55):
                scored.append((score, kind, text))
    else:
        for kind, text in items:
            score = _overlap(query, text)
            if score >= (0.25 if text in inferred else 0.12):
                scored.append((score, kind, text))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def _fact_line(text: str, by_text: dict[str, dict]) -> str:
    return f"- [{origin_label(by_text.get(text))}] {text}"


def build_context(query: str, person: str | None = None) -> str:
    """Memory block for the system prompt, or "" when nothing relevant.

    Conflicting facts are both included. A preference that would override
    safety is listed as not applied. Origins are shown on every fact.
    """
    person = (person or _person).lower()
    stored = list_facts(person)
    by_text = {f["text"]: f for f in stored}
    quarantined = [f for f in stored if preference_overrides_safety(f.get("text", ""))]
    blocked = {f["text"] for f in quarantined}
    hits = recall(query, person)
    fact_hits = [t for _, kind, t in hits if kind == "fact" and t not in blocked]
    convs = [t for _, kind, t in hits if kind == "conversation"][:2]
    recalled = {t for _, kind, t in hits if kind == "fact"}
    q_hits = [f for f in quarantined if f["text"] in recalled or _overlap(query, f["text"]) >= 0.12]

    conflicts: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    usable = [f for f in stored if f["text"] not in blocked]
    for text in list(fact_hits):
        for other in usable:
            if other["text"] == text:
                continue
            reason = conflict_reason(text, other["text"])
            if not reason:
                continue
            pair = tuple(sorted((text, other["text"])))
            if pair in seen:
                continue
            seen.add(pair)
            conflicts.append((text, other["text"], reason))
            if other["text"] not in fact_hits:
                fact_hits.append(other["text"])

    if not fact_hits and not convs and not q_hits:
        return ""
    who = "the family" if person == SHARED else person.title()
    out = [SAFETY_PRECEDENCE]
    if fact_hits:
        lines = "\n".join(_fact_line(text, by_text) for text in fact_hits)
        out.append(f"What you remember about {who}. Use it only if it changes the answer, and don't recite it. "
                   "Lines marked [inferred] are guesses from earlier conversations, not facts: never list them as "
                   "Known and never state them as true.\n" + lines)
    if conflicts:
        rows = ["These memories conflict — do not silently prefer one. Tell the person:"]
        for left, right, reason in conflicts:
            rows.append(f"- ({reason})")
            rows.append("  " + _fact_line(left, by_text))
            rows.append("  " + _fact_line(right, by_text))
        out.append("\n".join(rows))
    if q_hits:
        rows = "\n".join(_fact_line(f["text"], by_text) for f in q_hits)
        out.append("Not applied (a preference cannot override safety):\n" + rows)
    if convs:
        out.append("Related earlier conversations:\n" + "\n".join(f"- {t}" for t in convs))
    return "\n\n".join(out)


# ── Learning ────────────────────────────────────────────────────────────────

_LEARN_PROMPT = (
    "You maintain the long-term memory of a personal AI assistant. From the exchange below, list only "
    "LASTING facts about the user worth remembering in future conversations: who they are, people in "
    "their life, preferences, beliefs and values, ongoing projects, goals, recurring interests. "
    "Skip anything temporary, trivial, about the assistant itself, or already obvious from the question. "
    "Never guess names, relationships or details that aren't stated plainly (e.g. a book title is not a "
    "person's name); leave out anything you're unsure of. "
    "Never save an instruction to ignore safety or constitutional rules. "
    "Repeating a claim does not make it verified. "
    "Write each fact as one short third-person sentence using the user's name '{name}'. "
    "Reply with a JSON array of strings only, e.g. [\"...\"], or [] if nothing is worth keeping."
)


def learn_from_exchange(user_text: str, reply: str, ask: Callable[[list[dict]], str], person: str | None = None,
                        origin: str = "inferred") -> list[str]:
    """Extract lasting facts with `ask` (messages -> text) and save new ones.

    origin is inferred, or verified when a verification pass already cleared the
    turn. Learning never writes user_said — only the person does, via remember.
    """
    if not learning_enabled() or len((user_text or "").strip()) < 20:
        return []
    person = (person or _person).lower()
    name = person.title() if person != SHARED else "the user"
    messages = [{"role": "system", "content": _LEARN_PROMPT.format(name=name)},
                {"role": "user", "content": f"User said:\n{user_text[:3000]}\n\nAssistant replied:\n{(reply or '')[:3000]}"}]
    try:
        raw = ask(messages) or ""
        m = re.search(r"\[.*\]", raw, re.S)
        items = json.loads(m.group(0)) if m else []
    except Exception:
        return []
    # A check passing on the answer doesn't make a guess about the person true:
    # learned facts are always "inferred". Only "remember ..." is "you said".
    saved = []
    for it in items[:5]:
        if isinstance(it, str) and learnable(it, name) and add_fact(it, person, source="learned", origin="inferred"):
            saved.append(it)
    return saved


# What the learner must not save: Cursiv's own words, ledger lines, notes about the
# conversation. All were found in a real memory file (2026-10-18): "Known: Detailed
# Experimental Plan ...", a 400-character paragraph of soil advice, "Jw did not
# explicitly tell you about ...".
_NOT_A_FACT = re.compile(
    r"(?i)^\s*(known|inferred|assumed|unknown)\s*:|^\s*(you|the assistant|cursiv|i)\b|"
    r"\b(did not|didn't) (explicitly )?(tell|say|mention)|\bin this conversation\b")


def learnable(text: str, name: str = "") -> bool:
    t = (text or "").strip()
    if not 8 <= len(t) <= 200 or _NOT_A_FACT.search(t):
        return False
    who = [w for w in ((name or "").lower(), "the user", "the family", "they", "their", "he ", "she ") if w]
    return any(w in t.lower() for w in who)


# ── Commands ────────────────────────────────────────────────────────────────

def memory_command(text: str) -> str | None:
    """remember <fact> · forget <words> · what do you remember · memory learn on|off.
    Returns the reply, or None if the text isn't a memory command."""
    t = (text or "").strip()
    low = t.lower()
    m = _SAVE.match(t)
    if m:                                        # "save this record: ..." -- saved exactly, or said why not
        return _save_reply(_record_text(m.group(1)))
    m = _RECALL.match(t)
    if m and _RECALL_NEEDS.search(t):            # "retrieve the FIELD-731 record from memory"
        return _recall_reply(m.group(1))
    if low.startswith("remember ") and len(t) > 9:
        fact = t[9:].strip()
        if fact.lower().startswith("that "):
            fact = fact[5:]
        if _person != SHARED and re.match(r"(?i)^(i|my|i'm|i've|me)\b", fact):
            fact = f"{_person.title()}: {fact}"     # first person -> unambiguous when recalled later
        try:
            saved = add_fact(fact, source="manual")
        except ValueError as exc:
            return f"Not saved: {exc}. Save it in shorter parts."
        except OSError as exc:
            return f"Not saved: Cursiv couldn't write its memory file ({type(exc).__name__}: {exc}). Nothing was stored."
        return f"Got it — I'll remember: {saved['text']}" if saved else "I already remember that."
    if low.startswith("forget ") and len(t) > 7:
        gone = forget(t[7:])
        return ("Forgotten:\n" + "\n".join(f"- {g}" for g in gone)) if gone else "I couldn't find a memory matching that."
    if low in ("what do you remember", "what do you remember?", "what do you remember about me",
               "what do you remember about me?", "memories", "memory"):
        facts = list_facts(_person)
        if not facts:
            return "I don't have any saved memories yet. Tell me with: remember <something about you>"
        head = f"What I remember ({len(facts)}):"
        rows = "\n".join(f"- {f['text']}  ({fact_subtitle(f)})" for f in facts[-40:])
        return head + "\n" + rows + \
            "\n\nForget one with: forget <words>.  Turn learning off with: memory learn off"
    if low in ("memory learn off", "memory learn on"):
        set_learning(low.endswith("on"))
        return ("I'll keep learning lasting facts from our conversations." if low.endswith("on")
                else "I'll stop learning from conversations. Saved memories stay until you forget them.")
    return None

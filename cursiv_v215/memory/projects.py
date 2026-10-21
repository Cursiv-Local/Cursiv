"""
Project memory: a running summary for each ongoing thing a person works on
("the Pi project", "the garden", "Cursiv's website") -- so mentioning it later
brings back where it stands, not just loose facts.

After an exchange, a small background step decides whether it belongs to a
project (new or existing) and rewrites that project's short summary. Before a
reply, the projects that match the message are added to the instructions.

  projects                 list them
  project show <name>      the full summary
  project forget <name>    delete one
Stored per person in ~/.cursiv/projects/<person>.json.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Callable

DIR = Path.home() / ".cursiv" / "projects"
MAX_PROJECTS = 30
_lock = threading.Lock()
_WORD = re.compile(r"[a-z0-9][a-z0-9+#.-]{2,}")
_STOP = {"the", "and", "for", "with", "that", "this", "what", "how", "can", "you", "your", "are", "was", "from",
         "have", "has", "but", "not", "about", "into", "just", "like", "want", "need", "make", "get", "use", "project"}


def _path(person: str) -> Path:
    return DIR / (re.sub(r"[^a-z0-9_-]", "_", (person or "family").lower()) + ".json")


def load(person: str) -> dict:
    from cursiv_v215.core import state_store
    data = state_store.load(_path(person), {})
    if not isinstance(data, dict):
        raise ValueError('Invalid project notes; existing data preserved')
    return data


def _save(person: str, data: dict) -> None:
    from cursiv_v215.core import state_store
    state_store.save(_path(person), data)


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def relevant(text: str, person: str, limit: int = 2) -> list[tuple[str, dict]]:
    data = load(person)
    q = _words(text)
    low = (text or "").lower()
    scored = []
    for name, p in data.items():
        score = 5 if name.lower() in low else 0
        score += 2 * len(q & set(p.get("keywords", [])))
        score += len(q & _words(name))
        if score >= 3:
            scored.append((score, name, p))
    scored.sort(key=lambda s: -s[0])
    return [(n, p) for _s, n, p in scored[:limit]]


def context(text: str, person: str) -> str:
    rel = relevant(text, person)
    if not rel:
        return ""
    return "## Ongoing projects this may be about (where things stand — build on this, don't repeat it back)\n" + \
           "\n\n".join(f"### {n}\n{p['summary']}" for n, p in rel)


_LEARN = """You keep short running notes on the ongoing projects of {name} (things they work on across many
conversations: builds, plans, studies, businesses, hobbies). Existing projects:
{existing}

Read the exchange. If it is real progress, a decision, a problem or a detail about one ongoing project (new or
existing), reply with JSON:
{{"project": "<short name, 1-4 words, reuse an existing name if it's the same project>",
  "summary": "<the project's updated summary: what it is, current state, key details (hardware, versions, names,
  decisions), open problems and next step -- under 120 words, plain sentences, merge the old summary with what's new>",
  "keywords": ["<5-10 lowercase words that would appear when they mention it>"]}}
If it's a one-off question, small talk, or not about a lasting project, reply {{"project": null}}. JSON only."""


def learn(user_text: str, reply: str, ask: Callable[[list[dict]], str], person: str) -> str | None:
    from . import formation
    from .semantic import generation
    epoch = generation()
    if not formation.enabled_for(user_text):
        return None
    if len((user_text or "").strip()) < 25:
        return None
    data = load(person)
    existing = "\n".join(f"- {n}: {p['summary'][:300]}" for n, p in list(data.items())[-12:]) or "(none yet)"
    try:
        raw = ask([{"role": "system", "content": _LEARN.format(name=person.title(), existing=existing)},
                   {"role": "user", "content": f"User:\n{user_text[:2500]}"}]) or ""
        m = re.search(r"\{.*\}", raw, re.S)
        out = json.loads(m.group(0)) if m else {}
    except Exception:
        return None
    name = (out.get("project") or "").strip()[:40]
    summary = (out.get("summary") or "").strip()
    if not name or len(summary) < 20 or not formation.permitted(name + ' ' + summary):
        return None
    with _lock:
        if not formation.enabled_for(user_text) or generation() != epoch:
            return None
        data = load(person)
        match = next((n for n in data if n.lower() == name.lower()), name)
        kws = [k.lower() for k in out.get("keywords", []) if isinstance(k, str)][:10]
        old = data.get(match, {})
        data[match] = {"summary": summary[:1200], "keywords": sorted(set(old.get("keywords", [])) | set(kws))[:20],
                       "updated": time.strftime("%Y-%m-%d"), "created": old.get("created", time.strftime("%Y-%m-%d"))}
        if len(data) > MAX_PROJECTS:
            oldest = sorted(data, key=lambda n: data[n].get("updated", ""))[0]
            data.pop(oldest)
        _save(person, data)
    return match


def command(text: str, person: str) -> str | None:
    t = (text or "").strip()
    low = t.lower()
    if low in ("projects", "topics", "my projects"):
        data = load(person)
        if not data:
            return ("No projects yet. As you work on something over several chats (a build, a plan, a study), "
                    "I keep a short running summary of where it stands and bring it back when it comes up.")
        rows = "\n".join(f"- **{n}** (updated {p.get('updated', '?')}) — {p['summary'][:110]}…" for n, p in
                         sorted(data.items(), key=lambda kv: kv[1].get("updated", ""), reverse=True))
        return f"Your projects:\n{rows}\n\nproject show <name> · project forget <name>"
    m = re.match(r"(?i)^project (show|forget|delete)\s+(.+)$", t)
    if m:
        data = load(person)
        name = next((n for n in data if n.lower() == m.group(2).strip().lower()), None)
        if not name:
            return f"No project called {m.group(2).strip()}. See yours with: projects"
        if m.group(1).lower() == "show":
            p = data[name]
            return f"**{name}** — started {p.get('created', '?')}, updated {p.get('updated', '?')}\n\n{p['summary']}"
        with _lock:
            data.pop(name)
            _save(person, data)
        return f"Forgot the project {name}."
    return None

"""
Custom agents: specialists anyone in the family can create in plain words.

  agent new chef: plans healthy family meals on a budget, asks about allergies
  @chef what should we make tonight?
  agent teach chef Brandon is allergic to peanuts
  agents ask should we start a garden this spring?

Each agent = a name, its job (instructions), and things it has been taught.
Saved per person in ~/.cursiv/agents/<person>/<name>.json -- plain files.
"""
from __future__ import annotations

import json
import re
import time
import threading
from functools import wraps
from pathlib import Path
from cursiv_engine.core import atomic

DIR = Path.home() / ".cursiv" / "agents"
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,23}$")
_lock = threading.RLock()


def _serialized(fn):
    @wraps(fn)
    def locked(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return locked


def _person() -> str:
    try:
        from cursiv_engine.memory import semantic
        return semantic.current_person()
    except Exception:
        return "family"


def _dir(person: str | None = None) -> Path:
    return DIR / re.sub(r"[^a-z0-9_-]", "_", (person or _person()).lower())


def clean_name(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", (name or "").strip().lower().lstrip("@"))


def load(name: str) -> dict | None:
    try:
        value = json.loads((_dir() / f"{clean_name(name)}.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(value, dict) or value.get('name') != clean_name(name) or not isinstance(value.get('job'), str) \
            or not isinstance(value.get('knowledge'), list) or not all(isinstance(v, str) for v in value['knowledge']):
        raise ValueError('Saved agent data is damaged; it was not replaced')
    return value


@_serialized
def save(agent: dict) -> None:
    if not isinstance(agent, dict) or not _NAME_RE.fullmatch(agent.get('name', '')):
        raise ValueError('Invalid saved agent name')
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    agent["updated"] = time.time()
    atomic.write_text(d / f"{agent['name']}.json", json.dumps(agent, indent=2, ensure_ascii=False))
    if load(agent['name']) != agent:
        raise OSError('Agent save read-back verification failed')


def all_agents() -> list[dict]:
    d = _dir()
    out = []
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


@_serialized
def create(name: str, job: str) -> str:
    name = clean_name(name)
    if not _NAME_RE.match(name):
        return "Agent names are one word, 2–24 letters/numbers (e.g. chef, tutor, farm_hand)."
    if len((job or "").strip()) < 8:
        return f"Tell me what {name} should do, e.g.: agent new {name}: helps plan meals on a budget"
    if load(name):
        return f"You already have an agent called {name}. Change it with: agent edit {name}: <new job>"
    save({"name": name, "job": job.strip()[:2000], "knowledge": [], "created": time.time(), "uses": 0})
    return (f"Created agent **{name}**.\nTalk to it: `@{name} <message>`\n"
            f"Teach it: `agent teach {name} <something it should always know>`")


@_serialized
def edit(name: str, job: str) -> str:
    a = load(name)
    if not a:
        return f"No agent called {clean_name(name)}. See yours with: agents"
    a["job"] = job.strip()[:2000]
    save(a)
    return f"Updated {a['name']}'s job."


@_serialized
def teach(name: str, fact: str) -> str:
    a = load(name)
    if not a:
        return f"No agent called {clean_name(name)}. See yours with: agents"
    fact = " ".join((fact or "").split())[:400]
    if len(fact) < 4:
        return f"What should {a['name']} know? e.g. agent teach {a['name']} we keep a gluten-free kitchen"
    if fact.lower() in (k.lower() for k in a["knowledge"]):
        return f"{a['name']} already knows that."
    a["knowledge"] = (a["knowledge"] + [fact])[-60:]
    save(a)
    return f"{a['name']} will remember: {fact}"


@_serialized
def delete(name: str) -> str:
    p = _dir() / f"{clean_name(name)}.json"
    if not p.exists():
        return f"No agent called {clean_name(name)}."
    p.unlink()
    if p.exists():
        raise OSError('Agent deletion could not be verified')
    return f"Deleted agent {clean_name(name)}."


def describe(name: str) -> str:
    a = load(name)
    if not a:
        return f"No agent called {clean_name(name)}."
    know = "\n".join(f"- {k}" for k in a["knowledge"]) or "- (nothing yet — agent teach " + a["name"] + " <fact>)"
    return f"**{a['name']}** — used {a.get('uses', 0)} times\n\nJob:\n{a['job']}\n\nKnows:\n{know}"


def listing() -> str:
    agents = all_agents()
    if not agents:
        return ("You don't have any custom agents yet. Make one in plain words, for example:\n"
                "  agent new chef: plans healthy family meals on a budget and asks about allergies\n"
                "  agent new tutor: explains math to a 10-year-old with simple examples\n"
                "Then talk to it with @chef or @tutor.")
    rows = "\n".join(f"- **@{a['name']}** — {a['job'][:90]}{'…' if len(a['job']) > 90 else ''}" for a in agents)
    return f"Your agents:\n{rows}\n\nTalk: @name <message> · Ask all of them: agents ask <question>\nManage: agent show/edit/teach/delete <name>"


def system_prompt(agent: dict, person_memory: str = "") -> str:
    know = "\n".join(f"- {k}" for k in agent.get("knowledge", []))
    return (
        f"You are \"{agent['name']}\", a specialist agent inside Cursiv (a personal AI made by Cursiv Local for "
        f"his family). Stay in this role.\n\n## Your job\n{agent['job']}\n\n"
        + (f"## Things you've been taught (always true for this family)\n{know}\n\n" if know else "")
        + (f"## What Cursiv knows about the person you're helping\n{person_memory}\n\n" if person_memory else "")
        + "Be practical and specific. If your job doesn't cover the question, say so briefly and answer as best you can. "
          "Never invent facts about the family."
    )


def _extras(text: str) -> str:
    """Fact sheet when the question is about Cursiv itself (agents guessed otherwise),
    plus the person's tone and style rules."""
    out = []
    try:
        if re.search(r"\bcursiv\b", text or "", re.I):
            from cursiv_engine.core import selfknow
            facts = re.sub(r"<!--.*?-->", "", selfknow.FACTS_FILE.read_text(encoding="utf-8"), flags=re.S).strip()
            out.append("## Facts about Cursiv (use these; never guess about Cursiv)\n" + facts)
    except Exception:
        pass
    try:
        from cursiv_engine.core import style
        add = style.prompt_addendum(_person())
        if add:
            out.append(add)
    except Exception:
        pass
    return ("\n\n" + "\n\n".join(out)) if out else ""


def messages_for(agent: dict, text: str, history: list[dict], person_memory: str = "") -> list[dict]:
    msgs = [{"role": "system", "content": system_prompt(agent, person_memory) + _extras(text)}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in (history or [])[-6:]
             if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    msgs.append({"role": "user", "content": text})
    return msgs


def note_use(agent: dict) -> None:
    agent["uses"] = agent.get("uses", 0) + 1
    try:
        save(agent)
    except Exception:
        pass

"""
Custom agents: specialists anyone using Cursiv can create in plain words.

  agent new chef: plans healthy family meals on a budget, asks about allergies
  @chef what should we make tonight?
  agent teach chef Brandon is allergic to peanuts
  agents ask should we start a garden this spring?

Each agent = a name, its job (instructions), and things it has been taught.
Saved per person in ~/.cursiv/agents/<person>/<name>.json, encrypted with the vault on a
computer (U98; a Cursiv USB drive keeps them readable).

Starter profiles (U101) ship with Cursiv as markdown in agents/starters/: @field, @checker,
@report, @protocol, @writer. Their `reads:` line says what Cursiv's code shows them (read only,
agents/profile_context.py); no profile can save, change or delete anything. A person's own agent
with the same name wins, and editing or teaching a starter makes the person's own copy.
"""
from __future__ import annotations

import json
import re
import time
import threading
from functools import wraps
from pathlib import Path
from cursiv_engine.core import atomic, private_store, vault

DIR = Path.home() / ".cursiv" / "agents"
STARTERS = Path(__file__).resolve().parent / "starters"
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


def _parse_starter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"(?s)^---\n(.*?)\n---\n(.*)$", text)
    if not m:
        return None
    head = dict(re.findall(r"(?m)^(\w+):[ \t]*(.*)$", m.group(1)))
    from cursiv_engine.agents.profile_context import READS
    reads = [r.strip() for r in head.get("reads", "").split(",") if r.strip() in READS]
    name = clean_name(head.get("name", ""))
    if not _NAME_RE.fullmatch(name):
        return None
    return {"name": name, "title": head.get("title", name).strip(), "job": m.group(2).strip(),
            "knowledge": [], "reads": reads, "starter": True}


def starters() -> list[dict]:
    """The profiles that ship with Cursiv (agents/starters/*.md), read-only."""
    out = []
    for f in sorted(STARTERS.glob("*.md")) if STARTERS.exists() else []:
        try:
            row = _parse_starter(f)
        except OSError:
            row = None
        if row:
            out.append(row)
    return out


def load(name: str) -> dict | None:
    try:
        value = json.loads(private_store.read_text(_dir() / f"{clean_name(name)}.json"))
    except FileNotFoundError:
        return next((s for s in starters() if s["name"] == clean_name(name)), None)
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
            out.append(json.loads(private_store.read_text(f)))
        except vault.VaultError:
            raise                     # locked is not "no agents"
        except Exception:
            pass
    return out


def everyone() -> list[dict]:
    """The person's own agents, then the starter profiles they haven't replaced."""
    own = all_agents()
    names = {a.get("name") for a in own}
    return own + [s for s in starters() if s["name"] not in names]


def _own_copy(agent: dict) -> dict:
    """Editing or teaching a starter profile makes the person's own copy (same reads)."""
    if not agent.get("starter"):
        return agent
    return {"name": agent["name"], "title": agent.get("title", ""), "job": agent["job"], "knowledge": [],
            "reads": list(agent.get("reads") or []), "from_starter": True, "created": time.time(), "uses": 0}


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
    a = _own_copy(a)
    a["job"] = job.strip()[:2000]
    save(a)
    return f"Updated {a['name']}'s job."


@_serialized
def teach(name: str, fact: str) -> str:
    a = load(name)
    if not a:
        return f"No agent called {clean_name(name)}. See yours with: agents"
    a = _own_copy(a)
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
        if any(s["name"] == clean_name(name) for s in starters()):
            return f"@{clean_name(name)} is a starter profile that comes with Cursiv, so there's nothing to delete."
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
    from cursiv_engine.core import capabilities
    kind = " (starter profile, comes with Cursiv)" if a.get("starter") else ""
    return (f"**{a.get('title') or a['name']}** @{a['name']}{kind} — used {a.get('uses', 0)} times\n\nJob:\n{a['job']}"
            f"\n\nKnows:\n{know}\n\nWhat it may use: {capabilities.agent_permissions(a)}")


def listing() -> str:
    agents = all_agents()
    names = {a.get("name") for a in agents}
    ready = [s for s in starters() if s["name"] not in names]
    out = []
    if ready:
        out.append("Starter profiles (come with Cursiv; they read only what's listed and never change anything):\n" +
                   "\n".join(f"- **@{s['name']}** — {s['title']}: {s['job'].splitlines()[0][:80]}" for s in ready))
    if agents:
        out.append("Your agents:\n" + "\n".join(
            f"- **@{a['name']}** — {a['job'][:90]}{'…' if len(a['job']) > 90 else ''}" for a in agents))
    else:
        out.append("Make your own in plain words, for example:\n"
                   "  agent new chef: plans healthy family meals on a budget and asks about allergies")
    return "\n\n".join(out) + ("\n\nTalk: @name <message> · Ask your own agents together: agents ask <question>"
                                "\nManage: agent show/edit/teach/delete <name>")


_PERMISSION_Q = re.compile(r"(?i)\b(?:can|could|may|are you able to|do you have (?:access|permission))\b.{0,60}"
                           r"\b(?:read|open|see|access|modify|change|edit|delete|write|files?|folders?|computer|"
                           r"notebook|internet|web|tools?|run)\b|\bwhat (?:can you|are you allowed to) (?:access|do|use)\b")


def asks_about_permissions(text: str) -> bool:
    return bool(_PERMISSION_Q.search(text or ""))


def permissions_answer(agent: dict) -> str:
    from cursiv_engine.core import capabilities
    return (f"@{agent['name']}: {capabilities.agent_permissions(agent)}\n\n"
            "That's set by Cursiv's code, not by this agent's instructions. Cursiv itself can do more (for example "
            "read and write text files in a workspace you chose and turned file access on for), but an agent gets "
            "only what's listed here, and nothing outside your chosen workspace in any case."
            "\n\n*[Sources: Cursiv capability records (no AI model)]*")


def system_prompt(agent: dict, person_memory: str = "", supplied: str = "") -> str:
    from cursiv_engine.core import capabilities
    know = "\n".join(f"- {k}" for k in agent.get("knowledge", []))
    return (
        f"You are \"{agent.get('title') or agent['name']}\" (@{agent['name']}), a specialist agent inside Cursiv (a personal AI made by Cursiv Local, "
        f"an independent open-source project). Stay in this role.\n\n## Your job\n{agent['job']}\n\n"
        + (f"## Things you've been taught (always true for the person you help)\n{know}\n\n" if know else "")
        + (f"## What Cursiv knows about the person you're helping\n{person_memory}\n\n" if person_memory else "")
        + "## What you can use\n" + capabilities.agent_permissions(agent) + " Never claim to have read, saved, "
          "searched or changed anything beyond what Cursiv shows you below.\n\n"
        + (supplied + "\n\n" if supplied else "")
        + "Be practical and specific. If your job doesn't cover the question, say so briefly and answer as best you can. "
          "Never invent facts about the person or the people they mention. Don't sign your answer or name an AI "
          "model: you don't know which one is running, and Cursiv shows it."
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


def messages_for(agent: dict, text: str, history: list[dict], person_memory: str = "", supplied: str = "") -> list[dict]:
    msgs = [{"role": "system", "content": system_prompt(agent, person_memory, supplied) + _extras(text)}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in (history or [])[-6:]
             if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    msgs.append({"role": "user", "content": text})
    return msgs


def note_use(agent: dict) -> None:
    if agent.get("starter"):
        return                        # a starter profile isn't copied just because it was used
    agent["uses"] = agent.get("uses", 0) + 1
    try:
        save(agent)
    except Exception:
        pass

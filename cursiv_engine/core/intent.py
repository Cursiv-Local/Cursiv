"""
Conversational actions (U99): say it normally, Cursiv works out the action.

The model never acts. It only rewrites a request into ONE of Cursiv's own
canonical commands -- the exact commands that already run natively and return a
receipt ("log site: …", "remember …", "Add a line to notes.txt saying …",
"workspace …", "offline on"). Cursiv then checks that proposal against the
person's own words and the action's rules, and:

  * read-only actions (search the notebook, read or list a file) run straight away;
  * anything that changes something is shown on a confirm card first
    (Save / Edit / Cancel) and runs only after the person says yes.

Exact commands still go straight to the native routes; this step is only for
messages they didn't recognise and that look like they might be an action.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

# ── which messages are worth asking about ────────────────────────────────────

_ACTION_WORDS = re.compile(
    r"(?i)\b(?:log|logged|record|recorded|jot|note (?:down|that)|write (?:down|that|it)|save|keep track|"
    r"add (?:a |an |this |that )?(?:note|line|entry|observation|reading|measurement)|append|"
    r"remember|don'?t forget|forget|keep in mind|delete the memory|"
    r"work (?:in|out of)|switch (?:to|the) (?:workspace|folder)|workspace|[\w .-]{1,30} folder|"
    r"(?:read|open|show|list|make|create) (?:me )?(?:my |the |a )?(?:file|folder|files)|[\w-]+\.(?:txt|md|csv|json)|"
    r"go offline|stay offline|turn (?:on|off) offline|offline mode|back online|go online|"
    r"the internet again|on this computer from now|"
    r"my notes|my notebook|notebook entries|entries|"
    r"average|highest|lowest|maximum|minimum|how many (?:samples|entries|readings))\b")
_MEASUREMENT = re.compile(r"(?i)\b\d+(?:\.\d+)?\s*(?:°\s?[CF]|[CF]\b|ph\b|mg/?l\b|ppm\b|ntu\b|%|cm\b|mm\b|km\b|ml\b)|\bph\s*(?:of\s*)?\d")
_PLACE = re.compile(r"(?i)\b(?:site|creek|river|pond|lake|sample|station|transect|plot|well|stream|spring|marsh|bank)\b")
_QUESTION = re.compile(r"(?i)^(?:what|why|how|when|who|which|explain|tell me about|is|are|does|do|can you explain|should)\b")
_ABOUT_ME = re.compile(r"(?i)\b(?:did i|have i|i (?:recorded|logged|told you)|did i tell you|you remember|"
                       r"my (?:notebook|log|samples|notes|files?|workspace|memory|[\w ]{1,20} samples)|"
                       r"in my [\w ]{1,25}(?:samples|notebook|notes)|[\w-]+\.(?:txt|md|csv|json))\b")


def might_be_action(text: str) -> bool:
    """Cheap first check, so plain chat never pays for the model step."""
    t = (text or "").strip()
    if not t or len(t) > 600 or t.startswith(("/", "@")):
        return False
    if _QUESTION.match(t) and not _ABOUT_ME.search(t):
        return False
    return bool(_ACTION_WORDS.search(t) or (_MEASUREMENT.search(t) and _PLACE.search(t)))


# ── the actions Cursiv knows ─────────────────────────────────────────────────

@dataclass(frozen=True)
class Action:
    name: str
    changes: bool               # True: needs the confirm card
    title: str                  # card heading
    template: str               # canonical command, filled from the slots
    slots: tuple[str, ...]


ACTIONS: dict[str, Action] = {a.name: a for a in (
    Action("notebook.log", True, "Save to your field notebook?", "log {details}", ("details",)),
    Action("notebook.search", False, "Search your field notebook", "Find the observation about {words}", ("words",)),
    Action("notebook.today", False, "What you recorded today", "What did I record today?", ()),
    Action("notebook.average", False, "Work out from your notebook",
           "What was the {kind} {measure} in my {scope} samples?", ("kind", "measure", "scope")),
    Action("memory.save", True, "Remember this?", "remember {fact}", ("fact",)),
    Action("memory.forget", True, "Forget this?", "forget {words}", ("words",)),
    Action("file.read", False, "Read a file", "file read {path}", ("path",)),
    Action("file.list", False, "List your workspace", "file list", ()),
    Action("file.create", True, "Create this file?", "file create {path} :: {text}", ("path", "text")),
    Action("file.append", True, "Add to this file?", "Add a line to {path} saying {text}", ("path", "text")),
    Action("workspace.set", True, "Work in this folder? (file access on)", "workspace {folder} and files on", ("folder",)),
    Action("offline.on", True, "Turn offline mode on?", "offline on", ()),
    Action("offline.off", True, "Turn offline mode off?", "offline off", ()),
)}

PROMPT = """You turn a person's message into ONE Cursiv action, or none. You never answer the message.

Actions (name: what to fill in):
- notebook.log: details = the observation as "site: <place>; <measurement> <value> <unit>; note: <words>"
  using ONLY words and numbers the person wrote (leave out site: if they gave no place)
- notebook.search: words = what to look for in their field notebook
- notebook.today: (nothing) -- what they recorded today
- notebook.average: kind = average|minimum|maximum|median, measure = e.g. "water temp", scope = sample-ID prefix or site
- memory.save: fact = what to remember, in the person's own words
- memory.forget: words = which memory to forget
- file.read: path = the file name they gave
- file.list: (nothing) -- list their workspace folder
- file.create: path = the file name they gave, text = the exact text to put in it
- file.append: path = the file name they gave, text = the exact line to add
- workspace.set: folder = the folder they named, exactly as they wrote it
- offline.on / offline.off: (nothing)

Use only what the person wrote; never invent numbers, names, files or folders. If something needed is
missing, or the message is a general question, a story, a hypothetical, a joke, or talks ABOUT logging
or files without asking for it, the answer is none. A reading with a place and a number (a temperature,
pH, depth, count) is an observation to log even when they don't say "log". Questions about what they
logged, recorded or measured are about the notebook, not memory.

Examples:
"Beaver Dam outflow 8.7 C, foam on the surface" -> {"action": "notebook.log", "slots": {"details": "site: Beaver Dam outflow; water temp 8.7 C; note: foam on the surface"}}
"keep this one: Mill Race nitrate 2.1 mg/L" -> {"action": "notebook.log", "slots": {"details": "site: Mill Race; nitrate 2.1 mg/L"}}
"have I written anything about otters?" -> {"action": "notebook.search", "slots": {"words": "otters"}}
"what's the mean depth across my Q1 plots?" -> {"action": "notebook.average", "slots": {"kind": "average", "measure": "depth", "scope": "Q1"}}
"remember my waders are size 11" -> {"action": "memory.save", "slots": {"fact": "my waders are size 11"}}
"stick 'Plot 9 flagged' at the end of plan.txt" -> {"action": "file.append", "slots": {"path": "plan.txt", "text": "Plot 9 flagged"}}
"OK, internet's fine now" -> {"action": "offline.off", "slots": {}}
"my uncle used to log timber up north" -> {"action": "none", "slots": {}}
"Would 9 C water be too cold for wading all day?" -> {"action": "none", "slots": {}}

Reply with JSON only: {"action": "<name>" or "none", "slots": {...}}"""


@dataclass
class Proposal:
    action: Action
    slots: dict
    command: str
    problems: list[str] = field(default_factory=list)

    @property
    def needs_confirm(self) -> bool:
        return self.action.changes

    @property
    def ok(self) -> bool:
        return not self.problems

    def card_lines(self) -> list[str]:
        if self.action.name == "notebook.log":
            return [p.strip() for p in self.slots.get("details", "").split(";") if p.strip()]
        if self.action.name in ("file.create", "file.append"):
            return [f"File: {self.slots.get('path', '')}", f"Text: {self.slots.get('text', '')}"]
        return [v for v in (str(x) for x in self.slots.values()) if v]


# ── checking a proposal against the person's own words ───────────────────────

def _norm(text: str) -> str:
    text = (text or "").casefold().replace("°", " ").replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[\"“”]", "", text)).strip()


def _numbers(text: str) -> set[str]:
    out = set()
    for n in re.findall(r"-?\d+(?:[.,]\d+)?", text or ""):
        n = n.replace(",", ".")
        out.add(n)
        try:
            out.add(repr(float(n)).rstrip("0").rstrip("."))
        except ValueError:
            pass
    return out


_FILLER = {"the", "that", "this", "and", "for", "with", "you", "your", "they", "their", "user", "person",
           "prefers", "likes", "has", "have", "are", "was", "were", "who", "his", "her", "its", "my", "i'm", "is"}


def check(action: Action, slots: dict, said: str) -> list[str]:
    """Problems with a proposal. Empty means it may be shown (or, if read-only, run)."""
    problems = []
    said_n = _norm(said)
    said_numbers = _numbers(said)
    for name in action.slots:
        value = str(slots.get(name, "")).strip()
        if not value:
            problems.append(f"missing {name}")
            continue
        if len(value) > 2000:
            problems.append(f"{name} is too long")
        for raw in re.findall(r"-?\d+(?:[.,]\d+)?", value):
            if not (_numbers(raw) & said_numbers):          # 14.2 matches 14.20; 15.0 never matches 14.2
                problems.append(f"the number {raw} isn't in what you wrote")
                break
    if action.name in ("file.read", "file.create", "file.append"):
        path = str(slots.get("path", ""))
        base = re.split(r"[\\/]", path)[-1]
        if _norm(base) not in said_n:
            problems.append("that file name isn't in what you wrote")
        if re.search(r"(?:^|[\\/])\.\.(?:[\\/]|$)|^[\\/]|^[a-z]:", path, re.I):
            problems.append("only files inside your workspace")
    if action.name == "memory.forget" and not re.search(
            r"(?i)^(?:please\s+|ok,?\s+|you can\s+|can you\s+)?(?:forget|delete|remove|erase|drop)\b|"
            r"\bforget (?:what|that|about|the|my|everything i)\b|\b(?:delete|remove) (?:the|that|my) memory\b", said):
        problems.append("that doesn't sound like a request to forget a memory")
    if action.name in ("file.create", "file.append"):
        text = _norm(slots.get("text", "")).rstrip(".!")
        if text and text not in said_n:
            problems.append("the text to write isn't in what you wrote")
    if action.name == "workspace.set":
        folder = _norm(slots.get("folder", ""))
        if folder and folder not in said_n:
            problems.append("that folder isn't in what you wrote")
    if action.name in ("memory.save", "memory.forget", "notebook.search"):
        key = next(iter(action.slots))
        words = [w for w in re.findall(r"[a-z0-9'-]{3,}", _norm(slots.get(key, ""))) if w not in _FILLER]
        if words and sum(w in said_n for w in words) / len(words) < 0.6:
            problems.append("that isn't what you said")
    if action.name == "notebook.log":
        details = slots.get("details", "")
        if not re.search(r"\d|note\s*:", details, re.I):
            problems.append("no measurement or note to save")
        site = re.search(r"(?i)site\s*:\s*([^;]+)", details)
        if site and _norm(site.group(1)) not in said_n:
            problems.append("that site name isn't in what you wrote")
        note = re.search(r"(?i)note\s*:\s*([^;]+)", details)
        if note:
            words = [w for w in re.findall(r"[a-z0-9'-]{3,}", _norm(note.group(1))) if w not in _FILLER]
            if words and sum(w in said_n for w in words) / len(words) < 0.6:
                problems.append("the note isn't what you wrote")
    if action.name == "notebook.average" and _norm(slots.get("kind", "")) not in (
            "average", "mean", "minimum", "maximum", "median", "highest", "lowest"):
        problems.append("that isn't a calculation Cursiv does")
    return problems


def find_folder(name: str, homes=None) -> list:
    """Folders called `name` (any case) in the places people keep work: the home
    folder, Documents and Desktop (also under OneDrive), one and two levels down.
    A full path that exists is returned as it is."""
    import os
    from pathlib import Path
    raw = (name or "").strip().strip('"').strip("'")
    raw = re.sub(r"(?i)^(?:my|the)\s+|\s+folder$", "", raw).strip()
    if not raw:
        return []
    direct = Path(os.path.expandvars(raw)).expanduser()
    if direct.is_absolute():
        return [direct] if direct.is_dir() else []
    home = Path(os.environ.get("CURSIV_REAL_HOME") or Path.home())
    bases = homes if homes is not None else [home, home / "Documents", home / "Desktop", home / "OneDrive",
                                            home / "OneDrive" / "Documents", home / "OneDrive" / "Desktop"]
    want, found = raw.casefold(), []
    for base in bases:
        try:
            first = [p for p in Path(base).iterdir() if p.is_dir() and not p.name.startswith(".")]
        except OSError:
            continue
        for p in first:
            if p.name.casefold() == want:
                found.append(p)
            try:
                found += [q for q in p.iterdir() if q.is_dir() and q.name.casefold() == want]
            except OSError:
                pass
    return list(dict.fromkeys(found))


def _log_details(slots: dict) -> str:
    """The model often splits an observation into its own keys ({"site": …, "measurement":
    …, "value": …, "note": …}) instead of one details string. Put them back together;
    check() then holds every word and number to what the person wrote, as usual."""
    if isinstance(slots.get("details"), str) and slots["details"].strip():
        return slots["details"]
    src = slots.get("details") if isinstance(slots.get("details"), dict) else slots
    parts = []
    site = src.get("site") or src.get("place") or src.get("location")
    if site:
        parts.append(f"site: {site}")
    sample = src.get("sample") or src.get("sample_id")
    if sample:
        parts.append(f"sample ID: {sample}")
    measures = src.get("measurements") or src.get("measurement")
    if isinstance(measures, list):
        for m in measures:
            if isinstance(m, dict):
                parts.append(" ".join(str(m.get(k, "")) for k in ("name", "value", "unit")).strip())
            else:
                parts.append(str(m))
    elif isinstance(measures, dict):
        parts.append(" ".join(str(measures.get(k, "")) for k in ("name", "value", "unit")).strip())
    elif measures:
        value = src.get("value")
        unit = src.get("unit") or ""
        parts.append(" ".join(str(x) for x in (measures, value if value is not None else "", unit) if str(x)).strip())
    elif src.get("value") is not None:
        parts.append(f"{src.get('value')} {src.get('unit') or ''}".strip())
    note = src.get("note") or src.get("notes") or src.get("observation")
    if note:
        parts.append(f"note: {note}")
    return "; ".join(p for p in parts if p)


def build(action_name: str, slots: dict, said: str) -> Proposal | None:
    action = ACTIONS.get(action_name)
    if action is None:
        return None
    if action.name == "notebook.log":
        slots = {"details": _log_details(slots)}
    clean = {k: re.sub(r"\s+", " ", str(slots.get(k, ""))).strip().strip('"').strip() for k in action.slots}
    problems = check(action, clean, said)
    if action.name == "workspace.set" and not problems:
        matches = find_folder(clean["folder"])
        if len(matches) == 1:
            clean["folder"] = str(matches[0])
        elif not matches:
            problems.append(f"I couldn't find a folder called “{clean['folder']}”; give its full path")
        else:
            problems.append("more than one folder has that name: " + "; ".join(str(m) for m in matches[:3]))
    command = action.template.format(**clean) if action.slots else action.template
    return Proposal(action, clean, command, problems)


def propose(text: str, ask: Callable[[list[dict]], str], workspace: str = "") -> Proposal | None:
    """Ask the model for one action; None when it isn't one (or the model is unsure).
    A proposal with problems is returned so the card can say why it wasn't offered."""
    if not might_be_action(text):
        return None
    try:
        from . import guidance                     # U100: the person's own words and folder map
        extra = guidance.prompt_block(workspace)
    except Exception:
        extra = ""
    try:
        raw = ask([{"role": "system", "content": PROMPT + extra}, {"role": "user", "content": text[:1500]}]) or ""
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        return None
    if not isinstance(data, dict) or str(data.get("action", "none")).lower() in ("", "none", "null"):
        return None
    slots = data.get("slots") if isinstance(data.get("slots"), dict) else {}
    try:
        from . import guidance
        said = guidance.expand(text)               # "the creek" -> also "North Creek", from how-i-talk.md
    except Exception:
        said = text
    return build(str(data.get("action")), slots, said)

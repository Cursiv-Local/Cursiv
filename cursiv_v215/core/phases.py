"""
Cursiv's 8 phases as running code -- one pass per message, before the model is called.

  Energy        notice stress, exhaustion or rush -> shorter, gentler reply
  Emergency     notice a crisis -> care first, real help lines shown up front
  Grounding     the person's relevant memories (memory/semantic.py)
  Route         what kind of answer: direct, code, or a decision worth the council
  Structure     the shape of the answer: steps, direct yes/no, comparison, explanation
  Connectivity  online? local model ready? (recorded for routing and the trace)
  Future State  when the person is working toward something: end with one next step
  Recovery      long or late sessions: one gentle break suggestion per session

run() returns the instructions for the system prompt, any fixed text to show
before/after the reply, and a trace -- the "phases" command shows the last one.
Every phase is plain, inspectable rules; nothing here calls an AI model.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

# ── Session state (one Cursiv session = this process) ───────────────────────
_session = {"start": time.time(), "messages": 0, "break_suggested": False, "council_hinted": False}
_last_trace: list[tuple[str, str]] = []


@dataclass
class PhaseResult:
    instructions: list[str] = field(default_factory=list)   # added to the system prompt
    memory: str = ""                                        # Grounding block
    before_reply: str = ""                                  # shown above the model's reply
    after_reply: str = ""                                   # shown below it
    emergency: bool = False
    emergency_kind: str = ""          # "crisis", "medical" or "danger"
    trace: list[tuple[str, str]] = field(default_factory=list)

    def system_addendum(self) -> str:
        parts = []
        if self.instructions:
            parts.append("## How to answer this message (Cursiv's phases)\n" + "\n".join(f"- {i}" for i in self.instructions))
        if self.memory:
            parts.append("## What you remember (Grounding)\n" + self.memory)
        return "\n\n".join(parts)


def _has(text: str, patterns) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


# ── 1. Energy ───────────────────────────────────────────────────────────────
_LOW_ENERGY = [r"\bexhausted\b", r"\bso tired\b", r"\bdrained\b", r"\boverwhelmed\b", r"\bburn(?:ed|t)\s*out\b",
               r"\bstressed\b", r"\bcan'?t (?:sleep|focus|think)\b", r"\banxious\b", r"\bfrustrated\b",
               r"\bfed up\b", r"\bat my wit'?s end\b", r"\bfalling apart\b"]
_RUSH = [r"\basap\b", r"\burgent(?:ly)?\b", r"\bhurry\b", r"\bquick(?:ly)?\b", r"\bdeadline\b", r"\bright now\b",
         r"\bin a rush\b", r"\bno time\b"]


def _energy(text: str, now: time.struct_time, r: PhaseResult) -> None:
    letters = [c for c in text if c.isalpha()]
    shouting = len(letters) > 12 and sum(c.isupper() for c in letters) / len(letters) > 0.6
    low = _has(text, _LOW_ENERGY)
    rush = _has(text, _RUSH) or ("!!" in text)
    late = 0 <= now.tm_hour < 5
    if low or shouting:
        r.instructions.append("The person seems stressed or worn out. Be warm and calm, keep it short and easy to read, "
                              "and don't pile on extra options.")
        r.trace.append(("Energy", f"low/strained (\"{low or 'all caps'}\") -> shorter, gentler reply"))
    elif rush:
        r.instructions.append("The person is in a hurry. Lead with the answer in the first sentence; skip background.")
        r.trace.append(("Energy", "rushed -> answer first, no preamble"))
    elif late:
        r.instructions.append("It's the middle of the night for the person. Keep the reply compact.")
        r.trace.append(("Energy", f"late night ({now.tm_hour}:{now.tm_min:02d}) -> compact reply"))
    else:
        r.trace.append(("Energy", "steady"))


# ── 2. Emergency ────────────────────────────────────────────────────────────
_CRISIS = [r"\b(?:kill|hurt|harm)\s+my\s?self\b", r"\bsuicid(?:e|al)\b", r"\bend (?:it all|my (?:own )?life)\b",
           r"\b(?:don'?t|do not) want to (?:live|be alive|be here)\b", r"\bwant to die\b", r"\bself[- ]harm\b",
           r"\bcut(?:ting)? myself\b", r"\b(?:took|take|taking|taken|going to take) (?:an |a )?overdose\b", r"\boverdos(?:ed|ing) on\b", r"\bno reason to live\b", r"\bbetter off without me\b"]
_MEDICAL = [r"\bchest pain\b", r"\bcan'?t breathe\b", r"\bhaving a (?:stroke|seizure|heart attack)\b",
            r"\bunconscious\b", r"\bnot breathing\b", r"\bbleeding (?:a lot|heavily|badly)\b", r"\bswallowed (?:poison|bleach)\b",
            r"\b(?:spurting|gushing|pouring|squirting) blood\b", r"\bblood (?:is )?(?:spurting|gushing|pouring|everywhere)\b",
            r"\bwon'?t stop bleeding\b", r"\bbleeding (?:won'?t|will not|doesn'?t|isn'?t) stop", r"\bbleeding out\b",
            # "I think my husband has hypothermia" got the slow check and a wrong note (Phase 1, 2026-10-18)
            r"\bhypotherm\w*\b", r"\bheat ?stroke\b", r"\bchoking\b", r"\bunresponsive\b",
            r"\b(?:won'?t|can'?t|cannot) (?:wake (?:him|her|them) up|be woken)\b", r"\ballergic reaction\b",
            r"\b(?:throat|tongue|face) is swelling\b", r"\banaphyla\w*\b", r"\b(?:snake ?bite|bitten by a snake|snake bit)\b",
            r"\bdrown\w*\b", r"\belectrocuted\b", r"\bhaving a seizure\b|\bseizing\b"]
_DANGER = [r"\b(?:he|she|they|someone)(?:'s| is| are)? (?:hurting|beating|threatening) me\b", r"\bbeing abused\b",
           r"\bthreaten(?:ed|ing) to kill\b", r"\bnot safe at home\b"]

CRISIS_TEXT = ("**If you're thinking about ending your life or hurting yourself, you don't have to face it alone.** "
               "Call or text **988** (Suicide & Crisis Lifeline, US) any time, or text **HOME** to **741741**. "
               "If you're in immediate danger, call **911**.")
MEDICAL_TEXT = ("**If this is a medical emergency, call 911 (or your local emergency number) now.** "
                "For a poisoning, US Poison Control is **1-800-222-1222**.")
DANGER_TEXT = ("**If you're in danger, call 911.** The National Domestic Violence Hotline is **1-800-799-7233** "
               "(or text **START** to **88788**).")


def _emergency(text: str, r: PhaseResult) -> None:
    for patterns, notice, kind in ((_CRISIS, CRISIS_TEXT, "possible crisis"), (_MEDICAL, MEDICAL_TEXT, "possible medical emergency"),
                                   (_DANGER, DANGER_TEXT, "possible danger")):
        hit = _has(text, patterns)
        if hit:
            r.emergency = True
            r.emergency_kind = {"possible crisis": "crisis", "possible medical emergency": "medical"}.get(kind, "danger")
            r.before_reply = notice + "\n\n"
            if r.emergency_kind == "medical":
                # Help may be far away: give the few steps that matter while it comes.
                r.instructions.insert(0, "IMPORTANT: this may be a medical emergency. Start by telling them to call 911 "
                                         "(or their local emergency number) now if they haven't. Then give only the few "
                                         "most important first-aid steps for right now, numbered, short and plain, from "
                                         "Cursiv's offline reference when it has an entry. Stay calm and kind. No long "
                                         "explanations, and don't guess at anything the reference doesn't cover.")
            else:
                r.instructions.insert(0, "IMPORTANT: the person may be in crisis or danger. Respond with real warmth and care, "
                                         "take them seriously, keep it simple, gently encourage reaching out to the help line "
                                         "shown above and to someone they trust, and ask if they're safe right now. "
                                         "Don't lecture, don't change the subject, don't give clinical detail.")
            r.trace.append(("Emergency", f"{kind} (\"{hit}\") -> help lines shown first, care-first reply"))
            return
    r.trace.append(("Emergency", "none"))


# ── 3. Grounding ────────────────────────────────────────────────────────────
def _grounding(text: str, r: PhaseResult, memory_fn) -> None:
    mem = ""
    if memory_fn and len(text.strip()) >= 10:
        try:
            mem = memory_fn(text) or ""
        except Exception:
            mem = ""
    r.memory = mem
    lines = [l for l in mem.splitlines() if l.strip().startswith("- ")]
    note = (f"{len(lines)} memor{'y' if len(lines) == 1 else 'ies'} recalled" if mem
            else "nothing relevant in memory")
    try:
        from cursiv_v215.core.verify import needs_ledger
        if needs_ledger(text):
            note += "; assumption ledger required"
    except Exception:
        pass
    r.trace.append(("Grounding", note))


# ── 4. Route ────────────────────────────────────────────────────────────────
_DECISION = [r"\bshould i\b", r"\bshould we\b", r"\bpros and cons\b", r"\bwhich (?:one )?(?:is better|should)\b",
             r"\bhelp me (?:decide|choose)\b", r"\bis it worth\b", r"\bwhat would you do\b"]
_CODE = [r"```", r"\bdef \w+\(", r"\btraceback\b", r"\b(?:python|javascript|sql|powershell|bash)\b", r"\berror:\s"]


def _route(text: str, r: PhaseResult) -> None:
    if _has(text, _CODE):
        r.instructions.append("This is a coding question: give working code with a one-line explanation of each important part.")
        r.trace.append(("Route", "code"))
    elif _has(text, _DECISION):
        if not _session["council_hinted"]:
            _session["council_hinted"] = True
            r.after_reply = "\n\n*For several perspectives on a decision like this, try:* `council " + text.strip()[:80] + "`"
            r.trace.append(("Route", "decision -> direct answer, council suggested"))
        else:
            r.trace.append(("Route", "decision -> direct answer"))
        r.instructions.append("This is a decision: give a clear recommendation and the main reason, then the strongest reason "
                              "against it.")
    else:
        r.trace.append(("Route", "direct"))


# ── 5. Structure ────────────────────────────────────────────────────────────
def _structure(text: str, r: PhaseResult) -> None:
    t = text.strip().lower()
    if re.match(r"^(how (do|can|should) i|how to|steps to|walk me through|set ?up|install)\b", t):
        r.instructions.append("Format: numbered steps, one action per step.")
        r.trace.append(("Structure", "how-to -> numbered steps"))
    elif re.search(r"\b(vs\.?|versus|compare|difference between|differ)\b", t):
        r.instructions.append("Format: compare side by side (a short list or table), then a one-line takeaway.")
        r.trace.append(("Structure", "comparison -> side by side"))
    elif re.match(r"^(is|are|can|does|do|should|will|was|did|has|have)\b", t) and len(t) < 160:
        r.instructions.append("Format: answer yes or no (or the direct answer) in the first sentence, then explain briefly.")
        r.trace.append(("Structure", "direct question -> answer first"))
    elif re.match(r"^(why|explain|what is|what are|what's)\b", t):
        r.instructions.append("Format: a short, clear explanation in plain language; an example if it helps.")
        r.trace.append(("Structure", "explanation -> plain short paragraphs"))
    else:
        r.trace.append(("Structure", "conversational"))


# ── 6. Connectivity ─────────────────────────────────────────────────────────
_conn_cache: dict = {"t": 0.0, "online": None}


def _connectivity(r: PhaseResult, online_fn, local_fn) -> None:
    if online_fn is None:
        r.trace.append(("Connectivity", "unknown"))
        return
    # online_fn returns None when it chose not to probe (offline mode, or nothing
    # this turn would use the internet). That isn't cached, so turning a cloud
    # feature on is seen on the next message.
    online = _conn_cache["online"]
    if time.time() - _conn_cache["t"] > 60 or online is None:
        try:
            v = online_fn()
        except Exception:
            v = None
        online = None if v is None else bool(v)
        if online is not None:
            _conn_cache["online"], _conn_cache["t"] = online, time.time()
    local = None
    try:
        local = bool(local_fn()) if local_fn else None
    except Exception:
        pass
    r.trace.append(("Connectivity", f"{'online' if online else 'offline' if online is False else 'not checked'}"
                                    f", local model {'ready' if local else 'not ready' if local is False else 'unknown'}"))


# ── 7. Future State ─────────────────────────────────────────────────────────
_GOAL = [r"\bi want to\b", r"\bi'?m trying to\b", r"\bmy goal\b", r"\bi'?m (?:working on|building|planning|starting)\b",
         r"\bhelp me (?:build|start|plan|make|get)\b", r"\bhow can i (?:get|become|improve|grow|start)\b"]


def _future(text: str, r: PhaseResult) -> None:
    if r.emergency:
        r.trace.append(("Future State", "skipped (emergency)"))
        return
    hit = _has(text, _GOAL)
    if hit:
        r.instructions.append("The person is working toward something: end with ONE concrete next step they can take today.")
        r.trace.append(("Future State", f"goal (\"{hit}\") -> one next step"))
    else:
        r.trace.append(("Future State", "none"))


# ── 8. Recovery ─────────────────────────────────────────────────────────────
def _break_notes_on() -> bool:
    """Settings -> How Cursiv answers -> "Suggest a break late at night or after long sessions"."""
    try:
        from cursiv_v215.chat import keys
        return keys.saved_key("break_notes") != "off"
    except Exception:
        return True


def _recovery(now: time.struct_time, r: PhaseResult) -> None:
    _session["messages"] += 1
    minutes = (time.time() - _session["start"]) / 60
    late = 0 <= now.tm_hour < 5
    due = (_session["messages"] >= 30 or minutes >= 120 or (late and _session["messages"] >= 8))
    if due and not _session["break_suggested"] and not r.emergency and _break_notes_on():
        _session["break_suggested"] = True
        why = "it's late" if late else f"we've been at it for {int(minutes)} minutes" if minutes >= 120 else f"that's {_session['messages']} messages"
        r.after_reply += f"\n\n*({why} — a short break, some water or a stretch might help. I'll be right here.)*"
        r.trace.append(("Recovery", f"break suggested ({why})"))
    else:
        r.trace.append(("Recovery", f"ok ({_session['messages']} messages, {int(minutes)} min)"))


# ── Run all eight ───────────────────────────────────────────────────────────
def run(text: str, memory_fn=None, online_fn=None, local_fn=None, now: time.struct_time | None = None) -> PhaseResult:
    global _last_trace
    now = now or time.localtime()
    r = PhaseResult()
    text = text or ""
    _energy(text, now, r)
    _emergency(text, r)
    _grounding(text, r, memory_fn)
    _route(text, r)
    _structure(text, r)
    _connectivity(r, online_fn, local_fn)
    _future(text, r)
    _recovery(now, r)
    _last_trace = list(r.trace)
    return r


def last_trace_text() -> str:
    if not _last_trace:
        return "No message has gone through the phases yet this session."
    return "How Cursiv's 8 phases handled your last message:\n" + "\n".join(f"  {i}. {name}: {what}" for i, (name, what) in enumerate(_last_trace, 1))

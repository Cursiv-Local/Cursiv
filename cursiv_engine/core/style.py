"""
How each person wants Cursiv to talk -- learned from their corrections, plus a
tone they can pick.

  * Corrections ("too formal", "stop using bullet points", "no, I meant…",
    "keep it shorter") become short standing rules, saved per person.
  * `tone blunt|warm|brief|playful|legacy|teacher|normal` sets a default tone.
  * Rules + tone are added to every reply's instructions.
  * `style` shows them; `style forget <words>` / `style clear` remove them.

Stored in ~/.cursiv/style/<person>.json -- plain files on the computer.
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Callable

DIR = Path.home() / ".cursiv" / "style"
MAX_RULES = 15
PROMPT_HEADING = '## Current answer style'
_lock = threading.Lock()

TONES = {
    "normal": "",
    "warm": "Be warm and encouraging, like a kind friend, while staying direct and truthful.",
    "blunt": "Be blunt and efficient: facts and recommendations only, no pleasantries, no cushioning, no filler.",
    "brief": "Keep every answer as short as possible: a few sentences or a short list. Offer more only if asked.",
    "playful": "Be light and playful, with a little humor, while still being accurate and useful.",
    "legacy": "Frame answers in terms of family, long-term value and what lasts; thoughtful and grounded.",
    "teacher": "Teach: explain step by step in plain words, check understanding, and give a small example.",
}

_CORRECTION_RE = re.compile(
    r"\b(too (formal|long|wordy|short|casual|technical|vague|much|preachy|robotic)|"
    r"(stop|quit|don'?t|do not|never|please don'?t) (\w+ ){0,3}(saying|using|calling|giving|doing|adding|asking|"
    r"repeating|lecturing|starting|ending|use|say|call|give|add|ask|repeat|start|end|put|make|include)|"
    r"no,? (i meant|that'?s (not|wrong))|that'?s not what i (asked|meant|wanted)|i (already )?(said|told you)|"
    r"(be|sound) (more|less) \w+|(more|less) (casual|formal|detail|detailed|direct|concise)|"
    r"(shorter|simpler|plainer) (answers?|please|replies)|just (give|tell) me|"
    r"from now on|always (use|give|start|answer|call)|i (prefer|like it when|don'?t like|hate it when))\b",
    re.I)


def _path(person: str) -> Path:
    return DIR / (re.sub(r"[^a-z0-9_-]", "_", (person or "family").lower()) + ".json")


def load(person: str) -> dict:
    from . import state_store
    data = state_store.load(_path(person), {'tone': 'normal', 'rules': []})
    if not isinstance(data, dict) or not isinstance(data.get('rules'), list):
        raise ValueError('Invalid style preferences; existing data preserved')
    return data


def _save(person: str, data: dict) -> None:
    from . import state_store
    state_store.save(_path(person), data)


def looks_like_correction(text: str) -> bool:
    t = (text or "").strip()
    return 4 <= len(t) <= 600 and bool(_CORRECTION_RE.search(t))


def add_rule(person: str, rule: str, source: str = "learned") -> bool:
    rule = " ".join((rule or "").split()).strip(" -•\"'")[:200]
    if len(rule) < 6:
        return False
    with _lock:
        data = load(person)
        low = rule.lower()
        if any(r["text"].lower() == low for r in data["rules"]):
            return False
        data["rules"] = (data["rules"] + [{"text": rule, "source": source, "t": time.time()}])[-MAX_RULES:]
        _save(person, data)
    return True


_LEARN_PROMPT = (
    "The user just corrected how an AI assistant talks or behaves. Turn the correction into 1 short standing rule "
    "the assistant should follow from now on (e.g. \"Keep answers under 5 sentences\", \"Don't use bullet lists\", "
    "\"Call him Josh\"). Only rules about style, format, tone, names or habits — not one-time facts about the current "
    "task. If the message isn't really a lasting preference, reply NONE. Reply with the rule only."
)


def learn_correction(person: str, user_text: str, previous_reply: str, ask: Callable[[list[dict]], str]) -> str | None:
    """Background: correction -> standing rule (AI-worded; falls back to the user's own words)."""
    from cursiv_engine.memory import formation
    from . import presence
    if not presence.settings(person)['adapt_style']:
        return None
    from cursiv_engine.memory.semantic import generation
    epoch = generation()
    if not formation.enabled_for(user_text):
        return None
    rule = None
    try:
        raw = ask([{"role": "system", "content": _LEARN_PROMPT},
                   {"role": "user", "content": f"Assistant's previous reply (start):\n{(previous_reply or '')[:800]}\n\n"
                                               f"User's correction:\n{user_text[:600]}"}]) or ""
        line = next((l.strip() for l in raw.splitlines() if l.strip()), "")
        if line and line.upper().strip(".") != "NONE" and not line.startswith("[") and len(line) <= 200:
            rule = line.strip("\"'* ")
    except Exception:
        pass
    if rule is None and re.search(r"\b(from now on|always|never|stop|don'?t|prefer)\b", user_text, re.I):
        rule = user_text.strip()[:160]              # their own words, when the AI isn't available
    if (rule and formation.enabled_for(user_text) and generation() == epoch
            and formation.permitted(rule) and add_rule(person, rule)):
        return rule
    return None


def set_tone(person: str, tone: str) -> str:
    tone = (tone or "").strip().lower()
    if tone not in TONES:
        return "Tones: " + ", ".join(TONES) + ". Example: tone blunt"
    with _lock:
        data = load(person)
        data["tone"] = tone
        _save(person, data)
    return ("Back to my normal tone." if tone == "normal" else f"Tone set to **{tone}**: {TONES[tone]}")


def forget(person: str, words: str) -> list[str]:
    words = (words or "").lower().strip()
    with _lock:
        data = load(person)
        gone = [r["text"] for r in data["rules"] if words and words in r["text"].lower()]
        data["rules"] = [r for r in data["rules"] if r["text"] not in gone]
        _save(person, data)
    return gone


def clear(person: str) -> None:
    with _lock:
        data = load(person)
        data["rules"] = []
        _save(person, data)


def describe(person: str) -> str:
    data = load(person)
    tone = data.get("tone", "normal")
    rules = "\n".join(f"- {r['text']}" for r in data["rules"]) or "- (none yet — I learn these when you correct me, or add one: style add <rule>)"
    return (f"**Tone:** {tone}" + (f" — {TONES[tone]}" if TONES.get(tone) else "") +
            f"\n\n**How you've asked me to talk:**\n{rules}\n\n"
            "Change tone: tone blunt / warm / brief / playful / legacy / teacher / normal\n"
            "Remove a rule: style forget <words> · Remove all: style clear")


def brief_guidance(question: str) -> str:
    """A preference for ordinary prose, never a cut-off for steps, code or safety."""
    if re.search(r'(?i)\b(?:detail\w*|examples?|essay|comprehensive|code|python|function|tables?|'
                 r'steps|warnings|step.by.step)\b|\d+[\s-]+words?\b', question):
        return ''
    return ('Brief mode: use 1–3 short sentences and about 60 words or fewer. Lead with the direct '
            'answer or distinction. No examples, repeated definitions, second explanation, summary '
            'or closing offer unless requested. Keep essential warnings, uncertainty and necessary '
            'instructions; the current request takes priority over this length preference.')


def prompt_addendum(person: str, question: str = '') -> str:
    data = load(person)
    parts = ([f"Current tone: {data.get('tone', 'normal')}. Current requests override this preference; "
              'earlier tone commands in chat are not current settings.'] if question else [])
    if TONES.get(data.get("tone", "normal")):
        parts.append(TONES[data["tone"]])
    if data.get('tone') == 'brief' and question and (guidance := brief_guidance(question)):
        parts.append(guidance)
    parts += [r["text"] for r in data.get("rules", [])]
    if not parts:
        return ""
    who = person.title() if person and person != "family" else "this person"
    return f"{PROMPT_HEADING}\nHow {who} wants you to talk (presentation only; accuracy, permissions and safety take precedence)\n" + \
           "\n".join(f"- {p}" for p in parts)


def command(text: str, person: str) -> str | None:
    """tone … / style … chat commands. None if the text isn't one."""
    t = (text or "").strip()
    low = t.lower()
    if low == "tone" or low.startswith("tone "):
        return set_tone(person, t[5:]) if len(t) > 5 else describe(person)
    if low in ("style", "my style", "style show"):
        return describe(person)
    if low.startswith("style add "):
        return "Got it — I'll follow that from now on." if add_rule(person, t[10:], "manual") else "I already follow that (or it's too short)."
    if low.startswith("style forget "):
        gone = forget(person, t[13:])
        return ("Removed:\n" + "\n".join(f"- {g}" for g in gone)) if gone else "No rule matched that."
    if low == "style clear":
        clear(person)
        return "Cleared all your style rules (tone kept)."
    return None

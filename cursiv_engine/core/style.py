"""
How each person wants Cursiv to talk -- learned from their corrections.

Cursiv keeps its base personality (codex/system_prompt.md, "How to talk").
Optional presentation presets and each person's learned preferences apply:

  * Corrections ("too formal", "stop using bullet points", "no, I meant…",
    "keep it shorter") become short standing rules, saved per person.
  * Rules are added to every reply's instructions.
  * `style` shows them; `style add`, `style forget <words>` / `style clear` change them.

Older "tone" values remain ignored; new presentation presets are explicit opt-in.

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

def presentation(person: str) -> dict:
    """New preferences are opt-in; legacy rules/default personality stay intact."""
    defaults = dict(personality='off', frequency='occasional', verbosity='default',
                    checkpoint_limit=8, checkpoint_days=14)
    raw = load(person).get('presentation', {})
    if isinstance(raw, dict):
        for key, choices in _PRESENTATION_CHOICES.items():
            if raw.get(key) in choices:
                defaults[key] = raw[key]
        for key, ceiling in (('checkpoint_limit', 20), ('checkpoint_days', 90)):
            if type(raw.get(key)) is int and 1 <= raw[key] <= ceiling:
                defaults[key] = raw[key]
    return defaults


_PRESENTATION_CHOICES = dict(personality=('off', 'professional', 'playful', 'sassy'),
                             frequency=('off', 'rare', 'occasional', 'frequent'),
                             verbosity=('default', 'concise', 'balanced', 'detailed'))


def configure_presentation(person: str, **values) -> None:
    for key, value in values.items():
        if key in _PRESENTATION_CHOICES and value in _PRESENTATION_CHOICES[key]:
            continue
        if key in ('checkpoint_limit', 'checkpoint_days') and type(value) is int and 1 <= value <= (20 if key == 'checkpoint_limit' else 90):
            continue
        raise ValueError('Invalid presentation preference')
    with _lock:
        data = load(person)
        data['presentation'] = {**presentation(person), **values}
        _save(person, data)


def sensitive_context(question: str, history=()) -> bool:
    from .conversation_kind import safety_or_technical
    context = '\n'.join([question] + [str(r.get('content', '')) for r in list(history)[-6:] if r.get('role') == 'user'])
    return safety_or_technical(context) or bool(re.search(
        r'(?i)\b(?:emergency|medical|diagnos\w*|cancer|pregnan\w*|death|died|dying|grief|grieving|'
        r'bereave\w*|funeral|abus\w*|assault|trauma|panic|depress\w*|distress|heart attack|'
        r'overdose|hazard|safety|safe|unsafe|toxic|contaminat\w*|surviv\w*|oxygen reserve|'
        r'life support|critical threshold|serious|no (?:humou?r|jokes|sarcasm)|be professional)\b', context))


def presentation_prompt(person: str, question: str, history=()) -> str:
    """One short hint on the existing answer request; never a joke generator."""
    settings = presentation(person)
    parts = []
    verbosity = settings['verbosity']
    if verbosity != 'default':
        parts.append({'concise': 'Prefer a short direct answer; omit introductions and filler.',
                      'balanced': 'Use moderate detail suited to the question.',
                      'detailed': 'Give a thorough explanation when useful.'}[verbosity] +
                     ' The current request for more or less detail takes precedence.')
    mode = settings['personality']
    if mode == 'off':
        return '\n'.join(parts)
    if mode == 'professional' or sensitive_context(question, history):
        return '\n'.join(parts + ['Use a calm professional tone. No humor, sarcasm or interruption jokes for this turn.'])
    frequency = settings['frequency']
    if frequency == 'off':
        return '\n'.join(parts + ['Use natural conversational warmth without jokes or sarcasm.'])
    # Deterministic scheduling, no RNG/service/background work. Only the first
    # normal answer immediately after a pause can acknowledge that interruption.
    import hashlib
    count = sum(r.get('role') == 'user' for r in history)
    divisor = {'rare': 7, 'occasional': 3, 'frequent': 1}[frequency]
    selected = int.from_bytes(hashlib.sha256((question + str(count)).encode()).digest()[:2], 'big') % divisor == 0
    if not selected:
        return '\n'.join(parts + ['Keep a natural warm voice; answer directly without a joke this turn.'])
    tone = 'occasional light humor' if mode == 'playful' else 'an occasional brief witty or gently sarcastic aside'
    parts.append('You may use ' + tone + ' if it fits naturally. Answer the question promptly; '
                 'at most one short aside, no lengthy lead-in. Do not mock or insult the user. '
                 'Keep your own natural voice; humor is optional, not a required template.')
    last = next((r for r in reversed(history) if r.get('role') == 'assistant'), {})
    if (last.get('interruption') or {}).get('status') == 'interrupted':
        parts.append('You may briefly acknowledge the topic change, without repeating a previous joke. '
                     'The application has preserved the paused response; never claim a tool action completed.')
    return '\n'.join(parts)

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
    data = state_store.load(_path(person), {'rules': []})
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


NO_TONES = ("Cursiv keeps one personality as its base. Optional Professional, Playful and Sassy presentation "
            "preferences, humor frequency and answer detail are in Settings → How Cursiv answers. Old tone commands "
            "do not change these settings. You can also add a rule: style add <rule>. See rules with: style")


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
    rules = "\n".join(f"- {r['text']}" for r in data["rules"]) or "- (none yet — I learn these when you correct me, or add one: style add <rule>)"
    return (f"**How you've asked me to talk:**\n{rules}\n\n"
            "Add a rule: style add <rule> · Remove a rule: style forget <words> · Remove all: style clear")


def prompt_addendum(person: str, question: str = '') -> str:
    data = load(person)
    parts = [r["text"] for r in data.get("rules", [])]
    # A confirmed user-stated presentation preference should apply on later
    # turns even when semantic recall has no topic overlap with today's question.
    # Read active records only, without creating a second style source of truth.
    from cursiv_engine.memory import semantic
    try:
        saved = semantic.list_facts(person, repair=False)
    except (OSError, ValueError):
        saved = []  # best-effort: unavailable memory must not discard explicit style rules
    for fact in saved:
        text = fact.get('text', '')
        if (fact.get('origin') == 'user_said' and
                re.search(r'(?i)\b(?:I prefer|I like|please keep)\b', text) and
                re.search(r'(?i)\b(?:replies|answers|tone|talk|conversation|casual|formal)\b', text) and
                not semantic.preference_overrides_safety(text) and text not in parts):
            parts.append(text)
    if not parts:
        return ""
    if question:
        parts.append("The current request overrides these preferences.")
    who = person.title() if person and person != "family" else "this person"
    return f"{PROMPT_HEADING}\nHow {who} wants you to talk (presentation only; accuracy, permissions and safety take precedence)\n" + \
           "\n".join(f"- {p}" for p in parts)


def command(text: str, person: str) -> str | None:
    """style … chat commands (and the retired tone command). None if the text isn't one."""
    t = (text or "").strip()
    low = t.lower()
    if low == "tone" or low.startswith("tone "):
        return NO_TONES
    if low in ("style", "my style", "style show"):
        return describe(person)
    if low.startswith("style add "):
        return "Got it — I'll follow that from now on." if add_rule(person, t[10:], "manual") else "I already follow that (or it's too short)."
    if low.startswith("style forget "):
        gone = forget(person, t[13:])
        return ("Removed:\n" + "\n".join(f"- {g}" for g in gone)) if gone else "No rule matched that."
    if low == "style clear":
        clear(person)
        return "Cleared all your style rules."
    return None

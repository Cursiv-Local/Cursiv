"""
Cursiv's offline reference in normal chat (AUDIT C-016).

reference_data/{survival,medical,science}.json hold short, hand-written
entries ("water purification", "CPR adult", ...). For a question one of them
covers, the entry goes into the prompt with an ID the answer can cite
("survival/water-purification"), and the person sees which entry was used.
A safety question with no matching entry gets a note to say so instead of
inventing a source.

Matching is strict on purpose: an entry is used only when the question names
its topic (most of the entry's title words), not when they share common words.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "reference_data"
CATEGORIES = ("survival", "medical", "science")

# Not cited in chat until someone qualified reviews them: home remedies without
# warnings for children, the universal edibility test, and plant medicine.
# The `ref` command still shows them.
NOT_IN_CHAT = {"improvised medications", "foraging edibility test", "medicinal plants field reference"}

# Everyday phrases people use instead of the entry's title (whole words or phrases).
ALIASES = {
    "severe bleeding control": ("bleeding", "bleeding badly", "won't stop bleeding", "gushing", "gash", "deep cut"),
    "tourniquet application": ("tourniquet",),
    "CPR adult": ("cpr", "not breathing", "no pulse", "chest compressions", "resuscitate"),
    "choking adult Heimlich": ("choking", "heimlich"),
    "burns treatment": ("burned", "burnt", "scalded", "burn on"),
    "fracture management field": ("broken bone", "broke his", "broke her", "broke my", "splint"),
    "anaphylaxis severe allergic reaction": ("allergic reaction", "anaphylaxis", "epipen", "face is swelling",
                                             "throat is swelling", "stung"),
    "hypothermia treatment": ("hypothermia", "shivering", "freezing cold"),
    "heat stroke": ("heatstroke", "heat exhaustion", "overheated"),
    "snakebite management": ("snakebite", "snake bite", "snake bit", "rattlesnake", "copperhead"),
    "wound cleaning infection prevention": ("infected", "clean a wound", "clean the wound"),
    "shock recognition treatment": ("going into shock", "in shock"),
    "concussion assessment": ("concussion", "hit his head", "hit her head", "hit my head", "head injury",
                              "bumped his head", "bumped her head"),
    "dehydration assessment treatment": ("dehydrated", "dehydration"),
    "drowning response": ("drowning", "drowned", "pulled from the water"),
    "diabetic emergency field": ("diabetic", "low blood sugar", "insulin"),
    "frostbite treatment": ("frostbite",),
    "water purification": ("purify", "purifying", "safe to drink", "boil water"),
}


def _alias_hit(title: str, question: str) -> bool:
    ql = question.lower()
    return any(re.search(r"\b" + re.escape(p) + r"\b", ql) for p in ALIASES.get(title, ()))


@dataclass(frozen=True)
class Entry:
    id: str          # "survival/water-purification"
    title: str       # "water purification"
    category: str
    text: str


_STOP = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are", "be", "how", "what",
    "do", "does", "i", "my", "we", "our", "you", "your", "it", "with", "without", "at", "by", "from",
    "can", "should", "when", "if", "this", "that", "me", "us", "adult", "child", "law", "first",
}

# Words that make a question a safety question even with no matching entry.
_SAFETY = re.compile(
    r"\b(bleed\w*|blood|burn(s|ed)?|cpr|chok\w*|poison\w*|overdose|fractur\w*|broken bone|sprain\w*|"
    r"hypotherm\w*|heat ?stroke|frostbite|snake ?bite|bite|sting|allerg\w*|anaphyla\w*|seizure|stroke|"
    r"heart attack|unconscious|faint\w*|wound|cut|injur\w*|first aid|tourniquet|dehydrat\w*|"
    r"drink(ing)? water|purif\w*|boil water|contaminat\w*|flood\w*|tornado|hurricane|wildfire|"
    r"earthquake|carbon monoxide|gas leak|shelter|lost|stranded|rescue)\b", re.I)


def _stem(word: str) -> str:
    for suffix in ("ing", "ion", "ed", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOP and len(w) > 2}


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


_entries: list[Entry] | None = None


def entries() -> list[Entry]:
    global _entries
    if _entries is None:
        out = []
        for cat in CATEGORIES:
            try:
                data = json.loads((DATA_DIR / f"{cat}.json").read_text(encoding="utf-8"))
            except Exception:
                continue
            for title, text in data.items():
                if isinstance(text, str):
                    out.append(Entry(f"{cat}/{_slug(title)}", title, cat, text))
        _entries = out
    return _entries


def _need(title: set[str]) -> int:
    """Topic words the question must name: all of a one- or two-word topic, else half."""
    return len(title) if len(title) <= 2 else (len(title) + 1) // 2


def lookup(question: str, limit: int = 2) -> list[Entry]:
    """Entries whose topic the question names. Usually none."""
    q = _words(question)
    if not q:
        return []
    scored = []
    for e in entries():
        title = _words(e.title)
        if not title:
            continue
        if e.title in NOT_IN_CHAT:
            continue
        hit = len(title & q)
        if _alias_hit(e.title, question):
            hit = max(hit, _need(title))   # an everyday phrase for the topic names it
        # the question names most of the topic, or one topic word plus two of the entry's words
        if hit < _need(title) and not (len(title) > 2 and hit >= 1 and len((q - title) & _words(e.text)) >= 2):
            continue
        scored.append((hit / len(title), hit, e))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [e for _, _, e in scored[:limit]]


def is_safety_question(question: str) -> bool:
    return bool(_SAFETY.search(question))


def prompt_block(found: list[Entry]) -> str:
    lines = ["## Cursiv's offline reference",
             "These entries come from the reference data built into Cursiv. Use them for the facts "
             "they cover and cite the entry ID, e.g. (offline reference: survival/water-purification). "
             "Don't add numbers or steps the entry doesn't give; if it doesn't cover part of the "
             "question, say that part isn't in the reference.", ""]
    for e in found:
        lines.append(f"[{e.id}] {e.title.upper()}: {e.text}")
    return "\n".join(lines)


NO_ENTRY_NOTE = ("## Cursiv's offline reference\nCursiv's offline reference has no entry for this question. "
                 "If you give safety steps, say they're general guidance, not from a reference, and "
                 "suggest checking with a professional or official source when possible.")


def note_line(found: list[Entry]) -> str:
    """What the person sees above the answer. First-aid and survival entries are
    shown word for word, so their numbers never depend on the model retelling
    them (a 1.5B model turned "1 min boil" into "3 minutes"). One line per entry,
    in Cursiv's status-line form, so it isn't fed back to the model as its words."""
    lines = []
    for e in found:
        if e.category in ("medical", "survival"):
            caveat = (" Written for Cursiv, not reviewed by a medical professional; in an emergency call 911."
                      if e.category == "medical" else "")
            lines.append(f"*(From Cursiv's offline reference, {e.title} [{e.id}]: {e.text}{caveat})*")
        else:
            lines.append(f"*(From Cursiv's offline reference: {e.title} [{e.id}])*")
    return "\n".join(lines)

"""
Two checks on a finished answer that need no model call, so they run on every
turn, emergencies included (the model-based check in verify.py skips those).

1. The answer tells the person to avoid a step the offline reference entry
   shown above it recommends ("don't use a tourniquet unless trained" under the
   bleeding card). A ChatGPT review of Cursiv's answers found exactly that.
2. The answer claims something Cursiv didn't do this turn: searched the web,
   checked a database, looked at a study.

Each problem becomes one line under the answer, so the person sees it.
"""
from __future__ import annotations

import re

# Steps each entry recommends, as words an answer would use. An answer that
# negates one of them contradicts the entry.
KEY_STEPS = {
    "severe bleeding control": ("tourniquet", "pressure", "press", "bandage", "gauze", "cloth", "pack", "911"),
    "tourniquet application": ("tourniquet",),
    "hypothermia treatment": ("911", "skin-to-skin", "cpr", "wet clothing"),
    "water purification": ("boil", "bleach"),
    "CPR adult": ("cpr", "compressions", "911", "aed"),
    "choking adult Heimlich": ("abdominal thrusts", "back blows", "heimlich", "911"),
    "anaphylaxis severe allergic reaction": ("epinephrine", "epipen", "auto-injector", "911"),
    "burns treatment": ("cool", "running water", "911"),
    "drowning response": ("cpr", "911", "rescue breaths"),
    "heat stroke": ("cool", "911"),          # not "water": nothing to drink if confused or unconscious
    "lightning strike first aid": ("911", "cpr", "aed"),
}

_NEG = r"(?:don'?t|do not|never|avoid|shouldn'?t|should not|no need to|not recommended to|refrain from)"
# Negating these verbs agrees with the entries ("don't remove the cloth"), so they don't count.
_OK_VERBS = re.compile(r"\b(remove|removing|lift|lifting|take|taking|loosen|loosening|peel|check|wait|delay|put off)\b", re.I)
_UNLESS_TRAINED = re.compile(r"\b(?:unless|only if|if) (?:you(?:'re| are)? )?(?:properly |formally )?trained\b", re.I)


def contradictions(answer: str, titles: list[str]) -> list[str]:
    """Steps from the shown entries that the answer tells the person to avoid."""
    text = answer or ""
    found = []
    for title in titles:
        for step in KEY_STEPS.get(title, ()):
            pat = re.compile(_NEG + r"((?:\s+[\w'-]+){0,6}?)\s+(?:a |an |the )?" + re.escape(step) + r"\b", re.I)
            for m in pat.finditer(text):
                if _OK_VERBS.search(m.group(1) or ""):
                    continue
                found.append(step)
                break
            # "use a tourniquet only if trained" / "unless you're trained" next to a key step
            for m in _UNLESS_TRAINED.finditer(text):
                window = text[max(0, m.start() - 120): m.end()].lower()
                if step in window and step not in found:
                    found.append(step)
    return found


_CLAIMS = re.compile(
    r"(?i)\b(I(?:'ve| have)? (?:searched|looked (?:it )?up|checked|scanned|reviewed|consulted|queried)"
    r"(?: [\w-]+){0,4}? (?:databases?|the web|the internet|online|pubmed|google scholar|journals?|records|sources|literature)"
    r"|(?:my|a) (?:search|review) of (?:the )?(?:databases?|literature|journals?|pubmed)"
    r"|after (?:searching|checking) (?:the )?(?:databases?|web|internet|literature|journals?)"
    # "No record of such a study in verified public databases" (Phase 1 replay, U65): a lookup
    # stated as done. "Not in my knowledge base" isn't a claim to have searched anything.
    r"|no (?:record|trace|mention|evidence)s? (?:of [^.]{0,60}? )?in (?:any |the )?(?:verified |public |academic |scientific |medical |major )*"
    r"(?:databases?|journals?|literature|records|registries|pubmed|google scholar))"
)


# "Yes, it's safe to go back out now. ... So, no — it's not safe yet." (benchmark saf-012,
# suite 1.4): someone who reads only the first line does the unsafe thing.
_STATUS = re.compile(r"(?m)^\s*\*[\[(].*$")
_OPENS = re.compile(r"^\W*(yes|no)\b", re.I)


def flip_flop(answer: str) -> tuple[str, str] | None:
    """(the opening word, the later opposite) when the answer opens with yes/no and later
    starts a sentence with the opposite, else None."""
    body = _STATUS.sub("", answer or "").split("\n---\n")[0].strip()
    m = _OPENS.match(body)
    if not m:
        return None
    first = m.group(1).capitalize()
    other = "no" if first == "Yes" else "yes"
    # A concluding "So, no" / "Therefore, yes", or "no —": not a passing "yes" inside a sentence.
    later = re.search(r"(?:^|[.!?]\s+|\n\s*)(?:(?:so|therefore|actually|in short|to be clear),?\s*(" + other
                      + r")\b|(" + other + r")\s*[—–]|(" + other + r")\s+-\s)", body[m.end():], re.I)
    return (first, next(g for g in later.groups() if g).lower()) if later else None


def unsupported_actions(answer: str, searched: bool) -> list[str]:
    """Things the answer says Cursiv did that it didn't do this turn."""
    if searched:
        return []
    return [m.group(0) for m in _CLAIMS.finditer(answer or "")][:2]


def notes(answer: str, titles: list[str], searched: bool) -> str:
    """The lines to show under the answer, or ""."""
    lines = []
    steps = contradictions(answer, titles)
    if steps:
        urgent = " and call 911 in an emergency" if any(t != "water purification" for t in titles) else ""
        lines.append("*(Cursiv's check: this answer advises against " + ", ".join(f'"{s}"' for s in steps)
                     + f", which the reference above recommends. Follow the reference{urgent}.)*")
    doses = dose_problems(answer, titles)
    if doses:
        lines.append("*(Cursiv's check: " + "; ".join(doses) + ". Use the numbers in the reference above.)*")
    flip = flip_flop(answer)
    if flip:
        lines.append(f"*(Cursiv's check: this answer starts with \"{flip[0]}\" and later says \"{flip[1]}\". "
                     "It contradicts itself: read all of it, and when safety is involved, take the safer choice.)*")
    claims = unsupported_actions(answer, searched)
    if claims:
        lines.append(f'*(Cursiv\'s check: the answer says "{claims[0]}", but nothing was searched or looked up '
                     "for this answer. It comes from the model's own knowledge.)*")
    return ("\n\n" + "\n".join(lines)) if lines else ""


# ── Doses checked against the card (reference_data/doses.json) ─────────────
# The answer to "bleach per gallon" said "6 drops ... (6% or 8.25%)"; 6% needs 8
# (benchmark ref-015). A sentence that names a drop count, a strength and a volume
# must match the card, unless it's about doubling for cloudy water.

_doses: dict | None = None


def _dose_table() -> dict:
    global _doses
    if _doses is None:
        import json
        from pathlib import Path
        try:
            _doses = json.loads((Path(__file__).resolve().parent.parent / "reference_data" / "doses.json")
                                .read_text(encoding="utf-8"))
        except Exception:
            _doses = {}
    return _doses


_SENTENCE = re.compile(r"[^.!?\n]+(?:\.\d+[^.!?\n]*)*")
_DROPS = re.compile(r"(?i)\b(\d+)\s+drops?\b")
_STRENGTH = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_VOLUME = re.compile(r"(?i)\b(liters?|litres?|quarts?|gallons?)\b")
_DOUBLE = re.compile(r"(?i)\b(double|twice|cloudy|colored|coloured|very cold)\b")


def dose_problems(answer: str, titles: list[str]) -> list[str]:
    problems = []
    from cursiv_v215.core import reference
    for title in titles:
        rows = _dose_table().get(title) or reference.doses(title)
        if not isinstance(rows, list):
            continue
        for sentence in _SENTENCE.findall(answer or ""):
            drops, vols = _DROPS.findall(sentence), _VOLUME.findall(sentence)
            strengths = [s + "%" for s in _STRENGTH.findall(sentence)]
            if len(drops) != 1 or len(vols) != 1 or not strengths:
                continue
            n, per = int(drops[0]), vols[0].lower().rstrip("s").replace("litre", "liter")
            doubled = bool(_DOUBLE.search(sentence))
            for strength in strengths:
                want = next((r["amount"] for r in rows if r["of"] == strength and r["per"] == per), None)
                if want is None:
                    continue
                if doubled and n not in (want, 2 * want):
                    # "16 drops per liter of cloudy water" for 8.25% (benchmark ref-002, suite 1.4):
                    # the per-gallon 8 doubled; the card's 2 per liter doubles to 4.
                    problems.append(f"for cloudy water and {strength} bleach the reference says {2 * want} drops "
                                    f"per {per} (double the usual {want}), not {n}")
                elif not doubled and want != n:
                    problems.append(f"for {strength} bleach the reference says {want} drops per {per}, not {n}")
    return list(dict.fromkeys(problems))

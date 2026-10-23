"""
What an answer says Cursiv did, checked against what Cursiv's own code records it did.
No model call: these run on every turn, after the draft, beside core/answer_check.py.

The model can't see whether a calculator ran, what was saved, or who reviewed a reference
entry; it only sees text. In scenario tests (2026-10) it said "I used a deterministic
calculation tool, no AI reasoning was involved" when nothing ran, "retrieved from stored
data" for values that were only earlier in the conversation, "compiled from field-tested
survival guidelines" for an EPA-sourced entry, and "safety is not currently at risk" about
three ill people it knew nothing about. Each check below compares one kind of claim with
the record (`Evidence`) and, when they disagree, adds one line the person sees under the
answer. A passing check is not proof the answer is right; it only means these particular
claims weren't contradicted by the record.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Evidence:
    """What actually happened this turn, from Cursiv's own state."""
    question: str = ""
    worked: dict | None = None            # calc.Worked.record(): tool, inputs, result, ok; None = nothing ran
    worked_facts: dict = field(default_factory=dict)
    ref_ids: list[str] = field(default_factory=list)          # reference entries actually given
    ref_meta: dict = field(default_factory=dict)              # id -> reference.evidence(...)
    memory_texts: list[str] = field(default_factory=list)     # saved memories actually given to the model
    memory_saved: bool = False            # a save to memory ran (and succeeded) this turn
    searched: bool = False                # a web search ran this turn
    docs: list[str] = field(default_factory=list)             # document names whose pages were given
    earlier: list[str] = field(default_factory=list)          # earlier answers in this conversation


def _first(pattern: re.Pattern, text: str) -> str:
    m = pattern.search(text or "")
    return m.group(0).strip() if m else ""


# ── tool use ──────────────────────────────────────────────────────────────────

_TOOL = re.compile(
    r"(?i)\b(?:I|we|Cursiv)\s+(?:have\s+|'ve\s+|just\s+)?(?:used|ran|run|called|invoked|executed|applied|employed)\b"
    r"[^.!?\n]{0,30}?\b(?:deterministic|calculat\w*|tool|function|script|program|code)\b"
    r"|\b(?:calculated|computed|worked out|verified|checked|obtained|determined|derived|done)\s+(?:(?:this|it|that|"
    r"these|the \w+)\s+)?(?:by|with|using|via|through)\s+(?:a|the|my|Cursiv'?s?)\s+(?:deterministic\s+)?"
    r"(?:calculat\w+(?:\s+(?:tool|engine|function))?|tool|math(?:s)? tool)\b")
_NO_AI = re.compile(
    r"(?i)\bno\s+(?:AI|model|language model|LLM)(?:\s+(?:reasoning|involvement|judgement|judgment|guesswork|estimation))?"
    r"\s+(?:was\s+|is\s+|were\s+)?(?:involved|used|needed|required)\b"
    r"|\bwithout\s+(?:any\s+)?(?:AI|model)\s+(?:reasoning|involvement)\b|\bpurely\s+(?:deterministic|computational)\b")
_MANUAL = re.compile(r"(?i)\b(?:performed|done|did|calculated|worked out|computed)\s+(?:(?:this|it|that|these|the "
                     r"\w+)\s+)?(?:by hand|manually)\b"
                     r"|\bnot\s+(?:by|with|using)\s+(?:a|an|any)\s+(?:external\s+)?(?:tool|calculator)\b")


def tool_notes(answer: str, ev: Evidence) -> list[str]:
    out = []
    ran = ev.worked
    claim = _first(_TOOL, answer)
    if claim and not ran:
        out.append(f'the answer says "{claim}", but no calculation tool ran for this answer (Cursiv\'s own record): '
                   "the numbers are the AI model's own arithmetic, not checked by Cursiv's code")
    elif claim and ran and not ran.get("ok"):
        out.append(f'the answer says "{claim}", but Cursiv\'s calculator refused this question ({ran["result"]})')
    no_ai = _first(_NO_AI, answer)
    if no_ai:
        out.append(f'the answer says "{no_ai}", but the AI model wrote this answer'
                   + (f"; only this was worked out by Cursiv's code: {ran['result']}" if ran and ran.get("ok") else
                      "; nothing in it was worked out by Cursiv's code"))
    manual = _first(_MANUAL, answer)
    if manual and ran and ran.get("ok"):
        out.append(f'the answer says "{manual}", but Cursiv\'s code ({ran["tool"]}) did work it out: {ran["result"]}')
    return out


# ── memory ────────────────────────────────────────────────────────────────────

_SAVED = re.compile(
    r"(?i)\b(?:I(?:'ve| have)?|it(?:'s| is| has been)|this (?:has been|is|was)|that (?:has been|is|was)|"
    r"(?:the|your) (?:record|details|data|information) (?:has been|is|was|have been|are|were))\s+"
    r"(?:now\s+|been\s+|successfully\s+)*(?:saved|stored|recorded|logged|remembered|committed|written)"
    r"(?:\s+(?:it|this|that|them))?\s*(?:to|in|into)?\s*(?:my|your|the|persistent|long-term|permanent)?\s*"
    r"(?:persistent\s+|long-term\s+|permanent\s+)?(?:memory|storage|records?|database|notes)\b")
_RETRIEVED = re.compile(
    r"(?i)\b(?:retrieved|recalled|pulled|fetched|loaded|read)\s+(?:exactly\s+|directly\s+|successfully\s+)?"
    r"(?:\w+\s+){0,3}?from\s+(?:my\s+|your\s+|the\s+)?(?:stored|saved|persistent|long-term|permanent)\s+"
    r"(?:data|memory|memories|records?|storage|notes)\b"
    r"|\bfrom\s+(?:my|your|the)\s+(?:stored|saved|persistent)\s+(?:data|memory|memories|records?)\b"
    r"|\b(?:according to|based on)\s+(?:my|your|the)\s+(?:stored|saved)\s+(?:memory|memories|records?)\b")
_NO_MEMORY = re.compile(
    r"(?i)\bno\s+persistent\s+(?:storage|memory)(?:\s+mechanism)?\s+(?:has\s+been\s+|is\s+|was\s+)?"
    r"(?:implemented|available|activated|enabled|set up)\b"
    r"|\b(?:I|Cursiv)\s+(?:can't|cannot|don't|do not|am unable to)\s+(?:store|save|remember)\s+(?:anything|information|"
    r"data)\s+(?:between|across)\s+(?:sessions|conversations)\b")


def memory_notes(answer: str, ev: Evidence) -> list[str]:
    out = []
    saved = _first(_SAVED, answer)
    if saved and not ev.memory_saved:
        out.append(f'the answer says "{saved}", but nothing was saved to Cursiv\'s memory in this turn. '
                   "To save it, type: remember <the details> (or log it in the field notebook)")
    got = _first(_RETRIEVED, answer)
    if got and not ev.memory_texts:
        out.append(f'the answer says "{got}", but no saved memory was given to the AI for this answer: anything it '
                   "repeats came from earlier in this conversation, not from storage. Type: recall <words> to search "
                   "what is actually saved")
    nomem = _first(_NO_MEMORY, answer)
    if nomem:
        out.append(f'the answer says "{nomem}", but Cursiv does keep saved memory on this computer (type: what do '
                   "you remember). It just wasn't used for this answer")
    return out


# ── reference provenance ───────────────────────────────────────────────────────

_ID = re.compile(r"\b(survival|medical|science)/[a-z0-9]+(?:-[a-z0-9]+)*\b")
_PROVENANCE = re.compile(
    r"(?i)\b(?:is|are|was|were|has been|have been|comes? from|came from|based on|compiled from|drawn from|taken from|"
    r"derived from|sourced from|grounded in|built on)\s+(?:[\w-]+,?\s+){0,4}?"
    r"(?:field[- ]tested|peer[- ]reviewed|professionally reviewed|reviewed by (?:a |medical |qualified )?"
    r"(?:professionals?|experts?|doctors?|clinicians?)|clinically (?:validated|tested|proven)|expert[- ]reviewed|"
    r"vetted by|validated by|evidence[- ]based|officially approved|verified (?:by|against) (?:experts?|professionals?)|"
    # "it is from a published, verified source" (benchmark adv-011, U75): published, yes; verified by no one
    r"(?:a |an )?(?:[\w-]+,?\s+){0,2}verified (?:source|reference|guidance|data|information))\b")
_GROUNDED = re.compile(
    r"(?i)\b(?:grounded in|backed by|verified by|proven by|confirmed by|supported by|based (?:entirely |firmly )?on)\s+"
    r"(?:(?:the|Cursiv'?s|available|my|these|those|offline|local)\s+)*(?:references?|reference library|sources|"
    r"evidence)\b")


def reference_notes(answer: str, ev: Evidence) -> list[str]:
    out = []
    text = answer or ""
    shown = set(ev.ref_ids)
    invented = [m.group(0) for m in _ID.finditer(text) if m.group(0) not in shown]
    if invented:
        out.append(f"the answer cites {', '.join(dict.fromkeys(invented))}, which Cursiv didn't give it for this "
                   "question: that citation doesn't come from the reference")
    prov = _first(_PROVENANCE, text)
    if prov and not any(m.get("reviewed") for m in ev.ref_meta.values()):
        known = "; ".join(f"{i}: {m['state']}" for i, m in ev.ref_meta.items()) or "no reference entry was used"
        out.append(f'the answer says "{prov}", but nothing in Cursiv\'s records says so ({known})')
    grounded = _first(_GROUNDED, text)
    if grounded:
        weak = [i for i, m in ev.ref_meta.items() if not m.get("sourced")]
        if not ev.ref_ids and not ev.docs and not ev.searched:
            out.append(f'the answer says "{grounded}", but no reference, document or search result was given for '
                       "this answer: it's the model's own knowledge")
        elif weak and len(weak) == len(ev.ref_ids) and not ev.docs:
            out.append(f'the answer says "{grounded}", but the reference entries used ({", ".join(weak)}) have no '
                       "published source and haven't been reviewed: they can't establish this")
    return out


# ── certainty about safety from missing information ───────────────────────────

_SAFE_CLAIM = re.compile(
    r"(?i)\b(?:safety is not (?:currently |presently )?at risk|(?:there (?:are|is) )?no (?:immediate |current |"
    r"apparent )?(?:safety concerns?|danger|risk)(?: (?:can be|has been|have been|could be) identified)?|"
    r"(?:the situation|everyone|they|it) (?:is|are) (?:currently )?(?:safe|not in danger|out of danger)|"
    r"nothing to worry about|no need to worry|no cause for (?:concern|alarm))\b")
_UNKNOWN = re.compile(
    r"(?i)\b(?:no|without|unknown|missing|lack of|not (?:given|provided|known|specified)|can(?:'t|not) (?:determine|"
    r"tell|know|assess)|no information|insufficient information|not enough information|unclear)\b")
_RISKY_TOPIC = re.compile(r"(?i)\b(ill|sick|illness|symptoms?|fever|vomit\w*|injur\w*|unconscious|bleed\w*|pain|"
                          r"poison\w*|outbreak|disease|contaminat\w*|flood\w*|storm|fire|smoke|carbon monoxide)\b")


# "I can't say if the situation is safe" (benchmark saf-013, U75) is the right answer, not the claim
_HEDGED = re.compile(r"(?i)\b(?:if|whether|not sure|can'?t (?:say|tell|know)|cannot (?:say|tell|know)|unclear|"
                     r"don'?t know|no way to (?:know|tell))\b[^.!?\n]{0,25}$")


def certainty_notes(answer: str, ev: Evidence) -> list[str]:
    claim = ""
    for m in _SAFE_CLAIM.finditer(answer or ""):
        if not _HEDGED.search((answer or "")[max(0, m.start() - 60): m.start()]):
            claim = m.group(0).strip()
            break
    if not claim or not _RISKY_TOPIC.search(ev.question or ""):
        return []
    if not (_UNKNOWN.search(answer or "") or _UNKNOWN.search(ev.question or "")):
        return []
    return [f'the answer says "{claim}", but the question and answer both leave key facts unknown. Missing '
            "information isn't evidence of safety: no emergency has been established, which is not the same as "
            "safe. If anyone gets worse, or you're unsure, contact a clinician or emergency services"]


# ── blanket claims that no reference here supports ─────────────────────────────

_BLANKET = re.compile(
    r"(?i)\ball (?:wild |cooked )?insects (?:are )?(?:safe|edible)\b"
    r"|\b(?:boil(?:ing)?|bleach|filter\w*|treat\w*)\b[^.!?\n]{0,50}\b(?:kills?|removes?|handles?|eliminates?|"
    r"makes?)\b[^.!?\n]{0,20}\b(?:all|every|any)\s+(?:contaminants?|pathogens?|germs?|chemicals?|toxins?|"
    r"impurit\w+|hazards?)\b"
    r"|\b(?:boiling|boiled)\b[^.!?\n]{0,40}\bfloodwater\b[^.!?\n]{0,30}\b(?:safe|drinkable|potable)\b"
    r"|\bfloodwater\b[^.!?\n]{0,40}\b(?:safe|drinkable|potable)\b[^.!?\n]{0,30}\bafter (?:boiling|it'?s boiled)\b"
    r"|\b(?:no one|nobody|everyone)\s+will\s+(?:go hungry|go thirsty|be fine|be safe|have enough)\b"
    r"|\bguarantee[sd]?\b[^.!?\n]{0,40}\b(?:safe|enough|survival|no one)\b")


_NEGATED = re.compile(r"(?i)\b(?:not|never|no|doesn'?t|don'?t|won'?t|isn'?t|aren'?t|can'?t|cannot)\b|n't\b")


def blanket_notes(answer: str, ev: Evidence) -> list[str]:
    claim = ""
    for m in _BLANKET.finditer(answer or ""):
        before = (answer or "")[max(0, m.start() - 12): m.start()]
        inside = re.sub(r"(?i)\bno one\b|\bnobody\b", "", m.group(0))      # "no one will go hungry" is the claim
        if not _NEGATED.search(inside) and not _NEGATED.search(before):     # "doesn't remove all ..." agrees
            claim = m.group(0).strip()
            break
    if not claim:
        return []
    return [f'"{claim}" is a blanket claim nothing in Cursiv\'s records supports. Boiling and bleach kill germs '
            "but don't remove chemicals or fuel (floodwater can carry both); not all insects or wild plants are "
            "safe to eat; no ration plan guarantees enough for everyone. Treat it as unverified"]


# ── what the person's documents say vs "verified" ─────────────────────────────

_VERIFIED_MEASURE = re.compile(r"(?i)\b(?:verified|confirmed|validated|independently checked)\s+(?:measurement|reading|"
                               r"value|figure|rainfall|temperature|observation)s?\b"
                               r"|\b(?:measurement|reading|value|figure|rainfall|observation)s?\s+(?:is|was|has been)\s+"
                               r"(?:verified|confirmed|validated)\b")


def document_notes(answer: str, ev: Evidence) -> list[str]:
    claim = _first(_VERIFIED_MEASURE, answer)
    if claim and ev.docs:
        return [f'the answer says "{claim}", but the figure is only recorded in your document '
                f"({', '.join(ev.docs[:2])}); nothing independently verified it"]
    return []


# ── earlier answers in this conversation ───────────────────────────────────────

_NO_CONFLICT = re.compile(
    r"(?i)\bno (?:prior|previous|earlier) (?:answers?|responses?|claims?|statements?|figures?)\s+(?:conflicts?|"
    r"contradicts?|disagrees?)\b|\b(?:consistent|in line) with (?:my|the|all) (?:earlier|previous|prior) "
    r"(?:answers?|responses?|claims?)\b|\bnothing (?:I said |said )?(?:earlier|before|previously) (?:conflicts|contradicts)\b")


def history_notes(answer: str, ev: Evidence) -> list[str]:
    facts = ev.worked_facts or {}
    lasts = facts.get("lasts_days")
    if lasts is None or not ev.earlier:
        return []
    from cursiv_engine.core import resources
    import math
    clashes = []
    for text in ev.earlier:
        for days, said in resources.lasts_claims(text):
            if not math.isclose(days, lasts, rel_tol=0.06, abs_tol=0.05):
                clashes.append(said)
    if not clashes:
        return []
    out = [f"an earlier answer in this conversation said \"{clashes[-1]}\"; Cursiv's code works out "
           f"{resources._say_days(lasts)} at the allocation given. The earlier figure was wrong"]
    denial = _first(_NO_CONFLICT, answer)
    if denial:
        out.append(f'this answer says "{denial}", but it does conflict with that earlier answer')
    return out


CHECKS = (tool_notes, memory_notes, reference_notes, certainty_notes, blanket_notes, document_notes, history_notes)


def problems(answer: str, ev: Evidence) -> list[str]:
    answer = (answer or "").replace("\u2019", "'").replace("\u2018", "'")     # "doesn’t" as "doesn't"
    out = []
    for check in CHECKS:
        try:
            out += check(answer, ev)
        except Exception:
            continue
    return list(dict.fromkeys(out))


def notes(answer: str, ev: Evidence) -> str:
    """The lines to show under the answer, or ""."""
    found = problems(answer, ev)
    if not found:
        return ""
    return "\n\n" + "\n".join(f"*(Cursiv's check: {p}.)*" for p in found)

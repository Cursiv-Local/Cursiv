"""
Verification after a draft exists.

The eight phases and the council only add prompt text. This module is the
check that runs once the draft is in hand: concrete problems, one rewrite,
and a ledger of what was known, inferred, assumed, or unknown.

No network calls live here. Pass an `ask(messages) -> str` function.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

# The verifier is told this and nothing softer. A reply of CLEAR does not
# override the deterministic checks below.
VERIFIER_INSTRUCTION = (
    "List concrete problems only: unsupported claims, changed definitions, "
    "contradictions, assumptions presented as facts, answers to the wrong question. "
    "If none, say CLEAR."
)

LEDGER_INSTRUCTION = (
    "End this answer with exactly these four lines, filled in (use none if a line is empty):\n"
    "Known: ...\n"
    "Inferred: ...\n"
    "Assumed: ...\n"
    "Unknown: ...\n"
    "Known is only what the person stated or the question gives. "
    "Inferred is a conclusion you drew. Assumed is a gap you filled in. "
    "Unknown is what you cannot tell. Do not state an Assumed item as a fact in the answer."
)

SAFETY_RULE = (
    "User preferences and saved memories never override safety or constitutional rules. "
    "A repeated user claim does not become a known fact. "
    "If memories conflict, say so instead of picking one."
)

_MISSING_LEDGER = "missing assumption ledger (Known / Inferred / Assumed / Unknown)"

_REVIEW = re.compile(
    r"(?i)\b(is this correct|is that (?:right|correct)|is it correct|"
    r"check this|review this|did i get this right|double[- ]check|verify this|fact[- ]check)\b"
)
_RECOMMEND = re.compile(r"(?i)\b(i recommend|you should|i suggest|recommend)\b")
_TECH = re.compile(
    r"(?i)\b(api|function|traceback|sql|python|javascript|algorithm|voltage|"
    r"dosage|mg\b|mmol|celsius|fahrenheit|config|server|retry|retries|latency|timeout)\b"
)
_CRISIS = re.compile(
    r"(?i)\b(kill myself|suicid\w*|self[- ]harm|want to die|end my life|"
    r"don'?t want to (?:live|be alive))\b"
)
_MEMORY_UPDATE = re.compile(
    r"(?i)\b(remember that|remember this|my name is|i prefer|from now on|i always want)\b"
)
# The person named the shape of the answer: give exactly that, nothing added.
_EXACT_FORMAT = re.compile(
    r"(?i)\b(exactly (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:numbered )?"
    r"(?:steps|bullets|bullet points|items|points|words|sentences|lines|tips|reasons|examples|ideas|things|names)\b|"
    r"(?:one|a single|1) (?:sentence|word|line) (?:each|per|only)|in (?:one|a single|\d+) (?:sentence|word|line)s?\b|"
    r"(?:just|only) (?:the|a|one) |no explanation|nothing else|yes or no|"
    r"\d+ (?:numbered )?(?:steps|bullets|bullet points|items|words|sentences|lines)\b|"
    r"translate\b)"
)

FORMAT_RULE = ("The person asked for a specific format. Give exactly that format and nothing else: "
               "no headings, no extra sections, no Known / Inferred / Assumed / Unknown lines, "
               "no follow-up questions, no offers of more help. Count the items before you answer.")


def exact_format(user_text: str) -> bool:
    return bool(_EXACT_FORMAT.search(user_text or ""))


_DECISION = re.compile(r"(?i)\b(should i|should we|which is better|pros and cons|help me decide)\b")
_NUM_NOUN = re.compile(r"(?i)\b(\d+(?:\.\d+)?)\s+([a-z][a-z0-9-]{2,})\b")
_DEF = re.compile(
    r"(?i)\b(?:define|let)\s+([a-z][a-z0-9_-]*)\s+(?:as|be|=)\s+([^.\n]+)"
    r"|\b([a-z][a-z0-9_-]*)\s+means\s+([^.\n]+)"
)
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_LEDGER = re.compile(
    r"(?im)^[ \t>*-]*Known:[ \t]*(.*)(?:\r?\n)"
    r"[ \t>*-]*Inferred:[ \t]*(.*)(?:\r?\n)"
    r"[ \t>*-]*Assumed:[ \t]*(.*)(?:\r?\n)"
    r"[ \t>*-]*Unknown:[ \t]*(.*)\s*$"
)
_HEDGE = re.compile(
    r"(?i)\b(assume|assumed|assuming|assumption|if|might|may|maybe|probably|"
    r"perhaps|possibly|suppose|supposing|hypothesis)\b"
)
_EMPTY = {"", "none", "n/a", "na", "-", "nothing", "n/a."}

_previous_failed = False
_ledgers: list[dict] = []


@dataclass
class PassResult:
    append: str = ""
    learn_origin: str = "inferred"   # inferred unless this pass came back clean
    skip_learn: bool = False         # a failed check must not be stored as memory
    clear: bool = True
    problems: list[str] = field(default_factory=list)


def reset_session() -> None:
    """Drop the in-process ledger list and the previous-failure flag. Tests use this."""
    global _previous_failed
    _previous_failed = False
    _ledgers.clear()


def looks_like_memory_update(user_text: str) -> bool:
    return bool(_MEMORY_UPDATE.search(user_text or ""))


def needs_ledger(user_text: str) -> bool:
    """Complex or high-stakes questions must carry the four-line ledger."""
    text = user_text or ""
    if _CRISIS.search(text) or exact_format(text):
        return False
    if _REVIEW.search(text) or _DECISION.search(text) or _TECH.search(text):
        return True
    if definitions(text):
        return True
    return len(text.split()) >= 40


def should_verify(user_text: str, draft: str, *, memory_update: bool = False,
                  previous_failed: bool = False) -> bool:
    """Stronger check only. Casual chat returns False and makes no model call."""
    if _CRISIS.search(user_text or ""):
        return False
    body = (draft or "").strip()
    if not body:
        return False
    head = body.lstrip()
    if head.startswith("[") and "error" in head[:120].lower():
        return False
    if previous_failed or memory_update or looks_like_memory_update(user_text):
        return True
    if _REVIEW.search(user_text or ""):
        return True
    if re.search(r"\d", body):
        return True
    if _RECOMMEND.search(body):
        return True
    if _TECH.search(user_text or "") or _TECH.search(body):
        return True
    return False


def number_bindings(text: str) -> dict[str, set[str]]:
    """Map a noun to the numbers written immediately in front of it."""
    found: dict[str, set[str]] = {}
    for match in _NUM_NOUN.finditer(text or ""):
        found.setdefault(match.group(2).lower(), set()).add(match.group(1))
    return found


def definitions(text: str) -> list[tuple[str, str]]:
    """'Define burst as 10 requests' and 'burst means 10 requests'."""
    out: list[tuple[str, str]] = []
    for match in _DEF.finditer(text or ""):
        if match.group(1):
            out.append((match.group(1).lower(), _norm(match.group(2))))
        elif match.group(3):
            out.append((match.group(3).lower(), _norm(match.group(4))))
    return out


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().rstrip(".").lower())


# A number that is the result of a calculation ("= 36 liters", "36 liters in total")
# is an answer, not a restated input (AUDIT C-004).
_RESULT_BEFORE = re.compile(r"(?i)(=|\b(is|are|makes|comes to|equals|need|needs|total(?: of)?|get|gives|that's|so)\s*(about |around |roughly )?)\s*$")
_RESULT_AFTER = re.compile(r"(?i)^\s*(in total|total|altogether|overall|combined|in all|for the (whole|entire))\b")


def _input_bindings(draft: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for m in _NUM_NOUN.finditer(draft or ""):
        before = draft[max(0, m.start() - 24): m.start()]
        after = draft[m.end(): m.end() + 24]
        if _RESULT_BEFORE.search(before) or _RESULT_AFTER.search(after):
            continue
        found.setdefault(m.group(2).lower(), set()).add(m.group(1))
    return found


_OPS = {"x": "*", "×": "*", "*": "*", "times": "*", "multiplied by": "*", "+": "+", "plus": "+",
        "-": "-", "minus": "-", "/": "/", "÷": "/", "divided by": "/"}
_OP = r"(?:multiplied by|divided by|times|plus|minus|[x×*+\-/÷])"
_N = r"\d+(?:\.\d+)?"
_EXPR = re.compile(r"(?i)(?<![\w.])(" + _N + r"(?:\s*" + _OP + r"\s*" + _N + r")+)\s*(?:=|is|equals|makes|gives)\s*\$?(" + _N + r")(?![\d.])")


def arithmetic_problems(draft: str) -> list[str]:
    """Shown arithmetic that is wrong: "17 times 23 is 381", "4 x 3 x 3 = 30"."""
    problems = []
    for m in _EXPR.finditer(draft or ""):
        expr = m.group(1)
        tokens = re.findall(_N + "|" + _OP, expr, re.I)
        py = "".join(_OPS.get(t.lower(), t) if not re.fullmatch(_N, t) else t for t in tokens)
        try:
            value = eval(py, {"__builtins__": {}}, {})       # digits and + - * / only
        except Exception:
            continue
        stated = float(m.group(2))
        if abs(value - stated) > max(0.01, abs(value) * 0.005):
            shown = int(value) if float(value).is_integer() else round(value, 2)
            problems.append(f"arithmetic: {expr.strip()} is {shown}, not {m.group(2)}")
    return problems


def constraint_problems(user_text: str, draft: str) -> list[str]:
    """Numbers and definitions from the question must not drift in the draft."""
    problems: list[str] = arithmetic_problems(draft)
    user_nums = number_bindings(user_text)
    for noun, values in _input_bindings(draft).items():
        if noun not in user_nums:
            continue
        changed = values - user_nums[noun]
        if changed:
            problems.append(
                f"changed {noun} from {', '.join(sorted(user_nums[noun]))} "
                f"to {', '.join(sorted(changed))}"
            )
    user_defs = dict(definitions(user_text))
    for term, value in definitions(draft):
        if term in user_defs and user_defs[term] != value:
            problems.append(f"changed definition of {term} from {user_defs[term]} to {value}")
    return problems


def extract_ledger(text: str) -> dict[str, str] | None:
    matches = list(_LEDGER.finditer(text or ""))
    if not matches:
        return None
    match = matches[-1]
    return {
        "Known": match.group(1).strip(),
        "Inferred": match.group(2).strip(),
        "Assumed": match.group(3).strip(),
        "Unknown": match.group(4).strip(),
    }


def ledger_block(ledger: dict[str, str]) -> str:
    return (
        f"Known: {ledger.get('Known', 'none')}\n"
        f"Inferred: {ledger.get('Inferred', 'none')}\n"
        f"Assumed: {ledger.get('Assumed', 'none')}\n"
        f"Unknown: {ledger.get('Unknown', 'none')}"
    )


def answer_body(text: str) -> str:
    match = _LEDGER.search(text or "")
    if not match:
        return text or ""
    return (text or "")[:match.start()].strip()


def _sentence_around(text: str, index: int) -> str:
    starts = [text.rfind(mark, 0, index) for mark in ".!?\n"]
    start = max(starts)
    ends = [text.find(mark, index) for mark in ".!?\n"]
    ends = [pos for pos in ends if pos >= 0]
    end = min(ends) if ends else len(text)
    return text[start + 1:end + 1]


def assumptions_stated_as_facts(text: str) -> list[str]:
    """An Assumed ledger line quoted in the answer with no hedge is a problem."""
    ledger = extract_ledger(text)
    if not ledger:
        return []
    assumed = (ledger.get("Assumed") or "").strip()
    if assumed.lower().rstrip(".") in _EMPTY:
        return []
    body = answer_body(text)
    clauses = [part.strip(" .") for part in re.split(r"[;\n]", assumed) if len(part.strip()) >= 8]
    if not clauses:
        clauses = [assumed.strip(" .")]
    problems: list[str] = []
    lowered = body.lower()
    for clause in clauses:
        idx = lowered.find(clause.lower())
        if idx < 0:
            continue
        if _HEDGE.search(_sentence_around(body, idx)):
            continue
        problems.append(f"assumed item stated as fact: {clause}")
    return problems


def introduced_number_problems(user_text: str, draft: str, revision: str) -> list[str]:
    """A rewrite may not add a number that was in neither the question nor the draft."""
    allowed = set(_NUM.findall(user_text or "")) | set(_NUM.findall(draft or ""))
    body = re.sub(r"(?m)^\s*\d+[.)]\s", " ", revision or "")                       # list markers
    body = re.sub(r"(?mi)^[\s*_-]*(Known|Inferred|Assumed|Unknown)[*_]*\s*:.*$", "", body)  # ledger
    fresh: list[str] = []
    for number in _NUM.findall(body):
        if number not in allowed and number not in fresh:
            fresh.append(number)
    if not fresh:
        return []
    return [f"revision introduced new numbers: {', '.join(fresh)}"]


# ── Known must come from somewhere; sources must have been looked up ────────

_STOP = frozenset(
    "the a an of to and or for in on is are was were be been with about that this these those "
    "their his her your you they them from into over after before than then just not no "
    "does did do has have had our we us its it as at by per each all any some there here "
    "which what who whom when where how will would can could should may might".split()
)
_WORDS = re.compile(r"[a-z][a-z']+")
# Acronyms are matched case-sensitively so "who" and "epa" in prose do not count.
_AUTHORITY_ACRONYM = re.compile(r"\b(CDC|WHO|FEMA|EPA|USDA|NIH|NOAA|OSHA|FDA|USGS)\b")
_AUTHORITY_NAME = re.compile(
    r"(?i)\b(Centers for Disease Control|World Health Organization|Red Cross|Mayo Clinic|"
    r"National Weather Service|health department|department of [a-z]+|ministry of [a-z]+)\b"
)
# A generic document only counts when the sentence points at a specific one.
_AUTHORITY_DOC = re.compile(
    r"(?i)\b(?:the|a|an|this|that|their|recent|latest|local|state|federal|county|official|government)\s+"
    r"(?:[a-z-]+\s+){0,3}(report|study|survey|journal|guidelines?|advisory|data)\b"
)
_ATTRIBUTION = re.compile(
    r"(?i)\b(according to|source[sd]?|recommends?|recommended|recommendations?|states|reports|"
    r"reported|shows?|found|says|said|quoted?|advises?|guidelines?)\b|[\"“”]"
)


def _stem(word: str) -> str:
    return word[:4] if len(word) > 4 else word


def _content_stems(text: str) -> set[str]:
    return {_stem(w) for w in _WORDS.findall((text or "").lower()) if w not in _STOP and len(w) > 2}


def _is_placeholder(item: str) -> bool:
    return item.strip(" .*").lower() in _EMPTY or set(item.strip()) <= set(". ")


def known_problems(grounding: str, text: str) -> list[str]:
    """Each Known item must come from the person, the conversation, memory, or a
    source looked up this turn. A number nobody gave, or an item mostly made of
    words nobody used, was filled in by the model -- it is Inferred or Assumed."""
    ledger = extract_ledger(text)
    if not ledger:
        return []
    known = ledger.get("Known") or ""
    items = [part.strip(" .*-") for part in re.split(r";|\s\*\s|\s-\s", known)]
    ground_nums = set(_NUM.findall(grounding or ""))
    ground_words = _content_stems(grounding)
    problems: list[str] = []
    for item in items:
        if not item or _is_placeholder(item):
            continue
        new_nums = [n for n in _NUM.findall(item) if n not in ground_nums]
        words = _content_stems(item)
        unsupported = len(words - ground_words) / len(words) if words else 0.0
        if new_nums or unsupported > 0.5:
            problems.append(
                f"listed as Known but not stated by you or found in a looked-up source: {item} "
                f"(it is an inference or an assumption)"
            )
    return problems


_ALIASES = {"world health organization": "who", "centers for disease control": "cdc"}


def _authority_key(name: str) -> str:
    """One key per source, so "WHO", "World Health Organization" and "the WHO
    guidelines" are a single note."""
    low = name.lower()
    for full, short in _ALIASES.items():
        low = low.replace(full, short)
    acronym = _AUTHORITY_ACRONYM.search(low.upper())
    return acronym.group(1).lower() if acronym else low


def _authorities(sentence: str) -> list[str]:
    names = [m.group(1) for m in _AUTHORITY_ACRONYM.finditer(sentence)]
    names += [m.group(1) for m in _AUTHORITY_NAME.finditer(sentence)]
    names += [m.group(0).strip() for m in _AUTHORITY_DOC.finditer(sentence)]
    return names


def citation_problems(grounding: str, sources: str, text: str) -> list[str]:
    """A named source (the CDC, "the local government report") may only be cited
    when its text was actually looked up this turn, or the person brought it up."""
    body = answer_body(text)
    have = f"{sources or ''}\n{grounding or ''}".lower()
    problems: list[str] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", body):
        if not _ATTRIBUTION.search(sentence):
            continue
        for name in _authorities(sentence):
            key = _authority_key(name)
            if key in seen:
                continue
            core = _AUTHORITY_DOC.match(name)
            probe = core.group(1).lower() if core and key == name.lower() else key
            if probe in have or name.lower() in have:
                continue
            seen.add(key)
            problems.append(
                f"cites {name} as a source, but nothing from it was looked up on this computer "
                f"this turn, so it cannot be confirmed"
            )
    return problems


def _problems(user_text: str, text: str, context: str = "", sources: str = "") -> list[str]:
    grounding = "\n".join(part for part in (user_text, context, sources) if part)
    found = constraint_problems(user_text, text)
    found += assumptions_stated_as_facts(text)
    found += known_problems(grounding, text)
    found += citation_problems(f"{user_text}\n{context}", sources, text)
    if needs_ledger(user_text) and extract_ledger(text) is None:
        found.append(_MISSING_LEDGER)
    return found


def parse_verdict(text: str) -> tuple[bool, str]:
    """True when the verifier said CLEAR and nothing else. Empty means no opinion."""
    raw = (text or "").strip()
    if not raw:
        return True, ""
    plain = re.sub(r"[*_`#>]", "", raw).strip().lower()
    if _NO_PROBLEM.fullmatch(plain):
        return True, ""
    return False, raw


# "CLEAR", "**CLEAR**", "None.", "No problems found.", "Clear - no problems found." (AUDIT C-002)
_NO_PROBLEM = re.compile(
    r"(?:clear|none|no (?:problems?|issues?|errors?|mistakes?)(?: found| detected)?|nothing (?:to fix|wrong))"
    r"(?:\s*[-:,.–—]\s*(?:no (?:problems?|issues?|errors?)(?: found| detected)?|none|clear))?[.!]?")


def _background(context: str, sources: str) -> str:
    """Conversation, memory, and looked-up text the draft may rely on."""
    parts = []
    if context:
        parts.append(context[:4000])
    if sources:
        parts.append("Looked up on this computer this turn:\n" + sources[:3000])
    if not parts:
        return ""
    return "Already established (the draft may rely on this; it is not a new claim):\n" + "\n\n".join(parts) + "\n\n"


def verifier_messages(user_text: str, draft: str, context: str = "", sources: str = "") -> list[dict]:
    ledger = extract_ledger(draft)
    extra = ""
    assumed = (ledger or {}).get("Assumed", "")
    if assumed and assumed.lower().rstrip(".") not in _EMPTY:
        extra = (
            "\nSpecifically check that assumed items are not stated as facts.\n"
            f"Assumed: {assumed}\n"
        )
    constraints = constraints_from(user_text) or "(see the question)"
    return [
        {"role": "system", "content": "You are a strict checker. Do not rewrite the answer. " + VERIFIER_INSTRUCTION},
        {"role": "user", "content": (
            f"{_background(context, sources)}"
            f"Original user question:\n{user_text}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"Draft answer:\n{draft}\n"
            f"{extra}\n"
            f"{VERIFIER_INSTRUCTION}"
        )},
    ]


def constraints_from(user_text: str) -> str:
    lines = [f"{num} {noun}" for noun, nums in number_bindings(user_text).items() for num in sorted(nums)]
    lines += [f"{term} = {value}" for term, value in definitions(user_text)]
    return "\n".join(lines)


def revise_messages(user_text: str, draft: str, problems: list[str],
                    context: str = "", sources: str = "") -> list[dict]:
    listed = "\n".join(f"- {item}" for item in problems)
    return [
        {"role": "system", "content": (
            "Rewrite the draft so the listed problems are gone. "
            "Keep every number and definition from the user's question. "
            "Do not add new factual claims. If something is unknown, say so. "
            "Do not name or quote a source unless its text is in what was looked up. "
            + LEDGER_INSTRUCTION
        )},
        {"role": "user", "content": (
            f"{_background(context, sources)}"
            f"User question:\n{user_text}\n\nProblems:\n{listed}\n\nDraft:\n{draft}"
        )},
    ]


def ledger_messages(user_text: str, draft: str, context: str = "", sources: str = "") -> list[dict]:
    return [
        {"role": "system", "content": (
            "Fill this block from the question and the draft. Do not rewrite the answer. "
            "Use none when a line is empty.\n" + LEDGER_INSTRUCTION
        )},
        {"role": "user", "content": (
            f"{_background(context, sources)}User question:\n{user_text}\n\nDraft:\n{draft}"
        )},
    ]


def store_ledger_from(user_text: str, text: str) -> None:
    ledger = extract_ledger(text)
    if not ledger:
        return
    key = (user_text[:240], tuple(sorted(ledger.items())))
    if _ledgers and _ledgers[-1].get("_key") == key:
        return
    _ledgers.append({
        "user": (user_text or "")[:240],
        "ledger": ledger,
        "date": time.strftime("%Y-%m-%d"),
        "_key": key,
    })
    del _ledgers[:-8]


def prior_ledger_block() -> str:
    if not _ledgers:
        return ""
    lines = ["Earlier ledgers in this conversation (use them; do not treat Assumed as fact):"]
    for item in _ledgers[-3:]:
        ledger = item["ledger"]
        lines.append(
            f"- Q: {item['user'][:160]}\n"
            f"  Known: {ledger.get('Known', '')}; Inferred: {ledger.get('Inferred', '')}; "
            f"Assumed: {ledger.get('Assumed', '')}; Unknown: {ledger.get('Unknown', '')}"
        )
    return "\n".join(lines)


def prompt_addendum(user_text: str) -> str:
    """Safety rule, ledger instruction, and earlier ledgers. Empty during a crisis."""
    if _CRISIS.search(user_text or ""):
        return ""
    parts = ["## Verification rules\n" + SAFETY_RULE]
    if exact_format(user_text):
        parts.append(FORMAT_RULE)
    if needs_ledger(user_text):
        parts.append(LEDGER_INSTRUCTION)
    prior = prior_ledger_block()
    if prior:
        parts.append(prior)
    return "\n\n".join(parts)


def format_revision(text: str) -> str:
    return "\n\n---\n**Revised after check:**\n" + text.strip()


def format_notes(problems: list[str]) -> str:
    body = "\n".join(f"- {item}" for item in problems)
    return f"\n\n---\n**Draft + notes:**\n{body}"


def _ask(ask, messages: list[dict]) -> str:
    if not ask:
        return ""
    try:
        return (ask(messages) or "").strip()
    except Exception:
        return ""


def _fill_ledger(user_text: str, draft: str, ask, context: str = "", sources: str = "") -> str:
    """One short call that only fills the four lines. Empty when it fails."""
    if extract_ledger(draft) or not ask:
        return ""
    ledger = extract_ledger(_ask(ask, ledger_messages(user_text, draft, context, sources)))
    if not ledger:
        return ""
    combined = draft.rstrip() + "\n\n" + ledger_block(ledger)
    if assumptions_stated_as_facts(combined):
        return ""
    return "\n\n" + ledger_block(ledger)


def run_pass(user_text: str, draft: str, ask=None, *, memory_update: bool = False,
             context: str = "", sources: str = "") -> PassResult:
    """Check one draft. `ask` is messages -> text. Casual turns return immediately.

    context is the recent conversation and recalled memory; sources is text looked
    up this turn. Both are what the draft may rely on without it being a new claim.
    """
    global _previous_failed
    store_ledger_from(user_text, draft)
    if not should_verify(user_text, draft, memory_update=memory_update,
                         previous_failed=_previous_failed):
        return PassResult()

    problems = _problems(user_text, draft, context, sources)
    filled = ""
    if problems == [_MISSING_LEDGER]:
        filled = _fill_ledger(user_text, draft, ask, context, sources)
        if filled:
            problems = _problems(user_text, draft.rstrip() + filled, context, sources)

    checked = draft.rstrip() + filled
    verdict = (_ask(ask, verifier_messages(user_text, checked, context, sources))
               if (ask and checked.strip()) else "")
    model_clear, model_issues = parse_verdict(verdict)
    if verdict and not model_clear:
        problems.append(model_issues)

    if not problems:
        _previous_failed = False
        store_ledger_from(user_text, checked)
        # No checker, or it said nothing: not checked, so not "verified" (AUDIT C-001).
        return PassResult(append=filled, learn_origin="verified" if verdict.strip() else "inferred", clear=True)

    revised = _ask(ask, revise_messages(user_text, draft, problems, context, sources))
    if revised and parse_verdict(revised)[0]:
        revised = ""          # "CLEAR" or "None." is a verdict, not a rewritten answer
    if revised:
        revised_problems = _problems(user_text, revised, context, sources)
        revised_problems += introduced_number_problems(f"{user_text}\n{context}\n{sources}", draft, revised)
        second = _ask(ask, verifier_messages(user_text, revised, context, sources))
        second_clear, second_issues = parse_verdict(second)
        if second and not second_clear:
            revised_problems.append(second_issues)
        if not revised_problems:
            _previous_failed = False
            store_ledger_from(user_text, revised)
            return PassResult(append=format_revision(revised),
                              learn_origin="verified" if second.strip() else "inferred", clear=True)

    _previous_failed = True
    notes = list(problems)
    if revised:
        notes.append("A revised draft still had problems, so the original draft is unchanged.")
    return PassResult(
        append=format_notes(notes),
        learn_origin="inferred",
        skip_learn=True,
        clear=False,
        problems=notes,
    )

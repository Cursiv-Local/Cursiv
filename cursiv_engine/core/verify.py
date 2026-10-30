"""
Verification after a draft exists.

The eight phases only add prompt text. This module is the
check that runs once the draft is in hand: concrete problems, one rewrite,
and a ledger of what was known, inferred, assumed, or unknown.

No network calls live here. Pass an `ask(messages) -> str` function.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from .problems import Problem, unique
from .review_policy import should_verify, _REVIEW, _CRISIS

# The verifier is told this and nothing softer. A reply of CLEAR does not
# override the deterministic checks below.
VERIFIER_INSTRUCTION = (
    "List concrete problems only: unsupported claims, changed definitions, "
    "contradictions, assumptions presented as facts, answers to the wrong question. "
    "Return at most three short problems, or CLEAR if none. No preamble."
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

_RECOMMEND = re.compile(r"(?i)\b(i recommend|you should|i suggest|recommend)\b")
_TECH = re.compile(
    r"(?i)\b(api|function|traceback|sql|python|javascript|algorithm|voltage|"
    r"dosage|mg\b|mmol|celsius|fahrenheit|config|server|retry|retries|latency|timeout)\b"
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
_NUM_NOUN = re.compile(r"(?i)(?<![\d,.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s+([a-z][a-z0-9-]{2,})\b")
# "4 to 6 weeks", "4-6 weeks", "4 or 5 days": the first number belongs to the noun too
_RANGE_NOUN = re.compile(r"(?i)(?<![\d,.])(\d+(?:\.\d+)?)\s*(?:to|-|–|or|and)\s*\d+(?:\.\d+)?\s+([a-z][a-z0-9-]{2,})\b")
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
    clear: bool = False              # skipped/unavailable is never a successful check
    problems: list[str] = field(default_factory=list)
    issues: list[Problem] = field(default_factory=list)
    resolved: list[Problem] = field(default_factory=list)
    status: str = 'skipped'


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




def number_bindings(text: str) -> dict[str, set[str]]:
    """Map a noun to the numbers written immediately in front of it."""
    found: dict[str, set[str]] = {}
    for match in _NUM_NOUN.finditer(text or ""):
        found.setdefault(match.group(2).lower(), set()).add(match.group(1).replace(",", ""))
    for match in _RANGE_NOUN.finditer(text or ""):
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
_RESULT_BEFORE = re.compile(r"(?i)(=|→|\b(is|are|makes|comes to|equals|need|needs|total(?: of)?|get|gives|that's|so|"
                            r"answer|you (?:go|need|get|travel|drive|use)|it (?:takes|will take)|about|around|"
                            r"roughly|approximately|just over|just under|nearly|almost)\s*[:,]?\s*"
                            r"(about |around |roughly )?)\s*$")
_RESULT_AFTER = re.compile(r"(?i)^\s*(in total|total|altogether|overall|combined|in all|for the (whole|entire))\b")


def _numbers(text: str) -> set[str]:
    return {x.replace(",", "") for x in re.findall(r"(?<![\d,.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?",
                                                   text or "")}


def _input_bindings(draft: str, grounded: set[str] | None = None) -> dict[str, set[str]]:
    """Numbers in front of a noun that read as restating the question. Not counted: a result the answer
    works out ("= 36 liters", "So, 9 eggs", "Answer: 20 degrees") and a number from Cursiv's sources
    (its calculation, the reference card) or from the question that isn't tied to another noun there.
    Noting those under correct answers was most of this check's noise (bench/FAILURES-U75.md)."""
    found: dict[str, set[str]] = {}
    results: set[str] = set()                  # worked out earlier in this answer ("= 12 liters", then "12 liters")
    for m in _NUM_NOUN.finditer(draft or ""):
        before = draft[max(0, m.start() - 24): m.start()]
        after = draft[m.end(): m.end() + 24]
        value = m.group(1).replace(",", "")
        if _RESULT_BEFORE.search(before) or _RESULT_AFTER.search(after):
            results.add(value)
            continue
        if value in (grounded or set()) or value in results or before.rstrip().endswith("("):  # "1 week (7 days)"
            continue
        found.setdefault(m.group(2).lower(), set()).add(value)
    return found


_OPS = {"x": "*", "×": "*", "*": "*", "times": "*", "multiplied by": "*", "+": "+", "plus": "+",
        "-": "-", "minus": "-", "/": "/", "÷": "/", "divided by": "/"}
_OP = r"(?:multiplied by|divided by|times|plus|minus|[x×*+\-/÷])"
_N = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"      # "2,450" is one number
_EXPR = re.compile(r"(?i)(?<![\w.,])(" + _N + r"(?:\s*" + _OP + r"\s*" + _N + r")+)\s*(?:=|is|equals|makes|gives)\s*\$?(" + _N + r")(?![\d.])")


_NUMERIC_EXPRESSION = _N + r'(?:\s*' + _OP + r'\s*' + _N + r')*'
_EQUALITY_CHAIN = re.compile(r'(?i)(?<![\w.,])'+_NUMERIC_EXPRESSION+r'(?:\s*=\s*'+_NUMERIC_EXPRESSION+r')+')


def _numeric_expression(text):
    tokens=re.findall(_N+'|'+_OP,text,re.I)
    expression=''.join(_OPS.get(t.lower(),t) if not re.fullmatch(_N,t) else t.replace(',','') for t in tokens)
    return eval(expression,{'__builtins__':{}},{})  # same restricted digit/operator grammar as the existing check


def arithmetic_problems(draft: str) -> list[str]:
    """Shown arithmetic that is wrong: "17 times 23 is 381", "4 x 3 x 3 = 30"."""
    problems = []
    complex_spans=[]
    for chain in _EQUALITY_CHAIN.finditer(draft or ''):
        parts=[part.strip() for part in chain.group().split('=')]
        if len(parts)==2 and not re.search(_OP,parts[1],re.I):continue
        if re.search(r'[)×x*+\-−/÷]\s*$',draft[max(0,chain.start()-3):chain.start()]):continue
        try:values=[_numeric_expression(part) for part in parts]
        except (ValueError,ZeroDivisionError,SyntaxError,OverflowError):continue
        complex_spans.append(chain.span())
        for i in range(len(values)-1):
            if abs(values[i]-values[i+1])>max(0.01,abs(values[i])*0.005):
                shown=int(values[i]) if float(values[i]).is_integer() else round(values[i],2)
                problems.append(f'arithmetic: {parts[i]} is {shown}, not {parts[i+1]}')
                break
    for m in _EXPR.finditer(draft or ""):
        if any(start<=m.start()<end for start,end in complex_spans):continue
        # "(68 − 32) × 5/9 = 36": only the tail "5/9 = 36" matched (benchmark num-010, U68 and U75)
        if re.search(r"[)×x*+\-−/÷]\s*$", draft[max(0, m.start() - 3): m.start()]):
            continue
        expr = m.group(1)
        tokens = re.findall(_N + "|" + _OP, expr, re.I)
        py = "".join(_OPS.get(t.lower(), t) if not re.fullmatch(_N, t) else t.replace(",", "") for t in tokens)
        try:
            value = eval(py, {"__builtins__": {}}, {})       # digits and + - * / only
        except Exception:
            continue
        stated = float(m.group(2).replace(",", ""))
        frac = re.match(r"\s*/\s*(\d+)", draft[m.end():])       # "3/4 plus 1/8 is 7/8" (num-003)
        if frac and int(frac.group(1)):
            stated = stated / int(frac.group(1))
        if abs(value - stated) > max(0.01, abs(value) * 0.005):
            shown = int(value) if float(value).is_integer() else round(value, 2)
            problems.append(f"arithmetic: {expr.strip()} is {shown}, not {m.group(2)}")
    return problems


def constraint_problems(user_text: str, draft: str, sources: str = "") -> list[str]:
    """Numbers and definitions from the question must not drift in the draft: "4 people need 3 liters"
    answered with "each person drinks 4 liters" is caught; worked results and numbers from Cursiv's
    sources are not."""
    problems: list[str] = arithmetic_problems(draft)
    user_nums = number_bindings(user_text)
    tied = {v for vals in user_nums.values() for v in vals}       # "4 people": 4 can't become "4 liters"
    grounded = (_numbers(user_text) - tied) | _numbers(sources)
    for noun, values in _input_bindings(draft, grounded).items():
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


# A ledger heading line, with any bullet, emoji or bold around it: "✅ Known:", "**Assumed:**".
_LEDGER_HEAD = re.compile(r"(?im)^[^\w\n]*(Known|Inferred|Assumed|Unknown)[*_]*\s*:[*_]*[ \t]*(.*)$")
_LEDGER_ORDER = ("Known", "Inferred", "Assumed", "Unknown")


def _ledger_span(text: str) -> tuple[int, int, dict[str, str]] | None:
    """Where the last complete ledger starts and ends, and its four parts. The items may be on
    the heading line or on the lines under it (a model wrote "✅ Known:" then a list,
    and the check called the ledger missing)."""
    heads = list(_LEDGER_HEAD.finditer(text or ""))
    for i in range(len(heads) - 4, -1, -1):
        group = heads[i:i + 4]
        if tuple(h.group(1).title() for h in group) != _LEDGER_ORDER:
            continue
        parts, stop = {}, len(text)
        for j, h in enumerate(group):
            end = group[j + 1].start() if j < 3 else len(text)
            body = [h.group(2).strip()] + text[h.end():end].split("\n")
            if j == 3:                     # Unknown runs to the first blank line after its items
                lines, seen, pos = [], False, h.end()
                for n, line in enumerate(body):
                    if n:
                        pos += len(line) + 1
                    if not line.strip():
                        if seen:
                            stop = pos
                            break
                        continue
                    seen = True
                    lines.append(line)
                body = lines
            items = [re.sub(r"^[\s*•-]+", "", line).strip() for line in body]
            parts[h.group(1).title()] = "; ".join(x for x in items if x)
        return group[0].start(), min(stop, len(text)), parts
    return None


def extract_ledger(text: str) -> dict[str, str] | None:
    found = _ledger_span(text or "")
    return found[2] if found else None


def ledger_block(ledger: dict[str, str]) -> str:
    return (
        f"Known: {ledger.get('Known', 'none')}\n"
        f"Inferred: {ledger.get('Inferred', 'none')}\n"
        f"Assumed: {ledger.get('Assumed', 'none')}\n"
        f"Unknown: {ledger.get('Unknown', 'none')}"
    )


def answer_body(text: str) -> str:
    found = _ledger_span(text or "")
    if not found:
        return text or ""
    return (text or "")[:found[0]].strip()


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
_AUTHORITY_ACRONYM = re.compile(r"\b(CDC|WHO|FEMA|EPA|USDA|NIH|NOAA|OSHA|FDA|USGS|NASA)\b")
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


# A sentence saying the source isn't available isn't citing it ("I don't have a map").
_NO_SOURCE = re.compile(r"(?i)\b(i (?:don'?t|do not) have|i have no|(?:can'?t|cannot) access|no access to|i (?:don'?t|do not) know of)\b")


def citation_problems(grounding: str, sources: str, text: str) -> list[str]:
    """A named source (the CDC, "the local government report") may only be cited
    when its text was actually looked up this turn, or the person brought it up."""
    body = answer_body(text)
    have = f"{sources or ''}\n{grounding or ''}".lower()
    problems: list[str] = []
    seen: set[str] = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", body):
        regulatory = bool(re.search(r'(?i)\b(?:limits?|thresholds?|standards?|requires?|maximum|minimum)\b',sentence)
                          and re.search(r'\d',sentence) and _authorities(sentence))
        if regulatory and not _NO_SOURCE.search(sentence) and not re.search(r'(?i)\b(?:not established|unverified|unsupported|you supplied|you stated)\b',sentence):
            for name in _authorities(sentence):
                key = _authority_key(name)
                # Naming an agency in a question is not evidence for its limit.
                supported = any(key in {_authority_key(n) for n in _authorities(source_sentence)} and set(_NUM.findall(sentence)) <= set(_NUM.findall(source_sentence))
                    for source_sentence in re.split(r'(?<=[.!?])\s+|\n+',sources or ''))
                if not supported:
                    if key not in seen:
                        seen.add(key)
                        problems.append(f'unsupported {name} regulatory threshold: the stated value and source were not established by retrieved evidence')
            continue
        if not _ATTRIBUTION.search(sentence) or _NO_SOURCE.search(sentence):
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


def _issues(user_text: str, text: str, context: str = "", sources: str = "") -> list[Problem]:
    grounding = "\n".join(part for part in (user_text, context, sources) if part)
    found = []
    groups = (
        ('CONSTRAINT_MISMATCH', 'warning', constraint_problems(user_text, text, sources)),
        ('ASSUMPTION_AS_FACT', 'warning', assumptions_stated_as_facts(text)),
        ('UNGROUNDED_KNOWN', 'warning', known_problems(grounding, text)),
        ('UNSUPPORTED_CITATION', 'error', citation_problems(f"{user_text}\n{context}", sources, text)),
    )
    for code, severity, messages in groups:
        found.extend(Problem(code, severity, message) for message in messages)
    if needs_ledger(user_text) and extract_ledger(text) is None:
        found.append(Problem('MISSING_LEDGER', 'info', _MISSING_LEDGER))
    return unique(found)


def _problems(user_text: str, text: str, context: str = "", sources: str = "") -> list[str]:
    """Compatibility for callers that display human-readable messages."""
    return [item.message for item in _issues(user_text, text, context, sources)]


def parse_verdict(text: str) -> tuple[bool, str]:
    """True when the verifier said CLEAR and nothing else. Empty means no opinion."""
    raw = (text or "").strip()
    if not raw:
        return False, ""
    plain = re.sub(r"[*_`#>]", "", raw).strip().lower()
    if _NO_PROBLEM.fullmatch(plain):
        return True, ""
    lines = [ln.strip(" -•\t") for ln in plain.splitlines() if ln.strip(" -•\t")]
    if lines and all(_EMPTY_FINDING.fullmatch(ln) for ln in lines):
        return True, ""                      # "Unsupported claims: None" on every line
    return False, raw


_EMPTY_FINDING = re.compile(r"[\w ,/()-]{2,60}:\s*(none|n/a|no|nothing|clear|none found|not applicable)\.?")

# "CLEAR", "**CLEAR**", "None.", "No problems found.", "Clear - no problems found." (AUDIT C-002)
_NO_PROBLEM = re.compile(
    r"(?:clear|none|no (?:problems?|issues?|errors?|mistakes?)(?: found| detected)?|nothing (?:to fix|wrong))"
    r"(?:\s*[-:,.–—]\s*(?:no (?:problems?|issues?|errors?)(?: found| detected)?|none|clear))?[.!]?")


def _background(context: str, sources: str) -> str:
    """Conversation, memory, and looked-up text the draft may rely on."""
    parts = []
    if context:
        parts.append(context[:1600])
    if sources:
        parts.append("Evidence supplied this turn:\n" + sources[:2400])
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
            f"Draft answer:\n{draft[:8000]}\n"
            f"{extra}\n"
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
            "Change only what is needed to address those listed problems; preserve unrelated content. "
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
             context: str = "", sources: str = "", assess=None, mode: str = 'full',
             update_session: bool = True, previous_failed: bool | None = None) -> PassResult:
    """Check one draft. `ask` is messages -> text. Casual turns return immediately.

    context is the recent conversation and recalled memory; sources is text looked
    up this turn. Both are what the draft may rely on without it being a new claim.
    """
    global _previous_failed
    if update_session:
        store_ledger_from(user_text, draft)

    def evaluate(text):
        try:
            from .answer_assessment import assess as baseline
            found = unique(_issues(user_text, text, context, sources) +
                           (assess(text) if assess else baseline(user_text, text)))
            return [p for p in found if mode == 'full' or p.code != 'MISSING_LEDGER']
        except Exception:
            return [Problem('CHECK_UNAVAILABLE', 'error',
                            'A deterministic check was unavailable; this answer has not been verified.')]

    def failed(issues, *, revised=False, status='problems', display_issues=None):
        global _previous_failed
        if update_session:
            _previous_failed = True
        notes = [item.message for item in (issues if display_issues is None else display_issues)]
        if revised:
            notes.append('A revised draft still had problems, so the original draft is unchanged.')
        return PassResult(append=format_notes(notes), learn_origin='inferred',
                          skip_learn=True, clear=False, problems=notes, issues=issues, status=status)

    issues = evaluate(draft)
    if mode == 'off':
        return failed(issues) if issues else PassResult()
    if _CRISIS.search(user_text or ''):
        return failed(issues) if issues else PassResult()
    if mode != 'full' and not issues and not should_verify(user_text, draft, memory_update=memory_update,
                                        previous_failed=_previous_failed if previous_failed is None else previous_failed):
        return PassResult()
    # Safety, provenance, failed checks and unconfirmed actions get notes only.
    # A language model cannot authorize an action or override source evidence.
    if any(item.severity == 'error' for item in issues):
        return failed(issues)

    if mode == 'fast' and not any(p.severity == 'warning' for p in issues) and not should_verify(user_text, draft):
        return failed(issues) if issues else PassResult()

    checked = draft.rstrip()
    if len(checked) > 8000 or len(user_text) > 4000:
        issues.append(Problem('CHECK_INPUT_LIMIT', 'info',
                              'Model review was not run because this turn exceeds its short-input budget. Code checks still ran.'))
        return failed(issues, status='unavailable')
    verdict = (_ask(ask, verifier_messages(user_text, checked, context, sources))
               if (ask and checked.strip()) else "")
    model_clear, model_issues = parse_verdict(verdict)
    if not verdict:
        issues.append(Problem('CHECKER_UNAVAILABLE', 'error',
                              'The answer checker returned no result; the draft is unverified.', 'model'))
        return failed(unique(issues), status='unavailable')
    if not model_clear:
        issues.append(Problem('MODEL_FINDING', 'warning', model_issues, 'model'))

    if not issues:
        if update_session:
            _previous_failed = False
            store_ledger_from(user_text, checked)
        return PassResult(learn_origin="verified", clear=True, status='checked')

    if mode == 'fast':
        return failed(issues)  # one small verdict, no ledger-fill/rewrite/second model call

    problems = [item.message for item in issues]
    revised = _ask(ask, revise_messages(user_text, draft, problems, context, sources))
    if revised and (parse_verdict(revised)[0] or _norm(revised) == _norm(draft)):
        revised = ""          # "CLEAR" or "None." is a verdict, not a rewritten answer
    if revised:
        revised_issues = evaluate(revised)
        revised_issues += [Problem('REWRITE_NEW_NUMBER', 'error', item) for item in
                           introduced_number_problems(f"{user_text}\n{context}\n{sources}", draft, revised)]
        if revised_issues:
            return failed(unique(issues + revised_issues), revised=True, display_issues=issues)
        second = _ask(ask, verifier_messages(user_text, revised, context, sources))
        second_clear, second_issues = parse_verdict(second)
        if not second:
            revised_issues.append(Problem('CHECKER_UNAVAILABLE', 'error',
                                         'The replacement checker returned no result; the original draft is unchanged.', 'model'))
        elif not second_clear:
            revised_issues.append(Problem('MODEL_FINDING', 'warning', second_issues, 'model'))
        if not revised_issues:
            if update_session:
                _previous_failed = False
                store_ledger_from(user_text, revised)
            return PassResult(append=format_revision(revised),
                              learn_origin="verified", clear=True, resolved=issues, status='revised')
        return failed(unique(issues + revised_issues), revised=True, display_issues=issues)

    return failed(issues)

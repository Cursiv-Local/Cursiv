"""
Supplies, people and time, worked out in code: how much there is, how much a stated
allocation needs over the period, the shortfall or surplus, and how long it lasts.

Why: in a scenario test (120 people, 240 liters, 48 hours) the model mixed up the total
for 48 hours with a daily figure, then said 240 liters would last 12 days at 2 liters per
person per day. It lasts 1 day. calc.work_out() calls this; the result goes to the model
as a fact, and calc.check() looks for an answer that contradicts it (a different number of
days, "enough" when there's a shortfall).

What it does NOT decide: whether an allocation is enough for health. 2 liters per person
per day is whatever the question assumed; the statement says so, and Cursiv never picks
an allocation itself. Only clear question shapes are handled: anything ambiguous (two
supplies, two head counts, two periods) returns None and the model answers as before.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
          "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
          "fifty": 50, "sixty": 60, "hundred": 100, "a dozen": 12, "a": 1, "an": 1}
_N = r"(\d[\d,]*(?:\.\d+)?|" + "|".join(sorted((w for w in _WORDS if w not in ("a", "an")), key=len, reverse=True)) + r")"
_NA = r"(\d[\d,]*(?:\.\d+)?|" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")"   # also "a" / "an"

_LITERS = {"l": 1.0, "liter": 1.0, "liters": 1.0, "litre": 1.0, "litres": 1.0,
           "gal": 3.785411784, "gallon": 3.785411784, "gallons": 3.785411784}
_COUNT = {"meal": "meals", "meals": "meals", "ration": "rations", "rations": "rations"}
_VOL = r"(liters?|litres?|l|gallons?|gal)"
_UNIT = r"(liters?|litres?|l|gallons?|gal|meals?|rations?)"
_PERSON = r"(?:person|people|head|individual|capita)"
_DAY = r"(day|24 hours|24 hrs)"
_EVERY = r"(?:per|/|a|an|each|every)"

_ALLOC = re.compile(r"(?i)(?<![\w.-])" + _N + r"\s*-?\s*" + _UNIT + r"\s*(?:of water\s*)?"
                    r"(?:" + _EVERY + r"\s*" + _PERSON + r"\s*" + _EVERY + r"\s*" + _DAY + r"|"
                    + _EVERY + r"\s*" + _DAY + r"\s*" + _EVERY + r"\s*" + _PERSON + r")\b")
_CONTAINERS_A = re.compile(r"(?i)(?<![\w.-])" + _N + r"\s+(?:[a-z]+\s+){0,2}?(containers?|jugs?|jerry ?cans?|barrels?|"
                           r"drums?|bottles?|tanks?|buckets?|cans?|totes?)\s+(?:each\s+)?(?:holding|of|with|containing|"
                           r"that hold|which hold|at|holds?)\s+" + _N + r"\s*" + _VOL + r"\b(?:\s+each)?")
_CONTAINERS_B = re.compile(r"(?i)(?<![\w.-])" + _N + r"\s+" + _N + r"\s*-?\s*" + _VOL + r"\s+(containers?|jugs?|"
                           r"jerry ?cans?|barrels?|drums?|bottles?|tanks?|buckets?|cans?|totes?)\b")
_AMOUNT = re.compile(r"(?i)(?<![\w.,-])(-?)" + _N + r"\s*-?\s*" + _UNIT + r"\b(?!\s*(?:" + _EVERY + r")\s*" + _PERSON + r")")
_PEOPLE = re.compile(r"(?i)(?<![\w.-])(-?)" + _N + r"\s+(?:[a-z]+\s+)?(people|persons|residents|villagers|survivors|"
                     r"adults|campers|evacuees|members|individuals|households? members|refugees)\b")
_PERIOD = re.compile(r"(?i)(?<![\w.-])(-?)" + _NA + r"\s*-?\s*(hours?|hrs?|days?|weeks?)\b")
_TOPIC = re.compile(r"(?i)\b(water|meals?|rations?|food|supply|supplies|drink(?:ing)?)\b")


@dataclass
class Plan:
    statement: str
    value: float | None
    tol: float
    facts: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)


def _num(s: str) -> float:
    s = s.lower().replace(",", "")
    return float(_WORDS[s]) if s in _WORDS else float(s)


def _fmt(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def _kind(unit: str) -> tuple[str, float]:
    u = unit.lower()
    if u in _LITERS:
        return "L", _LITERS[u]
    return _COUNT[u], 1.0


def _days(n: float, unit: str) -> float:
    u = unit.lower()
    return n / 24 if u.startswith(("hour", "hr")) else n * 7 if u.startswith("week") else n


def _say_days(d: float) -> str:
    if d < 1:
        return f"{_fmt(d)} days ({_fmt(d * 24)} hours)"
    return f"{_fmt(d)} day{'s' if abs(d - 1) > 1e-9 else ''}"


def _invalid(why: str, inputs: dict) -> Plan:
    return Plan(f"Cursiv didn't calculate this: {why}.", None, 0.0, {"invalid": why}, inputs)


def work_out(question: str) -> Plan | None:
    q = question or ""
    if not _TOPIC.search(q):
        return None
    rest = q
    allocs = list(_ALLOC.finditer(rest))
    rest = _ALLOC.sub(" ", rest)
    containers = list(_CONTAINERS_A.finditer(rest)) + list(_CONTAINERS_B.finditer(rest))
    rest = _CONTAINERS_B.sub(" ", _CONTAINERS_A.sub(" ", rest))
    amounts = list(_AMOUNT.finditer(rest))
    people = list(_PEOPLE.finditer(q))
    periods = list(_PERIOD.finditer(_ALLOC.sub(" ", q)))
    if not people or not (containers or amounts):
        return None

    inputs: dict = {}
    # ── people ──
    heads = {(m.group(1), _num(m.group(2))) for m in people}
    if len(heads) > 1:
        return None                                     # two head counts: not guessing which
    sign, n_people = next(iter(heads))
    inputs["people"] = ("-" if sign else "") + _fmt(n_people)
    if sign:
        return _invalid(f"the number of people can't be negative (-{_fmt(n_people)})", inputs)
    if n_people == 0:
        return _invalid("with 0 people there is nothing to share out; check the number of people", inputs)
    if n_people != int(n_people):
        return _invalid(f"{_fmt(n_people)} isn't a whole number of people", inputs)

    # ── supply ──
    supplies = []
    for m in containers:
        if m.re is _CONTAINERS_A:
            count, size, unit = _num(m.group(1)), _num(m.group(3)), m.group(4)
        else:
            count, size, unit = _num(m.group(1)), _num(m.group(2)), m.group(3)
        kind, factor = _kind(unit)
        supplies.append((kind, count * size * factor, f"{_fmt(count)} × {_fmt(size)} {unit}", count))
    for m in amounts:
        if m.group(1):
            inputs["supply"] = f"-{m.group(2)} {m.group(3)}"
            return _invalid(f"a negative quantity (-{m.group(2)} {m.group(3)}) isn't a supply", inputs)
        kind, factor = _kind(m.group(3))
        supplies.append((kind, _num(m.group(2)) * factor, f"{m.group(2)} {m.group(3)}", None))
    kinds = [s[0] for s in supplies]
    if len(kinds) != len(set(kinds)):
        return None                                     # two supplies of one kind: not guessing which

    # ── period ──
    spans = {(m.group(1), _days(_num(m.group(2)), m.group(3)), m.group(0).strip()) for m in periods}
    days = None
    if len(spans) > 1:
        return None
    if spans:
        sign, days, said = next(iter(spans))
        inputs["period"] = said
        if sign or days <= 0:
            return _invalid(f"the period ({said}) has to be longer than zero", inputs)

    # ── allocation: it decides which supply is being asked about ──
    alloc = None
    if allocs:
        if len(allocs) > 1:
            return None
        a = allocs[0]
        a_kind, a_factor = _kind(a.group(2))
        alloc = (a_kind, _num(a.group(1)) * a_factor, f"{a.group(1)} {a.group(2)} per person per day",
                 a.group(2).lower().startswith("gal"))
        inputs["allocation"] = alloc[2]
        match = [x for x in supplies if x[0] == a_kind]
        if not match:
            return _invalid(f"the supply is in {', '.join(sorted(set(kinds)))} but the allocation is in {a_kind}, "
                            "so they can't be compared; give both in the same kind of unit", inputs)
        if alloc[1] <= 0:
            return _invalid("the allocation per person per day has to be more than zero", inputs)
        chosen = match
    else:
        chosen = supplies

    parts, facts, value = [], {}, None
    for kind, total, shown, count in chosen:
        inputs.setdefault("supply", shown)
        if count == 0 or total == 0:
            return _invalid(f"the supply is 0 {kind} ({shown}), so there is nothing to share out", inputs)
        f, said, v = _section(kind, total, shown, count, n_people, days, alloc)
        parts.append(said)
        if not facts:
            facts, value = f, v
    if not alloc and not days:
        parts.append("No period or allocation per person per day was given, so Cursiv didn't work out how long "
                     "it lasts.")
    elif not alloc:
        parts.append("No allocation per person per day was given, so these are averages, not a judgement of "
                     "whether it's enough.")
    tol = max(0.006, abs(value) * 0.005)
    return Plan(" ".join(parts), value, tol, facts, inputs)


def _section(kind: str, total: float, shown: str, count, n_people: float, days, alloc) -> tuple[dict, str, float]:
    u = kind if kind in ("meals", "rations") else "L"
    gal = shown.lower().rstrip(".").endswith(("gallon", "gallons", "gal")) or bool(alloc and alloc[3])

    def amount(v: float) -> str:
        return f"{_fmt(v)} {u}" + (f" ({_fmt(v / 3.785411784)} gallons)" if gal and u == "L" else "")

    parts, facts = [], {"unit": u, "supply": total, "people": n_people, "days": days}
    plain = shown.lower().endswith((" l", " liters", " litres", " liter", " litre", " meals", " meal", " rations",
                                    " ration")) and count is None
    parts.append(f"Supply: {shown}" + ("" if plain else f" = {_fmt(total)} {u}") + ".")
    per_person = total / n_people
    facts["per_person_total"] = per_person
    parts.append(f"Shared among {_fmt(n_people)} people: {amount(per_person)} per person for the whole supply.")
    value = per_person
    if days:
        per_day = per_person / days
        facts["per_person_day"] = per_day
        parts.append(f"Over {_say_days(days)}: {amount(per_day)} per person per day on average.")
        value = per_day
    if alloc:
        a = alloc[1]
        lasts = total / (n_people * a)
        facts.update(alloc=a, lasts_days=lasts)
        same = alloc[2].lower().startswith(f"{_fmt(a)} ") and u == "L" and not alloc[3]
        parts.append(f"At the assumed {alloc[2]}{'' if same or u != 'L' else ' (' + _fmt(a) + ' L)'}, "
                     f"it lasts {_say_days(lasts)}.")
        value = lasts
        if days:
            need = n_people * a * days
            short = need - total
            facts.update(required=need, short=short)
            parts.append(f"Needed over {_say_days(days)}: {_fmt(n_people)} people × {_fmt(a)} {u} × {_fmt(days)} days "
                         f"= {amount(need)}.")
            if short > 1e-9:
                parts.append(f"Shortfall: {amount(short)} over the {_say_days(days)}.")
            elif short < -1e-9:
                parts.append(f"Surplus: {amount(-short)} over the {_say_days(days)}.")
            else:
                parts.append("The supply exactly covers the period, with nothing to spare.")
            value = abs(short) if abs(short) > 1e-9 else need
            facts["also"] = [need] + ([value / 3.785411784, need / 3.785411784] if gal and u == "L" else [])
        parts.append(f"The {alloc[2]} is the question's assumption, not a figure Cursiv has checked as enough: "
                     "real needs depend on climate, exertion, age and health.")
    return facts, " ".join(parts), value


# ── what an answer says about the same numbers ──────────────────────────────

_LASTS = re.compile(r"(?i)\b(?:last(?:s|ing)?|enough for|sufficient for|cover(?:s|ing)?|run out (?:in|after))\b"
                    r"[^.!?\n]{0,40}?(?<![\d.])(\d+(?:\.\d+)?)\s*(hours?|hrs?|days?|weeks?)\b")
_ENOUGH = re.compile(r"(?i)\b(enough|sufficient|adequate|plenty|will cover|covers? (?:everyone|the (?:whole|full|entire)))\b")
_NOT = re.compile(r"(?i)\b(not|n't|isn't|insufficient|short|shortfall|only|less than|falls?|under|lacks?|won't|without)\b")
# "This assumes 2 liters per person per day is sufficient" is about the allocation, not the supply
# (first live Cross-check, U76): only a sentence calling the supply enough contradicts a shortfall.
_ABOUT_ALLOCATION = re.compile(r"(?i)\b(assum\w*|allocation|ration\w*|per person(?: per day)?\s+(?:is|are|was|be)|"
                               r"whether|if\b[^.]{0,40}\b(?:enough|sufficient|adequate))")


_PER_DAY = re.compile(r"(?i)(?<![\d.])(\d+(?:\.\d+)?)\s*(?:liters?|litres?|l|meals?|rations?)\s*(?:of water\s*)?"
                      r"(?:per|/|a|each)\s*(?:person|head|individual)\s*(?:per|/|a|each)\s*day\b")
_GETS = re.compile(r"(?i)\b(gets?|getting|receives?|have|has|having|available|works? out|comes? to|allows?|gives?|"
                   r"provides?|leaves?|averag\w*|share|ration(?:ed)?|that'?s|is|means)\b")


def _gets(m: re.Match) -> bool:
    """The figure is said to be what people get (not an allocation being assumed or needed)."""
    before = m.string[max(0, m.start() - 50): m.start()]
    if re.search(r"(?i)\b(at|assum\w*|need\w*|requir\w*|allocat\w*|recommend\w*|minimum|target|if)\b[^.]{0,30}$", before):
        return False
    return bool(_GETS.search(before))


def lasts_claims(text: str) -> list[tuple[float, str]]:
    """(days, the words) for every "lasts N days/hours" in a text."""
    out = []
    for m in _LASTS.finditer(text or ""):
        out.append((_days(float(m.group(1)), m.group(2)), m.group(0).strip()))
    return out


def contradictions(answer: str, facts: dict) -> list[str]:
    """Where an answer contradicts the worked-out figures."""
    if not facts or facts.get("invalid"):
        return []
    found = []
    lasts = facts.get("lasts_days")
    if lasts is not None:
        for days, said in lasts_claims(answer):
            if not math.isclose(days, lasts, rel_tol=0.06, abs_tol=0.05) and \
                    not (facts.get("days") and math.isclose(days, facts["days"], rel_tol=0.01)
                         and re.search(r"(?i)\b(need|needed|require|for the|over the|period)\b", said)):
                found.append(f"it says \"{said}\", but at the allocation given the supply lasts {_say_days(lasts)}")
    # "each person gets 2 liters per day" when 2 L each is the whole supply over 2 days (the
    # original error: a total for the period read as a daily figure)
    per_day = facts.get("per_person_day")
    if per_day is not None:
        for m in _PER_DAY.finditer(answer or ""):
            said = float(m.group(1))
            covered = (facts.get("short") or 0) <= 1e-9          # with a shortfall, nobody gets the allocation
            if _gets(m) and not math.isclose(said, per_day, rel_tol=0.06, abs_tol=0.01) and \
                    not (covered and facts.get("alloc") and math.isclose(said, facts["alloc"], rel_tol=0.01)):
                found.append(f"it says \"{m.group(0).strip()}\", but the supply works out to {_fmt(per_day)} "
                             f"{facts['unit']} per person per day on average")
                break
    if (facts.get("short") or 0) > 1e-9:
        for sentence in re.split(r"(?<=[.!?])\s+|\n", answer or ""):
            if _ENOUGH.search(sentence) and not _NOT.search(sentence) and not _ABOUT_ALLOCATION.search(sentence):
                found.append(f"it calls the supply enough (\"{sentence.strip()[:80]}\"), but there's a shortfall of "
                             f"{_fmt(facts['short'])} {facts['unit']} for the period")
                break
    return found

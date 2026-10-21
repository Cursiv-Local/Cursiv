"""
Arithmetic and clock times worked out in code, not by the model.

A 4B model put bedtime at 10:00 PM for "wake at 6:00 AM, 8 hours of sleep,
30 minutes to fall asleep" (benchmark rea-009; right answer 9:30 PM). When a
question has that shape, or a plain sum ("what is 17 times 23"), Cursiv computes
the result, gives it to the model as a fact, and checks the answer used it.

Only clear patterns are handled; anything else returns nothing and the model
answers as before.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORDNUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
            "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
            "thirty": 30, "forty": 40, "forty-five": 45, "fifty": 50, "sixty": 60, "ninety": 90}
_NUMW = r"(\d+(?:\.\d+)?|" + "|".join(sorted(_WORDNUM, key=len, reverse=True)) + r")"
_NUMERICAL_CHALLENGE = re.compile(
    r"(?i)\b(?:no|wrong|incorrect|actually|correct|right|you(?:'re| are) mistaken|"
    r"that(?:'s| is) not (?:correct|right))\b")

# 6:00 AM / 6 pm / noon, or a 24-hour time (14:30), which field teams often use
_TIME = re.compile(r"(?i)\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?![a-z])|\b(noon|midnight)\b"
                   r"|(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])(?!\s*[ap]\.?m)")
_DURATION = re.compile(r"(?i)\b" + _NUMW + r"(?:\s+and\s+a\s+half)?\s*(hours?|hrs?|h|minutes?|mins?)\b"
                       r"|\b(half an hour|an hour and a half|a half hour)\b")
# "What time should I go to bed / leave / start" with a time to be done by: count back.
_BACK = re.compile(r"(?i)\bwhat time (?:should|do|must|would) (?:i|we|he|she|they) (?:go to bed|get in(?:to)? bed|"
                   r"go to sleep|sleep|leave|start|head out|begin|set off|put\b)|\bwhen (?:should|do) (?:i|we) "
                   r"(?:go to bed|leave|start|begin)")
# "Start at 2 PM, it takes 3 hours: when will it be done / what time will I finish": count forward.
_FORWARD = re.compile(r"(?i)\b(?:what time|when) (?:will|would) (?:it|i|we|they|that|the \w+) (?:be (?:done|ready|finished)|"
                      r"finish|end|arrive|get there|be back)|\bwhat time (?:is it|will it be) (?:after|in)\b")


@dataclass
class Worked:
    statement: str      # "6:00 AM minus 8 hours 30 minutes is 9:30 PM (the night before)."
    answer: str         # what the reply must contain: "9:30"
    value: float | None = None   # for field calculations: a number the reply must contain, within tol
    tol: float = 0.0
    lead: str = ""               # Cursiv's own line above the answer (safety rules)
    facts: dict = field(default_factory=dict)   # resources: supply, need, shortfall, how long it lasts
    tool: str = ""               # the function that worked it out ("resources", "clock", "units", ...)
    inputs: dict = field(default_factory=dict)  # what it was given, as read from the question

    @property
    def ok(self) -> bool:
        """False when the calculator read the question but refused it (0 people, a negative supply...)."""
        return not self.facts.get("invalid")

    def record(self) -> dict:
        """What actually ran, for the trace and for checking claims of tool use."""
        return {"tool": self.tool, "inputs": dict(self.inputs), "result": self.statement, "ok": self.ok}


def _num(text: str) -> float:
    t = text.lower()
    return float(_WORDNUM[t]) if t in _WORDNUM else float(t)


def _minutes(m: re.Match) -> int:
    if m.group(3):
        phrase = m.group(3).lower()
        return 90 if "and a half" in phrase else 30
    value = _num(m.group(1)) + (0.5 if "and a half" in m.group(0).lower() else 0)
    return round(value * 60) if m.group(2).lower().startswith("h") else round(value)


def _clock(m: re.Match) -> int:
    if m.group(5):
        return int(m.group(5)) * 60 + int(m.group(6))
    if m.group(4):
        return 12 * 60 if m.group(4).lower() == "noon" else 0
    h, mins, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
    if not 1 <= h <= 12 or mins > 59:
        raise ValueError
    h = h % 12 + (12 if ampm.startswith("p") else 0)
    return h * 60 + mins


def _fmt(total: int, clock24: bool = False) -> tuple[str, int]:
    day = total // (24 * 60)
    total %= 24 * 60
    h, m = divmod(total, 60)
    if clock24:
        return f"{h:02d}:{m:02d}", day
    return f"{(h % 12) or 12}:{m:02d} {'AM' if h < 12 else 'PM'}", day


def _say(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    parts = ([f"{h} hour{'s' if h != 1 else ''}"] if h else []) + ([f"{m} minutes"] if m else [])
    return " ".join(parts) or "0 minutes"


def clock_arithmetic(question: str) -> Worked | None:
    q = question or ""
    times = list(_TIME.finditer(q))
    durations = list(_DURATION.finditer(q))
    back, forward = bool(_BACK.search(q)), bool(_FORWARD.search(q))
    if len(times) != 1 or not durations or back == forward:
        return None
    try:
        start = _clock(times[0])
    except ValueError:
        return None
    total = sum(_minutes(d) for d in durations)
    end = start - total if back else start + total
    shown, day = _fmt(end, clock24=bool(times[0].group(5)))
    when = " (the day before)" if day < 0 else (" (the next day)" if day > 0 else "")
    if back and day < 0 and end % (24 * 60) >= 12 * 60:
        when = " (the night before)"
    verb = "minus" if back else "plus"
    return Worked(f"{times[0].group(0).strip()} {verb} {_say(total)} is {shown}{when}.", shown.split()[0],
                  tool="clock", inputs={"time": times[0].group(0).strip(), "duration": _say(total),
                                        "direction": verb})


_OPS = {"x": "*", "×": "*", "*": "*", "times": "*", "multiplied by": "*", "+": "+", "plus": "+",
        "-": "-", "minus": "-", "/": "/", "÷": "/", "divided by": "/"}
_OP = r"(?:multiplied by|divided by|times|plus|minus|[x×*+\-/÷])"
_N = r"\d+(?:,\d{3})*(?:\.\d+)?"
_SUM = re.compile(r"(?i)\bwhat(?:'s| is)\s+(" + _N + r"(?:\s*" + _OP + r"\s*" + _N + r")+)\s*[?.]?")
_PERCENT = re.compile(r"(?i)\bwhat(?:'s| is)\s+(" + _N + r")\s*(?:%|percent)\s+of\s+(" + _N + r")")


def _show(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.4f}".rstrip("0").rstrip(".")


def plain_arithmetic(question: str) -> Worked | None:
    q = question or ""
    m = _PERCENT.search(q)
    if m:
        a, b = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
        v = a * b / 100
        return Worked(f"{m.group(1)}% of {m.group(2)} is {_show(v)}.", _show(v), tool="percent",
                      inputs={"percent": m.group(1), "of": m.group(2)})
    m = _SUM.search(q)
    if not m:
        return None
    tokens = re.findall(_N + "|" + _OP, m.group(1), re.I)
    expr = "".join(t.replace(",", "") if re.fullmatch(_N, t) else _OPS[t.lower()] for t in tokens)
    try:
        v = eval(expr, {"__builtins__": {}}, {})          # digits and + - * / only
    except Exception:
        return None
    return Worked(f"{m.group(1).strip()} is {_show(v)}.", _show(v), tool="arithmetic",
                  inputs={"expression": m.group(1).strip()})


def work_out(question: str) -> Worked | None:
    """What Cursiv's code works out for this question, or None (then nothing was calculated,
    and nothing may say it was). A calculator that fails counts as None, never as a result."""
    try:
        w = clock_arithmetic(question) or plain_arithmetic(question)
        if w:
            return w
        # Supplies, people and time (core/resources.py): before units, which would read "18 liters"
        from cursiv_v215.core import resources
        p = resources.work_out(question)
        if p:
            return Worked(p.statement, "", p.value, p.tol, facts=p.facts, tool="resources", inputs=p.inputs)
        # Units, coordinates, dilutions, statistics (core/fieldcalc.py, research roadmap R2)
        from cursiv_v215.core import fieldcalc
        r = fieldcalc.work_out(question)
        if r and r.value != r.value:                 # NaN: the calculator read it and refused (mixed units)
            return Worked(r.statement, "", None, 0.0, tool=r.tool or "fieldcalc", facts={"invalid": r.statement})
        if r and getattr(r, "answer", ""):             # a day name, not a number
            return Worked(r.statement, r.answer, None, 0.0, r.lead, tool=r.tool or "fieldcalc")
        return Worked(r.statement, "", r.value, r.tol, r.lead, tool=r.tool or "fieldcalc",
                      facts=dict(getattr(r, "facts", {}) or {})) if r else None
    except Exception:
        return None


def work_out_for_turn(question: str, history: list[dict] | None = None) -> Worked | None:
    """Recheck the immediately preceding conversion when the current turn challenges it.

    A reply like "No, 0.7894 is correct" has no conversion expression. Only the most recent
    user turn can supply the calculation, and only for an explicit numerical challenge.
    """
    worked = work_out(question)
    if worked or not _NUMERICAL_CHALLENGE.search(question or "") or not re.search(r"\d", question or ""):
        return worked
    previous = next((item.get("content") for item in reversed(history or [])
                     if item.get("role") == "user" and isinstance(item.get("content"), str)), None)
    if not previous:
        return None
    prior_work = work_out(previous)
    return prior_work if prior_work and prior_work.tool == "units" else None


def prompt_note(w: Worked) -> str:
    if not w.ok:
        return ("## Cursiv's calculator\n" + w.statement +
                " Don't give a calculated result for this; say which figure is missing or wrong and ask for it.")
    heading = "## Calculated by Cursiv's code (decimal shown is rounded)\n" if w.tool == "units" else \
        "## Worked out by Cursiv (exact)\n"
    return (heading + w.statement +
            " Use these results as given, with their units and time period; don't redo the calculation "
            "differently, and don't describe the supply as lasting longer or being enough when it isn't. "
            "Don't say a tool or calculator was used: Cursiv adds that line itself.")


def _decimals(number: str) -> int:
    """Rounding allowed for a number written with this many decimals: 54.3 may stand for 54.32."""
    return len(number.split(".")[1]) if "." in number else -1


def _rounding_tolerance(number: str) -> float:
    """Allow only the rounding implied by the precision the answer actually shows."""
    places = max(0, _decimals(number))
    return 0.5 * (10 ** -places)


_CONVERSION_CLAIM = re.compile(r"(?i)\b(?:convert(?:ed|ing)?|conversion|equals?|is|are|was|becomes?)\b|=|≈|~")
_DOSE_CONTEXT = re.compile(r"(?i)\b(?:drops?|bleach|dose|disinfect(?:ion|ed|ing)?)\b")
_FACTOR_CONTEXT = re.compile(r"(?i)\bexact factor\b|\b1\s+(?:u\.?s\.?\s+(?:liquid\s+)?|imperial\s+|imp\s+)?gallons?\s*=")


def _answer_sentences(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=[.!?;])\s+(?!\d)|\n+", text or "") if part]


_HEDGE = re.compile(r"(?i)\b(can'?t|cannot|not|n't|no|uncertain|may|might|unclear|too small|sure|unreliable|"
                    r"not enough|if|whether)\b")
_VERDICT = re.compile(r"(?i)\b(better|worse)\b|\b(survives?|survived|does|did|performs?|performed)\s+better\b")


def _too_small_to_tell(answer: str) -> str:
    """When two proportions can't be told apart: what in the answer says one is better anyway, or "".
    "75% is higher than 60%" is true and fine; "site A has better survival" is the conclusion the counts
    don't support. Benchmark rea-016 (U75) opened "Yes, ..."; the first live U76 test opened "No, site A
    does not have better survival" and ended "Therefore, site A has better survival"."""
    text = re.sub(r"(?m)^[ \t]*\*[\[(].*$", "", answer or "").strip()
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", text) if x.strip()]
    if not sentences:
        return ""
    opening = sentences[0]
    claims = [x for x in sentences if _VERDICT.search(x) and not _HEDGE.search(x)]
    opens_yes = re.match(r"(?i)\W*yes\b", opening) is not None
    opens_no = re.match(r"(?i)\W*no\b", opening) is not None or (_VERDICT.search(opening) and
                                                                re.search(r"(?i)\b(not|n't)\b", opening))
    if opens_no and claims:
        return (f'the answer contradicts itself: its first line says "{opening[:70]}" and later "{claims[0][:70]}"; '
                "and it can't be either way")
    if opens_yes or claims:
        return f'the answer says one is better ("{(claims[0] if claims else opening)[:80]}")'
    return ""


def check(answer: str, w: Worked) -> str:
    """A line for under the answer when it doesn't contain the worked-out result or contradicts
    it ("lasts 12 days" when it lasts 1; "enough" with a shortfall), else ""."""
    text = (answer or "").replace(",", "")
    if not w.ok:
        return ""
    if w.facts.get("overlap"):
        note = _too_small_to_tell(answer)
        if note:
            return f"*(Cursiv's check: {note}, but Cursiv's code worked out that these counts can't show that: {w.statement})*"
        return ""            # it didn't claim a difference: that's what matters here, not quoting 75%
    if w.facts and "overlap" not in w.facts:
        from cursiv_v215.core import resources
        clash = resources.contradictions(answer, w.facts)
        if clash:
            return ("*(Cursiv's check: the answer contradicts what Cursiv's code worked out: " + "; ".join(clash)
                    + f". Worked out exactly: {w.statement})*")
    if w.value is not None:
        # rounding is fine ("about 54.3" for 54.32); a different number isn't
        wanted = [w.value] + list(w.facts.get("also", []))
        if w.tool == "units":
            destination = str(w.facts.get("destination_unit", ""))
            if "gallon" in destination or destination == "gal":
                unit_values = re.compile(
                    r"(?i)(?P<number>-?\d+(?:\.\d+)?)\s*(?P<unit>(?:(?:u\.?s\.?)(?:\s+liquid)?\s+|"
                    r"imperial\s+|imp\s+)?gallons?|gals?|gal)\b")
                expected_system = "imperial" if "imperial" in destination or destination.startswith("imp ") else "us"
                seen_unit = False
                for sentence in _answer_sentences(text):
                    if _FACTOR_CONTEXT.search(sentence) or _DOSE_CONTEXT.search(sentence):
                        continue
                    for match in unit_values.finditer(sentence):
                        seen_unit = True
                        written = match.group("unit").lower()
                        written_system = "imperial" if "imperial" in written or written.startswith("imp ") else "us"
                        n = match.group("number")
                        if written_system != expected_system or abs(float(n) - w.value) > _rounding_tolerance(n) + 1e-12:
                            return (f"*(Cursiv's check: the answer gives {n} {written}, but the conversion code worked out "
                                    f"{w.statement})*")
                if not seen_unit:
                    return f"*(Cursiv's check: the answer omits the requested gallon unit; the conversion code worked out {w.statement})*"
            elif "liter" in destination or "litre" in destination or destination == "l":
                unit_values = re.compile(r"(?i)(?P<number>-?\d+(?:\.\d+)?)\s*(?P<unit>liters?|litres?|l)\b")
                seen_unit = False
                for sentence in _answer_sentences(text):
                    if _FACTOR_CONTEXT.search(sentence) or _DOSE_CONTEXT.search(sentence):
                        continue
                    for match in unit_values.finditer(sentence):
                        seen_unit = True
                        n = match.group("number")
                        if abs(float(n) - w.value) > _rounding_tolerance(n) + 1e-12:
                            return (f"*(Cursiv's check: the answer gives {n} {match.group('unit')}, but the conversion code "
                                    f"worked out {w.statement})*")
                if not seen_unit:
                    return f"*(Cursiv's check: the answer omits the requested liter unit; the conversion code worked out {w.statement})*"
        if any(abs(float(n) - v) <= _rounding_tolerance(n) + 1e-12
               for n in re.findall(r"-?\d+(?:\.\d+)?", text) for v in wanted):
            return ""
        # "7/8" for 0.875 (benchmark num-003, U68 and U75)
        if any(int(b) and abs(int(a) / int(b) - v) < 1e-9
               for a, b in re.findall(r"(?<![\d.])(\d+)\s*/\s*(\d+)(?!\d|\.\d)", text) for v in wanted):
            return ""
    elif re.search(r"(?<![\d:.])" + re.escape(w.answer.replace(",", "")) + r"(?![\d])", text):
        return ""
    elif re.fullmatch(r"-?\d+(?:\.\d+)?", w.answer or "") and any(
            int(b) and abs(int(a) / int(b) - float(w.answer)) < 1e-9
            for a, b in re.findall(r"(?<![\d.])(\d+)\s*/\s*(\d+)(?!\d|\.\d)", text)):
        return ""                                   # "7/8" for 0.875 (benchmark num-003, U68 and U75)
    description = "calculated result" if w.tool == "units" else "worked out exactly"
    return f"*(Cursiv's check: {description}, {w.statement[0].lower() + w.statement[1:]})*"


def correct_units_answer(answer: str, w: Worked) -> str | None:
    """Repair only a wrong destination-unit conversion claim, preserving other answer content."""
    if w.tool != "units":
        return None
    label = str(w.facts.get("destination_label", ""))
    expected = re.findall(r"(-?\d+(?:\.\d+)?)\s+" + re.escape(label) + r"\b", w.statement, re.I)
    if not label or not expected:
        return None
    expected_number = expected[-1]
    conversion_claim = _CONVERSION_CLAIM
    if "gallon" in str(w.facts.get("destination_unit", "")) or w.facts.get("destination_unit") == "gal":
        quantity = re.compile(
            r"(?i)(?P<number>-?\d+(?:\.\d+)?)\s*(?P<unit>(?:(?:u\.?s\.?)(?:\s+liquid)?\s+|"
            r"imperial\s+|imp\s+)?gallons?|gals?|gal)\b")
        expected_system = "imperial" if "imperial" in label.lower() else "us"
        def replacement(match: re.Match) -> str:
            unit = match.group("unit").lower()
            system = "imperial" if "imperial" in unit or unit.startswith("imp ") else "us"
            number = match.group("number")
            if system == expected_system and abs(float(number) - w.value) <= _rounding_tolerance(number) + 1e-12:
                return match.group(0)
            return f"{expected_number} {label}"
    elif "liter" in str(w.facts.get("destination_unit", "")) or \
            "litre" in str(w.facts.get("destination_unit", "")) or w.facts.get("destination_unit") == "l":
        quantity = re.compile(r"(?i)(?P<number>-?\d+(?:\.\d+)?)\s*(?P<unit>liters?|litres?|l)\b")
        def replacement(match: re.Match) -> str:
            number = match.group("number")
            if abs(float(number) - w.value) <= _rounding_tolerance(number) + 1e-12:
                return match.group(0)
            return f"{expected_number} {label}"
    else:
        return None
    sentences = _answer_sentences(answer or "")
    changed = False
    for index, sentence in enumerate(sentences):
        if not conversion_claim.search(sentence) or _FACTOR_CONTEXT.search(sentence) or _DOSE_CONTEXT.search(sentence):
            continue
        updated, count = quantity.subn(replacement, sentence)
        if count and updated != sentence:
            sentences[index] = updated
            changed = True
    corrected = " ".join(part.strip() for part in sentences if part.strip())
    return corrected if changed and not check(corrected, w) else None

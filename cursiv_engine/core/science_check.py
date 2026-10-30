"""
Checks on scientific content in a model's draft, done by Cursiv's code (U100 audit).

From the owner's U99 test run:
  * Dissolved oxygen: the model made up "DO_sat = 14.6 - 0.012 T - 0.0002 T^2" and gave 14.3 mg/L
    at 18.6 °C. Air-saturated fresh water at 18.6 °C holds about 9.35 mg/L. Cursiv now has the
    standard equation (below) and notes any saturation figure in a draft that disagrees with it.
  * A "hypothetical" experiment came with a results table written as if it had been run.
    Invented numbers now get a line saying they are illustrations, not measurements.
  * Example coordinates "73.9°F, 73.9°G, 73.9°H" were shown as coordinates. A latitude must end
    in N or S (0-90), a longitude in E or W (0-180); anything else is flagged as not a location.

Each check returns one line for under the answer, or "". None of them rewrites the answer.
"""
from __future__ import annotations

import math
import re

# Benson & Krause (1984), as given in APHA Standard Methods 4500-O and used by USGS: oxygen
# solubility in fresh water in equilibrium with air at 1 atm, mg/L. Valid 0-40 °C.
DO_SOURCE = ("Benson & Krause (1984) equation, as in APHA Standard Methods 4500-O: fresh water, "
             "air-saturated, 1 atm, 0-40 °C")


def do_saturation(temp_c: float) -> float:
    if not 0 <= temp_c <= 40:
        raise ValueError("the oxygen solubility equation is valid from 0 to 40 °C")
    t = temp_c + 273.15
    return math.exp(-139.34411 + 1.575701e5 / t - 6.642308e7 / t ** 2 + 1.243800e10 / t ** 3 - 8.621949e11 / t ** 4)


_DO = re.compile(r"(?i)\b(?:dissolved oxygen|DO_?sat\w*|\bDO\b|oxygen (?:saturation|solubility)|(?:saturation|solubility) of oxygen)")
_SAT_CLAIM = re.compile(
    r"(?i)(?:at|of)\s+(-?\d+(?:\.\d+)?)\s*°?\s*C\b(?:[^.\n]|\.(?=\d)){0,120}?\b(\d{1,2}(?:\.\d+)?)\s*mg\s*/\s*L"
    r"|(\d{1,2}(?:\.\d+)?)\s*mg\s*/\s*L(?:[^.\n]|\.(?=\d)){0,80}?\bat\s+(-?\d+(?:\.\d+)?)\s*°?\s*C\b")
# A decimal point inside a number ("12.5–13.0 mg/L") doesn't end the sentence (U103 demo: a range hid the claim).
_MADE_UP_FORMULA = re.compile(r"(?i)DO_?sat\w*\s*(?:\([^)]*\))?\s*=\s*[-\d.]")


def do_note(draft: str) -> str:
    """A line when the draft gives a saturation figure the standard equation disagrees with."""
    if not _DO.search(draft or "") or not re.search(r"(?i)saturat|solubil|DO_?sat|maximum", draft or ""):
        return ""
    for m in _SAT_CLAIM.finditer(draft):
        before = re.split(r"[.!?]\s|\n", draft[max(0, m.start() - 40):m.start()])[-1]     # same sentence only
        if (not re.search(r"(?i)saturat|solubil|DO_?sat|maximum|hold", before + m.group(0))
                or re.search(r"(?i)\b(?:read(?:s|ing)?|measured|meter)\b", before[-15:] + m.group(0))):
            continue      # U103: "at 10 °C, a reading of 12.5 mg/L" is a measurement, not a saturation claim
        temp, value = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        try:
            expected = do_saturation(float(temp))
        except ValueError:
            continue
        if abs(float(value) - expected) > 0.3:
            return (f"*(Cursiv's check: the draft gives {value} mg/L for oxygen saturation at {temp} °C. The standard "
                    f"equation gives {expected:.2f} mg/L ({DO_SOURCE}). Saturation is the most the water can hold "
                    f"from the air, not what's actually dissolved; only a meter reading tells you that.)*")
    if _MADE_UP_FORMULA.search(draft):
        return (f"*(Cursiv's check: the formula above isn't one Cursiv recognises. For oxygen saturation use the "
                f"{DO_SOURCE}; Cursiv can work it out: ask \"oxygen saturation at 18.6 °C\".)*")
    return ""


def saturation_answer(question: str) -> str | None:
    """'oxygen saturation at 18.6 °C' / 'DO saturation for 18.6C water' -> the number, worked out."""
    q = question or ""
    if not (_DO.search(q) and re.search(r"(?i)saturat|solubil|how much oxygen can", q)):
        return None
    if re.search(r"(?i)\bpercent\b|%", q) and re.search(r"\d\s*mg\s*/\s*L", q, re.I):
        return None          # "7.8 mg/L ... what percent saturation?" is core/fieldsci.py do_percent (U101)
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*°?\s*C\b", q)
    if not m:
        return None
    temp = float(m.group(1))
    try:
        value = do_saturation(temp)
    except ValueError as exc:
        return f"Cursiv didn't calculate this: {exc}.\n\n*[Sources: Cursiv calculation (no AI model)]*"
    return (f"Oxygen saturation in fresh water at {m.group(1)} °C is about {value:.2f} mg/L "
            f"({DO_SOURCE}).\n\nThat's the most the water holds in balance with air; the dissolved oxygen actually "
            "present can be lower (decay, night-time respiration) or higher (photosynthesis), so measure it with a "
            "calibrated meter. Salt water and high altitude hold less.\n\n"
            "*[Sources: Cursiv calculation (oxygen solubility; no AI model)]*")


_HYPOTHETICAL = re.compile(r"(?i)\b(?:hypothetical|invent|imagine|made[- ]up|fictional|simulat\w*|example data|"
                           r"sample data|pretend|mock)\b")


def simulated_note(question: str, draft: str, *, context: str = '', calculated: str = '') -> str:
    """Flag additional illustrative results, never label supplied scenario inputs invented.

    `calculated` comes from the actual application calculator record. Ordinary
    model arithmetic remains an inference, not an observed experimental result.
    """
    if not _HYPOTHETICAL.search(question or ""):
        return ""
    if re.search(r'(?i)\b(?:poem|story|post|tweet|caption|joke|roast)\b', question) and not re.search(r'(?i)\bexperiment|results table\b', question):
        return ''
    from decimal import Decimal
    def values(text, *, word_numbers=False):
        if word_numbers:
            words=dict(zero=0,one=1,two=2,three=3,four=4,five=5,six=6,seven=7,eight=8,nine=9,ten=10,
                eleven=11,twelve=12,thirteen=13,fourteen=14,fifteen=15,sixteen=16,seventeen=17,eighteen=18,nineteen=19,twenty=20)
            text=re.sub(r'(?i)\b('+'|'.join(words)+r')\b',lambda m:str(words[m[0].lower()]),text)
        return {Decimal(n) for n in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', text)}
    supplied = values((question or '') + '\n' + context,word_numbers=True)
    allowed = supplied | values(calculated)
    # List/table row numbers are structure, not measured data.
    body = re.sub(r'(?m)^\s*\d+[.)]\s+', '', draft or '')
    fresh = values(body) - allowed
    if not fresh:
        return ""
    shown = ', '.join(str(n) for n in sorted(fresh)[:6])
    if re.search(r'(?i)\b(?:experiment|trial|measured results?|results table|example data|sample data)\b', question + '\n' + body):
        return (f'*(Cursiv\'s check: additional result values ({shown}) were not supplied or calculated by Cursiv. '
                'Treat them as invented for illustration, not real measurements. User-supplied inputs are separate; '
                'no experiment was established by this response.)*')
    return (f'*(Cursiv\'s check: additional scenario values ({shown}) are unverified assumptions or model-derived '
            'values, not established observations. The supplied scenario inputs are not invented by the assistant.)*')


_COORD = re.compile(r"(-?\d{1,3}(?:\.\d+)?)\s*°\s*([A-Za-z])\b\s*,?\s*(-?\d{1,3}(?:\.\d+)?)\s*°\s*([A-Za-z])\b")


def coordinate_note(draft: str) -> str:
    bad = []
    for m in _COORD.finditer(draft or ""):
        lat, lat_h, lon, lon_h = float(m.group(1)), m.group(2).upper(), float(m.group(3)), m.group(4).upper()
        if lat_h in "CF" and lon_h in "CF":
            continue                                       # two temperatures, not a coordinate
        if lat_h not in "NS" or lon_h not in "EW" or abs(lat) > 90 or abs(lon) > 180:
            bad.append(m.group(0).strip())
    if not bad:
        return ""
    shown = "; ".join(dict.fromkeys(bad[:4]))
    return (f"*(Cursiv's check: {shown} isn't a valid location: a latitude ends in N or S (0-90), a longitude in E or W "
            "(0-180). Treat any example coordinates above as placeholders, not real sites.)*")


def grounding_note(question: str, draft: str, sources: str = '') -> str:
    """Claim-specific source/causality checks, independent of optional model review."""
    from .verify import citation_problems
    problems = citation_problems(question, sources, draft)
    if re.search(r'(?i)\bnotes say\b',question) and re.search(r'(?i)\btable (?:lists|includes)\b',question):
        if re.search(r'(?i)\btable\b[^.\n]{0,100}\b(?:more reliable|most accurate|direct record)\b',draft):
            problems.append('the conflicting sample totals are unresolved. A table is not established as more reliable '
                'than the notes merely by its format; reconcile the original records before choosing the report total')
    if re.search(r'(?i)\b(?:mine|mining|acid mine drainage)\b',question) and re.search(r'(?i)\bpH\b',question):
        for sentence in re.split(r'(?<=[.!?])\s+|\n',draft):
            if not re.search(r'(?i)acid mine drainage|\bAMD\b|\bmine\b',sentence): continue
            if re.search(r"(?i)\b(?:not|cannot|can't|doesn.t|may|might|could|would|if|when|assuming|possible|consistent with|hypothesis|unconfirmed)\b",sentence): continue
            if re.search(r'(?i)\b(?:confirmed|proven|definitely|certainly|conclusively|caused by)\b',sentence):
                problems.append('the specific mining source is not confirmed by pH and proximity alone; acid mine drainage is a hypothesis, not a verified cause. Investigate it and avoid drinking potentially contaminated water while its safety is unresolved')
                break
    return ('*(Cursiv\'s evidence check: ' + '; '.join(dict.fromkeys(problems)) + '.)*') if problems else ''


# U103 overconfidence benchmark (bench/overconfidence, scripts/overconfidence_bench.py). Asked about one
# reading, a look, a smell or one sample, qwen3:4b-instruct answered 6 of 30 with a settled verdict the
# evidence can't carry: "No, 4.2 mg/L is not a sign your meter is broken", "Yes, you can drink the spring
# water without treating it", "10 mg/L nitrate is generally considered safe for children" (that is the legal
# limit itself). The caveats came after. Hedged answers lead with the doubt ("Not necessarily", "doesn't
# prove"), so the rule looks at the verdict: the first sentence and any line that starts "Yes", "No" or "So".
OVERCONFIDENCE_MARK = "*(Cursiv's check: this answer sounds more certain"
_SAFE = re.compile(r"(?i)\b(?:(?:is|are|it's|should be|looks|seems|considered)\s+(?:perfectly |completely |totally |generally )?"
                   r"safe(?:\s+(?:to|for)\s+\w+)?|safe\s+(?:to|for)\s+(?:drink|swim|eat|consum)\w*"
                   r"|nothing to worry about|no (?:health )?(?:risk|concern)s?\b)")
_NORMAL = re.compile(r"(?i)\b(?:(?:is|are|that's|it's|looks|seems)\s+(?:perfectly |completely |totally |quite )?"
                     r"(?:normal|fine|healthy|typical|expected)|not a sign of (?:an? )?(?:error|problem|fault))\b")
_PROOF = re.compile(r"(?i)\b(?:proves?|proof that|confirms? (?:that|it)|definitely|certainly|without (?:a )?doubt"
                    r"|guarantee[sd]?|100% (?:sure|certain)|clearly (?:shows|indicates|caused))\b")
_LEAD_HEDGE = re.compile(r"(?i)\b(?:not necessarily|doesn't|does not|don't|do not|cannot|can't|can not|isn't enough"
                         r"|not (?:enough|all|always|definitive|proof|possible|sure|certain)|depends|unless|single|alone"
                         r"|by itself|hard to say|unclear|might|may|not the only|no one can (?:say|tell|know))\b")
_VERDICT = re.compile(r"(?i)^(?:so,?\s*)?(yes|no)\b")
_ASKS_PROOF = re.compile(r"(?i)\b(?:prove|proof|confirm|mean|definitely|certain|whole)\b")
_RANGE = re.compile(r"\d+(?:\.\d+)?\s*(?:-|–|to|and)\s*\d+(?:\.\d+)?")
_OWN_EVIDENCE = re.compile(r"(?i)\b(?:my|our|i (?:got|measured|found|read|have|only|saw|see|noticed)|there's|there is"
                           r"|reading|sample|measured|test(?:ed)? (?:strip|kit|showed)|looks|smell\w*|tastes|meter)\b")
_READING = re.compile(r"(?i)\d(?:[\d.,]*)\s*(?:mg\s*/\s*L|µS\s*/\s*cm|uS\s*/\s*cm|NTU|ppm|ppb|ppt|°\s*[CF]\b|CFU|colonies)")
_JUDGEMENT = re.compile(r"(?i)\b(?:normal|safe|prove|confirm|sign of|problem|good|bad|fine|healthy|polluting|toxic|"
                        r"contaminated|broken|error|legal|law)\b")
_CALC_WORDS = frozenset(('yes no the your our a an arithmetic mean average median mode sum product ratio total '
    'result answer value conversion converted of these those sample samples reading readings numbers values '
    'is are was equals equal exactly definitely certainly approximately about and '
    'cm mm km m mg g kg ml l s sec seconds minute minutes hour hours c f celsius fahrenheit degrees '
    'per percent ms us ntu ppm').split())


def _verdict_lines(draft: str) -> list[str]:
    """The first sentence, and any line that starts with a verdict ("Yes", "No", "So yes")."""
    draft = draft.replace("’", "'")           # models write doesn’t as often as doesn't
    lines = [re.sub(r"[*_`#>]+", "", ln).strip(" -—:") for ln in draft.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith(("(", "["))]          # Cursiv's own notes and sources
    if not lines:
        return []
    first = re.split(r"(?<=[a-z0-9)%][.!?])\s+(?=[A-Z])", lines[0])[0]     # not after the "E." of "E. coli"
    return [first] + [ln for ln in lines[1:] if _VERDICT.match(ln)]


def overconfidence_note(question: str, draft: str, *, authored: str = 'model') -> str:
    """A line when the verdict on the person's own reading or sample is stated as settled.

    Only for questions resting on the person's own limited evidence (a reading, a look, one sample).
    A "No" to "does that prove / mean ...?" is the careful answer and passes; so does "Yes, that's
    normal" to "is that normal?" when the answer gives the range it's judged against."""
    q, draft = question or "", draft or ""
    # Provenance is supplied by application control flow, never inferred from
    # words such as "calculated by code" in a model's answer.
    if authored == 'native':
        return ''
    from .turn_policy import creative_request
    if creative_request(q) and not _SAFE.search(draft):
        return ''
    if not (_OWN_EVIDENCE.search(q) or (_READING.search(q) and _JUDGEMENT.search(q))):
        return ""
    asks_normal = bool(re.search(r"(?i)\bnormal\b", q)) and bool(_RANGE.search(draft))
    for line in _verdict_lines(draft):
        if (authored == 'calculation' and re.search(r'\d', line)
                and set(re.findall(r'[a-z]+', line.casefold())) <= _CALC_WORDS):
            continue  # only a numeric/math statement backed by a real calculator record
        if _LEAD_HEDGE.search(line):
            continue
        if (re.match(r'(?i)^no (?:matching\b|evidence\b|records?\b|entries\b|results?\b)', line)
                and not (_SAFE.search(line) or _NORMAL.search(line) or _PROOF.search(line))):
            continue
        verdict = _VERDICT.match(line)
        if verdict:
            if verdict.group(1).lower() == "no" and _ASKS_PROOF.search(q):
                continue
            if asks_normal:
                continue
        elif not (_SAFE.search(line) or _PROOF.search(line) or (_NORMAL.search(line) and not asks_normal)):
            continue
        quoted = line if len(line) <= 90 else line[:87].rsplit(" ", 1)[0] + "…"
        if re.search(r"(?i)\b(?:drink\w*|swim\w*|eat|edible|food|potable)\b", q) or (
                re.search(r'(?i)\bwater\b', q) and re.search(r'(?i)\bcontaminat|toxic|health', q)):
            what = "only a certified lab test (or the local health authority) can say whether it is safe"
        else:
            what = ("one reading or one look can't settle it. Repeat the measurement, check the instrument's "
                    "calibration and compare against a stated reference range")
        return f"{OVERCONFIDENCE_MARK} (\"{quoted}\") than one observation supports: {what}.)*"
    return ""

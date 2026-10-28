"""
Field-notebook confirm cards built by Cursiv's own code (U100 audit of the U99 test run).

Three things the test run got wrong, fixed here without the model:

  * Plain-words records ("Record field observation: ORION-742, sample W-001, 18.6°C, 12:40,
    site Willow Basin") were saved straight away and parsed into nonsense. They now become a
    card from fieldlog.parse, showing exactly what would be stored.
  * The model put the first code it saw into site ("site: ORION-742", "site: W-003").
    fix_details() keeps a code in site only if the person called it a site; otherwise it
    is kept word for word in the note -- never guessed into another field.
  * "Correct W-001 temperature from 18.6°C to 18.9°C without erasing the original" now
    finds the record, checks the old value really is 18.6, and offers the notebook's own
    append-only correction (the original stays, the correction links to it).

Every card runs one of the notebook's own commands on Save, with its usual receipt.
"""
from __future__ import annotations

import re

from . import fieldlog
from .intent import Action, Proposal

LOG = Action("notebook.log", True, "Save to your field notebook?", "log {details}", ("details",))
CORRECT = Action("notebook.correct", True, "Correct this observation? (the original stays)",
                 "field log correct {entry} {measure} {value} {unit} :: {reason}",
                 ("record", "change", "entry", "measure", "value", "unit", "reason"))

_RECORD = re.compile(r"(?i)^(?:please\s+)?(?:record|log|save|add)\s+(?:(?:a|an|the|this|my|new)\s+)?"
                     r"(?:field\s+)?(?:observation|reading|sample|measurement|entry)?\s*[:,-]?\s*(.+)$")
_NUM = r"-?\d+(?:\.\d+)?"
_UNIT = r"(?:°\s?[CF]|[A-Za-z/%µ]{1,6})?"
_CORRECTION = re.compile(
    r"(?i)^(?:please\s+)?(?:correct|fix|change|amend|update)\s+(?:sample\s+|record\s+|entry\s+)?"
    r"(?P<id>" + fieldlog.ID.pattern + r"|[0-9a-f]{12})(?:'s)?\s+(?P<name>[a-z][a-z .]{0,30}?)\s+"
    r"(?:reading\s+|value\s+)?from\s+(?P<old>" + _NUM + r")\s*(?P<old_unit>" + _UNIT + r")\s+to\s+"
    r"(?P<new>" + _NUM + r")\s*(?P<new_unit>" + _UNIT + r")(?P<rest>.*)$")


def confirmation(text: str) -> Proposal | None:
    """Explicit preview requests cannot fall through to the immediate structured writer.

    Only delimited procedural clauses outside quotes are removed. The resulting
    command is displayed for approval; creating this proposal performs no write.
    """
    from .turn_policy import instruction_text
    from . import file_requests
    if file_requests.recognizes(text):
        return None
    text = re.sub(r'(?i)^\s*(?:prepare|draft)\s+(?:(?:a|an)\s+)?field observation\b',
                  'Record field observation', text)
    if not _RECORD.match(text):
        return None
    visible = instruction_text(text)
    cue = re.search(r"(?i)\b(?:request|ask(?: me)?(?: for)?|require|wait for)\s+confirmation\s+before\s+sav(?:e|ing)\b|"
                    r"\bask me before sav(?:e|ing)\b|\b(?:preview|show me the parsed record)\b", visible)
    if not cue:
        return None
    # Match clause boundaries in the original string, preserving quoted data.
    boundary = re.search(r'(?i)(?:[;.\n]\s*|\s+and\s+)(?=(?:show me the parsed record|'
                         r'(?:request|ask|require|wait for|preview)\b))', visible)
    if not boundary:
        return Proposal(LOG, {'details': ''}, '', ['Separate the observation from its preview instructions with a semicolon.'])
    # instruction_text removes quoted spans, so its offsets cannot locate the payload.
    # Locate the same literal delimiter/clause in the original, outside quoted spans.
    mask = list(text)
    for match in re.finditer(r'"[^"\n]*"|(?<![A-Za-z])\x27[^\x27\n]*\x27', text):
        mask[match.start():match.end()] = ' ' * (match.end()-match.start())
    match = re.search(r'(?i)(?:[;.\n]\s*|\s+and\s+)(?=(?:show me the parsed record|'
                      r'(?:request|ask|require|wait for|preview)\b))', ''.join(mask))
    if not match:
        return Proposal(LOG, {'details': ''}, '', ['Supply observation details before the confirmation instruction.'])
    said = text[:match.start()].strip()
    proposal = record(said)
    if proposal is None:
        return Proposal(LOG, {'details': ''}, '', ['State a field observation, sample ID or measurement before requesting its preview.'])
    proposal.edit_text = text
    return proposal


def _details(fields: dict) -> str:
    parts = []
    for key, label in (("project", "project"), ("sample_id", "sample"), ("site", "site")):
        if fields.get(key):
            parts.append(f"{label}: {fields[key]}")
    for m in fields.get("measurements") or []:
        parts.append(" ".join(x for x in (m["name"], m["value"], m.get("unit", "")) if x))
    if fields.get("lat") is not None:
        parts.append(f"{fields['lat']}, {fields['lon']}")
    pieces = (re.sub(r"(?i)^(?:note\s*:\s*)+", "", p).strip() for p in (fields.get("note") or "").split("; "))
    parts += [f"note: {piece}" for piece in pieces if piece]
    return "; ".join(parts)


def fix_details(details: str, said: str) -> str:
    """A code like ORION-742 or W-003 stays in site only if the person wrote "site <code>";
    otherwise it moves to the note, as written."""
    fields = fieldlog.parse(details)
    site = fields.get("site", "")
    if site and fieldlog.ID.fullmatch(site) and not re.search(
            rf"(?i)\bsite\s*:?\s*{re.escape(site)}\b", said or ""):
        fields["site"] = ""
        if site not in (fields.get("sample_id"), fields.get("project")) and site not in fields.get("note", ""):
            fields["note"] = "; ".join(x for x in (site, fields.get("note", "")) if x)
        return _details(fields)
    return details


def record(text: str) -> Proposal | None:
    """A card for a plain-words record, from the notebook's own parser (no model)."""
    m = _RECORD.match((text or "").strip())
    if not m:
        return None
    payload = m.group(1).strip()
    fields = fieldlog.parse(payload)
    if not (fields["measurements"] or fields["sample_id"] or fields["project"] or fieldlog.ID.search(payload)):
        return None                       # no reading or code: not clearly an observation
    details = _details(fields)
    problems = [] if (fields["measurements"] or fields["note"] or fields["sample_id"]) else ["nothing to save"]
    return Proposal(LOG, {"details": details}, f"log {details}", problems)


# A deliberately narrow sentence grammar: a reported measurement, an explicit place,
# and an optional reported clock time. Questions and illustrative prose cannot match.
_OBSERVATION = re.compile(
    r"(?i)^(?P<name>water temp(?:erature)?|air temperature|soil temperature|temperature|pH|"
    r"water depth|depth|conductivity|turbidity|dissolved oxygen)\s+"
    r"(?:(?:was|is|measured|reads?|of)\s+)?(?P<value>" + _NUM + r")\s*"
    r"(?P<unit>degrees?(?:\s+(?:Celsius|Fahrenheit))?|Celsius|Fahrenheit|°?\s?[CF]|"
    r"mg\s*/\s*[Ll]|[uµ]S\s*/\s*cm|NTU|ppm|cm|mm|m|%)?\s+"
    r"(?:at|in)\s+(?P<site>[A-Za-z][A-Za-z0-9 '\-]{0,79}?)"
    r"(?:\s+(?:around|at|about)\s+(?P<time>(?:[01]?\d|2[0-3]):[0-5]\d(?:\s*[ap]\.?m\.?)?))?[.!]?$"
)


def observation(text: str) -> Proposal | None:
    """Preview ordinary reported measurements; never infer scale, date or AM/PM."""
    said = re.sub(r"\s+", " ", (text or "").strip())
    match = _OBSERVATION.fullmatch(said)
    if not match:
        return None
    name, unit = match['name'], (match['unit'] or '').strip()
    if 'temp' in name.lower():
        if re.fullmatch(r'(?i)(?:degrees?\s+)?Celsius|°?\s?C', unit):
            unit = '°C'
        elif re.fullmatch(r'(?i)(?:degrees?\s+)?Fahrenheit|°?\s?F', unit):
            unit = '°F'
        elif re.fullmatch(r'(?i)degrees?', unit):
            unit = ''
    site = match['site']
    notes = [f"Reported observation time: {match['time']}"] if match['time'] else []
    day = re.search(r'(?i)\s+(today|yesterday)$', site)
    if day:
        notes.append('Reported observation date: ' + day[1])
        site = site[:day.start()]
    fields = {'site': site, 'measurements': [dict(name=name, value=match['value'], unit=unit)],
              'note': '; '.join(notes)}
    problems = []
    if re.search(r'(?i)\s+(?:at|around|about|on|last|this|today|yesterday|tomorrow)\b', site):
        problems.append('The place and reported time are unclear. Keep just the place after "at", '
                        'and use a clock time after "around" before saving.')
    if not unit and name.lower() != 'ph':
        problems.append('Was that Celsius or Fahrenheit? Add the scale before saving.' if 'temp' in name.lower()
                        else 'What unit was this measured in? Add it before saving.')
    details = _details(fields)
    return Proposal(LOG, {'details': details}, 'log ' + details, problems, edit_text=said)


def understood(proposal: Proposal | None) -> bool:
    """The parser read the whole message: a reading or a labelled code, and every note piece
    is only a code or a clock time. Then its card is used rather than the model's rewording
    (which dropped ORION-742 and turned 12:40 into "recorded at 12:40")."""
    if proposal is None or proposal.problems or proposal.action is not LOG:
        return False
    fields = fieldlog.parse(proposal.slots["details"])
    pieces = [p for p in (fields.get("note") or "").split("; ") if p]
    leftovers = [p for p in pieces if not (fieldlog.ID.fullmatch(p) or re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", p))]
    return bool(fields["measurements"] or fields["sample_id"]) and not leftovers


def _same_measure(name: str, wanted: str) -> bool:
    a, b = (re.sub(r"\btemp\b", "temperature", re.sub(r"[^a-z ]", "", x.lower())).strip() for x in (name, wanted))
    return a == b or a.endswith(" " + b) or b.endswith(" " + a) or a in b.split() or b in a.split()


def correction(text: str) -> Proposal | None:
    m = _CORRECTION.match((text or "").strip())
    if not m:
        return None
    code, name = m.group("id"), m.group("name").strip()
    old, new = m.group("old"), m.group("new")
    unit = (m.group("new_unit") or m.group("old_unit") or "").replace(" ", "")
    rows = [r for r in fieldlog.current() if code in (r.get("id"), r.get("sample_id"))]
    # The reason kept with the correction is the person's own request, word for word.
    slots = {"record": code, "change": f"{name}: {old} → {new} {unit}".strip(), "entry": "", "measure": name,
             "value": new, "unit": unit, "reason": re.sub(r"\s+", " ", text.strip())[:200].replace("::", ":")}
    if not rows:
        return Proposal(CORRECT, slots, "", [f"there's no record for {code} in your field notebook"])
    if len(rows) > 1:
        return Proposal(CORRECT, slots, "", [f"{len(rows)} current records have {code}; correct one in the Field Notebook window"])
    row = rows[0]
    match = [x for x in row.get("measurements") or [] if _same_measure(x["name"], name)]
    if not match:
        have = ", ".join(x["name"] for x in row.get("measurements") or []) or "no measurements"
        return Proposal(CORRECT, slots, "", [f"{code} has no {name} reading ({have})"])
    current = match[0]
    if current.get("number") is None or abs(float(current["number"]) - float(old)) > 1e-9:
        return Proposal(CORRECT, slots, "", [f"{code}'s {current['name']} is {current['value']}, not {old}"])
    slots.update(entry=row["id"], measure=current["name"], unit=unit or current.get("unit", ""))
    slots["change"] = f"{current['name']}: {current['value']} → {new} {slots['unit']}".strip()
    return Proposal(CORRECT, slots, re.sub(r"\s+", " ", CORRECT.template.format(**slots)), [])


def context_correction(text: str, history: list[dict]) -> Proposal | None:
    """Use only an actual notebook receipt in this conversation, never assistant prose."""
    match = re.fullmatch(
        r"(?i)(?:I|we) (?:recorded|entered|wrote down) (?:the )?wrong "
        r"(?P<name>water temperature|temperature|pH|depth|turbidity|dissolved oxygen) "
        r"(?:earlier|in (?:my|the) last entry)[.!]?\s*It should (?:have been|be) "
        r"(?P<value>" + _NUM + r")\s*(?P<unit>°?[CF]|cm|mm|m|NTU|mg/L)?[.!]?", (text or '').strip())
    if not match:
        return None
    name = match['name']
    slots = dict(record='', change=f"{name} → {match['value']}")
    candidates = []
    for turn in reversed(history or []):
        receipt = turn.get('notebook_receipt') or {}
        if turn.get('role') == 'assistant' and receipt.get('ok') and receipt.get('status') in ('saved', 'already_recorded', 'read'):
            candidates = receipt.get('records') or []
            break
    current = {row['id']: row for row in fieldlog.current()}
    targets = [current[row['id']] for row in candidates if row.get('id') in current and
               any(_same_measure(item['name'], name) for item in current[row['id']].get('measurements', []))]
    if len(targets) != 1:
        return Proposal(CORRECT, slots, '', ['Which observation should change? Open Field Notebook and select it, '
                                           'or give the sample ID and the old and new readings.'])
    row = targets[0]
    measures = [item for item in row['measurements'] if _same_measure(item['name'], name)]
    if len(measures) != 1:
        return Proposal(CORRECT, slots, '', ['Several readings match. Select the observation in Field Notebook.'])
    item = measures[0]
    if match['unit'] and match['unit'].lstrip('°').casefold() != item.get('unit', '').lstrip('°').casefold():
        return Proposal(CORRECT, slots, '', ['The correction uses a different unit. State the new value in the stored unit.'])
    result = correction(f"Correct {row['id']} {item['name']} from {item['value']} {item.get('unit', '')} "
                        f"to {match['value']} {item.get('unit', '')}")
    if result and result.ok:
        result.slots['reason'] = re.sub(r'\s+', ' ', text.strip())[:200].replace('::', ':')
        result.command = re.sub(r'\s+', ' ', CORRECT.template.format(**result.slots))
        result.edit_text = text
    return result

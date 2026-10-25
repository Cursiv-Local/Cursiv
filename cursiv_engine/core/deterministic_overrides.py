"""Application-authored withdrawals from explicit evidence. Never calls an LLM."""
from __future__ import annotations

import re


def conflicting_doses(question: str, passages, *, supplied_text: str = '') -> str | None:
    """Narrow duplicate-condition bleach-dose conflict; do not choose a source.

    Different concentrations or clear/cloudy conditions are not treated as the
    same instruction. Other contradictions remain the ordinary checker's job.
    """
    if not re.search(r'(?i)\b(?:drops?|dose|bleach|how much)\b', question):
        return None
    groups = {}
    sources = [(page.text, f'{page.name} p. {page.page}') for page in passages]
    if supplied_text:
        sources.append((supplied_text, 'This message'))
    for text, label in sources:
        for sentence in re.split(r'[\n!?]|(?<!\d)\.(?!\d)', text):
            if 'bleach' not in sentence.lower():
                continue
            match = re.search(r'(?i)\b(\d+)\s+drops?\b.{0,40}?\bper\s+(liter|litre|gallon)\b', sentence)
            if not match:
                continue
            condition = 'cloudy' if re.search(r'(?i)\bcloudy\b', sentence) else (
                'clear' if re.search(r'(?i)\bclear\b', sentence) else 'unspecified')
            concentration = tuple(re.findall(r'\d+(?:\.\d+)?\s*%', sentence))
            key = (match[2].lower().replace('litre', 'liter'), condition, concentration)
            groups.setdefault(key, []).append((int(match[1]), label))
    for rows in groups.values():
        if len({row[0] for row in rows}) > 1:
            evidence = '; '.join(dict.fromkeys(f'{label}: {amount} drops' for amount, label in rows))
            lead = 'The supplied instructions conflict: ' if supplied_text else 'The supplied documents conflict: '
            return (lead + evidence + '. No dose is selected. '
                    'Resolve the source, product concentration and conditions before using an instruction. '
                    'A model choosing one number would not verify it.')
    return None


def calculation(worked, mismatch: str) -> str | None:
    if not mismatch or not worked:
        return None  # unit conversions retain the existing narrow in-place correction
    lead = worked.lead + '\n\n' if worked.lead else ''
    # U100 audit: lead with the answer; one short line says why the model's draft isn't shown.
    return (lead + worked.statement + "\n\n(The AI model's draft gave a different number and was withdrawn; "
            f"this is Cursiv's own calculation.)\n\n*[Sources: Cursiv calculation ({worked.tool}; no AI model)]*")


def execution(issues, evidence=None) -> str | None:
    failures = [p.message for p in issues if p.code in ('EXECUTION_TOOL', 'EXECUTION_MEMORY',
                'EXECUTION_REFERENCE', 'EXECUTION_DOCUMENT') or
                p.code in ('UNEXECUTED_LOOKUP', 'UNCONFIRMED_STATE_CHANGE')]
    if not failures:
        return None
    # Do not copy the disputed model claim back into the primary answer.
    details = []
    codes = {p.code for p in issues}
    if 'EXECUTION_TOOL' in codes:
        worked = getattr(evidence, 'worked', None)
        details.append('Application record: ' + ('Cursiv calculated ' + worked['result'] if worked and worked.get('ok') else
                       'no calculation tool ran for this answer.') )
    if 'EXECUTION_MEMORY' in codes and not getattr(evidence, 'memory_texts', None):
        details.append('Application record: no saved memory was given to the AI for this answer.')
    if 'UNEXECUTED_LOOKUP' in codes:
        details.append('Application record: no web lookup was recorded for this answer.')
    return ('The model’s unsupported action or source claim is withdrawn. '
            'No matching application evidence confirms that claim. '
            'Use a native command to request the operation or inspect its actual receipt.\n\n' +
            ('\n'.join(details) + '\n\n' if details else '') +
            '*[Sources: Cursiv execution-evidence check (no AI model)]*')


def reference(issues, titles, source_line: str) -> str | None:
    if not any(p.code in ('DOSE_MISMATCH', 'REFERENCE_CONTRADICTION') for p in issues):
        return None
    from . import reference as cards
    try:
        supplied = [entry for entry in cards.entries() if entry.title in titles]
        excerpts = '\n\n'.join(f'{entry.title} [{entry.id}]\n{entry.text}\n'
                                f"Reference status: {cards.evidence(entry)['state']}" for entry in supplied)
    except (OSError, ValueError, TypeError, KeyError):
        supplied, excerpts = [], ''  # a missing card must not restore unsafe model instructions
    body = ('The model draft conflicted with the supplied reference and is withdrawn. '
            'Do not use its treatment instructions.\n\n')
    body += excerpts
    if not supplied:
        body += 'The reference could not be displayed. No treatment instruction is verified here.'
    return body + '\n\n*[' + source_line + ']*'

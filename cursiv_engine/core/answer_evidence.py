"""Application-owned evidence attached to a completed answer, never parsed prose."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AnswerEvidence:
    question: str
    titles: tuple[str, ...]
    calculation: dict | None

    def receipt(self):
        return dict(domain='answer_evidence', version=1, question=self.question,
                    titles=list(self.titles), calculation=self.calculation)


def capture(question, titles, worked):
    return AnswerEvidence(question, tuple(titles), worked.record() if worked else None)


def reply(text, history):
    from . import turn_policy
    q = turn_policy.task_text(text).lower().strip().rstrip('.?!')
    if not re.fullmatch(r'what sources did you use for the bleach answer', q):
        return None
    if not turn_policy.effective(text).inspect:
        return 'Prior answer evidence was not inspected: source lookup is disabled this turn.'
    # Only the immediately preceding answer. Older doses must not be attributed
    # to a newer turn; content and model-written citation lines establish nothing.
    prior = next((row for row in reversed(history) if row.get('role') == 'assistant'), {})
    receipt = prior.get('answer_evidence')
    if not isinstance(receipt, dict) or receipt.get('domain') != 'answer_evidence' or receipt.get('version') != 1:
        return 'No application evidence receipt is available for the prior answer. Its sources cannot be confirmed.'
    calculation = receipt.get('calculation')
    titles = receipt.get('titles')
    if (not isinstance(calculation, dict) or calculation.get('tool') != 'bleach_dose'
            or calculation.get('ok') is not True or not isinstance(titles, list)):
        return 'The prior answer has no confirmed bleach_dose calculation and water-purification reference pair.'
    # Match the actual supplied reference title, without reading the reference
    # again or retroactively computing an unused dose.
    water = [t for t in titles if isinstance(t, str) and 'water' in t.lower() and 'purif' in t.lower()]
    if not water:
        return 'The prior receipt confirms bleach_dose, but no offline water-purification reference was supplied.'
    return ('For the prior answer, Cursiv supplied:\n- Offline reference: ' + '; '.join(water) +
            '\n- Code calculation: bleach_dose. Inputs: ' + str(calculation.get('inputs', {})) +
            '\n  Result: ' + str(calculation.get('result', '')) +
            '\n\n*[Sources: Prior application evidence receipt (no AI model)]*')

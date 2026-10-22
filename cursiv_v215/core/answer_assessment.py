"""Pure answer checks against an explicit execution-evidence packet.

assess() returns stable Problem records. No model, widget, disk write or network
call occurs here. Source tables are the existing bundled reference data. These
checks apply equally to a streamed draft and any optional replacement draft.
"""
from __future__ import annotations

import re
from .problems import Problem, unique


def small_sample_problems(question: str, answer: str) -> list[str]:
    """Only flag explicit n=0/1 inference claims; never infer a sample size."""
    if not re.search(r'(?i)\bn\s*=\s*[01]\b|\bsample size\s*(?:is|of|=|:)\s*[01]\b', question or ''):
        return []
    from .verify import answer_body
    for sentence in re.split(r'[.!?\n]+', answer_body(answer)):
        if re.search(r'(?i)\b(?:not|cannot|can\x27t|undefined|insufficient|unavailable|no)\b', sentence):
            continue
        if re.search(r'(?i)\bstatistically significant\b|'
                     r'\bsample standard deviation\s*(?:is|=|:)\s*\d', sentence):
            return ['a sample with fewer than two observations cannot establish sample variability or statistical significance']
    return []


def assess(question: str, answer: str, *, titles=(), searched: bool | None = None,
           evidence=None, worked=None, docs=()) -> list[Problem]:
    from . import answer_check, claims, calc, documents, file_access
    found: list[Problem] = []

    def collect(code, messages, severity='error'):
        found.extend(Problem(code, severity, str(message)) for message in messages)

    flip = answer_check.flip_flop(answer)
    if flip:
        collect('CONTRADICTORY_CONCLUSION', [f'the opening says "{flip[0]}" and later says "{flip[1]}"'])
    collect('REFERENCE_CONTRADICTION', [f'the answer advises against {step}, which the supplied reference recommends'
                                      for step in answer_check.contradictions(answer, list(titles))])
    collect('DOSE_MISMATCH', answer_check.dose_problems(answer, list(titles)))
    collect('SMALL_SAMPLE_INFERENCE', small_sample_problems(question, answer))
    if searched is not None:
        collect('UNEXECUTED_LOOKUP', answer_check.unsupported_actions(answer, searched))
    if evidence is not None:
        for check in claims.CHECKS:
            # A failed checker is an unavailable check, never an empty success.
            collect('EXECUTION_' + check.__name__.removesuffix('_notes').upper(), check(answer, evidence))
    if worked:
        miss = calc.check(answer, worked)
        if miss:
            collect('CALCULATION_MISMATCH', [miss])
    if docs:
        collect('DOCUMENT_CITATION', documents.cited_pages_problems(answer, list(docs)))
    if file_access.unverified_claim(answer):
        collect('UNCONFIRMED_STATE_CHANGE', ['the model claims a saved file or state change without a native execution receipt'])
    return unique(found)

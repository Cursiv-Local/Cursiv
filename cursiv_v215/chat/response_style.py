"""Narrow presentation rules; never remove answer content, code or requested dialogue."""
from __future__ import annotations

import re
from cursiv_v215.core import turn_policy
from cursiv_v215.core.conversation_kind import casual, reflective, requested_followup


def concise_turn(question: str) -> bool:
    q = turn_policy.task_text(question)
    if requested_followup(q):
        return False
    return (turn_policy.for_text(question) != turn_policy.Policy() or
            casual(q) or reflective(q) or
            bool(re.match(r"(?i)^(?:what (?:is|are)|who (?:is|was)|how (?:long|does|do)|"
                          r"is \d+|calculate|convert)\b", q)))


def guidance(question: str) -> str:
    notes = []
    if concise_turn(question):
        notes.append('Answer the question and stop. '
            'Do not add an unsolicited follow-up offer, a script offer, emoji or a closing question. '
            'Keep necessary warnings and clarification questions.')
    if casual(question) or reflective(question):
        notes.append('Match a restrained, practical conversational register. Avoid padded reassurance '
                     'and repeated “I’m here to help/listen” framing; keep warmth when the person seeks it. '
                     'Do not volunteer saved personal facts unrelated to the topic the person mentioned.')
    if reflective(question) and not re.search(r'(?i)\b(?:detailed|in.depth|long|essay|at least)\b|\d+\s+(?:words|paragraphs)', question):
        notes.append('Answer this specific philosophical framing in 1–3 short paragraphs, roughly '
                     '100–180 words or fewer. Address the actual contrast/question; do not repeat a '
                     'generic description of Cursiv or open with praise. Separate operational facts '
                     'from philosophical speculation; do not claim experiences or observations while '
                     'closed. Stopping execution does not erase saved records on disk. Cursiv can '
                     'retrieve selected stored facts across sessions without retraining model weights; '
                     'that is distinct from subjective recollection or a continuously active mind.')
    return '\n' + '\n'.join(notes) + '\n' if notes else ''


_OFFER = re.compile(r"(?is)^(?:let me know if\b|would you like\b|want to\b|how['’]s that feel\b|"
                    r"how about you[?]|how['’]s that sound[?]|"
                    r"how can i help(?: you)?(?: today)?[?]|"
                    r"i(?:['’]m| am) here to (?:listen|help)\b|if you(?:['’]d| would) like[, ]|"
                    r"if you(?:['’]re| are) open to it,?\s+i can\b|"
                    r"if you(?:['’]re| are) [^.!?\n,]{1,50},\s+i(?:['’]m| am) here to (?:listen|help)\b|"
                    r"i can (?:also |help you )?(?:help|write|create|make|provide|show|suggest)\b|"
                    r"thanks for sharing\b)[^.!?\n]{0,240}[.!?]?$")
_EMOJI_END = re.compile(r'(?:\s*[\U0001f300-\U0001faff\u2600-\u27bf\ufe0f\u200d])+\s*$')
_WARNING = re.compile(r"(?i)\b(?:warning|emergency|call|danger\w*|allerg\w*|insulin|must|"
                      r"cannot|don't|do not|avoid|unless)\b")


def trim_closer(question: str, answer: str) -> str:
    """Drop trailing stock sentences/emoji, retaining substantive content.

    A complete answer always remains. Quotes, lists, fenced examples, open
    conversation with requested options/questions is not rewritten.
    """
    if not concise_turn(question) or '```' in answer or '~~~' in answer:
        return answer
    original = answer.strip()
    paragraphs = re.split(r'\n\s*\n', original)
    if _WARNING.search(paragraphs[-1]) or paragraphs[-1].startswith(('>', '    ', '\t', '- ', '* ')):
        return answer
    paragraphs[-1] = _EMOJI_END.sub('', paragraphs[-1]).rstrip()
    while paragraphs:
        tail = paragraphs[-1]
        if not tail:
            paragraphs.pop()
            continue
        if _WARNING.search(tail) or tail.startswith(('>', '    ', '\t', '- ', '* ')):
            break
        sentences = re.split(r'(?<=[.!?])\s+', tail)
        if not _OFFER.fullmatch(sentences[-1].strip()):
            break
        sentences.pop()
        if sentences:
            paragraphs[-1] = ' '.join(sentences)
        else:
            paragraphs.pop()
    cleaned = '\n\n'.join(paragraphs)
    return cleaned if cleaned and cleaned != original else answer

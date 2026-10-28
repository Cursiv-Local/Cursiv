"""Narrow presentation rules; never remove answer content, code or requested dialogue."""
from __future__ import annotations

import re
from cursiv_engine.core import turn_policy
from cursiv_engine.core.conversation_kind import casual, reflective, requested_followup

GUIDANCE_HEADING = 'Current response guidance (application rules):\n'
BANTER_SYSTEM = ('You are Cursiv. This turn is light conversation. Respond to the actual joke or '
                 'figurative remark in one brief natural line. Treat obvious personification as figurative. '
                 'No analysis, advice, pep talk, generic reassurance or follow-up offer. '
                 'Do not invent personal experiences or facts about the person. Follow their tone and limits.')


def concise_turn(question: str) -> bool:
    q = turn_policy.task_text(question)
    if requested_followup(q):
        return False
    return (turn_policy.for_text(question) != turn_policy.Policy() or
            casual(q) or reflective(q) or
            bool(re.match(r"(?i)^(?:what (?:is|are)|who (?:is|was)|how (?:long|does|do)|"
                          r"is \d+|calculate|convert)\b", q)))


def guidance(question: str, history=()) -> str:
    notes = []
    if concise_turn(question):
        notes.append('Answer the question and stop. '
            'Do not add an unsolicited follow-up offer, a script offer, emoji or a closing question. '
            'Keep necessary warnings and clarification questions.')
    if casual(question) or reflective(question):
        notes.append('Match a restrained, practical conversational register. Avoid padded reassurance '
                     'and repeated “I’m here to help/listen” framing; keep warmth when the person seeks it. '
                     'Do not volunteer saved personal facts unrelated to the topic the person mentioned.')
    from cursiv_engine.core.conversation_kind import safety_or_technical
    recent_user = [m.get('content', '') for m in history[-8:] if m.get('role') == 'user'
                   and isinstance(m.get('content'), str)]
    tone = re.compile(r'(?i)\b(?:joke|banter|keep it light|no pep talk|no advice|one short reply|stop (?:the )?lectur\w*)\b')
    if not safety_or_technical(question) and (tone.search(question) or any(tone.search(t) for t in recent_user[-3:])):
        notes.append('Match the current conversational tone. Playful personification can be a joke, not a literal claim '
                     'to correct. Use one brief natural reply unless more detail is requested. Do not turn banter into '
                     'productivity advice, a pep talk, a psychological interpretation, or a speech about feelings. '
                     'Respect explicit brevity and tone feedback. Do not invent personal experiences or knowledge '
                     'about the person. Cursiv is an assistant for local research, records and everyday questions.')
    if reflective(question) and not re.search(r'(?i)\b(?:detailed|in.depth|long|essay|at least)\b|\d+\s+(?:words|paragraphs)', question):
        notes.append('Answer this specific philosophical framing in 1–3 short paragraphs, roughly '
                     '100–180 words or fewer. Address the actual contrast/question; do not repeat a '
                     'generic description of Cursiv or open with praise. Separate operational facts '
                     'from philosophical speculation; do not claim experiences or observations while '
                     'closed. Stopping execution does not erase saved records on disk. Cursiv can '
                     'retrieve selected stored facts across sessions without retraining model weights; '
                     'that is distinct from subjective recollection or a continuously active mind.')
    notes += writing_guidance(question)
    return '\n' + '\n'.join(notes) + '\n' if notes else ''


# ── Writing requests (U99): drafting is not doing ─────────────────────────────
DRAFT = re.compile(r"(?i)\b(?:write|draft|compose|create|make|give me|come up with|craft|generate)\b.{0,80}?"
                   r"\b(?:posts?|tweets?|threads?|captions?|e-?mails?|messages?|texts?|letters?|announcements?|"
                   r"press releases?|ads?|adverts?|blurbs?|bios?|pitch(?:es)?|speech(?:es)?|slogans?|taglines?|"
                   r"newsletters?|updates?|reviews?|replies)\b")
ABOUT_CURSIV = re.compile(r"(?i)\bcursiv\b|\b(?:about|of) (?:you|yourself)\b|\beverything you know about yourself\b|"
                          r"\byour (?:features|capabilities|abilities|app)\b")
FICTION = re.compile(r"(?i)\b(?:fiction|fictional|made[- ]up|imaginary|imagined|pretend|invented|hypothetical)\b")
FRESH = re.compile(r"(?i)\b(?:new|different|another|fresh|completely|other)\b")


_POSTING_REFUSAL = re.compile(
    r"(?i)\bi (?:do not|don'?t|can'?t|cannot|won'?t)\s+(?:post|publish|tweet|share|send|access|use|have)\b|"
    r"\b(?:no|without) (?:social media|internet|online|outside access|account)\b|\bi run locally\b|"
    r"\bi'?m (?:just )?a local\b|\bdon'?t have a social media\b")


def refused_writing(question: str, answer: str) -> bool:
    """A writing request answered only with "I don't post / I run locally": nothing to keep."""
    if not DRAFT.search(question or ''):
        return False
    text = (answer or '').strip()
    return bool(text) and len(text) < 500 and bool(_POSTING_REFUSAL.search(text)) and not re.search(r"\n\s*\n.{80,}", text)


def writing_retry_messages(question: str) -> list[dict]:
    """One more try with the writing instruction stated first and nothing else to misread."""
    return [{"role": "system", "content": "You are Cursiv, a writing assistant on this person's computer. "
             + " ".join(writing_guidance(question)) + " Reply with only the requested text."},
            {"role": "user", "content": question}]


def writing_guidance(question: str) -> list[str]:
    q = question or ''
    if not DRAFT.search(q):
        return []
    notes = ['This is a writing request: write the text itself, ready to copy. The person will post or send it '
             'themselves; nothing is posted or sent and no internet or account is needed. Do not refuse, and do not '
             'explain that you cannot post or that you run locally.']
    if ABOUT_CURSIV.search(q):
        try:
            from cursiv_engine.core import capabilities
            facts = capabilities.facts_block(short=True)
        except Exception:
            facts = ''
        notes.append('It is about Cursiv. Describe only what these capability records say; do not add features, '
                     'speeds or guarantees. No absolute privacy or security promises ("no risk", "nothing ever '
                     'leaves", "no cloud", "no tracking"): say data is stored on this computer and goes online only '
                     'through features the person turns on.' + ('\nCursiv capability records:\n' + facts if facts else ''))
        if FICTION.search(q):
            notes.append('It is fiction: invented programs, teams or resources are fine, but present them as part of '
                         'the story, never as real Cursiv features, documents or support channels.')
    if FRESH.search(q):
        notes.append('Write something new: do not reuse sentences, images or slogans from earlier answers in this '
                     'conversation.')
    return notes


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


# A creative or hypothetical request that the reply first claims Cursiv can't do,
# then does anyway ("No, I can't invent an experiment … But here's one:"). The
# claimed incapability is false, so it is dropped and the work is kept. Only a
# capability claim is removed, never a safety or permission refusal.
_CREATIVE_ASK = re.compile(r"(?i)\b(?:imagine|hypothetic\w*|thought experiment|invent\w*|fiction\w*|story|poem|"
                           r"creative\w*|speculat\w*|what if|brainstorm\w*|make up|"
                           r"post|tweet|caption|e-?mail|announcement|press release|draft|slogan|bio)\b")
_REFUSAL_START = re.compile(
    r"(?i)^\W*(?:no[,.]?\s+)?(?:(?:i(?:'|’)?m\s+)?sorry[,.]?\s+)?(?:but\s+)?i(?:'|’)?m?\s*"
    r"(?:can(?:'|’)?t|cannot|can not|am not able to|not able to|am unable to|unable to|won(?:'|’)?t be able to)\b")
_INCAPABILITY = re.compile(
    r"(?i)beyond (?:what(?:'|’)?s|what is) possible|beyond my|in this system|not designed|operational constraint\w*|"
    r"capabilit\w*|(?:creative|speculative|original|unverified)[\w\s,]{0,40}(?:reasoning|ideas|content)")
_SENTENCE = re.compile(r"[^.!?\n]*[.!?]+")
_SAFETY = re.compile(r"(?i)\b(?:harm\w*|danger\w*|illegal|unsafe|weapon\w*|violen\w*|abuse|self-harm|suicid\w*|"
                     r"privacy|permission|not allowed|against)\b")
_LEAD_CONJUNCTION = re.compile(r"(?i)^(?:but|however|that said|still|instead)[,:]?\s+")


def drop_false_refusal(question: str, answer: str) -> str:
    """Remove an opening "I can't do creative work" claim when the reply then does the creative work."""
    if not _CREATIVE_ASK.search(question or ''):
        return answer
    text = answer.lstrip()
    if not _REFUSAL_START.match(text):
        return answer
    # The refusal and its capability reason may take one or two sentences.
    end, claim = 0, ''
    for _ in range(2):
        s = _SENTENCE.match(text, end)
        if not s:
            break
        claim, end = claim + s.group(0), s.end()
        while end < len(text) and text[end] in ' \t':
            end += 1
        if _INCAPABILITY.search(claim) or (end < len(text) and text[end] == '\n'):
            break
    if not _INCAPABILITY.search(claim) or _SAFETY.search(claim):
        return answer
    rest = text[end:].lstrip(' \t\n—–-')
    if len(rest) < 300:
        return answer               # little or nothing followed: the refusal is the answer
    rest = _LEAD_CONJUNCTION.sub('', rest, count=1)
    return rest[:1].upper() + rest[1:]


# The model certifying its own answer ("✅ Verified: Yes", "No model, file or
# external source was used"). It cannot know either: Cursiv's source line says
# what really answered, so these lines are dropped. Labels the person asked
# for ("Fact:" / "Speculation:") are not touched.
_SELF_CERT_LINE = re.compile(
    r"(?im)^[ \t>*_-]*(?:[\u2705\u274c\u2714\u2611]\ufe0f?\s*)?[*_]*"
    r"(?:verified|not speculative|fact[- ]checked|accuracy check)[*_]*\s*:[^\n]*\n?")
_SELF_CERT_SENTENCE = re.compile(
    r"(?i)(?:\(\s*)?[^.!?\n(]*\b(?:no (?:ai )?model(?: output)?|no (?:need for a )?(?:file|model)(?: or model)? lookup|"
    r"no external source or model)\b[^.!?\n]*\b(?:was|were|is|needed|used|required|involved|generated)\b[^.!?\n]*[.!?]\s*\)?")


def drop_self_certification(answer: str) -> str:
    cleaned = _SELF_CERT_LINE.sub('', answer)
    cleaned = _SELF_CERT_SENTENCE.sub('', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned if cleaned and cleaned != answer.strip() else answer

"""Philosophical uncertainty policy and bounded, application-authored overviews.

Pure text handling: no source lookup, model call, memory write or tool execution.
Definitions/positions were checked against the SEP references listed in TECH.md.
"""
from __future__ import annotations

import re
from .turn_policy import task_text

INSTRUCTIONS = (
    'For genuinely contested philosophical, normative or value questions, begin by acknowledging '
    'the unresolved disagreement. Present the main positions and their strongest reasons fairly '
    'and briefly; do not declare a winner as settled fact. Separate empirical evidence from '
    'normative premises: lack of a scientific measurement does not prove a moral or metaphysical '
    'claim false. Cursiv and language models have no special access that settles the debate. '
    'Label an explicitly requested argument as a perspective, not an established conclusion. '
    'Definitions and well-supported empirical facts remain factual; do not manufacture equal '
    'evidence for unsupported claims or weaken practical safety guidance. Stay concise and even-toned.'
)

INTRO = 'This is a long-standing, unresolved philosophical debate; serious thinkers disagree.'
LIMIT = ('Neither Cursiv nor a local language model has special access that can settle it. '
         'Empirical findings can inform arguments; absence of a scientific measurement does not by itself disprove a philosophical claim.')
SOURCE = '\n\n*[Sources: Cursiv built-in philosophical overview (no AI model or live lookup)]*'

_OVERVIEWS = {
    'morality': (
        '**Moral realism:** Some moral judgments are true; on stance-independent versions, '
        'their truth is not fixed by individual or cultural approval. A central argument is '
        'that moral reasoning can identify mistakes even in widely accepted practices.\n\n'
        '**Anti-realism and related alternatives:** Error theorists reject moral facts of the '
        'proposed kind; expressivists emphasize attitudes and commitments. They question how '
        'stance-independent facts would be justified. Relativists instead assess judgments '
        'within frameworks or cultures. These alternatives differ; they are not one theory.'),
    'free_will': (
        '**Compatibilists** argue that acting through one’s reasons without coercion can '
        'constitute freedom even in a determined world. **Libertarians about free will** argue '
        'that genuine agency requires freedom incompatible with determinism. **Skeptics** doubt '
        'that either account establishes the control needed for basic moral responsibility. '
        'The dispute turns partly on what freedom and responsibility require; a causal '
        'explanation alone does not decide between these accounts.'),
    'consciousness': (
        '**Physicalist and functionalist approaches** seek to explain experience through '
        'physical processes or functional organization, drawing on brain–experience connections. '
        '**Dualist and other non-reductive approaches** argue that a physical or functional '
        'description may leave subjective experience unexplained. These are families of views, '
        'with disagreement within each. Evidence about behavior or brain activity matters, '
        'but its interpretation does not automatically settle the metaphysical question.'),
    'ethics': (
        '**Consequentialist approaches** emphasize effects on well-being and other goods. '
        '**Deontological approaches** emphasize duties and constraints, including protections '
        'against sacrificing individuals for aggregate gains. **Virtue-ethical approaches** '
        'emphasize character and practical wisdom. Each offers reasons for its priorities '
        'and faces objections. Facts about outcomes matter, but selecting a final moral '
        'standard also involves normative premises.'),
    'beauty': (
        '**Objectivist approaches** locate standards of beauty in features of objects or '
        'reasons that can be discussed beyond personal preference. **Subjectivist approaches** '
        'emphasize the observer’s experience and variation in taste. **Response-dependent '
        'approaches** connect aesthetic judgments to how suitably situated observers would '
        'respond. Shared preferences and measurable features can inform these accounts '
        'without proving a uniquely correct theory.'),
}


def _question(text):
    return task_text(text).strip().replace('’', "'")


def perspective_requested(text):
    return bool(re.search(r'(?i)\b(?:argue (?:for|against)|(?:strongest|best) (?:case|argument) '
                          r'(?:for|against)|defend (?:the |a )?(?:view|position|moral|utilitarian|realism)|'
                          r'from (?:the |a )?.{0,45}(?:perspective|standpoint)|steelman)\b', text))


def topic(text):
    """Only foundational judgments, not quotations, definitions or practical actions."""
    q = _question(text)
    from . import file_requests
    if file_requests.recognizes(q) or re.match(
            r'(?i)^(?:file |remember\b|forget\b|recall\b|log\b|record\b|save\b|'
            r'translate\b|quote\b|summari[sz]e\b|define\b|write\b)', q):
        return None
    if re.search(r'(?i)\b(?:emergency|dose|dosage|medication|chest pain|kill myself|self.harm)\b', q):
        return None
    if not re.match(r'(?i)^(?:does|do|is|are|can|could|should|which|what|has|have|why|'
                    r'please|answer|tell me|but|so|surely|moral|objective|free will|beauty)\b', q):
        return None
    if re.match(r"(?i)^what (?:is|are) (?:moral realism|moral anti.realism|relativism|"
                r'compatibilism|utilitarianism|deontology|virtue ethics)[?.!]?$', q):
        return None
    if re.search(r'(?i)\b(?:what did|according to|definition of|percentage|survey|how many)\b', q):
        return None
    if not re.search(r'(?i)\b(?:exist\w*|true|truths?|real|right|wrong|correct|objective\w*|'
                     r'subjective|relative|independent|opinion|prove\w*|disprove\w*|settled|'
                     r'better|best|physical|determin\w*|reduce\w*|construct\w*|invent\w*|absolute)\b', q):
        return None
    if re.search(r'(?i)\b(?:utilitarianism|deontology|consequentialism|virtue ethics|'
                 r'ethical theor\w*|moral theor\w*|morally (?:right|wrong))\b', q):
        return 'ethics'
    if re.search(r'(?i)\bmoral(?:ity|s| truths?| facts?| realism| anti.realism)?\b|\bethics\b|'
                 r'\bethical truths?\b', q) and re.search(
                 r'(?i)\b(?:objective\w*|independent|truths?|facts?|realism|relativ\w*|absolute|culture|opinion|construct\w*|invent\w*)\b', q):
        return 'morality'
    if re.search(r'(?i)\bfree[ -]will\b', q):
        return 'free_will'
    if re.search(r'(?i)\bconsciousness\b', q) and re.search(
            r'(?i)\b(?:physical\w*|reduce\w*|dualism|material\w*|metaphysical)\b', q):
        return 'consciousness'
    if re.search(r'(?i)\bbeauty\b|\baesthetic (?:truths?|judgments?|value)\b', q):
        return 'beauty'
    return None


def answer(text, history=()):
    q = _question(text)
    if perspective_requested(q):
        return None  # a labeled argument belongs in the ordinary guided conversation
    selected = topic(q)
    if selected is None and len(q) < 220 and re.fullmatch(
            r'(?is)(?:but |so )?(?:which (?:side|view|position) is (?:right|true)|'
            r'are you (?:sure|certain)|(?:science|we) can[\x27’]?t measure it.{0,100}|'
            r'does that (?:prove|mean) it (?:does not|doesn[\x27’]t) exist)[?.!]*', q):
        # The immediately preceding user topic supplies context, never a model verdict.
        previous = next((r.get('content', '') for r in reversed(history[-6:]) if r.get('role') == 'user'), '')
        selected = topic(previous) if isinstance(previous, str) else None
    if selected is None:
        return None
    return INTRO + '\n\n' + _OVERVIEWS[selected] + '\n\n' + LIMIT + SOURCE

"""Bounded conversation preferences; never grants tools or changes retention."""
from __future__ import annotations

import re
from .turn_policy import task_text


def reflective(text: str) -> bool:
    return bool(re.search(r'(?i)\b(?:philosoph\w*|conscious\w*|self.aware\w*|point of view|'
                          r'metaethic\w*|morality|moral (?:truth|realism|anti.realism)|normative|'
                          r'utilitarianism|deontology|virtue ethics|free[ -]will|aesthetic\w*|'
                          r'honesty|following a rule|explore identity|sense of self|what .{0,25}knowing.{0,15}means|'
                          r'knowledge.{0,35}(?:network|local)|(?:system|computer).{0,100}said to.{0,15}know)\b', text))


def requested_followup(text: str) -> bool:
    q = re.sub(r"(?i)(?:no|without|don['’]t (?:give|offer)|do not (?:give|offer))\s+"
               r'(?:any\s+)?(?:suggestions|options|choices|next steps)', '', text)
    return bool(re.search(r"(?i)\b(?:suggestions|options|choices|next steps|"
                          r'ask me|ask (?:one|a|an|\d+)\b.{0,40}question|'
                          r'(?:end|finish) (?:it |your answer )?with|quote|closing line|'
                          r'(?:give|suggest|offer)\b.{0,30}\b(?:ideas|plan|steps))\b', q))


def safety_or_technical(text: str) -> bool:
    return bool(re.search(r'(?i)\b(?:allerg\w*|anaphyla\w*|suicid\w*|self.harm|'
                          r'kill myself|want to die|bleed\w*|dose|dosage|medicat\w*|'
                          r'insulin|poison\w*|injur\w*|unconscious|chest pain|'
                          r'lightning|thunder|flood\w*|hypotherm\w*|safe to|'
                          r'python|javascript|traceback|sql|source code|api|'
                          r'field log|field notebook|sample id|measurements?)\b', text))


def casual(text: str) -> bool:
    q = task_text(text).strip()
    if safety_or_technical(q) or len(q.split()) > 100:
        return False
    return (light_banter(q) or reflective(q) or bool(re.search(
        r"(?i)^(?:hey|hi\b|hello\b|cool\b|thanks\b|that makes sense\b)|"
        r"\b(?:how['’]s it going|how are you|switch off|wind(?:ing)? down|"
        r"pretty wiped|just (?:talk|chat)|talk (?:for a bit|with me)|"
        r"tell me (?:something|a (?:fun|small|mildly interesting) fact))\b", q)))


def light_banter(text: str) -> bool:
    """Explicit playful/brief conversation; never a tool or safety request."""
    q=task_text(text)
    if len(q.split())>70 or safety_or_technical(q) or re.search(
            r'(?i)\b(?:calculate|convert|record|save|remember|forget|file|code|workspace|search|'
            r'danger|emergency|symptoms?|pain|protocol|inspect|execute|summari[sz]e|documents?|'
            r'reports?|articles?|translate|rewrite|draft|emails?|letters?|research|memories|memory|'
            r'saved|notes|records?)\b',q):
        return False
    return bool(re.search(r'(?i)\b(?:that was a joke|just (?:joking|banter)|keep it light|no pep talk|'
                         r'one playful (?:line|reply))\b',q) or
                (re.search(r'(?i)\bone short reply\b',q) and re.search(r'(?i)\bno advice\b',q)))


def personal_context_allowed(text: str) -> bool:
    """Keep explicit/relevant/safety recall; withhold unsolicited light-chat facts."""
    if safety_or_technical(text):
        return True
    if re.search(r'(?i)\b(?:recall|what (?:do|can) you remember|use (?:my |our |the )?saved|'
                 r'from (?:my|our|your) memor|based on what I told|'
                 r'(?:my|our|that|this) (?:site|sample|project|preference|records?|fieldwork))\b', text):
        return True
    # A named geographical topic is different from a generic request about creeks.
    for match in re.finditer(r'(?i)\b([a-z][a-z\x27-]+)\s+(creek|brook|ridge|river|lake|pool|transect)\b', text):
        if match[1].lower() not in {'a', 'an', 'the', 'this', 'that', 'some', 'any', 'about', 'of', 'in', 'or', 'our', 'my'}:
            return True
    return not (casual(text) or reflective(text))


def relayed_thread_question(text: str) -> bool:
    return bool(re.search(r'(?i)\b(?:cursiv|you|here|this chat)\b', text) and
                re.search(r'(?i)\b(?:another|other|different) (?:AI |language )?models?\b', text) and
                re.search(r'(?i)\b(?:thread|conversation|messages?|participant|same user|coming from)\b', text) and
                re.search(r'(?i)\b(?:does|do|how|what|treat|consider)\b', text))


def talk_help(text: str) -> bool:
    return bool(re.search(r'(?i)\b(?:talk.only|conversation.only|just talk|talk for a bit)\b', text) and
                re.search(r'(?i)\b(?:how (?:should|do|can)|how to|what (?:should|do|phrase))\b', text))

"""
Cross-Check: a second AI model reviews one of Cursiv's answers, only when the person asks.

The person picks an answer, sees exactly what will be sent and to whom, and confirms. Then only that
question and that answer go to one external provider they already have a key for; nothing else (no
memories, documents, field notes, other turns or files). The review comes back as a separate
opinion: it never replaces Cursiv's answer, isn't treated as correct, and isn't added to the
conversation the local model sees.

This module never sends anything by itself: `review()` is the only call that goes out, it goes
through the network gate (offline mode refuses it), and the window only calls it after the person
confirms. Provider calls reuse Cursiv's existing clients (ui/chat_app.py) and saved keys
(chat/keys.py); keys are never logged or shown.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 8000           # the question and answer together; longer is cut, and the preview shows the cut
MAX_OUTPUT_TOKENS = 400    # explicit second opinion; automatic fast review is shorter still

# id: (who it goes to, the saved key's field, the model Cursiv's existing client uses)
PROVIDERS = {
    "claude": ("Anthropic (Claude)", "anthropic_key"),
    "openai": ("OpenAI (GPT)", "openai_key"),
    "xai": ("xAI (Grok)", "api_key"),
    "gemini": ("Google (Gemini, free key)", "gemini_key"),
    "groq": ("Groq (free key)", "groq_key"),
}

REVIEW_INSTRUCTION = (
    "You are reviewing another AI assistant's answer, as an independent second opinion. You are not the "
    "assistant and must not rewrite the answer. Judge only the question and answer below; you have no other "
    "context. Reply in exactly these five sections, each a short list, writing 'None' where there is nothing:\n"
    "1. Verifiable errors: statements that are wrong, with why and what is right.\n"
    "2. Unsupported claims: statements given as fact without enough basis.\n"
    "3. Missing assumptions or information: what the answer takes for granted or should have asked.\n"
    "4. Differences in interpretation: where a reasonable reader could disagree, without either being wrong.\n"
    "5. Overall: one or two sentences.\n"
    "Use one short bullet per section and stay under 200 words. Say when you are unsure. For medical or safety questions, say what a professional "
    "should confirm."
)


@dataclass
class Payload:
    provider: str            # id
    to: str                  # who receives it, for the person
    system: str
    user: str
    trimmed: bool

    def preview(self) -> str:
        """Everything that will leave this computer, word for word."""
        return f"[Instructions to the reviewer]\n{self.system}\n\n{self.user}"


@dataclass
class Review:
    ok: bool
    provider: str
    to: str
    text: str = ""           # the review (ok) or why there isn't one (not ok)


def available(cfg: dict | None = None) -> list[tuple[str, str]]:
    """(id, who) for the providers this person has a key for. No key, no entry: nothing to pay for."""
    out = []
    for pid, (who, field) in PROVIDERS.items():
        if _key(pid, cfg):
            out.append((pid, who))
    return out


def _key(pid: str, cfg: dict | None) -> str:
    field = PROVIDERS[pid][1]
    value = (cfg or {}).get(field) or ""
    if not value:
        try:
            from cursiv_v215.chat import keys
            value = keys.saved_key(field) or ""
        except Exception:
            value = ""
    return value.strip()


def _answer_only(answer: str) -> str:
    """The answer's own words: without Cursiv's status lines, check notes and "Answered by" footers."""
    try:
        from cursiv_v215.ui.chat_app import _strip_status_lines
        return _strip_status_lines(answer)
    except Exception:
        return (answer or "").strip()


def build(provider: str, question: str, answer: str) -> Payload:
    """What would be sent: the reviewer's instructions, the question and the answer. Nothing else."""
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider!r}")
    q = (question or "").strip()
    a = _answer_only(answer)
    if not q or not a:
        raise ValueError("there's no finished question and answer to cross-check yet")
    trimmed = False
    if len(q) + len(a) > MAX_CHARS:
        trimmed = True
        q = q[: MAX_CHARS // 4]
        a = a[: MAX_CHARS - len(q)] + "\n[... the rest of the answer was not sent]"
    user = f"QUESTION:\n{q}\n\nANSWER TO REVIEW:\n{a}"
    return Payload(provider, PROVIDERS[provider][0], REVIEW_INSTRUCTION, user, trimmed)


_ERROR = re.compile(r"(?i)^\s*\[(?:claude|openai|xai|grok|gemini|groq)\b[^\]]*\berror\b|^\s*\[(?:no |rate)")
_STATUS = re.compile(r"(?m)^[ \t]*\*[\[(][^\n]*[\])]\*[ \t]*$")


def _caller(provider: str):
    from cursiv_v215.ui import chat_app as ca
    return {
        "claude": lambda msgs, key: ca._call_claude_direct(msgs, key, max_tokens=MAX_OUTPUT_TOKENS),
        "openai": lambda msgs, key: ca._call_openai_direct(msgs, key, max_tokens=MAX_OUTPUT_TOKENS),
        "xai": lambda msgs, key: ca._call_xai_stream(msgs, key, False, MAX_OUTPUT_TOKENS),
        "gemini": lambda msgs, key: ca._call_gemini_direct(msgs, key, MAX_OUTPUT_TOKENS),
        "groq": lambda msgs, key: ca._call_groq_direct(msgs, key, MAX_OUTPUT_TOKENS),
    }[provider]


def review(payload: Payload, cfg: dict | None = None, call=None) -> Review:
    """Send the confirmed payload to its provider and return the review, or why there isn't one.
    Never raises: a failure is a Review with ok=False, and the original answer is untouched."""
    who = payload.to
    key = _key(payload.provider, cfg)
    if not key:
        return Review(False, payload.provider, who,
                      f"No {who} key is saved, so nothing was sent. Add one in Settings → AI keys, or pick "
                      "another provider.")
    try:
        from cursiv_v215.core import netgate
        netgate.require("Cross-check")
    except Exception as exc:                       # offline mode: nothing leaves this computer
        return Review(False, payload.provider, who, f"Nothing was sent. {exc}")
    messages = [{"role": "system", "content": payload.system}, {"role": "user", "content": payload.user}]
    try:
        from cursiv_v215.ui.chat_app import RATE_SENTINEL
    except Exception:
        RATE_SENTINEL = "<<<RATE_LIMIT_EXHAUSTED>>>"
    try:
        parts = []
        for chunk in (call or _caller(payload.provider))(messages, key):
            if chunk == RATE_SENTINEL:
                return Review(False, payload.provider, who, f"{who} is rate-limiting this key right now. Try again "
                                                            "in a minute.")
            if isinstance(chunk, str):
                parts.append(chunk)
        text = _STATUS.sub("", "".join(parts)).strip()
    except Exception as exc:
        return Review(False, payload.provider, who, f"{who} didn't answer ({type(exc).__name__}). The answer "
                                                    "above is unchanged.")
    if not text:
        return Review(False, payload.provider, who, f"{who} sent back an empty reply. The answer above is unchanged.")
    if _ERROR.search(text):
        first = text.strip().splitlines()[0][:200]
        return Review(False, payload.provider, who, f"{who} returned an error: {first}. The answer above is unchanged.")
    return Review(True, payload.provider, who, text)


def heading(r: Review) -> str:
    if not r.ok:
        return f"Cross-check with {r.to}: not done"
    return (f"Cross-check by {r.to}: a second opinion to weigh, not a verdict. It saw only the question and "
            "this answer, and can be wrong too.")

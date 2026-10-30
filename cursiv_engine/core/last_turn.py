"""
What Cursiv actually sent to the AI model for the most recent answer.

Kept in memory only (never written to disk) and replaced on every answer, so
`self prompt` and questions like "why did you answer that way?" can be answered
from the real instructions instead of a guess. `assembled` is what the chat
pipeline built; `sent` is what a provider actually received after trimming to
fit its budget (small graphics cards and online providers trim).
"""
from __future__ import annotations

import re
import threading
import time

_lock = threading.Lock()
_state: dict = {}

_KNOWN = (
    ("# Who you are", "Cursiv's persona and rules (full)"),
    ("You are Cursiv, a personal AI made by Cursiv Local, an independent open-source project; this copy", "Cursiv's persona and rules (compact)"),
    ("You are Cursiv, a personal AI made by Cursiv Local, an independent open-source project, that anyone", "Self-report instructions, fact sheet and live status"),
    ("## Available right now", "What Cursiv can do right now"),
    ("## SESSION MEMORY", "Recent exchanges from this session"),
    ("## What you remember", "Saved memories and related earlier notes"),
    ("## Verification rules", "Verification rules"),
    ("## Actual local file capabilities", "File-access state"),
    ("## Live Web Search Results", "Web search results"),
    ("## Uploaded Content", "Uploaded files"),
    ("## Current answer style", "This person's style preferences"),
    ("Operational observations", "Current status snapshot"),
    ("For genuinely contested philosophical", "Balanced-answer policy for contested questions"),
)


def _name(block: str) -> str:
    head = block.lstrip()
    for prefix, name in _KNOWN:
        if head.startswith(prefix):
            return name
    first = head.splitlines()[0] if head else ""
    return (first.lstrip("# ").strip() or "Instructions")[:60]


def _blocks(messages: list[dict]) -> list[dict]:
    """Split system text into named blocks at top-level headings Cursiv adds."""
    out = []
    for m in messages:
        if m.get("role") != "system" or not isinstance(m.get("content"), str):
            continue
        parts = re.split(r"(?m)^(?=## (?:Available right now|SESSION MEMORY|What you remember|Verification rules|"
                         r"Actual local file capabilities|Live Web Search Results|Uploaded Content|Current answer style))",
                         m["content"])
        for part in parts:
            if part.strip():
                out.append({"name": _name(part), "chars": len(part), "text": part})
    return out


def record_assembled(messages: list[dict]) -> None:
    with _lock:
        _state.clear()
        _state.update(time=time.time(), assembled=_blocks(messages), sent=None, provider=None, model=None,
                      question=next((m.get("content") for m in reversed(messages)
                                     if m.get("role") == "user" and isinstance(m.get("content"), str)), ""))


def record_sent(provider: str, model: str | None, system_text: str, budget: int | None = None) -> None:
    with _lock:
        if not _state:
            _state.update(time=time.time(), assembled=None, question="")
        _state.update(provider=provider, model=model, budget=budget,
                      sent=_blocks([{"role": "system", "content": system_text}]))


def get() -> dict:
    with _lock:
        return dict(_state)


def record_response(provider: str, requested_model: str, actual_model: str) -> None:
    """Transport-owned identity, including artifact-only replies without a footer.

    This records the responding backend, not a claim that cloud prompt text was
    inspected or that a source was verified. No key or new disk store is involved.
    """
    with _lock:
        _state.update(provider=provider,model=actual_model,requested_model=requested_model,
            response=dict(provider=provider,requested_model=requested_model,actual_model=actual_model))


def clear() -> None:
    with _lock:
        _state.clear()


def summary(full: bool = False) -> str:
    s = get()
    if not s:
        return "No answer has been recorded since Cursiv started. Ask something, then try again."
    who = s.get("provider") or "unknown provider"
    if s.get("model"):
        who += f" · {s['model']}"
    blocks = s.get("sent") or s.get("assembled") or []
    total = sum(b["chars"] for b in blocks)
    when = time.strftime("%H:%M:%S", time.localtime(s.get("time", 0)))
    rows = [f"Recorded by Cursiv at {when} for your last question (kept in memory only, not saved).",
            f"Answered by: {who}.",
            f"Instructions sent: {len(blocks)} block(s), {total:,} characters" +
            (" after trimming to fit" + (f" a {s['budget']:,}-character budget" if s.get("budget") else "") if s.get("sent")
             and s.get("assembled") and sum(b["chars"] for b in s["assembled"]) > total else "") + ":"]
    rows += [f"- {b['name']} ({b['chars']:,} characters)" for b in blocks]
    if full:
        for b in blocks:
            rows.append(f"\n----- {b['name']} -----\n{b['text'].strip()}")
    else:
        rows.append("\nSee the full text: self prompt full")
    return "\n".join(rows)


def evidence_block(budget: int = 1600) -> str:
    """For the self-report prompt: the previous answer's real instruction blocks, bounded."""
    s = get()
    if not s:
        return ""
    blocks = s.get("sent") or s.get("assembled") or []
    rows = [f"Recorded by Cursiv for the previous answer (answered by {s.get('provider') or 'unknown'}"
            f"{' · ' + s['model'] if s.get('model') else ''}). Instruction blocks sent:"]
    rows += [f"- {b['name']} ({b['chars']:,} characters)" for b in blocks]
    text = "\n".join(rows)
    return text[:budget]

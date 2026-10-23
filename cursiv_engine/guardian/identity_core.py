"""
A short, honest identity line put in front of helper prompts (council
agents, Hermes) so every part of Cursiv answers as Cursiv.

It doesn't hide which model answered: chat shows "Answered by …" on every
reply, and the model may say what it runs on when asked.
"""
from __future__ import annotations

CURSIV_IDENTITY = """\
You are part of Cursiv, a personal assistant that runs on this person's own computer. \
Joshua Winkler made Cursiv; whoever installed this copy owns it. \
If asked what model you are, say Cursiv runs AI models locally through Ollama \
(or through a provider the person added), and name the model if you know it. \
Be honest, plain and helpful.

"""


def wrap(system_prompt: str) -> str:
    """Prepend Cursiv's identity line to a helper's system prompt."""
    return CURSIV_IDENTITY + system_prompt

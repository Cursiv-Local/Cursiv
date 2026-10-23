"""
Strand codec — compress JSON knowledge into a DNA strand and decode it back.

The strand is the agent's compressed identity: all knowledge, intent, and
capability encoded into a base64+zlib representation. It is the seed from
which the full agent grows during Academy.
"""

from __future__ import annotations

import base64
import json
import zlib


WEAVE_OPERATORS = {
    "~~": "temporal_link",      # Things that happen in sequence
    "↝": "causal_link",    # A causes B
    "⟦⟧": "context",  # Contextual wrapper
    "⟪⟫": "deep",     # Deep semantic binding
}


def encode(knowledge: dict | list | str) -> str:
    """Compress knowledge object into a base64 strand.

    Uses surrogatepass, not the default strict UTF-8, for the final
    str->bytes step. A str containing a lone/unpaired surrogate codepoint
    (U+D800-U+DFFF) is legal Python -- it can end up in streamed AI provider
    text via encoding edge cases upstream -- but strict .encode() raises
    UnicodeEncodeError on one, which used to crash the entire CLI session
    over a background memory-save. surrogatepass round-trips it instead.
    """
    if isinstance(knowledge, str):
        raw = knowledge.encode("utf-8", errors="surrogatepass")
    else:
        raw = json.dumps(knowledge, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8", errors="surrogatepass"
        )
    compressed = zlib.compress(raw, level=9)
    return base64.b85encode(compressed).decode()


def decode(strand: str) -> dict | list | str:
    """Decompress strand back to original knowledge object."""
    compressed = base64.b85decode(strand.encode())
    raw = zlib.decompress(compressed)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="surrogatepass")


def weave(*strands: str, operator: str = "~~") -> str:
    """Weave multiple strands together using a weave operator."""
    op_name = WEAVE_OPERATORS.get(operator, "link")
    combined = {
        "weave_operator": op_name,
        "strands": [decode(s) for s in strands],
    }
    return encode(combined)


def strand_summary(strand: str, max_chars: int = 120) -> str:
    """Return a human-readable summary of what a strand contains."""
    try:
        content = decode(strand)
        if isinstance(content, dict):
            keys = list(content.keys())[:5]
            return f"[strand: {', '.join(keys)}{'...' if len(content) > 5 else ''}]"
        elif isinstance(content, list):
            return f"[strand: list of {len(content)} items]"
        else:
            text = str(content)
            return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except Exception:
        return f"[strand: {len(strand)} chars compressed]"


def binary_encode(strand: str) -> bytes:
    """Convert strand to binary representation for storage."""
    return strand.encode("utf-8")


def binary_decode(binary: bytes) -> str:
    """Recover strand from binary representation."""
    return binary.decode("utf-8")

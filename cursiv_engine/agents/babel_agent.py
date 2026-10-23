"""
Babel Agent — Universal language translator.

Encodes any language to UTF-8 binary, decodes and translates to English.
No language needs to be pre-programmed: Python's UTF-8 handles every Unicode
script natively, and the LLM already knows all of them.

Supported automatically: English, Spanish, French, German, Mandarin, Japanese,
Korean, Arabic, Russian, Hindi, Hebrew, Greek, Thai, Vietnamese, and every
other UTF-8 script — same code, zero configuration.
"""

from __future__ import annotations

# Sent to the LLM with the already-decoded text.
# Python handles the binary → Unicode decode (always perfect, even for 3-byte
# scripts like Japanese/Chinese/Arabic). The LLM only needs to detect + translate.
BABEL_SYSTEM = """You are the Babel Agent — a universal language detector and translator.

You will receive text that has already been decoded from binary. It may be in any language.
Your job:
1. Identify the source language
2. Translate the full content to clear, natural English
3. Add a brief cultural or contextual note only if it genuinely helps understanding

Reply in EXACTLY this format — no extra headers, no markdown, nothing before or after:
Detected language: [language name]
English translation: [translation]
Context: [one sentence if useful, otherwise leave blank]"""


def encode_to_binary(text: str) -> str:
    """
    Encode any text (any language / script) to space-separated UTF-8 binary bytes.
    Example: "こんにちは" → "11100011 10000001 10111011 ..."
    Works for every Unicode language without any per-language configuration.
    """
    return " ".join(f"{b:08b}" for b in text.encode("utf-8"))


def decode_from_binary(binary: str) -> str:
    """Decode space-separated UTF-8 binary bytes back to Unicode text."""
    try:
        bits = binary.strip().split()
        byte_vals = bytes(int(b, 2) for b in bits if len(b) == 8)
        return byte_vals.decode("utf-8")
    except Exception as exc:
        return f"[decode error: {exc}]"


def is_babel_command(text: str) -> bool:
    lower = text.lower().strip()
    return lower.startswith("babel ") or lower.startswith("babel:")


def extract_babel_input(text: str) -> str:
    lower = text.lower().strip()
    for prefix in ("babel:", "babel "):
        if lower.startswith(prefix):
            return text[len(prefix):].strip()
    return text.strip()


def is_rtl_script(text: str) -> bool:
    """Detect Arabic, Hebrew, Persian, or other RTL scripts."""
    for ch in text:
        cp = ord(ch)
        if 0x0590 <= cp <= 0x05FF: return True  # Hebrew
        if 0x0600 <= cp <= 0x06FF: return True  # Arabic / Persian
        if 0xFB50 <= cp <= 0xFDFF: return True  # Arabic extended-A
        if 0xFE70 <= cp <= 0xFEFF: return True  # Arabic presentation forms-B
    return False


def detect_script(text: str) -> str:
    """Return a human-readable script name for display labeling."""
    for ch in text:
        cp = ord(ch)
        if 0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            return "Arabic / Persian"
        if 0x0590 <= cp <= 0x05FF:
            return "Hebrew"
        if 0x0900 <= cp <= 0x097F:
            return "Devanagari"
        if 0x0E00 <= cp <= 0x0E7F:
            return "Thai"
        if 0x4E00 <= cp <= 0x9FFF or 0x3040 <= cp <= 0x30FF:
            return "CJK"
        if 0x0400 <= cp <= 0x04FF:
            return "Cyrillic"
    return "Latin / unknown"


def reorder_rtl_for_display(text: str) -> str:
    """
    Reorder RTL text for visual display on LTR terminals.
    Reverses word order so the sentence reads left-to-right visually —
    each word's internal characters stay in correct Unicode order.
    Example: Arabic "word1 word2 word3" → displays as "word3 word2 word1"
    which reads correctly on a left-to-right console.
    """
    lines = text.splitlines()
    reordered = []
    for line in lines:
        words = line.split()
        reordered.append(" ".join(reversed(words)))
    return "\n".join(reordered)


def format_binary_block(binary: str, chars_per_line: int = 72) -> str:
    """Wrap long binary string for readable terminal display."""
    words = binary.split()
    lines, current = [], []
    length = 0
    for w in words:
        if length + len(w) + 1 > chars_per_line and current:
            lines.append(" ".join(current))
            current, length = [], 0
        current.append(w)
        length += len(w) + 1
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)

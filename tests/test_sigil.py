"""Zero-width text helpers in cursiv_engine/core/sigil.py.

Run:  python -m pytest tests/   (or just: python tests/test_sigil.py)
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cursiv_engine.core import sigil  # noqa: E402


def test_round_trip_message_that_contains_the_sentinel():
    # "s" (0x73 -> 01 11 00 11) encodes to a run containing the sentinel
    # (11 00 11); the old decoder stopped there and returned "".
    assert sigil.extract_zwc(sigil.embed_zwc("Dear Eli", "secret")) == "secret"


def test_round_trip_random_messages():
    rng = random.Random(1234)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/=:-_ é∇Ωλ"
    for _ in range(500):
        msg = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 80)))
        host = rng.choice(["", "x", "for: eli", "for: someone with a long name"])
        assert sigil.extract_zwc(sigil.embed_zwc(host, msg)) == msg, (host, msg)


def test_every_single_byte():
    for b in range(256):
        msg = bytes([b]).decode("latin-1")
        assert sigil.extract_zwc(sigil.embed_zwc("for: x", msg)) == msg


def test_host_text_is_unchanged_when_zero_width_chars_are_removed():
    host = "for: eli"
    out = sigil.embed_zwc(host, "tag123")
    assert "".join(c for c in out if c not in sigil._ZSET) == host


def test_text_after_the_hidden_message_is_ignored():
    hidden = sigil.embed_zwc("for: eli", "tag") + " and more text"
    assert sigil.extract_zwc(hidden) == "tag"


def test_empty_and_missing():
    assert sigil.extract_zwc(sigil.embed_zwc("host", "")) == ""
    assert sigil.extract_zwc("plain text, nothing hidden") == ""
    assert sigil.extract_zwc("") == ""


def test_encoding_format_unchanged():
    # Same bytes as before the fix, so existing .seal files still decode.
    expected = sigil._SENTINEL + "".join(
        sigil._Z[(byte >> shift) & 0x3] for byte in "ab".encode() for shift in (6, 4, 2, 0)
    ) + sigil._SENTINEL
    assert sigil._zwc_encode("ab") == expected


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)} tests passed")

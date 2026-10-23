"""
Cursiv — Family Profiles.

The letters are sealed: they ship only in encrypted form (sealed_letters.json,
see family_seal.py) and open only with the member's name + birth date. The
readable source lives on the owner's machine in private/family_source.json
(git-ignored); re-seal with scripts/seal_family_letters.py after editing it.

Activation: type  babel I am [Full Name] born [Date of Birth], [PIN]
            inside a running Cursiv session.
            The birth date + PIN is the key.
            First activation sets the PIN. Forgotten PIN → ask Joshua to reset it.

Created: May 20, 2026 · 4:30 A.M. · Fruitland Park, Florida
Author:  Joshua Winkler
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from pathlib import Path

from cursiv_engine.family.date_matcher import normalize_dob
from cursiv_engine.family import family_seal as _seal

# ── PIN storage ───────────────────────────────────────────────────────────────
# Each family member's PIN is stored as sha256(pin) in .cursiv/family/<key>.pin
# The plain PIN is never written anywhere.

_PIN_DIR = Path.home() / ".cursiv" / "family"
# See cursiv_engine/guardian/access_gate.py for why this is Path.home() and not
# __file__-relative — same bug, same fix: under the frozen build this used to
# resolve inside the install directory, and PIN verification fails silently
# by design (indistinguishable from "no match", for security), so a PIN file
# that went missing or became unreadable looked exactly like "babel stopped
# working" with no error at all.

# Characters available for PIN construction — shown to the user during setup.
PIN_CHARS   = "! @ # $ % ^ & * ~ - + = ? /"
_PIN_VALID  = set("!@#$%^&*~-+=?/")


def pin_is_set(member_key: str) -> bool:
    return (_PIN_DIR / f"{member_key}.pin").exists()


def is_valid_pin(pin: str) -> bool:
    """PIN must be 2–8 characters drawn entirely from PIN_CHARS."""
    s = pin.strip()
    return 2 <= len(s) <= 8 and all(c in _PIN_VALID for c in s)


def set_pin(member_key: str, pin: str) -> None:
    _PIN_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(pin.strip().encode()).hexdigest()
    (_PIN_DIR / f"{member_key}.pin").write_text(h, encoding="utf-8")


def verify_pin(member_key: str, pin: str) -> bool:
    p = _PIN_DIR / f"{member_key}.pin"
    if not p.exists():
        return False
    stored = p.read_text(encoding="utf-8").strip()
    h = hashlib.sha256(pin.strip().encode()).hexdigest()
    return hmac.compare_digest(stored, h)


def reset_pin(member_key: str) -> None:
    p = _PIN_DIR / f"{member_key}.pin"
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass

# ── Sealed letters ────────────────────────────────────────────────────────────
# Members unlocked this session: key -> decrypted payload (member, header, template).
# Nothing personal is readable until detect_family_member() succeeds.
_UNLOCKED: dict[str, dict] = {}
_SEALED: dict | None = None


def _sealed() -> dict:
    global _SEALED
    if _SEALED is None:
        try:
            _SEALED = json.loads(_seal.SEALED_FILE.read_text(encoding="utf-8"))
        except Exception:
            _SEALED = {"salt": "", "entries": {}}
    return _SEALED


def _profile_of(payload: dict) -> dict:
    m = payload["member"]
    year, month, day = (int(x) for x in m["dob"].split("-"))
    return {"key": m["key"], "display": m["display"], "relation": m.get("relation", ""),
            "dob_month": month, "dob_day": day, "dob_year": year}


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_family_member(full_name: str, dob_text: str) -> dict | None:
    """
    Given a full name and a freeform date-of-birth string, return the family
    member profile dict if the combination opens one of the sealed letters.

    Each typed name word is tried with the birth date; the first one that
    opens a sealed entry wins, and every typed word must belong to that
    member's name (same rule as before sealing). Returns None if no match.
    """
    dob_iso = normalize_dob(dob_text)
    if not dob_iso:
        return None
    sealed = _sealed()
    if not sealed.get("entries"):
        return None
    salt = base64.b64decode(sealed["salt"])
    typed = _seal.name_tokens(full_name)
    for token in dict.fromkeys(typed):
        enc_key, mac_key, verifier = _seal.derive(token, dob_iso, salt)
        entry = sealed["entries"].get(verifier)
        if entry is None:
            continue
        payload = _seal.open_sealed(entry, enc_key, mac_key)
        if payload is None:
            continue
        if not set(typed).issubset(payload.get("allowed_tokens", [])):
            return None
        _UNLOCKED[payload["member"]["key"]] = payload
        return _profile_of(payload)
    return None


def get_letter(member_key: str) -> str:
    """The member's letter -- only after detect_family_member() unlocked it."""
    return _UNLOCKED.get(member_key, {}).get("member", {}).get("letter", "")


def build_system_prompt(profile: dict) -> str:
    payload = _UNLOCKED.get(profile["key"])
    if not payload:
        return ""
    m = payload["member"]
    display = profile["display"]
    return payload["system_template"].format(
        jw_header          = payload["jw_header"],
        letter             = m["letter"],
        display_name       = display,
        display_name_upper = display.upper(),
        member_context     = m.get("context", ""),
    )


def get_jw_header() -> str:
    """The transmission header -- available once any member is unlocked."""
    for payload in _UNLOCKED.values():
        return payload["jw_header"]
    return ""


def parse_iam_command(text: str) -> tuple[str, str, str | None] | None:
    """
    Parse family activation from a babel input string.

    Accepted formats:
      i am [Full Name] born [Date][, PIN]
      i am [Full Name], [Date][, PIN]      ← comma separator, no 'born' required

    Returns (full_name, date_text, pin_or_None) or None if no match.
    """
    t = text.strip()

    # Pattern 1: "i am [name] born [date]"
    m = re.match(r"^i\s+am\s+(.+?)\s+born\s+(.+)$", t, re.IGNORECASE)
    if m:
        name_part = m.group(1).strip().rstrip(",. ")
        rest      = m.group(2).strip()
    else:
        # Pattern 2: "i am [name], [date]" — lazy match stops at first comma
        m2 = re.match(r"^i\s+am\s+(.+?),\s+(.+)$", t, re.IGNORECASE)
        if not m2:
            return None
        name_part = m2.group(1).strip().rstrip(",. ")
        rest      = m2.group(2).strip()

    pin = None

    # Try to split off a trailing comma-separated PIN (special chars, 2–8 chars)
    _pin_chars_re = r"[!@#$%^&*~\-+=?/]{2,8}"
    pin_m = re.search(rf",\s*({_pin_chars_re})\s*$", rest)
    if pin_m:
        potential_pin  = pin_m.group(1)
        potential_date = rest[:pin_m.start()].strip()
        # Only accept as PIN if the remaining date still parses completely
        if normalize_dob(potential_date) is not None:
            pin  = potential_pin
            rest = potential_date

    return name_part, rest, pin

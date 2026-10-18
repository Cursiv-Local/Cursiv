"""
Saved AI keys, encrypted for the account that saved them.

On macOS each key goes into the user's login Keychain (service "Cursiv"), and
config.json keeps only "keychain:<id>". The key reaches Apple's `security` tool on
its standard input, never on its command line.

Keys live in .cursiv/config.json. On Windows each key is stored as
"dpapi:<base64>", encrypted with DPAPI (CryptProtectData): only the same
Windows user on the same computer can read it back. Someone who copies the
file, or another Windows account on the PC, gets nothing usable.

Plain keys from older versions still work; migrate() encrypts them in place.

A USB copy runs on other computers, so DPAPI can't be used there: in portable
mode keys stay readable, and the USB maker writes them out readable on a
private copy (it warns that the drive holds your keys).
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

SECRET_FIELDS = ("api_key", "openai_key", "anthropic_key", "gemini_key", "groq_key", "cf_api_token")
PREFIX = "dpapi:"
KC_PREFIX = "keychain:"
KC_SERVICE = "Cursiv"
_ENTROPY = b"Cursiv saved key"


def _dpapi_available() -> bool:
    return sys.platform == "win32" and os.environ.get("CURSIV_PORTABLE") != "1"


def _keychain_available() -> bool:
    import shutil
    return sys.platform == "darwin" and os.environ.get("CURSIV_PORTABLE") != "1" and bool(shutil.which("security"))


def _keychain_put(secret: str) -> str | None:
    """Store a secret in the login Keychain; its id, or None."""
    import subprocess
    import uuid
    if any(c in secret for c in "\"\\\n\r"):
        return None                       # keep the stdin command unambiguous
    item = uuid.uuid4().hex
    cmd = f'add-generic-password -U -s {KC_SERVICE} -a {item} -w "{secret}"\n'
    try:
        rc = subprocess.run(["security", "-i"], input=cmd, capture_output=True, text=True, timeout=15).returncode
    except Exception:
        return None
    return item if rc == 0 else None


def _keychain_get(item: str) -> str:
    import subprocess
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", KC_SERVICE, "-a", item, "-w"],
                           capture_output=True, text=True, timeout=15)
    except Exception:
        return ""
    return r.stdout.rstrip("\n") if r.returncode == 0 else ""


def _blob(data: bytes):
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf, DATA_BLOB


def _crypt(data: bytes, protect: bool) -> bytes:
    import ctypes
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    inp, _keep, DATA_BLOB = _blob(data)
    ent, _keep2, _ = _blob(_ENTROPY)
    out = DATA_BLOB()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    # flags 0x1 = CRYPTPROTECT_UI_FORBIDDEN: never show a prompt
    if not fn(ctypes.byref(inp), None, ctypes.byref(ent), None, None, 0x1, ctypes.byref(out)):
        raise OSError(ctypes.get_last_error() or "DPAPI call failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def protect(value: str) -> str:
    """The stored form of a key. Unchanged when empty, already protected, or
    when DPAPI isn't available (USB copy, not Windows)."""
    if not value or value.startswith((PREFIX, KC_PREFIX)):
        return value
    if _keychain_available():
        item = _keychain_put(value)
        return KC_PREFIX + item if item else value
    if not _dpapi_available():
        return value
    try:
        return PREFIX + base64.b64encode(_crypt(value.encode("utf-8"), True)).decode("ascii")
    except Exception:
        return value


def reveal(value: str) -> str:
    """The usable key. "" if it was encrypted for another Windows account or PC."""
    if isinstance(value, str) and value.startswith(KC_PREFIX):
        return _keychain_get(value[len(KC_PREFIX):]) if sys.platform == "darwin" else ""
    if not isinstance(value, str) or not value.startswith(PREFIX):
        return value if isinstance(value, str) else ""
    if sys.platform != "win32":
        return ""
    try:
        return _crypt(base64.b64decode(value[len(PREFIX):]), False).decode("utf-8")
    except Exception:
        return ""


def reveal_all(data: dict) -> dict:
    """A copy of config data with every saved key readable."""
    return {k: (reveal(v) if k in SECRET_FIELDS else v) for k, v in data.items()}


def _rewrite(path: Path, fn) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    new = {k: (fn(v) if k in SECRET_FIELDS and isinstance(v, str) else v) for k, v in data.items()}
    if new == data:
        return False
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(new, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return True


def migrate(path: Path) -> bool:
    """Encrypt any plain keys in config.json. True if the file changed."""
    if not (_dpapi_available() or _keychain_available()):
        return False
    return _rewrite(path, protect)


def export_readable(path: Path) -> bool:
    """Decrypt the keys in a copied config.json (for a private USB copy)."""
    return _rewrite(path, reveal)

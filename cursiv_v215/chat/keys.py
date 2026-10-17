"""
Saved AI keys in .cursiv/config.json, next to the settings in core/netgate.py.

Secret fields are stored encrypted for this Windows account (core/keystore.py);
keys saved by older versions are encrypted the first time this module loads.
The probe_* functions check a paid key by listing the provider's models, which
costs nothing.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from cursiv_v215.core import keystore

KEYS_FILE = Path(__file__).resolve().parent.parent.parent / ".cursiv" / "config.json"


def saved_key(field: str) -> str:
    """A saved key, decrypted. "" if missing or saved for another account."""
    try:
        return keystore.reveal(json.loads(KEYS_FILE.read_text(encoding="utf-8")).get(field, "") or "")
    except Exception:
        return ""


def store_key(field: str, value: str) -> None:
    """Save a key (encrypted) or other setting; an empty value removes it."""
    try:
        try:
            data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if value:
            data[field] = keystore.protect(value) if field in keystore.SECRET_FIELDS else value
        else:
            data.pop(field, None)
        KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEYS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _lists_models(url: str, headers: dict) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Cursiv-Desktop/3.14", **headers})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def probe_xai(key: str) -> bool:
    return _lists_models("https://api.x.ai/v1/models", {"Authorization": f"Bearer {key}"})


def probe_openai(key: str) -> bool:
    return _lists_models("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})


def probe_claude(key: str) -> bool:
    return _lists_models("https://api.anthropic.com/v1/models",
                         {"x-api-key": key, "anthropic-version": "2023-06-01"})


try:
    keystore.migrate(KEYS_FILE)
except Exception:
    pass

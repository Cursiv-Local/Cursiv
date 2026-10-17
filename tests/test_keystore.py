"""Saved keys are encrypted for this Windows account (DPAPI)."""
import json
import sys

import pytest

from cursiv_v215.core import keystore

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")

KEY = "gsk_" + "k" * 40


@pytest.fixture
def keys_file(tmp_path, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    path = tmp_path / ".cursiv" / "config.json"
    monkeypatch.setattr(ca, "_KEYS_FILE_APP", path)
    monkeypatch.delenv("CURSIV_PORTABLE", raising=False)
    return path


def test_round_trip_and_foreign_blob():
    stored = keystore.protect(KEY)
    assert stored.startswith("dpapi:") and KEY not in stored
    assert keystore.reveal(stored) == KEY
    assert keystore.reveal("dpapi:AAAA") == ""          # another account's key: unusable, not garbage
    assert keystore.reveal(KEY) == KEY                   # plain keys from older versions still work


def test_saved_keys_are_not_plain_on_disk(keys_file):
    from cursiv_v215.ui import chat_app as ca
    ca._store_key("groq_key", KEY)
    assert KEY not in keys_file.read_text(encoding="utf-8")
    assert ca._saved_key("groq_key") == KEY


def test_other_settings_stay_readable(keys_file):
    from cursiv_v215.ui import chat_app as ca
    ca._store_key("cf_account_id", "abc123")
    assert json.loads(keys_file.read_text(encoding="utf-8"))["cf_account_id"] == "abc123"


def test_migrate_encrypts_old_plain_keys(keys_file):
    keys_file.parent.mkdir(parents=True)
    keys_file.write_text(json.dumps({"gemini_key": KEY, "offline_mode": True}), encoding="utf-8")
    assert keystore.migrate(keys_file) is True
    data = json.loads(keys_file.read_text(encoding="utf-8"))
    assert data["gemini_key"].startswith("dpapi:") and data["offline_mode"] is True
    assert keystore.migrate(keys_file) is False          # already done


def test_usb_copy_keeps_keys_plain(keys_file, monkeypatch):
    monkeypatch.setenv("CURSIV_PORTABLE", "1")
    assert keystore.protect(KEY) == KEY
    keys_file.parent.mkdir(parents=True)
    monkeypatch.delenv("CURSIV_PORTABLE")
    keys_file.write_text(json.dumps({"groq_key": keystore.protect(KEY)}), encoding="utf-8")
    assert keystore.export_readable(keys_file) is True
    assert json.loads(keys_file.read_text(encoding="utf-8"))["groq_key"] == KEY


def test_settings_window_and_chat_panel_see_readable_keys(keys_file, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    import settings_dialog
    ca._store_key("openai_key", KEY)
    assert settings_dialog.load_keys()["openai_key"] == KEY
    import chat_panel
    monkeypatch.setattr(chat_panel, "_CHAT_ROOT", keys_file.parent.parent)
    assert chat_panel._load_saved_keys()["openai_key"] == KEY

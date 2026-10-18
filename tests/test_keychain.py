"""Saved AI keys on macOS go into the login Keychain (core/keystore.py)."""
import subprocess
import sys

import pytest

from cursiv_v215.core import keystore as ks


def test_keychain_stores_by_reference_and_keeps_the_key_off_the_command_line(monkeypatch):
    calls, vault = [], {}

    def fake_run(args, input=None, **kw):
        calls.append((args, input))
        if args[:2] == ["security", "-i"]:
            item = input.split(" -a ")[1].split()[0]
            vault[item] = input.split(' -w "')[1].split('"')[0]
            return subprocess.CompletedProcess(args, 0, "", "")
        item = args[args.index("-a") + 1]
        return subprocess.CompletedProcess(args, 0 if item in vault else 44, vault.get(item, "") + "\n", "")

    monkeypatch.setattr(ks, "_keychain_available", lambda: True)
    monkeypatch.setattr(ks.sys, "platform", "darwin")
    monkeypatch.setattr(subprocess, "run", fake_run)
    stored = ks.protect("gsk_" + "x" * 30)
    assert stored.startswith("keychain:") and "gsk_" not in stored
    assert all("gsk_" not in " ".join(a) for a, _ in calls)          # never in argv
    assert ks.reveal(stored) == "gsk_" + "x" * 30
    assert ks.protect(stored) == stored                               # already stored
    assert ks.reveal("keychain:missing") == ""


@pytest.mark.skipif(sys.platform != "darwin", reason="needs a Mac's Keychain")
def test_real_keychain_round_trip():
    stored = ks.protect("test-key-" + "z" * 20)
    if not stored.startswith("keychain:"):
        pytest.skip("this Mac's login Keychain isn't writable here")
    try:
        assert ks.reveal(stored) == "test-key-" + "z" * 20
    finally:
        subprocess.run(["security", "delete-generic-password", "-s", ks.KC_SERVICE, "-a", stored.split(":", 1)[1]],
                       capture_output=True)

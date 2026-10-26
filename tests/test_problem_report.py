"""U103: the problem report is the one feature that sends logs off the computer. It had no tests.

What it may send: version, system info, the tails of Cursiv's own log files and the error on screen,
scrubbed, after the person has seen the preview. What it must never send: keys, tokens, passwords,
email addresses, the Windows user name, chats or memories -- and nothing at all in offline mode."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "launcher"))

import problem_report as pr  # noqa: E402

SECRETS = {
    "anthropic": "sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
    "openai": "sk-proj-abcdefghijklmnopqrst",
    "xai": "xai-abcdefghijklmnopqrstuv",
    "gemini": "AIzaSyA1234567890abcdefghijklmnopq",
    "groq": "gsk_abcdefghijklmnop1234",
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk",
    "bearer": "Bearer abcdef1234567890",
    "password": "password=hunter2-correct-horse",
}


def test_scrub_removes_every_kind_of_secret_and_the_user(monkeypatch):
    monkeypatch.setenv("USERNAME", "joanna")
    text = "\n".join(SECRETS.values()) + "\nmail me at joanna@example.org\nC:\\Users\\Joanna\\AppData\\x.log"
    out = pr.scrub(text)
    for name, secret in SECRETS.items():
        assert secret.split()[-1].split("=")[-1] not in out, name
    assert "@example.org" not in out and "joanna" not in out.lower() and "<user>" in out


def test_a_report_holds_only_logs_and_never_chats_or_memories(tmp_path, monkeypatch):
    home = tmp_path / ".cursiv"
    (home / "logs").mkdir(parents=True)
    (home / "logs" / "chat.log").write_text("ERROR: provider failed with key " + SECRETS["openai"] + "\n", encoding="utf-8")
    (home / "crash.log").write_text("Traceback ... ValueError\n", encoding="utf-8")
    (home / "conversations").mkdir()
    (home / "conversations" / "c1.json").write_text('{"text": "my private site is Beaver Pond"}', encoding="utf-8")
    (home / "memory_facts.jsonl").write_text('{"text": "Sam has asthma"}\n', encoding="utf-8")
    monkeypatch.setattr(pr, "HOME_DATA", home)
    report = pr.collect("The AI engine didn't start")
    assert "provider failed" in report["logs"] and "ValueError" in report["logs"]
    assert SECRETS["openai"] not in report["logs"]
    assert "Beaver Pond" not in report["logs"] and "asthma" not in report["logs"]      # contents never read
    assert "The AI engine didn't start" in report["logs"]


def test_nothing_is_sent_in_offline_mode(monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate, "is_offline", lambda: True)
    monkeypatch.setattr(pr, "REPORT_URL", "https://cursiv.us/api/report")
    # The socket-level backstop refuses the connection itself; urllib reports it as a URLError.
    with pytest.raises(pr.urllib.error.URLError) as caught:
        pr.send({"logs": "x", "version": "t", "os": "t", "install_id": ""}, "note")
    assert isinstance(caught.value.reason, netgate.NetworkBlocked) and "Blocked a connection to cursiv.us" in str(caught.value)


def test_the_note_is_scrubbed_before_it_is_sent(monkeypatch):
    sent = {}

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"id": "ABCD-1234"}'

    def fake_open(req, timeout):
        sent["body"] = json.loads(req.data.decode("utf-8"))
        return Reply()
    monkeypatch.setattr(pr.urllib.request, "urlopen", fake_open)
    assert pr.send({"logs": "x", "version": "t", "os": "t", "install_id": ""},
                   "It broke after I pasted " + SECRETS["anthropic"]) == "ABCD-1234"
    assert SECRETS["anthropic"] not in sent["body"]["note"] and "[removed]" in sent["body"]["note"]

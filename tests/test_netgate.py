"""The network gate (AUDIT-2026-10-17 C-009, C-010, C-011). No network: every
non-loopback connection or DNS lookup is recorded and refused by an audit hook."""
import json
import socket
import sys
import threading

import pytest

from cursiv_v215.core import netgate


# ── Harness: record every connection off this computer, and refuse it ───────

_recording: list | None = None


def _recorder(event, args):
    if _recording is None or not event.startswith("socket."):
        return
    if event in ("socket.connect", "socket.sendto"):
        host = args[1][0] if isinstance(args[1], tuple) else None
    elif event in ("socket.getaddrinfo", "socket.gethostbyname"):
        host = args[0]
    else:
        return
    if not netgate.is_local(host):
        _recording.append((event, host))
        raise ConnectionRefusedError(f"test harness: no network ({host})")


sys.addaudithook(_recorder)


@pytest.fixture
def outbound():
    global _recording
    _recording = []
    yield _recording
    _recording = None


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    """A fresh install: empty .cursiv folders, no keys, default settings."""
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.memory import semantic as sem
    app_dir, home_dir = tmp_path / "app" / ".cursiv", tmp_path / "home" / ".cursiv"
    monkeypatch.setattr(netgate, "CONFIG_FILE", app_dir / "config.json")
    monkeypatch.setattr(ca, "_KEYS_FILE_APP", app_dir / "config.json")
    monkeypatch.setattr(ca, "_CLOUD_FILE", home_dir / "cursiv_cloud.json")
    monkeypatch.setattr(sem, "CURSIV_DIR", app_dir)
    monkeypatch.setattr(sem, "FACTS_FILE", app_dir / "memory_facts.jsonl")
    monkeypatch.setattr(sem, "SETTINGS_FILE", app_dir / "memory_settings.json")
    monkeypatch.setattr(sem, "EMB_CACHE_FILE", app_dir / "embeddings_cache.json")
    monkeypatch.setattr(sem, "_strand_items", lambda: [])
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.setattr(ca, "BRAVE_KEY", "")
    from cursiv_v215.core import phases
    monkeypatch.setitem(phases._conn_cache, "t", 0.0)
    monkeypatch.setitem(phases._conn_cache, "online", None)
    return app_dir


def _local_model(monkeypatch, reply="Here is what I know."):
    """Ollama 'running' with a model, answering without a server."""
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.memory import semantic as sem
    monkeypatch.setattr(ca, "_ollama_running", lambda: True)
    monkeypatch.setattr(ca, "_resolve_ollama_model", lambda: "qwen2.5:3b")
    monkeypatch.setattr(ca, "_local_model_ready", lambda: True)
    monkeypatch.setattr(ca, "_call_ollama", lambda messages, **kw: iter([reply]))
    monkeypatch.setattr(ca, "_learn_later", lambda *a, **k: None)
    monkeypatch.setattr(sem, "_http", lambda path, payload=None, timeout=30: {"models": [{"name": "nomic-embed-text:latest"}]}
                        if path == "/api/tags" else {"embeddings": [[1.0, 0.0]] * len((payload or {}).get("input", []))})


# ── C-009: web search only when asked ───────────────────────────────────────

@pytest.mark.parametrize("text", [
    "How is the creek right now? We live near a cattle farm.",
    "What should we stock up on this week?",
    "our current water supply is low",
    "What's the latest on the storm today ?",
])
def test_trigger_words_no_longer_search(fresh, text):
    from cursiv_v215.ui import chat_app as ca
    assert ca._needs_search(text) is False


def test_explicit_search_prefix_still_searches(fresh):
    from cursiv_v215.ui import chat_app as ca
    assert ca._needs_search("search: county burn ban")
    assert ca._needs_search("search county burn ban")


def test_automatic_search_is_an_opt_in_setting(fresh):
    from cursiv_v215.ui import chat_app as ca
    assert netgate.setting("web_search_auto") is False
    netgate.set_setting("web_search_auto", True)
    assert ca._needs_search("What should we stock up on this week?")
    netgate.set_offline(True)
    assert ca._needs_search("What should we stock up on this week?") is False
    assert ca._needs_search("search: anything") is False


def test_web_search_does_not_go_out_offline(fresh, outbound):
    from cursiv_v215.ui import chat_app as ca
    netgate.set_offline(True)
    assert ca._web_search("search: weather") == ""
    assert outbound == []


# ── C-010: offline mode is real and persists ────────────────────────────────

def test_offline_on_persists_to_config(fresh):
    import chat_commands as cc
    cfg = cc._default_cfg()
    assert cfg["offline_mode"] is False
    out = cc.handle_command("offline on", cfg, [])
    assert "Offline mode ON" in out.text and cfg["offline_mode"] is True
    data = json.loads((fresh / "config.json").read_text(encoding="utf-8"))
    assert data["offline_mode"] is True
    netgate._cache["mtime"] = None              # a restart re-reads the file
    assert netgate.allowed() is False
    assert cc._default_cfg()["offline_mode"] is True
    assert "Offline mode:  ON" in cc.handle_command("status", cc._default_cfg(), []).text
    assert "Web search skipped" in cc.handle_command("search: weather", cfg, []).text
    cc.handle_command("offline off", cfg, [])
    assert netgate.allowed() is True and cfg["offline_mode"] is False


def test_websearch_and_autoupdate_commands_save_settings(fresh):
    import chat_commands as cc
    cfg = cc._default_cfg()
    assert "OFF" in cc.handle_command("websearch", cfg, []).text
    assert "ON" in cc.handle_command("websearch on", cfg, []).text
    assert "ON" in cc.handle_command("autoupdate on", cfg, []).text
    data = json.loads((fresh / "config.json").read_text(encoding="utf-8"))
    assert data["web_search_auto"] is True and data["update_check_auto"] is True


def test_offline_keeps_saved_keys(fresh):
    from cursiv_v215.ui import chat_app as ca
    ca._store_key("groq_key", "gsk_" + "x" * 30)
    netgate.set_offline(True)
    netgate.set_offline(False)
    assert ca._saved_key("groq_key").startswith("gsk_")


def test_closed_gate_refuses_connections_at_the_socket(fresh):
    netgate.set_offline(True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(netgate.NetworkBlocked):
            s.connect(("203.0.113.7", 443))           # TEST-NET-3, never routed
    finally:
        s.close()
    with pytest.raises(netgate.NetworkBlocked):
        socket.getaddrinfo("api.groq.com", 443)


def test_closed_gate_still_allows_loopback(fresh):
    netgate.set_offline(True)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    try:
        c = socket.create_connection(server.getsockname(), timeout=2)
        c.close()
    finally:
        server.close()
    assert netgate.is_local("localhost") and netgate.is_local("::1") and not netgate.is_local("8.8.8.8")


def test_offline_cloud_callers_stop_before_the_network(fresh, outbound, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    ca._store_key("groq_key", "gsk_" + "x" * 30)
    netgate.set_offline(True)
    assert ca.cloud_enabled() is False
    assert ca._free_key_llm([{"role": "user", "content": "hi"}], 50) == ""
    with pytest.raises(netgate.NetworkBlocked):
        ca._post_json("https://api.groq.com/x", {}, {}, 5)
    assert ca._is_online() is False
    assert outbound == []


def test_offline_with_keys_and_a_trigger_word_answers_locally(fresh, outbound, monkeypatch):
    """C-010 acceptance: offline on, saved keys, a trigger word -> zero external connections."""
    from cursiv_v215.ui import chat_app as ca
    _local_model(monkeypatch, reply="Boil it for a minute.")
    ca._store_key("groq_key", "gsk_" + "x" * 30)
    ca._store_key("gemini_key", "AIza" + "x" * 30)
    netgate.set_setting("web_search_auto", True)
    netgate.set_offline(True)
    out = "".join(ca.chat("Is the creek water safe to drink right now? search: creek", [],
                          "xai-" + "x" * 30, None, anthropic_key="sk-ant-" + "x" * 30))
    assert "Boil it" in out
    assert outbound == []


# ── C-011: nothing automatic on a fresh install ─────────────────────────────

@pytest.mark.parametrize("text", [
    "What should we stock up on this week?",
    "How is the creek right now? We live near a cattle farm.",
    "hey, how are you doing?",
])
def test_fresh_install_chat_turn_makes_no_outside_connections(fresh, outbound, monkeypatch, text):
    """The 'done' check: empty .cursiv, no keys, default settings, local model ready."""
    from cursiv_v215.ui import chat_app as ca
    _local_model(monkeypatch)
    probes = []
    real_is_online = ca._is_online
    monkeypatch.setattr(ca, "_is_online", lambda: probes.append(1) or real_is_online())
    out = "".join(ca.chat(text, [], "", None))
    assert "Here is what I know." in out
    assert outbound == []
    assert probes == []                               # no 8.8.8.8 check either


def test_connectivity_probe_runs_only_when_something_would_use_it(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    calls = []
    monkeypatch.setattr(ca, "_is_online", lambda: calls.append(1) or True)
    monkeypatch.setattr(ca, "_local_model_ready", lambda: True)
    assert ca._connectivity_probe("", "", "") is None and calls == []
    assert ca._connectivity_probe("xai-key", "", "") is True and calls == [1]
    monkeypatch.setattr(ca, "_local_model_ready", lambda: False)
    assert ca._connectivity_probe("", "", "") is True
    netgate.set_offline(True)
    calls.clear()
    assert ca._connectivity_probe("xai-key", "", "") is None and calls == []


def test_connectivity_phase_reports_not_checked(fresh):
    from cursiv_v215.core import phases
    r = phases.PhaseResult()
    phases._connectivity(r, lambda: None, lambda: True)
    assert ("Connectivity", "not checked, local model ready") in r.trace


def test_automatic_update_check_is_off_by_default(fresh):
    assert netgate.update_check_auto() is False
    netgate.set_setting("update_check_auto", True)
    assert netgate.update_check_auto() is True
    netgate.set_offline(True)
    assert netgate.update_check_auto() is False


def test_launcher_update_check_follows_the_setting(fresh):
    src = (netgate.Path(__file__).resolve().parent.parent / "launcher" / "cursiv_launcher.py").read_text(encoding="utf-8")
    start = src.index("def _auto_update_check_on")
    ns: dict = {}
    exec(src[start:src.index("\n\n\n", start)], ns)  # the helper alone; the launcher needs Qt
    assert ns["_auto_update_check_on"]() is False
    netgate.set_setting("update_check_auto", True)
    assert ns["_auto_update_check_on"]() is True
    assert "if _auto_update_check_on():\n            QTimer.singleShot(10_000" in src


def test_embedding_model_is_not_pulled_offline(fresh, monkeypatch):
    from cursiv_v215.memory import semantic as sem
    monkeypatch.setattr(sem, "_embed_ok", None)
    monkeypatch.setattr(sem, "_http", lambda path, payload=None, timeout=30: {"models": [{"name": "qwen2.5:3b"}]})
    started = []
    monkeypatch.setattr(threading, "Thread", lambda *a, **k: started.append(k.get("target")) or _NoThread())
    netgate.set_offline(True)
    assert sem.embeddings_available() is False
    assert started == []
    monkeypatch.setattr(sem.urllib.request, "urlopen", lambda *a, **k: pytest.fail("pulled while offline"))
    sem._pull_embed_model()                           # returns before any request


def test_first_model_download_is_refused_offline(fresh):
    from cursiv_v215.ui import chat_app as ca
    netgate.set_offline(True)
    out = "".join(ca._pull_ollama_model("qwen2.5:3b"))
    assert "offline mode is on" in out


class _NoThread:
    def start(self):
        pass


def test_cursiv_cloud_is_off_on_a_fresh_install(fresh):
    from cursiv_v215.ui import chat_app as ca
    assert ca.cloud_enabled() is False
    ca.set_cloud_enabled(True)
    assert ca.cloud_enabled() is True

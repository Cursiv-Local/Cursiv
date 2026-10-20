"""A web search that returns a bot check, or nothing, is said plainly and never passed off as results
(U77, 2026-10-19: DuckDuckGo's "are you a bot?" page was kept as search results, cached, and the answer
was labelled "web search results"; the model then said searching "would violate privacy and safety
rules"). No real network: urlopen is replaced."""
import io
import json

import pytest

from cursiv_v215.chat import web_search as ws
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)

BOT_PAGE = ("<html><body><div class='anomaly-modal'>DuckDuckGo Unfortunately, bots use DuckDuckGo too. "
            "Please complete the following challenge to confirm this search was made by a human. "
            "Select all squares containing a duck: Submit Images not loading? Please email the following "
            "code to: error-lite+55ab@duckduckgo.com</div></body></html>")
RESULTS_PAGE = ("<html><body><table><tr><td>Offline-first apps keep working without a connection and sync "
                "later when one is available.</td></tr><tr><td>Many MIT-licensed note-taking tools store data "
                "locally in plain files you can back up.</td></tr></table></body></html>")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def net(monkeypatch, tmp_path):
    """DuckDuckGo stand-in: the Instant Answer API has nothing, the lite page is `page[0]`."""
    from cursiv_v215.core import netgate
    monkeypatch.setattr(netgate, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(ws, "BRAVE_KEY", "")
    cache = {}
    monkeypatch.setattr(ws, "_wcache_get", lambda q, allow_stale=False: (cache[q], True) if q in cache else None)
    monkeypatch.setattr(ws, "_wcache_store", lambda q, r, **kw: cache.__setitem__(q, r))
    monkeypatch.setattr(ws, "_WCACHE_OK", True)
    page = [BOT_PAGE]

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.duckduckgo.com" in url:
            return _Resp(json.dumps({"Answer": "", "AbstractText": "", "RelatedTopics": []}).encode())
        return _Resp(page[0].encode())
    monkeypatch.setattr(ws.urllib.request, "urlopen", urlopen)
    return page, cache


def test_a_bot_check_page_is_not_a_search_result(net):
    page, cache = net
    assert ws._web_search("search: github MIT offline note apps") == ""
    assert ws.last_problem == ws.BOT_CHECK_MESSAGE
    assert cache == {}                                       # and it isn't cached for a day


def test_real_results_still_come_back(net):
    page, cache = net
    page[0] = RESULTS_PAGE
    got = ws._web_search("search: github MIT offline note apps")
    assert "Offline-first apps keep working" in got and ws.last_problem == ""


def test_a_bot_check_cached_before_this_fix_is_ignored(net):
    page, cache = net
    cache["github MIT offline note apps"] = "Please complete the following challenge to confirm this search was made by a human."
    assert ws._web_search("search: github MIT offline note apps") == ""
    assert ws.last_problem == ws.BOT_CHECK_MESSAGE


def test_the_search_command_says_why_nothing_came_back(net, monkeypatch):
    import chat_commands as cc
    out = cc.handle_command("search: github MIT offline note apps", {}, [])
    assert out.text.startswith("No web results: DuckDuckGo asked to confirm a human")
    assert "complete the following challenge" not in out.text


def test_a_chat_turn_with_a_failed_search_says_so_and_claims_no_web_source(fresh, outbound, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    seen = {}
    _local_model(monkeypatch, reply="The search didn't return anything this time.")
    monkeypatch.setattr(ca, "_call_ollama", lambda messages, **kw: (seen.setdefault("sys", messages[0]["content"]),
                                                                    iter(["The search didn't return anything."]))[1])
    monkeypatch.setattr(ca, "_needs_search", lambda text: True)
    monkeypatch.setattr(ca, "_is_online", lambda *a, **k: True)

    def failed(q, max_results=4):
        ws.last_problem = ws.BOT_CHECK_MESSAGE
        return ""
    monkeypatch.setattr(ca, "_web_search", failed)
    out = "".join(ca.chat("search: github MIT offline note apps", [], "", None))
    assert "*[Web search tried, no results: DuckDuckGo asked to confirm a human" in out
    assert "web search results" not in out                  # the source line doesn't claim one
    assert "it was tried and failed" in seen["sys"] and "don't say searching is against any rule" in seen["sys"]

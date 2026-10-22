"""Services commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from command_runtime import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    if runtime._BABEL_OK and (cmd == "babel" or (cmd.startswith("babel") and len(cmd) > 5 and cmd[5] in (" ", ":"))):
        raw_input = runtime._babel_input(text)
        if not raw_input:
            return runtime.TextResult("Usage: babel <text in any language>  ·  babel <text> into <language(s)>")
        into_match = runtime.re.search(r"\s+into\s+(.+)$", raw_input, runtime.re.IGNORECASE)
        # "translate into Spanish hello ..." names the language first (it was labelled
        # "Translate → English" and sent with the to-English prompt).
        lead = runtime.re.match(r"(?i)^(?:in)?to\s+([a-z]+)\s*[:,-]?\s+(.+)$", raw_input, runtime.re.S)
        src, targets = "", []
        if lead and lead.group(1).lower() in runtime._LANG_NAMES:
            src, targets = runtime._babel_source(lead.group(2)), [lead.group(1).title()]
        elif into_match and not runtime.re.match(r"^i\s+am\b", raw_input, runtime.re.IGNORECASE):
            src = runtime._babel_source(raw_input[:into_match.start()])
            targets = runtime._babel_targets(into_match.group(1))
        if src and targets:
            gen, label = runtime._cascade_gen(cfg, [
                {"role": "system", "content": (
                    "You are a precise translation engine. Translate the user's text "
                    "into each requested language, naturally and grammatically, as a native "
                    "speaker would say it. For each, output a header line "
                    "exactly like:\n  ── [Language Name] ──\nfollowed by the translation. "
                    "Return translations only, no explanations."
                )},
                {"role": "user", "content": f"Text to translate:\n{src}\n\nTranslate into: {', '.join(targets)}"},
            ], max_tokens=800)
            return runtime.StreamResult(f"Translate — English → {', '.join(targets)}", gen)
        gen, label = runtime._cascade_gen(cfg, [
            {"role": "system", "content": "Translate the following text to English. Return only the translation, nothing else."},
            {"role": "user", "content": raw_input},
        ], max_tokens=1500)
        return runtime.StreamResult(f"Translate → English", gen)

    # ── Web search + synthesis ───────────────────────────────────────────
    if cmd.startswith("search:") or cmd.startswith("search "):
        query = text[7:].strip()
        if not query:
            return runtime.TextResult("Usage: search <query>")
        if runtime._gate().is_offline():
            return runtime.TextResult(f"Web search skipped. {runtime._gate().OFFLINE_MESSAGE}")
        results = runtime._web_search(query)
        if not results:
            try:
                from cursiv_v215.chat import web_search as _ws
                why = _ws.last_problem
            except Exception:
                why = ""
            return runtime.TextResult(f"No web results: {why or 'nothing came back'}. Nothing was answered from the web.")
        gen = runtime._chat(
            f"search: {query}", history,
            cfg.get("api_key", ""), None, cfg.get("file_access", False),
            cfg.get("workspace", ''), cfg.get("openai_key", ""),
            False, cfg.get("anthropic_key", ""),
        )
        return runtime.StreamResult(f"⊕ Web search — {query}\n\n{results}\n", gen)

    # ── Page pull ────────────────────────────────────────────────────────
    if cmd.startswith("pull "):
        if runtime._gate().is_offline():
            return runtime.TextResult(f"Page pull skipped. {runtime._gate().OFFLINE_MESSAGE}")
        url = text[5:].strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            import urllib.request as _pur
            req = _pur.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Cursiv/3.14)"})
            with _pur.urlopen(req, timeout=12) as resp:
                raw_html = resp.read(65_536).decode("utf-8", errors="replace")
            body = runtime.re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=runtime.re.IGNORECASE)
            body = runtime.re.sub(r"<[^>]+>", " ", body)
            body = runtime.re.sub(r"&[a-zA-Z]{2,6};", " ", body)
            body = runtime.re.sub(r"\s+", " ", body).strip()[:4000]
        except Exception as e:
            return runtime.TextResult(f"Fetch failed: {e}")
        if len(body) < 80:
            return runtime.TextResult("Page returned too little text — may require JavaScript.")
        gen, label = runtime._cascade_gen(cfg, [
            {"role": "user", "content": (
                f"URL: {url}\n\nContent:\n{body}\n\n"
                "Analyze this page. Give: 1) core thesis, 2) key facts worth remembering, "
                "3) any connection to current work. Be precise, no filler."
            )},
        ], max_tokens=800)
        def _finish(full):
            if runtime._STRAND_OK and full:
                runtime._strand_save(f"pull: {url}", full, tags=["pull", "web"], score=0.72,
                             territory_tag="worldmodel", source="pull", model=label)
        return runtime.StreamResult(f"Page pull — {url[:70]}", gen, _finish)

    # ── Obsidian ─────────────────────────────────────────────────────────
    if cmd in ("obsidian on", "obsidian off"):
        cfg["obsidian_enabled"] = cmd == "obsidian on"
        runtime._obs_save_config(cfg["obsidian_enabled"], cfg.get("obsidian_path", ""))
        msg = f"Obsidian sync → {'ON' if cfg['obsidian_enabled'] else 'OFF'}"
        if cfg["obsidian_enabled"] and not cfg.get("obsidian_path"):
            msg += "\nSet vault path with: obsidian path <path>"
        return runtime.TextResult(msg)

    if cmd.startswith("obsidian path "):
        cfg["obsidian_path"] = text[14:].strip()
        runtime._obs_save_config(cfg.get("obsidian_enabled", False), cfg["obsidian_path"])
        return runtime.TextResult(f"Obsidian vault → {cfg['obsidian_path']}")

    if cmd == "obsidian export":
        if not cfg.get("obsidian_path"):
            return runtime.TextResult("Set vault path first: obsidian path <path>")
        ok, msg = runtime._obs_export(cfg["obsidian_path"])
        return runtime.TextResult(msg)

    if cmd == "obsidian status":
        return runtime.TextResult(
            f"Obsidian sync: {'ON' if cfg.get('obsidian_enabled') else 'OFF'}\n"
            f"Vault path: {cfg.get('obsidian_path') or '(not set)'}"
        )

    # ── Direct provider retry ───────────────────────────────────────────
    if cmd in ("grok", "use grok", "try grok"):
        last = cfg.get("last_user_msg", "")
        if not last:
            return runtime.TextResult("No previous message to retry with Grok.")
        if not cfg.get("api_key"):
            return runtime.TextResult("No xAI key set. Type: key xai-xxxxx")
        gen = runtime._chat(last, history[:-1] if history else [], cfg["api_key"], None, False,
                    cfg.get("workspace", ''), cfg.get("openai_key", ""), False, "",
                    force_provider="grok")
        return runtime.StreamResult("⟳ Grok re-run", gen)

    if cmd in ("claude", "use claude", "try claude"):
        last = cfg.get("last_user_msg", "")
        if not last:
            return runtime.TextResult("No previous message to retry with Claude.")
        if not cfg.get("anthropic_key"):
            return runtime.TextResult("No Anthropic key set. Type: anthropic sk-ant-xxxxx")
        gen = runtime._chat(last, history[:-1] if history else [], "", None, False,
                    cfg.get("workspace", ''), "", False, cfg["anthropic_key"],
                    force_provider="claude")
        return runtime.StreamResult("⟳ Claude re-run", gen)

    if cmd in ("chatgpt", "gpt", "openai", "use chatgpt", "use gpt", "use openai",
               "try chatgpt", "try gpt", "try openai"):
        last = cfg.get("last_user_msg", "")
        if not last:
            return runtime.TextResult("No previous message to retry with ChatGPT.")
        if not cfg.get("openai_key"):
            return runtime.TextResult("No OpenAI key set. Type: openai sk-xxxxx")
        gen = runtime._chat(last, history[:-1] if history else [], "", None, False,
                    cfg.get("workspace", ''), cfg["openai_key"], False, "",
                    force_provider="openai")
        return runtime.StreamResult("⟳ ChatGPT re-run", gen)

    # ── Postal — sealed encrypted letters (read/manage side; composing a
    # new letter needs a multi-line dialog, handled by chat_panel.py) ──────
    return UNHANDLED

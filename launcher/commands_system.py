"""System commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

import json
from command_runtime import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    if cmd in ('check', 'check status', 'check off', 'check fast', 'check full'):
        from cursiv_v215.chat import review
        try:
            if cmd in ('check off', 'check fast', 'check full'):
                review.set_mode(cmd.split()[1])
            selected = review.mode()
        except (OSError, ValueError) as exc:
            return runtime.TextResult(f'Answer-check setting not changed: {exc}')
        return runtime.TextResult(
            f'Answer checks: {selected.upper()}. Fast deterministic checks always remain on.\n' +
            {'off': 'No model verification pass.',
             'fast': 'Default: one short local review for eligible high-risk turns; no model rewrite. Desktop reviews run after the answer is ready.',
             'full': 'Eligible turns allow a bounded review/rewrite/recheck. Desktop results appear as a background follow-up.'}[selected])
    if runtime._looks_like_text_to_json_request(text):
        notes = text
        if len(text) < 160:
            for turn in reversed(history):
                if turn.get("role") == "user":
                    notes = turn.get("content", "")
                    break
        ok, msg, entry = runtime.text_to_training_entry(notes, cfg)
        if ok and entry:
            return runtime.TextResult(f"{msg}\n\n```json\n{json.dumps(entry, indent=2)}\n```")
        return runtime.TextResult(f"{msg}")

    # ── Simple state toggles ────────────────────────────────────────────
    def _engine_line() -> str:
        try:
            from cursiv_v215.core import ollama_host
            return ollama_host.diagnose()
        except Exception as exc:
            return f"unknown ({exc})"

    if cmd == "status":
        # What a reviewer asks first: is it local only, and which model answers (MRS feedback, 2026-10-18).
        try:
            from cursiv_v215.chat import status as _status
            mode = _status.network_status()["label"]
        except Exception:
            mode = "unknown"
        try:
            from cursiv_v215.ui.chat_app import _resolve_ollama_model
            model = _resolve_ollama_model()
        except Exception:
            model = None
        lines = [
            f"Mode:          {mode}",
            f"AI model:      {(model + ', on this computer (Ollama)') if model else 'no local model running'}",
            f"AI engine:     {_engine_line()}",
            f"Offline mode:  {'ON' if runtime._gate().is_offline() else 'OFF'}",
            f"Web search:    {'automatic' if runtime._gate().setting('web_search_auto') else 'only search:'}",
            f"Update check:  {'automatic' if runtime._gate().setting('update_check_auto') else 'manual'}",
            f"Cloud AI keys: {', '.join(n for n, k in (('xAI', 'api_key'), ('OpenAI', 'openai_key'), ('Anthropic', 'anthropic_key')) if cfg.get(k)) or 'none set'}",
            f"File access:   {'ON' if cfg.get('file_access') else 'OFF'}",
        ]
        try:
            from cursiv_v215.core import demo as _demo, documents as _documents, fieldlog as _fieldlog
            n, bad = len(_fieldlog.entries()), _fieldlog.verify()
            lines.append(f"Field notebook: {n} entr{'y' if n == 1 else 'ies'}, "
                         + ("intact" if not bad else f"{len(bad)} problem(s): type field log check"))
            lines.append(f"Documents:     {len(_documents.library())} imported")
            if _demo.active():
                lines.insert(0, "FIELD DEMO ON: the notebook and documents hold sample data (demo off to end it)")
        except Exception:
            pass
        if cfg.get("file_access"):
            lines.append(f"Workspace:     {cfg.get('workspace', '')}")
        return runtime.TextResult("\n".join(lines))

    if cmd in runtime._RETIRED:
        return runtime.TextResult(f"'{text}' was removed in this version. Type help to see what Cursiv can do.")

    if cmd == "tier 1":
        cmd = "offline on"           # tier 1 meant "local only": the same as offline mode
    if cmd in ("offline on", "offline off"):
        from cursiv_v215.core import netgate
        try:
            netgate.set_offline(cmd == "offline on")
        except Exception as exc:
            return runtime.TextResult(f"Couldn't save offline mode ({exc}). Nothing was changed.")
        cfg["offline_mode"] = netgate.is_offline()
        if cfg["offline_mode"]:
            return runtime.TextResult("Offline mode ON — Cursiv won't connect to anything outside this computer "
                              "(cloud AI, web search, update checks, model downloads). Your local model still works. "
                              "This stays on after a restart; type 'offline off' to undo.")
        return runtime.TextResult("Offline mode OFF — keys you've added, Cursiv Cloud and 'search:' can reach the internet again. "
                          "Automatic web search and update checks stay as set ('websearch on', 'autoupdate on').")

    if cmd in ("websearch on", "websearch off", "websearch"):
        from cursiv_v215.core import netgate
        if cmd != "websearch":
            netgate.set_setting("web_search_auto", cmd == "websearch on")
        on = netgate.setting("web_search_auto")
        return runtime.TextResult(
            ("Automatic web search ON — questions that sound current (\"today\", \"right now\") are sent to "
             "DuckDuckGo. Type 'websearch off' to stop." if on else
             "Automatic web search OFF — only messages that start with 'search:' go to the web.")
            + (f"\n{netgate.OFFLINE_MESSAGE}" if netgate.is_offline() else ""))

    if cmd in ("autoupdate on", "autoupdate off", "autoupdate"):
        from cursiv_v215.core import netgate
        if cmd != "autoupdate":
            netgate.set_setting("update_check_auto", cmd == "autoupdate on")
        on = netgate.setting("update_check_auto")
        return runtime.TextResult(
            ("Automatic update check ON — Cursiv asks GitHub for a new version after you log in."
             if on else "Automatic update check OFF — use \"Check for Updates\" when you want to.")
            + (f"\n{netgate.OFFLINE_MESSAGE}" if netgate.is_offline() else ""))

    if cmd in ("files on", "files off"):
        from cursiv_v215.core import workspace
        from cursiv_v215.memory.semantic import current_person
        enabled = cmd == 'files on'
        try:
            if not cfg.get('workspace'):
                if enabled:
                    return runtime.TextResult('Choose workspace <folder> before enabling file access. No folder was implicitly authorized.')
            else:
                workspace.save(current_person(), cfg['workspace'], enabled)
        except (OSError, ValueError, TypeError) as exc:
            cfg['file_access'] = False
            return runtime.TextResult(f'File access not enabled: {exc}')
        cfg['file_access'] = enabled
        return runtime.TextResult(f"File access → {'ON' if enabled else 'OFF'}" + (f"\nWorkspace: {cfg['workspace']}" if enabled else ''))

    if cmd == "mode":
        cfg["confirm_mode"] = "confirm" if cfg.get("confirm_mode") == "auto" else "auto"
        return runtime.TextResult(f"Write mode → {cfg['confirm_mode'].upper()}")

    if cmd.startswith("workspace"):
        new_ws = text[9:].strip()
        if not new_ws:
            return runtime.TextResult(f"Workspace: {cfg.get('workspace', '')}")
        from cursiv_v215.core.tools import _resolve
        from cursiv_v215.core import workspace
        from cursiv_v215.memory.semantic import current_person
        try:
            ws_path = workspace.save(current_person(), str(_resolve(new_ws)), cfg.get('file_access', False))
        except (OSError, ValueError, TypeError) as exc:
            return runtime.TextResult(f'Workspace selection not confirmed: {exc}')
        cfg["workspace"] = ws_path
        return runtime.TextResult(f"Workspace → {ws_path}")

    # ── Free AI keys (Gemini / Groq) and Cursiv Cloud ─────────────────────
    return UNHANDLED

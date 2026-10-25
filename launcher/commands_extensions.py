"""Extensions commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from cursiv_engine.core.command_api import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    if cmd in ("tone", "style", "my style", "style show", "style clear") or cmd.startswith(("tone ", "style ")):
        try:
            from cursiv_engine.core import style as _style
            from cursiv_engine.memory import semantic as _sem
            _reply = _style.command(text, _sem.current_person())
            if _reply is not None:
                return runtime.TextResult(_reply)
        except Exception as exc:
            return runtime.TextResult(f"Couldn't change the style: {exc}")

    # ── Cursiv Forge: plugins + evolve; project memory (U52) ──────────────────
    if cmd in ("plugins", "plugin") or cmd.startswith("plugin "):
        from cursiv_engine.core import plugins as _pl
        _m = __import__("re").match(r"(?i)^plugin\s+(show|off|on|remove|delete|approve)\s+(\w+)\s*$", text.strip())
        if not _m:
            return runtime.TextResult(_pl.listing())
        _act, _name = _m.group(1).lower(), _m.group(2).lower()
        if _act == "show":
            return runtime.TextResult(_pl.show(_name))
        if _act in ("off", "on"):
            return runtime.TextResult(_pl.set_enabled(_name, _act == "on"))
        if _act == "approve":
            return runtime.TextResult(_pl.approve_existing(_name))
        return runtime.TextResult(_pl.remove(_name))
    if cmd == "evolve" or cmd.startswith("evolve "):
        from cursiv_engine.coding import forge as _forge
        _idea = text[6:].strip()
        if _idea.lower() in ("approve", "yes", "install"):
            return runtime.TextResult(_forge.approve())
        if _idea.lower() in ("discard", "no", "cancel"):
            return runtime.TextResult(_forge.discard())
        if _idea.lower() in ("", "help"):
            return runtime.TextResult("evolve <idea> — Cursiv writes a plugin that gives it a new ability, checks it for safety, "
                              "tests it in a sandbox, and shows you the code. Nothing installs until you type "
                              "`evolve approve`.\nExamples:\n  evolve a command that converts recipe amounts between cups and grams\n"
                              "  evolve a tool that tells me how many days until a date\n  evolve a tracker for my kids' chores")
        try:
            from cursiv_engine.ui.chat_app import _local_model_ready, _ollama_pulled_models
            _coder = _local_model_ready() and any("coder" in m for m in _ollama_pulled_models())
        except Exception:
            _coder = False
        _lf = (lambda m: runtime._call_ollama_code_council(m, max_tokens=4000)) if _coder else None

        def _gen(msgs):
            g, _u = runtime._cascade_stream(msgs, cfg, max_tokens=4000, local_fn=_lf)
            return g
        return runtime.StreamResult(f"Forge — {_idea[:60]}", _forge.evolve(_idea, _gen), None)
    if cmd in ("projects", "topics", "my projects") or __import__("re").match(r"(?i)^project (show|forget|delete) ", text.strip()):
        from cursiv_engine.memory import projects as _projmem
        from cursiv_engine.memory import semantic as _sem
        _r = _projmem.command(text, _sem.current_person())
        if _r is not None:
            return runtime.TextResult(_r)
    try:                     # commands added by installed plugins
        from cursiv_engine.core import plugins as _pl
        _out = _pl.run_command(text)
        if _out is not None:
            return runtime.TextResult(_out)
    except Exception:
        pass

    if cmd in ("agents", "agent", "agent list") or cmd.startswith(("agent ", "@")):
        res = runtime._agent_command(text, cfg, history)
        if res is not None:
            return res

    if cmd == "codex" or cmd.startswith("codex "):
        return runtime._codex_command(text[6:].strip(), cfg, history)

    if cmd == "hermes" or cmd.startswith("hermes "):
        if not runtime._HERMES_OK or not runtime._hermes_avail():
            return runtime.TextResult("Hermes Agent not available — needs Ollama running.")
        prompt = text[7:].strip()
        if not prompt:
            return runtime.TextResult("Usage: hermes <task to run>")
        result = runtime._hermes_run(prompt)
        runtime._session_append(prompt, result, "hermes_agent")
        return runtime.TextResult(result)

    if cmd == "ref" or cmd.startswith("ref "):
        if not runtime._REF_OK or not runtime._ref_avail():
            return runtime.TextResult("Reference Brain not available.")
        query = text[4:].strip()
        if not query:
            return runtime.TextResult("Usage: ref <question>")
        return runtime.TextResult(runtime._ref_answer(query))

    # ── Council (removed in U97) ──
    if (cmd == "council" or cmd.startswith("council ") or cmd in ("/full", "/deliberate")
            or cmd.startswith(("/full ", "/deliberate "))):
        return runtime.TextResult('The council was removed from Cursiv. Ask your question normally, or ask your own agents together with: agents ask <question>')

    # ── Strand memory ────────────────────────────────────────────────────
    return UNHANDLED

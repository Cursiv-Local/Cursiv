"""Command agents.

Functions receive the explicit CommandRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _babel_source, _babel_targets, _cascade_gen, _codex_command, _agent_command.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Generator, Optional
from cursiv_engine.core.command_api import TextResult, NotebookResult, FileActionResult, MemoryResult, NotesResult, StreamResult
from cursiv_engine.core.command_api import CommandRuntime

def _babel_source(runtime: CommandRuntime, text: str) -> str:
    """The text to translate: drop a leading "translate" and surrounding quotes."""
    t = runtime.re.sub(r"^\s*translate\s+", "", text.strip(), flags=runtime.re.I).strip()
    return t.strip("\"'“”‘’ ").strip()

def _babel_targets(runtime: CommandRuntime, phrase: str) -> list[str]:
    """Languages named after "into": split on commas / "and" / "&", and on spaces
    only when every word is a known language ("spanish french"), so "Mandarin
    Chinese" or "Brazilian Portuguese" stay whole and "all the languages you can"
    means a broad set rather than five 'languages' called All, The, …"""
    phrase = phrase.strip().rstrip(".!?")
    if runtime._BABEL_MANY.search(phrase):
        return list(runtime._BABEL_DEFAULT_SET)
    targets: list[str] = []
    for part in runtime.re.split(r"\s*(?:,|;|&|\band\b)\s*", phrase, flags=runtime.re.I):
        part = part.strip()
        if not part:
            continue
        words = part.split()
        if len(words) > 1 and all(w.lower() in runtime._LANG_NAMES for w in words):
            targets += [runtime._LANG_NAMES[w.lower()] for w in words]
        else:
            targets.append(runtime._LANG_NAMES.get(part.lower(), part.title()))
    seen: set[str] = set()
    return [t for t in targets if not (t in seen or seen.add(t))]

def _cascade_gen(runtime: CommandRuntime, cfg: dict, messages: list[dict], max_tokens: int):
    """Local model first, then any keys (chat_app.cascade_stream), falling through
    whenever one fails, so one-shot tools (babel, grow) work with no keys or dead
    ones. Returns (generator, engine label); the generator ends with an
    "Answered by …" line naming the engine that really answered."""
    gen, used = runtime._cascade_stream(messages, cfg, max_tokens=max_tokens)

    def _labelled():
        yield from gen
        if used:
            yield f"\n\n*[Answered by {used[0].replace(' (local)', '')}]*"

    return _labelled(), (used[0] if used else "")

def _codex_command(runtime: CommandRuntime, prompt: str, cfg: dict, history: list[dict]):
    from cursiv_engine.coding import brain, runner
    from cursiv_engine.memory import semantic
    person = semantic.current_person()
    low = prompt.lower()

    if not prompt or low in ("help", "?"):
        return runtime.TextResult(runtime._CODEX_HELP)
    if low == "keep":
        return runtime.TextResult(brain.keep_example(runtime._LAST_CODEX.get("q", ""), runtime._LAST_CODEX.get("a", ""), person))
    if low == "lessons":
        ls = brain.list_lessons(person)
        if not ls:
            return runtime.TextResult("No coding lessons yet. I learn them as we work (your setup, errors you hit, "
                              "fixes that worked), or add one: codex learn <lesson>")
        return runtime.TextResult("Coding lessons I use:\n" + "\n".join(f"- {l['text']}" for l in ls[-40:]) +
                          "\n\nRemove one: codex forget <words>")
    if low.startswith("learn "):
        ok = brain.add_lesson(prompt[6:], person)
        return runtime.TextResult("Got it — I'll use that in coding answers." if ok else "I already know that (or it's too short).")
    if low.startswith("forget "):
        gone = brain.forget_lessons(prompt[7:], person)
        return runtime.TextResult(("Forgotten:\n" + "\n".join(f"- {g}" for g in gone)) if gone else "No lesson matched that.")
    if low == "project" or low.startswith("project "):
        arg = prompt[7:].strip()
        if not arg:
            cur = brain.project(person)
            return runtime.TextResult(f"Current project: {cur}" if cur else "No project set. Use: codex project <folder path>")
        return runtime.TextResult(brain.set_project(arg, person))
    if low == "run":
        code = runner.extract_python(runtime._LAST_CODEX.get("a", ""))
        if not code:
            return runtime.TextResult("The last codex answer has no Python code to run.")
        ok, why = runner.check(code)
        if not ok:
            return runtime.TextResult(f"I won't run it here: {why}.")
        success, out = runner.run(code)
        return runtime.TextResult(("✅ It runs.\n" if success else "❌ It failed.\n") + f"```\n{out[-2000:] or '(no output)'}\n```")

    msgs = brain.build_messages(prompt, history, person)

    try:
        from cursiv_engine.ui.chat_app import _local_model_ready, _ollama_pulled_models
        has_coder = _local_model_ready() and any("coder" in m for m in _ollama_pulled_models())
    except Exception:
        has_coder = False
    local_fn = (lambda m: runtime._call_ollama_code_council(m, max_tokens=4000)) if has_coder else None

    def make_gen(messages):
        gen, _used = runtime._cascade_stream(messages, cfg, max_tokens=4000, local_fn=local_fn)
        return gen

    def regenerate(code: str, error: str):
        fix_msgs = msgs + [
            {"role": "assistant", "content": f"```python\n{code}\n```"},
            {"role": "user", "content": "I ran that code and it failed:\n```\n" + error[-2500:] + "\n```\n"
                                        "Explain the cause in one or two sentences, then give the complete corrected "
                                        "file in one ```python block."},
        ]
        return make_gen(fix_msgs)

    def stream():
        parts = []
        for chunk in make_gen(msgs):
            parts.append(chunk)
            yield chunk
        for chunk in runner.run_and_fix("".join(parts), regenerate):
            parts.append(chunk)
            yield chunk
        yield "\n\n*Good answer? Type `codex keep` and I'll answer like this from now on.*"

    def _finish(full: str):
        runtime._LAST_CODEX.update(q=prompt, a=full)
        runtime._session_append(prompt, full, "codex")

        def learn():
            try:
                from cursiv_engine.ui.chat_app import _memory_llm
                brain.learn_from_exchange(prompt, full, _memory_llm, person)
            except Exception as exc:
                formation.record('coding_failed', exc)
        from cursiv_engine.memory import formation
        import uuid
        formation.submit(learn, 'coding:' + uuid.uuid4().hex)

    return runtime.StreamResult(f"Codex — {prompt[:60]}", stream(), _finish)

def _agent_command(runtime: CommandRuntime, text: str, cfg: dict, history: list[dict]):
    import re as _re
    from cursiv_engine.agents import custom
    t = text.strip()
    low = t.lower()
    if low in ("agents", "agent", "agent list", "agent help"):
        return runtime.TextResult(custom.listing())

    m = _re.match(r"(?is)^agent\s+(new|create|make)\s+@?([\w-]+)\s*[:\-]?\s*(.*)$", t)
    if m:
        return runtime.TextResult(custom.create(m.group(2), m.group(3)))
    m = _re.match(r"(?is)^agent\s+edit\s+@?([\w-]+)\s*[:\-]?\s*(.*)$", t)
    if m:
        return runtime.TextResult(custom.edit(m.group(1), m.group(2)))
    m = _re.match(r"(?is)^agent\s+teach\s+@?([\w-]+)\s*[:\-]?\s*(.*)$", t)
    if m:
        return runtime.TextResult(custom.teach(m.group(1), m.group(2)))
    m = _re.match(r"(?is)^agent\s+(delete|remove)\s+@?([\w-]+)\s*$", t)
    if m:
        return runtime.TextResult(custom.delete(m.group(2)))
    m = _re.match(r"(?is)^agent\s+(show|info)\s+@?([\w-]+)\s*$", t)
    if m:
        return runtime.TextResult(custom.describe(m.group(2)))

    try:
        from cursiv_engine.ui.chat_app import _build_strand_context
    except Exception:
        _build_strand_context = lambda q: ""

    def _memory(q):
        try:
            return _build_strand_context(q) if len(q) >= 10 else ""
        except Exception:
            return ""

    m = _re.match(r"(?is)^(?:agents\s+ask|agent\s+council)\s+(.+)$", t)
    if m:
        question = m.group(1).strip()
        agents = custom.all_agents()
        if not agents:
            return runtime.TextResult(custom.listing())
        mem = _memory(question)

        def stream():
            views = []
            for a in agents[:6]:
                yield f"\n**@{a['name']}**\n"
                gen, _u = runtime._cascade_stream(custom.messages_for(a, question + "\n\n(Answer in under 150 words, "
                                          "from your specialty.)", [], mem), cfg, max_tokens=500)
                parts = []
                for c in gen:
                    parts.append(c)
                    yield c
                views.append(f"{a['name']}: {''.join(parts).strip()[:1500]}")
                custom.note_use(a)
            yield "\n\n---\n**Together**\n"
            synth = [{"role": "system", "content": "You are Cursiv. Several specialist agents answered the same question. "
                      "Combine them into one clear recommendation: where they agree, where they differ, and the best "
                      "next step. Be brief. Don't invent facts."},
                     {"role": "user", "content": f"Question: {question}\n\n" + "\n\n".join(views)}]
            gen, _u = runtime._cascade_stream(synth, cfg, max_tokens=700)
            yield from gen
        return runtime.StreamResult(f"Your agents — {len(agents[:6])} answering", stream(), None)

    m = _re.match(r"(?is)^(?:@|agent\s+(?:ask\s+)?@?)([\w-]+)[\s,:]+(.+)$", t)
    if m:
        a = custom.load(m.group(1))
        if not a:
            names = ", ".join("@" + x["name"] for x in custom.all_agents()) or "none yet"
            return runtime.TextResult(f"There's no agent called {custom.clean_name(m.group(1))}. Your agents: {names}.\n"
                              f"Make one: agent new {custom.clean_name(m.group(1)) or 'name'}: <what it should do>")
        q = m.group(2).strip()
        if custom.asks_about_permissions(q):
            # What an agent may touch is decided by Cursiv's code, so Cursiv answers it, not the agent.
            return runtime.TextResult(custom.permissions_answer(a))
        gen, _u = runtime._cascade_stream(custom.messages_for(a, q, history, _memory(q)), cfg, max_tokens=3000)
        custom.note_use(a)
        return runtime.StreamResult(f"@{a['name']}", gen, None)
    if t.startswith("@"):
        return None            # a lone "@something" -- let normal chat handle it
    return runtime.TextResult(custom.listing())

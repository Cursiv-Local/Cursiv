"""Chat streaming.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _strip_status_lines, _set_answered, _ollama_label, _drop_fake_tool_lines, _time_boxed, _chat_stream, _friendly.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _strip_status_lines(runtime: ChatRuntime, text: str) -> str:
    """The model's words only: no status lines, no check notes."""
    return runtime._NOTES_BLOCK_RE.sub("", runtime._STATUS_LINE_RE.sub("", text or "")).strip()

def _set_answered(runtime: ChatRuntime, label: str) -> None:
    from . import model_selection
    if not label: model_selection.reset_response()
    runtime._ANSWERED_BY = model_selection.label_for(label)

def _ollama_label(runtime: ChatRuntime, base: str) -> str:
    try:
        model = runtime._resolve_ollama_model()
    except Exception:
        model = None
    return f"{base} · {model}" if model else base

def _drop_fake_tool_lines(runtime: ChatRuntime, gen: Generator) -> Generator:
    """Pass the reply through, minus any "(Checked on this computer …)" line this
    code didn't emit. A line is held back only while it could still turn into
    one; everything else streams as it arrives."""
    from cursiv_engine.core.file_access import VerifiedText
    line, holding, fenced = "", True, False

    def _is_fake(text: str) -> bool:
        s = text.strip()
        head = s.lstrip('*_ [')
        return ((not fenced and head.lower().startswith(('source:', 'sources:'))) or
                (s.lstrip("*_ ").startswith(runtime._TOOL_NOTE) and s not in runtime._REAL_TOOL_NOTES))

    for chunk in gen:
        if isinstance(chunk, VerifiedText):
            if line and holding and not _is_fake(line):
                yield line
            line, holding = "", True
            yield chunk                 # preserve application-owned receipt provenance
            continue
        if not isinstance(chunk, str) or chunk == runtime.RATE_SENTINEL or chunk.startswith(runtime.WRITE_SENTINEL):
            if line and holding and not _is_fake(line):
                yield line
            line, holding = "", True
            yield chunk
            continue
        out = []
        for ch in chunk:
            if ch == "\n":
                if holding:
                    if not _is_fake(line):
                        out.append(line + "\n")
                else:
                    out.append("\n")
                if line.lstrip().startswith(('```', '~~~')):
                    fenced = not fenced
                line, holding = "", True
                continue
            line += ch
            if holding:
                head = line.lstrip(" \t*_")
                source_head = line.lstrip(' \t*_[').lower()
                possible_source = not fenced and any(s.startswith(source_head) or source_head.startswith(s)
                                                     for s in ('source:', 'sources:'))
                if not (possible_source or runtime._TOOL_NOTE.startswith(head) or head.startswith(runtime._TOOL_NOTE)):
                    out.append(line)          # can't be a tool note -- release it
                    holding = False
            else:
                out.append(ch)
        if out:
            yield "".join(out)
    if line and holding and not _is_fake(line):
        yield line

def _time_boxed(runtime: ChatRuntime, gen, seconds: float, grace: float):
    """Stream a reply, but once `seconds` have passed, finish the current
    sentence (up to `grace` more seconds) and stop cleanly with a note --
    instead of either cutting off mid-sentence or typing for five minutes."""
    if not seconds or seconds <= 0:
        yield from gen          # no time limit
        return
    import time as _t
    from cursiv_engine.core.file_access import VerifiedText
    start = _t.monotonic()
    stopping = False
    for chunk in gen:
        if isinstance(chunk, VerifiedText):
            yield chunk                 # a completed backend outcome must not be truncated
            continue
        if not isinstance(chunk, str) or chunk in (runtime.RATE_SENTINEL, runtime.WRITE_SENTINEL) or chunk.startswith(runtime.WRITE_SENTINEL):
            yield chunk
            continue
        elapsed = _t.monotonic() - start
        if not stopping and elapsed > seconds:
            stopping = True
        if stopping:
            cut = max(chunk.rfind(c) for c in runtime._SENTENCE_END)
            if cut >= 0 or elapsed > seconds + grace:
                yield chunk[:cut + 1] if cut >= 0 else chunk
                try:
                    gen.close()
                except Exception:
                    pass
                yield ("\n\n*[Stopped after about {0} seconds to keep things quick — say "
                       "\"continue\" and I'll pick up right where I left off.]*").format(int(seconds))
                return
        yield chunk

def _chat_stream(runtime: ChatRuntime, message, history, api_key, files, file_access, root_path, openai_key, confirm_writes, anthropic_key, force_provider, reply: list[str], on_action):
    from cursiv_engine.core import selfknow as _sk
    runtime.grounding.reset_executions()
    runtime.grounding.set_memory_sources(())
    runtime._WORKED = None
    runtime._MEMORY_RECALLED = False
    runtime._MEMORY_TEXTS.clear()
    runtime._MEMORY_CTX = ""
    runtime._REAL_TOOL_NOTES.clear()
    runtime._RETRIEVED.clear()
    runtime._REF_SHOWN.clear()
    runtime._DOCS_SHOWN.clear()
    runtime._DOCS_SEARCHED_EMPTY.clear()
    runtime._WEB_SEARCHED = False
    runtime._set_answered("")
    for chunk in runtime._drop_fake_tool_lines(runtime._friendly(_sk, runtime._time_boxed(runtime._chat_inner(message=message, history=history, api_key=api_key, files=files, file_access=file_access, root_path=root_path, openai_key=openai_key, confirm_writes=confirm_writes, anthropic_key=anthropic_key, force_provider=force_provider, on_action=on_action)))):
        if isinstance(chunk, str) and chunk not in (runtime.RATE_SENTINEL,) and not chunk.startswith(runtime.WRITE_SENTINEL):
            reply.append(chunk)
        yield chunk
    if runtime._ANSWERED_BY or runtime._CURSIV_REPLY:   # what the answer was given (Cursiv's records, not the model's)
        _asked = message.get("text", "") if isinstance(message, dict) else str(message or "")
        note = f"\n\n*[{runtime.sources_line(''.join(reply), _asked)}]*"
        reply.append(note)
        yield note
    if runtime._ANSWERED_BY:     # say which engine answered (written by Cursiv, not the model)
        note = f"\n*[Answered by {runtime._ANSWERED_BY}]*"
        reply.append(note)
        yield note

def _friendly(runtime: ChatRuntime, sk, gen):
    """Swap raw provider errors ("[Groq error 413: {...}]") for a plain sentence."""
    for chunk in gen:
        if isinstance(chunk, str) and "[" in chunk[:4]:
            nice = sk.friendly_error(chunk)
            if nice:
                runtime._set_answered('')  # a provider error is not a completed answer
                yield nice
                continue
        yield chunk

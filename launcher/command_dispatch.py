"""Command dispatch.

Functions receive the explicit CommandRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: handle_command.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Generator, Optional
from cursiv_engine.core.command_api import TextResult, NotebookResult, FileActionResult, MemoryResult, NotesResult, StreamResult
from cursiv_engine.core.command_api import CommandRuntime
from cursiv_engine.core.command_api import UNHANDLED
import commands_system as _system
import commands_research as _research
import commands_credentials as _credentials
import commands_extensions as _extensions
import commands_notes as _notes
import commands_services as _services
import commands_images as _images

def handle_command(runtime: CommandRuntime, raw: str, cfg: dict, history: list[dict]) -> Optional[TextResult | StreamResult]:
    """
    Returns None if `raw` isn't a recognized built-in command -- caller
    should fall through to a plain chat() call in that case.
    """
    text = raw.strip()
    if not text:
        return None
    cmd = text.lower()

    from cursiv_engine.core import turn_policy
    if turn_policy.for_text(text) != turn_policy.Policy():
        return None  # enforce limits before even classifying notebook/memory commands
    from cursiv_engine.core import command_sequence
    pair = command_sequence.state_reply(text)
    if pair is not None:
        return runtime.TextResult(pair)
    from cursiv_engine.core import file_requests
    from cursiv_engine.core import self_inspection
    if self_inspection.resolve(text,history):
        return None  # installed source precedes notebook/memory/workspace actions; no reads here
    if file_requests.recognizes(text):
        return None  # local source/search intent must precede notebook and memory keywords
    from cursiv_engine.core import profile
    if profile.letters_command(text):
        return runtime.TextResult(profile.REMOVED_NOTE)

    # Clean-up is exact and precedes memory intents, so "memory cleanup remove all"
    # can never be read as a request to forget every memory.
    from cursiv_engine.memory import cleanup as _cleanup
    if cmd.startswith(("memory cleanup", "memory clean up", "clean up memory", "cleanup memory")):
        from cursiv_engine.memory import semantic as _semantic
        _reply = _cleanup.command(text, _semantic.current_person())
        if _reply is not None:
            return runtime.TextResult(_reply)

    # Looking at itself: answered by Cursiv's own code from real records, never a model.
    if cmd.rstrip(".?!") in ("session note", "show the session note", "show session note", "session note clear",
                             "clear the session note"):
        from cursiv_engine.memory import session_notes   # U100: the note this conversation picks up from
        conv = session_notes._active.get("conv") or ""
        if "clear" in cmd:
            if conv:
                session_notes.path(conv).unlink(missing_ok=True)
            session_notes._active["note"] = ""
            return runtime.TextResult("This conversation's session note was cleared; a new one starts from here.")
        note = session_notes._active.get("note") or (session_notes.load(conv) if conv else "")
        return runtime.TextResult(note.strip() + "\n\n(session note clear starts it over.)" if note.strip() else
                                  "This conversation has no session note yet. One is written as you talk.")
    if cmd.startswith("when i say "):            # U100: "when I say the creek I mean North Creek"
        from cursiv_engine.core import guidance
        _hint = guidance.command(text)
        if _hint is not None:
            return runtime.TextResult(_hint)
    if cmd in ("self prompt", "self prompt full"):
        from cursiv_engine.core import last_turn
        return runtime.TextResult(last_turn.summary(full=cmd.endswith("full")))
    if cmd in ("self stores", "self store", "self data"):
        from cursiv_engine.core import self_stores
        from cursiv_engine.memory import semantic as _semantic
        return runtime.TextResult(self_stores.summary(_semantic.current_person()))
    if cmd.startswith(("self source", "self read", "self map")):
        from cursiv_engine.core import self_source
        _reply = self_source.command(text)
        if _reply is not None:
            return runtime.TextResult(_reply)

    # Native notebook intent takes precedence over generic files and memory.
    _notebook = runtime.notebook_command(text, history, cfg=cfg)
    if _notebook is not None:
        return _notebook
    _memory = runtime.memory_command(text, history)
    if _memory is not None:
        return _memory
    _notes_request = runtime._notes_view_request(text)
    if _notes_request is not None:
        return _notes_request if runtime._STRAND_OK else runtime.TextResult("Saved notes aren't available.")
    _note_id = runtime.re.fullmatch(r'(?:note|notes) (?:show )?([a-f0-9]{8})[.?]?', cmd)
    if _note_id:
        from saved_notes import read_notes, full_text
        try:
            records, warnings = read_notes()
            record = next((r for r in records if r.get('id') == _note_id[1]), None)
            return runtime.TextResult(f"Note {_note_id[1]}\n\n" + full_text(record) if record else 'No saved note matches that ID.')
        except (OSError, ValueError) as exc:
            return runtime.TextResult(f'Could not read saved note: {exc}')

    from cursiv_engine.core import file_access as _files
    if _files.is_request(text):
        return None                     # application-controlled file route in chat(), not the model

    # Plain names for older commands. The old names still work.
    if cmd in ("save this", "notes", "note export") or cmd.startswith(("save this ", "notes search ", "note import ")):
        for _new, _old in (("save this", "anchor this"), ("notes", "strands"),
                           ("note export", "strand export"), ("note import", "strand import")):
            if cmd.startswith(_new):
                text = _old + text[len(_new):]
                break
        cmd = text.lower()
    elif cmd.startswith("translate ") and " into " in cmd and "json" not in cmd:
        text = "babel " + text[len("translate "):]
        cmd = text.lower()

    # "help" / "help more" / "help family" -- but "help me write a letter" is chat.
    _topic = cmd[5:].strip() if cmd.startswith("help ") else None
    if _topic in ("family", "letters"):
        return runtime.TextResult(profile.REMOVED_NOTE)
    if cmd in ("help", "help?", "commands") or (_topic and (_topic in runtime._HELP_TOPICS or _topic in ("more", "all", "topics"))):
        return runtime.TextResult(runtime.help_text(_topic or ""))

    # ── Free-form notes → JSON training example ─────────────────────────
    # Fuzzy-matched, not a fixed command -- "translate my notes into JSON
    # for training", "convert this into json for training", etc. all hit
    # it. A short trigger-only message ("translate my current notes into
    # JSON format for training") means "the notes" are whatever the user
    # just said before this -- pull the prior user turn instead of trying
    # to translate the instruction sentence itself.
    for handler in (
        _system.handle,
        _research.handle,
        _credentials.handle,
        _extensions.handle,
        _notes.handle,
        _services.handle,
        _images.handle,
    ):
        result = handler(runtime, text, cmd, cfg, history)
        if result is not UNHANDLED:
            return result
    return None

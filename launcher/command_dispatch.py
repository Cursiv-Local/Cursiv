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
from command_results import TextResult, NotebookResult, FileActionResult, MemoryResult, NotesResult, StreamResult
from command_runtime import CommandRuntime
from command_runtime import UNHANDLED
import commands_system as _system
import commands_research as _research
import commands_credentials as _credentials
import commands_extensions as _extensions
import commands_notes as _notes
import commands_services as _services
import commands_postal as _postal
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
    if file_requests.recognizes(text):
        return None  # local source/search intent must precede notebook and memory keywords

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
        _postal.handle,
        _images.handle,
    ):
        result = handler(runtime, text, cmd, cfg, history)
        if result is not UNHANDLED:
            return result
    return None

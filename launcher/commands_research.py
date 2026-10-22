"""Research commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from command_runtime import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    _free_reply = runtime._free_key_command(text)
    if _free_reply is not None:
        return runtime.TextResult(_free_reply)
    from cursiv_v215.core import field_recall
    _field_recall = field_recall.command(text)
    if _field_recall is not None:
        return runtime.TextResult(_field_recall)
    from cursiv_v215.core import curiosity_engine, presence
    from cursiv_v215.memory import semantic as _sem_curiosity
    from cursiv_v215.core.paths import save_reference
    _curiosity_person = _sem_curiosity.current_person()
    _project_scope = save_reference(cfg['workspace']) if cfg.get('file_access') and cfg.get('workspace') else 'general'
    _curiosity_reply = curiosity_engine.command(text, _curiosity_person, _project_scope)
    if _curiosity_reply is not None:
        return runtime.TextResult(_curiosity_reply)
    if cmd in ('presence', 'presence status'):
        import json
        return runtime.TextResult(json.dumps(dict(identity=presence.settings(_curiosity_person),
            observed=presence.snapshot(cfg.get('workspace', ''), cfg.get('file_access', False),
                                       person=_curiosity_person)), indent=2))
    if cmd in ('style adapt on', 'style adapt off'):
        try:
            presence.configure(_curiosity_person, adapt_style=cmd.endswith(' on'))
            return runtime.TextResult('Style adaptation setting saved and verified.')
        except (OSError, ValueError) as exc:
            return runtime.TextResult(f'Style setting not confirmed: {exc}')
    try:
        from cursiv_v215.memory.semantic import memory_command as _memory_command
        _mem_reply = _memory_command(text)
    except (OSError, ValueError) as exc:
        _mem_reply = f'Memory operation could not be confirmed: {type(exc).__name__}: {exc}'
    if _mem_reply is not None:
        return runtime.TextResult(_mem_reply)
    # The paperclip: photo "<path>" <question> -- the image model reads a photo
    _pm = runtime._PHOTO_CMD.match(text.strip())
    if _pm and (runtime.Path(_pm.group(1) or _pm.group(2)).suffix.lower() in
                {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}):
        return runtime.describe_photo(_pm.group(1) or _pm.group(2), _pm.group(3), cfg)
    # The field demo: demo, demo off, demo questions (core/demo.py)
    try:
        from cursiv_v215.core import demo as _demo
        _demo_reply = _demo.command(text)
    except Exception as _exc:
        _demo_reply = f"The demo couldn't load: {_exc}" if cmd.strip() in ("demo", "load demo", "demo on") else None
    if _demo_reply is not None:
        return runtime.TextResult(_demo_reply)
    # Field notebook: log ..., field log, field log check, field log export (core/fieldlog.py)
    try:
        from cursiv_v215.core import fieldlog as _fieldlog
        from cursiv_v215.memory.semantic import current_person as _person
        _log_reply = _fieldlog.command(text, observer=_person().title())
        if _log_reply is None:
            # Team sync: field log share/import <folder>, team log (core/fieldsync.py)
            from cursiv_v215.core import fieldsync as _fieldsync
            _log_reply = _fieldsync.command(text, observer=_person().title())
    except Exception as _exc:
        _log_reply = f"Field-log operation failed: {_exc}" if runtime.re.match(r'^(log |field ?log|field notes|show field log|team log)', cmd) else None
    if _log_reply is not None:
        if _log_reply.startswith('Saved to the field log:'):
            curiosity_engine.notify(_curiosity_person, _project_scope)
        return runtime.TextResult(_log_reply)
    # The team's documents: "documents", "add document <path>" (core/documents.py)
    try:
        from cursiv_v215.core import documents as _documents
        _doc_reply = _documents.command(text)
    except Exception:
        _doc_reply = None
    if _doc_reply is not None:
        return runtime.TextResult(_doc_reply)
    if cmd in ("phases", "phase", "why that answer", "how did you decide"):
        from cursiv_v215.core.phases import last_trace_text
        return runtime.TextResult(last_trace_text())

    # ── API keys ─────────────────────────────────────────────────────────
    return UNHANDLED

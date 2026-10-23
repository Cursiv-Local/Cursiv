"""Source labels from application records, with no model-answer input."""
from .runtime import ChatRuntime


def capture_memory(runtime: ChatRuntime, messages: list[dict]) -> None:
    """Only label recalled memory when it survived final system-prompt assembly."""
    context = runtime._MEMORY_CTX
    supplied = runtime._MEMORY_RECALLED and context and any(
        row.get('role') == 'system' and isinstance(row.get('content'), str) and context in row['content']
        for row in messages)
    runtime.grounding.set_memory_sources(tuple(runtime._MEMORY_TEXTS) if supplied else ())


def sources_line(runtime: ChatRuntime) -> str:
    """Describe supplied evidence, not a claim that the model used or verified it."""
    parts = []
    if runtime._REF_SHOWN:
        ev = runtime._ref_evidence()
        sourced = {m['title'] for m in ev.values() if m['sourced']}
        bare = [t for t in dict.fromkeys(runtime._REF_SHOWN) if t not in sourced]
        parts.append('Cursiv Offline Reference (' + ', '.join(dict.fromkeys(runtime._REF_SHOWN))
                     + (f"; no published source for: {', '.join(bare)}" if bare else '')
                     + ('; none professionally reviewed' if not any(m['reviewed'] for m in ev.values()) else '')
                     + ')')
    if runtime._DOCS_SHOWN:
        pages = dict.fromkeys(f'{p.name} p. {p.page}' for p in runtime._DOCS_SHOWN)
        parts.append('Your documents (' + ', '.join(pages) + ')')
    elif runtime._DOCS_SEARCHED_EMPTY:
        parts.append('your documents searched; no matching passage found' if runtime._CURSIV_REPLY else
                     'your documents searched, nothing on this; the rest is model knowledge (not checked)')
    if runtime._WORKED:
        parts.append((f"worked out by Cursiv's code ({runtime._WORKED.tool}: {runtime._WORKED.statement})"
                      if runtime._WORKED.ok else
                      f"Cursiv's calculator ({runtime._WORKED.tool}: it refused this question — {runtime._WORKED.statement})"))
    if runtime._WEB_SEARCHED:
        parts.append('web search results')
    if runtime.grounding.executed_sources():
        parts.append('confirmed computer tool results (' + '; '.join(runtime.grounding.executed_sources()) + ')')
    if runtime.grounding.memory_sources():
        parts.append('saved memory context supplied (use by the model is not established)')
    if runtime._CURSIV_REPLY:
        return ('Sources: ' + '; '.join(parts) + '. Written by Cursiv, no AI model') if parts else \
            'Sources: Cursiv itself (no AI model)'
    if not parts:
        return 'Source: model knowledge (not checked against a source)'
    return 'Sources: ' + '; '.join(parts) + '. Wording by the AI model'

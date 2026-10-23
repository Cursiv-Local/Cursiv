"""Quoted payloads stay data; explicit mixed instructions never become one fact."""
import re

REST = 'Remaining instructions were not run. Send the next step separately.'
_NEXT = re.compile(r'(?i)(?:[.!?]\s+now\s+|,?\s+then\s+)(?='
                   r'(?:do|read|write|create|append|forget|remember|search|find|turn|list|file)\b)')


def split(text):
    if ' :: ' in text:
        return text, ''  # explicit command payload, including punctuation, is literal
    quote, masked = '', list(text)
    for i, char in enumerate(text):
        if quote:
            masked[i] = ' '
            if char == quote and (not i or text[i - 1] != '\\'):
                quote = ''
        elif char in ('"', "'") and (not i or not text[i - 1].isalnum()):
            quote = char
            masked[i] = ' '
    match = _NEXT.search(''.join(masked))
    return (text[:match.start()].strip(), text[match.end():].strip()) if match else (text, '')


def state_reply(text):
    """Small explicit version + offline command pair; no general command executor."""
    from . import turn_policy, native_answers, netgate
    first, rest = split(turn_policy.task_text(text))
    if not rest or not re.fullmatch(r'(?i)(?:turn )?offline on[.!]?', rest):
        return None
    if not re.fullmatch(r"(?i)what(?:'s| is) your version\??", first):
        return None
    version = native_answers.answer(first)
    if turn_policy.effective(text) != turn_policy.Policy():
        return version + '\n\n' + turn_policy.DENIED
    try:
        netgate.set_offline(True)
        if not netgate.is_offline():
            raise OSError('offline mode did not persist')
        return version + '\n\nOffline mode ON. External Cursiv connections are blocked; local Ollama remains available.'
    except (OSError, ValueError) as exc:
        return version + '\n\nOffline change not confirmed: ' + str(exc)

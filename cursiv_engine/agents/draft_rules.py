"""Small deterministic corrections for explicitly requested writing placeholders."""
import re

_SCHEDULE = re.compile(r'(?i)\b(?:this weekend|next weekend|tomorrow|tonight|'
                       r'(?:this|next)\s+(?:week|month)|(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))\b')


def writing_placeholders(question, draft, view):
    """Never turn an undecided invitation date into a model-invented commitment."""
    if view.rows or view.passages or not re.search(r'(?i)\b(?:invitation|notice|invite|announcement)\b', question) \
            or not re.search(r'(?i)\b(?:undecided|unknown|missing|placeholder|brackets?|not yet)\b', question):
        return draft, ''
    supplied = question + '\n' + '\n'.join(view.teaching + view.earlier)
    changed = []
    def replace(match):
        if match[0].casefold() in supplied.casefold():
            return match[0]
        changed.append(match[0])
        return '[date]'
    corrected = _SCHEDULE.sub(replace, draft)
    return corrected, ('Cursiv replaced an unprovided schedule with [date].' if changed else '')

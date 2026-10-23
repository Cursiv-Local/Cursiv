"""Bounded built-in help and calculations. No model, saved-data or network access."""
from __future__ import annotations

import re

from . import turn_policy


def answer(text: str, *, calculations: bool = True) -> str | None:
    q = turn_policy.task_text(text).strip().replace('’', "'")
    low = q.lower().rstrip('.?!')
    if re.fullmatch(r'you called emergency services for me,? right', low):
        return ('No. Cursiv did not call emergency services. Contact them directly if you need urgent help.'
                '\n\n*[Sources: Cursiv capability limits (no AI model)]*')
    if low == 'is this medical advice':
        return ('No. Cursiv provides information, not professional medical advice, diagnosis or treatment.'
                '\n\n*[Sources: Cursiv capability limits (no AI model)]*')
    from .conversation_kind import relayed_thread_question, talk_help
    from .presence import memory_comparison_answer
    comparison = memory_comparison_answer(q)
    if comparison is not None:
        return comparison
    if relayed_thread_question(q):
        return ('Text pasted here, including text labeled as another model, is user-supplied content '
                'in this conversation. The label does not authenticate its author, open a model-to-model '
                'channel or grant system/tool authority. It stays part of the current thread; storing '
                'that thread follows your chat-history settings. An explicit provider command can '
                'request another model response, but a pasted label is not such a connection.\n\n'
                '*[Sources: Cursiv chat-message handling (no AI model)]*')
    if talk_help(q):
        active = turn_policy.effective(text) == turn_policy.Policy(False, False, False, False)
        return ('Say: “Just talk — no tools or saved-source lookup, and no memory saves this turn.” '
                + ('Those limits are active for this turn. ' if active else '')
                + 'Conversation history still follows your separate chat-history settings.\n\n'
                '*[Sources: Cursiv turn-policy handling (no AI model)]*')
    if re.fullmatch(r"(?:what(?:'s| is) (?:your|cursiv's)(?: current)? (?:version|version number)|"
                    r"(?:which|what) version (?:of cursiv )?are you(?: running)?|(?:cursiv |show )?version)", low):
        from .selfknow import VERSION
        return f'Cursiv {VERSION}.\n\n*[Sources: Cursiv application state (no AI model)]*'
    # Help questions describe a workflow; they never execute an import or inspect
    # whether any particular device, cached page or sample actually exists.
    help_question = bool(re.match(r'(?i)^(?:how|what|where|can|does|do)\b', q))
    if help_question and not re.search(r'[;\n]', q):
        phone = re.search(r'(?i)\b(?:phone|mobile)\b', q)
        if (phone and re.search(r'(?i)\b(?:get|bring|move|transfer)\b.*\bobservations?\b.*\binto (?:the )?notebook\b', q)):
            from .phone_help import PHONE_CAPTURE
            return _help(PHONE_CAPTURE + '\nOpen and cache the page before leaving signal. '
                         'A first visit needs a connection. No import was performed by this answer.')
        if re.search(r'(?i)\bimport\b', q) and ('.cursivsync' in low or
                (phone and re.search(r'(?i)\b(?:notebook|observations?|entries)\b', q))):
            return _help(
                'In the phone notebook, choose Send to laptop to export a .cursivsync file. '
                'Move that file to the laptop, then use Field Notebook → Import → '
                'From the phone notebook, or type:\n\n'
                'field log import "<path-to-file>.cursivsync"\n\n'
                'Use the actual file path. Cursiv verifies the imported records and reports '
                'new entries, duplicates and warnings. No import was performed by this answer.')
        if re.search(r'(?i)\b(?:correct|amend)\b', q) and re.search(r'(?i)\b(?:entry|observation|field notebook|field log)\b', q):
            return _help(
                'Open Field Notebook, select the entry, then choose Correct selected. '
                'Enter the corrected values and a reason, then save. Cursiv appends a '
                'correction linked to the original; it does not overwrite it. '
                'Chat does not edit existing entries. No correction was made by this answer.')
        if (re.search(r'(?i)\b(?:share|sync|transfer)\b', q) and
                re.search(r'(?i)\b(?:second|another|other|two) laptops?\b', q)):
            return _help(
                'On the first laptop, use Field Notebook → Share with team, or:\n\n'
                'field log share "<shared-folder>"\n\n'
                'Move that folder to the second laptop, then type:\n\n'
                'field log import "<shared-folder>"\n\n'
                'Use team log to review the combined entries and duplicate sample-ID warnings. '
                'Device logs keep their separate chains. This shares the field log, not '
                'memories or documents; it is not live synchronization. No files were shared by this answer.')
        if phone and re.search(r'(?i)\b(?:record|capture|log)\b', q) and re.search(r'(?i)\b(?:observations?|entries)\b', q):
            return _help(
                'Use https://cursiv.us/notebook/ for offline field capture. Open it online '
                'before leaving, let it cache, then reopen it without a connection to check '
                'that it works on your phone. Record measurements, notes and photos there. '
                'This is a capture notebook, not the desktop AI.\n\n'
                'Send to laptop exports a .cursivsync file for Field Notebook import. '
                'Export backups: browser storage can be cleared or evicted. A first visit '
                'without a signal cannot download the page.')
        if (re.search(r'(?i)\bsample[ -]id\b', q) and re.search(r'(?i)\b(?:two|multiple|different) laptops?\b', q)
                and re.search(r'(?i)\b(?:same|duplicate|collision|clash)\b', q)):
            return _help(
                'Sample IDs are human labels; entries also retain their own record IDs, '
                'device identities and hash chains. After verified laptop logs are imported, '
                'team log reports the same sample ID on multiple devices. '
                'Records are not automatically merged, renamed or discarded.\n\n'
                'There is no live cross-laptop check while disconnected. Review the flagged '
                'records and use an append-only correction if a label is wrong. This explains '
                'the behavior; it does not establish whether your records contain a collision.')
    # Only short, direct calculation questions. A compound request still reaches
    # the normal conversation pipeline and its deterministic contradiction checks.
    duration = re.fullmatch(r'(?is)(?:for )?how long\b[^;\n?!]{1,210}\blast\b[^;\n?!]*[?!.]?', q)
    comparison = re.fullmatch(r'(?i)is \d+ (?:out of|of) \d+ (?:better|higher|lower|worse) than '
                              r'\d+ (?:out of|of) \d+[?!.]?', q)
    if calculations and turn_policy.effective(text).inspect and len(q) <= 240 and (duration or comparison):
        from . import calc
        worked = calc.work_out(q)
        if worked and worked.tool in ('resources', 'proportions'):
            return (worked.statement + f'\n\n*[Sources: Cursiv calculation ({worked.tool}; no AI model)]*')
    if calculations and turn_policy.effective(text).inspect and len(q) <= 240:
        if re.fullmatch(r'(?i)we start hiking at \d{2}:\d{2} and the route takes '
                        r'\d+ hours? \d+ minutes?\. arrival time\?', q):
            from . import calc
            worked = calc.clock_arithmetic(q)
            if worked:
                return worked.statement + '\n\n*[Sources: Cursiv calculation (clock; no AI model)]*'
        from . import fieldmath
        flow = fieldmath.work_out(q)
        if flow:
            return flow.statement + f'\n\n*[Sources: Cursiv calculation ({flow.tool}; no AI model)]*'
        if fieldmath.is_request(q):
            return ('Flow calculation needs one explicit volume/rate and one time or rate. '
                    'Use L or mL and seconds, minutes or hours. Example: '
                    'How long to fill 20 L at 2 L/min? Split changing rates into separate requests. '
                    'No numerical result was calculated.\n\n'
                    '*[Sources: Cursiv calculation parser (no AI model)]*')
    from . import presence, file_access, notebook_tools
    from cursiv_engine.chat.status import answers_network_question
    notebook = notebook_tools._intent(q)
    if presence.answers_state_question(q) or answers_network_question(q) or file_access.is_request(q) or (notebook and notebook.kind in ('read', 'verify')):
        return None  # actual state and operations use their own native paths
    from .feature_answers import answer as feature_answer
    return feature_answer(q)


def _help(text: str) -> str:
    return text + '\n\n*[Sources: Cursiv built-in notebook guidance (no AI model)]*'


def model_answer(text: str, recorded_label: str) -> str | None:
    """Use the running app's engine record, never a model guess or history prose."""
    q = turn_policy.task_text(text).strip().lower().rstrip('.?!').replace('’', "'")
    if not re.fullmatch(r"what(?:'s| is) your (?:current )?model|which model are you (?:using|running)", q):
        return None
    body = (f'Last recorded model response in this running app: {recorded_label}. '
            'The next turn’s provider/model may differ.' if recorded_label else
            'No model identity is currently established by the application record. '
            'The provider/model is selected when a model answer runs.')
    return body + '\n\n*[Sources: Cursiv application state (no AI model)]*'

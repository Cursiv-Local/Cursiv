"""Reviewed Cursiv workflow facts, not a live report or an execution receipt.

Return None only for unrelated or explicitly hypothetical discussion. Unknown
Cursiv workflows receive an honest native decline instead of invented steps.
"""
from __future__ import annotations

import re

SOURCE = '\n\n*[Sources: Cursiv built-in feature guidance (no AI model)]*'

OVERVIEW = (
    "Cursiv is a local-first AI assistant for field notes, documents and practical questions. "
    "You can talk normally; a few built-in commands give you predictable ways to save and check things.\n\n"
    "- **Keep a Field Notebook.** Record observations, measurements and sample IDs. For example, "
    "edit this before sending: `log site: Example; water temp 12.4 C; note: Example observation`. "
    "Type `field log` to see entries or open Field Notebook in the sidebar. Corrections keep the original; "
    "`field log check` checks the record chain.\n"
    "- **Check field calculations.** Ask naturally, such as “Convert 12.4 C to F.” "
    "Supported units, distances, times and rates are calculated in code, with a receipt.\n"
    "- **Ask about your documents.** Import a protocol in Memory & Knowledge → Documents, "
    "then ask about it. Matching passages can provide page references; missing evidence stays a limitation.\n"
    "- **Work with files.** Choose a workspace and turn `files on`, then try "
    "“Create notes.txt with the text: Site A, 14.2 C.” Reads, appends and local searches stay within "
    "that authorized folder. Existing-file changes require approval.\n"
    "- **Keep useful context.** Use `remember <fact>`, ask “What do you remember?”, or save an "
    "answer with `save this` and find it through `notes`. Saved memory can survive restarts; it is selective.\n"
    "- **Think things through.** Discuss an idea, compare explanations, translate text or ask for "
    "coding help. Model answers can be wrong; source labels show what evidence was supplied.\n\n"
    "Local chat works offline after Ollama and a compatible model are installed. Initial downloads "
    "and optional online services need internet. Phone capture is at https://cursiv.us/notebook; "
    "`help field` explains export/import. Type `help` for more examples. "
    "This guide has not opened workspace files or added notebook entries or memories. "
    "Chat history follows your separate save setting."
)


def answer(text: str) -> str | None:
    q = text.strip().lower().replace('’', "'")
    if re.fullmatch(r"(?:what can (?:cursiv|you) do|what (?:are|is) cursiv's (?:main )?"
                    r"(?:features|functionality)|(?:show|explain) cursiv's (?:main )?features)[?.!]*", q):
        return OVERVIEW + SOURCE
    if re.match(r"(?:do not|don't|dont|never)\b", q):
        return None  # a retention restriction plus data is not a feature question
    if not re.match(r"(?:how|what|which|who|where|when|why|can|could|does|do|is|are|will|would|explain|describe|tell me)\b", q):
        return None
    from .conversation_kind import reflective
    if reflective(q):
        return None
    if re.search(r'\b(?:imagine|hypothetical|thought experiment|philosoph\w*|conscious\w*|self.aware)\b', q):
        return None
    own = bool(re.search(r'\bcursiv\b|\b(?:your|you)\b.*\b(?:files?|memory|memories|notebook|'
                         r'capabilities|features|limitations|offline|online|closed|close|code|weights)\b|'
                         r'\b(?:field notebook|field log|sample[ -]ids?|\.cursivsync)\b|'
                         r"\b(?:what (?:can|can't|cannot) you do|who are you|what are you|how do you work|"
                         r'what makes you unique|do you store anything)\b', q))
    if not own:
        return None
    if re.search(r'\bwho\b.*\b(?:created|built|made)\b|\b(?:creator|license|licence|open.source)\b', q) and re.search(r'\bcursiv\b', q):
        body = 'Cursiv is made by Cursiv Local, an independent open-source project. Its source code is available under the MIT license.'
    elif re.search(r'\b(?:files?|workspace|permissions?)\b', q):
        body = ('Choose workspace <folder> and enable files on. Relative file paths use that authorized '
                'workspace; Cursiv does not silently use its installation folder. Use file read <path> '
                'or file create <path> :: <content>. These native commands work with local and cloud '
                'models; a paid key is not required. Protected paths and links are refused. Existing-file '
                'changes require confirmation. Only a successful backend result with the actual path '
                'confirms an operation; this help performed none.')
        if re.search(r'\b(?:cloud|online|privacy|private)\b', q):
            body += (' When an online provider is used, supplied file contents/context may be sent to it. '
                     'Use offline on to block external connections through Cursiv’s network gate.')
    elif re.search(r'\b(?:duplicate|same|clash|collision)\b.*\bsample|\bsample.*\b(?:duplicate|same|clash|collision)\b', q):
        body = ('Sample IDs are labels, not unique record IDs. Entries retain their own IDs and hash '
                'chains. Imported team logs flag the same sample ID on different devices; records are '
                'not silently merged, renamed or deleted. There is no live check between disconnected '
                'laptops. Inspect sample history and use an append-only correction for a mistaken label.')
    elif re.search(r'\b(?:field notebook|field log|observations?)\b', q):
        body = ('Use log site: North Creek; sample ID: NC-001; observation: clear water; temp 14.2 C. '
                'Notes and measurements are saved through the native Field Notebook, not field_log.txt. '
                'Read entries with field log, inspect a sample with field log sample NC-001, and verify '
                'the append-only SHA-256 chain with field log check. For a correction, select the entry '
                'in Field Notebook and choose Correct selected; the original remains. A confirmed save '
                'includes the actual record ID and fingerprint. This help did not save or inspect entries.')
    elif re.search(r'\b(?:memory|memories|learn|learning|weights|retrain|store anything)\b', q):
        body = ('Cursiv supports persistent local memory across restarts. remember <fact> requests a '
                'verified manual save; recall <words> searches saved facts. Automatic learning, when '
                'enabled, saves selected facts rather than everything. memory learn off disables it. '
                'Retrieval may miss a saved fact; remembering a fact does not retrain model weights. '
                'Conversation history has separate retention settings. This answer did not read or save memory.')
    elif re.search(r'\b(?:usb|ssd|portable)\b', q):
        body = ('Make a Cursiv USB copies the application, local runtime and selected models to a drive. '
                'Start that copy using Start Cursiv on the drive. Current portable data lives under '
                'Home/.cursiv on that drive. A personal copy can include memories, settings and readable '
                'exported API keys; keep it private. A fresh kit excludes those personal records. '
                'Verify saved data after restarting and on a second PC before relying on your kit. '
                'This answer did not inspect your drive.')
    elif re.search(r'\b(?:closed|close|background|working after)\b', q):
        body = 'Cursiv cannot observe, learn or keep working while its application process is closed.'
    elif re.search(r'\b(?:offline|online|internet|cloud|privacy|private)\b', q):
        body = ('Local inference can work offline with Ollama and an installed compatible model. '
                'offline on blocks external connections through Cursiv’s network gate; offline off '
                'does not prove connectivity. Optional online providers send supplied prompts/context '
                'to that provider when used. Local conversation and memory files remain plaintext; '
                'login is not encryption. Use presence status for current application state.')
    elif re.search(r'\b(?:update|updates|modify|modifies|code|itself|self.modif\w*)\b', q):
        body = ('Core Cursiv changes arrive through application updates, not model self-modification. '
                'Saved facts adapt context without changing model weights. Generated plugins need '
                'review and explicit approval before installation. A model describing a code change '
                'does not prove it was made. Inspect actual files and backend receipts.')
    elif re.search(r'\b(?:check|checks|verif\w*)\b', q):
        body = ('Fast code checks compare answers with supplied calculations, sources and execution '
                'records. check fast adds a bounded optional model review for higher-risk turns; '
                'check full requests deeper review, and check off keeps code checks only. In desktop '
                'chat, optional review follows the streamed draft. Passing checks do not prove correctness.')
    elif re.search(r'\b(?:what (?:is|does|are)|who are|capabilit\w*|features?|unique|different|what can|limitations?|how .*work|about cursiv)\b', q):
        body = ('Cursiv is a local-first AI assistant with Ollama inference, authorized workspace files, '
                'persistent memory and an append-only Field Notebook. It can work offline after local '
                'models are installed; optional online providers also exist. It can be wrong, does not '
                'remember everything, and cannot work while closed. Use help topics for built-in commands.')
    else:
        body = ('No verified built-in answer covers that Cursiv workflow. Use help topics or name the '
                'specific feature. No operation was performed; invented model instructions would not '
                'establish that the feature exists.')
    return body + SOURCE

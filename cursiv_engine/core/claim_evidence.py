"""
Claims of verification must be backed by a record (U99).

The model may not say it inspected the source, that a live report or the tests
confirm something, or that a claim is "fully verified", unless core/evidence_log.py
holds a matching record from this turn. Its own earlier answers are never evidence.

Three entry points:
  * unbacked(answer)        -- verification claims in an answer with no record behind them;
  * correction(answer)      -- the note Cursiv adds under such an answer;
  * answer(question, history) -- model-free replies to "have you inspected your source?"
                               and "you said … — check that claim".
"""
from __future__ import annotations

import re

from . import capabilities, evidence_log

# What a verification claim looks like, and which evidence kinds could back it.
_CLAIMS = (
    (re.compile(r"(?i)\b(?:i|we|cursiv)\s+(?:have\s+|has\s+)?(?:just\s+)?(?:checked|inspected|reviewed|read|examined|"
                r"looked at|scanned|audited)\s+(?:the\s+|my\s+|its\s+|your\s+|cursiv'?s\s+)?(?:own\s+)?"
                r"(?:source(?:\s+code)?|code(?:base)?|source files?|files?|modules?)\b"),
     {evidence_log.SOURCE_SEARCH, evidence_log.SOURCE_READ}, "inspecting Cursiv's source"),
    (re.compile(r"(?i)\b(?:verified|substantiated|confirmed|supported|proven|proved)\s+(?:directly\s+)?(?:by|from|in|against)\s+"
                r"(?:the\s+)?(?:live report|source(?:\s+code)?|source files?|code(?:base)?|operational observations|tests?)\b"),
     {evidence_log.SOURCE_SEARCH, evidence_log.SOURCE_READ, evidence_log.CAPABILITY, evidence_log.LIVE_STATE},
     "verification against Cursiv's records"),
    (re.compile(r"(?i)\bthe (?:live report|source code|operational observations) (?:confirms?|shows?|proves?)\b"),
     {evidence_log.SOURCE_SEARCH, evidence_log.SOURCE_READ, evidence_log.CAPABILITY, evidence_log.LIVE_STATE,
      evidence_log.SOURCE_SUPPLIED},
     "a confirming report or source"),
    (re.compile(r"(?i)\bthe tests (?:prove|show|confirm|pass)\b|\btests? (?:have )?passed\b"),
     set(), "test results"),                  # no runtime test record exists, so never backed in chat
    (re.compile(r"(?i)\b(?:fully|independently)\s+verified\b|\bis\s+verified\b|\bno (?:earlier )?error exists\b|"
                r"\bno correction is needed\b"),
     {evidence_log.SOURCE_READ, evidence_log.CAPABILITY, evidence_log.LIVE_STATE}, "verification"),
)


def _assertion_text(text: str) -> str:
    """Literal examples are data; surrounding execution assertions remain visible."""
    text = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?(?:^\s*\1\s*$|\Z)', ' ', text or '')
    text = re.sub(r'(?m)^\s*>.*$', ' ', text)
    return re.sub(r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`', ' ', text)


def _asserted(text, match):
    before = re.split(r'[.!?;\n]', text[:match.start()])[-1]
    return not (re.search(r"(?i)\b(?:not|never|cannot|can't|isn't|wasn't|didn't)\s+(?:\w+\s+){0,3}$", before)
                or re.search(r'(?i)\b(?:if|unless|suppose|hypothetically|for example)\b', before))


def unbacked(answer: str, records: list | None = None) -> list[str]:
    """Each kind of verification the answer claims that this turn's records don't support."""
    have = evidence_log.kinds(evidence_log.this_turn() if records is None else records)
    out = []
    text = _assertion_text(answer)
    for pattern, needs, what in _CLAIMS:
        matches=[m for m in pattern.finditer(text) if _asserted(text,m)]
        if what=='verification':
            # A mathematical consistency assertion is not a claim that a tool,
            # external source or independent observer verified it. Arithmetic
            # remains checked separately by verify.arithmetic_problems.
            matches=[m for m in matches if not (m.group().lower()=='is verified' and re.search(
                r'(?i)\b(?:arithmetic|equation|algebra|equality)\s*$',text[max(0,m.start()-45):m.start()]))]
        if matches and not (needs & have):
            out.append(what)
    return list(dict.fromkeys(out))


def correction(answer: str, records: list | None = None) -> str:
    missing = unbacked(answer, records)
    if not missing:
        return ""
    return ("**Cursiv's check:** this answer claims " + " and ".join(missing) + ", but Cursiv has no record of "
            "that happening for this answer. Treat those parts as unverified. Ask \"have you inspected your source "
            "code?\" to see what Cursiv actually read, or self source <words> to look.")


# ── absolute privacy promises and fiction about Cursiv ───────────────────────

_ABSOLUTE = re.compile(
    r"(?i)\bno risk\b|\b(?:no|zero) data (?:ever )?leaves\b|\bnothing (?:ever )?leaves\b|\bno data ever\b|"
    r"\bno cloud\b|\bno tracking\b|\bno inference leaks?\b|\bno outside access\b|\b100\s?% (?:private|offline|secure)\b|"
    r"\b(?:completely|fully|totally) (?:private|secure|offline)\b|\bnever (?:goes|connects|talks to the) (?:online|internet)\b|"
    r"\beverything (?:i do |you do )?stays on your (?:computer|machine|device)\b|\bno internet (?:needed|required)\b|"
    r"\bno data shared\b")
_CURSIV = re.compile(r"(?i)\bcursiv\b|\b(?:i|my|me)\b.{0,40}\b(?:run|runs|running|local|computer|machine)\b")


def _privacy_assertion(answer: str) -> bool:
    answer = _assertion_text(answer)
    for match in _ABSOLUTE.finditer(answer or ''):
        start=max(answer.rfind(mark,0,match.start()) for mark in ('.','!','?',';','\n'))+1
        before=answer[start:match.start()]
        if re.search(r"(?i)\b(?:not|isn't|aren't|cannot guarantee|can't guarantee|cannot promise|can't promise|not necessarily)\s+(?:\w+\s+){0,3}$",before):
            continue
        after=answer[match.end():match.end()+60]
        if match.group().lower()=='no cloud':
            if re.match(r'(?i)\s+(?:API\s+)?(?:key|credential|provider)\b',after):
                continue
            if re.search(r'(?i)\b(?:when|while|if|with)\b.{0,45}\boffline (?:mode|switch)\b.{0,20}\b(?:on|enabled|active)\b',before):
                continue
        return True
    return False


def privacy_overclaim(answer: str, question: str = "") -> str:
    """A correction when an answer about Cursiv makes an absolute privacy promise."""
    from . import last_turn
    triggered=_privacy_assertion(answer) and bool(_CURSIV.search(answer or '') or _CURSIV.search(question or ''))
    last_turn.diagnostic_event('guardian',check='privacy_overclaim',triggered=triggered)
    if not triggered:
        return ""
    try:
        from . import netgate
        now = ("Offline mode is on right now, so Cursiv refuses every connection off this computer."
               if netgate.is_offline() else
               "Offline mode is off right now; see the status pill for what can go online.")
    except Exception:
        now = "Cursiv couldn't read the current network setting."
    return ("**Cursiv's check:** an absolute privacy promise above isn't something Cursiv can guarantee. What's "
            "true: conversations, memories and the notebook are stored (encrypted) on this computer; Cursiv goes "
            "online only through features the person turns on (online AI keys, Cursiv Cloud, web search, update "
            "checks, the phone link); installing Ollama, models and updates needs the internet. " + now)


def fiction_label(question: str) -> str:
    from cursiv_engine.chat.response_style import ABOUT_CURSIV, DRAFT, FICTION
    q = question or ""
    if DRAFT.search(q) and FICTION.search(q) and ABOUT_CURSIV.search(q):
        return ("*Fiction: any programs, teams, guides or support channels named above are invented for this text "
                "and are not real Cursiv features or services.*")
    return ""


# ── model-free answers ───────────────────────────────────────────────────────

_INSPECTED = re.compile(r"(?i)\b(?:have|did)\s+you\s+(?:actually\s+)?(?:inspect|check|read|look at|examine|review|verify)"
                        r"\w*\s+(?:your|the|cursiv'?s)?\s*(?:own\s+)?(?:source|code|files|tests)")
_RECHECK = re.compile(r"(?i)\b(?:you|cursiv)\s+(?:previously\s+|earlier\s+|just\s+)?(?:said|stated|claimed|told me)\b|"
                      r"\bin your previous answers?\b|\bearlier you said\b")
_CHECK_WORDS = re.compile(r"(?i)\b(?:check|review|verify|re-?examine|look again|is that (?:true|right)|correct)\b")

# Earlier claims people ask to recheck, mapped to the capability that settles them.
_CLAIM_TOPICS = (
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}(?:update|updater|updates)\b|\bupdate mechanism\b|\bupdater\b"), "updater"),
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}online services?\b|\bonline services?\b|\bno cloud\b|\bonline ai\b"), "online_ai"),
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}(?:external )?dependenc\w*\b|\bexternal dependenc\w*\b"), "dependencies"),
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}web search\b|\bcan'?t search\b"), "web_search"),
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}encryption\b|\bnot encrypted\b"), "encryption"),
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}plugins?\b"), "plugins"),
    (re.compile(r"(?i)\bno (?:\w+ ){0,2}agents?\b"), "agents"),
)


def answer(question: str, history: list[dict] | None = None) -> str | None:
    q = (question or "").strip()
    if _INSPECTED.search(q):
        return _inspection_report()
    if _RECHECK.search(q) and _CHECK_WORDS.search(q):
        topics = [key for pattern, key in _CLAIM_TOPICS if pattern.search(q)]
        if not topics and history:
            last = next((m.get("content", "") for m in reversed(history) if m.get("role") == "assistant"), "")
            topics = [key for pattern, key in _CLAIM_TOPICS if pattern.search(str(last))]
        if topics:
            return _recheck(list(dict.fromkeys(topics)))
    return None


def _inspection_report() -> str:
    records = [r for r in evidence_log.session() if r.kind in (evidence_log.SOURCE_SEARCH, evidence_log.SOURCE_READ)]
    supplied = sum(r.kind == evidence_log.SOURCE_SUPPLIED for r in evidence_log.session())
    also = (f" (For questions about Cursiv, it did hand the AI model some matching lines automatically "
            f"{supplied} time(s); that's material the model was given, not an inspection that verified a claim.)"
            if supplied else "")
    if not records:
        return ("No. Cursiv has no record of inspecting its own source code in this session, so any earlier statement "
                "that something was \"verified from the source\" wasn't backed by an inspection." + also +
                " To look now: self source <words> or self map <words>, then self read <path>." + _SRC)
    seen = list(dict.fromkeys(f"{r.path} ({'lines ' + r.lines if r.lines else 'matches'}; {r.operation})" for r in records))
    return ("Yes, but only these parts, in this session:\n" + "\n".join(f"- {s}" for s in seen[:12]) +
            "\n\nThat shows what the code says in those lines, not that a feature ran, and nothing beyond them was "
            "inspected." + _SRC)


def _recheck(keys: list[str]) -> str:
    rows = []
    for key in keys:
        c = capabilities.BY_KEY[key]
        evidence_log.record(evidence_log.CAPABILITY, "capability records", path=", ".join(c.code),
                            operation=f"recheck of an earlier claim about {c.name}")
        if c.support in (capabilities.SUPPORTED, capabilities.OPTIONAL):
            verdict = (f"**False.** Cursiv does have this — {c.name.lower()}: {c.support}. {c.summary}")
        elif c.support == capabilities.REMOVED:
            verdict = f"**True now, but it existed before.** {c.summary}"
        else:
            verdict = f"**True.** {c.summary}"
        state = f" Right now: {c.state()}." if c.state is not None else ""
        backing = (" Evidence: Cursiv's capability records, which name " + ", ".join(f"`{p}`" for p in c.code) + "."
                   if c.code else " Evidence: Cursiv's capability records.")
        rows.append(f"- Earlier claim about {c.name.lower()}: {verdict}{state}{backing}")
    return ("Checking those claims against Cursiv's own records:\n" + "\n".join(rows) +
            "\n\nWhere an earlier answer said otherwise, it was wrong: a setting that is off, or offline mode being "
            "on, doesn't mean the feature doesn't exist. These records show what the application supports and its "
            "current settings; they don't show that a feature ran." + _SRC)


_SRC = "\n\n*[Sources: Cursiv's evidence log and capability records (no AI model)]*"

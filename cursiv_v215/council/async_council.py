"""
Cursiv Council -- the canonical council behind "council <question>" (terminal),
the desktop chat window, and chat_app.py::_call_provider_council.

Cursiv runs the question through its own agents (council/agents.py): each
seat is one advising agent -- its role, its question, its knowledge -- and the
AI providers are only the engines those seats run on: paid keys, the user's
free Gemini/Groq keys, local Ollama, and Cursiv Cloud as a last resort. Seats
are spread across the available engines; a seat whose engine fails moves to
the next working one. Cursiv's synthesizing agents (Shield, Lens, Builder,
Balance) then combine the seats into one answer, on local Ollama when it's
available, otherwise the best engine that answered.

Signal mode: 4 seats, short answers, one round.
Full mode (/full, /deliberate, trigger phrases, or territory gate): 7 seats,
plus a refinement round in which every seat sees the others' answers.
Seats that score too low (core/quality_scorer.py) are left out of synthesis.
council_memory feeds prior conclusions in and records each new synthesis.

Distinct from the Persona Council (council/deliberation.py), which runs the
named roles through a single model in one pass.
"""
from __future__ import annotations

try:
    from cursiv_v215.guardian.identity_core import wrap as _identity_wrap
except ImportError:
    def _identity_wrap(s: str) -> str: return s

try:
    from cursiv_v215.core.quality_scorer import score_response as _score_response, format_scores as _format_scores
    _SCORER_OK = True
except ImportError:
    _SCORER_OK = False
    def _score_response(*a, **kw): return {"avg": 70}   # type: ignore[misc]
    def _format_scores(*a, **kw): return ""              # type: ignore[misc]

_LOW_QUALITY_THRESHOLD = 30   # below this avg score, exclude from synthesis entirely

import json
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# ── ANSI palette ──────────────────────────────────────────────────────────────
_R   = "\033[0m"
_DIM = "\033[2m"
_B   = "\033[1m"
_CYN = "\033[96m"    # xAI Grok
_GRN = "\033[92m"    # OpenAI
_GLD = "\033[93m"    # Anthropic
_WHT = "\033[97m"    # Synthesis
_MAG = "\033[95m"    # Council chrome
_RED = "\033[91m"
_BLU = "\033[94m"



_SIGNAL_CHARS = 800    # ~150–200 tokens — signal extraction threshold

# ── Full mode trigger sets ────────────────────────────────────────────────────
_FULL_PREFIXES = {"/full ", "/deliberate "}

_FULL_PHRASES  = frozenset({
    "show your reasoning",
    "full deliberation",
    "deliberate completely",
    "explain how you reached",
    "i need to understand the entire",
    "walk me through",
    "what does the council actually think",
    "don't summarize",
    "do not summarize",
    "full context",
    "complete reasoning",
    "verify completely",
    "full verification",
    "clear verification",
    "show me everything",
    "nothing trimmed",
    "full token",
    "full response",
    "show the work",
    "show your work",
    "no signal cut",
    "all of it",
    "i want to understand",
    "full council",
    "complete deliberation",
})


# ── Result dataclass ──────────────────────────────────────────────────────────
@dataclass
class CouncilResult:
    query:             str
    mode:              str             # "signal" | "full"
    providers_used:    list[str]       # provider names that responded
    signals:           dict[str, str]  # provider_name → extracted signal text
    full_texts:        dict[str, str]  # provider_name → complete response text
    synthesis:         str
    full_triggered_by: str             # "prefix" | "phrase" | "territory" | "manual" | ""
    duration_s:        float


# ── Mode detection ────────────────────────────────────────────────────────────

def detect_full_mode(raw_query: str) -> tuple[bool, str, str]:
    """
    Returns (is_full, cleaned_query, trigger_reason).
    Strips /full or /deliberate prefix from the returned query when detected.
    """
    ql = raw_query.lower().strip()
    for prefix in _FULL_PREFIXES:
        if ql.startswith(prefix.lstrip("/")):       # e.g. "full ..." without slash
            return True, raw_query[len(prefix):].strip(), "prefix"
        if ql.startswith(prefix):                   # e.g. "/full ..."
            return True, raw_query[len(prefix):].strip(), "prefix"
    for phrase in _FULL_PHRASES:
        if phrase in ql:
            return True, raw_query, "phrase"
    return False, raw_query, ""


def _territory_full_required(query: str) -> bool:
    """Return True if the query matches strands in a full_token_required territory."""
    try:
        from cursiv_v215.core.strand_store import load_territories, search_strands
        territories = load_territories()
        full_t = {n for n, t_cfg in territories.items() if t_cfg.get("full_token_required")}
        if not full_t:
            return False
        for strand in search_strands(query, top_k=5, min_score=0.15):
            if strand.get("territory_tag") in full_t:
                return True
    except Exception:
        pass
    return False


# ── Engines ───────────────────────────────────────────────────────────────────
# The council isn't a poll of AI providers. Cursiv runs its own agents
# (cursiv_v215/council/agents.py): each seat is one advising agent with its
# own role, question and knowledge, and the AI providers are just the engines
# those seats run on -- whichever are available on this machine. Cursiv's
# synthesizing agents then combine the seats into one answer.
#
# Engine order: paid keys, the user's own free Gemini/Groq keys, local Ollama
# (when it has a model), and Cursiv Cloud only as a last resort when fewer
# than two other engines exist (it's rate-limited and shared).

_ENGINE_COLORS = {"xai": _CYN, "openai": _GRN, "anthropic": _GLD, "gemini": _BLU,
                  "groq": _RED, "ollama": _WHT, "cloud": _MAG}


def _engines(cfg: dict) -> list[dict[str, Any]]:
    from cursiv_v215.ui import chat_app as ca

    out: list[dict[str, Any]] = []
    online = ca._is_online()      # checked once: offline -> only local engines

    def add(eid: str, name: str, short: str, call: Callable) -> None:
        if eid != "ollama" and not online:
            return
        out.append({"id": eid, "name": name, "short": short, "color": _ENGINE_COLORS[eid], "call": call,
                    "local": eid == "ollama"})

    key = (cfg.get("api_key") or "").strip()
    if key:
        add("xai", "xAI Grok", "GRK", lambda m, mt, k=key: ca._call_xai_stream(m, k, False, mt))
    key = (cfg.get("openai_key") or "").strip()
    if key:
        add("openai", "OpenAI", "OAI", lambda m, mt, k=key: ca._call_openai_direct(m, k))
    key = (cfg.get("anthropic_key") or "").strip()
    if key:
        add("anthropic", "Claude", "CLD", lambda m, mt, k=key: ca._call_claude_direct(m, k))
    key = (cfg.get("gemini_key") or ca._saved_key("gemini_key")).strip()
    if key:
        add("gemini", "Gemini", "GEM", lambda m, mt, k=key: ca._call_gemini_direct(m, k, mt))
    key = (cfg.get("groq_key") or ca._saved_key("groq_key")).strip()
    if key:
        add("groq", "Groq", "GRQ", lambda m, mt, k=key: ca._call_groq_direct(m, k, mt))
    if ca._local_model_ready():
        add("ollama", "Local (Ollama)", "LOC", lambda m, mt: ca._call_ollama(m, max_tokens=mt))
    if len(out) < 2 and ca.cloud_enabled():
        add("cloud", "Cursiv Cloud", "CC", lambda m, mt: ca._call_cursiv_cloud(m, mt))
    return out


def council_available(cfg: dict) -> bool:
    """True when the council has at least one engine to run on. Cheap check --
    no network calls (local Ollama counts if it's installed)."""
    try:
        from cursiv_v215.ui import chat_app as ca
    except Exception:
        return False
    if any((cfg.get(k) or "").strip() for k in ("api_key", "openai_key", "anthropic_key")):
        return True
    if ca._saved_key("gemini_key") or ca._saved_key("groq_key") or ca.cloud_enabled():
        return True
    import shutil
    return bool(shutil.which("ollama"))


_NOTICE_RE = re.compile(r"^\s*\*\[[^\]]*\]\*\s*")   # e.g. Cursiv Cloud's first-use notice


# One local model can only think about one thing at a time; parallel requests
# just queue inside Ollama until they time out. Local seats take turns instead.
_LOCAL_LOCK = threading.Lock()

_TRANSIENT = ("timed out", "timeout", "busy", "429", "503", "502", "overload", "temporarily", "no reply", "unavailable")


def _is_transient(err: str) -> bool:
    e = (err or "").lower()
    return any(t in e for t in _TRANSIENT)


def _ask(engine: dict, messages: list[dict], max_tokens: int) -> tuple[str, str | None]:
    """Run one engine to completion. Returns (text, error)."""
    from cursiv_v215.ui import chat_app as ca
    try:
        if engine.get("local"):
            with _LOCAL_LOCK:
                text = "".join(c for c in engine["call"](messages, max_tokens) if c != ca.RATE_SENTINEL)
        else:
            text = "".join(c for c in engine["call"](messages, max_tokens) if c != ca.RATE_SENTINEL)
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"[:160]
    text = _NOTICE_RE.sub("", text).strip()
    if not text:
        return "", "busy or no reply"
    if text.startswith(ca._PROVIDER_ERROR_PREFIXES):
        return "", text.strip("[]")[:160]
    return text, None


# ── Seats ─────────────────────────────────────────────────────────────────────

# Advising agents in the order seats are filled.
_SEAT_ORDER = ("Depth", "Anchor", "Spark", "Horizon", "Forge", "Story", "Speed", "Cosmos", "Echo", "Pulse")


_FACTS_FILE = Path(__file__).with_name("cursiv_facts.md")


def _grounding(query: str) -> str:
    """What Cursiv really is, plus the user's saved notes that match the question."""
    parts = []
    try:
        parts.append(_FACTS_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        pass
    try:
        from cursiv_v215.ui import chat_app as ca
        mem = ca._build_strand_context(query, top_k=3)
        if mem and mem.strip():
            parts.append("The user's own saved notes that match this question:\n" + mem.strip())
    except Exception:
        pass
    return "\n\n".join(parts)


def _seat_system(agent: "CouncilAgent", full_mode: bool, grounding: str = "") -> str:
    # A genuine role brief, not an identity override: the engine is told what
    # Cursiv is and which seat it's powering, never told to claim to be a
    # different AI (models correctly refuse that as jailbreak-shaped).
    length = "Up to about 300 words." if full_mode else "Keep it under about 150 words."
    return (
        "You are serving as one seat on Cursiv's council. Cursiv is a personal, local-first AI "
        "system built by Joshua Winkler. It doesn't answer with a single model: it routes each "
        "council question through its own architecture of named agents, runs each agent's seat "
        "on whichever AI engines are available (you are one of them), and its synthesizing "
        "agents then combine the seats into Cursiv's one answer.\n\n"
        f"This seat is {agent.name} — {agent.role}.\n"
        f"The question this seat always asks: {agent.question}\n"
        + (f"How this seat thinks: {agent.knowledge}\n" if agent.knowledge else "")
        + "\nAnswer the user's question strictly through this seat's lens, in your own voice. "
        "You are not being asked to claim to be Cursiv or any other AI -- you are the engine for "
        "this one seat. Be concrete and substantive; skip preamble. " + length
        + ("\n\nGround truth -- use it, and never contradict it:\n" + grounding if grounding else "")
        + "\n\nIf the facts above don't cover something about Cursiv or the user, say you don't know "
          "instead of inventing features, history or details."
    )


def _plan_seats(engines: list[dict], full_mode: bool) -> list[dict]:
    from cursiv_v215.council.agents import COUNCIL_BY_NAME
    target = 7 if full_mode else 4
    if all(e.get("local") for e in engines):
        target = 4 if full_mode else 3        # one local model answers seats one at a time
    count = max(1, min(target, max(3, len(engines) * 3)))
    seats = []
    for i, name in enumerate(_SEAT_ORDER[:count]):
        seats.append({"agent": COUNCIL_BY_NAME[name], "engine_index": i % len(engines)})
    return seats


def _run_seat(seat: dict, engines: list[dict], messages_for, max_tokens: int,
              bad: set, lock: threading.Lock) -> dict:
    """Run a seat on its assigned engine; if that engine fails, move the seat
    to the next working engine. Engines that fail are skipped by later seats."""
    tried: list[str] = []
    n = len(engines)
    for step in range(n):
        engine = engines[(seat["engine_index"] + step) % n]
        with lock:
            if engine["id"] in bad:
                continue
        text, err = _ask(engine, messages_for(seat), max_tokens)
        if err is None:
            return {**seat, "engine": engine, "text": text, "tried": tried}
        tried.append(f"{engine['short']}: {err}")
        if not _is_transient(err):          # bad key, offline, refused -> skip it for the rest of the run
            with lock:
                bad.add(engine["id"])
    # Every engine failed; if a local one failed only temporarily, give it one more turn.
    local = next((e for e in engines if e.get("local") and e["id"] not in bad), None)
    if local is not None:
        text, err = _ask(local, messages_for(seat), max_tokens)
        if err is None:
            return {**seat, "engine": local, "text": text, "tried": tried}
        tried.append(f"{local['short']} (retry): {err}")
    return {**seat, "engine": None, "text": "", "tried": tried}


def _run_round(seats: list[dict], engines: list[dict], messages_for, max_tokens: int,
               write_fn: Callable[[str], None], bad: set, round_label: str = "") -> list[dict]:
    """All seats in parallel; each one is shown as soon as it finishes."""
    import concurrent.futures as cf
    lock = threading.Lock()
    results: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=len(seats)) as pool:
        futures = [pool.submit(_run_seat, s, engines, messages_for, max_tokens, bad, lock) for s in seats]
        for fut in cf.as_completed(futures):
            r = fut.result()
            results.append(r)
            agent = r["agent"]
            if r["engine"] is None:
                write_fn(f"\n  {_DIM}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{_R}\n"
                         f"  {_RED}⬡ {round_label}{agent.name} — no engine could answer "
                         f"({'; '.join(r['tried'])}){_R}\n")
                continue
            eng = r["engine"]
            moved = f"  {_DIM}(moved here: {'; '.join(r['tried'])}){_R}" if r["tried"] else ""
            write_fn(
                f"\n  {_DIM}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{_R}\n"
                f"  {eng['color']}{_B}⬡ {round_label}{agent.name}{_R}  {_DIM}{agent.role} · via {eng['name']}{_R}{moved}\n\n"
                f"  {eng['color']}{r['text']}{_R}\n"
            )
    order = {id(s["agent"]): i for i, s in enumerate(seats)}
    return sorted(results, key=lambda r: order[id(r["agent"])])


def _score_seats(query: str, results: list[dict], write_fn: Callable[[str], None]) -> dict[str, dict]:
    scores = {r["agent"].name: _score_response(query, r["text"], provider=r["engine"]["id"])
              for r in results if r["engine"] is not None}
    if _SCORER_OK and scores:
        write_fn(f"\n  {_DIM}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{_R}")
        for r in results:
            if r["engine"] is not None:
                write_fn(f"\n  {r['engine']['color']}{r['agent'].name}{_R}{_format_scores(scores[r['agent'].name])}")
        write_fn("\n")
    return scores


# ── Synthesis ─────────────────────────────────────────────────────────────────

def _synthesize(query: str, signals: dict[str, str], engines: list[dict], answered: list[str],
                full_mode: bool, prior_wisdom: str, write_fn: Callable[[str], None], grounding: str = "") -> str:
    """Cursiv's synthesizing agents combine the seats. Runs on local Ollama when
    it's available (private, local-first), otherwise the best engine that
    answered, falling back through the rest."""
    from cursiv_v215.council.agents import SYNTHESIZING_AGENTS
    voices = ", ".join(f"{a.name} ({a.role.lower()})" for a in SYNTHESIZING_AGENTS)
    seats_blk = "\n\n".join(f"[{name}]\n{text.strip()}" for name, text in signals.items() if text.strip())
    wisdom = f"\n\nWhat Cursiv's council concluded on related questions before:\n{prior_wisdom}" if prior_wisdom else ""
    system = (
        "You are writing the final answer that Cursiv gives the user. Cursiv is a personal, "
        "local-first AI system built by Joshua Winkler; it just ran the user's question through "
        "its council of agents, each seat powered by a different AI engine. Its synthesizing "
        f"agents -- {voices} -- now combine the seats into one answer.\n\n"
        "Where the seats agree, state the conclusion and why it holds. Where they conflict, "
        "name the tension and resolve it. If one seat saw something the others missed, keep it. "
        "Shield checks what could break, Lens removes ambiguity, Builder turns it into concrete "
        "next steps, Balance makes sure nothing is pushed too far in one direction.\n\n"
        "Answer the user directly and usefully, in Cursiv's voice. Don't list the seats or "
        "describe the process. " + ("Be thorough." if full_mode else "Aim for a focused answer of a few paragraphs.")
        + " Use only claims the seats or the ground truth below support; if they disagree with the ground truth, "
          "the ground truth wins. Never invent features or facts about Cursiv or the user."
        + ("\n\nGround truth:\n" + grounding if grounding else "")
    )
    user = f"The user asked:\n{query}\n\nCouncil seats:\n\n{seats_blk}{wisdom}"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    by_id = {e["id"]: e for e in engines}
    order = (["ollama"] if "ollama" in by_id else []) + [i for i in answered if i != "ollama"] + \
            [e["id"] for e in engines if e["id"] not in answered and e["id"] != "ollama"]
    from cursiv_v215.ui import chat_app as ca
    for eid in dict.fromkeys(order):
        engine = by_id[eid]
        collected: list[str] = []
        try:
            for chunk in engine["call"](messages, 3000 if full_mode else 2000):
                if chunk == ca.RATE_SENTINEL:
                    continue
                if not collected and (chunk.strip().startswith(ca._PROVIDER_ERROR_PREFIXES) or not chunk.strip()):
                    if chunk.strip():
                        collected = []
                        break
                    continue
                chunk = _NOTICE_RE.sub("", chunk) if not collected else chunk
                collected.append(chunk)
                write_fn(chunk)
        except Exception:
            collected = []
        text = "".join(collected).strip()
        if text:
            write_fn(f"\n\n  {_DIM}synthesized via {engine['name']}{_R}")
            return text
    msg = f"[Synthesis unavailable -- no engine could write it. The seats' answers are above.]"
    write_fn(f"  {_RED}{msg}{_R}")
    return msg


def _anchor_check(query: str, synthesis: str, signals: dict[str, str], grounding: str,
                  engines: list[dict], write_fn: Callable[[str], None]) -> None:
    """Anchor's grounding check on the final answer: list claims that neither a
    seat nor the ground truth supports. Shown under the answer; never rewrites it."""
    seats = "\n\n".join(f"[{n}]\n{t[:1500]}" for n, t in signals.items())
    messages = [
        {"role": "system", "content":
            "You are Anchor, Cursiv's grounding check. Compare a final answer against its sources. "
            "List only specific factual claims in the answer that are NOT supported by the sources "
            "(especially invented features, history, numbers or details about Cursiv or the user). "
            "Opinions, advice and suggestions are fine -- don't list those. "
            "Reply with exactly 'GROUNDED' if nothing is unsupported; otherwise reply with up to 4 lines, "
            "each starting with '- ', quoting the unsupported claim briefly."},
        {"role": "user", "content": f"Question: {query}\n\nSources -- ground truth:\n{grounding}\n\n"
                                    f"Sources -- council seats:\n{seats}\n\nFinal answer to check:\n{synthesis}"},
    ]
    order = [e for e in engines if e.get("local")] + [e for e in engines if not e.get("local")]
    for engine in order:
        text, err = _ask(engine, messages, 300)
        if err is None:
            verdict = text.strip()
            if verdict.upper().startswith("GROUNDED"):
                write_fn(f"\n  {_GRN}⬡ Anchor check: every claim is supported by the council or Cursiv's facts.{_R}\n")
            else:
                lines = [l.strip() for l in verdict.splitlines() if l.strip().startswith("-")][:4]
                if lines:
                    write_fn(f"\n  {_GLD}⬡ Anchor check — not supported by the sources, treat with care:{_R}\n"
                             + "".join(f"  {_GLD}{l}{_R}\n" for l in lines))
            return


# ── Entry point ───────────────────────────────────────────────────────────────

def run_council(
    raw_query:  str,
    cfg:        dict,
    *,
    force_full: bool | None = None,
    write_fn:   Callable[[str], None] | None = None,
) -> CouncilResult | None:
    """
    Run a question through Cursiv's council. Used directly by chat_cli.py and,
    through a thread+queue bridge, by the desktop chat window and chat_app.py.

    force_full:  True  -> full deliberation (more seats + a refinement round)
                 False -> signal mode
                 None  -> auto-detect from the query (default)
    write_fn:    None  -> print to stdout; otherwise every line goes through it.
    """
    _out = write_fn if write_fn is not None else (
        lambda text: (sys.stdout.write(text), sys.stdout.flush())
    )

    phrase_full, query, trigger = detect_full_mode(raw_query)
    if force_full is not None:
        full_mode = force_full
        trigger = "manual" if force_full else ""
    else:
        full_mode = phrase_full
    if not full_mode and _territory_full_required(query):
        full_mode = True
        trigger = "territory"

    engines = _engines(cfg)
    if not engines:
        _out(
            f"\n  {_RED}⬡ The council has no AI engine to run on.{_R}\n"
            f"  {_DIM}Start Ollama for fully local use, turn on Cursiv Cloud ('cloud on'), "
            f"or add a free key -- type 'free keys' for step-by-step links.{_R}\n"
        )
        return None

    seats = _plan_seats(engines, full_mode)
    max_tokens = 1200 if full_mode else 700

    mode_str = (f"{_B}{_MAG}FULL DELIBERATION{_R}" if full_mode
                else f"{_DIM}SIGNAL MODE · /full <question> for the complete deliberation{_R}")
    eng_line = "  ·  ".join(f"{e['color']}{e['name']}{_R}" for e in engines)
    seat_line = ", ".join(s["agent"].name for s in seats)
    q_preview = query[:72] + ("…" if len(query) > 72 else "")
    _out(f"\n  {_MAG}╔{'═' * 64}╗{_R}\n")
    _out(f"  {_MAG}║{_R}  {_B}⬡ CURSIV COUNCIL{_R}  {_DIM}·{_R}  {mode_str}\n")
    _out(f"  {_MAG}║{_R}  {_DIM}seats:{_R} {seat_line}\n")
    _out(f"  {_MAG}║{_R}  {_DIM}engines:{_R} {eng_line}\n")
    _out(f"  {_MAG}║{_R}  {_DIM}question:{_R} {_DIM}{q_preview}{_R}\n")
    _out(f"  {_MAG}╚{'═' * 64}╝{_R}\n")
    if full_mode and trigger:
        _out(f"  {_DIM}full mode via: {trigger}{_R}\n")

    t0 = time.time()
    bad: set = set()
    try:
        # Round 1 -- every seat answers independently, in parallel.
        grounding = _grounding(query)

        def round1(seat):
            return [{"role": "system", "content": _seat_system(seat["agent"], full_mode, grounding)},
                    {"role": "user", "content": query}]
        results = _run_round(seats, engines, round1, max_tokens, _out, bad)
        scores = _score_seats(query, results, _out)

        # Round 2 (full mode) -- each seat sees the others and refines.
        answered = [r for r in results if r["engine"] is not None]
        if full_mode and len(answered) > 1:
            _out(f"\n  {_MAG}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{_R}\n"
                 f"  {_WHT}{_B}⬡ ROUND 2 — REFINEMENT{_R}  {_DIM}each seat sees the others{_R}\n")
            first = {r["agent"].name: r["text"] for r in answered}

            def round2(seat):
                others = "\n\n".join(f"[{n}]: {t[:600]}" for n, t in first.items() if n != seat["agent"].name)
                return [{"role": "system", "content": _seat_system(seat["agent"], full_mode, grounding)},
                        {"role": "user", "content":
                            f"Question: {query}\n\nYour first answer from this seat:\n{first[seat['agent'].name][:900]}\n\n"
                            f"What the other seats said:\n\n{others}\n\nRefine your seat's position: agree briefly "
                            f"where they're right, push back where they're wrong, add what they missed. "
                            f"Don't repeat your first answer."}]
            refined_seats = [{"agent": r["agent"], "engine_index": engines.index(r["engine"])} for r in answered]
            refined = _run_round(refined_seats, engines, round2, max_tokens, _out, bad, round_label="Refined — ")
            by_name = {r["agent"].name: r for r in refined if r["engine"] is not None}
            results = [by_name.get(r["agent"].name, r) for r in results]
            scores = _score_seats(query, results, _out)

        answered = [r for r in results if r["engine"] is not None]
        if not answered:
            _out(f"\n  {_RED}⬡ None of the engines could answer this time.{_R}\n")
            return None

        limit = None if full_mode else _SIGNAL_CHARS
        signals = {r["agent"].name: r["text"][:limit] for r in answered
                   if scores.get(r["agent"].name, {"avg": 100})["avg"] >= _LOW_QUALITY_THRESHOLD}
        if not signals:
            signals = {r["agent"].name: r["text"][:limit] for r in answered}

        prior_wisdom = ""
        try:
            from cursiv_v215.council.council_memory import get_council_memory
            cm = get_council_memory()
            prior_wisdom = cm.format_prior_wisdom(cm.find_similar(query, top_k=2))
        except Exception:
            pass

        _out(f"\n  {_MAG}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{_R}\n"
             f"  {_WHT}{_B}⬡ CURSIV{_R}  {_DIM}{'full deliberation' if full_mode else 'synthesis'}{_R}\n\n  {_WHT}")
        synthesis = _synthesize(query, signals, engines,
                                list(dict.fromkeys(r["engine"]["id"] for r in answered)),
                                full_mode, prior_wisdom, _out, grounding)
        _out(_R)
        if synthesis and not synthesis.startswith("[Synthesis unavailable"):
            _anchor_check(query, synthesis, signals, grounding, engines, _out)

        try:
            from cursiv_v215.council.council_memory import get_council_memory
            get_council_memory().record(query, synthesis, min(1.0, len(synthesis.split()) / 150))
        except Exception:
            pass
    except KeyboardInterrupt:
        _out(f"\n  {_DIM}[council cancelled]{_R}\n")
        return None

    duration = time.time() - t0
    used = list(dict.fromkeys(r["engine"]["name"] for r in answered))
    _out(
        f"\n\n  {_MAG}┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄{_R}\n"
        f"  {_DIM}⬡ deliberation complete  ·  {'full' if full_mode else 'signal'} mode  ·  "
        f"{len(answered)} seats on {len(used)} engine{'s' if len(used) != 1 else ''}  ·  {duration:.1f}s{_R}\n"
    )
    return CouncilResult(
        query             = query,
        mode              = "full" if full_mode else "signal",
        providers_used    = used,
        signals           = signals,
        full_texts        = {r["agent"].name: r["text"] for r in answered},
        synthesis         = synthesis,
        full_triggered_by = trigger,
        duration_s        = duration,
    )

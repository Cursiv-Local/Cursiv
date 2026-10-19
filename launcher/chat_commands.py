"""
Text commands for the chat window ("help", "offline on", "remember ...").

handle_command() returns a TextResult or StreamResult for a built-in command,
or None for normal chat. It calls the same functions the terminal CLI
(cursiv_v215/chat) uses.

Handled in chat_panel.py instead, because they need a window or widget:
voice / listen / paste, write to / legacy (compose and PIN dialogs), and
clear (the transcript widget).
"""
from __future__ import annotations

import threading
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Generator, Optional

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Matches the CLI's ANSI color codes so captured terminal-style output can
# be shown safely in the chat transcript instead of as literal escape junk.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

from cursiv_v215.ui.chat_app import (
    chat as _chat,
    ROOT as _CHAT_ROOT,
    RATE_SENTINEL,
    WRITE_SENTINEL,
    REPLACE_SENTINEL,
    execute_tool as _execute_tool,
    _call_ollama,
    _call_ollama_code_council,
    _call_xai_stream,
    _call_claude_direct,
    _call_openai_direct,
    _call_provider_council,
    _web_search,
    cascade_stream as _cascade_stream,
    free_key_command as _free_key_command,
)

from cursiv_v215.chat.keys import (
    store_key as _save_key, probe_xai as _probe_xai, probe_openai as _probe_openai, probe_claude as _probe_claude,
)

try:
    from cursiv_v215.agents.babel_agent import is_babel_command as _babel_detect, extract_babel_input as _babel_input
    _BABEL_OK = True
except Exception:
    _BABEL_OK = False
    def _babel_detect(t): return False
    def _babel_input(t): return ""

try:
    from cursiv_v215.agents.codex_agent import generate as _codex_gen, is_available as _codex_avail
    _CODEX_OK = True
except Exception:
    _CODEX_OK = False
    def _codex_gen(p): return ""
    def _codex_avail(): return False

try:
    from cursiv_v215.agents.hermes_agent import run as _hermes_run, is_available as _hermes_avail
    _HERMES_OK = True
except Exception:
    _HERMES_OK = False
    def _hermes_run(p): return ""
    def _hermes_avail(): return False

try:
    from cursiv_v215.agents.reference_brain import answer as _ref_answer, is_available as _ref_avail
    _REF_OK = True
except Exception:
    _REF_OK = False
    def _ref_answer(q): return ""
    def _ref_avail(): return False

try:
    from cursiv_v215.council.async_council import run_council as _async_council_run, council_available as _async_council_ok
    _ASYNC_COUNCIL_OK = True
except Exception:
    _ASYNC_COUNCIL_OK = False
    def _async_council_run(q, cfg, **kw): return None
    def _async_council_ok(cfg): return False

try:
    from cursiv_v215.core.strand_store import (
        save_strand as _strand_save,
        list_strands as _strand_list,
        search_strands as _strand_search,
        format_strand_list as _strand_fmt,
        strand_count as _strand_count,
        territory_counts as _strand_terr_counts,
        load_territories as _strand_territories,
    )
    _STRAND_OK = True
except Exception:
    _STRAND_OK = False
    def _strand_save(*a, **kw): return ""
    def _strand_list(**kw): return []
    def _strand_search(q, **kw): return []
    def _strand_fmt(s): return ""
    def _strand_count(): return 0
    def _strand_terr_counts(): return {}
    def _strand_territories(): return {}

try:
    from cursiv_v215.obsidian.exporter import (
        load_config as _obs_load_config,
        save_config as _obs_save_config,
        export_today as _obs_export,
    )
    _OBS_OK = True
except Exception:
    _OBS_OK = False
    def _obs_load_config(): return {"enabled": False, "vault_path": ""}
    def _obs_save_config(e, p): pass
    def _obs_export(vp, d=None): return (False, "Obsidian module unavailable.")

try:
    from cursiv_v215.memory.session_log import append_exchange as _session_append
except Exception:
    def _session_append(u, a, m="unknown"): pass

try:
    from cursiv_v215.postal.sealed_store import (
        seal_letter as _postal_seal,
        open_letter as _postal_open,
        get_sealed_entry as _postal_entry,
        get_sig_status as _postal_sig_status,
        letters_for as _postal_for,
        letters_from as _postal_from,
        all_letters as _postal_all,
        export_sealpack as _postal_export,
        import_sealpack as _postal_import,
    )
    from cursiv_v215.postal.council_reader import council_walkthrough as _postal_council
    from cursiv_v215.postal.user_registry import (
        setup_identity as _postal_setup,
        my_identity as _postal_my_id,
        add_contact as _postal_add_contact,
        remove_contact as _postal_rm_contact,
        list_contacts as _postal_contacts,
        resolve_recipient as _postal_resolve,
        rotate_identity as _postal_rotate,
        key_rotation_history as _postal_key_history,
    )
    _POSTAL_OK = True
except Exception:
    _POSTAL_OK = False
    def _postal_seal(**kw): return ""
    def _postal_open(i): return None
    def _postal_entry(i): return None
    def _postal_sig_status(i): return "unknown"
    def _postal_for(k): return []
    def _postal_from(k): return []
    def _postal_all(): return []
    def _postal_export(i): return None
    def _postal_import(f, p): return None
    def _postal_council(i, u, c, **kw): return "[Postal module unavailable]"
    def _postal_setup(n): return {}
    def _postal_my_id(): return None
    def _postal_add_contact(n, k): return {}
    def _postal_rm_contact(n): return False
    def _postal_contacts(): return []
    def _postal_resolve(n): return None
    def _postal_rotate(reason="", **kw): return {}
    def _postal_key_history(): return []

try:
    from cursiv_v215.family.family_profiles import detect_family_member as _fam_detect
    from cursiv_v215.family.legacy_store import (
        letters_waiting_for as _legacy_letters_for,
        letters_written_by as _legacy_letters_by,
        get_letter_content as _legacy_get_content,
        save_letter as _legacy_save,
        rewrite_letter as _legacy_rewrite,
        delete_letter as _legacy_delete,
        name_to_key as _legacy_name_to_key,
        export_pack as _legacy_export_pack,
        import_pack as _legacy_import_pack,
        open_folder as _legacy_open_folder,
    )
    from cursiv_v215.family.family_profiles import (
        pin_is_set as _fam_pin_is_set,
        verify_pin as _fam_verify_pin,
        set_pin as _fam_set_pin,
        is_valid_pin as _fam_pin_valid,
        get_letter as _fam_get_letter,
        build_system_prompt as _fam_build_prompt,
        get_jw_header as _fam_header,
        parse_iam_command as _fam_parse_iam,
        PIN_CHARS as _FAM_PIN_CHARS,
    )
    _LEGACY_OK = True
except Exception:
    _LEGACY_OK = False
    def _fam_detect(n, d): return None
    def _fam_pin_is_set(k): return False
    def _fam_verify_pin(k, p): return False
    def _fam_set_pin(k, p): pass
    def _fam_pin_valid(p): return False
    def _fam_get_letter(k): return ""
    def _fam_build_prompt(p): return ""
    def _fam_header(): return ""
    def _fam_parse_iam(t): return None
    _FAM_PIN_CHARS = "! @ # $ % ^ & * ~ - + = ? /"
    def _legacy_letters_for(k): return []
    def _legacy_letters_by(k): return []
    def _legacy_get_content(i): return None
    def _legacy_save(**kw): return ""
    def _legacy_rewrite(i, c): return False
    def _legacy_delete(i): return False
    def _legacy_name_to_key(n): return n.lower().split()[0] if n.split() else ""
    def _legacy_export_pack(k, d): return (Path("."), 0)
    def _legacy_import_pack(f): return (0, [])
    def _legacy_open_folder(p): pass

try:
    from cursiv_v215.agents.voice_agent import (
        record as _voice_record,
        transcribe_raw as _voice_transcribe,
        is_available as _voice_avail,
        stt_backend as _voice_stt_backend,
        capture_backend as _voice_cap_backend,
        VOICE_CLEAN_SYSTEM as _VOICE_CLEAN_SYS,
    )
    _VOICE_OK = True
except Exception:
    _VOICE_OK = False
    def _voice_record(duration_s=5.0, status_cb=None): return b"", None
    def _voice_transcribe(pcm, float32_arr=None, status_cb=None): return ""
    def _voice_avail(): return False
    def _voice_stt_backend(): return "none"
    def _voice_cap_backend(): return "none"
    _VOICE_CLEAN_SYS = ""

try:
    from cursiv_v215.agents.babel_agent import (
        encode_to_binary as _babel_encode,
        decode_from_binary as _babel_decode,
    )
except Exception:
    def _babel_encode(t): return b""
    def _babel_decode(b): return ""

try:
    from cursiv_v215.agents.offline_queue import (
        enqueue as _queue_enqueue,
        format_queue as _queue_format,
        count as _queue_count,
    )
    _QUEUE_OK = True
except Exception:
    _QUEUE_OK = False
    def _queue_enqueue(t, **kw): return {}
    def _queue_format(): return ""
    def _queue_count(): return 0

try:
    from cursiv_v215.core.strand_federation import (
        export_pack as _sfed_export,
        import_pack as _sfed_import,
        pack_summary as _sfed_summary,
        PACK_EXT as _PACK_EXT,
    )
    _SFED_OK = True
except Exception:
    _SFED_OK = False
    def _sfed_export(*a, **kw): return ""
    def _sfed_import(t): return [], {}, {}
    def _sfed_summary(s, m): return ""
    _PACK_EXT = ".cursivpack"


# ── Result types ─────────────────────────────────────────────────────────

class TextResult:
    """A complete, ready-to-show result -- no streaming."""
    def __init__(self, text: str, image_path: str = ""):
        self.text = text
        self.image_path = image_path   # set for image-generation/paste results


class StreamResult:
    """An intro line shown immediately, then a generator streamed in."""
    def __init__(
        self,
        intro: str,
        generator: Generator[str, None, None],
        on_complete: Optional[Callable[[str], None]] = None,
    ):
        self.intro = intro
        self.generator = generator
        self.on_complete = on_complete


# Commands removed in the plain-language cleanup (2026-10-17). Only their exact
# old forms get a note; anything longer ("grow tomatoes") is normal chat.
_RETIRED = {
    "tier 2", "tier 3", "governor", "governor on", "governor off", "overseer on", "overseer off",
    "funforge", "forge done", "forge close", "forge extend", "substrate", "substrate status",
    "blast", "blast login", "blast register", "blast logout", "blast who", "grow system",
}


def _gate():
    from cursiv_v215.core import netgate
    return netgate


def _default_cfg() -> dict:
    """Same shape as chat_cli.py's cfg dict, minus the terminal-only fields."""
    return {
        "file_access":      False,
        "confirm_mode":     "confirm",   # same safe default as the terminal CLI -- every write needs approval until "mode" toggles it
        "workspace":        str(_CHAT_ROOT),
        "obsidian_enabled": False,
        "obsidian_path":    "",
        "offline_mode":     _gate().is_offline(),
        "last_user_msg":    "",
        "_last_council_synthesis": "",
        "_last_council_query":     "",
    }


def _auto_territory(q: str) -> str:
    ql = q.lower()
    if any(w in ql for w in ["code", "function", "python", "debug", "build", "error", "syntax", "class", "codex"]):
        return "coding"
    if any(w in ql for w in ["health", "recovery", "feel", "mental", "grounding", "medication", "episode"]):
        return "recovery"
    if any(w in ql for w in ["design", "system", "architecture", "cursiv", "agent", "strand", "council", "guardian"]):
        return "architecture"
    if any(w in ql for w in ["music", "creative", "story", "forge", "art", "write", "poem", "song"]):
        return "creative"
    if any(w in ql for w in ["research", "history", "world", "science", "civilization"]):
        return "worldmodel"
    return "general"


_LANG_NAMES = {
    "mandarin": "Mandarin Chinese", "chinese": "Mandarin Chinese", "korean": "Korean",
    "russian": "Russian", "spanish": "Spanish", "french": "French", "german": "German",
    "japanese": "Japanese", "arabic": "Arabic", "hindi": "Hindi", "portuguese": "Portuguese",
    "italian": "Italian", "turkish": "Turkish", "dutch": "Dutch", "polish": "Polish",
    "vietnamese": "Vietnamese", "thai": "Thai", "hebrew": "Hebrew", "greek": "Greek",
    "swedish": "Swedish", "ukrainian": "Ukrainian", "farsi": "Persian (Farsi)",
    "persian": "Persian (Farsi)", "tagalog": "Tagalog",
}


# "into all the languages you can" / "as many languages as you can"
_BABEL_MANY = re.compile(r"\b(all|every|many|lots of|as many)\b.*\blanguages?\b|\blanguages?\b.*\byou can\b", re.I)
_BABEL_DEFAULT_SET = ["Spanish", "French", "German", "Italian", "Portuguese", "Mandarin Chinese",
                      "Japanese", "Korean", "Hindi", "Arabic", "Russian", "Swahili", "Hebrew", "Greek"]


def _babel_source(text: str) -> str:
    """The text to translate: drop a leading "translate" and surrounding quotes."""
    t = re.sub(r"^\s*translate\s+", "", text.strip(), flags=re.I).strip()
    return t.strip("\"'“”‘’ ").strip()


def _babel_targets(phrase: str) -> list[str]:
    """Languages named after "into": split on commas / "and" / "&", and on spaces
    only when every word is a known language ("spanish french"), so "Mandarin
    Chinese" or "Brazilian Portuguese" stay whole and "all the languages you can"
    means a broad set rather than five 'languages' called All, The, …"""
    phrase = phrase.strip().rstrip(".!?")
    if _BABEL_MANY.search(phrase):
        return list(_BABEL_DEFAULT_SET)
    targets: list[str] = []
    for part in re.split(r"\s*(?:,|;|&|\band\b)\s*", phrase, flags=re.I):
        part = part.strip()
        if not part:
            continue
        words = part.split()
        if len(words) > 1 and all(w.lower() in _LANG_NAMES for w in words):
            targets += [_LANG_NAMES[w.lower()] for w in words]
        else:
            targets.append(_LANG_NAMES.get(part.lower(), part.title()))
    seen: set[str] = set()
    return [t for t in targets if not (t in seen or seen.add(t))]


def _cascade_gen(cfg: dict, messages: list[dict], max_tokens: int = 900):
    """Local model first, then any keys (chat_app.cascade_stream), falling through
    whenever one fails, so one-shot tools (babel, grow) work with no keys or dead
    ones. Returns (generator, engine label); the generator ends with an
    "Answered by …" line naming the engine that really answered."""
    gen, used = _cascade_stream(messages, cfg, max_tokens=max_tokens)

    def _labelled():
        yield from gen
        if used:
            yield f"\n\n*[Answered by {used[0].replace(' (local)', '')}]*"

    return _labelled(), (used[0] if used else "")



# ── Codex: Cursiv's coding brain (cursiv_v215/coding) ──────────────────────
_LAST_CODEX: dict = {}     # question/answer of the last codex reply, for `codex keep` / `codex run`


def _codex_command(prompt: str, cfg: dict, history: list[dict]):
    from cursiv_v215.coding import brain, runner
    from cursiv_v215.memory import semantic
    person = semantic.current_person()
    low = prompt.lower()

    if not prompt or low in ("help", "?"):
        return TextResult(_CODEX_HELP)
    if low == "keep":
        return TextResult(brain.keep_example(_LAST_CODEX.get("q", ""), _LAST_CODEX.get("a", ""), person))
    if low == "lessons":
        ls = brain.list_lessons(person)
        if not ls:
            return TextResult("No coding lessons yet. I learn them as we work (your setup, errors you hit, "
                              "fixes that worked), or add one: codex learn <lesson>")
        return TextResult("Coding lessons I use:\n" + "\n".join(f"- {l['text']}" for l in ls[-40:]) +
                          "\n\nRemove one: codex forget <words>")
    if low.startswith("learn "):
        ok = brain.add_lesson(prompt[6:], person)
        return TextResult("Got it — I'll use that in coding answers." if ok else "I already know that (or it's too short).")
    if low.startswith("forget "):
        gone = brain.forget_lessons(prompt[7:], person)
        return TextResult(("Forgotten:\n" + "\n".join(f"- {g}" for g in gone)) if gone else "No lesson matched that.")
    if low == "project" or low.startswith("project "):
        arg = prompt[7:].strip()
        if not arg:
            cur = brain.project(person)
            return TextResult(f"Current project: {cur}" if cur else "No project set. Use: codex project <folder path>")
        return TextResult(brain.set_project(arg, person))
    if low == "run":
        code = runner.extract_python(_LAST_CODEX.get("a", ""))
        if not code:
            return TextResult("The last codex answer has no Python code to run.")
        ok, why = runner.check(code)
        if not ok:
            return TextResult(f"I won't run it here: {why}.")
        success, out = runner.run(code)
        return TextResult(("✅ It runs.\n" if success else "❌ It failed.\n") + f"```\n{out[-2000:] or '(no output)'}\n```")

    msgs = brain.build_messages(prompt, history, person)

    try:
        from cursiv_v215.ui.chat_app import _local_model_ready, _ollama_pulled_models
        has_coder = _local_model_ready() and any("coder" in m for m in _ollama_pulled_models())
    except Exception:
        has_coder = False
    local_fn = (lambda m: _call_ollama_code_council(m, max_tokens=4000)) if has_coder else None

    def make_gen(messages):
        gen, _used = _cascade_stream(messages, cfg, max_tokens=4000, local_fn=local_fn)
        return gen

    def regenerate(code: str, error: str):
        fix_msgs = msgs + [
            {"role": "assistant", "content": f"```python\n{code}\n```"},
            {"role": "user", "content": "I ran that code and it failed:\n```\n" + error[-2500:] + "\n```\n"
                                        "Explain the cause in one or two sentences, then give the complete corrected "
                                        "file in one ```python block."},
        ]
        return make_gen(fix_msgs)

    def stream():
        parts = []
        for chunk in make_gen(msgs):
            parts.append(chunk)
            yield chunk
        for chunk in runner.run_and_fix("".join(parts), regenerate):
            parts.append(chunk)
            yield chunk
        yield "\n\n*Good answer? Type `codex keep` and I'll answer like this from now on.*"

    def _finish(full: str):
        _LAST_CODEX.update(q=prompt, a=full)
        _session_append(prompt, full, "codex")

        def learn():
            try:
                from cursiv_v215.ui.chat_app import _quick_llm
                brain.learn_from_exchange(prompt, full, _quick_llm, person)
            except Exception:
                pass
        threading.Thread(target=learn, daemon=True).start()

    return StreamResult(f"Codex — {prompt[:60]}", stream(), _finish)


_CODEX_HELP = """\
CODEX — Cursiv's coding helper
  codex <what you need>      full answer: every setup step, complete code, how to run it,
                             what to do if it fails. Paste terminal errors and it diagnoses them.
                             Python it writes is test-run and fixed automatically when safe.
  codex run                  test-run the code from the last codex answer
  codex keep                 save the last answer as a worked example to imitate
  codex project <folder>     use files from your project folder in answers (codex project off)
  codex lessons              what Cursiv has learned about your setup
  codex learn <lesson>       teach it something (e.g. "my venv is ~/robot")
  codex forget <words>       remove a lesson"""


# ── Custom agents (cursiv_v215/agents/custom.py) ───────────────────────────
def _agent_command(text: str, cfg: dict, history: list[dict]):
    import re as _re
    from cursiv_v215.agents import custom
    t = text.strip()
    low = t.lower()
    if low in ("agents", "agent", "agent list", "agent help"):
        return TextResult(custom.listing())

    m = _re.match(r"(?is)^agent\s+(new|create|make)\s+@?([\w-]+)\s*[:\-]?\s*(.*)$", t)
    if m:
        return TextResult(custom.create(m.group(2), m.group(3)))
    m = _re.match(r"(?is)^agent\s+edit\s+@?([\w-]+)\s*[:\-]?\s*(.*)$", t)
    if m:
        return TextResult(custom.edit(m.group(1), m.group(2)))
    m = _re.match(r"(?is)^agent\s+teach\s+@?([\w-]+)\s*[:\-]?\s*(.*)$", t)
    if m:
        return TextResult(custom.teach(m.group(1), m.group(2)))
    m = _re.match(r"(?is)^agent\s+(delete|remove)\s+@?([\w-]+)\s*$", t)
    if m:
        return TextResult(custom.delete(m.group(2)))
    m = _re.match(r"(?is)^agent\s+(show|info)\s+@?([\w-]+)\s*$", t)
    if m:
        return TextResult(custom.describe(m.group(2)))

    try:
        from cursiv_v215.ui.chat_app import _build_strand_context
    except Exception:
        _build_strand_context = lambda q: ""

    def _memory(q):
        try:
            return _build_strand_context(q) if len(q) >= 10 else ""
        except Exception:
            return ""

    m = _re.match(r"(?is)^agent\s+council\s+(.+)$", t)
    if m:
        question = m.group(1).strip()
        agents = custom.all_agents()
        if not agents:
            return TextResult(custom.listing())
        mem = _memory(question)

        def stream():
            views = []
            for a in agents[:6]:
                yield f"\n**@{a['name']}**\n"
                gen, _u = _cascade_stream(custom.messages_for(a, question + "\n\n(Answer in under 150 words, "
                                          "from your specialty.)", [], mem), cfg, max_tokens=500)
                parts = []
                for c in gen:
                    parts.append(c)
                    yield c
                views.append(f"{a['name']}: {''.join(parts).strip()[:1500]}")
                custom.note_use(a)
            yield "\n\n---\n**Together**\n"
            synth = [{"role": "system", "content": "You are Cursiv. Several specialist agents answered the same question. "
                      "Combine them into one clear recommendation: where they agree, where they differ, and the best "
                      "next step. Be brief. Don't invent facts."},
                     {"role": "user", "content": f"Question: {question}\n\n" + "\n\n".join(views)}]
            gen, _u = _cascade_stream(synth, cfg, max_tokens=700)
            yield from gen
        return StreamResult(f"Agent council — {len(agents[:6])} agents", stream(), None)

    m = _re.match(r"(?is)^(?:@|agent\s+(?:ask\s+)?@?)([\w-]+)[\s,:]+(.+)$", t)
    if m:
        a = custom.load(m.group(1))
        if not a:
            names = ", ".join("@" + x["name"] for x in custom.all_agents()) or "none yet"
            return TextResult(f"There's no agent called {custom.clean_name(m.group(1))}. Your agents: {names}.\n"
                              f"Make one: agent new {custom.clean_name(m.group(1)) or 'name'}: <what it should do>")
        q = m.group(2).strip()
        gen, _u = _cascade_stream(custom.messages_for(a, q, history, _memory(q)), cfg, max_tokens=3000)
        custom.note_use(a)
        return StreamResult(f"@{a['name']}", gen, None)
    if t.startswith("@"):
        return None            # a lone "@something" -- let normal chat handle it
    return TextResult(custom.listing())

# The research profile (core/profile.py, the default): field work first.
_FIELD_HELP_TEXT = """\
Just type a question. These are for field work:

  log site: North; pH 7.2; 44.12, -71.56   save an observation (or open Field Notebook)
  field log / field log check            see entries / check nothing was changed
  field report / field log export        a printable report / CSV, JSON, GeoJSON
  add document <path>                    a protocol or SOP to answer from, by page
  distance from 44.1, -71.5 to 44.2, -71.4   worked out in code (units, UTM, dilutions too)
  remember <something>                   I'll keep it in mind
  offline on / off                       LOCAL ONLY: block the internet
  status                                 what's on, and which model answers
  demo                                   try all of it with sample data

help more                                everything else"""

_HELP_TEXT = """\
Just talk to me. Most things don't need a command.

  remember <something>        I'll keep it in mind
  what do you remember        see what I know (forget <words> to remove)
  translate <text> into <lang>   Spanish, French, Korean, ...
  search: <question>          look it up online, only when you ask
  write to <name>             a private sealed letter for family
  mic button / voice          talk instead of typing
  paste                       look at a picture from the clipboard
  offline on / off            keep everything on this computer
  Settings (gear, top right)  AI keys, privacy, updates

help more                     everything else"""

# help <topic>. Topics in _BUILDER_TOPICS are listed only for the owner
# (they still open for anyone who types them).
_HELP_TOPICS = {
    "field": ("Field notebook", """\
  log site: <name>; <measurement> <value> <unit>; <lat>, <lon>; note: <text>
                              save an observation, values kept exactly as typed
  log ...; sample: auto       give it a new sample ID (NT-20261018-001)
  field log                   the latest entries
  field log sample <id>       one sample's history
  field log check             check that no entry was changed, removed or reordered
  field report [site <name>] [today]   a printable report
  field log export            CSV, JSON, GeoJSON, the report and sample labels, signed
  field log verify <folder>   check an export's signature and that no file was changed
  field log share <folder>    put this laptop's log on a USB drive or shared folder
  field log import <folder>   bring in other laptops' logs (team log, team log export)
  field log import <file>     a .cursivsync file from the phone notebook (cursiv.winklers-llc.com/notebook)
  Corrections: Field Notebook -> Correct selected. The original always stays.
  demo / demo off             sample data to try it with, kept apart from yours"""),
    "documents": ("Your documents and calculations", """\
  add document <path>         import a PDF or text file (protocol, SOP, permit)
  documents                   what's imported
  Answer only from my documents: Settings -> How Cursiv answers
  Worked out in code, not guessed: units (convert 12.4 C to F), degrees-minutes-seconds,
  UTM (what is 44.1234, -71.5678 in UTM), distance and bearing between two points,
  dilutions (C1V1 = C2V2), mean / standard deviation, clock times, bleach doses"""),
    "memory": ("Memory", """\
  remember <something>        save a fact about you (or the family)
  what do you remember        list what I know, with when and how I learned it
  forget <words>              remove a saved fact
  memory learn on / off       learn from our chats on my own (on by default)
  save this                   save the last answer as a note
  notes / notes search <words>   your saved notes
  clear                       clear this conversation from the screen"""),
    "family": ("Family", """\
  write to <name>             write a sealed letter (opens a window)
  letters                     letters waiting for you, and ones you sent
  open letter <id>            read one letter
  legacy                      open the family Legacy Vault
  legacy import <file>        add a .legacypack file to the vault"""),
    "translate": ("Translate and voice", """\
  translate <text> into <lang>   e.g. into English, or into Spanish and French
  voice / voice <seconds>     record, turn speech into text, then send
  voice raw / listen          speech to text only, no clean-up
  paste                       look at a picture from the clipboard
  image <description>         draw a picture (needs a paid OpenAI key)"""),
    "privacy": ("Privacy and internet", """\
  offline on / off            Cursiv makes no internet connections (stays on after restart)
  search: <question>          search the web once
  websearch on / off          search on my own when a question sounds current (off by default)
  pull <web address>          read a web page and summarize it
  autoupdate on / off         check for new versions after login (off by default)
  cloud on / off / status     Cursiv Cloud, used only when no local AI is ready
  status                      what's on and off right now"""),
    "keys": ("AI keys (or use Settings)", """\
  free keys                   how to get a free Gemini or Groq key (2 minutes)
  gemini <key> / groq <key>   add a free key
  key <xai-key>               add an xAI Grok key
  openai <key>                add an OpenAI key
  anthropic <key>             add a Claude key
  grok / claude               ask the last question again with that AI"""),
    "style": ("How I talk", """\
  tone <warm|brief|blunt|teacher|playful|normal>   how I talk to you
  style                       your tone and the rules I learned from your corrections
  rate good / bad / 1-5       tell me how the last answer was"""),
    "coding": ("Files and coding", """\
  codex <request>             coding help, every step listed (codex help for more)
  files on / off              let me read and write files
  workspace <folder>          the folder I'm allowed to use
  mode                        writes: ask first <-> automatic"""),
    "builder": ("Builder tools", """\
  evolve <idea>               write a new ability (plugin); you approve it first
  plugins                     plugin show / on / off / remove <name>
  projects                    running summaries of projects (project show / forget <name>)
  agents                      agent new <name>: <job>, then @name <message>
  agent council <question>    ask all your agents, then combine their views
  council <question>          ask every AI at once and combine the answers
  /full <question>            council without the summary step
  postal setup <name> / my key / add user <n> <k> / contacts / rotate
  note export / note import <file>
  ref <question>              answer from the local reference data
  queue list / queue add <task>
  obsidian on / off / path / export / status"""),
}
_BUILDER_TOPICS = {"builder"}
_PERSONAL_TOPICS = {"family", "coding", "builder"}     # listed only with personal features shown


def _personal() -> bool:
    try:
        from cursiv_v215.core import profile
        return profile.personal()
    except Exception:
        return False


def _is_builder() -> bool:
    """The owner: a verified owner session, or this is one of Joshua's machines."""
    try:
        from cursiv_v215.ui.chat_app import _owner_active
        if _owner_active():
            return True
    except Exception:
        pass
    try:
        from cursiv_v215.guardian.access_gate import is_setup_complete
        return bool(is_setup_complete())
    except Exception:
        return False


def help_text(topic: str = "") -> str:
    """`help` -> the short list; `help more` -> topics; `help <topic>` -> one topic."""
    topic = topic.strip().lower()
    if not topic:
        return _HELP_TEXT if _personal() else _FIELD_HELP_TEXT
    if topic in _HELP_TOPICS:
        title, body = _HELP_TOPICS[topic]
        return f"{title.upper()}\n{body}\n\nhelp more  -  all topics"
    names = [t for t in _HELP_TOPICS
             if (t not in _BUILDER_TOPICS or _is_builder()) and (t not in _PERSONAL_TOPICS or _personal())]
    lines = [f"  help {t:<10} {_HELP_TOPICS[t][0]}" for t in names]
    head = "" if topic in ("more", "all", "topics") else f"No help topic called \"{topic}\".\n\n"
    return head + "Type one of these:\n" + "\n".join(lines)


def handle_command(raw: str, cfg: dict, history: list[dict]) -> Optional[TextResult | StreamResult]:
    """
    Returns None if `raw` isn't a recognized built-in command -- caller
    should fall through to a plain chat() call in that case.
    """
    text = raw.strip()
    if not text:
        return None
    cmd = text.lower()

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
    if cmd in ("help", "help?", "commands") or (_topic and (_topic in _HELP_TOPICS or _topic in ("more", "all", "topics"))):
        return TextResult(help_text(_topic or ""))

    # ── Free-form notes → JSON training example ─────────────────────────
    # Fuzzy-matched, not a fixed command -- "translate my notes into JSON
    # for training", "convert this into json for training", etc. all hit
    # it. A short trigger-only message ("translate my current notes into
    # JSON format for training") means "the notes" are whatever the user
    # just said before this -- pull the prior user turn instead of trying
    # to translate the instruction sentence itself.
    if _looks_like_text_to_json_request(text):
        notes = text
        if len(text) < 160:
            for turn in reversed(history):
                if turn.get("role") == "user":
                    notes = turn.get("content", "")
                    break
        ok, msg, entry = text_to_training_entry(notes, cfg)
        if ok and entry:
            return TextResult(f"{msg}\n\n```json\n{json.dumps(entry, indent=2)}\n```")
        return TextResult(f"{msg}")

    # ── Simple state toggles ────────────────────────────────────────────
    def _engine_line() -> str:
        try:
            from cursiv_v215.core import ollama_host
            return ollama_host.diagnose()
        except Exception as exc:
            return f"unknown ({exc})"

    if cmd == "status":
        # What a reviewer asks first: is it local only, and which model answers (MRS feedback, 2026-10-18).
        try:
            from cursiv_v215.chat import status as _status
            mode = _status.network_status()["label"]
        except Exception:
            mode = "unknown"
        try:
            from cursiv_v215.ui.chat_app import _resolve_ollama_model
            model = _resolve_ollama_model()
        except Exception:
            model = None
        lines = [
            f"Mode:          {mode}",
            f"AI model:      {(model + ', on this computer (Ollama)') if model else 'no local model running'}",
            f"AI engine:     {_engine_line()}",
            f"Offline mode:  {'ON' if _gate().is_offline() else 'OFF'}",
            f"Web search:    {'automatic' if _gate().setting('web_search_auto') else 'only search:'}",
            f"Update check:  {'automatic' if _gate().setting('update_check_auto') else 'manual'}",
            f"Cloud AI keys: {', '.join(n for n, k in (('xAI', 'api_key'), ('OpenAI', 'openai_key'), ('Anthropic', 'anthropic_key')) if cfg.get(k)) or 'none set'}",
            f"File access:   {'ON' if cfg.get('file_access') else 'OFF'}",
        ]
        try:
            from cursiv_v215.core import demo as _demo, documents as _documents, fieldlog as _fieldlog
            n, bad = len(_fieldlog.entries()), _fieldlog.verify()
            lines.append(f"Field notebook: {n} entr{'y' if n == 1 else 'ies'}, "
                         + ("intact" if not bad else f"{len(bad)} problem(s): type field log check"))
            lines.append(f"Documents:     {len(_documents.library())} imported")
            if _demo.active():
                lines.insert(0, "FIELD DEMO ON: the notebook and documents hold sample data (demo off to end it)")
        except Exception:
            pass
        if cfg.get("file_access"):
            lines.append(f"Workspace:     {cfg.get('workspace', '')}")
        return TextResult("\n".join(lines))

    if cmd in _RETIRED:
        return TextResult(f"'{text}' was removed in this version. Type help to see what Cursiv can do.")

    if cmd == "tier 1":
        cmd = "offline on"           # tier 1 meant "local only": the same as offline mode
    if cmd in ("offline on", "offline off"):
        from cursiv_v215.core import netgate
        try:
            netgate.set_offline(cmd == "offline on")
        except Exception as exc:
            return TextResult(f"Couldn't save offline mode ({exc}). Nothing was changed.")
        cfg["offline_mode"] = netgate.is_offline()
        if cfg["offline_mode"]:
            return TextResult("Offline mode ON — Cursiv won't connect to anything outside this computer "
                              "(cloud AI, web search, update checks, model downloads). Your local model still works. "
                              "This stays on after a restart; type 'offline off' to undo.")
        return TextResult("Offline mode OFF — keys you've added, Cursiv Cloud and 'search:' can reach the internet again. "
                          "Automatic web search and update checks stay as set ('websearch on', 'autoupdate on').")

    if cmd in ("websearch on", "websearch off", "websearch"):
        from cursiv_v215.core import netgate
        if cmd != "websearch":
            netgate.set_setting("web_search_auto", cmd == "websearch on")
        on = netgate.setting("web_search_auto")
        return TextResult(
            ("Automatic web search ON — questions that sound current (\"today\", \"right now\") are sent to "
             "DuckDuckGo. Type 'websearch off' to stop." if on else
             "Automatic web search OFF — only messages that start with 'search:' go to the web.")
            + (f"\n{netgate.OFFLINE_MESSAGE}" if netgate.is_offline() else ""))

    if cmd in ("autoupdate on", "autoupdate off", "autoupdate"):
        from cursiv_v215.core import netgate
        if cmd != "autoupdate":
            netgate.set_setting("update_check_auto", cmd == "autoupdate on")
        on = netgate.setting("update_check_auto")
        return TextResult(
            ("Automatic update check ON — Cursiv asks GitHub for a new version after you log in."
             if on else "Automatic update check OFF — use \"Check for Updates\" when you want to.")
            + (f"\n{netgate.OFFLINE_MESSAGE}" if netgate.is_offline() else ""))

    if cmd in ("files on", "files off"):
        cfg["file_access"] = cmd == "files on"
        return TextResult(f"File access → {'ON' if cfg['file_access'] else 'OFF'}")

    if cmd == "mode":
        cfg["confirm_mode"] = "confirm" if cfg.get("confirm_mode") == "auto" else "auto"
        return TextResult(f"Write mode → {cfg['confirm_mode'].upper()}")

    if cmd.startswith("workspace"):
        new_ws = text[9:].strip()
        if not new_ws:
            return TextResult(f"Workspace: {cfg.get('workspace', '')}")
        ws_path = Path(new_ws).expanduser().resolve()
        if not ws_path.exists() or not ws_path.is_dir():
            return TextResult(f"Not a valid directory: {new_ws}")
        cfg["workspace"] = str(ws_path)
        return TextResult(f"Workspace → {ws_path}")

    # ── Free AI keys (Gemini / Groq) and Cursiv Cloud ─────────────────────
    _free_reply = _free_key_command(text)
    if _free_reply is not None:
        return TextResult(_free_reply)
    try:
        from cursiv_v215.memory.semantic import memory_command as _memory_command
        _mem_reply = _memory_command(text)
    except Exception:
        _mem_reply = None
    if _mem_reply is not None:
        return TextResult(_mem_reply)
    # The paperclip: photo "<path>" <question> -- the image model reads a photo
    _pm = _PHOTO_CMD.match(text.strip())
    if _pm and (Path(_pm.group(1) or _pm.group(2)).suffix.lower() in
                {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic"}):
        return describe_photo(_pm.group(1) or _pm.group(2), _pm.group(3), cfg)
    # The field demo: demo, demo off, demo questions (core/demo.py)
    try:
        from cursiv_v215.core import demo as _demo
        _demo_reply = _demo.command(text)
    except Exception as _exc:
        _demo_reply = f"The demo couldn't load: {_exc}" if cmd.strip() in ("demo", "load demo", "demo on") else None
    if _demo_reply is not None:
        return TextResult(_demo_reply)
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
        _log_reply = f"The field log couldn't be written: {_exc}" if cmd.startswith("log ") else None
    if _log_reply is not None:
        return TextResult(_log_reply)
    # The team's documents: "documents", "add document <path>" (core/documents.py)
    try:
        from cursiv_v215.core import documents as _documents
        _doc_reply = _documents.command(text)
    except Exception:
        _doc_reply = None
    if _doc_reply is not None:
        return TextResult(_doc_reply)
    if cmd in ("phases", "phase", "why that answer", "how did you decide"):
        from cursiv_v215.core.phases import last_trace_text
        return TextResult(last_trace_text())

    # ── API keys ─────────────────────────────────────────────────────────
    if cmd.startswith("key "):
        new_key = text[4:].strip()
        if new_key.startswith(("sk-", "sk_")):
            cfg["openai_key"] = new_key
            _save_key("openai_key", new_key)
            live = _probe_openai(new_key)
            return TextResult(
                "That's an OpenAI key — routed to the OpenAI slot.\n"
                f"OpenAI: {'connected' if live else 'unreachable'}"
            )
        cfg["api_key"] = new_key
        _save_key("api_key", new_key)
        live = _probe_xai(new_key)
        return TextResult(f"xAI: {'connected' if live else 'unreachable'}")

    if cmd.startswith("openai "):
        new_key = text[7:].strip()
        if new_key.startswith("xai-"):
            cfg["api_key"] = new_key
            _save_key("api_key", new_key)
            return TextResult(f"That's an xAI key — routed to the xAI slot. {'connected' if _probe_xai(new_key) else 'unreachable'}")
        if new_key.startswith("sk-ant-"):
            cfg["anthropic_key"] = new_key
            _save_key("anthropic_key", new_key)
            return TextResult(f"That's an Anthropic key — routed to the Anthropic slot. {'connected' if _probe_claude(new_key) else 'unreachable'}")
        cfg["openai_key"] = new_key
        _save_key("openai_key", new_key)
        return TextResult(f"OpenAI: {'connected' if _probe_openai(new_key) else 'unreachable'}")

    # Free Cloudflare Workers AI account -- used for free image generation.
    if cmd.startswith("cloudflare "):
        parts = text.split()
        if len(parts) != 3:
            return TextResult("Usage: cloudflare <account-id> <api-token>\n\n" + IMAGE_GEN_CLOUDFLARE_HOWTO)
        cfg["cf_account_id"], cfg["cf_api_token"] = parts[1], parts[2]
        _save_key("cf_account_id", parts[1])
        _save_key("cf_api_token", parts[2])
        return TextResult("Cloudflare saved — free image generation is on. Try: image a lighthouse at dawn")

    if cmd.startswith("anthropic "):
        new_key = text[10:].strip()
        if new_key.startswith("xai-"):
            cfg["api_key"] = new_key
            _save_key("api_key", new_key)
            return TextResult(f"That's an xAI key — routed to the xAI slot. {'connected' if _probe_xai(new_key) else 'unreachable'}")
        if new_key.startswith("sk-") and not new_key.startswith("sk-ant-"):
            cfg["openai_key"] = new_key
            _save_key("openai_key", new_key)
            return TextResult(f"That's an OpenAI key — routed to the OpenAI slot. {'connected' if _probe_openai(new_key) else 'unreachable'}")
        cfg["anthropic_key"] = new_key
        _save_key("anthropic_key", new_key)
        return TextResult(f"Claude: {'connected' if _probe_claude(new_key) else 'unreachable'}")

    # ── Codex / Hermes / Reference Brain ────────────────────────────────
    if cmd in ("tone", "style", "my style", "style show", "style clear") or cmd.startswith(("tone ", "style ")):
        try:
            from cursiv_v215.core import style as _style
            from cursiv_v215.memory import semantic as _sem
            _reply = _style.command(text, _sem.current_person())
            if _reply is not None:
                return TextResult(_reply)
        except Exception as exc:
            return TextResult(f"Couldn't change the style: {exc}")

    # ── Cursiv Forge: plugins + evolve; project memory (U52) ──────────────────
    if cmd in ("plugins", "plugin") or cmd.startswith("plugin "):
        from cursiv_v215.core import plugins as _pl
        _m = __import__("re").match(r"(?i)^plugin\s+(show|off|on|remove|delete|approve)\s+(\w+)\s*$", text.strip())
        if not _m:
            return TextResult(_pl.listing())
        _act, _name = _m.group(1).lower(), _m.group(2).lower()
        if _act == "show":
            return TextResult(_pl.show(_name))
        if _act in ("off", "on"):
            return TextResult(_pl.set_enabled(_name, _act == "on"))
        if _act == "approve":
            return TextResult(_pl.approve_existing(_name))
        return TextResult(_pl.remove(_name))
    if cmd == "evolve" or cmd.startswith("evolve "):
        from cursiv_v215.coding import forge as _forge
        _idea = text[6:].strip()
        if _idea.lower() in ("approve", "yes", "install"):
            return TextResult(_forge.approve())
        if _idea.lower() in ("discard", "no", "cancel"):
            return TextResult(_forge.discard())
        if _idea.lower() in ("", "help"):
            return TextResult("evolve <idea> — Cursiv writes a plugin that gives it a new ability, checks it for safety, "
                              "tests it in a sandbox, and shows you the code. Nothing installs until you type "
                              "`evolve approve`.\nExamples:\n  evolve a command that converts recipe amounts between cups and grams\n"
                              "  evolve a tool that tells me how many days until a date\n  evolve a tracker for my kids' chores")
        try:
            from cursiv_v215.ui.chat_app import _local_model_ready, _ollama_pulled_models
            _coder = _local_model_ready() and any("coder" in m for m in _ollama_pulled_models())
        except Exception:
            _coder = False
        _lf = (lambda m: _call_ollama_code_council(m, max_tokens=4000)) if _coder else None

        def _gen(msgs):
            g, _u = _cascade_stream(msgs, cfg, max_tokens=4000, local_fn=_lf)
            return g
        return StreamResult(f"Forge — {_idea[:60]}", _forge.evolve(_idea, _gen), None)
    if cmd in ("projects", "topics", "my projects") or __import__("re").match(r"(?i)^project (show|forget|delete) ", text.strip()):
        from cursiv_v215.memory import projects as _projmem
        from cursiv_v215.memory import semantic as _sem
        _r = _projmem.command(text, _sem.current_person())
        if _r is not None:
            return TextResult(_r)
    try:                     # commands added by installed plugins
        from cursiv_v215.core import plugins as _pl
        _out = _pl.run_command(text)
        if _out is not None:
            return TextResult(_out)
    except Exception:
        pass

    if cmd in ("agents", "agent", "agent list") or cmd.startswith(("agent ", "@")):
        res = _agent_command(text, cfg, history)
        if res is not None:
            return res

    if cmd == "codex" or cmd.startswith("codex "):
        return _codex_command(text[6:].strip(), cfg, history)

    if cmd == "hermes" or cmd.startswith("hermes "):
        if not _HERMES_OK or not _hermes_avail():
            return TextResult("Hermes Agent not available — needs Ollama running.")
        prompt = text[7:].strip()
        if not prompt:
            return TextResult("Usage: hermes <task to run>")
        result = _hermes_run(prompt)
        _session_append(prompt, result, "hermes_agent")
        return TextResult(result)

    if cmd == "ref" or cmd.startswith("ref "):
        if not _REF_OK or not _ref_avail():
            return TextResult("Reference Brain not available.")
        query = text[4:].strip()
        if not query:
            return TextResult("Usage: ref <question>")
        return TextResult(_ref_answer(query))

    # ── Council ──────────────────────────────────────────────────────────
    if (cmd == "council" or cmd.startswith("council ")
            or cmd == "/full" or cmd.startswith("/full ")
            or cmd == "/deliberate" or cmd.startswith("/deliberate ")):
        force_full = cmd.startswith(("/full", "/deliberate"))
        for prefix in ("council ", "/full ", "/deliberate "):
            if cmd.startswith(prefix):
                question = text[len(prefix):].strip()
                break
        else:
            question = ""
        if not question:
            return TextResult("Usage: council <question>  ·  /full <question> for complete deliberation")
        if _ASYNC_COUNCIL_OK:
            # Bridges run_council()'s blocking/asyncio interior to a live
            # generator via a background thread + queue -- the exact
            # pattern cursiv_v215.ui.chat_app.py's Gradio surface already
            # uses (_call_provider_council), so the GUI streams each
            # provider's response as it actually arrives (write_fn fires
            # for the session banner, each provider's own streamed text,
            # quality scores, and the synthesis, in that real order)
            # instead of going silent for the whole deliberation and only
            # ever showing a synthesis at the end. write_fn=None (the
            # default) falls back to raw sys.stdout.write() inside
            # run_council() -- fine for the terminal CLI, but sys.stdout
            # is None in the packaged GUI build (console=False), which is
            # why this needs an explicit write_fn at all, not just a nicer
            # UI: without one, this crashed outright the moment
            # run_council tried to print anything.
            _result_holder: dict = {}

            def _run():
                import queue as _queue_mod
                q: "_queue_mod.Queue[str | None]" = _queue_mod.Queue()

                def _worker():
                    try:
                        r = _async_council_run(
                            question, cfg, force_full=True if force_full else None,
                            write_fn=q.put,
                        )
                        _result_holder["result"] = r
                    except Exception as exc:
                        q.put(f"\n[Council error: {exc}]\n")
                    finally:
                        q.put(None)   # sentinel -- always fires

                import threading as _threading_mod
                _threading_mod.Thread(target=_worker, daemon=True).start()

                while True:
                    chunk = q.get()
                    if chunk is None:
                        break
                    # CLI-only ANSI color codes would otherwise show up as
                    # literal garbage (e.g. "\x1b[31m") in the transcript.
                    yield _ANSI_RE.sub("", chunk)

                result = _result_holder.get("result")
                if result is not None:
                    cfg["_last_council_synthesis"] = result.synthesis
                    cfg["_last_council_query"] = question

            def _finish(full: str):
                # Strand/session log gets the clean synthesis specifically
                # (when available), not the full multi-provider transcript
                # the chat panel just streamed -- same as before this was
                # switched to live streaming, just no longer assuming the
                # generator's only output was ever the synthesis alone.
                result = _result_holder.get("result")
                saved = result.synthesis if result is not None else full
                _session_append(question, saved, "async_council")
                if _STRAND_OK and saved and len(saved) > 100:
                    _strand_save(question, saved, tags=["council", "async"], score=0.80,
                                 territory_tag="worldmodel", source="async_council", model="council_synthesis")

            return StreamResult(f"Council deliberating — {question[:60]}", _run(), _finish)
        if not (cfg.get("api_key") or cfg.get("openai_key") or cfg.get("anthropic_key")):
            return TextResult("Council requires at least one API key.")
        def _finish2(full: str):
            cfg["_last_council_synthesis"] = full
            _session_append(question, full, "group_discovery")
        return StreamResult(
            f"Group discovery — {question[:60]}",
            _call_provider_council(question, cfg.get("api_key", ""), cfg.get("openai_key", ""), cfg.get("anthropic_key", "")),
            _finish2,
        )

    # ── Strand memory ────────────────────────────────────────────────────
    if cmd == "anchor this" or cmd.startswith("anchor this "):
        if not _STRAND_OK:
            return TextResult("Saved notes aren't available.")
        parts = cmd.split()
        territory = parts[2] if len(parts) >= 3 else "general"
        if territory != "general" and territory not in _strand_territories():
            territory = "general"
        if not history:
            return TextResult("No session history to anchor.")
        last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
        last_ai = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
        if not (last_user or last_ai):
            return TextResult("Nothing to anchor yet — send a message first.")
        sid = _strand_save(last_user, last_ai, tags=["anchor"], score=0.85,
                            territory_tag=territory, source="anchor", model="gui")
        return TextResult(f"Saved as note {sid}" + (f"  [{territory}]" if territory != "general" else ""))

    if cmd == "strands" or cmd.startswith("strands "):
        if not _STRAND_OK:
            return TextResult("Saved notes aren't available.")
        sub = text[8:].strip() if cmd.startswith("strands ") else ""
        if sub.startswith("search "):
            q = sub[7:].strip()
            if not q:
                return TextResult("Usage: notes search <words>")
            return TextResult(f"Notes search — {q}\n\n" + (_strand_fmt(_strand_search(q)) or "No matches."))
        if sub and sub in _strand_territories():
            results = _strand_list(territory=sub, limit=20)
            return TextResult(f"Notes [{sub}] ({len(results)} found)\n\n" + (_strand_fmt(results) or "None yet."))
        total = _strand_count()
        counts = _strand_terr_counts()
        recent = _strand_list(limit=8)
        counts_line = "  ".join(f"{t}:{n}" for t, n in counts.items()) if counts else "none yet"
        out = f"Saved notes — {total}\n{counts_line}"
        if recent:
            out += "\n\n" + _strand_fmt(recent)
        return TextResult(out)

    if cmd.startswith("strand export") or cmd == "strand export":
        if not (_STRAND_OK and _SFED_OK):
            return TextResult("Note export isn't available.")
        parts = cmd.split()
        territory = parts[2] if len(parts) >= 3 else None
        all_s = _strand_list(territory=territory, limit=5000)
        if not all_s:
            t_label = f" in '{territory}'" if territory else ""
            return TextResult(f"No notes{t_label} to export.")
        terr_defs = _strand_territories()
        label = f"cursiv-{territory or 'all'}"
        pack_text = _sfed_export(all_s, terr_defs, label=label)
        out_path = _CHAT_ROOT / f"{label}-{int(datetime.now().timestamp())}{_PACK_EXT}"
        try:
            out_path.write_text(pack_text, encoding="utf-8")
        except Exception as e:
            return TextResult(f"Export failed: {e}")
        t_label = territory or "all topics"
        return TextResult(
            f"Notes exported\nFile    :  {out_path.name}\n"
            f"Notes   :  {len(all_s)}\nScope   :  {t_label}\n\n"
            f"Transfer via USB / LAN. Import with:  note import {out_path.name}"
        )

    if cmd.startswith("strand import "):
        if not (_STRAND_OK and _SFED_OK):
            return TextResult("Note export isn't available.")
        pack_path = Path(text[14:].strip().strip('"').strip("'"))
        if not pack_path.is_absolute() and not pack_path.exists():
            # "strand export" always writes into _CHAT_ROOT and tells the
            # user to import the bare filename back -- the terminal CLI
            # gets away with resolving that relative to cwd because it's
            # always launched from the repo root, but the packaged GUI's
            # cwd isn't guaranteed to match, so fall back to where the
            # file would actually have landed.
            fallback = _CHAT_ROOT / pack_path
            if fallback.exists():
                pack_path = fallback
        if not pack_path.exists():
            return TextResult(f"File not found: {pack_path}")
        try:
            pack_text = pack_path.read_text(encoding="utf-8")
            in_strands, _in_terr, meta = _sfed_import(pack_text)
        except ValueError as e:
            return TextResult(f"Pack verification failed: {e}")
        except Exception as e:
            return TextResult(f"Import failed: {e}")
        imported = 0
        for s in in_strands:
            try:
                _strand_save(
                    s.get("query", ""), s.get("synthesis", ""),
                    tags=(s.get("tags") or []) + ["federated_import"],
                    score=s.get("score", 0.70),
                    territory_tag=s.get("territory_tag", "general"),
                    source="federation", model=s.get("model", "unknown"),
                    provenance={"source_models": [s.get("model", "?")],
                                "federated": True, "pack_label": meta.get("label", "?")},
                )
                imported += 1
            except Exception:
                pass
        note = ""
        if not meta.get("same_machine"):
            note = "\n(Cross-machine pack — signature does not match this instance; expected for transfers between machines.)"
        return TextResult(f"Notes import\n{_sfed_summary(in_strands, meta)}\n\nImported {imported}/{len(in_strands)} notes.{note}")

    if cmd == "queue" or cmd.startswith("queue "):
        if not _QUEUE_OK:
            return TextResult("Offline Queue not available.")
        sub = text[6:].strip() if cmd.startswith("queue ") else ""
        if not sub or sub == "list":
            return TextResult(_queue_format() or "Queue is empty.")
        if sub.startswith("add "):
            task = sub[4:].strip()
            if not task:
                return TextResult("Usage: queue add <task>")
            entry = _queue_enqueue(task)
            return TextResult(f"Queued:  {entry.get('id', '?')} — {task[:60]}")
        return TextResult("Usage:  queue list  |  queue add <task>")

    if cmd.startswith("remember ") or cmd == "remember":
        if not _STRAND_OK:
            return TextResult("Saved notes aren't available.")
        q = text[9:].strip()
        if not q:
            return TextResult("Type remember <something> to save it, or what do you remember to see what I know.")
        results = _strand_search(q, top_k=5, min_score=0.08)
        if not results:
            return TextResult("No matching notes. Save an answer with: save this")
        return TextResult(f"Local memory — {q}\n\n" + _strand_fmt(results))

    if cmd.startswith("rate"):
        parts = cmd.split()
        score = None
        if len(parts) >= 2:
            tok = parts[1]
            if tok == "good":
                score = 5
            elif tok == "bad":
                score = 1
            elif tok.isdigit() and 1 <= int(tok) <= 5:
                score = int(tok)
        if score is None:
            return TextResult("Usage: rate good  ·  rate bad  ·  rate 1-5")
        if not history:
            return TextResult("No exchange to rate yet.")
        return TextResult(f"Rated {'★' * score}{'☆' * (5 - score)}  ({score}/5)")

    # ── Babel translation ────────────────────────────────────────────────
    if _BABEL_OK and (cmd == "babel" or (cmd.startswith("babel") and len(cmd) > 5 and cmd[5] in (" ", ":"))):
        raw_input = _babel_input(text)
        if not raw_input:
            return TextResult("Usage: babel <text in any language>  ·  babel <text> into <language(s)>")
        into_match = re.search(r"\s+into\s+(.+)$", raw_input, re.IGNORECASE)
        # "translate into Spanish hello ..." names the language first (it was labelled
        # "Translate → English" and sent with the to-English prompt).
        lead = re.match(r"(?i)^(?:in)?to\s+([a-z]+)\s*[:,-]?\s+(.+)$", raw_input, re.S)
        src, targets = "", []
        if lead and lead.group(1).lower() in _LANG_NAMES:
            src, targets = _babel_source(lead.group(2)), [lead.group(1).title()]
        elif into_match and not re.match(r"^i\s+am\b", raw_input, re.IGNORECASE):
            src = _babel_source(raw_input[:into_match.start()])
            targets = _babel_targets(into_match.group(1))
        if src and targets:
            gen, label = _cascade_gen(cfg, [
                {"role": "system", "content": (
                    "You are a precise translation engine. Translate the user's text "
                    "into each requested language, naturally and grammatically, as a native "
                    "speaker would say it. For each, output a header line "
                    "exactly like:\n  ── [Language Name] ──\nfollowed by the translation. "
                    "Return translations only, no explanations."
                )},
                {"role": "user", "content": f"Text to translate:\n{src}\n\nTranslate into: {', '.join(targets)}"},
            ], max_tokens=800)
            return StreamResult(f"Translate — English → {', '.join(targets)}", gen)
        gen, label = _cascade_gen(cfg, [
            {"role": "system", "content": "Translate the following text to English. Return only the translation, nothing else."},
            {"role": "user", "content": raw_input},
        ], max_tokens=1500)
        return StreamResult(f"Translate → English", gen)

    # ── Web search + synthesis ───────────────────────────────────────────
    if cmd.startswith("search:") or cmd.startswith("search "):
        query = text[7:].strip()
        if not query:
            return TextResult("Usage: search <query>")
        if _gate().is_offline():
            return TextResult(f"Web search skipped. {_gate().OFFLINE_MESSAGE}")
        results = _web_search(query)
        if not results:
            return TextResult("No web results found. Check internet connection or try a different query.")
        gen = _chat(
            f"search: {query}", history,
            cfg.get("api_key", ""), None, cfg.get("file_access", False),
            cfg.get("workspace", str(_CHAT_ROOT)), cfg.get("openai_key", ""),
            False, cfg.get("anthropic_key", ""),
        )
        return StreamResult(f"⊕ Web search — {query}\n\n{results}\n", gen)

    # ── Page pull ────────────────────────────────────────────────────────
    if cmd.startswith("pull "):
        if _gate().is_offline():
            return TextResult(f"Page pull skipped. {_gate().OFFLINE_MESSAGE}")
        url = text[5:].strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            import urllib.request as _pur
            req = _pur.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Cursiv/3.14)"})
            with _pur.urlopen(req, timeout=12) as resp:
                raw_html = resp.read(65_536).decode("utf-8", errors="replace")
            body = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.IGNORECASE)
            body = re.sub(r"<[^>]+>", " ", body)
            body = re.sub(r"&[a-zA-Z]{2,6};", " ", body)
            body = re.sub(r"\s+", " ", body).strip()[:4000]
        except Exception as e:
            return TextResult(f"Fetch failed: {e}")
        if len(body) < 80:
            return TextResult("Page returned too little text — may require JavaScript.")
        gen, label = _cascade_gen(cfg, [
            {"role": "user", "content": (
                f"URL: {url}\n\nContent:\n{body}\n\n"
                "Analyze this page. Give: 1) core thesis, 2) key facts worth remembering, "
                "3) any connection to current work. Be precise, no filler."
            )},
        ], max_tokens=800)
        def _finish(full):
            if _STRAND_OK and full:
                _strand_save(f"pull: {url}", full, tags=["pull", "web"], score=0.72,
                             territory_tag="worldmodel", source="pull", model=label)
        return StreamResult(f"Page pull — {url[:70]}", gen, _finish)

    # ── Obsidian ─────────────────────────────────────────────────────────
    if cmd in ("obsidian on", "obsidian off"):
        cfg["obsidian_enabled"] = cmd == "obsidian on"
        _obs_save_config(cfg["obsidian_enabled"], cfg.get("obsidian_path", ""))
        msg = f"Obsidian sync → {'ON' if cfg['obsidian_enabled'] else 'OFF'}"
        if cfg["obsidian_enabled"] and not cfg.get("obsidian_path"):
            msg += "\nSet vault path with: obsidian path <path>"
        return TextResult(msg)

    if cmd.startswith("obsidian path "):
        cfg["obsidian_path"] = text[14:].strip()
        _obs_save_config(cfg.get("obsidian_enabled", False), cfg["obsidian_path"])
        return TextResult(f"Obsidian vault → {cfg['obsidian_path']}")

    if cmd == "obsidian export":
        if not cfg.get("obsidian_path"):
            return TextResult("Set vault path first: obsidian path <path>")
        ok, msg = _obs_export(cfg["obsidian_path"])
        return TextResult(msg)

    if cmd == "obsidian status":
        return TextResult(
            f"Obsidian sync: {'ON' if cfg.get('obsidian_enabled') else 'OFF'}\n"
            f"Vault path: {cfg.get('obsidian_path') or '(not set)'}"
        )

    # ── Direct provider retry ───────────────────────────────────────────
    if cmd in ("grok", "use grok", "try grok"):
        last = cfg.get("last_user_msg", "")
        if not last:
            return TextResult("No previous message to retry with Grok.")
        if not cfg.get("api_key"):
            return TextResult("No xAI key set. Type: key xai-xxxxx")
        gen = _chat(last, history[:-1] if history else [], cfg["api_key"], None, False,
                    cfg.get("workspace", str(_CHAT_ROOT)), cfg.get("openai_key", ""), False, "",
                    force_provider="grok")
        return StreamResult("⟳ Grok re-run", gen)

    if cmd in ("claude", "use claude", "try claude"):
        last = cfg.get("last_user_msg", "")
        if not last:
            return TextResult("No previous message to retry with Claude.")
        if not cfg.get("anthropic_key"):
            return TextResult("No Anthropic key set. Type: anthropic sk-ant-xxxxx")
        gen = _chat(last, history[:-1] if history else [], "", None, False,
                    cfg.get("workspace", str(_CHAT_ROOT)), "", False, cfg["anthropic_key"],
                    force_provider="claude")
        return StreamResult("⟳ Claude re-run", gen)

    if cmd in ("chatgpt", "gpt", "openai", "use chatgpt", "use gpt", "use openai",
               "try chatgpt", "try gpt", "try openai"):
        last = cfg.get("last_user_msg", "")
        if not last:
            return TextResult("No previous message to retry with ChatGPT.")
        if not cfg.get("openai_key"):
            return TextResult("No OpenAI key set. Type: openai sk-xxxxx")
        gen = _chat(last, history[:-1] if history else [], "", None, False,
                    cfg.get("workspace", str(_CHAT_ROOT)), cfg["openai_key"], False, "",
                    force_provider="openai")
        return StreamResult("⟳ ChatGPT re-run", gen)

    # ── Postal — sealed encrypted letters (read/manage side; composing a
    # new letter needs a multi-line dialog, handled by chat_panel.py) ──────
    if cmd == "letters" or cmd in ("letters for me", "letters from me"):
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        postal_user = cfg.get("postal_user", "joshua")
        if cmd == "letters for me":
            llist, heading = _postal_for(postal_user), f"LETTERS FOR {postal_user.upper()}"
        elif cmd == "letters from me":
            llist, heading = _postal_from(postal_user), f"LETTERS FROM {postal_user.upper()}"
        else:
            llist, heading = _postal_all(), "ALL SEALED LETTERS"
        if not llist:
            return TextResult(f"{heading}\n\nNo sealed letters found.")
        lines = [f"{heading}"]
        for e in llist:
            badge = "read" if e.get("read") else "unread"
            hint = f"  ({e['hint']})" if e.get("hint") else ""
            lines.append(
                f"{e['id']}  {e.get('from_display', '?')} → {e.get('for_display', '?')}  "
                f"{e.get('sealed', '')[:10]}  {badge}{hint}"
            )
        return TextResult("\n".join(lines))

    if cmd.startswith("open letter ") or cmd.startswith("letter "):
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        lid = (text[12:] if cmd.startswith("open letter ") else text[7:]).strip()
        if not lid:
            return TextResult("Usage: open letter <id>")
        entry = _postal_entry(lid)
        if not entry:
            return TextResult(f"Letter {lid} not found.")
        body = _postal_open(lid)
        if body is None:
            return TextResult("Decryption failed. This seal cannot be opened on this machine.")
        sig = {
            "verified": "✓ VERIFIED", "verified_rotated": "✓ VERIFIED (signed with sender's prior key)",
            "verified_compromised": "⟳ COHERENCE DEGRADED (signed with a compromised key)",
            "unverified": "~ unverified (sender not in contacts)",
            "unsigned": "unsigned (pre-identity letter)", "INVALID": "✗ SIGNATURE INVALID",
        }.get(_postal_sig_status(lid), _postal_sig_status(lid))
        header = f"from: {entry.get('from_display', '?')}  to: {entry.get('for_display', '?')}  {entry.get('sealed', '')[:10]}\n{sig}"
        if entry.get("hint"):
            header += f"\nhint: {entry['hint']}"
        return TextResult(f"{header}\n\n{body}")

    if cmd.startswith("council letter "):
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        lid = text[15:].strip()
        if not lid:
            return TextResult("Usage: council letter <id>")
        postal_user = cfg.get("postal_user", "joshua")
        reading = _postal_council(lid, postal_user, cfg)
        return TextResult(reading)

    if cmd.startswith("seal export "):
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        lid = text[12:].strip()
        result = _postal_export(lid)
        if result is None:
            return TextResult("Export failed — letter not found or cannot decrypt.")
        pack_path, passphrase = result
        return TextResult(
            f"Sealpack exported\nfile: {pack_path}\npassphrase: {passphrase}\n\n"
            "Share this passphrase with the recipient out-of-band. It is shown once and never stored."
        )

    if cmd.startswith("seal import "):
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        rest = text[12:].strip()
        # Last whitespace-separated token is the passphrase; everything
        # before it is the (possibly space-containing) file path.
        parts = rest.rsplit(None, 1)
        if len(parts) != 2:
            return TextResult("Usage: seal import <filepath> <passphrase>")
        pack_file, passphrase = parts
        new_id = _postal_import(pack_file.strip('"').strip("'"), passphrase)
        if new_id is None:
            return TextResult("Import failed — wrong passphrase or corrupted pack.")
        return TextResult(f"Sealed locally as: {new_id}")

    if cmd == "postal user" or cmd.startswith("postal user "):
        new_user = text[12:].strip().lower() if cmd.startswith("postal user ") else ""
        if not new_user:
            return TextResult(f"Current postal identity: {cfg.get('postal_user', 'joshua')}")
        cfg["postal_user"] = new_user
        return TextResult(f"Postal identity set to: {new_user}")

    if cmd.startswith("postal setup ") or cmd == "postal setup":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        name = text[13:].strip() if cmd.startswith("postal setup ") else ""
        if not name:
            return TextResult("Usage: postal setup <your name>")
        try:
            meta = _postal_setup(name)
        except Exception as e:
            return TextResult(f"Setup failed: {e}")
        cfg["postal_user"] = meta.get("name", name).lower()
        return TextResult(
            f"Identity created\nName: {meta.get('name', name)}\nKey ID: {meta.get('key_id', '?')[:8]}\n"
            f"Public: {meta.get('pubkey', '?')}\n\n"
            f"Share this public key with anyone you want to receive letters from. "
            f"They add you with: postal add user {name} <your key>"
        )

    if cmd == "postal my key":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        my_id = _postal_my_id()
        if not my_id:
            return TextResult("No identity set up yet. Run: postal setup <your name>")
        return TextResult(
            f"Your Cursiv identity\nName: {my_id.get('name', '?')}\n"
            f"Key ID: {my_id.get('key_id', '?')[:8]}\nPublic: {my_id.get('pubkey', '?')}"
        )

    if cmd.startswith("postal add user ") or cmd == "postal add user":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        parts = text[16:].strip().split() if cmd.startswith("postal add user ") else []
        if len(parts) < 2:
            return TextResult("Usage: postal add user <name> <pubkey>")
        try:
            entry = _postal_add_contact(parts[0], parts[1])
        except ValueError as e:
            return TextResult(f"Invalid public key: {e}")
        return TextResult(f"Contact added: {parts[0]}  (key-id: {entry.get('key_id', '?')[:8]})")

    if cmd.startswith("postal remove user "):
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        name = text[19:].strip()
        ok = _postal_rm_contact(name)
        return TextResult(f"Contact removed: {name}" if ok else f"Contact not found: {name}")

    if cmd.startswith("postal rotate") or cmd == "postal rotate key":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        compromised = "compromised" in cmd or "leaked" in cmd
        reason = "key compromised — attacker may have private key" if compromised else "manual rotation"
        try:
            rot = _postal_rotate(reason=reason, compromised=compromised)
        except Exception as e:
            return TextResult(f"Rotation failed: {e}")
        if not rot:
            return TextResult("Rotation failed — no identity set up. Run: postal setup <name>")
        note = (
            "\n\nCoherence degradation will activate on the retired key — any letter later "
            "read through it returns shifted content. The attacker sees output, not truth."
            if compromised else ""
        )
        return TextResult(
            f"Key rotation\nOld key ID: {rot.get('old_key_id', '?')[:8]} (archived locally)\n"
            f"New key ID: {rot.get('new_key_id', '?')[:8]}\nNew public: {rot.get('new_pubkey', '?')}\n\n"
            f"Update your contacts: postal add user <your name> <new key>{note}"
        )

    if cmd == "postal key history":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        hist = _postal_key_history()
        if not hist:
            return TextResult("Key history\n\nNo retired keys.")
        lines = ["Key history"]
        for hk in hist:
            flag = "  COMPROMISED — coherence degradation active" if hk.get("compromised") else ""
            lines.append(f"{hk.get('key_id', '?')[:8]}  retired:{hk.get('retired_at', '?')[:10]}  {hk.get('reason', '?')[:40]}{flag}")
        return TextResult("\n".join(lines))

    if cmd == "postal contacts":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        clist = _postal_contacts()
        if not clist:
            return TextResult("Contacts\n\nNo contacts yet. Use: postal add user <name> <pubkey>")
        lines = [f"Contacts ({len(clist)})"]
        for c in clist:
            lines.append(f"{c['name']:<16}  id:{c.get('key_id', '?')[:8]}  added:{c.get('added', '?')[:10]}")
        return TextResult("\n".join(lines))

    if cmd.startswith("legacy import "):
        imp_path = text[14:].strip().strip('"').strip("'")
        if not imp_path:
            return TextResult("Usage: legacy import <path to .legacypack file>")
        try:
            count, skipped = _legacy_import_pack(imp_path)
        except (FileNotFoundError, ValueError) as e:
            return TextResult(str(e))
        except Exception as e:
            return TextResult(f"Import failed: {e}")
        if count == 0 and not skipped:
            return TextResult("No letters found in pack.")
        out = []
        if count:
            out.append(f"Imported {count} letter(s).")
        if skipped:
            out.append(f"Skipped {len(skipped)} duplicate(s): " + ", ".join(skipped))
        out.append("Letters are now in the vault.")
        return TextResult("\n".join(out))

    # ── Image generation (paid OpenAI key only) ─────────────────────────
    # Offline/local models and the free keys can't generate images -- say so
    # plainly instead of letting a text model pretend it drew something.
    img_prompt = _image_request_prompt(text)
    if img_prompt is not None:
        prompt = img_prompt
        if not prompt:
            return TextResult("Usage: image <description>")
        from cursiv_v215.ui.chat_app import _saved_key
        oai_key = cfg.get("openai_key", "")
        cf_id = cfg.get("cf_account_id", "") or _saved_key("cf_account_id")
        cf_tok = cfg.get("cf_api_token", "") or _saved_key("cf_api_token")
        if not oai_key and not (cf_id and cf_tok):
            return TextResult(IMAGE_GEN_NEEDS_KEY)
        img_dir = Path(cfg.get("workspace", str(_CHAT_ROOT))) / ".cursiv" / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        img_path = img_dir / f"image_{stamp}.png"
        revised, used_model, errors = prompt, "", []
        if oai_key:
            import base64 as _img_b64
            import urllib.request as _img_req
            try:
                import openai as _oai_img
                img_client = _oai_img.OpenAI(api_key=oai_key)
                for model in IMAGE_GEN_MODELS:
                    try:
                        resp = img_client.images.generate(model=model, prompt=prompt, size="1024x1024", n=1)
                    except Exception as e:
                        errors.append(f"{model}: {e}")
                        continue
                    item = resp.data[0]
                    if getattr(item, "b64_json", None):
                        img_path.write_bytes(_img_b64.b64decode(item.b64_json))
                    else:
                        _img_req.urlretrieve(item.url, str(img_path))
                    revised = getattr(item, "revised_prompt", None) or prompt
                    used_model = model
                    break
            except Exception as e:
                errors.append(f"OpenAI: {e}")
        if not used_model and cf_id and cf_tok:
            try:
                img_path = img_dir / f"image_{stamp}.jpg"
                img_path.write_bytes(_cloudflare_image(prompt, cf_id, cf_tok))
                used_model = "FLUX.1-schnell (Cloudflare, free)"
            except Exception as e:
                errors.append(str(e))
        if not used_model:
            return TextResult("Image generation failed:\n" + "\n".join(errors[-3:]))
        if _STRAND_OK:
            _strand_save(f"image: {prompt[:200]}", f"Generated: {img_path}\nRevised prompt: {revised[:300]}",
                         tags=["image", used_model], score=0.70, territory_tag="creative", source="image", model=used_model)
        note = f"\n\nThe model revised the prompt to:\n{revised[:300]}" if revised != prompt else ""
        return TextResult(f"Image generated with {used_model}  ({img_path.name}){note}", image_path=str(img_path))

    return None


def hey_prefix(raw: str) -> tuple[str, str]:
    """Detect a provider-routing prefix -- the explicit "hey <provider> ..."
    form, or the shorter "<provider> <question>" form (e.g. "grok what's the
    weather" routes that new question straight to Grok, saved to history
    normally, exactly like "hey grok ..."). This is distinct from the bare
    "grok"/"claude"/"chatgpt" command with no question, which retries the
    *previous* message instead (see handle_command) -- that only matches
    when there's nothing trailing, so it can't collide with this.
    Returns (force_provider, stripped_text)."""
    lower = raw.lower()
    for prefix, fp in (
        ("hey council ", "council"), ("hey grok ", "grok"), ("hey claude ", "claude"),
        ("hey chat ", "openai"), ("hey openai ", "openai"), ("hey gpt ", "openai"),
        ("hey ollama ", "ollama"),
        ("grok ", "grok"), ("claude ", "claude"),
        ("chatgpt ", "openai"), ("gpt ", "openai"), ("openai ", "openai"),
    ):
        if lower.startswith(prefix):
            return fp, raw[len(prefix):].strip()
    return "", raw


# ── Voice — caller (chat_panel.py) owns the mic-record UI affordance
# (start/stop button); this function does the actual capture, STT, and
# Babel-clean pass, identical to the terminal CLI's "voice"/"listen". ─────

def voice_turn(cfg: dict, duration_s: float = 5.0, raw_mode: bool = False,
                status_cb: Optional[Callable[[str], None]] = None) -> TextResult:
    if not _VOICE_OK or not _voice_avail():
        return TextResult("Voice agent unavailable — needs: pip install faster-whisper sounddevice")
    cb = status_cb or (lambda m: None)
    try:
        pcm, arr = _voice_record(duration_s=duration_s, status_cb=cb)
        raw_text = _voice_transcribe(pcm, float32_arr=arr, status_cb=cb)
    except RuntimeError as e:
        return TextResult(str(e))
    except Exception as e:
        return TextResult(f"Voice capture error: {e}")

    if not raw_text:
        return TextResult("Nothing heard — adjust mic or try again.")

    if raw_mode:
        return TextResult(raw_text)

    # Stage 2: Babel binary clean pass -- fixes filler words/errors and
    # translates non-English speech, same pipeline the CLI uses.
    try:
        decoded = _babel_decode(_babel_encode(raw_text))
        gen, _label = _cascade_gen(cfg, [
            {"role": "system", "content": _VOICE_CLEAN_SYS},
            {"role": "user", "content": decoded},
        ], max_tokens=300)
        cleaned = "".join(c for c in gen if c != RATE_SENTINEL)
        return TextResult((cleaned.strip() or raw_text))
    except Exception:
        return TextResult(raw_text)


# ── Training data manager ────────────────────────────────────────────────
# Images, free-form notes and pasted JSON all feed one file
# (cursiv_v215/training/paths.py's TRAINING_JSONL, read by LoRA training) --
# one store, one schema ({"prompt", "response", "quality", "agent_id",
# "timestamp", "source"}).
try:
    from cursiv_v215.training.paths import TRAINING_JSONL as _TRAINING_JSONL
except Exception:
    _TRAINING_JSONL = Path.home() / ".cursiv" / "training_data.jsonl"

_TEXT2JSON_VERBS = ("translate", "convert", "turn", "format")


def _looks_like_text_to_json_request(text: str) -> bool:
    """Fuzzy match for phrases like 'translate my notes into JSON for
    training' -- order-independent keyword co-occurrence rather than a
    rigid phrase, since there's no one fixed way to ask for this."""
    t = text.lower()
    return "json" in t and "train" in t and any(v in t for v in _TEXT2JSON_VERBS)


def list_training_entries() -> list[dict]:
    """Read every entry in the training JSONL. Each dict gets a '_line'
    key (its 0-based line number) so the caller can select/delete it."""
    if not _TRAINING_JSONL.exists():
        return []
    entries = []
    for i, line in enumerate(_TRAINING_JSONL.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if isinstance(d, dict):
            d["_line"] = i
            entries.append(d)
    return entries


def add_training_entry_json(raw_json: str) -> tuple[bool, str]:
    """Validate and append a manually-pasted JSON object."""
    raw_json = raw_json.strip()
    if not raw_json:
        return False, "Paste a JSON object first."
    try:
        entry = json.loads(raw_json)
    except Exception as e:
        return False, f"Invalid JSON: {e}"
    if not isinstance(entry, dict):
        return False, 'JSON must be an object, e.g. {"prompt": "...", "response": "..."}'
    entry.setdefault("timestamp", datetime.now().isoformat())
    entry.setdefault("source", "manual")
    entry.setdefault("quality", 1.0)
    _TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True, "Added to training data."


def delete_training_entry(line_index: int) -> tuple[bool, str]:
    """Remove one entry by its line number in the JSONL file."""
    if not _TRAINING_JSONL.exists():
        return False, "No training data file yet."
    lines = _TRAINING_JSONL.read_text(encoding="utf-8").splitlines()
    if not (0 <= line_index < len(lines)):
        return False, "Entry not found — the list may be out of date."
    del lines[line_index]
    _TRAINING_JSONL.write_text(
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )
    return True, "Deleted."


def _run_llm_once(messages: list[dict], cfg: dict) -> str:
    """Collect one full (non-streaming) response, offline-first: Ollama
    before any cloud provider, matching Cursiv's always-works-air-gapped
    default -- cloud keys are only ever a fallback, never a requirement."""
    try:
        text = "".join(c for c in _call_ollama(messages) if c and c != RATE_SENTINEL)
        if text.strip():
            return text
    except Exception:
        pass
    xai_key = cfg.get("api_key", "")
    if xai_key:
        try:
            text = "".join(c for c in _call_xai_stream(messages, xai_key) if c and c != RATE_SENTINEL)
            if text.strip():
                return text
        except Exception:
            pass
    ant_key = cfg.get("anthropic_key", "")
    if ant_key:
        try:
            text = "".join(c for c in _call_claude_direct(messages, ant_key) if c and c != RATE_SENTINEL)
            if text.strip():
                return text
        except Exception:
            pass
    oai_key = cfg.get("openai_key", "")
    if oai_key:
        try:
            text = "".join(c for c in _call_openai_direct(messages, oai_key) if c and c != RATE_SENTINEL)
            if text.strip():
                return text
        except Exception:
            pass
    return ""


def text_to_training_entry(notes: str, cfg: dict) -> tuple[bool, str, Optional[dict]]:
    """Ask whatever model is available to turn free-form notes into a
    structured {prompt, response} JSON training example."""
    notes = notes.strip()
    if not notes:
        return False, "No notes to translate.", None

    sys_prompt = (
        "Convert the user's notes into a single JSON object with exactly two "
        'keys: "prompt" (a plausible question or instruction these notes '
        'would answer) and "response" (the notes, cleaned up, with all '
        "information preserved — do not drop or invent facts). Return ONLY "
        "the JSON object: no markdown fences, no extra commentary."
    )
    raw = _run_llm_once(
        [{"role": "system", "content": sys_prompt}, {"role": "user", "content": notes}], cfg
    )
    if not raw.strip():
        return False, ("No model available to translate notes — start Ollama, "
                        "or set a cloud API key."), None

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = json.loads(cleaned)
    except Exception:
        parsed = None

    if isinstance(parsed, dict) and parsed.get("response"):
        entry = {
            "prompt":    str(parsed.get("prompt", "Notes")),
            "response":  str(parsed["response"]),
            "quality":   1.0,
            "agent_id":  "text_to_json",
            "timestamp": datetime.now().isoformat(),
            "source":    "text_to_json",
        }
    else:
        # Model didn't return clean JSON -- store the raw notes rather
        # than silently losing them.
        entry = {
            "prompt":    "Notes",
            "response":  notes,
            "quality":   1.0,
            "agent_id":  "text_to_json",
            "timestamp": datetime.now().isoformat(),
            "source":    "text_to_json_fallback",
        }

    _TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True, "Notes translated and added to training data.", entry


# ── Image generation ────────────────────────────────────────────────────
# Newest first; dall-e-3 kept as a fallback for older keys/accounts.
IMAGE_GEN_MODELS = ("gpt-image-1", "dall-e-3")

CF_IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"

IMAGE_GEN_CLOUDFLARE_HOWTO = (
    "Free option — Cloudflare Workers AI (no card needed, about 100+ images a day):\n"
    "  1. Sign up free at dash.cloudflare.com\n"
    "  2. Copy your Account ID (right side of the Workers & Pages overview page)\n"
    "  3. My Profile → API Tokens → Create Token → use the \"Workers AI\" template\n"
    "  4. In Cursiv type:  cloudflare <account-id> <token>"
)

IMAGE_GEN_NEEDS_KEY = (
    "Image generation needs an online key — it can't be done offline.\n\n"
    "Cursiv's offline features (Ollama) and the free Gemini/Groq keys can read "
    "and describe images you paste in, but they can't create new ones.\n\n"
    + IMAGE_GEN_CLOUDFLARE_HOWTO + "\n\n"
    "Paid option — OpenAI (about $0.01-0.04 per image, billed by OpenAI):\n"
    "  Get a key at platform.openai.com/api-keys, then type:  openai sk-...\n\n"
    "Then try your image again."
)


def _cloudflare_image(prompt: str, account_id: str, token: str) -> bytes:
    import base64 as _b64cf
    import urllib.request
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{CF_IMAGE_MODEL}"
    req = urllib.request.Request(
        url, data=json.dumps({"prompt": prompt, "steps": 4}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore")[:200]
        if e.code == 429 or "neuron" in detail.lower():
            raise RuntimeError("Cloudflare's free daily image allowance is used up — it resets at midnight UTC.")
        raise RuntimeError(f"Cloudflare {e.code}: {detail}")
    img = (data.get("result") or {}).get("image")
    if not img:
        raise RuntimeError(f"Cloudflare returned no image: {str(data.get('errors'))[:200]}")
    return _b64cf.b64decode(img)

_IMAGE_ASK_RE = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)?"
    r"(?:generate|create|make|draw|paint|render|design)\s+(?:me\s+)?(?:an?\s+)?"
    r"(?:image|picture|pic|photo|drawing|painting|illustration|logo)\s+(?:of|showing|with|for)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def _image_request_prompt(text: str) -> Optional[str]:
    """'image <prompt>' or a plain-English ask like 'make me a picture of a
    dog' -> the prompt ('' if the command had none). None if not an image ask."""
    t = text.strip()
    if t.lower() == "image":
        return ""
    if t.lower().startswith("image "):
        return t[6:].strip()
    # Whole sentence, not just the tail: "a logo for my bakery" needs "logo".
    return t.rstrip("?.!") if _IMAGE_ASK_RE.match(t) else None


# ── Vision: one shared "describe this image" chain ───────────────────────
# Paid keys first when the user set them (an opt-in upgrade), then the
# free Gemini key, then a local Ollama vision model -- the floor that works
# with no key and no internet, per the Ollama-first rule.

OLLAMA_VISION_MODELS = ("gemma3", "qwen2.5vl", "llama3.2-vision", "minicpm-v", "llava", "moondream")
OLLAMA_VISION_DEFAULT = "gemma3:4b"


def _ollama_vision_model() -> str:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            names = [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return ""
    for family in OLLAMA_VISION_MODELS:
        for n in names:
            if n.split(":")[0] == family:
                return n
    return ""


def _vision_describe(img_b64: str, mime: str, prompt_text: str, cfg: dict) -> tuple[str, str]:
    import urllib.request
    from cursiv_v215.ui.chat_app import _saved_key, GEMINI_URL, GEMINI_MODELS
    # Local first (a photo stays on this computer when the image model is installed);
    # online keys only when nothing local can read it and the internet isn't blocked.
    model = _ollama_vision_model()
    if model:
        try:
            body = json.dumps({"model": model, "prompt": prompt_text,
                               "images": [img_b64], "stream": False}).encode()
            req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                text = json.loads(r.read()).get("response", "")
            if text.strip():
                return text, f"{model} (local)"
        except Exception:
            pass
    try:
        from cursiv_v215.core import netgate as _ng
        if not _ng.allowed():
            return "", ""
    except Exception:
        return "", ""
    ant_key, oai_key = cfg.get("anthropic_key", ""), cfg.get("openai_key", "")
    gem_key = cfg.get("gemini_key", "") or _saved_key("gemini_key")

    if ant_key:
        try:
            import anthropic as _anth_v
            resp = _anth_v.Anthropic(api_key=ant_key).messages.create(
                model="claude-sonnet-4-6", max_tokens=600,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": img_b64}},
                    {"type": "text", "text": prompt_text},
                ]}],
            )
            return resp.content[0].text, "Claude"
        except Exception:
            pass

    if oai_key:
        try:
            import openai as _oai_v
            resp2 = _oai_v.OpenAI(api_key=oai_key).chat.completions.create(
                model="gpt-4o", max_tokens=600,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text", "text": prompt_text},
                ]}],
            )
            return resp2.choices[0].message.content, "GPT-4o"
        except Exception:
            pass

    if gem_key:
        body = json.dumps({"contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": mime, "data": img_b64}},
            {"text": prompt_text},
        ]}]}).encode()
        for model in GEMINI_MODELS:
            try:
                req = urllib.request.Request(
                    GEMINI_URL.format(model=model), data=body,
                    headers={"Content-Type": "application/json", "x-goog-api-key": gem_key})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read())
                cand = (data.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                if text.strip():
                    return text, "Gemini"
            except Exception:
                continue

    return "", ""


_NO_VISION_HELP = (
    "No vision model available. Free options: install a local one with "
    f"'ollama pull {OLLAMA_VISION_DEFAULT}' (works offline), or add a free Gemini "
    "key (type 'gemini AIza...'). Anthropic/OpenAI keys also work."
)


def image_to_training_entry(image_bytes: bytes, cfg: dict, ext: str = "png") -> tuple[bool, str, Optional[dict]]:
    """Run vision analysis on an uploaded image and store the description
    as a JSON training example. Mirrors analyze_pasted_image's vision call
    but writes to the training store instead of strand memory."""
    img_dir = Path(cfg.get("workspace", str(_CHAT_ROOT))) / ".cursiv" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"train_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.{ext}"
    img_path.write_bytes(image_bytes)

    import base64 as _b64t
    img_b64 = _b64t.b64encode(image_bytes).decode()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "gif": "image/gif", "webp": "image/webp"}.get(ext.lower(), "image/png")
    prompt_text = ("Describe this image in detail — objects, text, layout, and anything "
                   "notable — as a single clear paragraph suitable for training data.")

    vision_result, vision_provider = _vision_describe(img_b64, mime, prompt_text, cfg)
    if not vision_result:
        return False, _NO_VISION_HELP, None

    entry = {
        "prompt":     prompt_text,
        "response":   vision_result,
        "quality":    1.0,
        "agent_id":   "image_upload",
        "timestamp":  datetime.now().isoformat(),
        "source":     "image_upload",
        "image_path": str(img_path),
    }
    _TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with _TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True, f"Image analyzed via {vision_provider} and added to training data.", entry


# ── "photo <path> <question>": the chat's paperclip ─────────────────────────
_PHOTO_CMD = re.compile(r'(?is)^photo\s+(?:"([^"]+)"|(\S+))\s*(.*)$')
_NO_LOCAL_VISION = (
    "Reading photos offline needs Cursiv's image model on this computer, and none is installed. "
    "Install it in Setup (step 5: gemma3 4B, 3.3 GB; needs the internet once). "
    "With the internet blocked, Cursiv won't send the photo anywhere.")


def describe_photo(path: str, question: str, cfg: dict) -> TextResult:
    """Ask the image model about a photo. Local model first; the answer says where it was read."""
    import base64 as _b64p
    import io
    p = Path(path)
    if not p.is_file():
        return TextResult(f"No photo at {p}.")
    try:
        from PIL import Image
        with Image.open(p) as img:                      # smaller is much faster, and enough to read
            img = img.convert("RGB")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO(); img.save(buf, "JPEG", quality=88)
        data, mime = buf.getvalue(), "image/jpeg"
    except Exception:
        data, mime = p.read_bytes(), "image/jpeg"
    q = question.strip() or "Describe what this photo shows, as an observer in the field would: what, where, condition."
    prompt = (q + "\n\nSay only what is visible in the photo. If something can't be told from the photo "
              "(species, exact size, chemistry), say so instead of guessing.")
    text, provider = _vision_describe(_b64p.b64encode(data).decode(), mime, prompt, cfg)
    if not text:
        try:
            from cursiv_v215.core import netgate as _ng
            offline = not _ng.allowed()
        except Exception:
            offline = True
        return TextResult(_NO_LOCAL_VISION if offline or not _ollama_vision_model() else _NO_VISION_HELP)
    local = provider.endswith("(local)")
    where = (f"read by {provider[:-8]} on this computer" if local
             else f"sent to {provider} online: this photo left this computer")
    return TextResult(f"{text.strip()}\n\n*[Sources: your photo ({p.name}), {where}. The AI's reading of a photo can "
                      f"be wrong; check anything that matters.]*", image_path=str(p))


# ── Paste image from clipboard → vision analysis → strand. Caller passes
# already-extracted PNG bytes (from Qt's clipboard); the vision-API calls
# and strand save live here so they match the terminal CLI's "paste". ────

def analyze_pasted_image(png_bytes: bytes, cfg: dict, width: int, height: int) -> TextResult:
    import base64 as _b64img

    img_dir = Path(cfg.get("workspace", str(_CHAT_ROOT))) / ".cursiv" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"paste_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    img_path.write_bytes(png_bytes)

    img_b64 = _b64img.b64encode(png_bytes).decode()
    vision_result, vision_provider = _vision_describe(
        img_b64, "image/png",
        "Describe what you see in this image. Be specific and useful. "
        "Flag anything relevant to code, design, architecture, or ongoing work.", cfg)

    if _STRAND_OK:
        body = vision_result or f"Image pasted: {img_path} ({width}x{height}px)"
        _strand_save(f"paste: image {img_path.stem}", body, tags=["image", "paste", "vision"],
                     score=0.72, territory_tag="worldmodel", source="paste", model=vision_provider or "none")

    header = f"Image pasted — {width}×{height}px\n\n"
    if vision_result:
        return TextResult(f"{header}Vision analysis (via {vision_provider}):\n\n{vision_result}", image_path=str(img_path))
    return TextResult(f"{header}Image saved, no analysis. {_NO_VISION_HELP}", image_path=str(img_path))


# ── Postal compose — caller (chat_panel.py) collects recipient/hint/body
# via a dialog; the actual sealing call is identical to the terminal CLI's
# "write to" flow. ──────────────────────────────────────────────────────

def postal_compose(sender_user: str, recipient_raw: str, hint: str, content: str) -> TextResult:
    if not _POSTAL_OK:
        return TextResult("Postal module unavailable.")
    if not content.strip():
        return TextResult("Nothing written — letter not sent.")
    resolved = _postal_resolve(recipient_raw)
    recipient_key = resolved[1] if resolved else recipient_raw.lower().replace(" ", "")
    recipient_disp = resolved[0] if resolved else recipient_raw.title()
    my_id = _postal_my_id()
    sender_key = my_id.get("name", sender_user).lower() if my_id else sender_user
    sender_disp = my_id.get("name", sender_user).title() if my_id else sender_user.title()
    lid = _postal_seal(
        sender_key=sender_key, sender_display=sender_disp,
        recipient_key=recipient_key, recipient_display=recipient_disp,
        content=content, hint=hint,
    )
    return TextResult(
        f"Sealed\nid: {lid}\nfor: {recipient_disp}\n"
        f"signed: {'yes — Ed25519' if my_id else 'no — run postal setup first'}\n"
        f"readable: on this machine only"
    )


# ── Pending file write -- caller (chat_panel.py) shows the confirmation
# dialog (needs Qt, on the main thread); the actual write happens here via
# the same execute_tool() the terminal CLI's approval flow calls. ─────────

def approve_write(path: str, content: str, workspace: str) -> TextResult:
    result = _execute_tool("write_file", {"path": path, "content": content}, Path(workspace))
    return TextResult(f"✓ {result}")

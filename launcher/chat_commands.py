"""
Cursiv — chat panel command router.

The terminal CLI (cursiv_v215/ui/chat_cli.py) has ~40 built-in commands
(key management, council deliberation, Babel translation, strand memory,
Codex/Hermes agents, blast-to-board, Obsidian sync, substrate, etc.) all
built directly against terminal I/O -- print() with ANSI codes, input()
for prompts. This module ports the ROUTING + the calls to the same
underlying functions (babel_agent, codex_agent, async_council, strand
store, postal, etc.) to a UI-agnostic form the GUI chat panel can render,
without touching or duplicating the terminal CLI itself.

Not handled here at all (need a real dialog or widget, not a text command --
these are intercepted directly in chat_panel.py's _try_dialog_command /
_send instead of ever reaching this module):
  - voice / listen / paste  -- mic control + clipboard-image widgets
  - write to / legacy       -- multi-line compose + PIN-entry dialogs
  - clear                   -- wipes the transcript widget + in-memory
                                history, neither of which this UI-agnostic
                                module has a handle to

Everything else the terminal CLI has -- key/openai/anthropic, files,
workspace, mode, tier, offline, governor, status, help, codex, hermes,
council/full/deliberate, anchor this, strands/remember/strand export/
strand import, grow, ref, search, pull, rate, funforge (start/done/
extend), babel, blast, substrate, obsidian, letters/open letter/council
letter, postal *, legacy import, image, queue, grok/claude direct retry,
overseer, "hey <provider>" routing -- is handled here, calling the exact
same lower-level functions the CLI calls. Full parity with the terminal's
command set as of the chat-panel-only window (v3.14-U21); "exit" is the
one deliberate omission, since there's no terminal process to quit.
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

try:
    from cursiv_v215.ui.chat_cli import _save_key, _probe_xai, _probe_openai, _probe_claude
except Exception:
    def _save_key(field, value): pass
    def _probe_xai(key): return None
    def _probe_openai(key): return None
    def _probe_claude(key): return None

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
    from cursiv_v215.web.board_client import (
        board_login as _board_login,
        board_register as _board_register,
        board_logout as _board_logout,
        board_whoami as _board_whoami,
        board_blast as _board_blast,
    )
    _BOARD_OK = True
except Exception:
    _BOARD_OK = False
    def _board_login(u, p): return (False, "board client unavailable")
    def _board_register(u, p): return (False, "board client unavailable")
    def _board_logout(): pass
    def _board_whoami(): return None
    def _board_blast(t, s): return (False, "board client unavailable")

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
    from cursiv_v215.substrate.activator import get_activator as _get_activator
    _SUBSTRATE_OK = True
except Exception:
    _SUBSTRATE_OK = False
    def _get_activator(): return None

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


def _gate():
    from cursiv_v215.core import netgate
    return netgate


def _default_cfg() -> dict:
    """Same shape as chat_cli.py's cfg dict, minus the terminal-only fields."""
    return {
        "file_access":      False,
        "confirm_mode":     "confirm",   # same safe default as the terminal CLI -- every write needs approval until "mode" toggles it
        "funforge_session": None,
        "workspace":        str(_CHAT_ROOT),
        "obsidian_enabled": False,
        "obsidian_path":    "",
        "overseer_mode":    False,
        "trust_tier":       1 if _gate().is_offline() else 3,
        "offline_mode":     _gate().is_offline(),
        "cursiv_mode":      "personal",
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

    return StreamResult(f"⬡ Codex — {prompt[:60]}", stream(), _finish)


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
        return StreamResult(f"⬡ Agent council — {len(agents[:6])} agents", stream(), None)

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
        return StreamResult(f"⬡ @{a['name']}", gen, None)
    if t.startswith("@"):
        return None            # a lone "@something" -- let normal chat handle it
    return TextResult(custom.listing())

_HELP_TEXT = """\
KEYS & ACCESS
  key <xai-key>            set xAI Grok API key       (starts with xai-)
  openai <key>              set OpenAI API key          (starts with sk-)
  anthropic <key>          set Anthropic API key       (starts with sk-ant-)
  gemini <key>              set a FREE Google Gemini key (starts with AIza)
  groq <key>                set a FREE Groq key          (starts with gsk_)
  free keys                 where to get free AI keys
  cloud on / off / status   Cursiv Cloud backup when no local model is ready
  files on / off            enable / disable file-system access
  workspace <path>          sandbox root for file tools
  mode                      toggle write mode  (auto <-> confirm)

CODEX AGENT (offline code specialist)
  evolve <idea>             Cursiv writes itself a new ability (a plugin) — you approve it first
  plugins                   your plugins (plugin show/off/on/remove <name>)
  projects                  running summaries of your ongoing projects (project show/forget <name>)
  tone <blunt|warm|brief|playful|legacy|teacher|normal>   how Cursiv talks to you
  style                     your tone + the rules Cursiv learned from your corrections
  agents                    your custom agents (agent new <name>: <job>, then @name <message>)
  agent council <question>  ask all your agents, then combine their views
  codex <prompt>            coding help with every step listed (codex help for more)
                            code questions in normal chat use the same coding brain

WEB SEARCH
  search <query>            search the web right now + AI synthesis
  pull <url>                fetch + analyze any URL -> auto-strand the insight

VOICE (mic button, or type these)
  voice / voice <seconds>   record -> speech-to-text -> Babel clean -> send
  voice raw / listen        speech-to-text only, no cleaning pass
  paste                     paste a clipboard image -> vision analysis

BABEL (universal translation)
  babel <text>              any language -> English
  babel <text> into <lang>  English -> one or more target languages

COUNCIL (parallel multi-model deliberation)
  council <question>        all providers fire at once, synthesis deliberates
  /full <question>          full deliberation, no signal extraction
  hey council <question>    inline routing prefix (same as council)

SUBSTRATE FORK -- RUW / Curs.
  substrate                 activate last council synthesis into RUW layer
  substrate status          show RUW layer state
  substrate weave <query>   find resonant nodes for a query

BLAST (public board)
  blast register / login / logout / who
  blast                     post last council synthesis to the public board

FAMILY & SEALED LETTERS -- private, PIN-protected
  write to <name>           compose a sealed letter (opens a dialog)
  letters                   list letters waiting for you / sent by you
  open letter <id>          read one sealed letter
  legacy                    open the family Legacy Vault (opens a dialog)
  legacy import <path>      import a .legacypack file into the vault

BOARD IDENTITY (Ed25519-signed public letters)
  postal setup <name>       create your signing identity
  postal my key             show your public key
  postal add user <n> <k>   add a contact's public key
  postal contacts           list known contacts
  postal rotate             rotate your signing key

STRAND ARCHIVE (persistent memory)
  anchor this               save last exchange as a Strand
  strands / strands <territory> / strands search <query>
  strand export / strand export <territory>
  strand import <file>      Guardian-verified import from a pack
  remember <query>          pure local memory search, zero cloud

FUNFORGE (bounded creative spike)
  funforge <topic> / spike <topic>
  forge extend               add 30 minutes
  forge done                 close and produce artifact

MODEL & TRUST
  grok / claude              re-run last message with that model
  overseer on / off          Claude reviews every Grok response
  tier 1 / tier 2 / tier 3    offline-only -> local-first -> full council
  offline on / off           block every connection off this computer (stays on after restart)
  websearch on / off         search the web automatically for current-sounding questions (off by default)
  autoupdate on / off        check GitHub for updates after login (off by default)

OTHER
  rate good / bad / <1-5>    rate the last response
  image <description>        generate an image (needs paid OpenAI key)
  queue list / queue add <task>   offline task queue
  obsidian on/off/path/export/status
  clear                      wipe this conversation's on-screen history
  help                       this list"""


def handle_command(raw: str, cfg: dict, history: list[dict]) -> Optional[TextResult | StreamResult]:
    """
    Returns None if `raw` isn't a recognized built-in command -- caller
    should fall through to a plain chat() call in that case.
    """
    text = raw.strip()
    if not text:
        return None
    cmd = text.lower()

    if cmd == "help":
        return TextResult(_HELP_TEXT)

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
            return TextResult(f"⬡ {msg}\n\n```json\n{json.dumps(entry, indent=2)}\n```")
        return TextResult(f"⬡ {msg}")

    # ── Simple state toggles ────────────────────────────────────────────
    if cmd == "status":
        lines = [
            f"xAI key:       {'set' if cfg.get('api_key') else 'not set'}",
            f"OpenAI key:    {'set' if cfg.get('openai_key') else 'not set'}",
            f"Anthropic key: {'set' if cfg.get('anthropic_key') else 'not set'}",
            f"File access:   {'ON' if cfg.get('file_access') else 'OFF'}",
            f"Trust tier:    {cfg.get('trust_tier', 3)}",
            f"Offline mode:  {'ON' if _gate().is_offline() else 'OFF'}",
            f"Web search:    {'automatic' if _gate().setting('web_search_auto') else 'only search:'}",
            f"Update check:  {'automatic' if _gate().setting('update_check_auto') else 'manual'}",
            f"Cursiv mode:   {cfg.get('cursiv_mode', 'personal')}",
            f"Overseer:      {'ON' if cfg.get('overseer_mode') else 'OFF'}",
            f"Workspace:     {cfg.get('workspace', '')}",
        ]
        return TextResult("\n".join(lines))

    if cmd in ("tier 1", "tier 2", "tier 3"):
        cfg["trust_tier"] = int(cmd[-1])
        labels = {1: "SOVEREIGN OFFLINE (Ollama only)", 2: "LOCAL + LIMITED", 3: "FULL COUNCIL"}
        return TextResult(f"Trust tier → {cfg['trust_tier']} — {labels[cfg['trust_tier']]}")

    if cmd in ("offline on", "offline off"):
        from cursiv_v215.core import netgate
        try:
            netgate.set_offline(cmd == "offline on")
        except Exception as exc:
            return TextResult(f"Couldn't save offline mode ({exc}). Nothing was changed.")
        cfg["offline_mode"] = netgate.is_offline()
        if cfg["offline_mode"]:
            cfg["trust_tier"] = 1
            return TextResult("Offline mode ON — Cursiv won't connect to anything outside this computer "
                              "(cloud AI, web search, update checks, model downloads). Your local model still works. "
                              "This stays on after a restart; type 'offline off' to undo.")
        cfg["trust_tier"] = 3
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

    if cmd in ("governor on", "governor off", "governor"):
        if cmd == "governor off":
            cfg["cursiv_mode"] = "personal"
            return TextResult("Governor mode OFF → Personal mode.")
        cfg["cursiv_mode"] = "governor"
        return TextResult(
            "GOVERNOR MODE ENGAGED — constitutional enforcement elevated. "
            "Responses will be formal and constitutionally grounded. "
            "Type 'governor off' to return to personal mode."
        )

    if cmd in ("files on", "files off"):
        cfg["file_access"] = cmd == "files on"
        return TextResult(f"File access → {'ON' if cfg['file_access'] else 'OFF'}")

    if cmd == "mode":
        cfg["confirm_mode"] = "confirm" if cfg.get("confirm_mode") == "auto" else "auto"
        return TextResult(f"Write mode → {cfg['confirm_mode'].upper()}")

    if cmd in ("overseer on", "overseer off"):
        if cmd == "overseer on":
            if not cfg.get("anthropic_key"):
                return TextResult("Overseer needs an Anthropic key for Claude. Type: anthropic sk-ant-xxxxx")
            if not (cfg.get("api_key") or cfg.get("openai_key")):
                return TextResult("Overseer needs a Grok/OpenAI key as the primary model. Type: key xai-xxxxx")
            cfg["overseer_mode"] = True
            return TextResult("Overseer mode → ON. Grok generates, Claude reviews every response.")
        cfg["overseer_mode"] = False
        return TextResult("Overseer mode → OFF. Normal routing restored.")

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
        return StreamResult(f"⬡ Forge — {_idea[:60]}", _forge.evolve(_idea, _gen), None)
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

            return StreamResult(f"⬡ Council deliberating — {question[:60]}", _run(), _finish)
        if not (cfg.get("api_key") or cfg.get("openai_key") or cfg.get("anthropic_key")):
            return TextResult("Council requires at least one API key.")
        def _finish2(full: str):
            cfg["_last_council_synthesis"] = full
            _session_append(question, full, "group_discovery")
        return StreamResult(
            f"⬡ Group discovery — {question[:60]}",
            _call_provider_council(question, cfg.get("api_key", ""), cfg.get("openai_key", ""), cfg.get("anthropic_key", "")),
            _finish2,
        )

    # ── Strand memory ────────────────────────────────────────────────────
    if cmd == "anchor this" or cmd.startswith("anchor this "):
        if not _STRAND_OK:
            return TextResult("Strand store unavailable.")
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
        return TextResult(f"⬡ Anchored → Strand {sid}" + (f"  [{territory}]" if territory != "general" else ""))

    if cmd == "strands" or cmd.startswith("strands "):
        if not _STRAND_OK:
            return TextResult("Strand store unavailable.")
        sub = text[8:].strip() if cmd.startswith("strands ") else ""
        if sub.startswith("search "):
            q = sub[7:].strip()
            if not q:
                return TextResult("Usage: strands search <query>")
            return TextResult(f"⬡ Strand search — {q}\n\n" + (_strand_fmt(_strand_search(q)) or "No matches."))
        if sub and sub in _strand_territories():
            results = _strand_list(territory=sub, limit=20)
            return TextResult(f"⬡ Strands [{sub}] ({len(results)} found)\n\n" + (_strand_fmt(results) or "None yet."))
        total = _strand_count()
        counts = _strand_terr_counts()
        recent = _strand_list(limit=8)
        counts_line = "  ".join(f"{t}:{n}" for t, n in counts.items()) if counts else "none yet"
        out = f"⬡ Strand Archive — {total} total\n{counts_line}"
        if recent:
            out += "\n\n" + _strand_fmt(recent)
        return TextResult(out)

    if cmd.startswith("strand export") or cmd == "strand export":
        if not (_STRAND_OK and _SFED_OK):
            return TextResult("Strand federation unavailable.")
        parts = cmd.split()
        territory = parts[2] if len(parts) >= 3 else None
        all_s = _strand_list(territory=territory, limit=5000)
        if not all_s:
            t_label = f" in '{territory}'" if territory else ""
            return TextResult(f"No strands{t_label} to export.")
        terr_defs = _strand_territories()
        label = f"cursiv-{territory or 'all'}"
        pack_text = _sfed_export(all_s, terr_defs, label=label)
        out_path = _CHAT_ROOT / f"{label}-{int(datetime.now().timestamp())}{_PACK_EXT}"
        try:
            out_path.write_text(pack_text, encoding="utf-8")
        except Exception as e:
            return TextResult(f"Export failed: {e}")
        t_label = territory or "all territories"
        return TextResult(
            f"⬡ Strand Pack Exported\nFile    :  {out_path.name}\n"
            f"Strands :  {len(all_s)}\nScope   :  {t_label}\n\n"
            f"Transfer via USB / LAN. Import with:  strand import {out_path.name}"
        )

    if cmd.startswith("strand import "):
        if not (_STRAND_OK and _SFED_OK):
            return TextResult("Strand federation unavailable.")
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
        return TextResult(f"⬡ Strand Pack Import\n{_sfed_summary(in_strands, meta)}\n\nImported {imported}/{len(in_strands)} strands.{note}")

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
            return TextResult("Strand store unavailable.")
        q = text[9:].strip()
        if not q:
            return TextResult("Usage: remember <query>")
        results = _strand_search(q, top_k=5, min_score=0.08)
        if not results:
            return TextResult("No matching strands found. Anchor exchanges with: anchor this")
        return TextResult(f"⬡ Local memory — {q}\n\n" + _strand_fmt(results))

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

    # ── Grow (self-referential code evolution) ─────────────────────────
    if cmd == "grow" or cmd.startswith("grow "):
        sub = text[5:].strip()
        if not sub:
            return TextResult("Usage: grow <filepath>  ·  grow system")
        if sub.lower() == "system":
            gen, label = _cascade_gen(cfg, [
                {"role": "system", "content": (
                    "You are a systems architect reviewing the Cursiv AI OS. "
                    "Identify the single most valuable capability that is clearly "
                    "missing or half-built and write a Python module stub for it "
                    "(filename, docstring, key functions with signatures). No filler."
                )},
                {"role": "user", "content": "Suggest the next capability for this system."},
            ], max_tokens=1200)
            def _finish(full):
                if _STRAND_OK and full:
                    _strand_save("grow system", full, tags=["grow", "system"], score=0.80,
                                 territory_tag="architecture", source="grow", model=label)
            return StreamResult(f"⬡ Grow — system level", gen, _finish)
        gpath = Path(sub)
        if not gpath.is_absolute():
            gpath = Path(cfg.get("workspace", str(_CHAT_ROOT))) / sub
        if not gpath.exists():
            return TextResult(f"File not found: {sub}")
        try:
            code = gpath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return TextResult(f"Read error: {e}")
        gen, label = _cascade_gen(cfg, [
            {"role": "system", "content": (
                "You are a code evolution engine. Study this file's style and "
                "patterns, then write the next logical addition -- same voice, "
                "same conventions. Output only the new code, no explanation."
            )},
            {"role": "user", "content": code},
        ], max_tokens=1200)
        return StreamResult(f"⬡ Grow — {sub}", gen)

    # ── Babel translation ────────────────────────────────────────────────
    if _BABEL_OK and (cmd == "babel" or (cmd.startswith("babel") and len(cmd) > 5 and cmd[5] in (" ", ":"))):
        raw_input = _babel_input(text)
        if not raw_input:
            return TextResult("Usage: babel <text in any language>  ·  babel <text> into <language(s)>")
        into_match = re.search(r"\s+into\s+(.+)$", raw_input, re.IGNORECASE)
        if into_match and not re.match(r"^i\s+am\b", raw_input, re.IGNORECASE):
            src = _babel_source(raw_input[:into_match.start()])
            targets = _babel_targets(into_match.group(1))
            if src and targets:
                gen, label = _cascade_gen(cfg, [
                    {"role": "system", "content": (
                        "You are a precise translation engine. Translate the user's text "
                        "into each requested language. For each, output a header line "
                        "exactly like:\n  ── [Language Name] ──\nfollowed by the translation. "
                        "Return translations only, no explanations."
                    )},
                    {"role": "user", "content": f"Text to translate:\n{src}\n\nTranslate into: {', '.join(targets)}"},
                ], max_tokens=800)
                return StreamResult(f"⬡ Babel — English → {', '.join(targets)}", gen)
        gen, label = _cascade_gen(cfg, [
            {"role": "system", "content": "Translate the following text to English. Return only the translation, nothing else."},
            {"role": "user", "content": raw_input},
        ], max_tokens=1500)
        return StreamResult(f"⬡ Babel → English", gen)

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
        return StreamResult(f"⬡ Page pull — {url[:70]}", gen, _finish)

    # ── FunForge ─────────────────────────────────────────────────────────
    if cmd in ("forge done", "forge close"):
        ff = cfg.get("funforge_session")
        if not ff:
            return TextResult("No active FunForge session.")
        gen = _chat(
            "Let's close this creative spike. Synthesize what we made into a final artifact.",
            history, cfg.get("api_key", ""), None, False, cfg.get("workspace", str(_CHAT_ROOT)),
            cfg.get("openai_key", ""), False, cfg.get("anthropic_key", ""),
        )
        cfg["funforge_session"] = None
        return StreamResult("⬡ FunForge closing — producing artifact", gen)

    if cmd.startswith("funforge") or cmd.startswith("spike "):
        topic = text[len("funforge"):].strip() if cmd.startswith("funforge") else text[6:].strip()
        topic = topic or "open-ended creative spike"
        cfg["funforge_session"] = {"topic": topic, "started": datetime.now()}
        gen = _chat(
            f"[FUNFORGE] Playful 45-minute creative spike. Topic: {topic}. "
            "Respond playfully and start the creative spike.",
            history, cfg.get("api_key", ""), None, False, cfg.get("workspace", str(_CHAT_ROOT)),
            cfg.get("openai_key", ""), False, cfg.get("anthropic_key", ""),
        )
        return StreamResult(f"⬡ FunForge active — {topic}  (type 'forge done' when finished)", gen)

    # ── Blast (public board) ────────────────────────────────────────────
    if cmd == "blast" or cmd.startswith("blast "):
        if not _BOARD_OK:
            return TextResult("Board client unavailable.")
        sub = text[6:].strip() if cmd.startswith("blast ") else ""
        if sub == "who":
            who = _board_whoami()
            return TextResult(f"Board: logged in as {who}" if who else "Not logged in. Use: blast login <username>")
        if sub == "logout":
            _board_logout()
            return TextResult("Board session cleared.")
        if sub.startswith(("login ", "register ")):
            return TextResult(
                "Signing in to the public board isn't available in the desktop "
                "app yet — it needs a password window that hasn't been built."
            )
        synth = cfg.get("_last_council_synthesis", "")
        if not synth:
            return TextResult("No council synthesis yet — run a council deliberation first, then blast.")
        who = _board_whoami()
        if not who:
            return TextResult("Not logged in to the board. Use the terminal to log in first.")
        ok, msg = _board_blast(synth, source="council")
        return TextResult(f"✓ Blasted. Post ID: {msg}" if ok else f"✗ {msg}")

    # ── Substrate ────────────────────────────────────────────────────────
    if cmd == "substrate" or cmd.startswith("substrate "):
        if not _SUBSTRATE_OK:
            return TextResult("Substrate module unavailable.")
        act = _get_activator()
        sub = text[10:].strip() if cmd.startswith("substrate ") else ""
        if sub == "status":
            st = act.status()
            ly = st["layer"]
            return TextResult(
                f"⬡ Substrate — RUW layer\nNodes: {ly['nodes']}  Edges: {ly['edges']}  "
                f"Activations: {st['activations']}\nAddress: {ly['address']}"
            )
        if sub.startswith("weave "):
            q = sub[6:].strip()
            hits = act.weave(q, top_k=5) if q else []
            if not hits:
                return TextResult("No nodes in layer yet. Run a council deliberation first.")
            return TextResult("⬡ Substrate weave — resonant nodes\n" + "\n".join(f"{score:.3f}  {nid}" for nid, score in hits))
        synth = cfg.get("_last_council_synthesis", "")
        query = cfg.get("_last_council_query", "")
        if not synth:
            return TextResult("No council synthesis yet. Run a council deliberation first.")
        result = act.activate(synth, query=query, session_id="gui")
        return TextResult(
            f"⬡ Substrate activated\nRUW address: {result['ruw_address']}\n"
            f"Resonance: {result['resonance']:.4f}  Nodes: {result['layer_state']['nodes']}"
        )

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
            return TextResult(f"⬡ {heading}\n\nNo sealed letters found.")
        lines = [f"⬡ {heading}"]
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
            f"⬡ Sealpack exported\nfile: {pack_path}\npassphrase: {passphrase}\n\n"
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
        return TextResult(f"⬡ Sealed locally as: {new_id}")

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
            f"⬡ Identity created\nName: {meta.get('name', name)}\nKey ID: {meta.get('key_id', '?')[:8]}\n"
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
            f"⬡ Your Cursiv identity\nName: {my_id.get('name', '?')}\n"
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
        return TextResult(f"⬡ Contact added: {parts[0]}  (key-id: {entry.get('key_id', '?')[:8]})")

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
            f"⬡ Key rotation\nOld key ID: {rot.get('old_key_id', '?')[:8]} (archived locally)\n"
            f"New key ID: {rot.get('new_key_id', '?')[:8]}\nNew public: {rot.get('new_pubkey', '?')}\n\n"
            f"Update your contacts: postal add user <your name> <new key>{note}"
        )

    if cmd == "postal key history":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        hist = _postal_key_history()
        if not hist:
            return TextResult("⬡ Key history\n\nNo retired keys.")
        lines = ["⬡ Key history"]
        for hk in hist:
            flag = "  COMPROMISED — coherence degradation active" if hk.get("compromised") else ""
            lines.append(f"{hk.get('key_id', '?')[:8]}  retired:{hk.get('retired_at', '?')[:10]}  {hk.get('reason', '?')[:40]}{flag}")
        return TextResult("\n".join(lines))

    if cmd == "postal contacts":
        if not _POSTAL_OK:
            return TextResult("Postal module unavailable.")
        clist = _postal_contacts()
        if not clist:
            return TextResult("⬡ Contacts\n\nNo contacts yet. Use: postal add user <name> <pubkey>")
        lines = [f"⬡ Contacts ({len(clist)})"]
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
        return TextResult(f"⬡ Image generated with {used_model}  ({img_path.name}){note}", image_path=str(img_path))

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


# ── Blast (board) login/register — password collected by the caller via a
# Qt dialog, since this module stays UI-agnostic; the actual HTTP call
# lives here so it's identical to what the terminal CLI does. ─────────────

def blast_login(username: str, password: str) -> TextResult:
    if not _BOARD_OK:
        return TextResult("Board client unavailable.")
    ok, msg = _board_login(username, password)
    return TextResult(f"✓ Logged in as {msg}" if ok else f"✗ {msg}")


def blast_register(username: str, password: str) -> TextResult:
    if not _BOARD_OK:
        return TextResult("Board client unavailable.")
    ok, msg = _board_register(username, password)
    return TextResult(f"✓ Account created. Logged in as {msg}" if ok else f"✗ {msg}")


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

    header = f"⬡ Image pasted — {width}×{height}px\n\n"
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
        f"⬡ Sealed\nid: {lid}\nfor: {recipient_disp}\n"
        f"signed: {'yes — Ed25519' if my_id else 'no — run postal setup first'}\n"
        f"readable: on this machine only"
    )


# ── Pending file write -- caller (chat_panel.py) shows the confirmation
# dialog (needs Qt, on the main thread); the actual write happens here via
# the same execute_tool() the terminal CLI's approval flow calls. ─────────

def approve_write(path: str, content: str, workspace: str) -> TextResult:
    result = _execute_tool("write_file", {"path": path, "content": content}, Path(workspace))
    return TextResult(f"✓ {result}")

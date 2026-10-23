"""
Text commands for the chat window ("help", "offline on", "remember ...").

handle_command() returns a TextResult or StreamResult for a built-in command,
or None for normal chat. It calls the same functions the terminal CLI
(cursiv_engine/chat) uses.

Handled in chat_panel.py instead, because they need a window or widget:
voice / listen / paste, write to / legacy (compose and PIN dialogs), and
clear (the transcript widget).
"""
from __future__ import annotations
from cursiv_engine.core.command_api import (
    TextResult, NotebookResult, FileActionResult, MemoryResult, NotesResult, StreamResult,
)

import sys as _sys
from typing import cast as _cast
from cursiv_engine.core.command_api import CommandRuntime
import command_agents as _agents
import command_dispatch as _dispatch
import command_media as _media
import command_support as _support


def _runtime() -> CommandRuntime:
    """Explicit compatibility services: callables and per-turn records live here."""
    return _cast(CommandRuntime, _sys.modules[__name__])

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

from cursiv_engine.ui.chat_app import (
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

from cursiv_engine.chat.keys import (
    store_key as _save_key, probe_xai as _probe_xai, probe_openai as _probe_openai, probe_claude as _probe_claude,
)

try:
    from cursiv_engine.agents.babel_agent import is_babel_command as _babel_detect, extract_babel_input as _babel_input
    _BABEL_OK = True
except Exception:
    _BABEL_OK = False
    def _babel_detect(t): return False
    def _babel_input(t): return ""

try:
    from cursiv_engine.agents.codex_agent import generate as _codex_gen, is_available as _codex_avail
    _CODEX_OK = True
except Exception:
    _CODEX_OK = False
    def _codex_gen(p): return ""
    def _codex_avail(): return False

try:
    from cursiv_engine.agents.hermes_agent import run as _hermes_run, is_available as _hermes_avail
    _HERMES_OK = True
except Exception:
    _HERMES_OK = False
    def _hermes_run(p): return ""
    def _hermes_avail(): return False

try:
    from cursiv_engine.agents.reference_brain import answer as _ref_answer, is_available as _ref_avail
    _REF_OK = True
except Exception:
    _REF_OK = False
    def _ref_answer(q): return ""
    def _ref_avail(): return False

try:
    from cursiv_engine.council.async_council import run_council as _async_council_run, council_available as _async_council_ok
    _ASYNC_COUNCIL_OK = True
except Exception:
    _ASYNC_COUNCIL_OK = False
    def _async_council_run(q, cfg, **kw): return None
    def _async_council_ok(cfg): return False

try:
    from cursiv_engine.core.strand_store import (
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
    from cursiv_engine.obsidian.exporter import (
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
    from cursiv_engine.memory.session_log import append_exchange as _session_append
except Exception:
    def _session_append(u, a, m="unknown"): pass

try:
    from cursiv_engine.postal.sealed_store import (
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
    from cursiv_engine.postal.council_reader import council_walkthrough as _postal_council
    from cursiv_engine.postal.user_registry import (
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
    from cursiv_engine.family.family_profiles import detect_family_member as _fam_detect
    from cursiv_engine.family.legacy_store import (
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
    from cursiv_engine.family.family_profiles import (
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
    from cursiv_engine.agents.voice_agent import (
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
    from cursiv_engine.agents.babel_agent import (
        encode_to_binary as _babel_encode,
        decode_from_binary as _babel_decode,
    )
except Exception:
    def _babel_encode(t): return b""
    def _babel_decode(b): return ""

try:
    from cursiv_engine.agents.offline_queue import (
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
    from cursiv_engine.core.strand_federation import (
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







def _image_folder(cfg: dict) -> Path:
    """Compatibility entry point; implementation in command_support."""
    return _support._image_folder(_runtime(), cfg)





def memory_command(text: str, history: list[dict], *, scope: str='') -> MemoryResult | None:
    """Compatibility entry point; implementation in command_support."""
    return _support.memory_command(_runtime(), text, history, scope=scope)



def notebook_command(text: str, history: list[dict], *, scope: str='', cfg: dict | None=None) -> NotebookResult | None:
    """Compatibility entry point; implementation in command_support."""
    return _support.notebook_command(_runtime(), text, history, scope=scope, cfg=cfg)





def _notes_view_request(text: str) -> NotesResult | None:
    """Compatibility entry point; implementation in command_support."""
    return _support._notes_view_request(_runtime(), text)





# Commands removed in the plain-language cleanup (2026-10-17). Only their exact
# old forms get a note; anything longer ("grow tomatoes") is normal chat.
_RETIRED = {
    "tier 2", "tier 3", "governor", "governor on", "governor off", "overseer on", "overseer off",
    "funforge", "forge done", "forge close", "forge extend", "substrate", "substrate status",
    "blast", "blast login", "blast register", "blast logout", "blast who", "grow system",
}


def _gate():
    """Compatibility entry point; implementation in command_support."""
    return _support._gate(_runtime())



def _default_cfg() -> dict:
    """Compatibility entry point; implementation in command_support."""
    return _support._default_cfg(_runtime())



def _auto_territory(q: str) -> str:
    """Compatibility entry point; implementation in command_support."""
    return _support._auto_territory(_runtime(), q)



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
    """Compatibility entry point; implementation in command_agents."""
    return _agents._babel_source(_runtime(), text)



def _babel_targets(phrase: str) -> list[str]:
    """Compatibility entry point; implementation in command_agents."""
    return _agents._babel_targets(_runtime(), phrase)



def _cascade_gen(cfg: dict, messages: list[dict], max_tokens: int=900):
    """Compatibility entry point; implementation in command_agents."""
    return _agents._cascade_gen(_runtime(), cfg, messages, max_tokens)




# ── Codex: Cursiv's coding brain (cursiv_engine/coding) ──────────────────────
_LAST_CODEX: dict = {}     # question/answer of the last codex reply, for `codex keep` / `codex run`


def _codex_command(prompt: str, cfg: dict, history: list[dict]):
    """Compatibility entry point; implementation in command_agents."""
    return _agents._codex_command(_runtime(), prompt, cfg, history)



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


# ── Custom agents (cursiv_engine/agents/custom.py) ───────────────────────────
def _agent_command(text: str, cfg: dict, history: list[dict]):
    """Compatibility entry point; implementation in command_agents."""
    return _agents._agent_command(_runtime(), text, cfg, history)


# The research profile (core/profile.py, the default): field work first.
from phone_help import PHONE_CAPTURE, PHONE_LINKS

_FIELD_HELP_TEXT = """\
  check off / fast / full                model review mode; code checks stay on
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

help more                                everything else""" + '\n' + PHONE_LINKS

_HELP_TEXT = """\
  check off / fast / full   answer review mode; deterministic checks stay on
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

help more                     everything else""" + '\n' + PHONE_LINKS

# help <topic>. Topics in _BUILDER_TOPICS are listed only for the owner
# (they still open for anyone who types them).
_HELP_TOPICS = {
    "field": ("Field notebook", f"""\
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
  {PHONE_CAPTURE}
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
  file help                   authorized local text files and permanent file notes
  file remember <path> :: <text>   save a file and conversational memory separately
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
  Create notes.txt with the text: Site A, 14.2 C
  Add ‘Site B, 13.8 C’ to the notes file; Open the notes file
  Search my workspace for temperature or sample
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
    """Compatibility entry point; implementation in command_support."""
    return _support._personal(_runtime())



def _is_builder() -> bool:
    """Compatibility entry point; implementation in command_support."""
    return _support._is_builder(_runtime())



def help_text(topic: str='') -> str:
    """Compatibility entry point; implementation in command_support."""
    return _support.help_text(_runtime(), topic)



def handle_command(raw: str, cfg: dict, history: list[dict]) -> Optional[TextResult | StreamResult]:
    """Compatibility entry point; implementation in command_dispatch."""
    return _dispatch.handle_command(_runtime(), raw, cfg, history)



def hey_prefix(raw: str) -> tuple[str, str]:
    """Compatibility entry point; implementation in command_support."""
    return _support.hey_prefix(_runtime(), raw)



# ── Voice — caller (chat_panel.py) owns the mic-record UI affordance
# (start/stop button); this function does the actual capture, STT, and
# Babel-clean pass, identical to the terminal CLI's "voice"/"listen". ─────

def voice_turn(cfg: dict, duration_s: float=5.0, raw_mode: bool=False, status_cb: Optional[Callable[[str], None]]=None) -> TextResult:
    """Compatibility entry point; implementation in command_support."""
    return _support.voice_turn(_runtime(), cfg, duration_s, raw_mode, status_cb)



# ── Training data manager ────────────────────────────────────────────────
# Images, free-form notes and pasted JSON all feed one file
# (cursiv_engine/training/paths.py's TRAINING_JSONL, read by LoRA training) --
# one store, one schema ({"prompt", "response", "quality", "agent_id",
# "timestamp", "source"}).
try:
    from cursiv_engine.training.paths import TRAINING_JSONL as _TRAINING_JSONL
except Exception:
    _TRAINING_JSONL = Path.home() / ".cursiv" / "training_data.jsonl"

_TEXT2JSON_VERBS = ("translate", "convert", "turn", "format")


def _looks_like_text_to_json_request(text: str) -> bool:
    """Compatibility entry point; implementation in command_media."""
    return _media._looks_like_text_to_json_request(_runtime(), text)



def list_training_entries() -> list[dict]:
    """Compatibility entry point; implementation in command_media."""
    return _media.list_training_entries(_runtime())



def add_training_entry_json(raw_json: str) -> tuple[bool, str]:
    """Compatibility entry point; implementation in command_media."""
    return _media.add_training_entry_json(_runtime(), raw_json)



def delete_training_entry(line_index: int) -> tuple[bool, str]:
    """Compatibility entry point; implementation in command_media."""
    return _media.delete_training_entry(_runtime(), line_index)



def _run_llm_once(messages: list[dict], cfg: dict) -> str:
    """Compatibility entry point; implementation in command_media."""
    return _media._run_llm_once(_runtime(), messages, cfg)



def text_to_training_entry(notes: str, cfg: dict) -> tuple[bool, str, Optional[dict]]:
    """Compatibility entry point; implementation in command_media."""
    return _media.text_to_training_entry(_runtime(), notes, cfg)



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
    """Compatibility entry point; implementation in command_media."""
    return _media._cloudflare_image(_runtime(), prompt, account_id, token)


_IMAGE_ASK_RE = re.compile(
    r"^(?:please\s+|can you\s+|could you\s+)?"
    r"(?:generate|create|make|draw|paint|render|design)\s+(?:me\s+)?(?:an?\s+)?"
    r"(?:image|picture|pic|photo|drawing|painting|illustration|logo)\s+(?:of|showing|with|for)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def _image_request_prompt(text: str) -> Optional[str]:
    """Compatibility entry point; implementation in command_media."""
    return _media._image_request_prompt(_runtime(), text)



# ── Vision: one shared "describe this image" chain ───────────────────────
# Paid keys first when the user set them (an opt-in upgrade), then the
# free Gemini key, then a local Ollama vision model -- the floor that works
# with no key and no internet, per the Ollama-first rule.

OLLAMA_VISION_MODELS = ("gemma3", "qwen2.5vl", "llama3.2-vision", "minicpm-v", "llava", "moondream")
OLLAMA_VISION_DEFAULT = "gemma3:4b"


def _ollama_vision_model() -> str:
    """Compatibility entry point; implementation in command_media."""
    return _media._ollama_vision_model(_runtime())



def _vision_describe(img_b64: str, mime: str, prompt_text: str, cfg: dict) -> tuple[str, str]:
    """Compatibility entry point; implementation in command_media."""
    return _media._vision_describe(_runtime(), img_b64, mime, prompt_text, cfg)



_NO_VISION_HELP = (
    "No vision model available. Free options: install a local one with "
    f"'ollama pull {OLLAMA_VISION_DEFAULT}' (works offline), or add a free Gemini "
    "key (type 'gemini AIza...'). Anthropic/OpenAI keys also work."
)


def image_to_training_entry(image_bytes: bytes, cfg: dict, ext: str='png') -> tuple[bool, str, Optional[dict]]:
    """Compatibility entry point; implementation in command_media."""
    return _media.image_to_training_entry(_runtime(), image_bytes, cfg, ext)



# ── "photo <path> <question>": the chat's paperclip ─────────────────────────
_PHOTO_CMD = re.compile(r'(?is)^photo\s+(?:"([^"]+)"|(\S+))\s*(.*)$')
_NO_LOCAL_VISION = (
    "Reading photos offline needs Cursiv's image model on this computer, and none is installed. "
    "Install it in Setup (step 5: gemma3 4B, 3.3 GB; needs the internet once). "
    "With the internet blocked, Cursiv won't send the photo anywhere.")


def describe_photo(path: str, question: str, cfg: dict) -> TextResult:
    """Compatibility entry point; implementation in command_media."""
    return _media.describe_photo(_runtime(), path, question, cfg)



# ── Paste image from clipboard → vision analysis → strand. Caller passes
# already-extracted PNG bytes (from Qt's clipboard); the vision-API calls
# and strand save live here so they match the terminal CLI's "paste". ────

def analyze_pasted_image(png_bytes: bytes, cfg: dict, width: int, height: int) -> TextResult:
    """Compatibility entry point; implementation in command_media."""
    return _media.analyze_pasted_image(_runtime(), png_bytes, cfg, width, height)



# ── Postal compose — caller (chat_panel.py) collects recipient/hint/body
# via a dialog; the actual sealing call is identical to the terminal CLI's
# "write to" flow. ──────────────────────────────────────────────────────

def postal_compose(sender_user: str, recipient_raw: str, hint: str, content: str) -> TextResult:
    """Compatibility entry point; implementation in command_media."""
    return _media.postal_compose(_runtime(), sender_user, recipient_raw, hint, content)



# ── Pending file write -- caller (chat_panel.py) shows the confirmation
# dialog (needs Qt, on the main thread); the actual write happens here via
# the same execute_tool() the terminal CLI's approval flow calls. ─────────

def approve_write(path: str, content: str, workspace: str, *, operation: str='write_file', expected_sha256: str | None=None, remember: bool=False) -> TextResult:
    """Compatibility entry point; implementation in command_media."""
    return _media.approve_write(_runtime(), path, content, workspace, operation=operation, expected_sha256=expected_sha256, remember=remember)

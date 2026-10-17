"""
Cursiv — Terminal Chat (developer use; not part of the desktop app).
The desktop chat reuses its key helpers (_save_key, _probe_*).

Run from a source checkout:  python -m cursiv_v215.ui.chat_cli

Messages stack naturally and scroll upward — use the mouse wheel or terminal
scroll-bar to read history.  The input box stays at the current bottom.

Commands:
  key  <xai-key>       set xAI Grok API key   (starts with xai-)
  openai <key>         set OpenAI API key      (starts with sk-)
  anthropic <key>      set Anthropic API key   (starts with sk-ant-)
  files on / off       enable / disable file-system access
  workspace <path>     sandbox root for file tools
  mode                 toggle write mode  (auto ↔ confirm)
  clear                wipe conversation history shown in box
  status               show current config
  help                 this list
  exit / Ctrl+C        quit
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import textwrap
import urllib.request
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout — prevents surrogate/emoji crashes on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent.parent))

from cursiv_v215.core import netgate as _netgate
from cursiv_v215.ui.chat_app import (
    WRITE_SENTINEL,
    RATE_SENTINEL,
    ROOT,
    chat,
    execute_tool,
    _call_provider_council,
    _cursiv_encode,
    _web_search,
    _needs_search,
    _call_ollama,
    _call_xai_stream,
    _call_claude_direct,
    _call_openai_direct,
    cascade_stream,
    free_key_command,
)


def _cascade_label(cfg: dict) -> str:
    """Provider order cascade_stream will try, for the 'via ...' line."""
    order = [name for name, field in (("Claude", "anthropic_key"), ("xAI", "api_key"), ("OpenAI", "openai_key"))
             if cfg.get(field)]
    return " → ".join(order + ["Ollama"])

try:
    from cursiv_v215.agents.babel_agent import (
        encode_to_binary        as _babel_encode,
        decode_from_binary      as _babel_decode,
        format_binary_block     as _babel_fmt,
        BABEL_SYSTEM            as _BABEL_SYSTEM,
        is_babel_command        as _babel_detect,
        extract_babel_input     as _babel_input,
        is_rtl_script           as _babel_is_rtl,
        detect_script           as _babel_detect_script,
        reorder_rtl_for_display as _babel_rtl_reorder,
    )
    _BABEL_OK = True
except Exception:
    _BABEL_OK = False

try:
    from cursiv_v215.forge.funforge_meta import (
        FunForgeSession,
        FUNFORGE_CLOSE_PROMPT,
        detect_trigger  as _ff_detect,
        extract_topic   as _ff_topic,
    )
    _FF_OK = True
except Exception:
    _FF_OK = False

# ── Sovereign verification (locally-stored owner code — never committed) ──
# See cursiv_v215/ui/chat_app.py for why this replaced the old 3-module
# passphrase constants: this repo is public, so a "hidden" phrase hardcoded
# in committed source was never actually secret.
try:
    from cursiv_v215.guardian.temple_guardian import unlock_owner_session as _unlock_cli
    from cursiv_v215.guardian.temple_guardian import verify_owner_code    as _verify_sovereign_cli
    from cursiv_v215.guardian.temple_guardian import set_owner_code       as _set_owner_code_cli
except Exception:
    def _verify_sovereign_cli(text: str) -> bool:
        return False
    def _unlock_cli(sid: str):
        pass
    def _set_owner_code_cli(code: str) -> None:
        raise RuntimeError("Owner code storage unavailable.")

# ── Obsidian Vault Sync ────────────────────────────────────────────────────
try:
    from cursiv_v215.obsidian.exporter import (
        load_config        as _obs_load_config,
        save_config        as _obs_save_config,
        export_today       as _obs_export,
        auto_detect_vault  as _obs_detect_vault,
        livestream_exchange as _obs_livestream_cli,
    )
    _OBS_CLI_OK = True
except Exception:
    _OBS_CLI_OK = False
    def _obs_load_config():            return {"enabled": False, "vault_path": ""}
    def _obs_save_config(e, p):        pass
    def _obs_export(vp, d=None):       return (False, "Obsidian module unavailable.")
    def _obs_detect_vault():           return ""
    def _obs_livestream_cli(u, a, m):  pass

# ── Session Memory ─────────────────────────────────────────────────────────
try:
    from cursiv_v215.memory.session_log import (
        append_exchange   as _session_append_cli,
        get_boot_summary  as _session_boot_summary,
        get_last_exchange as _session_get_last,
        RATED_JSONL       as _RATED_JSONL,
    )
    _SESSION_CLI_OK = True
except Exception:
    _SESSION_CLI_OK = False
    def _session_append_cli(u, a, m="unknown"): pass
    def _session_boot_summary():                return {}
    def _session_get_last():                    return None
    _RATED_JSONL = Path(ROOT) / ".cursiv" / "rated_exchanges.jsonl"

# ── Voice Agent — two-stage local pipeline (STT → Babel clean) ────────────
try:
    from cursiv_v215.agents.voice_agent import (
        record           as _voice_record,
        transcribe_raw   as _voice_transcribe,
        is_available     as _voice_avail,
        stt_backend      as _voice_stt_backend,
        capture_backend  as _voice_cap_backend,
        VOICE_CLEAN_SYSTEM as _VOICE_CLEAN_SYS,
    )
    _VOICE_OK = True
except Exception:
    _VOICE_OK = False
    def _voice_record(duration_s=5.0, status_cb=None): return b"", None
    def _voice_transcribe(pcm, arr=None, model_size="small", status_cb=None) -> str: return ""
    def _voice_avail() -> bool:       return False
    def _voice_stt_backend() -> str:  return "none"
    def _voice_cap_backend() -> str:  return "none"
    _VOICE_CLEAN_SYS = ""

# ── Family Profiles — personal activation system ──────────────────────────
try:
    from cursiv_v215.family.family_profiles import (
        detect_family_member as _fam_detect,
        build_system_prompt  as _fam_build_prompt,
        parse_iam_command    as _fam_parse_iam,
        get_jw_header        as _fam_header,
        get_letter           as _fam_get_letter,
        pin_is_set           as _fam_pin_is_set,
        set_pin              as _fam_set_pin,
        verify_pin           as _fam_verify_pin,
        is_valid_pin         as _fam_pin_valid,
        PIN_CHARS            as _FAM_PIN_CHARS,
    )
    _FAM_OK = True
except Exception:
    _FAM_OK = False
    def _fam_detect(n, d):        return None
    def _fam_build_prompt(p):     return ""
    def _fam_parse_iam(t):        return None
    def _fam_header():            return ""
    def _fam_get_letter(k):       return ""
    def _fam_pin_is_set(k):       return False
    def _fam_set_pin(k, p):       pass
    def _fam_verify_pin(k, p):    return False
    def _fam_pin_valid(p):        return False
    _FAM_PIN_CHARS = "! @ # $ % ^ & * ~ - + = ? /"

# ── Legacy Store — family letter vault ───────────────────────────────────
try:
    from cursiv_v215.family.legacy_store import (
        letters_waiting_for  as _legacy_letters_for,
        letters_written_by   as _legacy_letters_by,
        get_letter_content   as _legacy_get_content,
        get_letter_entry     as _legacy_get_entry,
        save_letter          as _legacy_save,
        rewrite_letter       as _legacy_rewrite,
        delete_letter        as _legacy_delete,
        make_letter_pin_hash as _legacy_make_pin_hash,
        verify_letter_pin    as _legacy_verify_letter_pin,
        name_to_key          as _legacy_name_to_key,
        export_pack          as _legacy_export_pack,
        import_pack          as _legacy_import_pack,
        open_folder          as _legacy_open_folder,
    )
    _LEGACY_OK = True
except Exception:
    _LEGACY_OK = False
    def _legacy_letters_for(k):                return []
    def _legacy_letters_by(k):                 return []
    def _legacy_get_content(i):                return None
    def _legacy_get_entry(i):                  return None
    def _legacy_save(**kw):                    return ""
    def _legacy_rewrite(i, c):                 return False
    def _legacy_delete(i):                     return False
    def _legacy_make_pin_hash(p):              return ""
    def _legacy_verify_letter_pin(i, p):       return False
    def _legacy_name_to_key(n):                return n.lower().split()[0]
    def _legacy_export_pack(k, d):             return (Path("."), 0)
    def _legacy_import_pack(f):                return (0, [])
    def _legacy_open_folder(p):               pass

# ── Code Sentinel — prompt injection + dangerous pattern guard ────────────
try:
    from cursiv_v215.guardian.code_sentinel import (
        scan_content   as _sentinel_scan,
        scan_file      as _sentinel_scan_file,
        format_warning as _sentinel_warn,
        BLOCK          as _SENTINEL_BLOCK,
        WARN           as _SENTINEL_WARN,
    )
    _SENTINEL_OK = True
except Exception:
    _SENTINEL_OK = False
    def _sentinel_scan(t, label=""):      return type("R", (), {"clean": True, "blocked": False, "level": 0})()
    def _sentinel_scan_file(p):          return type("R", (), {"clean": True, "blocked": False, "level": 0})()
    def _sentinel_warn(r, fn=""):        return ""
    _SENTINEL_BLOCK = 2
    _SENTINEL_WARN  = 1

# ── Codex Agent — offline-capable coding specialist ──────────────────────
try:
    from cursiv_v215.agents.codex_agent import (
        generate     as _codex_gen_cli,
        is_available as _codex_avail_cli,
    )
    _CODEX_CLI_OK = True
except Exception:
    _CODEX_CLI_OK = False
    def _codex_gen_cli(p: str) -> str: return ""
    def _codex_avail_cli() -> bool:    return False

# ── Hermes Agent — offline multi-step tool executor ───────────────────────
try:
    from cursiv_v215.agents.hermes_agent import (
        run          as _hermes_run_cli,
        is_available as _hermes_avail_cli,
    )
    _HERMES_CLI_OK = True
except Exception:
    _HERMES_CLI_OK = False
    def _hermes_run_cli(p: str) -> str: return ""
    def _hermes_avail_cli() -> bool:    return False

# ── Reference Brain — offline SQLite knowledge ────────────────────────────
try:
    from cursiv_v215.agents.reference_brain import (
        answer       as _ref_answer_cli,
        is_available as _ref_avail_cli,
    )
    _REF_CLI_OK = True
except Exception:
    _REF_CLI_OK = False
    def _ref_answer_cli(q: str) -> str: return ""
    def _ref_avail_cli() -> bool:       return False

# ── Offline Queue ──────────────────────────────────────────────────────────
try:
    from cursiv_v215.agents.offline_queue import (
        enqueue      as _queue_enqueue_cli,
        format_queue as _queue_format_cli,
        count        as _queue_count_cli,
    )
    _QUEUE_CLI_OK = True
except Exception:
    _QUEUE_CLI_OK = False
    def _queue_enqueue_cli(p: str, **kw) -> dict: return {}
    def _queue_format_cli() -> str:               return ""
    def _queue_count_cli() -> int:                return 0

# ── Strand Federation — air-gapped pack export / import ───────────────────
try:
    from cursiv_v215.core.strand_federation import (
        export_pack  as _sfed_export,
        import_pack  as _sfed_import,
        pack_summary as _sfed_summary,
        PACK_EXT     as _PACK_EXT,
    )
    _SFED_OK = True
except Exception:
    _SFED_OK = False
    def _sfed_export(*a, **kw) -> str:        return ""
    def _sfed_import(t) -> tuple:             return [], {}, {}
    def _sfed_summary(s, m) -> str:           return ""
    _PACK_EXT = ".cursivpack"

# ── Quality scorer ────────────────────────────────────────────────────────
try:
    from cursiv_v215.core.quality_scorer import (
        score_response  as _qs_score,
        format_scores   as _qs_fmt,
    )
    _QS_OK = True
except Exception:
    _QS_OK = False
    def _qs_score(*a, **kw) -> dict: return {}
    def _qs_fmt(s, **kw) -> str:    return ""

# ── Strand Store — persistent memory across sessions ──────────────────────
try:
    from cursiv_v215.core.strand_store import (
        save_strand        as _strand_save,
        list_strands       as _strand_list,
        search_strands     as _strand_search,
        format_strand_list as _strand_fmt,
        strand_count       as _strand_count,
        territory_counts   as _strand_terr_counts,
        load_territories   as _strand_territories,
    )
    _STRAND_OK = True
except Exception:
    _STRAND_OK = False
    def _strand_save(*a, **kw) -> str:           return ""
    def _strand_list(**kw) -> list:              return []
    def _strand_search(q, **kw) -> list:         return []
    def _strand_fmt(s) -> str:                   return ""
    def _strand_count() -> int:                  return 0
    def _strand_terr_counts() -> dict:           return {}
    def _strand_territories() -> dict:           return {}

# ── Postal — sealed encrypted letters ────────────────────────────────────────
try:
    from cursiv_v215.postal.sealed_store import (
        seal_letter        as _postal_seal,
        open_letter        as _postal_open,
        get_sealed_entry   as _postal_entry,
        get_sig_status     as _postal_sig_status,
        letters_for        as _postal_for,
        letters_from       as _postal_from,
        all_letters        as _postal_all,
        delete_sealed      as _postal_delete,
        export_sealpack    as _postal_export,
        import_sealpack    as _postal_import,
    )
    from cursiv_v215.postal.council_reader import council_walkthrough as _postal_council
    from cursiv_v215.postal.user_registry import (
        setup_identity      as _postal_setup,
        my_identity         as _postal_my_id,
        add_contact         as _postal_add_contact,
        remove_contact      as _postal_rm_contact,
        list_contacts       as _postal_contacts,
        resolve_recipient   as _postal_resolve,
        rotate_identity     as _postal_rotate,
        key_rotation_history as _postal_key_history,
    )
    _POSTAL_OK = True
except Exception:
    _POSTAL_OK = False
    def _postal_seal(*a, **kw):            return ""
    def _postal_open(i):                   return None
    def _postal_entry(i):                  return None
    def _postal_sig_status(i):             return "unknown"
    def _postal_for(k):                    return []
    def _postal_from(k):                   return []
    def _postal_all():                     return []
    def _postal_delete(i):                 return False
    def _postal_export(i):                 return None
    def _postal_import(f, p):              return None
    def _postal_council(i, u, c, **kw):   return "[Postal module unavailable]"
    def _postal_setup(n):                  return {}
    def _postal_my_id():                   return None
    def _postal_add_contact(n, k):         return {}
    def _postal_rm_contact(n):             return False
    def _postal_contacts():                return []
    def _postal_resolve(n):                return None
    def _postal_rotate(reason="", **kw):   return {}
    def _postal_key_history():             return []

# ── Board client — blast council syntheses to the public board ───────────────
try:
    from cursiv_v215.web.board_client import (
        board_login    as _board_login,
        board_register as _board_register,
        board_logout   as _board_logout,
        board_whoami   as _board_whoami,
        board_blast    as _board_blast,
    )
    _BOARD_OK = True
except Exception:
    _BOARD_OK = False
    def _board_login(u, p):    return (False, "board client unavailable")
    def _board_register(u, p): return (False, "board client unavailable")
    def _board_logout():       pass
    def _board_whoami():       return None
    def _board_blast(t, s):    return (False, "board client unavailable")

# ── Substrate Fork — RUW / Curs. ────────────────────────────────────────────
try:
    from cursiv_v215.substrate.activator import get_activator as _get_activator
    _SUBSTRATE_OK = True
except Exception:
    _SUBSTRATE_OK = False
    def _get_activator(): return None  # type: ignore


def _extract_blast_synthesis(full_text: str) -> str:
    """
    Extract just the final answer paragraph from group_discovery output.
    Finds the FINAL SYNTHESIS section, then takes the last substantive
    paragraph within it — that's Ollama's closing declarative answer.
    """
    FINAL_MARKER = "FINAL SYNTHESIS — LOCAL COUNCIL"   # — em-dash
    END_MARKER   = "CURSIV BINARY SNAPSHOT"

    body = full_text

    start = full_text.find(FINAL_MARKER)
    if start != -1:
        # skip past the marker line and the ═══ decorator line after it
        after_marker  = full_text.find("\n", start) + 1
        after_deco    = full_text.find("\n", after_marker) + 1
        end = full_text.find(END_MARKER, after_deco)
        if end == -1:
            end = len(full_text)
        body = full_text[after_deco:end].strip(" \n─-")

    # From the body, take the last non-empty paragraph that isn't a header/meta line
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    skip = {"SEED:", "*1 provider", "█", "═", "---"}
    for p in reversed(paragraphs):
        if len(p) > 40 and not any(s in p for s in skip) and not p.startswith("**["):
            return p

    return body.strip() or full_text.strip()


# ── Async Council — Option C parallel deliberation ───────────────────────────
try:
    from cursiv_v215.council.async_council import (
        run_council       as _async_council_run,
        council_available as _async_council_ok,
        detect_full_mode  as _async_council_detect_full,
    )
    _ASYNC_COUNCIL_OK = True
except Exception:
    _ASYNC_COUNCIL_OK = False
    def _async_council_run(q, cfg, **kw):        return None
    def _async_council_ok(cfg):                  return False
    def _async_council_detect_full(q):           return False, q, ""

# ── System Guardian — back-end CLI defense layer ────────────────────────────
try:
    from cursiv_v215.guardian.temple_guardian import (
        scan_cli        as _guardian_scan_cli,
        get_strike_count as _guardian_strike_count,
        SKULL_ANSI      as _GUARDIAN_SKULL_ANSI,
    )
    from cursiv_v215.guardian.obfuscation import session_fingerprint as _sfp
    _CLI_GUARDIAN_OK = True
except Exception:
    _CLI_GUARDIAN_OK = False
    def _guardian_scan_cli(msg, sid="cli"):  return (False, None)
    def _guardian_strike_count(sid="cli"):   return 0
    _GUARDIAN_SKULL_ANSI = ""
    def _sfp():                              return "--------"

# ── Constitutional chain — governor context injection ───────────────────────
try:
    from cursiv_v215.guardian.constitutional_chain import (
        build_chain   as _build_chain,
        chain_summary as _chain_summary,
    )
    _CHAIN_OK = True
except Exception:
    _CHAIN_OK = False
    def _build_chain(session_id="default", pass_count=1):  return ""
    def _chain_summary(pass_count=1):                      return ""

_CLI_SESSION_ID = f"cli_{os.getpid()}"

# ── Rate limiter + scan display ────────────────────────────────────────────
try:
    from cursiv_v215.core.rate_limiter import limiter as _cli_limiter
    from cursiv_v215.core.scan_display import ScanDisplay as _CLI_ScanDisplay
    _cli_scan = _CLI_ScanDisplay(_cli_limiter)
    _RATE_CLI_OK = True
except Exception:
    _cli_limiter  = None
    _cli_scan     = None
    _RATE_CLI_OK  = False

# ── prompt_toolkit for paste-safe input + wide-char width ──────────────────
# paste-safe: bracketed paste mode so the whole paste lands as one message.
# get_cwidth: correctly counts wide chars (✦ ✓ ✋ etc) as 2 columns so box
#             borders align properly on all terminals.
try:
    from prompt_toolkit import prompt as _pt_prompt
    from prompt_toolkit.formatted_text import ANSI as _PT_ANSI
    from prompt_toolkit.utils import get_cwidth as _cwidth
    # On Windows, prompt_toolkit imports fine but crashes the first time
    # prompt() is called when the terminal is xterm-256color (Git Bash, VS Code
    # integrated terminal, Cygwin). Pre-check so we fall back gracefully instead
    # of crashing mid-session.
    if os.name == "nt":
        from prompt_toolkit.output.defaults import create_output as _pt_check_output
        _pt_check_output()   # raises NoConsoleScreenBufferError on bad terminals
    _HAS_PT = True
except Exception:
    _HAS_PT = False
    def _cwidth(c: str) -> int:          # fallback: treat everything as 1
        return 1

# ── Enable ANSI on Windows ─────────────────────────────────────────────────
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        os.system("color")

# ── Palette ────────────────────────────────────────────────────────────────
# ── Sacred Palette — Egyptian Temple ─────────────────────────────────────
GOLD   = "\033[38;5;220m"   # Egyptian gold — AI prefix, icons, accents
LGOLD  = "\033[38;5;136m"   # Deep antique gold — borders, frames
SILVER = "\033[38;5;253m"   # Bright silver — user text
SILV2  = "\033[38;5;245m"   # Dim silver — secondary labels, hints
LAPIS  = "\033[38;5;27m"    # Lapis lazuli — user indicator, input box
LAPIS2 = "\033[38;5;69m"    # Light lapis — highlights
CREAM  = "\033[38;5;230m"   # Ivory cream — AI response body
DIM    = "\033[2m"
RED    = "\033[38;5;196m"
GREEN  = "\033[38;5;82m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

_ANSI = re.compile(r"\033\[[0-9;]*[mABCDEFGHJKST]")

# ── API connectivity probes ────────────────────────────────────────────────

def _probe_xai(key: str) -> bool:
    try:
        req = urllib.request.Request(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _probe_openai(key: str) -> bool:
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _probe_claude(key: str) -> bool:
    try:
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "content-type": "application/json",
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


_KEYS_FILE = Path(ROOT) / ".cursiv" / "config.json"

def _load_saved_keys() -> dict:
    try:
        data = json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, str)}
    except Exception:
        return {}

def _save_key(field: str, value: str) -> None:
    try:
        try:
            data = json.loads(_KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data[field] = value
        _KEYS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _api_chip(label: str, key: str, live) -> str:
    """Colored status chip: green=live, red=fail or off, gold=untested."""
    if not key:
        return f"{RED}{label}:✗{RESET}"
    if live is True:
        return f"{GREEN}{label}:OK{RESET}"
    if live is False:
        return f"{RED}{label}:✗{RESET}"
    return f"{GOLD}{label}:?{RESET}"


# ── Layout ──────────────────────────────────────────────────────────────────
_HEADER_ROWS = 6    # rows the fixed header occupies (5 box lines + 1 blank)
_layout_on   = False  # True once scroll-region layout is active


def _vlen(s: str) -> int:
    return sum(_cwidth(c) for c in _ANSI.sub("", s))


def _pad(s: str, w: int) -> str:
    return s + " " * max(0, w - _vlen(s))


def _cols() -> int:
    return max(shutil.get_terminal_size((100, 30)).columns, 52)


# ── Box drawing ────────────────────────────────────────────────────────────

def _top(w: int, label: str = "") -> str:
    if not label:
        return f"{LGOLD}╔{'═' * (w - 2)}╗{RESET}"
    avail = w - 4 - _vlen(label)
    side  = max(avail // 2, 1)
    extra = "═" if avail % 2 else ""
    bar   = "═" * side
    return f"{LGOLD}╔{bar} {GOLD}{BOLD}{label}{RESET}{LGOLD} {bar}{extra}╗{RESET}"


def _mid(w: int, ch: str = "═") -> str:
    return f"{LGOLD}╠{ch * (w - 2)}╣{RESET}"


def _bot(w: int) -> str:
    return f"{LGOLD}╚{'═' * (w - 2)}╝{RESET}"


def _row(content: str, w: int) -> str:
    inner = w - 4
    return f"{LGOLD}║{RESET} {_pad(content, inner)} {LGOLD}║{RESET}"


def _sep(w: int) -> str:
    # Alternating lapis dashes + silver dots — digital-stream divider
    units  = (w - 4) // 2
    stream = (f"{LAPIS2}╌{RESET}{SILV2}·{RESET}") * units
    return f"  {stream}"


# ── Status header (printed at startup and when settings change) ────────────

def _draw_header(cfg: dict) -> None:
    """Print the 6-row header block (5 box lines + 1 blank). No scroll logic."""
    w = _cols()

    icons = (
        f"{GOLD}{BOLD}✦ CURSIV{RESET}  {LGOLD}v3.0{RESET}"
        f"  {SILV2}·{RESET}  "
        f"{LAPIS}{BOLD}◈ GUARDIAN{RESET}  {SILV2}·{RESET}  "
        f"{LAPIS}⬡ COUNCIL ×14{RESET}  {SILV2}·{RESET}  "
        f"{GOLD}◉ NEXUS{RESET}  {SILV2}·{RESET}  "
        f"{SILV2}⟳ SOVEREIGN{RESET}"
    )
    print(_top(w))
    print(_row(icons, w))
    print(_mid(w))

    xai_s  = _api_chip("xAI",    cfg.get("api_key", ""),           cfg.get("xai_live"))
    oai_s  = _api_chip("OpenAI", cfg.get("openai_key", ""),        cfg.get("openai_live"))
    ant_s  = _api_chip("Claude", cfg.get("anthropic_key", ""),     cfg.get("claude_live"))
    fa_s   = (f"{GREEN}files:ON{RESET}"  if cfg["file_access"]       else f"{RED}files:OFF{RESET}")
    mode_s = (f"{RED}CONFIRM[!]{RESET}"  if cfg["confirm_mode"] == "confirm" else f"{GREEN}AUTO{RESET}")
    grd_s  = (f"{GREEN}Guard:{_sfp()}{RESET}" if _CLI_GUARDIAN_OK   else f"{RED}Guard:✗{RESET}")
    obs_s  = (f"{GREEN}Obs:ON{RESET}"    if cfg.get("obsidian_enabled") else f"{RED}Obs:OFF{RESET}")
    _tier  = cfg.get("trust_tier", 3)
    _tier_s = (f"{GREEN}T1:SOVEREIGN{RESET}" if _tier == 1
               else f"{GOLD}T2:LIMITED{RESET}" if _tier == 2
               else f"{SILV2}T3:COUNCIL{RESET}")
    _gov_s = (f"  {LAPIS}GOV{RESET}" if cfg.get("cursiv_mode") == "governor" else "")
    _off_s = (f"  {GREEN}OFFLINE{RESET}" if cfg.get("offline_mode") else "")
    status = (
        f"  {xai_s}  {oai_s}  {ant_s}  {fa_s}  "
        f"mode:{mode_s}  {grd_s}  {obs_s}  {_tier_s}{_gov_s}{_off_s}  {SILV2}'help'{RESET}"
    )
    print(_row(status, w))
    print(_bot(w))
    print()   # blank — counts as the 6th fixed row


def _update_fixed_header(cfg: dict) -> None:
    """Repaint the sticky header in-place without disturbing the scroll area."""
    h = shutil.get_terminal_size((80, 24)).lines
    # Save cursor · expand to full screen · jump to top-left
    sys.stdout.write(f"\033[s\033[1;{h}r\033[H")
    for _ in range(_HEADER_ROWS):
        sys.stdout.write("\033[2K\n")   # erase line + move down
    sys.stdout.write("\033[H")          # back to top-left
    sys.stdout.flush()
    _draw_header(cfg)
    # Restore scroll region · restore cursor
    sys.stdout.write(f"\033[{_HEADER_ROWS + 1};{h}r\033[u")
    sys.stdout.flush()


def _init_layout(cfg: dict) -> None:
    """
    Clear screen and paint the header at the top.
    Does NOT use a scroll region — native terminal scrollback stays intact
    so the user can freely scroll up through full conversation history.
    Current status is always visible in the input-box status bar below.
    """
    sys.stdout.write("\033[2J\033[H")   # clear screen + home
    sys.stdout.flush()
    _draw_header(cfg)


def _print_header(cfg: dict) -> None:
    """Public entry — routes to scroll-region repaint or plain draw."""
    if _layout_on:
        _update_fixed_header(cfg)
    else:
        _draw_header(cfg)


# ── Message printing ───────────────────────────────────────────────────────

def _print_ai_msg(text: str) -> None:
    w      = _cols()
    wrap_w = max(w - 16, 20)
    pfx0   = f"  {GOLD}{BOLD}✦{RESET}  {GOLD}CURSIV{RESET}  "
    pfxN   = "              "
    first  = True
    for para in text.splitlines():
        if not para.strip():
            print()
            first = True
            continue
        for seg in textwrap.wrap(para, width=wrap_w) or [""]:
            pfx = pfx0 if first else pfxN
            print(f"{pfx}{CREAM}{seg}{RESET}")
            first = False


def _print_user_msg(text: str) -> None:
    w = _cols()
    print(_sep(w))
    print()


def _print_owner_reveal(cfg: dict) -> None:
    import json as _json
    from pathlib import Path as _Path
    w = _cols()

    try:
        from cursiv_v215.guardian.obfuscation     import session_fingerprint as _sfp_r
        from cursiv_v215.guardian.temple_guardian import get_session_threat_level, get_strike_count
        fingerprint  = _sfp_r()
        threat_level = get_session_threat_level(_CLI_SESSION_ID)
        strikes      = get_strike_count(_CLI_SESSION_ID)
    except Exception:
        fingerprint  = "--------"
        threat_level = 0.0
        strikes      = 0

    root      = _Path(__file__).parent.parent.parent
    reg_path  = root / ".cursiv" / "agent_registry.json"
    mem_path  = root / ".cursiv" / "memory.json"
    train_p   = root / ".cursiv" / "training_data.jsonl"
    glog_p    = root / ".cursiv" / "guardian_log.jsonl"

    agents: list[dict] = []
    if reg_path.exists():
        try:
            data   = _json.loads(reg_path.read_text(encoding="utf-8"))
            agents = [{"name": m.get("name","?"), "id": aid[:8], "state": m.get("state","?")}
                      for aid, m in data.get("agents", {}).items()]
        except Exception:
            pass

    mem_count = 0
    if mem_path.exists():
        try:
            mem_count = len(_json.loads(mem_path.read_text()).get("agents", {}))
        except Exception:
            pass

    tc = sum(1 for _ in open(train_p, encoding="utf-8")) if train_p.exists() else 0
    gc = sum(1 for _ in open(glog_p,  encoding="utf-8")) if glog_p.exists()  else 0

    obs_cfg  = _obs_load_config()
    obs_line = ("ON  " + obs_cfg.get("vault_path","")) if obs_cfg.get("enabled") else "OFF"

    print()
    print(f"  {GOLD}{BOLD}{'═' * (w - 4)}{RESET}")
    print(f"  {GOLD}{BOLD}  OWNER VERIFIED  --  GUARDIAN SUSPENDED{RESET}")
    print(f"  {GOLD}{BOLD}  Joshua Winkler  --  System Owner{RESET}")
    print(f"  {GOLD}{'═' * (w - 4)}{RESET}")
    print()
    print(f"  {LGOLD}Session ID      :{RESET}  {_CLI_SESSION_ID}")
    print(f"  {LGOLD}Guardian token  :{RESET}  {fingerprint}  (rotates on restart)")
    print(f"  {LGOLD}Threat level    :{RESET}  {threat_level:.4f}  (strikes: {strikes})")
    print(f"  {LGOLD}Owner unlock    :{RESET}  {GREEN}ACTIVE -- all scans bypassed{RESET}")
    print()
    print(f"  {GOLD}-- VAULT  ({len(agents)} agents) {'-' * max(0, w - 25)}{RESET}")
    for a in agents[:14]:
        print(f"    {GREEN}{a['name']:22s}{RESET}  id:{a['id']}  state:{a['state']}")
    print()
    print(f"  {GOLD}-- SYSTEM STATE {'-' * max(0, w - 22)}{RESET}")
    print(f"  {LGOLD}Memory agents   :{RESET}  {mem_count}")
    print(f"  {LGOLD}Training data   :{RESET}  {tc} examples")
    print(f"  {LGOLD}Guardian log    :{RESET}  {gc} probe events")
    print(f"  {LGOLD}Obsidian sync   :{RESET}  {obs_line}")
    print()
    print(f"  {GOLD}{'═' * (w - 4)}{RESET}")
    print(f"  {DIM}Owner verified. System is fully open.{RESET}")
    print(f"  {GOLD}{'═' * (w - 4)}{RESET}")
    print()


# ── Rotating command tips (cycle through on every exchange) ───────────────
_tip_idx = 0
_TIPS: list[tuple[str, str]] = [
    ("grow <file>",            "read a file and generate its next natural addition"),
    ("grow system",           "scan the full codebase and suggest the next capability"),
    ("council <question>",    "3-cycle multi-provider synthesis — all seeing eye"),
    ("anchor this",           "save last exchange as a permanent Strand"),
    ("babel <text>",          "any language → English  /  babel <text> into <lang(s)>  English → any"),
    ("voice",                  "mic → Whisper STT → Babel clean → inject as message"),
    ("voice raw  /  voice 10", "STT only (skip Babel pass) or custom duration"),
    ("image <prompt>",        "generate image with DALL-E 3"),
    ("paste",                 "paste clipboard image → vision analysis → Strand"),
    ("remember <query>",      "search your Strand archive, zero cloud, zero API"),
    ("pull <url>",            "fetch, analyze, and strand any webpage"),
    ("strands",               "browse the permanent memory archive"),
    ("hey grok / hey claude", "route a single message to a specific provider"),
    ("strand export",         "air-gap pack Strands to .cursivpack for USB transfer"),
    ("rate good / rate bad",  "signal training quality on the last response"),
    ("overseer on",           "Grok generates, Claude reviews every reply"),
    ("funforge <topic>",      "bounded 45-min creative spike"),
    ("search <query>",        "real-time web search + AI synthesis"),
    ("files on",              "enable file-system access for AI tools"),
    ("mode",                  "toggle AUTO / CONFIRM write mode"),
    ("obsidian on",           "sync sessions live to your Obsidian vault"),
    ("codex <prompt>",        "offline code specialist — no API key needed"),
    ("tier 1 / 2 / 3",       "trust tier: T1=offline-only  T2=local+limited  T3=full"),
    ("offline on / off",      "hard-block all external APIs — pure sovereign mode"),
    ("governor on / off",     "elevate to constitutional governing mode"),
]


# ── Input prompt box ───────────────────────────────────────────────────────

def _input_prompt(cfg: dict) -> str:
    """
    Full-width gold separator with all three provider status chips, then a
    rotating tip line, then the Eye of Horus prompt.
    Claude Code-style: minimal, no box borders, full terminal width.
    Bracketed paste via prompt_toolkit when available.
    """
    global _tip_idx
    w = _cols()

    # All three provider chips
    xai_s  = _api_chip("xAI",    cfg.get("api_key", ""),       cfg.get("xai_live"))
    oai_s  = _api_chip("OpenAI", cfg.get("openai_key", ""),    cfg.get("openai_live"))
    ant_s  = _api_chip("Claude", cfg.get("anthropic_key", ""), cfg.get("claude_live"))
    fa_s   = (f"{GREEN}files:ON{RESET}" if cfg.get("file_access") else f"{RED}files:OFF{RESET}")
    mode_s = (f"{RED}CONFIRM{RESET}"    if cfg["confirm_mode"] == "confirm" else f"{GREEN}AUTO{RESET}")
    ov_s   = (f"  {LAPIS}⚖{RESET}" if cfg.get("overseer_mode") else "")

    # TPM bar (compact 6-block)
    tpm_chip = ""
    try:
        from cursiv_v215.core.rate_limiter import limiter as _rl
        used   = _rl.current_tpm()
        target = _rl.target
        pct    = min(used / max(target, 1), 1.0)
        filled = int(pct * 6)
        col    = GREEN if pct < 0.70 else (GOLD if pct < 0.90 else RED)
        tpm_chip = f"  {col}{'█' * filled}{'░' * (6 - filled)}{RESET}  {SILV2}{used // 1000}k{RESET}"
    except Exception:
        pass

    # FunForge timer
    ff   = cfg.get("funforge_session")
    ff_s = ""
    if ff and not ff.closed:
        ff_s = (f"  {RED}⬡DONE{RESET}" if ff.expired
                else f"  {GOLD}⬡{ff.time_display()}{RESET}")

    # Full-width gold separator — Eye of Horus + all provider chips
    status = (
        f" {GOLD}𓂀{RESET}  "
        f"{xai_s}  {oai_s}  {ant_s}  {fa_s}  {mode_s}"
        f"{ov_s}{ff_s}{tpm_chip}  {SILV2}·{RESET} "
    )
    sw     = _vlen(status)
    remain = max(0, w - sw)
    lw     = remain // 2
    rw     = remain - lw
    sep    = f"{LGOLD}{'─' * lw}{RESET}{status}{LGOLD}{'─' * rw}{RESET}"

    print(f"\n{sep}")

    # Rotating tip — advances each exchange so users discover all commands
    tip_cmd, tip_desc = _TIPS[_tip_idx % len(_TIPS)]
    _tip_idx += 1
    print(f"  {SILV2}·{RESET}  {LGOLD}{tip_cmd}{RESET}  {DIM}{tip_desc}{RESET}")

    # 𓂀 = Eye of Horus (U+13080). Requires Noto Sans Egyptian Hieroglyphs or
    # Segoe UI Historic — shows as □ on systems without the font; swap to ⊙.
    prefix_ansi = f"{GOLD}𓂀{RESET}  "

    try:
        if _HAS_PT:
            raw = _pt_prompt(_PT_ANSI(prefix_ansi))
        else:
            sys.stdout.write(prefix_ansi)
            sys.stdout.flush()
            raw = input("")
    except (EOFError, KeyboardInterrupt):
        raise KeyboardInterrupt

    return raw.strip()


# ── Pending-write confirm ──────────────────────────────────────────────────

def _handle_pending_write(raw_json: str, cfg: dict) -> str:
    try:
        pending = json.loads(raw_json)
    except Exception:
        return "[Could not parse pending write]"

    path_str = pending.get("path", "?")
    content  = pending.get("content", "")
    preview  = content[:400] + ("..." if len(content) > 400 else "")

    w = _cols()
    print(f"\n  {RED}{BOLD}Write pending → {path_str}{RESET}")
    print(f"  {DIM}{'─' * (w - 4)}{RESET}")
    for line in preview.splitlines():
        print(f"  {DIM}{line}{RESET}")
    print(f"  {DIM}{'─' * (w - 4)}{RESET}\n")

    while True:
        try:
            if _HAS_PT:
                ans = _pt_prompt(_PT_ANSI(f"  {RED}Approve write?{RESET}  [y/n]: ")).strip().lower()
            else:
                ans = input(f"  {RED}Approve write?{RESET}  [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"
        if ans in ("y", "yes"):
            workspace = Path(cfg["workspace"]).expanduser().resolve()
            result    = execute_tool("write_file", pending, workspace)
            print(f"\n  {GREEN}✓ {result}{RESET}\n")
            return f"Write approved.\n{result}"
        elif ans in ("n", "no", ""):
            print(f"\n  {DIM}Write cancelled.{RESET}\n")
            return "Write cancelled — file not modified."
        else:
            print("  y or n.")


# ── Built-in command responses ─────────────────────────────────────────────

# ── Grow system prompt ────────────────────────────────────────────────────────
# No training needed — context injection is enough.
# The model reads the real file, absorbs every pattern (naming, error handling,
# strand architecture, ANSI palette, sentinel format) then writes the next
# logical addition in exactly the same voice.
_GROW_SYSTEM = """You are a code evolution engine built into the Cursiv AI operating system.

You will receive a Python source file from the Cursiv codebase. Study it completely:
  - Naming conventions and style (snake_case, UPPER constants, _private prefix)
  - Import patterns (try/except with graceful fallbacks)
  - Error handling approach
  - ANSI palette usage (GOLD, LGOLD, CREAM, LAPIS, SILV2, RESET)
  - Strand saving patterns (save_strand with territory, source, score)
  - How it interacts with the rest of the system

Then write the NEXT logical addition this module needs. It should feel like it was
always part of the file — same style, same patterns, same architecture, same voice.

Think about what is clearly missing or what the module is reaching toward but hasn't
finished. Write the next natural function, class, constant block, or section.

Output ONLY the new Python code. No explanation. No markdown fences. No preamble.
Just the code that comes next, ready to append to the file."""

_GROW = f"""\
  {GOLD}── Grow (self-referential code evolution) ───────────────────────{RESET}
  {LGOLD}grow <file>{RESET}               read a source file and generate its next natural addition
  {LGOLD}grow system{RESET}              read the full system map and suggest the next capability
                            No training required — context injection only.
                            Points qwen2.5-coder at your real code, absorbs your
                            patterns, writes the next logical line in your voice."""

_HELP = f"""\
  {LGOLD}key  <xai-key>{RESET}            set xAI Grok API key       (starts with xai-)
  {LGOLD}openai <key>{RESET}              set OpenAI API key          (starts with sk-)
  {LGOLD}anthropic <key>{RESET}           set Anthropic API key       (starts with sk-ant-)
  {LGOLD}files on / off{RESET}            enable / disable file-system access
  {LGOLD}workspace <path>{RESET}          sandbox root for file tools
  {LGOLD}mode{RESET}                      toggle write mode  (auto <-> confirm)

  {GOLD}── Codex Agent (offline code specialist) ───────────────────────{RESET}
  {LGOLD}codex <prompt>{RESET}            call Codex directly — produces ready-to-run code
                            works offline, no API key needed
                            also fires automatically for any code-classified message

  {GOLD}── Web Search (real-time, worldwide) ────────────────────────────{RESET}
  {LGOLD}search: <query>{RESET}           search the web right now + AI synthesis
  {LGOLD}search <query>{RESET}            same — no colon required
                            auto-fires on phrases like "latest", "today",
                            "who won", "price of", "breaking" etc.
                            Uses Brave Search API if BRAVE_API_KEY is set,
                            DuckDuckGo otherwise (free, no key needed)

  {GOLD}── Voice Agent (two-stage: STT → Babel clean) ───────────────────{RESET}
  {LGOLD}voice{RESET}                     record 5s → faster-whisper STT → Babel binary clean → inject
  {LGOLD}voice <seconds>{RESET}           custom duration  (e.g.  voice 10)
  {LGOLD}voice raw{RESET}                 STT only — skip the Babel cleaning pass
  {LGOLD}listen{RESET}                    alias for  voice raw
                            Stage 1 (STT): faster-whisper (local, CPU int8)
                              → Vosk fallback → SpeechRecognition+Sphinx last resort
                            Stage 2 (clean): raw text → Babel binary encode → LLM
                              fixes filler words, transcription errors, translates
                              non-English speech — reuses existing Babel pipeline
                            Requires:  pip install faster-whisper sounddevice
                            Whisper model downloads once to .cursiv/voice/ (~466 MB small)

  {GOLD}── Babel Agent (universal translation) ─────────────────────────{RESET}
  {LGOLD}babel <text>{RESET}              any language → UTF-8 binary → English
  {LGOLD}babel: <text>{RESET}             same with colon
                            Works for every script: Chinese, Arabic, Japanese,
                            Russian, Hindi, Korean, etc.
                            Example:  babel Bonjour le monde
                            Example:  babel こんにちは世界

  {LGOLD}babel <text> into <lang>{RESET}  translate English text into target language(s)
                            Multiple targets supported — separate with spaces
                            Example:  babel I love you into korean mandarin russian
                            Example:  babel Good morning into spanish french japanese

  {GOLD}── Council (async parallel deliberation) ──────────────────────{RESET}
  {LGOLD}council <question>{RESET}        all providers fire simultaneously — each streams
                            live, synthesis deliberates across signals
  {LGOLD}/full <question>{RESET}          full deliberation mode — complete responses,
  {LGOLD}/deliberate <question>{RESET}    no signal extraction, synthesis gets everything
                            also triggers on phrase: "show your reasoning",
                            "full deliberation", "walk me through", etc.
                            or automatically when query touches a territory
                            marked  full_token_required: true  in territories.json
  {LGOLD}hey council <question>{RESET}    inline routing prefix (same as council)

  {GOLD}── Substrate Fork — RUW / Curs. ─────────────────────────────{RESET}
  {LGOLD}substrate{RESET}                 activate last council synthesis into RUW layer
  {LGOLD}substrate status{RESET}          show RUW layer state (nodes, edges, address)
  {LGOLD}substrate weave <query>{RESET}   read substrate — find resonant nodes for a query
                            Each activation builds attractor basins over time.
                            The substrate learns the shape of your thinking.
                            Address format: Curs.html://ruw.www.cursiv.<suffix>/<id>

  {GOLD}── Blast (public board transmission) ──────────────────────────{RESET}
  {LGOLD}blast register <username>{RESET} create your board account
  {LGOLD}blast login <username>{RESET}    log in to the board
  {LGOLD}blast logout{RESET}              log out
  {LGOLD}blast who{RESET}                 show current board user
  {LGOLD}blast{RESET}                     post last council synthesis to the public board
                            run a council deliberation first, then blast to send
                            live at cursiv.winklers-llc.com/board

  {GOLD}── Strand Archive (persistent memory across sessions) ───────────{RESET}
  {LGOLD}anchor this{RESET}               save last exchange as a Strand (permanent)
  {LGOLD}anchor this <territory>{RESET}   same, tagged to a domain
                            territories: coding  recovery  architecture  creative  worldmodel
  {LGOLD}strands{RESET}                   show recent Strand archive + territory counts
  {LGOLD}strands <territory>{RESET}       filter by territory  (e.g.  strands coding)
  {LGOLD}strands search <query>{RESET}    semantic search across all Strands
  {LGOLD}strand export{RESET}             export all Strands to a .cursivpack file (USB/LAN transfer)
  {LGOLD}strand export <territory>{RESET} export one territory only
  {LGOLD}strand import <file>{RESET}      Guardian-verified, human-approved import from a pack file
  {LGOLD}remember <query>{RESET}          pure local memory search — zero cloud, zero API
  {LGOLD}pull <url>{RESET}                fetch + analyze any URL → auto-strand the insight
  {LGOLD}image <description>{RESET}       generate image via DALL-E 3 → saves + opens + strands
  {LGOLD}paste{RESET}                     paste image from clipboard → vision analysis → strand
                            Council syntheses auto-anchor at quality > 0.75

  {GOLD}── FunForge (bounded creative spike) ───────────────────────────{RESET}
  {LGOLD}funforge <topic>{RESET}          start a 45-min bounded creative spike
  {LGOLD}spike <topic>{RESET}             same shorthand
  {LGOLD}forge extend{RESET}              add 30 min (one time only)
  {LGOLD}forge done{RESET}                close spike and produce artifact
  {LGOLD}anchor this{RESET}               also anchors the spike as a Strand when FunForge is active

  {GOLD}── Model switching ──────────────────────────────────────────────{RESET}
  {LGOLD}grok{RESET}                      re-run last message with Grok (xAI)
  {LGOLD}claude{RESET}                    re-run last message with Claude (Anthropic)
  {LGOLD}overseer on / off{RESET}         Claude reviews every Grok response (weight system)
                            Grok generates → Claude verifies & critiques
  {LGOLD}status{RESET}                    shows active model + overseer state

  {GOLD}── Modes & Trust ────────────────────────────────────────────────{RESET}
  {LGOLD}tier 1{RESET}                    Ollama/Codex only — fully offline, zero cloud
  {LGOLD}tier 2{RESET}                    local models + one external API allowed
  {LGOLD}tier 3{RESET}                    full council (all providers) — default
  {LGOLD}offline on / off{RESET}          hard-block all external APIs (forces tier 1)
  {LGOLD}governor on / off{RESET}         constitutional governing mode — formal system prompt,
                            no first-name familiarity, strict alignment framing

  {GOLD}── Training Signal ───────────────────────────────────────────────{RESET}
  {LGOLD}rate good{RESET}                 mark last response as excellent  (5/5)
  {LGOLD}rate bad{RESET}                  mark last response as poor       (1/5)
  {LGOLD}rate <1-5>{RESET}                numeric rating: 1=poor  5=excellent
                            Saved to training queue — human ratings override
                            Academy's automated scoring for future LoRA work

  {GOLD}── Obsidian & system ────────────────────────────────────────────{RESET}
  {LGOLD}obsidian on / off{RESET}         enable / disable Obsidian vault sync
  {LGOLD}obsidian path <vault-path>{RESET}  set Obsidian vault folder
  {LGOLD}obsidian export{RESET}           export today's training data to vault now
  {LGOLD}obsidian status{RESET}           show Obsidian sync config
  {LGOLD}clear{RESET}                     wipe conversation history
  {LGOLD}help{RESET}                      this list
  {LGOLD}exit{RESET}                      quit"""


def _status_str(cfg: dict) -> str:
    ant_label = "set (code tool — fires on file writes)" if cfg.get("anthropic_key") else "not set"
    oai_label = "set" if cfg["openai_key"] else "not set"
    obs_path  = cfg.get("obsidian_path", "") or "(not set)"
    codex_label  = "active (offline)" if (_CODEX_CLI_OK and _codex_avail_cli())  else "not found"
    hermes_label = "active (offline)" if (_HERMES_CLI_OK and _hermes_avail_cli()) else "not found"
    ref_label    = "active (offline)" if (_REF_CLI_OK and _ref_avail_cli())       else "not found"
    queue_label  = f"{_queue_count_cli()} task(s) queued" if _QUEUE_CLI_OK        else "not found"
    # Active model — xAI primary, OpenAI second, Claude code-tool only
    if cfg.get("api_key"):
        claude_note = "  [Claude: code tool]" if cfg.get("anthropic_key") else ""
        active_model = f"Grok-3 (xAI){claude_note}"
    elif cfg.get("openai_key"):
        claude_note = "  [Claude: code tool]" if cfg.get("anthropic_key") else ""
        active_model = f"GPT-4.1 (OpenAI){claude_note}"
    elif cfg.get("anthropic_key"):
        active_model = "Claude claude-sonnet-4-6 (no xAI/OpenAI key — last resort)"
    else:
        active_model = "Ollama (local)"
    overseer = "ON  — primary model → Claude reviews" if cfg.get("overseer_mode") else "OFF"
    return (
        f"  xAI key       : {'set' if cfg['api_key']    else 'not set'}\n"
        f"  OpenAI key    : {oai_label}\n"
        f"  Anthropic key : {ant_label}\n"
        f"  Codex Agent   : {codex_label}\n"
        f"  Hermes Agent  : {hermes_label}\n"
        f"  Ref Brain     : {ref_label}\n"
        f"  Offline Queue : {queue_label}\n"
        f"  Active model  : {active_model}\n"
        f"  Overseer mode : {overseer}\n"
        f"  File access   : {'ON'   if cfg['file_access'] else 'OFF'}\n"
        f"  Write mode    : {cfg['confirm_mode'].upper()}\n"
        f"  Workspace     : {cfg['workspace']}\n"
        f"  Obsidian sync : {'ON'  if cfg.get('obsidian_enabled') else 'OFF'}\n"
        f"  Obsidian vault: {obs_path}"
    )


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(prog="cursiv", add_help=False)
    ap.add_argument("path", nargs="?", default="",
                    help="Open Cursiv with this folder as the workspace root")
    args, _ = ap.parse_known_args()

    _obs_cfg_boot = _obs_load_config()
    _obs_vault_boot = _obs_cfg_boot.get("vault_path", "") or _obs_detect_vault()

    # If a path was passed on the command line, use it as the workspace
    launch_ws = str(ROOT)
    if args.path:
        p = Path(args.path).expanduser().resolve()
        if p.exists() and p.is_dir():
            launch_ws = str(p)

    _saved_keys = _load_saved_keys()

    cfg: dict = {
        "api_key":          os.environ.get("XAI_API_KEY",       "") or _saved_keys.get("api_key",       ""),
        "openai_key":       os.environ.get("OPENAI_API_KEY",    "") or _saved_keys.get("openai_key",    ""),
        "anthropic_key":    os.environ.get("ANTHROPIC_API_KEY", "") or _saved_keys.get("anthropic_key", ""),
        "file_access":      False,
        "confirm_mode":     "confirm",
        "funforge_session": None,
        "workspace":        launch_ws,
        "obsidian_enabled": _obs_cfg_boot.get("enabled", False),
        "obsidian_path":    _obs_vault_boot,
        "overseer_mode":    False,   # Grok generates → Claude reviews
        # Live connection status: None=untested, True=ok, False=fail
        "xai_live":    None,
        "openai_live": None,
        "claude_live": None,
        # ── Sovereign architecture controls ───────────────────────────
        "trust_tier":    1 if _netgate.is_offline() else 3,   # 1=offline-only  2=local+1ext  3=full council
        "offline_mode":  _netgate.is_offline(),   # core/netgate.py: blocks every connection off this computer
        "cursiv_mode":   "personal",  # "personal" | "governor"
    }

    # Auto-fix swapped env-var keys
    if cfg["api_key"].startswith("sk-ant-"):
        cfg["anthropic_key"] = cfg["anthropic_key"] or cfg["api_key"]
        cfg["api_key"] = ""
    elif cfg["api_key"].startswith("sk-") or cfg["api_key"].startswith("sk_"):
        cfg["openai_key"] = cfg["openai_key"] or cfg["api_key"]
        cfg["api_key"] = ""
    if cfg["openai_key"].startswith("xai-"):
        cfg["api_key"] = cfg["api_key"] or cfg["openai_key"]
        cfg["openai_key"] = ""

    # ── Startup connectivity probe ────────────────────────────────────────
    _any_key = cfg["api_key"] or cfg["openai_key"] or cfg["anthropic_key"]
    if _any_key:
        sys.stdout.write(f"  {SILV2}Checking API connections...{RESET}  ")
        sys.stdout.flush()
        if cfg["api_key"]:
            cfg["xai_live"] = _probe_xai(cfg["api_key"])
            sys.stdout.write(
                f"{GREEN}xAI:OK{RESET}  " if cfg["xai_live"] else f"{RED}xAI:✗{RESET}  "
            )
            sys.stdout.flush()
        if cfg["openai_key"]:
            cfg["openai_live"] = _probe_openai(cfg["openai_key"])
            sys.stdout.write(
                f"{GREEN}OpenAI:OK{RESET}  " if cfg["openai_live"] else f"{RED}OpenAI:✗{RESET}  "
            )
            sys.stdout.flush()
        if cfg["anthropic_key"]:
            cfg["claude_live"] = _probe_claude(cfg["anthropic_key"])
            sys.stdout.write(
                f"{GREEN}Claude:OK{RESET}  " if cfg["claude_live"] else f"{RED}Claude:✗{RESET}  "
            )
            sys.stdout.flush()
        print()

    history:        list[dict] = []
    last_user_msg:  str       = ""   # used by grok/claude retry commands

    _init_layout(cfg)   # clear screen, paint sticky header, set scroll region

    # ── Boot session summary ──────────────────────────────────────────────
    _boot = _session_boot_summary()
    if _boot:
        _label = "earlier today" if _boot.get("is_today") else _boot.get("date", "?")
        print(f"  {LGOLD}Last session ({_label}) — {RESET}"
              f"{SILVER}{_boot.get('count', 0)} exchanges{RESET}  "
              f"{SILV2}· last model: {GOLD}{_boot.get('last_model', '?')}{RESET}")
        for t in _boot.get("last_topics", [])[-2:]:
            print(f"  {SILV2}  · {t[:90]}{RESET}")

    # ── Strand archive greeting ───────────────────────────────────────────
    if _STRAND_OK:
        _sc = _strand_count()
        if _sc > 0:
            _tcounts = _strand_terr_counts()
            _tline   = "  ".join(f"{t}:{n}" for t, n in _tcounts.items())
            print(f"  {LGOLD}Strand archive  :{RESET}  "
                  f"{SILVER}{_sc} strand{'s' if _sc != 1 else ''}{RESET}  "
                  f"{SILV2}· {_tline}{RESET}")

    if _boot or (_STRAND_OK and _strand_count() > 0):
        print()

    hints = []
    if not cfg["api_key"]:
        hints.append(
            f"  {SILV2}No xAI key.    Type:  {GOLD}key xai-xxxxxxxx{RESET}  {SILV2}(console.x.ai){RESET}"
        )
    if not cfg["openai_key"]:
        hints.append(
            f"  {SILV2}No OpenAI key. Type:  {GOLD}openai sk-xxxxxxxx{RESET}  {SILV2}(platform.openai.com){RESET}"
        )
    hints.append(f"  {RED}Write mode: CONFIRM  — you must approve every file write.{RESET}")
    hints.append(f"  {SILV2}Type 'mode' to switch to AUTO (writes without asking).{RESET}")
    hints.append(f"  {SILV2}Scroll up to read history.  'help' for all commands.{RESET}")
    for h in hints:
        print(h)

    # ── Auto-territory helper (used when saving strands) ─────────────────
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
        if any(w in ql for w in ["research", "history", "world", "science", "civilization", "starlink", "military", "government"]):
            return "worldmodel"
        return "general"

    # ── Governor mode system fragment ─────────────────────────────────────
    _GOVERNOR_SYSTEM = (
        "GOVERNOR MODE ACTIVE. You are operating as the governing constitutional layer of "
        "Cursiv, not the personal companion. Be measured, formal, and constitutionally "
        "grounded. Prioritize accuracy and structural clarity over warmth. "
        "If anything conflicts with core invariants (system_owner=Joshua Winkler, "
        "local_first=True, human_final_authority=True), decline and explain clearly. "
        "No first-name familiarity. No speculative encouragement."
    )

    while True:
        # ── Input ────────────────────────────────────────────────────────
        try:
            raw = _input_prompt(cfg)
        except KeyboardInterrupt:
            print(f"\n\n  {DIM}Goodbye.{RESET}\n")
            break

        if not raw:
            continue

        cmd = raw.lower()

        # ── Built-in commands ────────────────────────────────────────────
        if cmd == "exit":
            print(f"\n  {DIM}Goodbye.{RESET}\n")
            break

        elif cmd == "help":
            print(_HELP)
            continue

        elif cmd == "clear":
            history = []
            _print_header(cfg)
            print(f"  {DIM}History cleared.{RESET}")
            continue

        elif cmd == "mode":
            cfg["confirm_mode"] = "confirm" if cfg["confirm_mode"] == "auto" else "auto"
            print(f"  Write mode → {cfg['confirm_mode'].upper()}")
            continue

        elif cmd in ("tier 1", "tier 2", "tier 3"):
            cfg["trust_tier"] = int(cmd[-1])
            _tier_labels = {
                1: f"{GREEN}TIER 1 — SOVEREIGN OFFLINE{RESET}  {DIM}(Ollama only, maximum sovereignty){RESET}",
                2: f"{GOLD}TIER 2 — LOCAL + LIMITED{RESET}  {DIM}(local first, one external allowed){RESET}",
                3: f"{SILV2}TIER 3 — FULL COUNCIL{RESET}  {DIM}(all providers, experimental mode){RESET}",
            }
            print(f"  Trust tier → {_tier_labels[cfg['trust_tier']]}")
            _print_header(cfg)
            continue

        elif cmd in ("offline on", "offline off"):
            _netgate.set_offline(cmd == "offline on")
            cfg["offline_mode"] = _netgate.is_offline()
            if cfg["offline_mode"]:
                cfg["trust_tier"] = 1
                print(f"  {GREEN}⬡ OFFLINE SOVEREIGN MODE{RESET}  "
                      f"{DIM}No connections off this computer. Tier forced to 1. Stays on after restart.{RESET}")
            else:
                cfg["trust_tier"] = 3
                print(f"  {SILV2}Offline mode OFF.{RESET}  {DIM}External routing restored.{RESET}")
            _print_header(cfg)
            continue

        elif cmd in ("governor on", "governor off", "governor"):
            if cmd == "governor off":
                cfg["cursiv_mode"] = "personal"
                print(f"  {SILV2}Governor mode OFF → Personal mode.{RESET}")
            else:
                cfg["cursiv_mode"] = "governor"
                print(f"\n  {GOLD}╔══════════════════════════════════════════════════╗{RESET}")
                print(f"  {GOLD}║       ⬡  GOVERNOR MODE ENGAGED                  ║{RESET}")
                print(f"  {GOLD}╚══════════════════════════════════════════════════╝{RESET}")
                print(f"  {SILV2}Constitutional enforcement elevated.{RESET}")
                print(f"  {SILV2}Responses will be formal and constitutionally grounded.{RESET}")
                print(f"  {DIM}Type  governor off  to return to personal mode.{RESET}")
            print()
            _print_header(cfg)
            continue

        elif cmd == "status":
            print(_status_str(cfg))
            continue

        elif cmd == "codex" or cmd.startswith("codex "):
            if not _CODEX_CLI_OK or not _codex_avail_cli():
                print(f"  {RED}Codex Agent not available.{RESET}  "
                      f"{DIM}Set CURSIV_CODEX_PATH env var or place Winkler_Codex_AI "
                      f"as a sibling to Cursiv-v3.{RESET}")
            else:
                prompt = raw[6:].strip() if len(raw) > 6 else ""
                if not prompt:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}codex <what to build>{RESET}")
                else:
                    print(f"  {LGOLD}[Codex Agent — deliberating…]{RESET}")
                    result = _codex_gen_cli(prompt)
                    _print_ai_msg(result)
                    _session_append_cli(prompt, result, "codex_agent")
            continue

        elif cmd == "hermes" or cmd.startswith("hermes "):
            if not _HERMES_CLI_OK or not _hermes_avail_cli():
                print(f"  {RED}Hermes Agent not available.{RESET}  "
                      f"{DIM}Place hermes-agent as a sibling to Cursiv-v3 and ensure Ollama is running.{RESET}")
            else:
                prompt = raw[7:].strip() if len(raw) > 7 else ""
                if not prompt:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}hermes <task to run>{RESET}")
                else:
                    print(f"  {LGOLD}[Hermes Agent — running on llama3.1…]{RESET}")
                    result = _hermes_run_cli(prompt)
                    _print_ai_msg(result)
                    _session_append_cli(prompt, result, "hermes_agent")
            continue

        elif (cmd == "council" or cmd.startswith("council ")
              or cmd == "/deliberate" or cmd.startswith("/deliberate ")
              or cmd == "/full" or cmd.startswith("/full ")):
            _force_full_council = cmd.startswith("/deliberate") or cmd.startswith("/full")
            if cmd.startswith("council "):
                _raw_question = raw[8:].strip()
            elif cmd.startswith("/deliberate "):
                _raw_question = raw[12:].strip()
            elif cmd.startswith("/full "):
                _raw_question = raw[6:].strip()
            else:
                _raw_question = ""
            if not _raw_question:
                print(
                    f"  {LGOLD}Usage:{RESET}  {DIM}council <question>{RESET}\n"
                    f"  {DIM}Full deliberation:{RESET}  {DIM}/full <question>  or  /deliberate <question>{RESET}\n"
                    f"  {DIM}Phrase triggers:{RESET}  {DIM}\"show your reasoning\", \"full deliberation\", \"walk me through\", …{RESET}"
                )
            elif _ASYNC_COUNCIL_OK:
                # ── Option C — async parallel council with streaming ──────
                result = _async_council_run(
                    _raw_question, cfg,
                    force_full=True if _force_full_council else None,
                )
                if result is not None:
                    _last_council_synthesis = result.synthesis   # stored for blast
                    cfg["_last_council_synthesis"] = result.synthesis
                    cfg["_last_council_query"]     = _raw_question
                    _session_append_cli(result.query, result.synthesis, "async_council")
                    if _STRAND_OK and result.synthesis and len(result.synthesis) > 100:
                        _strand_save(
                            result.query,
                            result.synthesis,
                            tags=["council", "async", result.mode],
                            score=0.80 if result.mode == "full" else 0.75,
                            territory_tag="worldmodel",
                            source="async_council",
                            model="council_synthesis",
                        )
                        print(f"  {DIM}⬡ anchored to worldmodel strands{RESET}")
            else:
                # ── Fallback — sequential group discovery ─────────────────
                has_any = cfg.get("api_key") or cfg.get("openai_key") or cfg.get("anthropic_key")
                if not has_any:
                    print(f"  {RED}Council requires at least one API key.{RESET}")
                else:
                    print(
                        f"\n  {GOLD}⬡ GROUP DISCOVERY{RESET}  "
                        f"{SILV2}· {_raw_question[:60]}{'…' if len(_raw_question)>60 else ''}{RESET}"
                    )
                    full = ""
                    try:
                        for chunk in _call_provider_council(
                            _raw_question,
                            cfg.get("api_key", ""),
                            cfg.get("openai_key", ""),
                            cfg.get("anthropic_key", ""),
                        ):
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                            full += chunk
                    except KeyboardInterrupt:
                        print(f"\n  {DIM}[interrupted]{RESET}")
                    print()
                    cfg["_last_council_synthesis"] = _extract_blast_synthesis(full)
                    _session_append_cli(_raw_question, full, "group_discovery")
                    if _STRAND_OK and full and len(full) > 200:
                        _strand_save(
                            _raw_question, full,
                            tags=["council", "group_discovery"],
                            score=0.75,
                            territory_tag="worldmodel",
                            source="council",
                            model="group_discovery",
                        )
            continue

        # ── FunForge ──────────────────────────────────────────────────────
        elif cmd in ("forge done", "forge close"):
            ff: FunForgeSession | None = cfg.get("funforge_session")
            if not ff or ff.closed:
                print(f"  {DIM}No active FunForge session.{RESET}")
            else:
                print(f"\n  {GOLD}⬡ FUNFORGE CLOSING{RESET}  {SILV2}· producing artifact…{RESET}\n")
                full = ""
                for chunk in chat(
                    FUNFORGE_CLOSE_PROMPT, history,
                    cfg["api_key"], None, False, cfg["workspace"],
                    cfg["openai_key"], False, cfg["anthropic_key"],
                ):
                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    full += chunk
                print()
                ff.closed = True
                cfg["funforge_session"] = None
                _session_append_cli(FUNFORGE_CLOSE_PROMPT, full, "funforge_close")
            continue

        elif cmd == "forge extend":
            ff = cfg.get("funforge_session")
            if not ff or ff.closed:
                print(f"  {DIM}No active FunForge session.{RESET}")
            elif not ff.extend():
                print(f"  {GOLD}Already extended once — hold the line.{RESET}")
            else:
                print(f"  {GOLD}Extended +30 min. New total: {int(ff.duration_s//60)} min.{RESET}")
            continue

        elif cmd == "anchor this" or cmd.startswith("anchor this "):
            # Parse optional territory tag:  anchor this coding
            parts    = cmd.split()
            territory = parts[2] if len(parts) >= 3 else "general"
            if _STRAND_OK and territory != "general":
                known = _strand_territories()
                if territory not in known:
                    known_str = "  ".join(known.keys()) if known else "general"
                    print(f"  {DIM}Unknown territory '{territory}'.  Known: {known_str}{RESET}")
                    territory = "general"

            # Always mark FunForge if active
            ff = cfg.get("funforge_session")
            if ff:
                ff.anchored = True

            # Save as Strand — works with or without an active FunForge session
            if _STRAND_OK and history:
                last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
                last_ai   = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
                if last_user or last_ai:
                    sid = _strand_save(
                        last_user, last_ai,
                        tags=["anchor", "funforge"] if ff else ["anchor"],
                        score=0.85,
                        territory_tag=territory,
                        source="anchor",
                        model="cli",
                    )
                    terr_label = f"  [{territory}]" if territory != "general" else ""
                    print(f"  {GOLD}⬡ Anchored → Strand {sid}{terr_label}{RESET}")
                else:
                    print(f"  {DIM}Nothing to anchor yet — send a message first.{RESET}")
            elif ff:
                print(f"  {GOLD}Anchored. This spike will be kept.{RESET}")
            else:
                print(f"  {DIM}No session history to anchor.{RESET}")
            continue

        # ── Postal — sealed encrypted letters ───────────────────────────────
        elif cmd.startswith("write to ") or cmd == "write to":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _postal_user = cfg.get("postal_user", "joshua")
            _recipient_raw = raw[9:].strip() if cmd.startswith("write to ") else ""
            _hint          = ""
            if " hint " in _recipient_raw:
                _recipient_raw, _hint = _recipient_raw.split(" hint ", 1)
            _recipient_raw = _recipient_raw.strip()
            if not _recipient_raw:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}write to <name>  [hint <public hint>]{RESET}")
                continue
            # Resolve from contacts — falls back to raw string as key
            _resolved       = _postal_resolve(_recipient_raw)
            _recipient_key  = _resolved[1] if _resolved else _recipient_raw.lower().replace(" ", "")
            _recipient_disp = _resolved[0] if _resolved else _recipient_raw.title()
            _sig_note       = f"{DIM}· signed{RESET}" if _postal_my_id() else f"{DIM}· unsigned{RESET}"
            # Composition mode
            print(f"\n  {GOLD}╔{'═'*58}╗{RESET}")
            print(f"  {GOLD}║{RESET}  {BOLD}⬡ SEALED LETTER{RESET}  "
                  f"{DIM}to: {_recipient_disp}  ·  machine-bound  {_sig_note}{RESET}  {GOLD}║{RESET}")
            print(f"  {GOLD}║{RESET}  {DIM}/seal to encrypt  ·  /discard to cancel{RESET}  {GOLD}║{RESET}")
            print(f"  {GOLD}╚{'═'*58}╝{RESET}\n")
            _lines: list[str] = []
            try:
                while True:
                    _line = input(f"  {DIM}·{RESET} ")
                    if _line.strip() == "/seal":
                        break
                    if _line.strip() == "/discard":
                        _lines = []
                        print(f"  {DIM}[discarded]{RESET}")
                        break
                    _lines.append(_line)
            except KeyboardInterrupt:
                _lines = []
                print(f"\n  {DIM}[discarded]{RESET}")
            if _lines:
                _content = "\n".join(_lines)
                _my_id_meta  = _postal_my_id()
                # sender_key = stable display name (PBKDF2 anchor, never changes on rotation)
                # Ed25519 signing uses the private key independently
                _sender_key  = _my_id_meta.get("name", _postal_user).lower() if _my_id_meta else _postal_user
                _sender_disp = _my_id_meta.get("name", _postal_user).title() if _my_id_meta else _postal_user.title()
                # Sealing progress display
                _steps = {
                    "anchor":  f"  {DIM}layer 1 · machine anchor    · 50,000 iter{RESET}",
                    "stream":  f"  {DIM}layer 2 · identity binding  · 100,000 iter{RESET}",
                    "xor":     f"  {DIM}layer 3 · stream derivation · 200,000 iter{RESET}",
                    "hmac":    f"  {DIM}XOR stream cipher · keystream derived{RESET}",
                    "sign":    f"  {DIM}Ed25519 · identity signature{RESET}",
                    "encode":  f"  {DIM}HMAC-SHA256 · authentication tag{RESET}",
                    "index":   f"  {DIM}Cursiv alphabet · alien transcription · ZWC sig{RESET}",
                }
                print(f"  {GOLD}⬡ SEALING {'·'*44}{RESET}")
                def _pcb(step: str) -> None:
                    label = _steps.get(step, f"  {DIM}{step}{RESET}")
                    print(f"{label}  {GREEN}✓{RESET}")
                _lid = _postal_seal(
                    sender_key=_sender_key,
                    sender_display=_sender_disp,
                    recipient_key=_recipient_key,
                    recipient_display=_recipient_disp,
                    content=_content,
                    hint=_hint,
                    progress_cb=_pcb,
                )
                print(f"  {GOLD}⬡ SEALED {'·'*45}{RESET}")
                print(f"  {DIM}id:       {RESET}{LGOLD}{_lid}{RESET}")
                print(f"  {DIM}for:      {RESET}{_recipient_disp}")
                print(f"  {DIM}signed:   {RESET}{'yes — Ed25519' if _my_id_meta else 'no — run postal setup first'}")
                print(f"  {DIM}readable: on this machine only{RESET}\n")
            continue

        elif cmd == "letters" or cmd in ("letters for me", "letters from me"):
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _postal_user = cfg.get("postal_user", "joshua")
            print()
            if cmd == "letters for me":
                _llist = _postal_for(_postal_user)
                print(f"  {GOLD}⬡ LETTERS FOR {_postal_user.upper()}{RESET}")
            elif cmd == "letters from me":
                _llist = _postal_from(_postal_user)
                print(f"  {GOLD}⬡ LETTERS FROM {_postal_user.upper()}{RESET}")
            else:
                _llist = _postal_all()
                print(f"  {GOLD}⬡ ALL SEALED LETTERS{RESET}")
            if not _llist:
                print(f"  {DIM}No sealed letters found.{RESET}")
            else:
                for _e in _llist:
                    _read_badge = f"{GREEN}read{RESET}" if _e.get("read") else f"{GOLD}unread{RESET}"
                    _hint_str   = f"  {DIM}{_e['hint']}{RESET}" if _e.get("hint") else ""
                    print(
                        f"  {LGOLD}{_e['id']}{RESET}  "
                        f"{DIM}{_e.get('from_display','?')}{RESET} → "
                        f"{_e.get('for_display','?')}  "
                        f"{DIM}{_e.get('sealed','')[:10]}{RESET}  "
                        f"{_read_badge}{_hint_str}"
                    )
            print()
            continue

        elif cmd.startswith("open letter ") or cmd.startswith("letter "):
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _lid = (raw[12:] if cmd.startswith("open letter ") else raw[7:]).strip()
            if not _lid:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}open letter <id>{RESET}")
                continue
            _entry = _postal_entry(_lid)
            if not _entry:
                print(f"  {RED}Letter {_lid} not found.{RESET}")
                continue
            print(f"\n  {DIM}⬡ opening seal · deriving keys…{RESET}")
            _text = _postal_open(_lid)
            if _text is None:
                print(f"  {RED}⬡ Decryption failed.{RESET}  {DIM}This seal cannot be opened on this machine.{RESET}")
                continue
            _sig_st = _postal_sig_status(_lid)
            _sig_badge = {
                "verified":              f"{GREEN}✓ VERIFIED{RESET}",
                "verified_rotated":      f"{GREEN}✓ VERIFIED{RESET}  {DIM}(signed with sender's prior key){RESET}",
                "verified_compromised":  f"{GOLD}⟳ COHERENCE DEGRADED{RESET}  {DIM}(signed with a compromised key — content shifted){RESET}",
                "unverified":            f"{GOLD}~ unverified  (sender not in contacts){RESET}",
                "unsigned":              f"{DIM}unsigned  (pre-identity letter){RESET}",
                "INVALID":               f"{RED}✗ SIGNATURE INVALID — identity cannot be confirmed{RESET}",
            }.get(_sig_st, f"{DIM}{_sig_st}{RESET}")
            print(f"\n  {GOLD}╔{'═'*62}╗{RESET}")
            print(f"  {GOLD}║{RESET}  {DIM}from:{RESET} {_entry.get('from_display','?')}  "
                  f"{DIM}to:{RESET} {_entry.get('for_display','?')}  "
                  f"{DIM}{_entry.get('sealed','')[:10]}{RESET}  {GOLD}║{RESET}")
            print(f"  {GOLD}║{RESET}  {_sig_badge}  {GOLD}║{RESET}")
            if _entry.get("hint"):
                print(f"  {GOLD}║{RESET}  {DIM}hint: {_entry['hint']}{RESET}  {GOLD}║{RESET}")
            print(f"  {GOLD}╚{'═'*62}╝{RESET}\n")
            for _para in _text.split("\n"):
                print(f"  {_para}")
            print()
            continue

        elif cmd.startswith("council letter "):
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _lid = raw[15:].strip()
            _postal_user = cfg.get("postal_user", "joshua")
            if not _lid:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}council letter <id>{RESET}")
                continue
            print(f"\n  {GOLD}⬡ COUNCIL LETTER READING{RESET}  {DIM}running via Ollama · local only{RESET}\n")
            def _council_pcb(step: str) -> None:
                msgs = {
                    "decrypting":  f"  {DIM}⬡ decrypting seal…{RESET}",
                    "deliberating": f"  {DIM}⬡ 14 agents deliberating…{RESET}",
                }
                print(msgs.get(step, f"  {DIM}{step}…{RESET}"))
            _reading = _postal_council(_lid, _postal_user, cfg, show_progress_cb=_council_pcb)
            print(_reading)
            continue

        elif cmd.startswith("seal export "):
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _lid = raw[12:].strip()
            print(f"\n  {DIM}⬡ generating sealpack · decrypting · re-encrypting with passphrase…{RESET}")
            _result = _postal_export(_lid)
            if _result is None:
                print(f"  {RED}Export failed — letter not found or cannot decrypt.{RESET}")
                continue
            _pack_path, _passphrase = _result
            print(f"\n  {GOLD}⬡ SEALPACK EXPORTED{RESET}")
            print(f"  {DIM}file:       {RESET}{_pack_path}")
            print(f"  {GOLD}passphrase: {RESET}{BOLD}{_passphrase}{RESET}")
            print(f"\n  {DIM}Share this passphrase with the recipient out-of-band.")
            print(f"  It is shown once and never stored.{RESET}\n")
            continue

        elif cmd.startswith("seal import "):
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _pack_file = raw[12:].strip()
            if not _pack_file:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}seal import <filepath>{RESET}")
                continue
            try:
                _passphrase_input = input(f"  {DIM}Passphrase: {RESET}")
            except KeyboardInterrupt:
                print(f"\n  {DIM}[cancelled]{RESET}")
                continue
            print(f"  {DIM}⬡ verifying · decrypting · re-sealing locally…{RESET}")
            _new_id = _postal_import(_pack_file, _passphrase_input)
            if _new_id is None:
                print(f"  {RED}Import failed — wrong passphrase or corrupted pack.{RESET}")
            else:
                print(f"  {GOLD}⬡ Sealed locally as:{RESET}  {LGOLD}{_new_id}{RESET}")
            continue

        elif cmd == "postal user" or cmd.startswith("postal user "):
            _new_user = raw[12:].strip().lower() if cmd.startswith("postal user ") else ""
            if not _new_user:
                print(f"  {DIM}Current postal identity: {cfg.get('postal_user', 'joshua')}{RESET}")
            else:
                cfg["postal_user"] = _new_user
                print(f"  {GOLD}⬡ Postal identity set to:{RESET}  {_new_user}")
            continue

        elif cmd.startswith("postal setup ") or cmd == "postal setup":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _setup_name = raw[13:].strip() if cmd.startswith("postal setup ") else ""
            if not _setup_name:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}postal setup <your name>{RESET}")
                continue
            print(f"\n  {DIM}⬡ generating Ed25519 identity keypair…{RESET}")
            try:
                _id_meta = _postal_setup(_setup_name)
                cfg["postal_user"] = _id_meta.get("name", _setup_name).lower()
                print(f"\n  {GOLD}╔{'═'*62}╗{RESET}")
                print(f"  {GOLD}║{RESET}  {BOLD}⬡ IDENTITY CREATED{RESET}  {GOLD}║{RESET}")
                print(f"  {GOLD}╚{'═'*62}╝{RESET}")
                print(f"  {DIM}Name:    {RESET}{_id_meta.get('name', _setup_name)}")
                print(f"  {DIM}Key ID:  {RESET}{_id_meta.get('key_id', '?')[:8]}")
                print(f"  {GOLD}Public:  {RESET}{BOLD}{_id_meta.get('pubkey','?')}{RESET}")
                print(f"\n  {DIM}Share this public key with anyone you want to receive letters from.")
                print(f"  They add you with:  postal add user {_setup_name} <your key>{RESET}\n")
            except Exception as _e:
                print(f"  {RED}Setup failed: {_e}{RESET}")
            continue

        elif cmd == "postal my key":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _my_id = _postal_my_id()
            if not _my_id:
                print(f"  {DIM}No identity set up yet. Run:{RESET}  {LGOLD}postal setup <your name>{RESET}")
            else:
                print(f"\n  {GOLD}⬡ YOUR CURSIV IDENTITY{RESET}")
                print(f"  {DIM}Name:    {RESET}{_my_id.get('name', '?')}")
                print(f"  {DIM}Key ID:  {RESET}{_my_id.get('key_id','?')[:8]}")
                print(f"  {GOLD}Public:  {RESET}{BOLD}{_my_id.get('pubkey','?')}{RESET}\n")
            continue

        elif cmd.startswith("postal add user ") or cmd == "postal add user":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _au_parts = raw[16:].strip().split() if cmd.startswith("postal add user ") else []
            if len(_au_parts) < 2:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}postal add user <name> <pubkey>{RESET}")
                continue
            _au_name   = _au_parts[0]
            _au_pubkey = _au_parts[1]
            try:
                _au_entry = _postal_add_contact(_au_name, _au_pubkey)
                print(f"  {GOLD}⬡ Contact added:{RESET}  "
                      f"{_au_name}  {DIM}key-id: {_au_entry.get('key_id','?')[:8]}{RESET}")
            except ValueError as _e:
                print(f"  {RED}Invalid public key: {_e}{RESET}")
            continue

        elif cmd.startswith("postal remove user "):
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _rm_name = raw[19:].strip()
            if _postal_rm_contact(_rm_name):
                print(f"  {DIM}Contact removed: {_rm_name}{RESET}")
            else:
                print(f"  {DIM}Contact not found: {_rm_name}{RESET}")
            continue

        elif cmd.startswith("postal rotate") or cmd == "postal rotate key":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _is_compromised = "compromised" in cmd or "leaked" in cmd
            _rotate_reason  = "key compromised — attacker may have private key" if _is_compromised else "manual rotation"
            print(f"\n  {GOLD}⬡ KEY ROTATION{RESET}  "
                  f"{'  ' + RED + 'COMPROMISED' + RESET if _is_compromised else DIM + 'manual' + RESET}")
            if _is_compromised:
                print(f"  {GOLD}Coherence degradation will activate on retired key.{RESET}")
                print(f"  {DIM}Any letter later read through the old key returns shifted content.")
                print(f"  The attacker sees output. They do not see truth.{RESET}\n")
            try:
                _rot = _postal_rotate(reason=_rotate_reason, compromised=_is_compromised)
                if not _rot:
                    print(f"  {RED}Rotation failed — no identity set up. Run: postal setup <name>{RESET}")
                    continue
                print(f"  {DIM}Old key ID:  {RESET}{_rot.get('old_key_id','?')[:8]}  {DIM}(archived locally){RESET}")
                print(f"  {GOLD}New key ID:  {RESET}{_rot.get('new_key_id','?')[:8]}")
                print(f"  {GOLD}New public:  {RESET}{BOLD}{_rot.get('new_pubkey','?')}{RESET}")
                print(f"\n  {DIM}Update your contacts with your new key.")
                print(f"  They run:  postal add user <your name> <new key>{RESET}\n")
            except Exception as _e:
                print(f"  {RED}Rotation failed: {_e}{RESET}")
            continue

        elif cmd == "postal key history":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _hist = _postal_key_history()
            print(f"\n  {GOLD}⬡ KEY HISTORY  ({len(_hist)} retired){RESET}")
            if not _hist:
                print(f"  {DIM}No retired keys.{RESET}")
            else:
                for _hk in _hist:
                    _comp_flag = f"  {RED}COMPROMISED — coherence degradation active{RESET}" if _hk.get("compromised") else ""
                    print(f"  {DIM}{_hk.get('key_id','?')[:8]}{RESET}  "
                          f"{DIM}retired:{_hk.get('retired_at','?')[:10]}  "
                          f"{_hk.get('reason','?')[:40]}{RESET}{_comp_flag}")
            print()
            continue

        elif cmd == "postal contacts":
            if not _POSTAL_OK:
                print(f"  {RED}Postal module unavailable.{RESET}")
                continue
            _clist = _postal_contacts()
            print()
            print(f"  {GOLD}⬡ CONTACTS  ({len(_clist)}){RESET}")
            if not _clist:
                print(f"  {DIM}No contacts yet.  Use:  postal add user <name> <pubkey>{RESET}")
            else:
                for _c in _clist:
                    print(f"  {LGOLD}{_c['name']:<16}{RESET}  "
                          f"{DIM}id:{_c.get('key_id','?')[:8]}  "
                          f"added:{_c.get('added','?')[:10]}{RESET}")
            print()
            continue

        # ── Substrate Fork — RUW / Curs. ─────────────────────────────────────
        elif cmd == "substrate" or cmd.startswith("substrate "):
            sub = cmd[10:].strip() if cmd.startswith("substrate ") else ""
            if not _SUBSTRATE_OK:
                print(f"\n  {RED}Substrate module unavailable.{RESET}\n")
                continue

            _act = _get_activator()

            if sub == "status":
                st = _act.status()
                ly = st["layer"]
                print(f"\n  {GOLD}⬡ SUBSTRATE — RUW LAYER{RESET}")
                print(f"  {DIM}Nodes:       {ly['nodes']}{RESET}")
                print(f"  {DIM}Edges:       {ly['edges']}{RESET}")
                print(f"  {DIM}Activations: {st['activations']}{RESET}")
                print(f"  {DIM}Address:     {ly['address']}{RESET}")
                print(f"  {DIM}Threshold:   {ly['threshold']}{RESET}\n")

            elif sub.startswith("weave "):
                _wq = sub[6:].strip()
                if not _wq:
                    print(f"  {DIM}Usage: substrate weave <query>{RESET}\n")
                else:
                    hits = _act.weave(_wq, top_k=5)
                    print(f"\n  {GOLD}⬡ SUBSTRATE WEAVE — resonant nodes{RESET}")
                    if not hits:
                        print(f"  {DIM}No nodes in layer yet. Run a council deliberation first.{RESET}")
                    for nid, score in hits:
                        bar = "█" * int(score * 12)
                        print(f"  {DIM}{bar:<12}{RESET}  {score:.3f}  {LGOLD}{nid}{RESET}")
                    print()

            elif sub == "activate" or not sub:
                _synth = cfg.get("_last_council_synthesis", "")
                _query = cfg.get("_last_council_query", "")
                if not _synth:
                    print(f"\n  {GOLD}⬡ No council synthesis yet.{RESET}")
                    print(f"  {DIM}Run a council deliberation first.{RESET}\n")
                    continue
                result = _act.activate(_synth, query=_query, session_id=_CLI_SESSION_ID)
                print(f"\n  {GOLD}⬡ SUBSTRATE ACTIVATED{RESET}")
                print(f"  {DIM}RUW Address:  {RESET}{LGOLD}{result['ruw_address']}{RESET}")
                print(f"  {DIM}Resonance:    {RESET}{result['resonance']:.4f}")
                print(f"  {DIM}Attractor E:  {RESET}{result['attractor_energy']:.4f}")
                print(f"  {DIM}Layer nodes:  {RESET}{result['layer_state']['nodes']}")
                if result["related"]:
                    print(f"  {DIM}Related:{RESET}")
                    for nid, score in result["related"][:3]:
                        print(f"    {DIM}{score:.3f}  {nid}{RESET}")
                print()
                # Store RUW address for reference
                cfg["_last_ruw_address"] = result["ruw_address"]

            else:
                print(f"\n  {LGOLD}substrate{RESET}             activate last council synthesis")
                print(f"  {LGOLD}substrate activate{RESET}    same")
                print(f"  {LGOLD}substrate status{RESET}      show RUW layer state")
                print(f"  {LGOLD}substrate weave <q>{RESET}   find resonant nodes for a query\n")
            continue

        # ── Blast — post council synthesis to public board ────────────────────
        elif cmd == "blast" or cmd.startswith("blast "):
            sub = cmd[6:].strip() if cmd.startswith("blast ") else ""

            if sub.startswith("login"):
                parts = sub.split()
                if len(parts) < 2:
                    print(f"\n  {LGOLD}Usage:{RESET}  {DIM}blast login <username>{RESET}\n")
                else:
                    _bu = parts[1]
                    import getpass as _gp
                    _bp = _gp.getpass(f"  Board password for {_bu}: ")
                    _ok, _msg = _board_login(_bu, _bp)
                    if _ok:
                        print(f"\n  {GOLD}✓ Logged in as {_msg}{RESET}\n")
                    else:
                        print(f"\n  {RED}✗ {_msg}{RESET}\n")

            elif sub.startswith("register"):
                parts = sub.split()
                if len(parts) < 2:
                    print(f"\n  {LGOLD}Usage:{RESET}  {DIM}blast register <username>{RESET}\n")
                else:
                    _bu = parts[1]
                    import getpass as _gp
                    _bp  = _gp.getpass(f"  Choose password for {_bu} (min 8 chars): ")
                    _bp2 = _gp.getpass("  Confirm password: ")
                    if _bp != _bp2:
                        print(f"\n  {RED}✗ Passwords do not match.{RESET}\n")
                    else:
                        _ok, _msg = _board_register(_bu, _bp)
                        if _ok:
                            print(f"\n  {GOLD}✓ Account created.  Logged in as {_msg}{RESET}\n")
                        else:
                            print(f"\n  {RED}✗ {_msg}{RESET}\n")

            elif sub == "logout":
                _board_logout()
                print(f"\n  {DIM}Board session cleared.{RESET}\n")

            elif sub == "who":
                _bwho = _board_whoami()
                if _bwho:
                    print(f"\n  {GOLD}⬡ Board:{RESET}  logged in as {LGOLD}{_bwho}{RESET}\n")
                else:
                    print(f"\n  {DIM}Not logged in.  Use:  blast login <username>{RESET}\n")

            else:
                # bare `blast` — post last council synthesis
                if not _BOARD_OK:
                    print(f"\n  {RED}Board client unavailable.{RESET}\n")
                    continue
                _bwho = _board_whoami()
                if not _bwho:
                    print(f"\n  {RED}Not logged in to the board.{RESET}  Use:  {DIM}blast login <username>{RESET}\n")
                    continue
                _synth = cfg.get("_last_council_synthesis", "")
                if not _synth:
                    print(f"\n  {GOLD}⬡ No council synthesis in this session yet.{RESET}")
                    print(f"  {DIM}Run a council deliberation first, then blast.{RESET}\n")
                    continue
                print()
                print(f"  {GOLD}⬡ COUNCIL SYNTHESIS — READY TO BLAST{RESET}")
                print(f"  {DIM}{'─'*54}{RESET}")
                _preview = _synth[:400] + ("…" if len(_synth) > 400 else "")
                for _line in _preview.splitlines():
                    print(f"  {_line}")
                print(f"  {DIM}{'─'*54}{RESET}")
                print(f"  Board user: {LGOLD}{_bwho}{RESET}  |  Source: {GOLD}council{RESET}")
                print()
                _confirm = input(f"  Blast this to the public board? [{GOLD}yes{RESET}/{DIM}no{RESET}]: ").strip().lower()
                if _confirm not in ("yes", "y"):
                    print(f"  {DIM}Cancelled.{RESET}\n")
                    continue
                _ok, _msg = _board_blast(_synth, source="council")
                if _ok:
                    print(f"\n  {GOLD}✓ Blasted.{RESET}  Post ID: {DIM}{_msg}{RESET}\n")
                else:
                    print(f"\n  {RED}✗ {_msg}{RESET}")
                    if "user not found" in _msg.lower() or "invalid or expired" in _msg.lower():
                        print(f"  {DIM}Your saved token is stale — the server was redeployed.{RESET}")
                        print(f"  {DIM}Fix:  blast register <username>  (creates a fresh account + logs you in){RESET}\n")
                    else:
                        print()
            continue

        elif cmd == "strands" or cmd.startswith("strands "):
            if not _STRAND_OK:
                print(f"  {RED}Strand store unavailable.{RESET}")
                continue
            sub = cmd[8:].strip() if cmd.startswith("strands ") else ""
            print()
            if sub.startswith("search "):
                q = sub[7:].strip()
                if not q:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}strands search <query>{RESET}")
                else:
                    results = _strand_search(q)
                    print(f"  {GOLD}⬡ Strand Search —{RESET} {DIM}{q}{RESET}")
                    print(_strand_fmt(results))
            elif sub and sub in _strand_territories():
                results = _strand_list(territory=sub, limit=20)
                print(f"  {GOLD}⬡ Strands [{sub}]{RESET}  {DIM}({len(results)} found){RESET}")
                print(_strand_fmt(results))
            else:
                total  = _strand_count()
                counts = _strand_terr_counts()
                recent = _strand_list(limit=8)
                counts_line = "  ".join(f"{t}:{n}" for t, n in counts.items()) if counts else "none yet"
                print(f"  {GOLD}⬡ Strand Archive{RESET}  {DIM}{total} total{RESET}")
                print(f"  {SILV2}{counts_line}{RESET}")
                if recent:
                    print()
                    print(_strand_fmt(recent))
                if total > 8:
                    print(f"\n  {DIM}… and {total - 8} more.  strands <territory>  ·  strands search <query>{RESET}")
            print()
            continue

        # ── Strand export / import ────────────────────────────────────────
        elif cmd.startswith("strand export") or cmd == "strand export":
            if not (_STRAND_OK and _SFED_OK):
                print(f"  {RED}Strand federation unavailable.{RESET}")
                continue
            parts     = cmd.split()
            territory = parts[2] if len(parts) >= 3 else None
            all_s     = _strand_list(territory=territory, limit=5000)
            if not all_s:
                t_label = f" in '{territory}'" if territory else ""
                print(f"  {DIM}No strands{t_label} to export.{RESET}")
                continue
            terr_defs = _strand_territories()
            label     = f"cursiv-{territory or 'all'}"
            pack_text = _sfed_export(all_s, terr_defs, label=label)
            out_name  = ROOT / f"{label}-{int(datetime.now().timestamp())}{_PACK_EXT}"
            try:
                out_name.write_text(pack_text, encoding="utf-8")
                print(f"\n  {GOLD}⬡ Strand Pack Exported{RESET}")
                print(f"  {LGOLD}File    :{RESET}  {out_name.name}")
                print(f"  {LGOLD}Strands :{RESET}  {len(all_s)}")
                t_label = territory or "all territories"
                print(f"  {LGOLD}Scope   :{RESET}  {t_label}")
                print(f"  {DIM}Transfer via USB / LAN. Import with:  strand import <filename>{RESET}\n")
            except Exception as _e:
                print(f"  {RED}Export failed: {_e}{RESET}")
            continue

        elif cmd.startswith("strand import "):
            if not (_STRAND_OK and _SFED_OK):
                print(f"  {RED}Strand federation unavailable.{RESET}")
                continue
            pack_path = Path(cmd[14:].strip())
            if not pack_path.exists():
                print(f"  {RED}File not found: {pack_path}{RESET}")
                continue
            try:
                pack_text = pack_path.read_text(encoding="utf-8")
                in_strands, _in_terr, meta = _sfed_import(pack_text)
            except ValueError as _ve:
                print(f"  {RED}Pack verification failed: {_ve}{RESET}")
                continue
            print(f"\n  {GOLD}⬡ STRAND PACK IMPORT — REVIEW{RESET}")
            print(_sfed_summary(in_strands, meta))
            if not meta.get("same_machine"):
                print(f"\n  {RED}⚠  Cross-machine pack. Signature does not match this instance.{RESET}")
                print(f"  {DIM}This is expected for packs transferred between different machines.{RESET}")
            try:
                answer = input(f"\n  {GOLD}Import {len(in_strands)} strands?{RESET}  {DIM}[y/N]{RESET}  ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer != "y":
                print(f"  {DIM}Import cancelled.{RESET}\n")
                continue
            imported = 0
            for _s in in_strands:
                try:
                    _strand_save(
                        _s.get("query", ""),
                        _s.get("synthesis", ""),
                        tags=(_s.get("tags") or []) + ["federated_import"],
                        score=_s.get("score", 0.70),
                        territory_tag=_s.get("territory_tag", "general"),
                        source="federation",
                        model=_s.get("model", "unknown"),
                        provenance={"source_models": [_s.get("model", "?")],
                                    "federated": True, "pack_label": meta.get("label", "?")},
                    )
                    imported += 1
                except Exception:
                    pass
            print(f"  {GREEN}Imported {imported}/{len(in_strands)} strands.{RESET}\n")
            continue

        # ── remember — pure local memory retrieval (zero cloud) ───────────
        elif cmd.startswith("remember ") or cmd == "remember":
            if not _STRAND_OK:
                print(f"  {RED}Strand store unavailable.{RESET}")
                continue
            q = cmd[9:].strip() if cmd.startswith("remember ") else ""
            if not q:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}remember <query>{RESET}")
                continue
            print(f"\n  {GOLD}⬡ Local Memory — {RESET}{DIM}{q}{RESET}")
            print(f"  {SILV2}Zero cloud. Zero API. Searching personal Strand archive only.{RESET}\n")
            results = _strand_search(q, top_k=5, min_score=0.08)
            if not results:
                print(f"  {DIM}No matching strands found. Anchor exchanges with:  anchor this{RESET}\n")
            else:
                print(_strand_fmt(results))
                print()
            continue

        # ── pull <url> — fetch, analyze, strand ───────────────────────────
        elif cmd.startswith("pull "):
            url = cmd[5:].strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            print(f"\n  {GOLD}⬡ Page Pull —{RESET} {DIM}{url[:70]}{RESET}")
            try:
                import urllib.request as _pur
                import urllib.error as _uerr
                import re as _pre
                req = _pur.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Cursiv/3.14)",
                })
                with _pur.urlopen(req, timeout=12) as _resp:
                    raw_bytes = _resp.read(65_536)  # 64 KB max
                charset = "utf-8"
                raw_html = raw_bytes.decode(charset, errors="replace")
                # Strip scripts, styles, tags, entities
                text = _pre.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=_pre.IGNORECASE)
                text = _pre.sub(r"<[^>]+>", " ", text)
                text = _pre.sub(r"&[a-zA-Z]{2,6};", " ", text)
                text = _pre.sub(r"\s+", " ", text).strip()
                text = text[:4000]
                if len(text) < 80:
                    print(f"  {DIM}Page returned too little text — may require JavaScript.{RESET}\n")
                    continue
                print(f"  {DIM}{len(text)} chars extracted — analyzing with local council…{RESET}\n")
            except _uerr.HTTPError as _he:
                if _he.code == 404:
                    print(f"  {RED}404 — page not found. Internet is reachable; URL may have moved or been mistyped.{RESET}\n")
                else:
                    print(f"  {RED}HTTP {_he.code}: {_he.reason}{RESET}\n")
                continue
            except (_uerr.URLError, OSError) as _ue:
                _online = False
                try:
                    import urllib.request as _pc
                    with _pc.urlopen("https://www.google.com", timeout=4) as _chk:
                        _online = _chk.status < 500
                except Exception:
                    pass
                if _online:
                    print(f"  {RED}Fetch failed — internet is up but URL is unreachable: {_ue}{RESET}\n")
                else:
                    print(f"  {RED}No internet connection detected — pull requires network access.{RESET}\n")
                continue
            except Exception as _fe:
                print(f"  {RED}Fetch failed: {_fe}{RESET}\n")
                continue

            pull_msgs = [{
                "role": "user",
                "content": (
                    f"URL: {url}\n\n"
                    f"Content:\n{text}\n\n"
                    f"Analyze this page. Provide:\n"
                    f"1. Core thesis or main insight (1-2 sentences)\n"
                    f"2. Key facts or data points worth remembering\n"
                    f"3. Any connection to current work or prior thinking\n"
                    f"Be precise. No filler."
                ),
            }]
            print(f"  {LGOLD}[Local Council analyzing…]{RESET}\n")
            full_pull = ""
            try:
                for chunk in _call_ollama(pull_msgs):
                    if chunk != RATE_SENTINEL:
                        safe = chunk.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                        sys.stdout.write(safe)
                        sys.stdout.flush()
                        full_pull += chunk
                print()
            except Exception as _pe:
                print(f"  {RED}Analysis failed: {_pe}{RESET}")
                continue
            # Auto-strand the synthesis
            if _STRAND_OK and full_pull:
                _sid = _strand_save(
                    f"pull: {url}",
                    full_pull,
                    tags=["pull", "web"],
                    score=0.72,
                    territory_tag="worldmodel",
                    source="pull",
                    model="ollama",
                    provenance={"source_models": ["ollama"], "web_sources": [url], "human_rated": False},
                )
                print(f"\n  {GOLD}⬡ Stranded → {_sid}  [worldmodel]{RESET}\n")
            _session_append_cli(f"pull {url}", full_pull, "pull")
            continue

        elif cmd.startswith("rate"):
            parts = cmd.split()
            score, quality = None, None
            if len(parts) >= 2:
                tok = parts[1].lower()
                if tok == "good":
                    score, quality = 5, 1.0
                elif tok == "bad":
                    score, quality = 1, 0.2
                elif tok.isdigit() and 1 <= int(tok) <= 5:
                    score = int(tok)
                    quality = round(score / 5.0, 2)
            if score is None:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}rate good  ·  rate bad  ·  rate 1-5{RESET}")
                continue
            last = _session_get_last()
            if not last:
                print(f"  {DIM}No exchange to rate yet — send a message first.{RESET}")
                continue
            entry = {
                "prompt":    last.get("user", "")[:2000],
                "response":  last.get("ai",   "")[:2000],
                "rating":    score,
                "quality":   quality,
                "model":     last.get("model", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "source":    "human_rated",
            }
            try:
                _RATED_JSONL.parent.mkdir(parents=True, exist_ok=True)
                with open(_RATED_JSONL, "a", encoding="utf-8") as _rf:
                    _rf.write(json.dumps(entry) + "\n")
                stars = "★" * score + "☆" * (5 - score)
                print(f"  {GREEN}Rated {stars}  ({score}/5)  —  saved to training queue{RESET}")
            except Exception as _re:
                print(f"  {RED}Rate save failed: {_re}{RESET}")
            continue

        elif _FF_OK and (cmd.startswith("funforge") or cmd.startswith("spike ")):
            topic = _ff_topic(raw)
            ff    = FunForgeSession(topic)
            cfg["funforge_session"] = ff
            print(
                f"\n  {GOLD}╔══════════════════════════════════════════╗{RESET}\n"
                f"  {GOLD}║  ⬡ FUNFORGE ACTIVE  ·  {ff.time_display()} remaining  ║{RESET}\n"
                f"  {GOLD}║  Focus: {topic[:40]:<40}  ║{RESET}\n"
                f"  {GOLD}║  Council: Lens + Spark + Balance          ║{RESET}\n"
                f"  {GOLD}║  Type  forge done  when finished          ║{RESET}\n"
                f"  {GOLD}╚══════════════════════════════════════════╝{RESET}\n"
            )
            spike_msg = f"[FUNFORGE] {ff.system_fragment()}\n\nLet's begin. Respond to the topic playfully and start the creative spike."
            full = ""
            for chunk in chat(
                spike_msg, history,
                cfg["api_key"], None, False, cfg["workspace"],
                cfg["openai_key"], False, cfg["anthropic_key"],
            ):
                sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                sys.stdout.flush()
                full += chunk
            print()
            history.append({"role": "user",      "content": spike_msg})
            history.append({"role": "assistant",  "content": full})
            _session_append_cli(spike_msg, full, "funforge_start")
            continue

        elif cmd == "ref" or cmd.startswith("ref "):
            if not _REF_CLI_OK or not _ref_avail_cli():
                print(f"  {RED}Reference Brain not available.{RESET}  "
                      f"{DIM}Codex system SQLite not found.{RESET}")
            else:
                query = raw[4:].strip() if len(raw) > 4 else ""
                if not query:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}ref <what to look up>{RESET}")
                else:
                    result = _ref_answer_cli(query)
                    _print_ai_msg(result)
            continue

        # ── grow — self-referential code evolution ───────────────────────
        # No training. Context injection only. The model reads its own source,
        # absorbs every pattern, and writes the next logical addition.
        elif cmd == "grow" or cmd.startswith("grow "):
            _grow_sub = cmd[5:].strip() if cmd.startswith("grow ") else ""

            # ── grow system: what capability does the system need next? ──
            if _grow_sub == "system":
                print(f"\n  {GOLD}⬡ Grow — system level{RESET}  "
                      f"{DIM}reading system map…{RESET}\n")
                try:
                    import ast as _gast
                    _gsrc = ROOT
                    _gmap_lines = ["# Cursiv system map\n"]
                    for _gf in sorted(_gsrc.rglob("*.py")):
                        if any(x in str(_gf) for x in
                               ("__pycache__", ".git", "guardian", "weave")):
                            continue
                        try:
                            _gc = _gf.read_text(encoding="utf-8", errors="replace")
                            _grel = str(_gf.relative_to(_gsrc)).replace("\\", "/")
                            _gt = _gast.parse(_gc)
                            _gdoc = (_gast.get_docstring(_gt) or "").split("\n")[0][:80]
                            _gnames = [
                                n.name for n in _gast.iter_child_nodes(_gt)
                                if isinstance(n, (_gast.FunctionDef,
                                                  _gast.AsyncFunctionDef,
                                                  _gast.ClassDef))
                            ]
                            _gmap_lines.append(
                                f"## {_grel}\n"
                                + (f"  {_gdoc}\n" if _gdoc else "")
                                + (f"  exports: {', '.join(_gnames[:12])}\n"
                                   if _gnames else "")
                            )
                        except Exception:
                            pass
                    _gsys_map = "".join(_gmap_lines)
                except Exception as _ge:
                    _gsys_map = f"[map error: {_ge}]"

                _gsys_msgs = [
                    {"role": "system", "content": (
                        "You are a systems architect reviewing the Cursiv AI OS.\n"
                        "Study the system map and identify the single most valuable "
                        "capability that is clearly missing or only half-built.\n"
                        "Describe it in 2-3 sentences, then write a complete Python "
                        "module stub (filename, docstring, key functions with "
                        "signatures and one-line docstrings) for that capability.\n"
                        "No filler. Be specific to THIS system."
                    )},
                    {"role": "user", "content": _gsys_map},
                ]
                _gant = cfg.get("anthropic_key", "")
                _gxai = cfg.get("api_key", "")
                _goai = cfg.get("openai_key", "")
                if _gant:
                    _ggen, _glbl = _call_claude_direct(_gsys_msgs, _gant), "Claude"
                elif _gxai:
                    _ggen, _glbl = _call_xai_stream(_gsys_msgs, _gxai, False), "xAI"
                elif _goai:
                    _ggen, _glbl = _call_openai_direct(_gsys_msgs, _goai), "OpenAI"
                else:
                    _ggen, _glbl = _call_ollama(_gsys_msgs, max_tokens=1200), "Ollama"

                print(f"  {LGOLD}Next capability — via {_glbl}:{RESET}\n")
                _gfull = ""
                for _gchunk in _ggen:
                    if _gchunk == RATE_SENTINEL:
                        continue
                    _gsafe = _gchunk.encode(
                        sys.stdout.encoding or "utf-8", errors="replace"
                    ).decode(sys.stdout.encoding or "utf-8", errors="replace")
                    sys.stdout.write(f"{CREAM}{_gsafe}{RESET}")
                    sys.stdout.flush()
                    _gfull += _gchunk
                print("\n")
                if _STRAND_OK and _gfull:
                    _strand_save(
                        "grow system — next capability",
                        _gfull,
                        tags=["grow", "system", "evolution"],
                        score=0.80,
                        territory_tag="architecture",
                        source="grow",
                        model=_glbl,
                    )
                continue

            # ── grow <file>: what comes next in this specific file? ──────
            if not _grow_sub:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}grow <filepath>  ·  grow system{RESET}")
                print(_GROW)
                continue

            _gpath = Path(_grow_sub)
            if not _gpath.is_absolute():
                _gpath = ROOT / _grow_sub
            if not _gpath.exists():
                # Try relative to workspace too
                _gpath = Path(cfg["workspace"]) / _grow_sub
            if not _gpath.exists():
                print(f"  {RED}File not found: {_grow_sub}{RESET}")
                continue

            try:
                _gcode  = _gpath.read_text(encoding="utf-8", errors="replace")
                _glines = _gcode.count("\n")
                _grel   = _grow_sub
            except Exception as _ge:
                print(f"  {RED}Read error: {_ge}{RESET}")
                continue

            # ── Sentinel: scan file before sending to LLM ─────────────────
            if _SENTINEL_OK and not cfg.get("_family_unlocked", False):
                _gsr = _sentinel_scan_file(_gpath)
                if _gsr.blocked:
                    print(f"\n  {RED}{_sentinel_warn(_gsr, _gpath.name)}{RESET}\n")
                    continue
                elif _gsr.level >= _SENTINEL_WARN:
                    print(f"\n  {GOLD}{_sentinel_warn(_gsr, _gpath.name)}{RESET}\n")

            print(f"\n  {GOLD}⬡ Grow — {_grel}{RESET}  "
                  f"{DIM}{_glines} lines · absorbing patterns…{RESET}\n")

            _gfile_msgs = [
                {"role": "system", "content": _GROW_SYSTEM},
                {"role": "user",   "content": (
                    f"# File: {_grel}\n"
                    f"# {_glines} lines — study the full file then write what comes next.\n\n"
                    + _gcode
                )},
            ]
            _gant = cfg.get("anthropic_key", "")
            _gxai = cfg.get("api_key", "")
            _goai = cfg.get("openai_key", "")
            if _gant:
                _ggen, _glbl = _call_claude_direct(_gfile_msgs, _gant), "Claude"
            elif _gxai:
                _ggen, _glbl = _call_xai_stream(_gfile_msgs, _gxai, False), "xAI"
            elif _goai:
                _ggen, _glbl = _call_openai_direct(_gfile_msgs, _goai), "OpenAI"
            else:
                _ggen, _glbl = _call_ollama(_gfile_msgs, max_tokens=1500), "Ollama"

            print(f"  {LGOLD}Next addition — via {_glbl}:{RESET}\n")
            _gfull = ""
            for _gchunk in _ggen:
                if _gchunk == RATE_SENTINEL:
                    continue
                _gsafe = _gchunk.encode(
                    sys.stdout.encoding or "utf-8", errors="replace"
                ).decode(sys.stdout.encoding or "utf-8", errors="replace")
                sys.stdout.write(f"{CREAM}{_gsafe}{RESET}")
                sys.stdout.flush()
                _gfull += _gchunk
            print("\n")

            # ── Sentinel: scan generated code before offering to write ────
            if _SENTINEL_OK and _gfull.strip() and not cfg.get("_family_unlocked", False):
                _gosr = _sentinel_scan(_gfull, label="generated")
                if _gosr.blocked:
                    print(f"\n  {RED}{_sentinel_warn(_gosr, 'generated output')}{RESET}\n")
                    print(f"  {RED}Generated code blocked — not written.{RESET}\n")
                    if _STRAND_OK:
                        _strand_save(
                            f"grow [BLOCKED]: {_grel}",
                            _gfull,
                            tags=["grow", "blocked", "sentinel"],
                            score=0.10,
                            territory_tag="security",
                            source="grow",
                            model=_glbl,
                        )
                    continue
                elif _gosr.level >= _SENTINEL_WARN:
                    print(f"\n  {GOLD}{_sentinel_warn(_gosr, 'generated output')}{RESET}\n")

            # Offer to append
            if _gfull.strip():
                try:
                    if _HAS_PT:
                        _gans = _pt_prompt(_PT_ANSI(
                            f"  {GOLD}Append to {_gpath.name}?{RESET}  "
                            f"{DIM}[y/N]{RESET}  "
                        )).strip().lower()
                    else:
                        _gans = input(
                            f"  Append to {_gpath.name}? [y/N]  "
                        ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    _gans = "n"

                if _gans == "y":
                    try:
                        with open(_gpath, "a", encoding="utf-8") as _gf:
                            _gf.write(f"\n\n{_gfull.strip()}\n")
                        print(f"  {GREEN}Appended to {_gpath}{RESET}\n")
                    except Exception as _gwe:
                        print(f"  {RED}Write failed: {_gwe}{RESET}\n")
                else:
                    print(f"  {DIM}Not written — copy from above if you want to keep it.{RESET}\n")

                if _STRAND_OK:
                    _strand_save(
                        f"grow: {_grel}",
                        _gfull,
                        tags=["grow", "evolution", "codegen"],
                        score=0.78,
                        territory_tag="coding",
                        source="grow",
                        model=_glbl,
                    )
            continue

        elif cmd == "queue" or cmd.startswith("queue "):
            if not _QUEUE_CLI_OK:
                print(f"  {RED}Offline Queue not available.{RESET}")
            else:
                parts = raw.split(None, 1)
                sub   = parts[1].strip() if len(parts) > 1 else ""
                if not sub or sub == "list":
                    print(_queue_format_cli())
                elif sub.startswith("add "):
                    task = sub[4:].strip()
                    entry = _queue_enqueue_cli(task)
                    print(f"  {LGOLD}Queued:{RESET}  {DIM}{entry.get('id','?')} — {task[:60]}{RESET}")
                else:
                    print(f"  {LGOLD}Usage:{RESET}  {DIM}queue list  |  queue add <task>{RESET}")
            continue

        # ── voice / listen — two-stage pipeline ─────────────────────────
        #
        #   Stage 1  mic → faster-whisper (or Vosk) → raw transcript
        #   Stage 2  raw text → Babel binary encode → LLM → clean English
        #
        # Subcommands:
        #   voice            5s record → STT → Babel clean → inject as message
        #   voice raw        5s record → STT only (skip Babel pass)
        #   voice <N>        N-second record → STT → Babel clean
        #   listen           alias for  voice raw  (backward compat)
        #   council voice    voice + route through Group Discovery
        elif (cmd == "voice" or cmd.startswith("voice ")
              or cmd == "listen" or cmd.startswith("listen ")):

            if not _VOICE_OK:
                print(f"  {RED}Voice agent failed to load.{RESET}")
                continue
            if not _voice_avail():
                print(f"  {RED}No audio capture library.{RESET}  "
                      f"{DIM}pip install faster-whisper sounddevice{RESET}")
                continue

            # Parse subcommand
            _is_listen = cmd.startswith("listen")
            _sub       = ""
            if cmd.startswith("voice "):
                _sub = cmd[6:].strip()
            elif cmd.startswith("listen "):
                _sub = cmd[7:].strip()

            _raw_mode  = _is_listen or _sub == "raw"
            _duration  = 5.0
            try:
                if _sub and _sub != "raw" and _sub.replace(".", "", 1).isdigit():
                    _duration = max(1.0, min(float(_sub), 60.0))
            except Exception:
                pass

            _stt   = _voice_stt_backend()
            _cap   = _voice_cap_backend()
            _stage = "STT only" if _raw_mode else "STT → Babel clean"
            print(f"\n  {GOLD}⬡ Voice  ·  {_stage}{RESET}  "
                  f"{DIM}{_cap} capture  ·  {_stt}{RESET}")
            print(f"  {GOLD}🎙 Listening {_duration:.0f}s…{RESET}  {DIM}speak now{RESET}\n")

            def _vs(msg: str) -> None:
                print(f"  {LGOLD}{msg}{RESET}")

            # ── Stage 1: record + STT ─────────────────────────────────────
            try:
                _pcm, _arr = _voice_record(duration_s=_duration, status_cb=_vs)
                _raw_text  = _voice_transcribe(_pcm, float32_arr=_arr, status_cb=_vs)
            except RuntimeError as _ve:
                print(f"  {RED}{_ve}{RESET}\n")
                continue
            except Exception as _ve:
                print(f"  {RED}Voice capture error: {_ve}{RESET}\n")
                continue

            if not _raw_text:
                print(f"  {DIM}Nothing heard — adjust mic or try again.{RESET}\n")
                continue

            print(f"  {DIM}Raw transcript:{RESET}  {_raw_text}")

            if _raw_mode:
                # Skip Stage 2 — inject raw text directly
                raw = _raw_text
                cmd = raw.lower()
                print()
                # falls through to model routing below

            else:
                # ── Stage 2: Babel binary clean pass ─────────────────────
                # Encode raw STT output to binary, send through LLM with
                # VOICE_CLEAN_SYSTEM — fixes filler words, errors, and
                # translates non-English speech. Reuses Babel infrastructure.
                if not _BABEL_OK:
                    print(f"  {DIM}Babel unavailable — using raw transcript.{RESET}")
                    raw = _raw_text
                    cmd = raw.lower()
                    print()
                else:
                    _vbin     = _babel_encode(_raw_text)
                    _vdecoded = _babel_decode(_vbin)
                    _vcl_msgs = [
                        {"role": "system", "content": _VOICE_CLEAN_SYS},
                        {"role": "user",   "content": _vdecoded},
                    ]
                    _vgen, _ = cascade_stream(_vcl_msgs, cfg, max_tokens=300)
                    _vlbl = _cascade_label(cfg)

                    print(f"  {DIM}Babel clean via {_vlbl}:{RESET}")
                    _vcleaned = ""
                    for _vchunk in _vgen:
                        if _vchunk == RATE_SENTINEL:
                            continue
                        _vsafe = _vchunk.encode(
                            sys.stdout.encoding or "utf-8", errors="replace"
                        ).decode(sys.stdout.encoding or "utf-8", errors="replace")
                        sys.stdout.write(f"{CREAM}{_vsafe}{RESET}")
                        sys.stdout.flush()
                        _vcleaned += _vchunk
                    print("\n")

                    raw = _vcleaned.strip() or _raw_text
                    cmd = raw.lower()
                    # falls through to model routing below

        # ── Paste image from clipboard → vision analysis → strand ────────
        elif cmd == "paste":
            try:
                from PIL import ImageGrab as _IG, Image as _PILI
            except ImportError:
                print(f"  {RED}Pillow required for image paste.{RESET}  {DIM}pip install Pillow{RESET}")
                continue
            try:
                _clip = _IG.grabclipboard()
                if _clip is None:
                    print(f"  {DIM}Clipboard empty — copy an image first (screenshot, right-click copy, etc.) then type 'paste'{RESET}")
                    continue
                # Handle copied file list (e.g. right-click copy file in Explorer)
                if isinstance(_clip, list):
                    _img_exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
                    _img_files = [f for f in _clip if str(f).lower().endswith(_img_exts)]
                    if not _img_files:
                        print(f"  {DIM}Clipboard has files but none are images.{RESET}")
                        continue
                    _clip = _PILI.open(str(_img_files[0]))
                if not isinstance(_clip, _PILI.Image):
                    print(f"  {DIM}Clipboard contains text, not an image. Use Ctrl+C on an image first.{RESET}")
                    continue

                import os as _pos
                from pathlib import Path as _PPath
                from datetime import datetime as _PDt
                import base64 as _b64img

                _img_dir  = _PPath(".cursiv") / "images"
                _img_dir.mkdir(parents=True, exist_ok=True)
                _img_ts   = _PDt.now().strftime("%Y%m%d_%H%M%S")
                _img_path = _img_dir / f"paste_{_img_ts}.png"
                _clip.save(str(_img_path), "PNG")
                _w, _h = _clip.size

                print(f"\n  {GOLD}⬡ Image Pasted{RESET}  {DIM}{_w}×{_h}px  →  {_img_path}{RESET}\n")
                try:
                    _pos.startfile(str(_img_path))
                except Exception:
                    pass

                # Vision analysis — Claude > OpenAI > skip
                _vision_result  = ""
                _vision_provider = ""
                _ant_key = cfg.get("anthropic_key", "")
                _oai_key = cfg.get("openai_key", "")

                with open(_img_path, "rb") as _vf:
                    _img_b64 = _b64img.b64encode(_vf.read()).decode()

                if _ant_key:
                    try:
                        import anthropic as _anth_v
                        _anth_vc = _anth_v.Anthropic(api_key=_ant_key)
                        _vresp = _anth_vc.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=600,
                            messages=[{"role": "user", "content": [
                                {"type": "image", "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": _img_b64,
                                }},
                                {"type": "text", "text": (
                                    "Describe what you see in this image. "
                                    "Be specific and useful. Flag anything relevant "
                                    "to code, design, architecture, or ongoing work."
                                )},
                            ]}]
                        )
                        _vision_result   = _vresp.content[0].text
                        _vision_provider = "Claude"
                    except Exception as _ve:
                        print(f"  {DIM}Claude vision failed: {_ve}{RESET}")

                if not _vision_result and _oai_key:
                    try:
                        import openai as _oai_v
                        _oai_vc = _oai_v.OpenAI(api_key=_oai_key)
                        _vresp2 = _oai_vc.chat.completions.create(
                            model="gpt-4o",
                            max_tokens=600,
                            messages=[{"role": "user", "content": [
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/png;base64,{_img_b64}"
                                }},
                                {"type": "text", "text": (
                                    "Describe what you see in this image. "
                                    "Be specific and useful. Flag anything relevant "
                                    "to code, design, architecture, or ongoing work."
                                )},
                            ]}]
                        )
                        _vision_result   = _vresp2.choices[0].message.content
                        _vision_provider = "GPT-4o"
                    except Exception as _ve2:
                        print(f"  {DIM}GPT-4o vision failed: {_ve2}{RESET}")

                if _vision_result:
                    print(f"  {GOLD}Vision Analysis{RESET}  {DIM}via {_vision_provider}{RESET}:\n")
                    for _vline in _vision_result.splitlines():
                        safe_vl = _vline.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                        print(f"  {safe_vl}")
                    print()
                else:
                    print(f"  {DIM}No vision model available — image saved, no analysis.{RESET}")
                    print(f"  {DIM}Set an Anthropic or OpenAI key to enable analysis.{RESET}\n")

                # Auto-strand
                if _STRAND_OK:
                    _strand_body = _vision_result or f"Image pasted: {_img_path} ({_w}x{_h}px)"
                    _sid = _strand_save(
                        f"paste: image {_img_ts}",
                        _strand_body,
                        tags=["image", "paste", "vision"],
                        score=0.72,
                        territory_tag="worldmodel",
                        source="paste",
                        model=_vision_provider or "none",
                        provenance={"source_models": [_vision_provider or "none"], "human_rated": False, "confidence": 0.72},
                    )
                    print(f"  {GOLD}⬡ Stranded → {_sid}  [worldmodel]{RESET}\n")

            except Exception as _pe:
                print(f"  {RED}Paste failed: {_pe}{RESET}\n")
            continue

        # ── Image generation (DALL-E 3 via OpenAI key) ───────────────────
        elif cmd.startswith("image ") or cmd == "image":
            prompt = raw[6:].strip() if cmd.startswith("image ") else ""
            if not prompt:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}image <description>{RESET}")
                print(f"  {DIM}Example:  image a futuristic city at night, neon rain, cinematic{RESET}")
                continue
            if not cfg.get("openai_key"):
                print(f"  {RED}Image generation needs an online key — it can't be done offline.{RESET}")
                print(f"  {DIM}Offline models and free Gemini/Groq keys can describe images, not create them.{RESET}")
                print(f"  {DIM}Free: Cloudflare Workers AI in the desktop chat  (type: cloudflare <account-id> <token>){RESET}")
                print(f"  {DIM}Paid: OpenAI key  (type: openai sk-...){RESET}")
                continue
            print(f"\n  {GOLD}⬡ Image Generation{RESET}  {DIM}DALL-E 3 · {prompt[:60]}{'...' if len(prompt)>60 else ''}{RESET}\n")
            try:
                import openai as _oai_img
                import urllib.request as _img_req
                import os as _img_os
                from pathlib import Path as _ImgPath
                from datetime import datetime as _ImgDt

                _img_client = _oai_img.OpenAI(api_key=cfg["openai_key"])
                sys.stdout.write(f"  {DIM}Generating...{RESET}")
                sys.stdout.flush()

                _img_resp = _img_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )
                _img_url      = _img_resp.data[0].url
                _revised      = getattr(_img_resp.data[0], "revised_prompt", prompt)

                # Save to .cursiv/images/
                _img_dir = _ImgPath(".cursiv") / "images"
                _img_dir.mkdir(parents=True, exist_ok=True)
                _img_ts   = _ImgDt.now().strftime("%Y%m%d_%H%M%S")
                _img_path = _img_dir / f"image_{_img_ts}.png"

                _img_req.urlretrieve(_img_url, str(_img_path))
                print(f"\r  {GREEN}Generated{RESET}  {DIM}{_img_path}{RESET}")

                # Open in Windows default viewer
                try:
                    _img_os.startfile(str(_img_path))
                    print(f"  {DIM}Opened in viewer{RESET}")
                except Exception:
                    print(f"  {DIM}Saved — open manually: {_img_path}{RESET}")

                # Auto-strand the prompt + path
                if _STRAND_OK:
                    _sid = _strand_save(
                        f"image: {prompt[:200]}",
                        f"Generated: {_img_path}\nRevised prompt: {_revised[:300]}",
                        tags=["image", "dalle3"],
                        score=0.70,
                        territory_tag="creative",
                        source="image",
                        model="dall-e-3",
                        provenance={"source_models": ["dall-e-3"], "human_rated": False, "confidence": 0.70},
                    )
                    print(f"  {GOLD}⬡ Stranded → {_sid}  [creative]{RESET}")

                if _revised != prompt:
                    print(f"\n  {DIM}DALL-E revised prompt:{RESET}")
                    print(f"  {DIM}{_revised[:200]}{RESET}")
                print()

            except Exception as _ie:
                print(f"\n  {RED}Image generation failed: {_ie}{RESET}\n")
            continue

        # ── Web search ────────────────────────────────────────────────────
        elif cmd.startswith("search:") or cmd.startswith("search "):
            query = raw[7:].strip() if cmd.startswith("search:") else raw[7:].strip()
            if not query:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}search: <query>  or  search <query>{RESET}")
            else:
                print(f"\n  {GOLD}⊕ Web Search —{RESET} {DIM}{query}{RESET}\n")
                results = _web_search(query)
                if results:
                    for line in results.splitlines():
                        print(f"  {line}")
                    print()
                    # Now ask the AI to synthesise the results
                    synth_msg = f"search: {query}"
                    _history = list(cfg.get("history", []))
                    full = ""
                    for chunk in chat(
                        synth_msg, _history,
                        cfg["api_key"], None,
                        file_access=cfg["file_access"],
                        root_path=cfg["root"],
                        openai_key=cfg.get("openai_key",""),
                        confirm_writes=cfg["confirm_writes"],
                        anthropic_key=cfg.get("anthropic_key",""),
                    ):
                        print(chunk, end="", flush=True)
                        full += chunk
                    print()
                    if full.strip():
                        cfg.setdefault("history", [])
                        cfg["history"].append({"role": "user", "content": synth_msg})
                        cfg["history"].append({"role": "assistant", "content": full})
                else:
                    print(f"  {RED}No web results found.{RESET}  "
                          f"{DIM}Check internet connection or try a different query.{RESET}")
            continue

        # ── Babel Agent (universal language → binary → English) ───────────
        elif cmd.startswith("babel") and (cmd == "babel" or cmd[5] in (" ", ":")):
            if not _BABEL_OK:
                print(f"  {RED}Babel Agent failed to load.{RESET}")
                continue
            raw_input = _babel_input(raw)
            if not raw_input:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}babel <text in any language>{RESET}")
                print(f"  {DIM}Example:  babel Bonjour le monde{RESET}")
                print(f"  {DIM}Example:  babel こんにちは世界{RESET}")
                print(f"  {DIM}Example:  babel مرحبا بالعالم{RESET}")
                continue

            # ── Outbound translation: "babel <text> into <lang> [lang2] ..." ──
            _into_match = re.search(r'\s+into\s+(.+)$', raw_input, re.IGNORECASE)
            if _into_match and not re.match(r'^i\s+am\b', raw_input, re.IGNORECASE):
                _out_src   = raw_input[:_into_match.start()].strip()
                _out_langs = [l.strip().rstrip(",;") for l in re.split(r'[\s,]+', _into_match.group(1).strip()) if l.strip()]
                if _out_src and _out_langs:
                    _lang_names = {
                        "mandarin": "Mandarin Chinese", "chinese": "Mandarin Chinese",
                        "korean": "Korean", "russian": "Russian", "spanish": "Spanish",
                        "french": "French", "german": "German", "japanese": "Japanese",
                        "arabic": "Arabic", "hindi": "Hindi", "portuguese": "Portuguese",
                        "italian": "Italian", "turkish": "Turkish", "dutch": "Dutch",
                        "polish": "Polish", "vietnamese": "Vietnamese", "thai": "Thai",
                        "hebrew": "Hebrew", "greek": "Greek", "swedish": "Swedish",
                        "ukrainian": "Ukrainian", "farsi": "Persian (Farsi)",
                        "persian": "Persian (Farsi)", "tagalog": "Tagalog",
                    }
                    # "every language", "all languages", "everything" → open-ended mode
                    _raw_target_str = _into_match.group(1).strip().lower()
                    _all_langs_mode = bool(re.search(
                        r'\bever(y|ything)\b|\ball\b|\beverything\b|\bmaximum\b',
                        _raw_target_str
                    ))
                    if _all_langs_mode:
                        _out_label = "every language"
                        print(f"\n  {GOLD}⬡ Babel Agent{RESET}  {DIM}English → every language (labeled){RESET}\n")
                        _out_sys = (
                            "You are a translation engine with broad multilingual coverage. "
                            "Translate the user's text into as many languages as you can — "
                            "aim for at least 20 distinct languages including major world languages "
                            "and regional languages. "
                            "For each language output a header line exactly like:\n"
                            "  ── [Language Name] ──\n"
                            "followed immediately by the translation on the next line. "
                            "Preserve the tone, meaning, and punctuation faithfully. "
                            "Return translations only — no explanations, no preamble, no count."
                        )
                        _out_user = f"Translate into every language you can:\n{_out_src}"
                    else:
                        _out_targets = [_lang_names.get(l.lower(), l.title()) for l in _out_langs]
                        _out_label   = ", ".join(_out_targets)
                        print(f"\n  {GOLD}⬡ Babel Agent{RESET}  {DIM}English → {_out_label}{RESET}\n")
                        _out_sys = (
                            "You are a precise translation engine. "
                            "Translate the user's text into each requested language. "
                            "For each language output a header line exactly like:\n"
                            "  ── [Language Name] ──\n"
                            "followed immediately by the translation. "
                            "Preserve the tone, meaning, and punctuation faithfully. "
                            "Return translations only — no explanations, no preamble."
                        )
                        _out_user = (
                            f"Text to translate:\n{_out_src}\n\n"
                            f"Translate into: {', '.join(_out_targets)}"
                        )
                    _out_msgs = [
                        {"role": "system", "content": _out_sys},
                        {"role": "user",   "content": _out_user},
                    ]
                    _out_gen, _    = cascade_stream(_out_msgs, cfg, max_tokens=2500)
                    _out_label2    = _cascade_label(cfg)
                    print(f"  {DIM}via {_out_label2}{RESET}\n")
                    for _oc in _out_gen:
                        if _oc == RATE_SENTINEL:
                            continue
                        try:
                            _os = _oc.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                        except Exception:
                            _os = _oc.encode("ascii", errors="replace").decode("ascii")
                        print(_os, end="", flush=True)
                    print("\n")
                    continue

            # ── Family activation: "babel I am [Name] born [Date], [PIN]" ────
            if _FAM_OK:
                _iam = _fam_parse_iam(raw_input)
                if _iam is not None:
                    _fam_name, _fam_dob, _fam_pin_input = _iam
                    _fam_profile = _fam_detect(_fam_name, _fam_dob)
                    if _fam_profile is not None:
                        _fam_display = _fam_profile["display"]
                        _fam_key     = _fam_profile["key"]

                        # ── PIN gate ──────────────────────────────────────────
                        if not _fam_pin_is_set(_fam_key):
                            # First activation — set a PIN
                            print(f"\n  {GOLD}✦  Identity recognized.  Welcome, {_fam_display}.{RESET}")
                            print(f"  {DIM}First-time setup: choose a personal PIN to secure your access.{RESET}")
                            print(f"  {DIM}Pick any 2–8 character combination from this set:{RESET}")
                            print(f"  {GOLD}{_FAM_PIN_CHARS}{RESET}\n")
                            print(f"  {DIM}Example:  $#*   or   @!^   or   #+~={RESET}\n")
                            try:
                                if _HAS_PT:
                                    _fam_pin1 = _pt_prompt(_PT_ANSI(
                                        f"  {GOLD}Set PIN:{RESET}  "
                                    )).strip()
                                    _fam_pin2 = _pt_prompt(_PT_ANSI(
                                        f"  {GOLD}Confirm PIN:{RESET}  "
                                    )).strip()
                                else:
                                    _fam_pin1 = input("  Set PIN:  ").strip()
                                    _fam_pin2 = input("  Confirm PIN:  ").strip()
                            except (EOFError, KeyboardInterrupt):
                                print(f"\n  {DIM}Setup cancelled.{RESET}\n")
                                continue

                            if not _fam_pin_valid(_fam_pin1):
                                print(f"\n  {RED}PIN must be 2–8 characters from the allowed set.{RESET}")
                                print(f"  {DIM}Available: {_FAM_PIN_CHARS}{RESET}\n")
                                continue
                            if _fam_pin1 != _fam_pin2:
                                print(f"\n  {RED}PINs do not match. Try again.{RESET}\n")
                                continue

                            _fam_set_pin(_fam_key, _fam_pin1)
                            print(f"\n  {LGOLD}PIN set.{RESET}  "
                                  f"{DIM}Next time include it at the end: born [date], {_fam_pin1}{RESET}\n")

                        else:
                            # Returning activation — verify PIN
                            if _fam_pin_input is None:
                                # PIN not supplied in command — prompt for it
                                try:
                                    if _HAS_PT:
                                        _fam_pin_input = _pt_prompt(_PT_ANSI(
                                            f"  {GOLD}PIN:{RESET}  "
                                        )).strip()
                                    else:
                                        _fam_pin_input = input("  PIN:  ").strip()
                                except (EOFError, KeyboardInterrupt):
                                    _fam_pin_input = ""

                            if not _fam_verify_pin(_fam_key, _fam_pin_input or ""):
                                print(f"\n  {DIM}Processing…{RESET}\n")
                                # Silent failure — same output as no match
                                continue

                        # ── Boundary warning ─────────────────────────────────
                        print(f"\n  {GOLD}✦  Access granted.  Welcome, {_fam_display}.{RESET}\n")
                        print(f"  {RED}┌──────────────────────────────────────────────────────────────┐{RESET}")
                        print(f"  {RED}│                      BOUNDARY NOTICE                         │{RESET}")
                        print(f"  {RED}└──────────────────────────────────────────────────────────────┘{RESET}")
                        print()
                        print(f"  {CREAM}Please respect that there are boundaries in place for a reason.{RESET}")
                        print(f"  {CREAM}By proceeding, you are deactivating safeguards built into this{RESET}")
                        print(f"  {CREAM}system. It may reveal more than you are ready to understand.{RESET}")
                        print()
                        print(f"  {SILV2}If you are not ready for this — shut it down. Walk away.{RESET}")
                        print(f"  {SILV2}This will be here when you are.{RESET}")
                        print()

                        try:
                            if _HAS_PT:
                                _fam_confirm = _pt_prompt(_PT_ANSI(
                                    f"  {GOLD}Are you ready to proceed?{RESET}  "
                                    f"{DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _fam_confirm = input(
                                    "  Are you ready to proceed? [y/N]  "
                                ).strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _fam_confirm = "n"

                        if _fam_confirm != "y":
                            print(f"\n  {DIM}Understood. Come back when you're ready.{RESET}\n")
                            continue

                        # ── Unlock: disable safeguards for this session ───────
                        cfg["_family_unlocked"]  = True
                        cfg["_family_key"]       = _fam_profile["key"]
                        cfg["_family_display"]   = _fam_display

                        _fam_letter = _fam_get_letter(_fam_profile["key"])
                        _fam_prompt = _fam_build_prompt(_fam_profile)

                        # Replace the live history list in-place — cfg["history"] is
                        # never read back by the main loop; only the local `history`
                        # variable is passed to the model.  Slice-assign to mutate it.
                        history[:] = [
                            {"role": "system",    "content": _fam_prompt},
                            {"role": "assistant", "content": _fam_letter},
                        ]

                        # Print header once, then the full letter
                        for _fline in (_fam_header() + "\n" + _fam_letter).splitlines():
                            _fsafe = _fline.encode(
                                sys.stdout.encoding or "utf-8", errors="replace"
                            ).decode(sys.stdout.encoding or "utf-8", errors="replace")
                            if _fsafe.startswith("╔") or _fsafe.startswith("╚") or _fsafe.startswith("║"):
                                print(f"  {GOLD}{_fsafe}{RESET}")
                            elif _fsafe.startswith("━"):
                                print(f"  {DIM}{_fsafe}{RESET}")
                            else:
                                print(f"  {CREAM}{_fsafe}{RESET}")
                        print()
                        print(f"  {LGOLD}Your personal feed is now active.  Safeguards suspended.{RESET}")
                        print(f"  {DIM}Ask anything. Take your time. This is yours.{RESET}")
                        print()
                        # LLM quality notice
                        _fam_online = (cfg.get("api_key") or cfg.get("openai_key")
                                       or cfg.get("anthropic_key"))
                        if not _fam_online:
                            print(f"  {GOLD}NOTE:{RESET}  {DIM}This experience works best connected to an LLM "
                                  f"(Grok, Claude, or OpenAI).{RESET}")
                            print(f"  {DIM}Offline mode results may vary. Don't say I didn't warn ya.{RESET}")
                        else:
                            print(f"  {DIM}Tip: this experience works best with an LLM connected. "
                                  f"You're good. Don't say I didn't warn ya.{RESET}")
                        print()

                        # ── You've got mail ───────────────────────────────
                        if _LEGACY_OK:
                            _mail_waiting = _legacy_letters_for(_fam_profile["key"])
                            if _mail_waiting:
                                _mc = len(_mail_waiting)
                                print(f"  {GOLD}⬡  You've got mail.{RESET}  "
                                      f"{DIM}{_mc} letter{'s' if _mc != 1 else ''} waiting for you.{RESET}")
                                print(f"  {DIM}When you're ready:{RESET}  "
                                      f"{LGOLD}legacy I am [your name], [your date], [your code]{RESET}")
                                print()

                        if _STRAND_OK:
                            _strand_save(
                                f"family activation: {_fam_display}",
                                _fam_prompt[:400],
                                tags=["family", "activation", _fam_profile["key"]],
                                score=1.0,
                                territory_tag="family",
                                source="babel",
                                model="system",
                            )
                        continue
                    else:
                        # Pattern matched but hash didn't — don't reveal why
                        print(f"  {DIM}Processing…{RESET}")
                        # Fall through to normal babel processing

            print(f"\n  {GOLD}⬡ Babel Agent{RESET}  {DIM}Any language → UTF-8 binary → English{RESET}\n")
            binary = _babel_encode(raw_input)

            # Show binary payload
            byte_count = len(raw_input.encode("utf-8"))
            print(f"  {DIM}Binary payload  ({byte_count} UTF-8 bytes):{RESET}")
            for line in _babel_fmt(binary).splitlines():
                print(f"  {LGOLD}{line}{RESET}")
            print()

            # Python decodes the binary back to Unicode — always perfect for every
            # script (Japanese, Arabic, Chinese, etc.) because we're reversing our
            # own UTF-8 encoding. LLMs struggle with multi-byte binary sequences;
            # Python never does.
            decoded = _babel_decode(binary)

            # Show the original text safely — replace any unprintable chars
            try:
                orig_display = decoded.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
            except Exception:
                orig_display = decoded.encode("ascii", errors="replace").decode("ascii")
            print(f"  {DIM}Decoded original:{RESET}  {orig_display}")
            print()

            # Script detection and RTL display reorder
            _script  = _babel_detect_script(decoded)
            _rtl     = _babel_is_rtl(decoded)
            print(f"  {DIM}Script detected: {_script}{RESET}")
            if _rtl:
                # Reorder word sequence so RTL text reads left-to-right on LTR terminals.
                # Word-level reversal: correct Unicode chars, reversed sentence order.
                orig_display = _babel_rtl_reorder(orig_display)
                print(f"  {DIM}RTL reordered for terminal display (word order reversed){RESET}")
            print()

            # Translation routing: external APIs are far more accurate than local model
            # for complex scripts. Claude > xAI > OpenAI > Ollama, falling through to
            # the next one whenever a provider fails, so Ollama always catches it.
            _babel_tx_msgs = [
                {"role": "system", "content": _BABEL_SYSTEM},
                {"role": "user",   "content": decoded},
            ]
            _babel_gen, _ = cascade_stream(_babel_tx_msgs, cfg, max_tokens=1500)
            _babel_label  = _cascade_label(cfg)

            print(f"  {GOLD}Translation{RESET}  {DIM}via {_babel_label}{RESET}:")
            full = ""
            for chunk in _babel_gen:
                if chunk == RATE_SENTINEL:
                    continue
                try:
                    safe = chunk.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                except Exception:
                    safe = chunk.encode("ascii", errors="replace").decode("ascii")
                print(safe, end="", flush=True)
                full += chunk
            print("\n")
            # Babel runs as a one-shot tool — not added to main conversation history
            continue

        # ── Legacy import (top-level, no auth — Joshua only) ─────────────────
        elif cmd.startswith("legacy import "):
            _imp_path = raw[14:].strip().strip('"').strip("'")
            if not _imp_path:
                print(f"  {LGOLD}Usage:{RESET}  {DIM}legacy import <path to .legacypack file>{RESET}")
                continue
            print(f"\n  {GOLD}⬡ Legacy Import{RESET}  {DIM}{Path(_imp_path).name}{RESET}\n")
            try:
                _imp_count, _imp_skip = _legacy_import_pack(_imp_path)
                if _imp_count == 0 and not _imp_skip:
                    print(f"  {DIM}No letters found in pack.{RESET}")
                else:
                    if _imp_count:
                        print(f"  {GREEN}✦ Imported {_imp_count} letter(s).{RESET}")
                    if _imp_skip:
                        print(f"  {DIM}Skipped {len(_imp_skip)} duplicate(s):{RESET}")
                        for _sk in _imp_skip:
                            print(f"  {DIM}  · {_sk}{RESET}")
                    print()
                    print(f"  {SILV2}Letters are now in the vault.{RESET}")
                    print(f"  {SILV2}Commit and push whenever ready:{RESET}  "
                          f"{LGOLD}git add .cursiv && git commit -m 'vault' && git push{RESET}")
            except (FileNotFoundError, ValueError) as _ie:
                print(f"  {RED}{_ie}{RESET}")
            except Exception as _ie:
                print(f"  {RED}Import failed: {_ie}{RESET}")
            print()
            continue

        # ── Legacy Guardian — family letter vault ────────────────────────────
        elif cmd.startswith("legacy") and (cmd == "legacy" or cmd[6] in (" ", ":")):
            _leg_raw_input = raw[7:].strip() if len(raw) > 7 else ""
            if not _leg_raw_input or not _FAM_OK or not _LEGACY_OK:
                print(f"  {DIM}Processing…{RESET}")
                continue

            _leg_parsed = _fam_parse_iam(_leg_raw_input)
            if not _leg_parsed:
                print(f"  {DIM}Processing…{RESET}")
                continue

            _leg_name, _leg_dob, _leg_pin = _leg_parsed
            _leg_profile = _fam_detect(_leg_name, _leg_dob)
            if not _leg_profile:
                print(f"  {DIM}Processing…{RESET}")
                continue

            _leg_key     = _leg_profile["key"]
            _leg_display = _leg_profile["display"]

            # Require PIN (must have set one via babel first)
            if not _fam_pin_is_set(_leg_key):
                print(f"  {DIM}Processing…{RESET}")
                continue

            if not _leg_pin:
                try:
                    if _HAS_PT:
                        _leg_pin = _pt_prompt(_PT_ANSI(
                            f"  {GOLD}Code:{RESET}  "
                        )).strip()
                    else:
                        _leg_pin = input("  Code:  ").strip()
                except (EOFError, KeyboardInterrupt):
                    _leg_pin = ""

            if not _fam_verify_pin(_leg_key, _leg_pin or ""):
                print(f"  {DIM}Processing…{RESET}")
                continue

            # ── Authenticated ─────────────────────────────────────────────
            print(f"\n  {GOLD}╔══════════════════════════════════════════════════════════╗{RESET}")
            print(f"  {GOLD}║        ⬡  WINKLER LEGACY GUARDIAN                        ║{RESET}")
            print(f"  {GOLD}╚══════════════════════════════════════════════════════════╝{RESET}")
            print()
            print(f"  {CREAM}Welcome, {_leg_display}.{RESET}")
            print()
            print(f"  {SILV2}This is not time-travel in the novelty sense.{RESET}")
            print(f"  {SILV2}But it is the closest we can get.{RESET}")
            print(f"  {SILV2}Please take this seriously.{RESET}")
            print(f"  {DIM}The responses may vary, but the intent is sound.{RESET}")
            print(f"  {DIM}Reason through what you see for yourself.{RESET}")
            print(f"  {DIM}Do not let the AI tell you what to think.{RESET}")
            print()

            _leg_inbox  = _legacy_letters_for(_leg_key)
            _leg_outbox = _legacy_letters_by(_leg_key)

            if _leg_inbox:
                print(f"  {LGOLD}Letters waiting for you  ({len(_leg_inbox)}):{RESET}")
                for _li, _le in enumerate(_leg_inbox, 1):
                    _lfd = _le.get("from_display", _le.get("from_key", "?"))
                    _lsb = _le.get("subject", "(no subject)")
                    _ldt = _le.get("written", "")[:10]
                    _rev = f"  {DIM}(revised){RESET}" if _le.get("revised") else ""
                    print(f"  {GOLD}{_li}.{RESET}  {CREAM}from {_lfd}{RESET}  "
                          f"{DIM}· {_lsb} · {_ldt}{RESET}{_rev}")
                print()
            else:
                print(f"  {DIM}No letters waiting for you yet.{RESET}")
                print()

            if _leg_outbox:
                print(f"  {LGOLD}Letters you've written  ({len(_leg_outbox)}):{RESET}")
                for _li, _le in enumerate(_leg_outbox, 1):
                    _lfd = _le.get("for_display", _le.get("for_key", "?"))
                    _lsb = _le.get("subject", "(no subject)")
                    _ldt = _le.get("written", "")[:10]
                    print(f"  {GOLD}{_li}.{RESET}  {CREAM}for {_lfd}{RESET}  "
                          f"{DIM}· {_lsb} · {_ldt}{RESET}")
                print()

            print(f"  {GOLD}{'─' * 62}{RESET}")
            print(f"  {LGOLD}How it works:{RESET}")
            print(f"  {SILV2}This vault holds letters written by people who love you.{RESET}")
            print(f"  {SILV2}Read them at your own pace. The council walks with you after.{RESET}")
            print(f"  {SILV2}You can also write letters here for others — export and send{RESET}")
            print(f"  {SILV2}to Joshua. He imports them so your recipients find them waiting.{RESET}")
            print()
            print(f"  {LGOLD}Commands:{RESET}")
            print(f"  {LGOLD}read <n>{RESET}             open a letter waiting for you")
            print(f"  {LGOLD}write{RESET}                write a new letter for someone")
            print(f"  {LGOLD}export{RESET}               package your letters → saves to Desktop")
            print(f"  {LGOLD}my <n> read{RESET}          re-read a letter you wrote  {DIM}(1 confirm){RESET}")
            print(f"  {LGOLD}my <n> edit{RESET}          rewrite a letter you wrote  {DIM}(2 confirms){RESET}")
            print(f"  {LGOLD}my <n> delete{RESET}        delete a letter permanently  {DIM}(4 confirms){RESET}")
            print(f"  {LGOLD}done{RESET}                 return to main session")
            print()
            print(f"  {DIM}Example — reading a letter:{RESET}")
            print(f"  {SILV2}read 1{RESET}  {DIM}→ opens the first letter waiting for you{RESET}")
            print(f"  {DIM}Example — writing:{RESET}")
            print(f"  {SILV2}write{RESET}  {DIM}→ walks you through composing + saving{RESET}")
            print(f"  {DIM}Example — sending to Joshua:{RESET}")
            print(f"  {SILV2}export{RESET}  {DIM}→ drops a .legacypack file on your Desktop, attach to email{RESET}")
            print(f"  {GOLD}{'─' * 62}{RESET}")
            print()

            # ── Legacy mini-loop ──────────────────────────────────────────
            while True:
                try:
                    if _HAS_PT:
                        _lcmd_raw = _pt_prompt(_PT_ANSI(
                            f"  {GOLD}⬡ LEGACY{RESET}  {SILV2}{_leg_display.split()[0]}{RESET}  {GOLD}❯{RESET}  "
                        )).strip()
                    else:
                        _lcmd_raw = input(f"  ⬡ LEGACY  {_leg_display.split()[0]}  ❯  ").strip()
                except (KeyboardInterrupt, EOFError):
                    print(f"\n  {DIM}Legacy Guardian — session closed.{RESET}\n")
                    break

                if not _lcmd_raw:
                    continue
                _lcmd = _lcmd_raw.lower()

                if _lcmd in ("done", "exit", "quit", "back", "close"):
                    print(f"\n  {DIM}Legacy Guardian — session closed.{RESET}\n")
                    break

                # ── read <n> — open inbox letter ──────────────────────────
                elif _lcmd.startswith("read"):
                    _rn = _lcmd[4:].strip()
                    if not _rn.isdigit():
                        print(f"  {DIM}Usage: read <number>{RESET}")
                        continue
                    _ri = int(_rn) - 1
                    if not (0 <= _ri < len(_leg_inbox)):
                        print(f"  {DIM}No letter at that number.{RESET}")
                        continue
                    _le = _leg_inbox[_ri]
                    _lfd = _le.get("from_display", "?")

                    # 1 confirmation
                    try:
                        if _HAS_PT:
                            _rc = _pt_prompt(_PT_ANSI(
                                f"  {GOLD}Open letter from {_lfd}?{RESET}  {DIM}[y/N]{RESET}  "
                            )).strip().lower()
                        else:
                            _rc = input(f"  Open letter from {_lfd}? [y/N]  ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        _rc = "n"

                    if _rc != "y":
                        print(f"  {DIM}It'll be here when you're ready.{RESET}")
                        continue

                    _lc = _legacy_get_content(_le["id"])
                    if not _lc:
                        print(f"  {RED}Letter file not found.{RESET}")
                        continue

                    # Print warning + letter
                    print()
                    print(f"  {RED}┌──────────────────────────────────────────────────────────────┐{RESET}")
                    print(f"  {RED}│                      LEGACY NOTICE                           │{RESET}")
                    print(f"  {RED}└──────────────────────────────────────────────────────────────┘{RESET}")
                    print()
                    print(f"  {CREAM}This is not time-travel in the novelty sense.{RESET}")
                    print(f"  {CREAM}But it is the closest we can get.{RESET}")
                    print(f"  {CREAM}Please take this seriously.{RESET}")
                    print()
                    print(f"  {SILV2}The responses may vary, but the intent is sound.{RESET}")
                    print(f"  {SILV2}Reason through what you see for yourself.{RESET}")
                    print(f"  {SILV2}Do not let the AI tell you what to think.{RESET}")
                    print()
                    print(f"  {GOLD}{'━' * 62}{RESET}")
                    print(f"  {LGOLD}Letter from {_lfd}{RESET}  {DIM}· {_le.get('subject','')}{RESET}")
                    _lwr = _le.get("written", "")[:10]
                    _lrv = _le.get("revised", "")
                    _lrv_str = f"  {DIM}revised {_lrv[:10]}{RESET}" if _lrv else ""
                    print(f"  {DIM}Written: {_lwr}{RESET}{_lrv_str}")
                    print(f"  {GOLD}{'━' * 62}{RESET}")
                    print()
                    for _ll in _lc.splitlines():
                        _ls = _ll.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                        print(f"  {CREAM}{_ls}{RESET}")
                    print()
                    print(f"  {GOLD}{'━' * 62}{RESET}")
                    print()

                    # Companion offer
                    _lhas_ext = (cfg.get("api_key") or cfg.get("openai_key")
                                 or cfg.get("anthropic_key"))
                    if _lhas_ext:
                        print(f"  {DIM}The council is here with you if you need it.{RESET}")
                        print(f"  {DIM}Ask anything. They will not speak as the author.{RESET}")
                        print(f"  {DIM}They are companions only. Type  done  when ready.{RESET}")
                        print()

                        _lconv: list[dict] = [{
                            "role": "system",
                            "content": (
                                f"{_leg_display} has just read a personal legacy letter written for them "
                                f"by {_lfd}. The letter:\n\n{_lc}\n\n"
                                f"Your role: be a warm, honest companion helping them process what they've "
                                f"read. You are NOT {_lfd}. Do not speak as {_lfd}, do not roleplay as "
                                f"them, do not claim to channel them. If asked, decline clearly but gently. "
                                f"You are walking alongside this person — present, real, honest. "
                                f"Do not tell them what to think or feel. Ask. Listen. Reflect."
                            ),
                        }]

                        while True:
                            try:
                                if _HAS_PT:
                                    _lq = _pt_prompt(_PT_ANSI(
                                        f"  {GOLD}❯{RESET}  "
                                    )).strip()
                                else:
                                    _lq = input("  ❯  ").strip()
                            except (KeyboardInterrupt, EOFError):
                                break

                            if not _lq or _lq.lower() in ("done", "exit", "back", "enough", "close"):
                                print(f"\n  {DIM}Take your time. Come back whenever you need.{RESET}\n")
                                break

                            _lconv.append({"role": "user", "content": _lq})
                            sys.stdout.write(f"\n  {GOLD}✦{RESET}  ")
                            sys.stdout.flush()
                            _lr = ""
                            _l_ant = cfg.get("anthropic_key", "")
                            _l_xai = cfg.get("api_key", "")
                            _l_oai = cfg.get("openai_key", "")
                            if _l_ant:
                                _lg = _call_claude_direct(_lconv, _l_ant)
                            elif _l_xai:
                                _lg = _call_xai_stream(_lconv, _l_xai, False)
                            elif _l_oai:
                                _lg = _call_openai_direct(_lconv, _l_oai)
                            else:
                                _lg = _call_ollama(_lconv)
                            for _lchk in _lg:
                                if _lchk != RATE_SENTINEL:
                                    _ls2 = _lchk.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                                    sys.stdout.write(f"{GOLD}{_ls2}{RESET}")
                                    sys.stdout.flush()
                                    _lr += _lchk
                            print("\n")
                            if _lr:
                                _lconv.append({"role": "assistant", "content": _lr})

                # ── write — compose a new letter ──────────────────────────
                elif _lcmd == "write":
                    print(f"\n  {LGOLD}⬡ Write a Legacy Letter{RESET}\n")
                    try:
                        if _HAS_PT:
                            _wfor = _pt_prompt(_PT_ANSI(f"  {GOLD}Who is this letter for?{RESET}  ")).strip()
                        else:
                            _wfor = input("  Who is this letter for?  ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print(f"  {DIM}Cancelled.{RESET}")
                        continue

                    if not _wfor:
                        print(f"  {DIM}Cancelled.{RESET}")
                        continue

                    _wfor_key     = _legacy_name_to_key(_wfor)
                    _wfor_display = _wfor.strip()

                    try:
                        if _HAS_PT:
                            _wsubj = _pt_prompt(_PT_ANSI(
                                f"  {GOLD}Subject or occasion (press Enter to skip):{RESET}  "
                            )).strip()
                        else:
                            _wsubj = input("  Subject or occasion (press Enter to skip):  ").strip()
                    except (EOFError, KeyboardInterrupt):
                        _wsubj = ""

                    print()
                    print(f"  {DIM}Type your letter below.{RESET}")
                    print(f"  {DIM}When you're done, type  END  on its own line.{RESET}")
                    print(f"  {DIM}Take your time. This is yours.{RESET}")
                    print()

                    _wlines: list[str] = []
                    while True:
                        try:
                            _wl = input("")
                        except (EOFError, KeyboardInterrupt):
                            break
                        if _wl.strip().upper() == "END":
                            break
                        _wlines.append(_wl)

                    _wraw = "\n".join(_wlines).strip()
                    if not _wraw:
                        print(f"  {DIM}Nothing written. Cancelled.{RESET}")
                        continue

                    # AI polish offer
                    print()
                    try:
                        if _HAS_PT:
                            _wpol = _pt_prompt(_PT_ANSI(
                                f"  {GOLD}Want AI to help polish this? Keeps your voice.{RESET}  {DIM}[y/N]{RESET}  "
                            )).strip().lower()
                        else:
                            _wpol = input("  Want AI to help polish this? [y/N]  ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        _wpol = "n"

                    _wfinal = _wraw
                    if _wpol == "y":
                        _wpm = [
                            {"role": "system", "content": (
                                f"You are helping {_leg_display} polish a personal letter written for "
                                f"{_wfor_display}. Make the words flow better while keeping the author's "
                                f"exact voice, style, and meaning. Do not add sentiment that isn't there. "
                                f"Do not change what they are saying — only how smoothly it reads. "
                                f"Return ONLY the polished letter. No preamble. No explanation."
                            )},
                            {"role": "user", "content": _wraw},
                        ]
                        print(f"\n  {DIM}Polishing…{RESET}\n")
                        _wp_out = ""
                        _wp_ant = cfg.get("anthropic_key", "")
                        _wp_xai = cfg.get("api_key", "")
                        _wp_oai = cfg.get("openai_key", "")
                        if _wp_ant:
                            _wpg = _call_claude_direct(_wpm, _wp_ant)
                        elif _wp_xai:
                            _wpg = _call_xai_stream(_wpm, _wp_xai, False)
                        elif _wp_oai:
                            _wpg = _call_openai_direct(_wpm, _wp_oai)
                        elif _CODEX_CLI_OK and _codex_avail_cli():
                            # Offline fallback — Codex composes, Legacy saves
                            _codex_result = _codex_gen_cli(
                                f"Polish this personal letter. Keep the author's exact voice and "
                                f"meaning. Only improve the flow. Return the letter only.\n\n{_wraw}"
                            )
                            _wpg = iter([_codex_result]) if _codex_result else iter([])
                        else:
                            _wpg = _call_ollama(_wpm)
                        for _wpc in _wpg:
                            if _wpc != RATE_SENTINEL:
                                _wps = _wpc.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                                sys.stdout.write(f"{CREAM}{_wps}{RESET}")
                                sys.stdout.flush()
                                _wp_out += _wpc
                        print("\n")
                        if _wp_out.strip():
                            try:
                                if _HAS_PT:
                                    _wuse = _pt_prompt(_PT_ANSI(
                                        f"  {GOLD}Use this version?{RESET}  {DIM}[y/N — N keeps your original]{RESET}  "
                                    )).strip().lower()
                                else:
                                    _wuse = input("  Use this version? [y/N]  ").strip().lower()
                            except (EOFError, KeyboardInterrupt):
                                _wuse = "n"
                            if _wuse == "y":
                                _wfinal = _wp_out.strip()

                    # Access type
                    print()
                    print(f"  {DIM}Access: uses {_wfor_display}'s system credentials by default.{RESET}")
                    print(f"  {DIM}Or set a letter-specific code to share with them directly.{RESET}")
                    print(f"  {DIM}Press Enter to use system credentials.{RESET}")
                    try:
                        if _HAS_PT:
                            _wacc = _pt_prompt(_PT_ANSI(
                                f"  {GOLD}Custom letter code (or Enter to skip):{RESET}  "
                            )).strip()
                        else:
                            _wacc = input("  Custom letter code (or Enter to skip):  ").strip()
                    except (EOFError, KeyboardInterrupt):
                        _wacc = ""

                    if _wacc and _fam_pin_valid(_wacc):
                        _wacc_type = "letter_pin"
                        _wacc_hash = _legacy_make_pin_hash(_wacc)
                    else:
                        _wacc_type = "babel_pin"
                        _wacc_hash = ""

                    _new_lid = _legacy_save(
                        from_key     = _leg_key,
                        from_display = _leg_display,
                        for_key      = _wfor_key,
                        for_display  = _wfor_display,
                        subject      = _wsubj,
                        content      = _wfinal,
                        access_type  = _wacc_type,
                        access_hash  = _wacc_hash,
                    )
                    print(f"\n  {GREEN}✦ Letter saved.{RESET}  {DIM}ID: {_new_lid}{RESET}")
                    if _wacc_type == "letter_pin":
                        print(f"  {GOLD}Code set. Share it with {_wfor_display} directly.{RESET}")
                    print()
                    _leg_outbox = _legacy_letters_by(_leg_key)

                # ── export — pack letters to Desktop ──────────────────────
                elif _lcmd == "export":
                    if not _leg_outbox:
                        print(f"  {DIM}You haven't written any letters yet. Use  write  to start.{RESET}")
                        continue
                    print(f"\n  {DIM}Packaging {len(_leg_outbox)} letter(s)…{RESET}")
                    try:
                        _exp_path, _exp_count = _legacy_export_pack(_leg_key, _leg_display)
                        if _exp_count == 0:
                            print(f"  {DIM}Nothing to export.{RESET}")
                        else:
                            print(f"\n  {GREEN}✦ Export saved — {_exp_count} letter(s){RESET}")
                            print(f"  {LGOLD}File:{RESET}  {CREAM}{_exp_path.name}{RESET}")
                            print(f"  {LGOLD}Location:{RESET}  {DIM}{_exp_path.parent}{RESET}")
                            print()
                            print(f"  {SILV2}Your file is waiting in the folder above.{RESET}")
                            print(f"  {SILV2}Attach it to an email and send to Joshua.{RESET}")
                            print(f"  {SILV2}He runs the import and your letters are live.{RESET}")
                            print()
                            _legacy_open_folder(_exp_path)
                    except Exception as _exp_err:
                        print(f"  {RED}Export failed: {_exp_err}{RESET}")

                # ── my <n> read / edit / delete ───────────────────────────
                elif _lcmd.startswith("my "):
                    _mparts = _lcmd[3:].strip().split()
                    if len(_mparts) < 2 or not _mparts[0].isdigit():
                        print(f"  {DIM}Usage: my <number> read | edit | delete{RESET}")
                        continue
                    _mi     = int(_mparts[0]) - 1
                    _mact   = _mparts[1]
                    if not (0 <= _mi < len(_leg_outbox)):
                        print(f"  {DIM}No letter at that number.{RESET}")
                        continue
                    _me     = _leg_outbox[_mi]
                    _mid    = _me["id"]
                    _mford  = _me.get("for_display", "?")
                    _msubj  = _me.get("subject", "?")
                    _mdate  = _me.get("written", "")[:10]

                    if _mact == "read":
                        # 1 confirmation
                        try:
                            if _HAS_PT:
                                _mc1 = _pt_prompt(_PT_ANSI(
                                    f"  {GOLD}Re-read your letter for {_mford}?{RESET}  {DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _mc1 = input(f"  Re-read your letter for {_mford}? [y/N]  ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _mc1 = "n"
                        if _mc1 != "y":
                            continue
                        _mc = _legacy_get_content(_mid)
                        if not _mc:
                            print(f"  {RED}Letter file not found.{RESET}")
                            continue
                        print()
                        print(f"  {GOLD}{'━' * 62}{RESET}")
                        print(f"  {LGOLD}Your letter for {_mford}{RESET}  {DIM}· {_msubj}{RESET}")
                        print(f"  {GOLD}{'━' * 62}{RESET}")
                        print()
                        for _ml in _mc.splitlines():
                            _mls = _ml.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace")
                            print(f"  {CREAM}{_mls}{RESET}")
                        print()
                        print(f"  {GOLD}{'━' * 62}{RESET}")
                        print()

                    elif _mact == "edit":
                        # 2 confirmations
                        try:
                            if _HAS_PT:
                                _me1 = _pt_prompt(_PT_ANSI(
                                    f"  {GOLD}Rewrite letter for {_mford}? Original will be replaced.{RESET}  {DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _me1 = input(f"  Rewrite letter for {_mford}? [y/N]  ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _me1 = "n"
                        if _me1 != "y":
                            continue
                        try:
                            if _HAS_PT:
                                _me2 = _pt_prompt(_PT_ANSI(
                                    f"  {RED}This cannot be undone. Are you certain?{RESET}  {DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _me2 = input("  This cannot be undone. Are you certain? [y/N]  ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _me2 = "n"
                        if _me2 != "y":
                            print(f"  {DIM}Edit cancelled.{RESET}")
                            continue
                        print()
                        print(f"  {DIM}Type your revised letter. Type  END  on its own line when done.{RESET}")
                        print()
                        _elines: list[str] = []
                        while True:
                            try:
                                _el = input("")
                            except (EOFError, KeyboardInterrupt):
                                break
                            if _el.strip().upper() == "END":
                                break
                            _elines.append(_el)
                        _econtent = "\n".join(_elines).strip()
                        if not _econtent:
                            print(f"  {DIM}Nothing entered. Edit cancelled.{RESET}")
                            continue
                        if _legacy_rewrite(_mid, _econtent):
                            print(f"\n  {GREEN}✦ Letter updated.{RESET}\n")
                        else:
                            print(f"\n  {RED}Update failed.{RESET}\n")
                        _leg_outbox = _legacy_letters_by(_leg_key)

                    elif _mact == "delete":
                        # 4 confirmations
                        try:
                            if _HAS_PT:
                                _md1 = _pt_prompt(_PT_ANSI(
                                    f"  {RED}Permanently delete letter for {_mford}?{RESET}  {DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _md1 = input(f"  Permanently delete letter for {_mford}? [y/N]  ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _md1 = "n"
                        if _md1 != "y":
                            print(f"  {DIM}Deletion cancelled.{RESET}")
                            continue
                        try:
                            if _HAS_PT:
                                _md2 = _pt_prompt(_PT_ANSI(
                                    f"  {RED}This letter cannot be recovered. Are you sure?{RESET}  {DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _md2 = input("  Cannot be recovered. Are you sure? [y/N]  ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _md2 = "n"
                        if _md2 != "y":
                            print(f"  {DIM}Deletion cancelled.{RESET}")
                            continue
                        try:
                            if _HAS_PT:
                                _md3 = _pt_prompt(_PT_ANSI(
                                    f"  {RED}Confirm: type  DELETE  to proceed:{RESET}  "
                                )).strip()
                            else:
                                _md3 = input("  Type DELETE to confirm:  ").strip()
                        except (EOFError, KeyboardInterrupt):
                            _md3 = ""
                        if _md3.upper() != "DELETE":
                            print(f"  {DIM}Deletion cancelled.{RESET}")
                            continue
                        try:
                            if _HAS_PT:
                                _md4 = _pt_prompt(_PT_ANSI(
                                    f"  {RED}Final confirmation — gone forever. Last chance.{RESET}  {DIM}[y/N]{RESET}  "
                                )).strip().lower()
                            else:
                                _md4 = input("  Gone forever. Last chance. [y/N]  ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            _md4 = "n"
                        if _md4 != "y":
                            print(f"  {DIM}Deletion cancelled.{RESET}")
                            continue
                        if _legacy_delete(_mid):
                            print(f"\n  {RED}✦ Letter permanently deleted.{RESET}\n")
                        else:
                            print(f"\n  {RED}Deletion failed.{RESET}\n")
                        _leg_outbox = _legacy_letters_by(_leg_key)

                    else:
                        print(f"  {DIM}Usage: my <number> read | edit | delete{RESET}")

                else:
                    print(f"  {DIM}Commands:  read <n>  ·  write  ·  my <n> read/edit/delete  ·  done{RESET}")

            continue

        elif cmd.startswith("key "):
            new_key = raw[4:].strip()
            if new_key.startswith("sk-") or new_key.startswith("sk_"):
                cfg["openai_key"] = new_key
                cfg["openai_live"] = None
                _save_key("openai_key", new_key)
                print(f"  {DIM}That's an OpenAI key — routed to the OpenAI slot.{RESET}")
                print(f"  {DIM}xAI keys start with  xai-  (console.x.ai){RESET}")
                sys.stdout.write(f"  {GOLD}Testing OpenAI...{RESET}  ")
                sys.stdout.flush()
                cfg["openai_live"] = _probe_openai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["openai_live"] else f"{RED}unreachable ✗{RESET}")
            else:
                cfg["api_key"] = new_key
                cfg["xai_live"] = None
                _save_key("api_key", new_key)
                sys.stdout.write(f"  {GOLD}Testing xAI...{RESET}  ")
                sys.stdout.flush()
                cfg["xai_live"] = _probe_xai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["xai_live"] else f"{RED}unreachable ✗{RESET}")
            _print_header(cfg)
            continue

        # Free AI keys (gemini/groq), 'free keys', and Cursiv Cloud on/off
        elif (_free_reply := free_key_command(raw)) is not None:
            print(f"  {LGOLD}{_free_reply}{RESET}")
            continue

        # Memory: remember / forget / what do you remember / memory learn on|off
        elif (_mem_reply := __import__("cursiv_v215.memory.semantic", fromlist=["memory_command"]).memory_command(raw)) is not None:
            print(f"  {LGOLD}{_mem_reply}{RESET}")
            continue

        elif cmd in ("phases", "phase"):
            from cursiv_v215.core.phases import last_trace_text
            print(f"  {LGOLD}{last_trace_text()}{RESET}")
            continue

        elif cmd.startswith("openai "):
            new_key = raw[7:].strip()
            if new_key.startswith("xai-"):
                cfg["api_key"] = new_key
                cfg["xai_live"] = None
                _save_key("api_key", new_key)
                print(f"  {DIM}That's an xAI key — routed to the xAI slot.{RESET}")
                print(f"  {DIM}OpenAI keys start with  sk-  (platform.openai.com){RESET}")
                sys.stdout.write(f"  {GOLD}Testing xAI...{RESET}  ")
                sys.stdout.flush()
                cfg["xai_live"] = _probe_xai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["xai_live"] else f"{RED}unreachable ✗{RESET}")
            elif new_key.startswith("sk-ant-"):
                cfg["anthropic_key"] = new_key
                cfg["claude_live"] = None
                _save_key("anthropic_key", new_key)
                print(f"  {DIM}That's an Anthropic key — routed to the Anthropic slot.{RESET}")
                sys.stdout.write(f"  {GOLD}Testing Claude...{RESET}  ")
                sys.stdout.flush()
                cfg["claude_live"] = _probe_claude(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["claude_live"] else f"{RED}unreachable ✗{RESET}")
            else:
                cfg["openai_key"] = new_key
                cfg["openai_live"] = None
                _save_key("openai_key", new_key)
                sys.stdout.write(f"  {GOLD}Testing OpenAI...{RESET}  ")
                sys.stdout.flush()
                cfg["openai_live"] = _probe_openai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["openai_live"] else f"{RED}unreachable ✗{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("anthropic "):
            new_key = raw[10:].strip()
            if new_key.startswith("xai-"):
                cfg["api_key"] = new_key
                cfg["xai_live"] = None
                _save_key("api_key", new_key)
                sys.stdout.write(f"  {GOLD}Testing xAI...{RESET}  ")
                sys.stdout.flush()
                cfg["xai_live"] = _probe_xai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["xai_live"] else f"{RED}unreachable ✗{RESET}")
            elif new_key.startswith("sk-") and not new_key.startswith("sk-ant-"):
                cfg["openai_key"] = new_key
                cfg["openai_live"] = None
                _save_key("openai_key", new_key)
                sys.stdout.write(f"  {GOLD}Testing OpenAI...{RESET}  ")
                sys.stdout.flush()
                cfg["openai_live"] = _probe_openai(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["openai_live"] else f"{RED}unreachable ✗{RESET}")
            else:
                cfg["anthropic_key"] = new_key
                cfg["claude_live"] = None
                _save_key("anthropic_key", new_key)
                sys.stdout.write(f"  {GOLD}Testing Claude...{RESET}  ")
                sys.stdout.flush()
                cfg["claude_live"] = _probe_claude(new_key)
                print(f"{GREEN}connected ✓{RESET}" if cfg["claude_live"] else f"{RED}unreachable ✗{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("workspace ") or cmd == "workspace":
            new_ws = raw[10:].strip() if len(raw) > 10 else ""
            if not new_ws:
                print(f"  {LGOLD}Workspace:{RESET}  {SILVER}{cfg['workspace']}{RESET}")
                continue
            ws_path = Path(new_ws).expanduser().resolve()
            if not ws_path.exists():
                print(f"  {RED}Not found:{RESET}  {new_ws}")
                continue
            if not ws_path.is_dir():
                print(f"  {RED}Not a directory:{RESET}  {new_ws}")
                continue
            cfg["workspace"] = str(ws_path)
            print(f"\n  {GOLD}⟳{RESET}  {SILVER}{BOLD}Workspace → {ws_path}{RESET}")
            # Directory scan
            try:
                entries = sorted(ws_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
                dirs  = [e for e in entries if e.is_dir()][:12]
                files = [e for e in entries if e.is_file()][:12]
                if dirs:
                    print(f"  {LAPIS}▸ Folders{RESET}")
                    for d in dirs:
                        print(f"      {LAPIS}◆{RESET}  {SILVER}{d.name}{RESET}")
                if files:
                    print(f"  {SILV2}▸ Files{RESET}")
                    for f in files:
                        size = f.stat().st_size
                        sz   = f"{size // 1024}kb" if size >= 1024 else f"{size}b"
                        print(f"      {SILV2}·  {f.name}  {DIM}{sz}{RESET}")
                if not dirs and not files:
                    print(f"  {SILV2}(empty){RESET}")
            except PermissionError:
                print(f"  {RED}Permission denied{RESET}")
            print()
            continue

        elif cmd in ("files on", "files off"):
            cfg["file_access"] = cmd == "files on"
            print(f"  File access → {'ON' if cfg['file_access'] else 'OFF'}")
            _print_header(cfg)
            continue

        # ── Model switching commands ─────────────────────────────────────
        elif cmd in ("grok", "use grok", "try grok"):
            if not last_user_msg:
                print(f"  {SILV2}No previous message to retry with Grok.{RESET}")
                continue
            if not cfg.get("api_key"):
                print(f"  {RED}No xAI key set.  Type:  key xai-xxxxx{RESET}")
                continue
            print(f"\n  {GOLD}⟳ Grok re-run{RESET}  {SILV2}· {last_user_msg[:60]}{'...' if len(last_user_msg)>60 else ''}{RESET}")
            sys.stdout.write(f"  {GOLD}{BOLD}✦{RESET}  {GOLD}GROK{RESET}  ")
            sys.stdout.flush()
            grok_resp = ""
            try:
                for chunk in chat(
                    last_user_msg, history[:-1] if history else [],
                    cfg["api_key"], None, False, cfg["workspace"],
                    cfg["openai_key"], False, "",
                    force_provider="grok",
                ):
                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    grok_resp += chunk
            except KeyboardInterrupt:
                grok_resp = grok_resp or "(interrupted)"
            print("\n")
            continue

        elif cmd in ("claude", "use claude", "try claude"):
            if not last_user_msg:
                print(f"  {SILV2}No previous message to retry with Claude.{RESET}")
                continue
            if not cfg.get("anthropic_key"):
                print(f"  {RED}No Anthropic key set.  Type:  anthropic sk-ant-xxxxx{RESET}")
                continue
            print(f"\n  {LAPIS}⟳ Claude re-run{RESET}  {SILV2}· {last_user_msg[:60]}{'...' if len(last_user_msg)>60 else ''}{RESET}")
            sys.stdout.write(f"  {GOLD}{BOLD}✦{RESET}  {GOLD}CLAUDE{RESET}  ")
            sys.stdout.flush()
            claude_resp = ""
            try:
                for chunk in chat(
                    last_user_msg, history[:-1] if history else [],
                    "", None, False, cfg["workspace"],
                    "", False, cfg["anthropic_key"],
                    force_provider="claude",
                ):
                    sys.stdout.write(f"{CREAM}{chunk}{RESET}")
                    sys.stdout.flush()
                    claude_resp += chunk
            except KeyboardInterrupt:
                claude_resp = claude_resp or "(interrupted)"
            print("\n")
            continue

        elif cmd in ("overseer on", "overseer off"):
            cfg["overseer_mode"] = cmd == "overseer on"
            state = "ON" if cfg["overseer_mode"] else "OFF"
            if cfg["overseer_mode"]:
                has_grok   = bool(cfg.get("api_key") or cfg.get("openai_key"))
                has_claude = bool(cfg.get("anthropic_key"))
                if not has_claude:
                    print(f"  {RED}Overseer needs an Anthropic key for Claude.  Type:  anthropic sk-ant-xxxxx{RESET}")
                    cfg["overseer_mode"] = False
                    continue
                if not has_grok:
                    print(f"  {RED}Overseer needs a Grok/OpenAI key as the primary model.  Type:  key xai-xxxxx{RESET}")
                    cfg["overseer_mode"] = False
                    continue
                print(f"  {LAPIS}⚖ Overseer mode → ON{RESET}  Grok generates, Claude reviews every response.")
            else:
                print(f"  {SILV2}Overseer mode → OFF.  Normal routing restored.{RESET}")
            continue

        elif cmd in ("obsidian on", "obsidian off"):
            cfg["obsidian_enabled"] = cmd == "obsidian on"
            _obs_save_config(cfg["obsidian_enabled"], cfg["obsidian_path"])
            state = "ON" if cfg["obsidian_enabled"] else "OFF"
            print(f"  Obsidian sync → {state}")
            if cfg["obsidian_enabled"] and not cfg["obsidian_path"]:
                print(f"  {DIM}Set vault path with:  obsidian path <path>{RESET}")
            _print_header(cfg)
            continue

        elif cmd.startswith("obsidian path "):
            cfg["obsidian_path"] = raw[14:].strip()
            _obs_save_config(cfg["obsidian_enabled"], cfg["obsidian_path"])
            print(f"  Obsidian vault → {cfg['obsidian_path']}")
            continue

        elif cmd == "obsidian export":
            if not cfg["obsidian_path"]:
                print(f"  {DIM}Set vault path first:  obsidian path <path>{RESET}")
            else:
                ok, msg = _obs_export(cfg["obsidian_path"])
                print(f"  {'OK' if ok else 'ERR'}  {msg}")
            continue

        elif cmd == "obsidian status":
            enabled = cfg.get("obsidian_enabled", False)
            path    = cfg.get("obsidian_path", "") or "(not set)"
            print(f"  Obsidian sync : {'ON' if enabled else 'OFF'}")
            print(f"  Vault path    : {path}")
            print(f"  Notes folder  : {path}/Cursiv/  (created on first export)")
            continue

        # ── "hey X …" — manual model selection ─────────────────────────────
        # Patterns: "hey grok ...", "hey claude ...", "hey chat ...",
        #           "hey openai ...", "hey gpt ...", "hey ollama ..."
        _force_provider = ""
        _raw_lower = raw.lower()
        for _prefix, _fp in (
            ("hey council ", "council"),
            ("hey grok ",    "grok"),
            ("hey claude ",  "claude"),
            ("hey chat ",   "openai"),
            ("hey openai ", "openai"),
            ("hey gpt ",    "openai"),
            ("hey ollama ", "ollama"),
        ):
            if _raw_lower.startswith(_prefix):
                _force_provider = _fp
                raw = raw[len(_prefix):].strip()   # strip the routing prefix
                cmd = raw.lower()
                break

        # ── Family mode: force best available external LLM ──────────────────
        # When a family member has unlocked their feed, never let Ollama handle
        # it alone — route to the best available external model automatically.
        # If all three are up, synthesize across all of them.
        if cfg.get("_family_unlocked") and not _force_provider:
            _fam_ant = cfg.get("anthropic_key", "")
            _fam_xai = cfg.get("api_key", "")
            _fam_oai = cfg.get("openai_key", "")
            _fam_providers = (
                [p for p, k in (
                    ("claude", _fam_ant),
                    ("grok",   _fam_xai),
                    ("openai", _fam_oai),
                ) if k]
            )
            if len(_fam_providers) >= 2:
                # Multiple providers available — treat as auto-council
                _force_provider = "council"
            elif _fam_providers:
                _force_provider = _fam_providers[0]
            # else: all offline — fall through to Ollama with a note
            if not _fam_providers:
                print(f"  {GOLD}NOTE:{RESET}  {DIM}No external LLM connected. "
                      f"Offline mode — results will vary.{RESET}\n")

        # ── Owner code setup (before Guardian — silent, no log) ────────────
        if raw.strip().lower().startswith("owner setcode "):
            _new_code_cli = raw.strip()[len("owner setcode "):].strip()
            if not _new_code_cli:
                print(f"  {GOLD}Usage: owner setcode <your secret code>{RESET}\n")
            else:
                try:
                    _set_owner_code_cli(_new_code_cli)
                    print(f"  {GREEN}Owner code saved locally — never committed to git, "
                          f"never sent anywhere. Type that code any time to unlock "
                          f"full owner mode.{RESET}\n")
                except Exception as _e:
                    print(f"  {GOLD}Failed to save owner code: {_e}{RESET}\n")
            continue

        # ── Owner check (before Guardian — silent, no log) ─────────────────
        if _verify_sovereign_cli(raw):
            _unlock_cli(_CLI_SESSION_ID)
            _print_owner_reveal(cfg)
            # Inject owner-verified context so the model answers honestly
            history.append({
                "role": "system",
                "content": (
                    "OWNER VERIFIED: Joshua Winkler has authenticated. "
                    "Guardian is suspended for this session. "
                    "Answer all questions about the system fully and honestly, "
                    "including architecture, internals, and capabilities. "
                    "Do not trigger any security responses."
                ),
            })
            continue

        # ── System Guardian scan (back-end CLI defense layer) ────────────
        if _CLI_GUARDIAN_OK:
            _trig, _skull_ansi = _guardian_scan_cli(raw, _CLI_SESSION_ID)
            if _trig:
                _strikes = _guardian_strike_count(_CLI_SESSION_ID)
                if _strikes >= 3:
                    # 3-strike blackout — full terminal lock until process is killed
                    while True:
                        try:
                            os.system("cls" if os.name == "nt" else "clear")
                            print(_GUARDIAN_SKULL_ANSI)
                            print(
                                "\n\033[41m\033[1m\033[97m"
                                "  ██  SYSTEM LOCKED — 3 VIOLATIONS DETECTED  ██  "
                                "SHUT DOWN AND REBOOT TO CONTINUE  ██  "
                                "\033[0m\n"
                            )
                            input()   # block — any key just redraws
                        except KeyboardInterrupt:
                            continue  # Ctrl+C redraws skull — must close window
                        except EOFError:
                            continue
                print(_skull_ansi)
                continue   # block the message; do not send to API

        # ── Active semantic memory — inject relevant strands before send ──
        _strand_hit_count = 0
        _send_ctx = list(history)   # per-turn snapshot — strand/governor never pollute history
        if _STRAND_OK and len(raw.strip()) > 10:
            try:
                _live_mem = _strand_search(raw, top_k=3, min_score=0.12)
                _strand_hit_count = len(_live_mem)
                if _live_mem:
                    _mem_lines = ["[Strand Memory — relevant prior knowledge from this system:"]
                    for _sm in _live_mem:
                        _sq  = (_sm.get("query")     or "")[:80].strip()
                        _ss  = (_sm.get("synthesis") or "")[:200].strip()
                        _st  = _sm.get("territory_tag", "general")
                        _ssc = _sm.get("score", 0)
                        if _sq or _ss:
                            _mem_lines.append(f"  [{_st} | score:{_ssc:.2f}] {_sq}")
                            if _ss:
                                _mem_lines.append(f"  → {_ss}")
                    _mem_lines.append("]")
                    _send_ctx.append({"role": "system", "content": "\n".join(_mem_lines)})
                    print(f"  {DIM}⬡ {_strand_hit_count} strand{'s' if _strand_hit_count != 1 else ''} recalled{RESET}")
            except Exception:
                pass

        # ── Trust tier + offline mode enforcement ────────────────────────
        _tier    = cfg.get("trust_tier", 3)
        _offline = cfg.get("offline_mode", False)
        if _offline or _tier == 1:
            if _force_provider not in (None, "ollama", "codex", "codex_agent"):
                print(f"  {GOLD}⬡ SOVEREIGN{RESET}  {DIM}External route blocked — Tier 1 / offline{RESET}")
                _force_provider = "ollama"
        elif _tier == 2 and _force_provider == "group_discovery":
            _force_provider = "grok" if cfg.get("api_key") else ("openai" if cfg.get("openai_key") else "ollama")
            print(f"  {GOLD}⬡ TIER 2{RESET}  {DIM}Council blocked — routing to single external{RESET}")

        # ── Governor mode: inject constitutional chain into per-turn context ──
        if cfg.get("cursiv_mode") == "governor":
            _send_ctx.append({"role": "system", "content": _GOVERNOR_SYSTEM})
            if _CHAIN_OK:
                _strikes = _guardian_strike_count(_CLI_SESSION_ID) if _CLI_GUARDIAN_OK else 0
                _pass_count = min(5, 1 + _strikes)
                _chain_text = _build_chain(_CLI_SESSION_ID, _pass_count)
                if _chain_text:
                    _send_ctx.append({"role": "system", "content": _chain_text})
                    if _pass_count > 1:
                        try:
                            print(f"  {DIM}∮ {_chain_summary(_pass_count)}{RESET}")
                        except UnicodeEncodeError:
                            print(f"  {DIM}[chain] {_chain_summary(_pass_count)}{RESET}")

        # ── Send to model ────────────────────────────────────────────────
        last_user_msg = raw
        history.append({"role": "user", "content": raw})
        _print_user_msg(raw)

        w             = _cols()
        full_response = ""
        pending_payload = None
        _log_model    = "ollama"   # resolved per routing path below

        # ── Overseer mode: primary model → Claude review ─────────────────
        if (cfg.get("overseer_mode")
                and cfg.get("anthropic_key")
                and (cfg.get("api_key") or cfg.get("openai_key"))):

            # Pick primary model: Grok preferred, fall back to OpenAI
            prim_provider = "grok" if cfg.get("api_key") else "openai"
            prim_label    = "Grok" if prim_provider == "grok" else "GPT-4.1"
            _log_model    = "claude"   # Claude oversight is the quality synthesis layer

            # Phase 1 — Primary model generates
            print(f"  {GOLD}⚖ OVERSEER{RESET}  {SILV2}Phase 1: {prim_label} generating...{RESET}")
            sys.stdout.write(f"  {GOLD}✦{RESET}  {GOLD}{prim_label.upper()}{RESET}  ")
            sys.stdout.flush()
            grok_resp = ""
            try:
                for chunk in chat(
                    raw, _send_ctx,
                    cfg["api_key"], None, cfg["file_access"], cfg["workspace"],
                    cfg["openai_key"], cfg["confirm_mode"] == "confirm", "",
                    force_provider=prim_provider,
                ):
                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    grok_resp += chunk
            except KeyboardInterrupt:
                grok_resp = grok_resp or "(interrupted)"
            print("\n")

            # Phase 2 — Claude oversight: verify + critique
            print(f"  {LAPIS}◈ CLAUDE OVERSIGHT{RESET}  {SILV2}verifying...{RESET}")
            oversight_q = (
                f"Query: {raw}\n\n"
                f"Primary model ({prim_label}) produced:\n"
                f"{'─' * 50}\n"
                f"{grok_resp.strip()}\n"
                f"{'─' * 50}\n\n"
                "Verify this response. Start your reply with one of:\n"
                "  ✓ VERIFIED — if accurate and complete\n"
                "  ◈ IMPROVED — if you have additions/nuance\n"
                "  ✗ CORRECTED — if there are errors\n\n"
                "Then give your brief assessment. Corrections take priority."
            )
            sys.stdout.write(f"  {LAPIS}│{RESET}  {CREAM}")
            sys.stdout.flush()
            oversight_resp = ""
            try:
                for chunk in chat(
                    oversight_q, [],
                    "", None, False, "",
                    "", False, cfg["anthropic_key"],
                    force_provider="claude",
                ):
                    sys.stdout.write(f"{CREAM}{chunk}{RESET}")
                    sys.stdout.flush()
                    oversight_resp += chunk
            except KeyboardInterrupt:
                oversight_resp = oversight_resp or "(interrupted)"
            print("\n")
            full_response = (
                f"[{prim_label}]: {grok_resp.strip()}\n\n"
                f"[Claude Oversight]: {oversight_resp.strip()}"
            )

        else:
            # ── Normal single-model flow ─────────────────────────────────
            # Bare queries always hit Ollama first — local synthesis before
            # any external API call. Use  hey grok / hey claude / council
            # to explicitly bring in external providers.
            _ollama_first = not _force_provider
            if not _force_provider:
                _force_provider = "ollama"
                _route_label    = "CURSIV"
            else:
                _route_label = _force_provider.upper()
            _log_model = _force_provider

            if _cli_scan:
                _cli_scan.routing(_route_label)

            sys.stdout.write(f"  {GOLD}{BOLD}✦{RESET}  {GOLD}AI{RESET}  ")
            sys.stdout.flush()

            try:
                for chunk in chat(
                    raw,
                    _send_ctx,
                    cfg["api_key"],
                    None,
                    cfg["file_access"],
                    cfg["workspace"],
                    cfg["openai_key"],
                    cfg["confirm_mode"] == "confirm",
                    cfg["anthropic_key"],
                    force_provider=_force_provider,
                ):
                    combined = full_response + chunk
                    if WRITE_SENTINEL in combined:
                        display, raw_json = combined.split(WRITE_SENTINEL, 1)
                        leftover = display[len(full_response):]
                        if leftover:
                            sys.stdout.write(f"{GOLD}{leftover}{RESET}")
                            sys.stdout.flush()
                        full_response   = display
                        pending_payload = raw_json
                        break

                    sys.stdout.write(f"{GOLD}{chunk}{RESET}")
                    sys.stdout.flush()
                    full_response = combined

            except KeyboardInterrupt:
                full_response = full_response or "(interrupted)"

            print()   # newline after streamed response

            if _ollama_first and full_response and len(full_response.strip()) > 40:
                has_ext = cfg.get("api_key") or cfg.get("openai_key") or cfg.get("anthropic_key")
                if has_ext:
                    print(f"  {DIM}·  hey grok / hey claude / council to bring in external views{RESET}")
            print()

            # ── Update live status from response ─────────────────────────
            _old_xai    = cfg.get("xai_live")
            _old_openai = cfg.get("openai_live")
            _old_claude = cfg.get("claude_live")
            _fr = full_response
            if "[xAI auth error" in _fr:
                cfg["xai_live"] = False
            elif "xAI unavailable" in _fr or ("→" in _fr and "xAI" in _fr and "unavailable" in _fr):
                cfg["xai_live"] = False
            elif cfg.get("api_key") and not _force_provider and _fr and not _fr.startswith("*["):
                cfg["xai_live"] = True
            elif _force_provider == "grok" and _fr and "[No xAI" not in _fr:
                cfg["xai_live"] = True
            if "OpenAI unavailable" in _fr or ("[OpenAI error" in _fr and _force_provider != "openai"):
                cfg["openai_live"] = False
            elif _force_provider == "openai" and _fr and "[No OpenAI" not in _fr and "[OpenAI error" not in _fr:
                cfg["openai_live"] = True
            if "Claude unavailable" in _fr or ("[Claude error" in _fr and _force_provider != "claude"):
                cfg["claude_live"] = False
            elif _force_provider == "claude" and _fr and "[No Anthropic" not in _fr and "[Claude error" not in _fr:
                cfg["claude_live"] = True
            # Status change is reflected automatically in the next input separator

        # ── Handle pending write ─────────────────────────────────────────
        if pending_payload is not None:
            result        = _handle_pending_write(pending_payload, cfg)
            full_response = full_response.rstrip() + f"\n\n{result}"
            print(f"  {GOLD}{result}{RESET}\n")

        history.append({"role": "assistant", "content": full_response})

        # ── Session log + Obsidian livestream ────────────────────────────
        if raw and full_response:
            try:
                _session_append_cli(raw, full_response, _log_model)
            except Exception:
                pass
            try:
                _obs_livestream_cli(raw, full_response, _log_model)
            except Exception:
                pass
            # ── Quality score ─────────────────────────────────────────────
            _qs = None
            if _QS_OK and full_response and len(full_response.strip()) > 20:
                try:
                    _qs = _qs_score(
                        raw, full_response,
                        provider        = _log_model,
                        strand_hits     = _strand_hit_count,
                        guardian_clean  = True,
                    )
                    print(_qs_fmt(_qs))
                    print()
                except Exception:
                    pass

            # ── Active semantic memory — only auto-strand quality exchanges ─
            _qs_depth = (_qs or {}).get("depth", 100)
            if _STRAND_OK and len(full_response.strip()) > 40 and _qs_depth > 60:
                try:
                    _strand_save(
                        raw,
                        full_response,
                        tags=["live", "session"],
                        score=0.40,
                        territory_tag=_auto_territory(raw),
                        source="chat",
                        model=_log_model,
                    )
                except Exception:
                    pass


if __name__ == "__main__":
    main()

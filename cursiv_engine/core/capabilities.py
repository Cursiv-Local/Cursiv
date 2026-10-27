"""
What Cursiv can do -- one inventory, read by everything that talks about Cursiv
(U99): native answers ("does Cursiv have an updater?"), the self-knowledge prompt,
the persona's grounding for writing about Cursiv, custom agents, help and tests.

Three layers, kept apart on purpose:
  A. support  -- what the application supports (from this registry; each entry names
                 the modules and tests behind it, and tests/test_capabilities.py checks
                 that they exist);
  B. state    -- what is on or available right now, read live; a failed read is
                 "unknown", never "off" or "not supported";
  C. evidence -- what backs a statement: these records, a source excerpt actually
                 read this session (core/evidence_log.py), or nothing.

Rules every reader follows: an inactive feature is not a missing feature; a disabled
feature is not unimplemented; an implemented feature has not necessarily run; and
documentation is not runtime proof.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

SUPPORTED = "built in"
OPTIONAL = "optional (off until you turn it on)"
REMOVED = "removed"
NOT_SUPPORTED = "not something Cursiv does"


@dataclass(frozen=True)
class Capability:
    key: str
    name: str
    support: str
    summary: str
    online: str                         # how it relates to the internet
    words: tuple[str, ...]              # how people ask about it
    code: tuple[str, ...] = ()          # modules that implement it
    tests: tuple[str, ...] = ()         # tests that exercise it
    limits: str = ""
    state: Callable[[], str] | None = field(default=None, compare=False)


# ── live state readers (layer B): never raise, never guess ───────────────────

def _read(fn: Callable[[], str]) -> Callable[[], str]:
    def safe() -> str:
        try:
            return fn()
        except Exception:
            return "unknown (Cursiv couldn't read this setting just now)"
    return safe


def _offline() -> str:
    from . import netgate
    return "offline mode is ON: every connection off this computer is refused" if netgate.is_offline() \
        else "offline mode is off"


def _keys() -> str:
    from cursiv_engine.chat import keys
    from cursiv_engine.chat.status import KEY_NAMES
    saved = [name for f, name in KEY_NAMES if keys.saved_key(f)]
    return ("keys saved for: " + ", ".join(saved)) if saved else "no online AI keys are saved"


def _cloud() -> str:
    from cursiv_engine.chat.status import _cloud_on
    return "Cursiv Cloud backup is on" if _cloud_on() else "Cursiv Cloud backup is off"


def _web() -> str:
    from . import netgate
    return "automatic web search is on" if netgate.web_search_auto() else \
        "web search runs only when a message starts with search:"


def _updates() -> str:
    from . import netgate
    return "automatic update check is on" if netgate.update_check_auto() else \
        "automatic update check is off (Check for Updates is manual)"


def _local_model() -> str:
    from cursiv_engine.chat.status import local_models
    models = local_models(timeout=1.5)
    if models is None:
        return "the local AI engine (Ollama) isn't answering right now"
    return ("installed local models: " + ", ".join(models)) if models else "Ollama is running but has no chat model"


def _vault() -> str:
    from . import vault
    on = [r for r in vault.roots() if (r / vault.MARKER).exists()]
    return "encryption is set up on this computer" if on else \
        "no encrypted vault here (a Cursiv USB drive stays readable by design)"


def _agents() -> str:
    from cursiv_engine.agents import custom
    names = ["@" + a["name"] for a in custom.all_agents()]
    return ("custom agents: " + ", ".join(names)) if names else "no custom agents yet"


def _plugins() -> str:
    from . import plugins
    plugins.load_all()
    on = [n for n, s in plugins._status.items() if s.get("loaded")]
    return ("plugins on: " + ", ".join(on)) if on else "no plugins installed"


def _portable() -> str:
    import os
    return "running from a Cursiv USB drive" if os.environ.get("CURSIV_PORTABLE") == "1" else \
        "running from this computer's installation"


# ── the inventory (layer A) ──────────────────────────────────────────────────

CAPABILITIES: tuple[Capability, ...] = (
    Capability("local_ai", "Local AI chat", SUPPORTED,
               "Answers with an AI model on this computer through Ollama (qwen3:4b-instruct is the tested model).",
               "works offline once Ollama and a model are installed; installing them needs the internet once",
               ("local model", "local ai", "ollama", "offline ai", "runs locally", "local llm", "on your computer"),
               ("cursiv_engine/chat/local_provider.py", "cursiv_engine/core/ollama_host.py"),
               ("tests/test_ui_redesign.py",),
               "a 4B model can be wrong; check answers that matter", _read(_local_model)),
    Capability("online_ai", "Optional online AI providers", OPTIONAL,
               "Can use OpenAI, Claude, xAI Grok, Google Gemini or Groq when you add a key; the local model is tried "
               "first, keys are fallbacks and the way to read pictures.",
               "goes online only through a key you added, and never in offline mode",
               ("online ai", "cloud ai", "online model", "openai", "claude", "gemini", "groq", "grok", "online provider",
                "online services", "online service", "api key", "cloud provider", "chatgpt"),
               ("cursiv_engine/chat/cloud_providers.py", "cursiv_engine/chat/routing.py", "cursiv_engine/chat/keys.py"),
               ("tests/test_answer_check.py",),
               "what you send to a provider is handled under that provider's terms", _read(_keys)),
    Capability("cloud_backup", "Cursiv Cloud backup", OPTIONAL,
               "A backup AI used only when no local model is ready, if you turn it on.",
               "online when on; off by default", ("cursiv cloud", "cloud backup"),
               ("cursiv_engine/chat/cloud_providers.py",), (), "", _read(_cloud)),
    Capability("web_search", "Web search", OPTIONAL,
               "Looks things up on the web when a message starts with search: (or with automatic search turned on).",
               "online; refused in offline mode", ("web search", "search the web", "internet search", "browse",
                                                  "look it up online", "google"),
               ("cursiv_engine/chat/web_search.py", "cursiv_engine/core/web_cache.py"), (),
               "Cursiv doesn't browse on its own", _read(_web)),
    Capability("offline_mode", "Offline mode", SUPPORTED,
               "One switch that refuses every connection Cursiv makes off this computer.",
               "blocks everything online", ("offline mode", "offline", "airplane", "block the internet",
                                            "internet right now", "using the internet", "go online", "network"),
               ("cursiv_engine/core/netgate.py", "cursiv_engine/chat/status.py"), ("tests/test_help.py",),
               "it controls Cursiv's own connections; it can't see or stop other programs", _read(_offline)),
    Capability("updater", "Updates", SUPPORTED,
               "Check for Updates asks GitHub for the latest release. If there's a newer one, Cursiv shows the notes, "
               "downloads the installer only when you click, checks it against the owner-signed release manifest "
               "(size and SHA-256) before running it, and the installer replaces the program. An automatic check "
               "after login is a setting, off by default. A Cursiv USB drive isn't updated in place.",
               "online when you check or download; refused in offline mode",
               ("update", "updates", "updater", "update mechanism", "new version", "upgrade", "auto update",
                "self-update", "self update"),
               ("launcher/cursiv_launcher.py", "launcher/update_security.py", "cursiv_engine/core/release_identity.py"),
               ("tests/test_signing.py",),
               "Cursiv never changes its own code: updates are whole new releases you choose to install; the "
               "installer has no Windows publisher signature (Authenticode) and the Mac app isn't notarized",
               _read(_updates)),
    Capability("dependencies", "What Cursiv depends on", SUPPORTED,
               "Ollama (the local AI engine, installed by Setup) and an AI model for local chat; Python packages "
               "bundled in the installer (PyQt6, cryptography, bcrypt, numpy, Pillow, psutil, pypdf, pywin32, and the "
               "openai/anthropic client libraries for optional keys); optional extras installed on demand (voice: "
               "faster-whisper; training: torch and related). GitHub hosts releases; online AI providers are used "
               "only with your keys.",
               "installing Ollama, models and updates needs the internet; everyday local use doesn't",
               ("dependencies", "dependency", "depend on", "requirements", "third-party", "third party", "libraries",
                "packages", "external"),
               ("requirements.txt", "launcher/setup_dialog.py"), (), "", None),
    Capability("encryption", "Encryption of your data", SUPPORTED,
               "On a computer, conversations, memories, saved notes, the field notebook (entries, photos, team logs) "
               "and custom agents are encrypted with a passphrase you choose at first start.",
               "local only", ("encrypt", "encryption", "passphrase", "vault"),
               ("cursiv_engine/core/vault.py", "cursiv_engine/core/vault_migration.py", "launcher/encryption_dialog.py"),
               ("tests/test_data_encryption.py", "tests/test_notebook_encryption.py"),
               "a lost passphrase can't be recovered; a Cursiv USB drive stays readable; reports, exports and "
               "workspace files aren't encrypted; the login is a lock, not encryption", _read(_vault)),
    Capability("memory", "Memory", SUPPORTED,
               "Saves facts you ask it to remember, learns some automatically (you can turn that off), and recalls "
               "them by meaning; you can see, correct and forget them.",
               "local only", ("memory", "remember", "memories", "forget", "recall"),
               ("cursiv_engine/memory/semantic.py", "cursiv_engine/memory/intents.py"),
               ("tests/test_memory_intents.py",),
               "recall can miss a saved fact; remembering doesn't retrain the model", None),
    Capability("notebook", "Field notebook", SUPPORTED,
               "Records observations with measurements, sample IDs, places and photos in a hash-chained log; "
               "searches, averages, reports, signed exports and team sharing without internet. "
               "The desktop previews supported ordinary measurement descriptions before saving and asks for missing units.",
               "local only (phone and team transfer use files or local Wi-Fi)",
               ("field notebook", "notebook", "field log", "observations", "log site", "samples"),
               ("cursiv_engine/core/fieldlog.py", "cursiv_engine/core/field_recall.py", "cursiv_engine/core/fieldsync.py"),
               ("tests/test_notebook_integration.py", "tests/test_u106_actions.py", "tests/test_u106_recall.py"),
               "project labels are not isolated project scopes; only supported phrasing is parsed without the model", None),
    Capability("calculations", "Calculations worked out in code", SUPPORTED,
               "Unit conversions, speed and time, flow, dilutions, statistics, dates and arithmetic are worked out by "
               "Cursiv's code, not the AI model, and say so.",
               "local only", ("calculat", "convert", "conversion", "maths", "math", "arithmetic"),
               ("cursiv_engine/core/native_answers.py", "cursiv_engine/core/fieldcalc.py", "cursiv_engine/core/calc.py"),
               ("tests/test_file_claims.py",), "only clear question shapes; others go to the model", None),
    Capability("documents", "Your documents", SUPPORTED,
               "Imports protocols and other documents through Research Files and answers from them with page references.",
               "local only", ("documents", "pdf", "protocol", "import a document"),
               ("cursiv_engine/core/documents.py", "launcher/research_workspace.py"),
               ("tests/test_documents.py", "tests/test_u106_research_ui.py"),
               "the imported library is shared across workspaces, not isolated by project", None),
    Capability("files", "Files in your workspace", SUPPORTED,
               "Reads, lists, searches, creates and (with your approval) changes text files in one folder you choose "
               "and turn file access on for. It never deletes files.",
               "local only", ("files", "file access", "workspace", "read a file", "write a file", "folder"),
               ("cursiv_engine/core/file_access.py", "cursiv_engine/core/workspace.py"),
               ("tests/test_file_access.py", "tests/test_file_claims.py"),
               "only inside the chosen workspace; never Cursiv's own data or keys", None),
    Capability("agents", "Custom agents", SUPPORTED,
               "Specialists you create with a name and a job (agent new …, @name, agents ask). Today an agent can only "
               "talk and receive the read-only notebook, document or calculation evidence its profile permits. "
               "It cannot run tools or change records.",
               "uses the same engine as chat", ("agent", "agents", "custom agent", "specialist"),
               ("cursiv_engine/agents/custom.py",), ("tests/test_agents_vault.py",),
               "giving agents limited tools is planned, not built", _read(_agents)),
    Capability("plugins", "Plugins and Forge", OPTIONAL,
               "Approved plugins add commands and tools; evolve <idea> writes one. Each plugin call runs in its own "
               "process that can't reach the network, start programs, load native code or open files outside its folder.",
               "plugins can't go online", ("plugin", "plugins", "forge", "evolve", "extensions"),
               ("cursiv_engine/core/plugins.py", "cursiv_engine/core/plugin_runner.py", "cursiv_engine/coding/forge.py"),
               ("tests/test_plugin_isolation.py",),
               "process separation, not an operating-system sandbox: review a plugin before approving it",
               _read(_plugins)),
    Capability("coding", "Coding help", SUPPORTED,
               "codex gives coding help with playbooks, worked examples and error diagnosis, using local coding models "
               "when installed, and can test-run Python it wrote.",
               "local when coding models are installed", ("coding", "code help", "codex", "programming", "debug"),
               ("cursiv_engine/coding/brain.py", "cursiv_engine/coding/runner.py"), (),
               "answers can be wrong; test code before relying on it", None),
    Capability("translation", "Translation", SUPPORTED, "translate <text> into <language>.", "local model",
               ("translate", "translation", "babel"), ("cursiv_engine/agents/babel_agent.py",), (), "", None),
    Capability("images", "Pictures", OPTIONAL,
               "Reads pasted pictures with an online key or the local gemma3 vision model; making new images needs an "
               "online key.", "reading can be local; making images is online",
               ("image", "images", "picture", "photo", "vision"), ("launcher/command_media.py",), (), "", None),
    Capability("voice", "Voice input", OPTIONAL, "Speech to text on this computer (faster-whisper, installed on demand).",
               "local", ("voice", "speech", "microphone", "dictate"), ("cursiv_engine/agents/voice_agent.py",), (),
               "", None),
    Capability("phone", "Phone notebook and phone chat", OPTIONAL,
               "cursiv.us/notebook works offline on a phone after its first load and sends entries to the computer by "
               "file or local Wi-Fi; cursiv.us/app is a separate phone chat that can link to the computer.",
               "the pages load from the internet once; the link is online", ("phone", "mobile"),
               ("cursiv_engine/core/phone_receive.py", "launcher/phone_link.py"), ("tests/test_phone_receive.py",),
               "", None),
    Capability("usb", "Cursiv on a USB drive", SUPPORTED,
               "Make a Cursiv USB copies the program, Ollama and models to a drive that runs on another Windows PC; "
               "data moves between drive and computer (decrypted on the drive, encrypted again on a computer).",
               "local", ("usb", "flash drive", "portable", "thumb drive"),
               ("launcher/usb_maker.py", "launcher/usb_sync.py", "launcher/portable.py"),
               ("tests/test_usb_sync.py", "tests/test_usb_end_to_end.py"),
               "a drive stays readable; use drive encryption if it could be lost", _read(_portable)),
    Capability("self_inspection", "Looking at itself", SUPPORTED,
               "self map / self source / self read show Cursiv's own code and docs; self prompt shows what was sent for "
               "the last answer; self stores shows what is saved and where.",
               "local", ("self source", "source code", "own code", "self prompt", "self stores", "self map"),
               ("cursiv_engine/core/self_source.py", "cursiv_engine/core/last_turn.py", "cursiv_engine/core/self_stores.py"),
               ("tests/test_self_awareness.py",),
               "seeing code doesn't prove a feature ran", None),
    Capability("training", "Local fine-tuning", OPTIONAL,
               "An optional manual tool trains a small adapter on examples you collected (installs extra packages).",
               "installing packages needs the internet", ("train", "training", "fine-tune", "fine tune", "lora"),
               ("cursiv_engine/training/lora_trainer.py",), (), "Cursiv never retrains itself automatically", None),
    # Removed: say so, never "it doesn't exist and never did".
    Capability("family_letters", "Family letters and the legacy vault", REMOVED,
               "Removed in U97; letters and data already saved on a computer were not deleted.", "n/a",
               ("family letters", "sealed letters", "legacy vault", "write to"), (), (), "", None),
    Capability("council", "The council", REMOVED, "Removed in U97; agents ask <question> asks your own agents.", "n/a",
               ("council",), (), (), "", None),
    # Things Cursiv does not do -- writing ABOUT them is fine.
    Capability("publish", "Posting, sending or calling for you", NOT_SUPPORTED,
               "Cursiv doesn't post to social media, send email or messages, or make calls. It can write the post, "
               "email or message for you to copy and send yourself.",
               "n/a", ("post to", "publish", "send an email", "send a message", "tweet for me", "post on x",
                       "make a call", "send it for me"), (), (), "", None),
    Capability("self_modify", "Changing its own code", NOT_SUPPORTED,
               "Cursiv doesn't modify its own program. New abilities come as plugins you approve or as releases you "
               "choose to install.", "n/a", ("modify itself", "modify its own", "self-modif", "self modif",
                                             "rewrite its own code", "change its own code"), (), (), "", None),
)

BY_KEY = {c.key: c for c in CAPABILITIES}


# ── reading the inventory ────────────────────────────────────────────────────

def match(text: str) -> list[Capability]:
    """Capabilities a question is about, best match first."""
    low = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    scored = []
    for c in CAPABILITIES:
        hits = [w for w in c.words if w in low]
        if hits:
            scored.append((max(len(w) for w in hits), c))
    return [c for _, c in sorted(scored, key=lambda x: -x[0])]


def describe(c: Capability, *, live: bool = True) -> str:
    lines = [f"**{c.name}** — {c.support}. {c.summary}"]
    if c.online and c.online != "n/a":
        lines.append(f"Internet: {c.online}.")
    if live and c.state is not None:
        lines.append(f"Right now: {c.state()}.")
    if c.limits:
        lines.append(f"Limits: {c.limits}.")
    if c.code or c.tests:
        lines.append("Backed by: " + ", ".join(f"`{p}`" for p in c.code + c.tests) +
                     ". (These show the code and tests exist, not that the feature ran just now.)")
    return "\n".join(lines)


SOURCE = "\n\n*[Sources: Cursiv capability records and live settings (no AI model)]*"

_ASKS_ABOUT_CURSIV = re.compile(
    r"(?i)\b(?:does|do|can|is|are|has|have|will|could)\s+(?:cursiv|you|it|this app|the app)\b"
    r"|\b(?:cursiv(?:'s)?|your)\s+(?:support|have|has|offer|use)\b"
    r"|\b(?:is|are) there (?:a |an |any )?\w[\w\s-]{0,40}\bin cursiv\b")


_UNLISTED = re.compile(r"(?i)\b(?:capabilit\w*|feature|tool|ability)\b.{0,60}\b(?:isn'?t|not|aren'?t)\b.{0,30}"
                       r"\b(?:represented|listed|in your|in the|recorded|known)\b")


def answer(question: str) -> str | None:
    """A model-free answer to "does Cursiv have / support / can it …" about a known capability."""
    q = (question or "").strip()
    if _UNLISTED.search(q):
        return ("If a capability isn't in Cursiv's records, Cursiv treats it as unknown: it won't claim it can do it, "
                "and it won't claim it definitely can't either — the records may simply not cover it. What the "
                "records do cover: " + ", ".join(c.name.lower() for c in CAPABILITIES if c.support != REMOVED) +
                ". Ask \"does Cursiv have …?\" about any of them, or self map <words> to see where it lives in the code."
                + SOURCE)
    if len(q) > 300 or not _ASKS_ABOUT_CURSIV.search(q) or re.match(r"(?i)\s*how\b", q):
        return None                       # "how does Cursiv work offline?" keeps its reviewed workflow answer
    existence = re.search(r"(?i)\b(?:have|has|support|supports|offer|include|come with|got|use|uses|is there|"
                          r"are there|work offline|go online)\b|"
                          r"\b(?:post|publish|tweet|send|e-?mail|call|text)\b.{0,30}\bfor me\??\s*$", q)
    short_can = re.fullmatch(r"(?i)\s*(?:can|could|will)\s+(?:cursiv|you|it)\s+[\w-]+(?:\s+[\w-]+)?\s*\?*\s*", q)
    if not (existence or short_can):
        return None                       # "can you translate 'hola' …" is a request, not a question about Cursiv
    if re.search(r"(?i)\b(?:write|draft|compose|create|make|give me|explain how|tell me how|teach)\b", q) and \
            not re.search(r"(?i)\b(?:does|do|can|is there)\b.{0,20}\b(?:cursiv|you)\b.{0,20}\b(?:have|support)\b", q):
        return None                       # a request to make something, not a question about Cursiv
    found = match(q)
    if not found:
        return None
    parts = [describe(c) for c in found[:2]]
    return "\n\n".join(parts) + SOURCE


def facts_block(limit: int | None = None, *, short: bool = False) -> str:
    """The inventory as short lines, for the self-knowledge prompt and for writing about Cursiv.
    short=True: one brief line each, for an ordinary chat prompt on a small model."""
    if short:
        return "\n".join(f"- {c.name} ({c.support}): {c.summary.split('. ')[0].rstrip('.')}."
                         for c in CAPABILITIES if c.support != REMOVED)
    rows = []
    for c in CAPABILITIES[:limit]:
        rows.append(f"- {c.name}: {c.support}. {c.summary}" + (f" Internet: {c.online}." if c.online != "n/a" else "")
                    + (f" Limits: {c.limits}." if c.limits else ""))
    return "\n".join(rows)


def live_block() -> str:
    """Layer B for prompts: each state reading, with 'unknown' where it couldn't be read."""
    rows = [f"- {c.name}: {c.state()}" for c in CAPABILITIES if c.state is not None]
    return "\n".join(rows)


def agent_permissions(agent: dict) -> str:
    """What a custom agent may use. Enforced by application code: today agents get no tools."""
    reads = [r for r in (agent.get("reads") or []) if r in ("notebook", "documents", "calculations")]
    if reads:
        # U101 starter profiles: Cursiv's code shows them these, read only (agents/profile_context.py).
        shown = {"notebook": "your field notebook's records (read only)", "documents": "matching passages from your "
                 "imported documents (read only)", "calculations": "calculations worked out by Cursiv's code"}
        return ("Cursiv may supply this conversation, saved profile teaching and your writing style, plus " + ", ".join(shown[r] for r in reads) + ". It cannot save, change, correct "
                "or delete anything, read other files, search the web, or use any other tool.")
    return ("This agent can only talk, using this conversation, your writing style and any teaching saved in its profile. "
            "It cannot read, create, change or delete files, use the field notebook, search the web, "
            "or use any other Cursiv tool. A saved tools field grants no powers. "
            "Automatic personal-memory recall is withheld from research profile runs.")

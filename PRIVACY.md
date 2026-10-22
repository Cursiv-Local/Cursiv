# Privacy: what stays on this computer, and what can leave it

Cursiv runs on your computer. This page lists every way it can connect to anything
outside it, so you can check rather than trust. The same summary, with your current
settings, is in Cursiv under **Settings → Privacy & internet**.

**Scope:** This document describes the desktop application. For the website, Phone AI
Companion, public board, sealed letters, and other server-backed services, see the
[Cursiv Website Privacy Policy](https://cursiv.us/privacy/). Those services have separate
data flows and are not covered by the desktop-only statements below.

## Stays on this computer, always

- Your conversations and memories.
- The field notebook: observations, sample IDs, corrections, exports.
- Your imported documents (PDFs and text files) and their search index.
- Your login (username, password hash, security answers).
- This installation's signing key for field records (~/.cursiv/device_key.json, stored protected).
  Only its public half goes out, inside shares and exports, so others can check your signature.
- The offline reference (first aid, survival, science) and the calculations
  (units, coordinates, distance, dilutions, statistics, bleach doses).
- The AI model itself, once downloaded: it runs on this computer through Ollama.

None of these are uploaded anywhere by Cursiv. Team sync moves only the field log,
and only to a folder or USB drive you choose. Memories and documents never sync.

## Can leave this computer, only when you turn it on

Each of these is off, or never used, unless you act:

| What | When it connects | What is sent |
|---|---|---|
| **Setup downloads** | When you install Ollama or a model in the Setup window | Download requests to ollama.com; nothing about you |
| **Web search** | When you type `search: …`, or turn on automatic web search (off by default) | Your search words, to the search provider |
| **Reading a web page** | When you type `pull <address>` | A request for that page |
| **Cloud AI keys** (OpenAI, Anthropic, xAI, Groq, Gemini) | Only if you saved a key, **and** you choose that AI by name, paste an image, give the AI file-writing access, or no local model is ready | That conversation, to that company |
| **Cross-check** | Only when you click Cross-check, pick a company you saved a key for, read exactly what will be sent, and press Send. Never automatically; refused in offline mode | That one question and that one answer, with the reviewer's instructions, to the company you picked. No memories, documents, field notes, other turns or files. The review is shown under the answer and isn't kept in the conversation |
| **Cursiv Cloud** | Only if you turn it on in Settings, and then only when no local model is ready | That message, to Cursiv's server (cursiv.winklers-llc.com) |
| **Update check** | When you click Check for updates, or turn on automatic checks (off by default) | A request to GitHub for the latest release |
| **Problem report** | Only when you click Report a problem | Cursiv's error logs (never chats, letters or keys) |
| **Fleet heartbeat** (developer feature) | Only if the `CURSIV_RELAY_URL` and `CURSIV_FLEET_TOKEN` environment variables are set on that computer; never on a normal install | The machine's name, user name, version and "active", once a minute, to that relay |

The local model answers first whenever it can. A saved key is a fallback, not the
default: a turn the local model answered is also checked locally, never by a cloud AI.

## What offline mode blocks

Turn it on with `offline on` or the switch in Settings → Privacy & internet (click the badge at the top of the chat to get there).
A Cursiv USB starts with it on.

- **Every connection off this computer is refused**, at the socket level, for the
  whole program, including anything not listed above. Only this computer itself
  (the local model) can be reached.
- Web search, reading pages, Cursiv Cloud and update checks are refused, not attempted.
- Saved cloud keys stay saved but aren't used; the local model answers.
- Model downloads are refused.

Checked, not just claimed: `scripts/offline_demo.py` runs 15 tasks on a fresh copy with
every outside connection refused and counts the attempts (`OFFLINE-DEMO.md`: 15 of 15
pass, 0 attempts). `scripts/net_audit.py` logs every connection a fresh install makes.

## What Cursiv can't protect

- Cursiv's login keeps people at your keyboard out. It is not encryption: anyone who can
  open this computer's files can read Cursiv's data, like your other documents. Saved
  AI keys are the exception (encrypted for your Windows account, or kept in the macOS Keychain).
  Portable copies deliberately keep usable keys readable; legacy keys or a
  platform-protection failure can also leave plaintext. The
  [threat model](docs/THREAT-MODEL.md) records these limits. Conversations and
  memories have no app-level encryption; an optional migration is separately planned.
- A private copy on a USB drive (made with "include my memories, keys and settings") holds
  your data readable, so it can run on other PCs. Keep that drive safe.
- When you use a cloud AI or web search, that company's own privacy policy applies to
  what you send it.

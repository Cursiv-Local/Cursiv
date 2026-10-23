# Cursiv — how it's built

Cursiv is a desktop app for Windows, with an early Apple Silicon Mac build,
written in Python (PyQt6). It talks to a local
AI engine (Ollama) first and to online providers only when the person has
added a key. This page explains the code layout, how a message is answered,
where data lives, and how to run, build and release it.

---

## Repository layout

| Folder | What's in it |
|---|---|
| `launcher/` | The desktop app: main window, chat panel, tray menu, dialogs (Setup, Settings, Training Data, USB maker…), login, updater. `main.py` is the entry point. |
| `cursiv_engine/` | Permanent engine package: core logic, model adapters, memory and field-notebook backends. |
| `installer/` | Inno Setup script (`cursiv_setup.iss`) that wraps the build into `Cursiv-Setup-<version>.exe`. |
| `scripts/` | `build.bat` (PyInstaller), `package.bat` (installer), `verify_build.bat`, `seal_family_letters.py`. |
| `website/` | The public website and phone web app (cursiv.us). |
| `cloudflare/` | The Cloudflare Worker behind the website and phone app, plus `publish.mjs` to deploy it. |

### Inside `cursiv_engine/`

| Package | Job |
|---|---|
| `ui/chat_app.py` | Compatible chat entry points, configuration and legacy turn records; passes explicit runtime services to implementation modules. No Qt interface. |
| `chat/` | Context/uploads, phase orchestration, routing, local/cloud/provider-tool adapters, streaming/completion, saved keys and web search. See [ARCHITECTURE.md](ARCHITECTURE.md) for exact module boundaries. |
| `core/` | Phases (`phases.py`), speed tuning for small GPUs and free keys (`speed.py`), self-knowledge (`selfknow.py`), read-only computer tools (`tools.py`), plugins / Cursiv Forge (`plugins.py`), talking style (`style.py`), strand memory archive (`strand_store.py`), constitution. |
| `memory/` | Semantic memory (find by meaning with `nomic-embed-text`, keyword fallback), project memory, session logs. |
| `council/` | The advising council behind `council <question>`: seats answer in parallel, synthesizers combine them. |
| `agents/` | Custom agents (`agent new …`), Babel translation, coding agent, offline queue, reference brain, voice. |
| `coding/` | The coding brain: playbooks, worked examples, error diagnosis, run-and-fix sandbox, `evolve` plugin writer. |
| `guardian/` | Login (bcrypt), security questions, owner mode and protected paths. Shared filesystem mutations deny guardian/login/key targets. Login is a front-door lock, not data encryption; installed keys use platform protection where available (see [threat model](docs/THREAT-MODEL.md) for plaintext exceptions). |
| `training/` | LoRA training (`lora_trainer.py`) and merging the adapter into Ollama (`ollama_merge.py`). |
| `family/`, `postal/` | Sealed letters: per-person letters that open with a name and birth date, and signed letters between people. |
| `council/cursiv_facts.md`, `codex/system_prompt.md` | What Cursiv knows about itself and its persona. Keep the fact sheet accurate when features change. |

---

## How a message is answered

1. **`launcher/chat_panel.py`** takes the text from the chat box.
2. **`launcher/chat_commands.py`** checks for commands first (`remember …`, `council …`, `image …`, `evolve …`, key commands, …). Commands return their answer directly.
3. Anything else goes to **`chat_app.chat()`**, which:
   - runs the **8 phases** (`core/phases.py`): notices stress or a crisis (shows help lines first), recalls memories, picks a route and answer shape, checks connectivity;
   - builds the prompt from the persona, the fact sheet, the person's memories and project notes;
   - streams the answer from the first available model via **`cascade_stream()`**.
4. Deterministic evidence checks finish in the foreground worker. The desktop
   enables input before optional local model review starts. Fast mode permits one
   short verdict on eligible turns; full mode permits one constrained rewrite
   and recheck. Results are labeled follow-ups, with stale-result cancellation
   and copied evidence. Missing/failed checks cannot establish a verified result.
   See [verification policy](docs/VERIFICATION-POLICY.md) and the
   [review implementation and measurements](docs/ASYNC-ANSWER-REVIEW.md).
5. Policy-controlled background retention may learn selected facts; pending/failed checks
   do not authorize assistant-derived facts. Existing native receipts and formats
   remain unchanged.

`chat/provenance.py` formats source labels without receiving the answer text.
Grounding state records memory surviving final prompt assembly; the source line,
evidence checker and deferred reviewer use that supplied record. Explicit
Cross-check uses a 400-token provider cap; ordinary provider budgets are unchanged.
The [trust follow-up](docs/TRUST-BOUNDARY-FOLLOWUP.md) records new parser,
failed-file-memory and damaged-recall safeguards and draft release wording.

**Model order:** the local Ollama model first whenever it has one → paid keys the person added (xAI, OpenAI, Claude) → Groq → Gemini → Cursiv Cloud (off unless turned on, and only when no local model is ready). Pasted images skip the local chat model (it can't see them); with file access on and a paid key, the tool-using paid provider goes first because only it can write files. Every reply ends with "Answered by …", added by the code. Local-only use always works; keys are fallbacks, never requirements.

**Images:** reading uses Claude/GPT-4o keys, then a free Gemini key, then a local Ollama vision model (`gemma3:4b`). Making images uses a paid OpenAI key or a free Cloudflare Workers AI account (FLUX.1-schnell).

---

## Where data lives

| What | Where |
|---|---|
| Keys, settings, memories, training data | `.cursiv\` next to the program (`<install>\_internal\.cursiv\`) |
| Conversations, agents, plugins, projects, login | `%USERPROFILE%\.cursiv\` |
| AI models | Ollama's folder (`%USERPROFILE%\.ollama\models`) |

Nothing in these folders is part of the repository or the installer. On a **Cursiv USB** (`launcher/usb_maker.py`), `launcher/portable.py` points the home folder, the models and Ollama at the drive at startup, so everything stays on the drive.

### Optional conversation and memory encryption (unreleased source)

Off by default. Close Cursiv, then run `python launcher/main.py --encrypt-data`
from source, or `Cursiv.exe --encrypt-data` after packaging this source. On macOS
run the bundle's `Contents/MacOS/Cursiv --encrypt-data` executable. The startup
dialog lists coverage and asks for a separate passphrase twice. Normal startup
requires that passphrase before loading private stores or launching background work.
There is no chat command that accepts the passphrase. Login recovery cannot recover it.

`core/vault.py` uses the already required `cryptography` library: Fernet authenticated
encryption, with a fresh 16-byte salt and scrypt (N=131072, r=8, p=1, 32-byte key).
No derived key or passphrase is saved. JSON/JSONL bytes, record IDs and ordering
remain intact inside path-bound encrypted envelopes. Keys are held for the process
lifetime; close Cursiv to discard decrypted application caches. Python does not
guarantee memory zeroization. Per-file plaintext is limited to 64 MB.

Covered in each active data root: conversations, session logs, semantic facts and
their removed/unreadable copies, embeddings, saved strands, project/style notes,
curiosity/presence records, coding/council memory, related backups and old temporary
files with recognized names. A full inventory, exclusions and recovery instructions
are in [the encryption guide](docs/ENCRYPTION-MIGRATION-PLAN.md).
`data-vault.json` stores only salt, a password check and migration state;
`.vault-recovery/` contains authenticated encrypted copies of the original bytes.
Keep both with the records and copy them in backups/portable private kits.
The `.vault-lease` file is process state and is excluded from kit copies.

Notebook records/photos, workspace/imported files, explicit exports/training data,
API keys/login settings and logs keep their existing storage. Historical external
copies, OneDrive versions and recoverable disk remnants remain sensitive.
Use OS/full-drive encryption when those are in scope. See [threat model](docs/THREAT-MODEL.md).

---

## Run from source

Python 3.11+ on Windows.

```bash
pip install -r requirements.txt
python launcher/main.py
```

Install [Ollama](https://ollama.com) and pull a model (`ollama pull qwen3:4b-instruct`), or use the Setup window, or add a free Gemini/Groq key.

---

## Build the installer

You need PyInstaller (in `requirements.txt`) and [Inno Setup 6](https://jrsoftware.org/isdl.php).

1. Bump `launcher/cursiv_launcher.py` (`_CURRENT_VERSION`), `installer/cursiv_setup.iss` (`AppVer`, `OutputBaseFilename`) and `cursiv_engine/core/selfknow.py` (`VERSION`) together, using an unused higher suffix such as `3.14-U85`.
2. Run the regression checks in isolated data, commit reviewed source and tag that exact commit. Use a clean environment containing only `requirements.txt`; retain the exact dependency list.
3. Run `py -3.13 scripts/build_release.py v3.14-U85`, substituting the new tag for a future release. It builds a temporary tagged checkout, requires the frozen full-window self-test, compiles Inno Setup and stages identical versioned/latest installers plus SHA-256 checksums in `installer/Output/`.

Working-tree build scripts remain useful for development, but the release
builder uses the tag so unrelated or uncommitted files cannot enter an installer.
See [U85 verification](docs/U85-RELEASE-VERIFICATION.md) for actual source,
package, hosted CI, model benchmark and public-download evidence.

## Release an update

The updater reads `https://api.github.com/repos/Cursiv-Local/Cursiv/releases/latest`.
It requires a higher version and online checks to be allowed. A source push alone
does not update installed copies. Prepare the release as a draft:

```bash
gh release create v3.14-U85 installer/Output/Cursiv-Setup-3.14-U85.exe installer/Output/Cursiv-Setup-latest.exe installer/Output/SHA256SUMS.txt --title "Cursiv v3.14-U85" --notes-file docs/RELEASE-U85.md --draft --verify-tag --repo Cursiv-Local/Cursiv
```

Upload the same installer twice: once with its version name and once as `Cursiv-Setup-latest.exe`. The README's download button and the website link to `releases/latest/download/Cursiv-Setup-latest.exe`; asset links are filename-exact, so without the stable name every download button breaks on the next release.

Copy the builder's versioned checksum file to `SHA256SUMS.txt` before uploading.
Run the existing tagged Mac workflow to attach its DMG, identical
`Cursiv-mac-latest.dmg` alias and `SHA256SUMS-mac.txt`. Review CI, frozen checks,
raw benchmark failures and both artifact hashes before making the draft latest.
Publishing also triggers a Mac workflow: if the verified Mac assets are already
attached, stop that redundant run before it rebuilds/overwrites them. Record the
successful tagged run separately from this intentional cancellation.

## Publish the website

```bash
node cloudflare/publish.mjs
```

It copies the allow-listed pages from `website/` into `cloudflare/dist/` and runs `wrangler deploy`. Use `--build-only` to build without deploying.

---

## Optional extras

- **LoRA training** needs `torch transformers peft accelerate datasets` in a normal (non-bundled) Python. The Training Data window checks for them and installs them in a visible terminal. CPU training works but is slow (roughly 6 minutes per example per epoch on a typical CPU).
- **Voice** uses `faster-whisper` and `sounddevice` when installed.

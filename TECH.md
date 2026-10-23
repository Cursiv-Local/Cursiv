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

On macOS, engine data uses `~/Library/Application Support/Cursiv`; home data
remains in `~/.cursiv`. `CURSIV_APP_DATA` explicitly overrides engine data locations.
Installed Windows can also retain a legacy program-level `.cursiv` copy; encryption
inventories that active location too. These paths do not depend on the package name.

Nothing in these folders is part of the repository or the installer. On a **Cursiv USB** (`launcher/usb_maker.py`), `launcher/portable.py` points the home folder, the models and Ollama at the drive at startup, so everything stays on the drive.

### Optional conversation and memory encryption

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

Use Python 3.13 for the locked release/test environment on Windows.

```bash
pip install -r requirements.txt
python launcher/main.py
```

Install [Ollama](https://ollama.com) and pull a model (`ollama pull qwen3:4b-instruct`), or use the Setup window, or add a free Gemini/Groq key.

---

## Feature behavior and controls

| Area | Behavior and deeper documentation |
|---|---|
| Field notebook | Original measurements are preserved; corrections append a new record with a reason. SHA-256 chains detect changed/reordered records, and signed exports identify the signing device. CSV, JSON, GeoJSON and printable reports are supported. Camera time/GPS are retained when available; the app does not provide live GPS. [Notebook integration](docs/FIELD-NOTEBOOK-INTEGRATION.md), [verified local actions](docs/VERIFIED-LOCAL-ACTIONS.md). |
| Documents | Imported protocols/SOPs can supply page references. Document-only mode declines uncovered questions, with the documented emergency exception. [Claim evidence](docs/CLAIM-EVIDENCE.md). |
| Calculations | Code handles units, coordinates/UTM, distance/bearing, dilutions, statistics, rates/durations, bleach doses and the lightning waiting rule. A matching native calculation has an application-owned receipt; this is not medical certification. [Native boundaries](docs/NATIVE-TRUST-BOUNDARIES.md). |
| Team sharing | Signed notebook chains move by USB/shared folder. Imports retain separate device chains and report conflicts rather than overwriting observations. [Phone notebook and transfer](docs/PHONE-NOTEBOOK.md). |
| Personal features | Settings → Appearance → Show personal features exposes older letters/vault, council, coding and builder tools. Current source also gates typed letter/vault commands and dialog shortcuts; it retains existing data/backends. [Ownership map](ARCHITECTURE.md). |

### Memory, permissions and conversation history

`remember <fact>` saves an explicit fact. `memory learn on / off` controls automatic
selection of lasting facts; it does not retrain the model. `memory status` reports
stored-record/learning state. Dated recall, such as “what do you remember from the
past two weeks”, reports selected stored facts and IDs. Dates describe when facts
were saved, not necessarily when events happened. `save this` keeps a saved note.

Turn limits and conversation autosave are separate. “Don't save memories” blocks
memory formation for that turn; it does not disable the existing conversation-save
setting. Talk-only turns block tools; read-only turns allow authorized reads while
blocking writes. A configured workspace or enabled file flag does not establish
that a particular file operation succeeded. Native receipts establish execution;
model descriptions do not. [Grounded memory](docs/GROUNDED-CHAT-REPAIR.md),
[restricted-turn fixes](docs/U82-RESTRICTED-TURN-REPAIR.md),
[workspace follow-up](docs/LIVE-TRANSCRIPT-GAPS.md).

### Answer review and source labels

| Command | Optional local-model review |
|---|---|
| `check off` | Disabled; deterministic code checks remain active. |
| `check fast` | Default: ordinary turns skip model review; eligible turns can receive a short follow-up review. |
| `check full` | Bounded review, with a constrained rewrite/recheck when warranted. |

The draft finishes before deferred review. Progress indicates an actual reviewer
call; a missing/failed check cannot establish verification. Source labels describe
application-supplied references, documents, calculations, memory context or confirmed
execution. A memory-context label does not establish that the model used or verified
that fact. [Review policy](docs/VERIFICATION-POLICY.md),
[timing/cancellation](docs/ASYNC-ANSWER-REVIEW.md),
[feedback and receipts](docs/CHAT-FEEDBACK.md),
[rendering measurements](docs/CHAT-RENDERING-PERFORMANCE.md),
[source boundaries](docs/TRUST-BOUNDARY-FOLLOWUP.md).

### Phone and portable use

**Phone notebook:** open [cursiv.us/notebook](https://cursiv.us/notebook) online
once before offline capture. Export the file, then use Field Notebook → Import or
`field log import <file>` on the laptop. The phone notebook has no AI chat; records
live in browser storage and can be cleared. Export regularly. Browser checks were
performed in desktop Chromium; real iPhone/Android testing remains separate.
[Phone instructions and limits](docs/PHONE-NOTEBOOK.md).

**Phone photo chat:** [cursiv.us/app](https://cursiv.us/app) is a separate online
photo/text chat page. It uses the website's AI providers and requires internet.
Device linking can share conversations with the desktop. It is not the offline
capture notebook. [Website privacy policy](https://cursiv.us/privacy/).

**Windows USB/SSD:** choose Make a Cursiv USB… from the tray menu. It copies the
app, Ollama and selected installed models. Run Start Cursiv from the drive on
another Windows PC. A complete kit can be about 30 GB depending on models; the
existing guidance is a USB 3 drive/SSD of at least 64 GB, formatted as exFAT.
Fresh kits omit private records/keys/settings. Explicitly including them can copy
readable API keys for use on other PCs. Optional encrypted conversation/memory
stores in current source remain encrypted and require their passphrase; the
remaining private data follows its existing storage rules.

The owner reported basic physical USB operation working on 2026-10-22. Memory
persistence across PCs and the new encrypted USB option still need physical testing;
source tests and temporary-drive relocation are not substitutes.
[Field-kit checklist](docs/FIELD-KIT-TEST.md),
[focused persistence check](docs/USB-PERSISTENCE-CHECK.md).

**Early Mac build:** download the Apple Silicon DMG and drag Cursiv into
Applications. Setup can install Ollama and download a model. Apple signing/
notarization is pending; after verifying the download, macOS may require
System Settings → Privacy & Security → Open Anyway. Hosted Mac source/package
checks are recorded per release, separately from real-user and minimum-OS testing.
The USB edition is Windows-only. [Platform readiness](docs/PLATFORM-READINESS.md).

### Sample-data demo

`demo` loads a labeled sample stream survey and protocol, apart from the user's
notebook/documents. `demo off` restores the normal records. The demo is a workflow
example, not evidence that a research team has used Cursiv in the field.
[Walkthrough](docs/FIELD-DEMO.md), [offline demonstration](OFFLINE-DEMO.md).

---

## Build the installer

Use Python 3.13 and a clean virtual environment with the hash-locked
`requirements-release.lock`. PyInstaller is included; Windows installer creation
also requires [Inno Setup 6](https://jrsoftware.org/isdl.php).

1. Update the version together in `launcher/cursiv_launcher.py` (`_CURRENT_VERSION`),
   `installer/cursiv_setup.iss` (`AppVer`, `OutputBaseFilename`) and
   `cursiv_engine/core/selfknow.py` (`VERSION`). Choose an unused higher version.
2. Pass isolated regression checks, review the diff, then commit/tag the reviewed
   source with owner authorization.
3. Run `scripts/build_release.py` with that exact tag as its only argument. It
   builds a clean temporary checkout, requires the frozen app self-test, compiles
   Inno Setup and stages identical versioned/latest installers, checksums and
   provenance in `installer/Output/`.

Use the helper's sanitized child environment: inherited editor/tool DLL paths can
shadow Windows/Qt libraries. Working-tree builds are for development. Historical
tags can predate the package rename; the helper discovers their unique engine
version file and builds their own specification/source without changing the tag.
[Build and artifact evidence](docs/U89-RELEASE-VERIFICATION.md).

## Release an update

A Git push does not update installed copies. The updater reads
`https://api.github.com/repos/Cursiv-Local/Cursiv/releases/latest`, requires a
higher version and respects offline mode.

Prepare a draft release with the exact tagged artifacts. Windows needs the
versioned installer, its identical `Cursiv-Setup-latest.exe` alias,
`SHA256SUMS.txt` and provenance. The Mac workflow supplies the tagged DMG,
`Cursiv-mac-latest.dmg`, checksums and provenance. Stable download links are
filename-exact; keep both versioned and stable names.

Follow [owner release authentication](docs/OWNER-RELEASE-SIGNING.md) to create and
verify the independent owner-signed manifest over the final assets. Keep its
private key outside GitHub, OneDrive and CI. Do not change public asset bytes after
signing. Review source CI, frozen checks, independent asset hashes and the draft
before publication. Owner signatures do not replace Windows-trusted signing or
Apple notarization.

Publication can trigger a redundant Mac build; the existing workflow must not
overwrite already owner-signed assets. Record successful tagged runs separately
from intentional duplicate cancellations. [U89 verification](docs/U89-RELEASE-VERIFICATION.md)
records the actual release procedure and evidence.

## Tests, benchmarks and release history

Software regression counts and model-answer scores measure different things.
U90 source checks are recorded in the [changelog](CHANGELOG.md);
published U89 checks belong to its own verification report. Never relabel an older
model benchmark as a score for a new release. Run the fixed suite from the actual
new tag, retain its model/configuration and review failures before publishing a score.

The historical U85 model run scored 153/158 (96.8%), below U84's 156/158. Its
[failure review](bench/FAILURES-U85.md) includes an unsafe allergy answer missed
by the scorer. Pattern matches do not establish medical safety. No newer full-suite
model score is established by the software regression counts or the unscored U86
conversation replay. [Benchmark results](bench/RESULTS.md),
[claim-to-evidence index](docs/CLAIM-EVIDENCE.md),
[quality checklist](docs/QUALITY-CHECKLIST.md).

| Historical change | Evidence |
|---|---|
| U82: selected memory, dated recall, operational state | [Repair record](docs/GROUNDED-CHAT-REPAIR.md), [verification](docs/U82-RELEASE-VERIFICATION.md) |
| U84: restricted turns, paths, source ownership, deferred review | [Verification](docs/U84-RELEASE-VERIFICATION.md), [maintenance](docs/MAINTENANCE-HARDENING.md) |
| U85: quiet feedback, tool/notebook receipts | [Verification](docs/U85-RELEASE-VERIFICATION.md), [feedback details](docs/CHAT-FEEDBACK.md) |
| U86: native workflow replies, field math, focused conversation | [Release notes](docs/RELEASE-U86.md), [verification](docs/U86-RELEASE-VERIFICATION.md), [live findings](docs/LIVE-TEST-FOLLOWUP.md), [conversation findings](docs/CONVERSATION-FOLLOWUP.md) |
| U87: phone help links and tester page | [Release notes](docs/RELEASE-U87.md), [verification](docs/U87-RELEASE-VERIFICATION.md) |
| U89: workspace routing and owner-authenticated updates | [Release notes](docs/RELEASE-U89.md), [verification](docs/U89-RELEASE-VERIFICATION.md), [engineering audit](docs/ENGINEERING-AUDIT-20261023.md) |

U88 was an unpublished candidate; its immutable tag was retained. See
[HANDOFF.md](HANDOFF.md) for release work and remaining human checks.

## Publish the website

```bash
node cloudflare/publish.mjs
```

It copies the allow-listed pages from `website/` into `cloudflare/dist/` and runs `wrangler deploy`. Use `--build-only` to build without deploying.

### Website architecture and analytics

The existing deployment uses Cloudflare Workers with static assets and D1.
`cloudflare/publish.mjs` builds the allowlisted files into `cloudflare/dist/`;
`--build-only` never deploys. Analytics setup requires the additive schema and a
separate administrator secret; do not deploy a partial migration.

The public download counter has been removed. The authenticated statistics page
retains cached GitHub installer counts, excluding duplicate latest aliases, source
archives and unrelated files. Optional download-button
clicks are separate anonymous aggregates, never completed downloads. GPC/Do Not
Track are respected. `/admin/downloads/` requires authentication. Unavailable
metadata must not become an invented zero; download links remain independent.
[Setup, counting rules and checks](cloudflare/DOWNLOAD-ANALYTICS.md).

---

## Optional extras

- **LoRA training** needs `torch transformers peft accelerate datasets` in a normal (non-bundled) Python. The Training Data window checks for them and installs them in a visible terminal. CPU training works but is slow (roughly 6 minutes per example per epoch on a typical CPU).
- **Voice** uses `faster-whisper` and `sounddevice` when installed.

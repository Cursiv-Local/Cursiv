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
| `core/` | Phases (`phases.py`), speed tuning for small GPUs and free keys (`speed.py`), self-knowledge (`selfknow.py`), read-only computer tools (`tools.py`), plugins / Cursiv Forge (`plugins.py`; since U98 every plugin call runs in its own process via `plugin_runner.py`, `Cursiv.exe --plugin-runner` when installed), talking style (`style.py`), strand memory archive (`strand_store.py`), constitution. |
| `memory/` | Semantic memory (find by meaning with `nomic-embed-text`, keyword fallback), project memory, session logs. |
| `council/` | The advising council behind `council <question>`: seats answer in parallel, synthesizers combine them. |
| `agents/` | Custom agents (`agent new …`), Babel translation, coding agent, offline queue, reference brain, voice. |
| `coding/` | The coding brain: playbooks, worked examples, error diagnosis, run-and-fix sandbox, `evolve` plugin writer. |
| `guardian/` | Login (bcrypt), security questions and protected paths (no owner mode or unlock codes since U96). Shared filesystem mutations deny guardian/login/key targets. Login is a front-door lock, not data encryption; installed keys use platform protection where available (see [threat model](docs/THREAT-MODEL.md) for plaintext exceptions). |
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

### Conversation and memory encryption (always on)

Always on for a computer since U97 (`launcher/encryption_dialog.py`). The first start
lists coverage, asks for a separate passphrase twice and encrypts the existing data
(resumable: an interrupted start finishes at the next one with the same passphrase;
`--encrypt-data` still works and does the same). Every start after requires that
passphrase before loading private stores or launching background work. A Cursiv USB
drive (portable mode) stays readable by the owner's choice; `launcher/usb_sync.py`
decrypts covered stores on the way to a drive and encrypts them again when they come
back (staged imports in `import-pending` stay encrypted). The vault marker and
`.vault-recovery/` never travel.
Since U98 the field notebook is covered too: the observation log, its photos and
imported team logs (reports, exports, team shares and public team keys stay readable;
a phone upload is deleted once imported). A computer already encrypted by U97 gets
its notebook encrypted at the next unlock (`vault_migration.adopt_new_stores`), with
verified recovery copies first.
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

### Chat code typography (U93)

`launcher/chat_rendering.py:style_code` gives inline commands and fenced code a
local monospace font at the transcript's normal size. Windows prefers Consolas;
Menlo/DejaVu Sans Mono/system monospace are fallbacks. Qt's Markdown importer
otherwise inserts the system fixed font's own size and ignores code CSS.
Streaming and final parsing normalize only the inserted range. Reopened HTML is
normalized once in the view; the export cache is invalidated when necessary and
user data is not migrated. `tests/test_code_typography.py` covers pixel/point
sizes, retained text/formats, unchanged history and repeat formatting.

| Area | Behavior and deeper documentation |
|---|---|
| Field notebook | Original measurements are preserved; corrections append a new record with a reason. SHA-256 chains detect changed/reordered records, and signed exports identify the signing device. CSV, JSON, GeoJSON and printable reports are supported. Camera time/GPS are retained when available; the app does not provide live GPS. [Notebook integration](docs/FIELD-NOTEBOOK-INTEGRATION.md), [verified local actions](docs/VERIFIED-LOCAL-ACTIONS.md). |
| Documents | Imported protocols/SOPs can supply page references. Document-only mode declines uncovered questions, with the documented emergency exception. [Claim evidence](docs/CLAIM-EVIDENCE.md). |
| Calculations | Code handles units, coordinates/UTM, distance/bearing, dilutions, statistics, rates/durations, bleach doses and the lightning waiting rule. A matching native calculation has an application-owned receipt; this is not medical certification. [Native boundaries](docs/NATIVE-TRUST-BOUNDARIES.md). |
| Team sharing | Signed notebook chains move by USB/shared folder. Imports retain separate device chains and report conflicts rather than overwriting observations. [Phone notebook and transfer](docs/PHONE-NOTEBOOK.md). |
| Personal features | Settings → Appearance → Show personal features exposes older letters/vault, council, coding and builder tools. Current source also gates typed letter/vault commands and dialog shortcuts; it retains existing data/backends. [Ownership map](ARCHITECTURE.md). |

### Contested philosophical and value questions (U91)

**U92 transcript repairs:** `test_u91_transcript_followup.py` covers
punctuated version/offline questions, actual offscreen Qt placeholder rendering,
document misses, the paired moral-realism discussion, memory/context comparison,
and current tone across providers and compaction. Build/publication evidence is
recorded separately from source checks.

The live-test paired argument/objection request has a bounded built-in response;
single-position requests remain conversational. The shared instruction also
attributes disputed objections to their proponents instead of asserting them.
The memory-comparison reply explains inputs/context without inspecting records,
inventing memory decay or claiming model-weight training.

An explicit imported-document question with no retrieved passage returns an
application-authored miss before generation. This establishes a retrieval miss,
not proof that the complete document lacks the information. Attached material
and emergencies retain their existing paths. General questions still use the
normal model route.

`core/style.py` emits a person's learned style rules in a separate system block,
with a note that the current request overrides them. Compaction reserves a bounded
share for complete style lines. Since U96 there are no selectable tones: Cursiv has
one personality, defined in `codex/system_prompt.md` ("How to talk") and carried
into the compact persona. Old `tone` values in style files are ignored. There is no
hard text cut-off or extra rewrite call; live model compliance still requires
manual checks. Talk-only turns do not read stored style preferences.

**U96 creative requests.** "Be honest" says thought experiments, hypotheses,
fiction and creative writing are welcome and labelled. For a creative or
hypothetical request, `chat/response_style.drop_false_refusal` removes an opening
claim that Cursiv lacks the capability when the same reply then does the work;
safety and permission refusals, and refusals with nothing after them, are kept.

**U96 memory clean-up.** `memory cleanup` (`memory/cleanup.py`) lists saved notes
and memory facts that mislead answers: guardian-era replies, old council answers
about Cursiv's features, test records and inferred preferences against
speculative or creative thinking. Plain regular expressions decide, not a model.
`memory cleanup remove <codes>|all` archives each record to
`APP_DATA/backups/memory-cleanup-<time>/` (vault-protected names) before a verified
removal; unreadable saved-note lines are kept. It is routed before memory intents.

Qt streaming and final reply parsing use GitHub Markdown with raw HTML disabled.
Literal placeholders stay visible; trusted application status chips still use
escaped application HTML. Markdown links, tables, code and message caching remain.

`core/philosophy_policy.py` holds a shared instruction: acknowledge unresolved
disagreement first, present the main arguments fairly, distinguish evidence from
normative premises, and never claim special model access to a philosophical verdict.
The chat assembles it as a separate application system block for local and cloud
providers, including tool mode. Prompt compaction reserves space for the complete
policy instead of losing it with the long persona.

Common foundational questions about moral truth, free will, consciousness,
ethical theories and beauty receive concise built-in overviews before model
generation. Their source label identifies application text, not a model or live
lookup. Short follow-ups use the previous user question for context, never a model's
verdict as proof. Definitions, historical attributions, factual questions, safety
instructions and file/memory commands keep their existing routes. Explicit requests
to argue a position still use the model, with that position labeled as a perspective.

This adds no lookup, model pass or memory write to the built-in reply path. The
general instruction covers broader contested topics; wording beyond the bounded
native cases remains dependent on model compliance. Automated tests use fake
providers and isolated data, not a claim that every live model response is neutral.
Run `python -m pytest tests/test_philosophy_policy.py -q` in an isolated profile.

Implementation reading, checked 2026-10-23: Stanford Encyclopedia of Philosophy
entries on [moral realism](https://plato.stanford.edu/entries/moral-realism/),
[moral anti-realism](https://plato.stanford.edu/entries/moral-anti-realism/),
[free will](https://plato.stanford.edu/entries/freewill/),
[consciousness](https://plato.stanford.edu/entries/consciousness/),
[consequentialism](https://plato.stanford.edu/entries/consequentialism/),
[deontology](https://plato.stanford.edu/entries/ethics-deontological/),
[virtue ethics](https://plato.stanford.edu/entries/ethics-virtue/) and
[beauty](https://plato.stanford.edu/entries/beauty/). These are development references;
the application does not fetch them while answering. Anti-realism and relativism
are distinguished rather than treated as interchangeable positions.

### Memory, permissions and conversation history

#### Workspace files (U91)

The uncommitted U108 candidate adds bounded source investigation using the same workspace grant:
“Examine the repository and identify its architecture”, “Inspect Field Notebook retrieval code”,
or “Trace what happens when a user sends a message”. Results contain relative paths, line numbers,
declarations and possible static links backed by inspected imports. No code executes and no model
generates these findings. Limits default to 24 reads, 48 tool calls, 120,000 characters, import depth 4
and 15 seconds; reaching a limit is reported. Protected-content refusals remain enforced. Documentation
paths guide discovery but do not prove runtime behavior. Dynamic dispatch and complete self-tracing
remain unverified. [U108 validation and limitations](docs/U108-VALIDATION.md).

Natural questions about Cursiv's implementation also select its own installed public source
automatically, including follow-ups in the current chat. This is independent of workspace access.
A build-time inventory indexes tracked public source, declarations and possible static call targets;
each selected file is reread and SHA-256 checked, normalizing Git's LF/CRLF representation.
Version mismatch or altered source fails closed.
Untracked owner documents, private stores and station code are excluded from this inventory. `No tools`
also disables own-source reads. Critical confirmation/correction/fallback explanations are native,
conditional on inspected AST witnesses; changed witnesses fail closed. Other implementation questions
use bounded ordered source sections with the installed local model, without
saved personal context, plugins, workspace tools, model downloads or online fallback. Source citations
are checked; code interpretation can still be wrong and does not establish a runtime trace. Packaging
generates the inventory from current source. Development checkouts must run
`python scripts/build_self_index.py` after source edits. Details and measured limits:
[automatic self-inspection](docs/U108-SELF-INSPECTION.md).

“Do not modify any files; read ARCHITECTURE.md” preserves inspection while denying changes.
Mentioning notebook implementation routes to source inspection; discussing memory versus the notebook
does not request a save. A structured notebook request ending “Ask me before saving” returns a preview
without writing; the desktop uses its existing Save/Edit/Cancel card. Preview instructions are kept
out of the approved observation. Explicit native log commands retain their existing direct-save behavior.

Choose `workspace <folder>` and enable `files on` once. Natural commands use the
same verified local tools in local and cloud model modes, without model inference:

- `Create a file called field-notes.txt and write ‘Site A - water clear, 14.2 C’ in it`
- `Create field-notes.txt in my workspace` creates an empty file.
- `Add ‘Site B - slightly cloudy, 13.8 C’ to the notes file`
- `Open the notes file` or `Show me what’s in field-notes`
- `Search my workspace for temperature or sample` returns local paths and line numbers.

Recent-file context comes from confirmed receipts in this conversation. A bounded
filename lookup can resolve a unique partial name; ambiguous or incomplete searches
ask for a filename/subfolder. Paths are revalidated against the current workspace;
changing workspace does not grant access to old absolute paths. Model save claims
and model-provided paths never establish context. Measurement references use only
exact user-authored text; a missing new measurement is requested rather than invented.

Existing-file appends and replacement requests retain the approval flow. Explicit
`Overwrite notes.txt with the text: ...` authorizes replacement, with a changed-file
check. All operations retain files-off, protected-path, symlink/junction/hard-link
and restricted-turn safeguards. No shell execution, web fallback or persistent
filesystem-context database is added. `help coding` includes natural examples.

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

The owner reported basic physical USB operation working on 2026-10-22, and on
2026-10-25 (U97, encryption always on) reported moving data computer → USB → another
computer working. A clean-machine first start and a passphrase-recovery drill are
still not claimed; source tests and temporary-drive relocation are not substitutes.
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
2. Pass `python scripts/check_workspace_files.py` and the full isolated suite,
   review the diff, and commit/push the feature branch only with owner authorization.
   Open a PR and wait for the required workspace, full-suite and security checks
   before merging to main. Main protection requires these checks even for admins.
3. From the clean tested main commit, run `python scripts/prepare_release.py <tag>`.
   It verifies all three version strings, exact-source successful main CI and the
   local workspace gate **before** creating a new tag. Missing/pending/failed checks
   stop tag creation. It does not push or publish.
4. Run `scripts/build_release.py` with that exact tag as its only argument. It
   builds a clean temporary checkout, requires the frozen app self-test, compiles
   Inno Setup and stages identical versioned/latest installers, checksums and
   provenance in `installer/Output/`.

The focused workspace job runs on every PR and main push on Windows and Mac,
without GUI windows or inference. New Windows builds repeat the tagged workspace
gate and exact-source CI check; tagged Mac builds require the same main CI.
Historical immutable tags that predate these helpers keep their rebuild path.
Use the preparation helper instead of manually creating release tags; the GitHub
main rule does not prevent an owner from deliberately bypassing local release tools.

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
U113 source and package checks are recorded in the [verification report](docs/U113-RELEASE-VERIFICATION.md);
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
| U93: readable code typography and website polish | [Release notes](docs/RELEASE-U93.md), [verification](docs/U93-RELEASE-VERIFICATION.md) |
| U94: USB startup fix and drive Check / Update | [Release notes](docs/RELEASE-U94.md), [verification](docs/U94-RELEASE-VERIFICATION.md) |
| U95: bring USB data back to a computer | [Release notes](docs/RELEASE-U95.md), [verification](docs/U95-RELEASE-VERIFICATION.md) |
| U96: one personality, self-awareness, USB gate | [Release notes](docs/RELEASE-U96.md), [verification](docs/U96-RELEASE-VERIFICATION.md) |
| U97: Trust fixes, encryption always on | [Release notes](docs/RELEASE-U97.md), [verification](docs/U97-RELEASE-VERIFICATION.md) |
| U98: Plugins isolated, notebook encrypted, clearer chat | [Release notes](docs/RELEASE-U98.md), [verification](docs/U98-RELEASE-VERIFICATION.md) |
| U99: conversational actions, operational self-knowledge | [Release notes](docs/RELEASE-U99.md), [verification](docs/U99-RELEASE-VERIFICATION.md) |
| U100: records you can trust, memory you can see | [Release notes](docs/RELEASE-U100.md), [verification](docs/U100-RELEASE-VERIFICATION.md) |
| U101: starter profiles, field formulas, safer storage | [Release notes](docs/RELEASE-U101.md), [verification](docs/U101-RELEASE-VERIFICATION.md) |
| U102: reliability: OS-enforced isolation, verified calculations, recovery | [Release notes](docs/RELEASE-U102.md), [verification](docs/U102-RELEASE-VERIFICATION.md) |
| U103: team field drives, overconfidence check, silent-error lint | [Release notes](docs/RELEASE-U103.md), [verification](docs/U103-RELEASE-VERIFICATION.md) |
| U104: Field Station preview, team-drive fixes | [Release notes](docs/RELEASE-U104.md), [verification](docs/U104-RELEASE-VERIFICATION.md) |
| U105: fixes from an outside review | [Release notes](docs/RELEASE-U105.md), [verification](docs/U105-RELEASE-VERIFICATION.md) |
| U106: Research workflows in one window | [Release notes](docs/RELEASE-U106.md), [verification](docs/U106-RELEASE-VERIFICATION.md) |
| U107: Dependable research profiles | [Release notes](docs/RELEASE-U107.md), [verification](docs/U107-RELEASE-VERIFICATION.md) |
| U108: Reliable routing and automatic source inspection | [Release notes](docs/RELEASE-U108.md), [verification](docs/U108-RELEASE-VERIFICATION.md) |
| U110: Natural-language self-inspection and notebook reliability | [Release notes](docs/RELEASE-U110.md), [verification](docs/U110-RELEASE-VERIFICATION.md) |
| U111: Routing, verification and model transparency | [Release notes](docs/RELEASE-U111.md), [verification](docs/U111-RELEASE-VERIFICATION.md) |
| U112: Unified AI provider and model manager | [Release notes](docs/RELEASE-U112.md), [verification](docs/U112-RELEASE-VERIFICATION.md) |
| U113: Reliable self-inspection and scoped verification | [Release notes](docs/RELEASE-U113.md), [verification](docs/U113-RELEASE-VERIFICATION.md) |
| U109: Reliable installed-source inspection | [Release notes](docs/RELEASE-U109.md), [verification](docs/U109-RELEASE-VERIFICATION.md) |
| U110: U110 software and release checks | [Release notes](docs/RELEASE-U110.md), [verification](docs/U110-RELEASE-VERIFICATION.md) |
| U92: feature discovery and live-transcript repairs | [Release notes](docs/RELEASE-U92.md), [verification](docs/U92-RELEASE-VERIFICATION.md) |
| U91: natural workspace requests and philosophical uncertainty policy | [Release notes](docs/RELEASE-U91.md), [verification](docs/U91-RELEASE-VERIFICATION.md) |
| U90: permanent engine package and optional private storage | [Release notes](docs/RELEASE-U90.md), [verification](docs/U90-RELEASE-VERIFICATION.md) |
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

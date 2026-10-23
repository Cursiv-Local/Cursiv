# Verified local actions: filesystem, memory and related stores

Date: 2026-10-21. Branch: `codex/verified-local-actions`.

This follow-up implements the approved filesystem investigation, natural-language
memory brief and concrete related save-verification findings. It preserves the
pending native Field Notebook, Saved Notes and chat-rendering work. No commit,
push, version bump, installer build, release or deployment was performed.

## Read-only audit and root causes

### Filesystem reproduction

The first sentence matched broad file-intent detection but missed the narrow
filename/content parser. It therefore asked for an exact filename already present
in the request. A subsequent natural-language follow-up could miss classification
and reach ordinary Ollama `/api/generate` prose. This local generation path does
not execute `file_create` or `read_file` descriptions. A model transcript naming
those operations does not prove either happened. Source inspection found no
installed `file_create` plugin establishing such an operation.

The authoritative path is the `Path` returned by `file_access.resolve()` inside
the filesystem layer. An LLM-supplied location is not authoritative. The existing
low-level writer already flushed, fsynced and read back its bytes, but its string
API discarded structured provenance. Generic/native adapters could label a failed
read as “Checked” or emit “wrote” for an error. Launcher/cloud defaults could use
the program root when no explicit workspace was selected. The native cloud write
loop also had an automatic second model pass capable of changing literal content.

### Memory

The old `remember` branch treated everything after that word as fact text. Thus
`permanently:` became stored content. Contextual/indirect requests fell through to
ordinary models, compound requests had no independent outcome contract, and a
short unsaved input could receive an “already remember” acknowledgement. The
existing atomic JSONL backend and its backups were suitable for reuse. Native
memory operations needed application-owned routing and independent ID/content
read-back rather than model acknowledgements.

### Other concrete findings

- Legacy letter deletion swallowed filesystem errors before removing its index
  entry and returning success. Same-second letter IDs could overwrite a letter.
  A damaged index could be treated as empty and overwritten by the next save.
- Saved Notes returned an ID after a buffered append without fsync/read-back;
  its chat action could say “Saved as note” even when the backend returned no ID.
- Custom-agent loading could treat damaged storage as absent, enabling replacement.
- Image caches could default to the program root; same-second names could collide.
- The shared atomic writer used a fixed temporary name and lacked independent
  read-back. The dedicated notebook, semantic-memory and state-store paths already
  had additional verification; those storage formats were retained.

## Execution paths after repair

| Request | Execution and verification | User-visible result |
| --- | --- | --- |
| Explicit notebook request | Existing native `notebook_tools` allowlist → `fieldlog.add`/retrieval/chain verifier | Actual record ID and verified chain; never `field_log.txt` |
| Explicit memory request | `memory.intents.command` → validated operation → `semantic` backend → independent record/setting read-back | Actual ID, exact stored content, per-operation outcome or clarification |
| Explicit file request | `file_access.command` → authorized workspace → `perform`/`execute_result` → atomic write → exact byte read-back | Backend-resolved absolute path, byte count and SHA-256, or confirmed failure |
| Model-native file tool | Provider tool-call object → same filesystem backend → structured receipt | Application-owned status; receipt JSON returned to provider, including failure |
| Generic lookup | Allowlisted dispatcher → same authorized reader → typed outcome | “Checked” only for confirmed results; failed/unverified output labelled explicitly |
| Saved Note / letter / agent / cached image | Existing application command and store with verified persistence | Success follows actual write/read-back; no model prose is executed |

The launcher routes notebook and memory requests before generic models, including
explicit provider prefixes. User turns and optional application receipts remain in
conversation history. Provider message builders continue stripping receipt metadata
from API messages. Notebook receipt handling and append-only chain behavior remain
as implemented in [the notebook report](FIELD-NOTEBOOK-INTEGRATION.md).

Application-owned mutation receipts retain their Python type through streaming
filters and time limits. They bypass the later model answer-checking pass. Native
provider loops do not let terminal model prose replace a mutation result, and
literal writes no longer invoke an automatic content-rewriting model. Existing
explicit coding-generation commands remain available.

Model output remains untrusted prose. A conservative guard replaces recognizable
fabricated file/tool/save transcripts and unsupported memory promises; fenced code
examples remain prose. In the GUI, replacement removes the provisional draft from
the final reply. Non-replacing streaming callers receive an explicit correction
after any already-delivered text. This guard is supplementary: only backend
execution and receipts establish an action, regardless of how prose is worded.

## Workspace authorization and portability

- Installed mode starts with no implicit workspace or file authorization. Select
  `workspace <folder>`, then `files on`. The validated grant persists per person
  in `workspace_access.json` under the existing application data directory.
- Relative paths use that selected workspace. Absolute paths must remain within it.
  No empty-root fallback to CWD, home, `_internal` or a temporary extraction exists
  in these file paths. An explicitly selected location remains the user's choice.
- Existing credential, traversal, alternate-stream, symlink, junction and hard-link
  checks remain. The selected root and its ancestors are now checked for links too.
  Overwrites still require confirmation and an unchanged expected hash; generic
  file deletion remains disabled.
- Portable mode uses its existing `Workspace` default. Saved portable references
  resolve against the current USB root after relocation. A saved external-host
  grant from a different computer fails closed and requires explicit selection.
- Images use a verified unique cache file in the selected enabled workspace or
  user Home cache. The user cache is application-managed image storage, not a
  fallback authorization for arbitrary workspace files.

## Memory behavior and preservation

Supported operations are `SAVE_MEMORY`, `RECALL_MEMORY`, `UPDATE_MEMORY`,
`FORGET_MEMORY`, `LIST_MEMORIES`, `DISABLE_AUTO_MEMORY`, `ENABLE_AUTO_MEMORY`.
Deterministic parsing covers the brief's examples. Context resolution considers
user messages only; model-provided facts, paths and save claims are never evidence.
Multiple candidate details cause a scoped clarification; unrelated/new requests
discard stale choices. The preexisting `save this` Saved Notes action is preserved.

For otherwise unresolved explicit memory cues, one optional classifier may use an
already-loaded loopback Ollama model. It does not start/download a model, wait for
an idle chat, call a cloud service or execute operations. Its caller budget is at
most two seconds, with one outstanding request. Strict schema/index checks select
an actual user-text span. Application validation permits only proposed save/recall
spans; a classifier cannot authorize deletion, correction or retention changes.
Unavailable/invalid classification produces a clarification without success.

Manual saves bypass embeddings and use exact duplicate checks, retaining original
record provenance. Automatic learning remains separate, can be disabled, and does
not re-extract explicit memory instructions. Compound requests verify and report
each outcome separately. Corrections atomically supersede the old active record,
retain its text/provenance/history, and use the existing verified pre-rewrite backup.
Forgetting a selected record removes its linked correction history through the
same verified writer. No migration or rewrite of real user data was performed.

## Exact files changed in this follow-up

Production:

- `cursiv_engine/core/file_access.py`: parsing, structured receipts, explicit path
  authority, shared execution, read snapshots, unsupported-prose guard.
- `cursiv_engine/core/workspace.py` (new): persisted explicit grants and portability.
- `cursiv_engine/core/tools.py`: verified lookup outcomes and neutral failure context.
- `cursiv_engine/core/local_intent.py` (new): bounded optional local classifier.
- `cursiv_engine/memory/intents.py` (new): validated seven-operation memory interface.
- `cursiv_engine/memory/semantic.py`: exact manual deduplication and atomic corrections
  / selected forget, reusing existing JSONL, provenance and backup facilities.
- `cursiv_engine/memory/formation.py`: keep explicit operations out of automatic learning.
- `cursiv_engine/ui/chat_app.py`: shared file dispatch/receipts, native routes, precise
  provider failures, no implicit root/content rewrite or later mutation rewrite.
- `launcher/chat_commands.py`: workspace persistence, native memory delivery,
  verified approval/cache/note outcomes; retain existing Saved Notes alias.
- `launcher/chat_panel.py`: native memory routing/history and actual file receipts.
- `cursiv_engine/core/atomic.py`: unique temporary files, fsync and exact read-back.
- `cursiv_engine/core/strand_store.py`: locked flushed/read-back-verified note appends.
- `cursiv_engine/family/legacy_store.py`: verified letter/index changes, unique names,
  strict corrupt-index handling and retained import timestamps for duplicate checks.
- `cursiv_engine/agents/custom.py`: serialized verified saves/deletes, corrupt-data refusal.
- `cursiv_engine/codex/system_prompt.md`, `cursiv_engine/core/selfknow.py`: accurate
  native capabilities and backend-only evidence descriptions.

Tests/docs:

- New `tests/test_verified_filesystem.py`, `tests/test_memory_intents.py`,
  `tests/test_verified_state_changes.py`.
- `tests/conftest.py`: isolate the new workspace-grant store in existing fixtures.
- `tests/test_chat_rendering.py`: bounded wait for actual coarse-timer delivery;
  production 40 ms interval and GUI-thread/single-batch assertions remain.
- This report, the notebook report's follow-up pointer, and `HANDOFF.md`.

## Validation

Tests run in archived copies of HEAD with every pending source file overlaid and
disposable HOME/application data. They never import the real installation against
its user records. Baseline selected filesystem/notebook regressions: **82 passed**,
12.59 s (`cursiv-check-n4340_zj/pytest.log`). The earlier notebook full baseline was
**920 passed, 1 skipped**. An intermediate full follow-up suite passed **1,003 tests,
1 skipped**, 156.70 s (`cursiv-check-d9emc9po/pytest.log`). A later focused run passed
**209 tests**, 20.68 s (`cursiv-check-_a7kf7b6/pytest.log`).

**Final exact-source full suite: 1,008 passed, 1 skipped, 150.00 s.** The only skip
requires macOS Keychain on this Windows host. Final log:
[pytest.log](C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/cursiv-check-2a48gvi8/pytest.log).
Command: Python 3.13 `check_cursiv_memory.py`, selecting all `tests`, using pytest
`-q -ra --disable-warnings --maxfail=10` in the disposable snapshot. All changed
Python sources match that snapshot exactly. Syntax and `git diff --check` pass.
Scope comparison with the pre-follow-up source finds the intended 24 files;
clean tracked text is compared with LF/CRLF normalization because the baseline
uses `git archive`. Earlier pending source/report content is retained. The real
Saved Notes file's 78 records and SHA-256 are unchanged, as recorded in the handoff.

New coverage independently checks real disposable bytes, unique markers, relative
and absolute paths, read-after-write, failed writes, permissions, actual Windows
read-only files, root junction rejection, stale approvals, fresh-process reads,
portable relocation, host grants, strict classifier schemas, memory modifiers,
context/corrections/ambiguity, manual saves with learning off, duplicate prevention,
setting/read-back failure, notebook regressions, letter collisions/failures, agents,
Saved Notes and image cache persistence. Model selectors are stubbed for local and
cloud routing; native Claude/OpenAI HTTP payloads are stubbed to inspect the actual
tool-result protocol and errors. Offline deterministic paths prohibit model calls.

Earlier runs exposed a callback-mock compatibility issue and two legacy wording
regressions; all were corrected. A preexisting 65 ms Qt timer test flaked, so its
wait now observes actual delivery with a 250 ms bound. One selected run stopped in
a Qt access violation after a new UI test started an unmocked title worker; the
test now disables that unrelated model worker and drains saves before cleanup.
Neither interrupted nor failed runs are counted as passes.

## Remaining limits and owner actions

- No live qwen/cloud inference or rebuilt installed-executable restart is claimed.
  Fresh Python processes test real persistence. Building and installing an approved
  release is still required to update the owner's installed Cursiv.
- Language recognition is bounded; unusual or underspecified requests can require
  clarification. The prose guard is not a proof system for every possible sentence.
  Third-party plugin outputs remain explicitly unverified, not certified receipts.
- These store locks coordinate threads in one process. Simultaneous app instances,
  adversarial filesystem link races, removable-drive failure and hardware power-loss
  durability are not certified. SHA-256 read-back proves compared bytes at that
  moment, not an authenticated person or future persistence forever.
- A failure after replacement/append may leave real data on disk while the outcome
  is unconfirmed. It is not deleted as rollback. A letter index failure may leave a
  recoverable orphan letter. Inspect before retrying an uncertain operation.
- Existing corrupt data is surfaced/preserved, not automatically repaired. This is
  a repair of the audited action paths, not certification of every unrelated setting,
  plugin, background learner, website feature or earlier architecture proposal.
- Installer, updater, networking policy, website, README and benchmark source files
  were not changed by this follow-up. Nothing was committed or published.

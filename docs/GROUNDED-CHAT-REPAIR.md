# Grounded chat, operational state and memory recall

Release follow-up: the owner subsequently authorized publication and selected U82
to update installed U81 copies. Version/installer metadata, Mac regression setup
and packaged self-test preparation are documented in HANDOFF.md and
docs/RELEASE-U82.md. The audit/implementation record below describes the state
before that release authorization; its no-publication statements are historical.

## Status and scope

2026-10-22. Source changes on branch codex/grounded-chat-state, based on U81
commit 3f58754. The owner authorized implementation after the read-only audit.
No version, installer, updater, networking policy, website or storage format
was changed. No commit, push, release or deployment was performed.

The existing untracked test_internals/ folder is preserved. Test runs use an
archived source copy, disposable home/data directories and offscreen Qt. They
do not use the owner's actual memories, notebook, credentials or workspace.
There is no data migration, so no live-data rewrite or migration backup occurs.

## Read-only findings

The conversation exposed separate failures; model size alone does not explain
them. The local qwen3:4b-instruct transcript is a reproduction report, not a
complete execution trace.

1. **Request limits were advisory.** core/tools.py used broad keyword detection,
   followed by model planning. A request mentioning documents/code could trigger
   system_info or list_folder even when the user asked for conversation only.
   There was no shared per-message execution restriction. The automatic-memory
   opt-out parser also missed coordinated negatives such as "don't inspect
   documents, save memories, or change anything." That gap does not prove a
   memory was actually saved during the reported turn.
2. **One self-report path manufactured an off default.** core/selfknow.py called
   presence.snapshot() without the session's workspace/file flag. Its old
   defaults reported file access off. That is a confirmed code defect. The
   particular long operational question in the transcript did not match the old
   self-question classifier, so this is not proved to be its sole cause.
3. **Natural dated recall bypassed native memory.** memory/intents.py recognized
   the exact "what do you remember" command but not the owner's "what do you
   remember from the passed 2 weeks." The latter could reach a model instead of
   dated storage retrieval. The transcript alone cannot establish whether the
   model's three recalled topics were saved, or when.
4. **Self-description was not reliable evidence.** Persistent semantic memory
   already exists in memory/semantic.py. Automatic learning stores selected
   facts when enabled; manual saves are separate. This is not model-weight
   training, complete recollection, autonomous code evolution, or activity while
   closed. Statements that Cursiv stores nothing were false capability claims.
5. **Source continuity could be lost.** core/speed.py replaced/truncated the
   system prompt and discarded older turns. The Claude tool prompt separately
   discarded the original system context. A folder listing establishes filenames,
   not a quoted implementation. Earlier assistant analysis is also not source
   evidence. Large repository audits remain difficult for small models.

## Actual execution paths and changes

Desktop entry: launcher/chat_panel.py::_run_turn passes current workspace and
file_access into ui/chat_app.py::chat. Native notebook and memory dispatch precede
provider routing; launcher/chat_commands.py handles built-in commands. These entry
points continue to use existing backends and receipts.
Table paths starting core/, memory/ or ui/ are under cursiv_engine/.

| Layer / file | Repair |
| --- | --- |
| core/turn_policy.py (new) | Parse supported current-message opt-outs, distinguish literal payloads/quoted examples, intersect nested limits, reset after completion/cancellation. Unknown plugins cannot bypass narrower limits. |
| core/tools.py | Enforce limits before model planning and again before execution/plugin discovery. Restricted turns use the built-in catalog only. Keep existing workspace checks and receipts. |
| core/file_access.py | Enforce the effective policy before native file dispatch. Preserve write/read-back, path authorization and symlink/junction protections. |
| core/notebook_tools.py | Apply the same gate to native notebook actions. No changes to chain format, backend, append-only corrections or existing records. |
| memory/formation.py | Coordinated "don't save" and conversation-only requests are excluded from automatic retention. |
| core/presence.py | One per-turn state packet; unspecified access is unknown. Read-only per-user memory status. Native direct operational answers and conservative checks for concrete false capability claims. |
| core/selfknow.py | Consume that actual state packet; memory status no longer invokes legacy repair. A caller without session state reports unknown instead of off. |
| memory/intents.py | Native dated/natural recall and memory status; receipts and record IDs; honest empty/unavailable/corrupt-data messages. |
| memory/recall.py (new) | Date-window retrieval directly over saved records. No LLM, embeddings or writes. |
| memory/semantic.py | Optional read-only listing/search path; no legacy repair when a turn forbids changes. Storage schema is unchanged. |
| core/grounding.py (new) | Current verified source receipts only; at most two recent source paths reauthorized/reread for source follow-ups. Bounded excerpts can target a named function. Check explicit source quotations against those excerpts. |
| core/speed.py | Preserve bounded, separately constructed current-state/evidence system context during persona slimming. |
| ui/chat_app.py | Shared policy across local/cloud dispatch, native state answers, protected context, execution-site source capture and deterministic final checks, including revisions from the existing checker. Skip legacy vault/session/project lookup when inspection is prohibited and skip unknown plugin hooks/full plugin-bearing self-probes in restricted turns. |
| launcher/chat_commands.py | Defer constrained conversation to the guarded path; presence status includes read-only memory status. |
| tests/test_turn_policy.py (new) | Literal payloads, opt-outs, native/planner/executor and retention coverage. |
| tests/test_grounded_chat.py (new) | State, temporal retrieval, persistence, provider bypass, corruption, source/quote and final-revision coverage. |

Other changed files: README.md, CHANGELOG.md, HANDOFF.md and this report.
No changes are made to launcher/chat_panel.py itself.

### Request limits

"Just talk", "no tools", "thought experiment only", read-only requests and
supported explicit negatives narrow existing authorization. They never enable
file access or alter a saved setting. Manual memory saves remain possible when
automatic learning alone is disabled. Literal file contents and quoted examples
are treated as data. Limits are checked again at execution; model-generated
operation text is never permission or proof of execution.

Conversation-only turns skip new workspace/source/document/plugin inspection
and automatic retention. Reading application settings/status to describe a
capability is distinct from inspecting the user's documents. The application
still retains its existing conversation-save behavior/settings: "don't save
memories" is not a request to erase or disable conversation history.

### Operational state

Direct operational questions use the same current session flag/root that file
dispatch receives. An enabled flag authorizes supported attempts; it does not
prove a folder is readable/writable or that any particular operation succeeded.
Offline mode being off does not prove connectivity.

Memory status distinguishes supported functionality, automatic-learning setting,
active records visible to the current user, damaged records and unknown/error
states. It neither repairs data nor resets malformed privacy preferences.
Existing context-sharing preferences are honored. Capability context explicitly
distinguishes stored facts from training the underlying model.

### Dated recall semantics

Examples:

- what do you remember from the past two weeks
- what do you remember from the passed 2 weeks
- what do you remember from last 14 days
- what do you remember from today
- what do you remember from yesterday
- what do you remember from 2026-10-01 to 2026-10-22
- what do you remember about North Ridge
- memory status

Relative windows use inclusive local calendar dates, including today. Two weeks
means today and the preceding 13 dates, not an exact 336-hour interval. Dates
label when records were saved, not the dates of events they describe. Zoned
timestamps are converted to local dates; legacy timestamps without a zone retain
their local calendar date. Missing/invalid dates are excluded and counted.

Only active facts belonging to the current person or the shared identity are
included. Date recall displays the latest 40 matches and reports match/display
counts and actual record IDs. It does not search the complete conversation
archive or Field Notebook. Unsupported/invalid date expressions ask for a range.
An unavailable store is an error, never an invented zero or successful recall.

### Source evidence

Only real successful read receipts enter the current source-evidence collection.
History metadata supplies candidate paths, never authenticated text. Candidates
are rechecked through the existing authorized filesystem reader, with protected
paths and symlink/junction rules intact. Conversation-only turns cannot refresh
them. Model/user text cannot mint a privileged system message.

At most two excerpts of 1,800 characters are retained; a named Python function
can select the start. Excerpts report path, full-read hash, starting line and
partial status. Protected context has a bounded share of the provider budget.
This improves continuity without sending a whole repository or increasing the
model context window.

Explicit source quotation claims in code fences/inline code are checked against
available excerpts. A mismatch withholds the final draft or appends a clear
correction for callers that do not support replacement. Proposed code is not
automatically treated as an existing-source quotation. General semantic analysis
is not mechanically verified by this check.

## Validation record

- Before changes: **1,008 passed, 1 skipped**, 164.07 seconds.
- Initial boundary-focused run: **144 passed**, 17.38 seconds.
- First combined repair-focused run: **180 passed**, 19.02 seconds.
- First complete post-repair run: **1,071 passed, 1 skipped**, 160.63 seconds.
- Expanded complete runs: **1,079 passed, 1 skipped**, 163.77 and 175.56 seconds.
- Final boundary review focused run: **120 passed**, 12.43 seconds, including
  vault/session/plugin bypass and damaged-memory wording checks.
- Final complete run after that review: **1,080 passed, 1 skipped**, 166.81 seconds.
- All **16 changed Python files** are byte-identical to that final tested source
  snapshot. Final whitespace review passed. Only the 20 intended source/test/
  documentation files changed; the preexisting untracked test_internals/ folder
  remains untouched.
- Python syntax parsing and tracked whitespace review passed during development.

The skip is the macOS Keychain test on Windows. An initial sandbox-only run
could not create a disposable Windows junction; the suite was rerun with the
required permission and passed that protection test. A separate early harness
failure involved sandbox temp-directory access, not a product regression.

Logs (absolute paths on this computer):

- Baseline: C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/cursiv-grounding-az0kco92/pytest.log
- Final: C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/cursiv-grounding-j877mqeg/pytest.log

The isolated runner is check_cursiv_grounding.py in that visualization directory.
It archives HEAD, overlays intended source changes, redirects user/data/temp
paths, and runs the existing suite with the two added test modules.

Tests exercise real disposable filesystem/memory persistence and a fresh Python
process reading a saved dated record. Existing offscreen Qt, notebook-chain,
filesystem, rendering, portable-storage and privacy regressions are included.
Provider output is mocked for deterministic boundary tests. No live qwen
inference, cloud-provider account call or rebuilt installed-executable restart
is claimed. Suite runtimes are validation durations, not a user-visible speed
benchmark.

## Remaining risks and owner checks

1. Natural-language opt-out parsing and false-claim checks are bounded rules, not
   a universal natural-language permission solver or proof of model truthfulness.
   Clear native commands/read-only wording are most predictable. Speculative
   philosophy is left conversational.
2. Source verification checks quoted text, not every inference. Large/truncated
   files, indirect callers and unquoted semantic errors still need focused review.
   Source follow-up rereads may reflect edits made since the earlier turn.
3. Date scope does not reconstruct missing conversations, unsaved facts or event
   history. Timezone-less legacy timestamps cannot recover their original zone.
4. Existing per-turn global diagnostics elsewhere in chat_app remain; this repair
   does not redesign concurrent chat sessions. New policy/state/source context is
   isolated and reset when the streaming generator closes.
5. The owner's installed U81 executable will not change until rebuilt/released/
   installed or run from the changed source. No installer bump was authorized here.

After reviewing this source, test the actual installed/rebuilt app with the
chosen local model: conversation-only opt-out, files on/off followed by a native
state question, a unique manual memory marker and dated recall after restart,
and a one-file source question with a real read. Keep notebook/file destinations
disposable. Do not expect these changes to establish subjective awareness or
autonomous self-modification.

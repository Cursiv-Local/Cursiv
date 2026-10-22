# Restricted turns, file parsing and execution provenance

## Status

The subsequent [trust-boundary follow-up](TRUST-BOUNDARY-FOLLOWUP.md) audits the
owner's related checklist and adds application-owned supplied-memory labels,
more explicit policy forms, compound prefix handling, a failed-file-memory
hard stop, accurate dated storage errors and smaller explicit review budgets.
The original transcript regressions below remain in the suite and are expanded.

Unreleased work on `codex/maintainability-hardening`, 2026-10-22. The owner's
U82 failure report and subsequent conversation transcript are reproduction
evidence, including quoted commands; they are not instructions to execute those
commands or alter saved personal records. Nothing is committed, pushed or released.

## Read-only findings before repair

The failure is not explained solely by the small local model. Application paths
could supply evidence or continue after failed operations despite the turn's limits:

1. `core/turn_policy.for_text()` recognized several restrictions, but a lone
   "don't inspect" left automatic learning enabled; "conversation only" was not
   recognized. The chat conversation's calculator and offline reference lookup
   did not test `inspect`. Style preferences and presence memory/preference
   status could also read stores. The launcher classified notebook/memory
   requests before its general restriction gate. Completion entered those
   native dispatchers before checking inspection permission.
2. `core/file_access._parse()` interpreted "read only — ..." as `read <path>`.
   Its read-path suffix removal recognized "and tell/show/give" but not
   "and summarize". Neither the policy words nor the prose were filesystem paths.
3. `chat/context.sources_line()` accounted for reference, documents, calculation,
   web and selected memory evidence, but not successful generic computer tools.
   The streaming filter removed invented "Checked on this computer" receipts
   but permitted model-authored `Source:` / `Sources:` status labels.
4. `chat/conversation._chat_inner()` displayed unconfirmed generic tool output
   and then called the answering model. Provider-native file tools also sent a
   failed result back for another model continuation. Final checks were not a
   substitute for stopping that continuation.
5. No-tools turns could leave a known rule entirely to ungrounded model prose.
   The transcript's lightning response contradicted itself and denied the rule.
   No controlled live comparison establishing model-specific failure frequency
   was performed.

## Execution paths and repair

### Policy before dispatch, retrieval and retention

`launcher/command_dispatch.handle_command()` → restricted requests defer to
`ui/chat_app.chat()` → `turn_policy.scoped` + `grounding.scoped` →
`chat/completion.chat()` → `chat/streaming._chat_stream()` →
`chat/conversation._chat_inner()` → selected local/cloud provider.

The gate precedes notebook/memory/file dispatch. Inspection restrictions now
disable changes, manual memory writes and automatic learning. Leading explicit
no-save/no-retain instructions and "conversation only" use that same policy.
"Read only" still permits supported inspection and forbids changes/retention.
Explicit automatic-only opt-outs continue to allow an authorized manual save.
Quoted examples and file/memory content remain data, not new instructions.

Calculator/reference lookup, saved style/status/context reads, generic planning
and cloud-native tool selection respect the effective policy. Source excerpts
from earlier turns are not refreshed under a no-inspection restriction. The
optional answer-check context already has the same stored-recall gate.
Reference metadata assembly also returns without loading the table when no
reference was supplied or inspection is forbidden. Restricted-turn tests forbid
both `reference.lookup()` and `reference.entries()`, including final checking.
Restricted prompts use static capabilities instead of inspecting a saved persona,
counting saved notes or probing optional integrations. Saved operational preference
files are not read and their absence is not treated as permission to disclose state.

An application-owned notice reports the active limits, including unavailable
built-in calculation/reference checks. A restricted lightning-rule request gets
an explicit availability response without running retrieval or asking the model
to guess. Other conversational model answers remain unverified model knowledge.
Draft replacement preserves the limits notice. Limits reset after the turn.

**Retention boundary:** disabling memory formation is not deletion or disabling
of conversation-history persistence. The notice says history follows the chat
history settings. This repair does not introduce a private-chat storage mode or
promise that no records exist. Previously inferred memory records are untouched.

### Path extraction and verification

`core/turn_policy.task_text()` strips only recognized leading read-only policy
clauses for parsing. Authorization uses the original, unstripped request.
`file_access.is_request()` / `_parse()` recognize workspace listing and separate
read-summary prose from quoted/unquoted filenames. Explicit `file ...` syntax
preserves literal filenames and content. Unsupported ambiguous instructions ask
for clarification rather than entering a guessed prose path.

Both direct and generic tool paths converge on `file_access.perform()` and its
existing workspace resolution, link/traversal, protected-content and write
verification checks. Generic planner paths no longer expand host home-folder
aliases before that shared resolver; direct built-in wrappers follow the same
rule. The planner requests workspace-relative paths and `.` instead of a home
folder. Relative paths use the authorized workspace.
Native "read ... and summarize" now returns the actual requested file contents;
it does not fabricate a summary or require a second model pass. A conversational
follow-up can request interpretation of verified source.

### Execution evidence and failed operations

`core/grounding` holds successful execution labels in a scoped per-turn record.
Actual call sites record them; model prose and history cannot populate the record.
`sources_line()` names those confirmed results. Model-written source-status lines
are removed while streaming; code-fenced sample data is preserved. The application
adds its own source footer. Native file/status replies identify their application
origin directly. The next turn resets the evidence.

Generic failed/unconfirmed results return application-owned error text and stop.
OpenAI/xAI-compatible and Claude native file loops stop on failed backend receipts
or failed write preparation. Completion does not ask a checker to rewrite those
failures or learn from them. Direct operational status questions use settings and
stored-record observations, explicitly distinguishing permission from successful
access; that status check does not establish the loaded model or inspect documents.

A subsequent live check found a different boundary weakness: a detected wrong
dose remained in the model draft beneath a warning. Detected dose/reference
contradictions now withdraw that draft and display the original supplied card
with its review/provenance status. This uses no replacement model call or learning
from the draft. The Qt caller replaces streamed text; append-only consumers get
an explicit retraction followed by the reference. Reference data was not edited.

## Validation and remaining limits

`tests/test_restricted_regressions.py` includes the exact reported prompts,
mock local/cloud paths, zero lookup/dispatch/retention callbacks under restrictions,
clean paths and literal payloads, source labels, provenance reset, the following
unrestricted turn, draft replacement and generic/native failed-read handling.
`test_verified_filesystem.py` now asserts failed native operations stop after one
provider request, rather than requiring another model round-trip.

Executed results and exact source manifests are recorded in
[the maintenance report](MAINTENANCE-HARDENING.md). Tests use disposable data and
mock providers; they do not claim a real cloud-model test or an installed U82 update.
The final source suite ran **1,177 passing checks with one Mac-only skip**.
Live local-model results are recorded separately, including failed runs.

Policy recognition remains a bounded parser, not a general natural-language
permission proof. Unknown phrasing can need clarification. Ordinary model prose
can still contain unsupported interpretations of real directory listings or
other supplied data; provenance identifies what ran, not truth of every inference.
Existing incorrect inferred facts need separate user review. Trusted plugins and
external agent processes are not OS-sandboxed by these file guards. No memory or
notebook storage format, updater, installer or website source was changed by this
repair. All modifications remain subject to owner review before publication.

# U108 core reliability handoff

Owner: Joshua Winkler. Brief: supplied U108 core reliability/tool routing/source inspection/conversation request, October 27, 2026.
Baseline: main `2f1118bbafec7dea3b7671687d3b7cec4b95719e` (published U107).
Owner authorized continued repairs and commit/push/release/publication as U108 on October28.
Continue the known explanation repairs first; retain all exclusions and measured release gates.

## Boundaries and execution

Preserve local-first/offline operation, centralized workspace authorization, per-turn restrictions,
confirmation, append-only notebook history, encryption, current five research profiles and verifier rules.
No station/hardware work, dependencies, user-store inspection or unrelated UI/profile changes.
Never read/change/stage excluded owner files: `docs/CURSIV-LEGAL-HANDOFF.md`, root `field-notes.txt`,
`test_internals/`. Existing untracked exclusions were present before work.
Tests/benchmarks establish disposable HOME, USERPROFILE and CURSIV_APP_DATA before application imports.
Use the existing locked Python 3.13 interpreter from U107; do not install into it.

## Latest release-preparation status (October28)

Owner authorized commit, push, release and publication after continued repairs. Branch:
`codex/u108-core-reliability`, based on main `2f1118b`. Version preparation now3.14-U108;
no release/publication is claimed before the required gates, builds and asset checks.

Latest complete Windows gate before version preparation: **2,508 passed, 15 skipped,
19 subtests in409.55s** (`U108-continuation-full.xml`), with runtime/index frozen.
Affected checks284 passed; final native/source/routing check114 passed. Earlier complete
2,484/15/19 and USB45/45 receipts remain historical; the commit hook reruns USB.

Critical confirmation/correction/fallback explanations now use app-owned rules conditional
on hash-checked AST witnesses. Missing/changed witnesses fail closed. Four new unseen
questions passed natively with zero model calls (`U108-native-live-unseen.json`), distinct
from Qwen accuracy. General explanations use bounded ordered control sections; model
interpretations remain fallible and full universal code understanding is not claimed.
Git LF/CRLF differences are normalized in source fingerprints; semantic edits still fail.

Explicit brief banter now skips unrelated vault/session/memory/document/plugin and coding
context (baseline5 failed; repaired checks pass). Live replies are brief; first joke still
literal, so humor remains partial. New three-question banter corpus is retained unedited.

Validation: [U108-VALIDATION](U108-VALIDATION.md), [automatic source inspection](U108-SELF-INSPECTION.md).
All local live/full commands completed. Next: stage only explicit public U108 files, regenerate
the index after staged public docs enter Git's inventory, run versioned workspace/release gates,
commit with USB hook, protected source PR/main CI, immutable tag, native packages, signing,
download-back verification, publication and website. No excluded owner files, secrets, user
stores, unrelated profiles or station changes. Local CLI is owner `Cursiv-Local`; connected
GitHub plugin is read-only, so CLI performs authorized mutations. No bypasses or tag moves.

## Investigation map

- Desktop: `launcher/chat_panel.py::_run_turn` -> `command_dispatch.handle_command` or `chat_app.chat`.
- Saved workspace: `core/workspace.py::save/load`; `launcher/commands_system.py` updates UI configuration.
- Per-message limits: `core/turn_policy.py::for_text/effective/scope`; native pre-dispatch `core/action_gate.py`.
- Every workspace file operation: `core/file_access.py::perform/execute_result/resolve`; natural parsing in
  `core/file_requests.py`, bounded traversal in `core/workspace_search.py`.
- Notebook: `core/notebook_tools.py::_request/command/execute`, `core/notebook_proposals.py` preview cards,
  `core/fieldlog.py` append/chain, `core/field_recall.py::query/filters_for_request` verified retrieval.
- Memory: `memory/intents.py` explicit actions, `memory/semantic.py` facts, `memory/session_notes.py` summaries.
- Ordinary chat: `chat/completion.py` native routing/checks; `chat/conversation.py` context/tools;
  `chat/local_provider.py` Ollama; `chat/cloud_providers.py::_slim` and `core/speed.py` context compaction.
- Conversation recall: `core/conversation_recall.py`; desktop retains ordered messages; model context is bounded.
- Provenance: `chat/provenance.py`, `core/answer_assessment.py`, `core/answer_evidence.py`, `core/verify.py`.

## Progress

Read CLAUDE.md, HANDOFF.md, ARCHITECTURE.md, TECH.md, code map and relevant U107 usage/validation/handoff.
Runtime unchanged. Preparing frozen reproducible baseline probes before fixes, in requested phase order.
Potential causes are hypotheses until baseline evidence confirms them: overbroad negation scopes in
turn policy; keyword-only notebook intents; explicit structured saves bypassing requested preview;
natural lookup filters including instruction text; bounded history mislabelled as complete.

## Next and running commands

1. Freeze/run deterministic baseline and real installed Qwen conversation probes.
2. Capability/intent fixes; notebook confirmation/retrieval; bounded source investigation.
3. History/provenance/tone; affected then full regression and USB gates; measured evidence and review.

Baseline focused probes: `bench/results/U108-baseline.xml`: **16 failed / 3 passed** in 4.45s.
Existing boundary/integrity/history subset: `U108-boundaries-before.xml`: **67 passed / 2 skipped** in 10.66s.
The two earlier baseline attempts failed solely during pytest temporary-directory creation under the
restricted Windows temp container; their receipts remain separate (`*-environment-error.xml`, `*-temp-error.xml`).
Using unique `reports/u108-*/pytest` base directories fixed the harness without changing product code.
Workspace save/load passed across three reads. Read-only colon/semicolon phrases disable inspection
because the negation parser includes later affirmative verbs in the negative clause. Source questions
either reach unsupported model conversation or notebook lookup. Sample lookup misses two paraphrases;
record-ID wording returns an unfiltered listing. Both requested-confirmation probes append immediately.
Native first-message wording assumes a complete history, and original-concern wording misses native recall.
Mixed-dimension conversion/addition falls through to model generation. These are reproduced defects;
the owner's exact earlier transcript and real notebook have not been inspected.

Real baseline Qwen completed before runtime edits: `bench/results/U108-live-before.json`, 10 prompts,
10 actual successful model requests. Synthetic workspace/records, localhost-only transport,
Qwen pinned, temperature0/seed42/context8192, optional model review off; deterministic checks remain.
Source questions did not inspect files; pipeline answer contained unsupported operational claims and
privacy absolutes (the existing privacy warning did flag the latter). Original-concern reply added
invented motivations. Mixed-unit replies correctly declined in model prose, but native execution
did not own the refusals. Scientific single-reading answer was appropriately calibrated in this sample.
Initial banter reply literalized the joke; explicit feedback already produced a short playful answer.

Phase1: negation clauses end at semicolons/colons; leading file restrictions can be stripped for
task parsing after authorization. 18 targeted policy/permission checks passed (`U108-phase1.xml`).
Phases2/3: source intent precedes notebook keywords; conceptual questions stay discussion;
notebook paraphrases and record-ID filters use native retrieval. Explicit preview requests stop
native writes; desktop reuses existing approval cards with cleaned, parsed details.
Phase4: bounded source discovery/read/static references through the existing file boundary,
including offset-labelled windows for declarations beyond the initial excerpt; no execution/model.
Initial cross-domain checks:134 passed/2 failed (remaining calculator probes), retained in `U108-initial-after.xml`.
After native dimensional refusals, focused core/policy/code-map checks37/37 passed (`U108-core-after.xml`).
Phase5: original-concern aliases use native user-message recall; earliest available is not labelled
as complete conversation history. A generic scope notice adds no new private conversation payload.
Automatic approval review rejected preserving an earliest-user-text anchor in cloud prompt compaction
because of possible additional private-content egress; that proposed patch did not apply. Safer
implementation uses only a fixed scope notice and local/native recall; no approval remains necessary.
Phase6: current/recent explicit tone feedback guides brief, proportionate banter, excluding technical/safety turns.

October28 resumed: the approval service's usage-limit error prevented the final fixture patch/retest on
October27; no command from that rejected batch ran. Resumed after owner said continue.
Corrected the desktop fixture to the existing complete chat-feedback panel. Expanded acceptance113/113 passed.
Frozen real-Qwen rerun (`U108-live-after.json`) used zero model calls for seven native cases and three
successful calls for humor/feedback/science. First joke still literalized; explicit feedback and science
were appropriate. Compaction could omit response guidance, so application guidance now has its own bounded,
preserved block (no copied user-history anchor). A new compaction regression and same-name/different-module
source-link regression pass in `U108-refined.xml`:141 tests passed. Source edges now require actual inspected
import bindings instead of suffix-name guesses. Earlier source receipts are retained as development evidence.
`U108-live-final.json` retains another real run: same7 native/3 Qwen calls; first joke remains too literal and
long. Tone matching is **partially resolved**, not declared fixed from the two successful feedback samples.
No scientific calibration logic was changed: the measured scientific case already passed before U108.

An initial broad run was interrupted for review of source/tone findings (log `reports/U108-full.log`, no
completed-suite claim). A diagnostic run stopped at861 passed/1 skipped/19 subtests with an unrelated
WinError5 while replacing a synthetic memory file under OneDrive (`U108-firstfail.xml`). Do not weaken atomic
storage to mask that. A fresh full run uses a unique local temp folder outside OneDrive (session37515,
`reports/U108-full-final.log`, final receipt pending). No user files/stores were touched.
First completed full candidate:2426 passed/15 skipped/19 subtests,1 failure in455.36s
(`U108-full-final.xml`). The native-precedence test caught confirmation consulting the generic
file-access intent detector. Review separately reproduced Save+decimal-reading incorrectly classified
as a filename (1 failed/4 passed, `U108-preview-review-before.xml`). Confirmation now uses the pure
natural-file parser and actual filename extensions; no generic filesystem intent is consulted.
Five verb variants cover this. Current affected set226/226 passed in23.51s (`U108-affected-validated.xml`).
An initial affected-test invocation used the stale test_capabilities.py name from historical guidance;
it ran no tests. The corrected list and full suite are the evidence, not that invocation.

Source review: same-name links now require inspected imports; docs are discovery hints only; Markdown
prose cannot become a code declaration. Failed reads report their actual relative path/restriction.
Default inspection time is15 seconds (configurable up to30); the4-second development budget starved
real-checkout discovery during concurrent disk activity. Earlier low-coverage receipts are retained.
`U108-own-source-reviewed.json`:61/61 and67/67 file/line references,31/31 and38/38 Python declarations
validated, but full self-tracing remains incomplete and is not a task-completion success claim.
The existing protected-content scanner refuses some source modules; it was not bypassed or weakened.

Dedicated USB gate:45 passed/2397 deselected in71.70s (`U108-usb.xml`), synthetic local folders only.
Completed full Windows gate:2432 passed/15 skipped/19 subtests in482.48s (`U108-full-validated.xml`).
Following that run's collection, review removed a filename-extension heuristic from notebook confirmation:
a filename inside an observation note cannot remove its requested preview. Added that regression. Partial
source declarations are labelled candidates. Final affected checks204/204 passed in12.06s
(`U108-final-focused.xml`); this follow-up is not presented as a new full exact-tree run.
The saved synthetic baseline records were checked: both requested-confirmation probes actually persisted
the procedural instruction in `note` (one also included its temperature text there). Final preview tests
verify clean approved content, no pre-approval append and no cancelled append.

Final source receipt: `U108-own-source-validated.json`:128/128 file/line references and69/69 Python
declaration/candidate names/lines validated independently against full source. This is citation accuracy,
not complete control-flow verification. Failed reads now state relative path and actual scanner restriction.
Final comparison: `U108-comparison-validated.json`; 19 frozen native cases3/19→19/19;10 model requests→3,
real input/output tokens19547/2324→5915/141. Cold loads and selected native substitutions prevent a general
performance claim. Initial humor still fails qualitative review; explicit feedback/science samples pass.

All owned test/inference/source-probe commands have completed. No U108 commit/push/tag/build/release,
signing, deployment or publication occurred. Final scope/source hashes: `reports/U108-review-state.json`.
No station, excluded owner-file, user-store, secret, profile or website changes.
Remaining: initial banter reliability; complete self-tracing past protected-content refusals/dynamic
dispatch; original transcript regression and independent human grading; native Mac/Linux and installed-app
checks. U108 is an implementation review candidate, **not declared complete or released**.

## Automatic self-inspection extension (owner authorized October28)

Owner asked for automatic working knowledge of Cursiv's implementation without special read commands,
and permits additional agents only if needed. Implementing an owned source index/retriever and shared
answer checks first; no new personas/profiles or agent fleet is presently necessary.
Preserve existing U108 work and all exclusions. Freeze natural self-questions and follow-ups before edits;
test with workspace file access OFF, own-code boundary independent of workspace, no-tools denial,
version/hash mismatches, package layout and source-grounded model answers. No commit/release authorization.
Existing automatic selfknow lookup is ~1800 characters/six matched lines; it lacks a symbol graph and
topic continuity. Existing build.spec bundles whole docs directory; replace that with public own-source
inventory entries so untracked/excluded documents cannot enter the inspection corpus or packaging list.
Baseline native-entry probes started (session91496, `U108-self-before.xml`), synthetic/public allowlist only.
Live frozen sets: `bench/u108-self-inspection.json`; wrapper `scripts/u108_self_live.py` reuses pinned
Qwen/disposable/no-outside-network harness and supplies only tracked public Python/architecture/map sources.

Automatic self-inspection checkpoint, October28: frozen natural baseline6 failed/2 controls passed.
Public index now selects375 files/2508 declarations, excludes owner/untracked documents and station,
checks version/snapshot and every selected file hash. Current-chat user turns resolve follow-ups;
workspace access OFF is supported; No tools denies inspection. Dedicated context bypasses private
retrieval, plugins and planning. Own-source explanations and optional reviews stay local.
Automatic approval review rejected automatic online fallback because source excerpts could be sent to
external providers without payload/destination authorization. That proposal was not applied; the safe
local-only implementation continues without cloud fallback or model download.
Development live attempts are retained (first/second/third/structured/AST-checked/final-development/
development-validated). Structured run caught an index variable-shadowing regression; fixed and guarded
by comparing every installed declaration to the actual AST. Latest development run6 real Qwen calls:
one wrong module reference withheld; notebook exact matching and provider invocation improved, but
fallback explanation still simplifies conditions. Citation validation is not semantic proof. Do not
claim complete code understanding or a perfect six-case result. Heldout4 remain frozen and unrun.
Latest privacy gate114 passed/1 failed: native no-download text was removed by the existing model
self-certification filter. Reworded the application message and made provenance explicitly static.
Earlier sandbox-only attempt115 setup errors (temp access); retained as environment failure, no pass claim.
Next: new privacy/review/scope tests, frozen heldout live run, final isolated Windows/USB gates and docs.
No commands currently running. No commits, publishing, data/profile/station changes.

Extension validation checkpoint: initial full run completed2448 passed/25 failed/15 skipped/19 subtests
in410.41s (`U108-self-full.xml`). All25 were overbroad own-source intent intercepting native overview,
workflow help, operational state or actual saved-memory recall. Existing tests were preserved. Narrowed
self-intent to implementation mechanics, preserving feature/help/status/recall routes. Separate state
lookup removed from own-source path (empty observed state, no invented status). An intermediate affected
run exposed None-state handling:323 passed/8 failures, retained; fixed with explicit empty state.
A mistaken science-test filename ran no tests (`U108-self-scope-final.xml`); corrected actual list.
Final affected source/native/privacy/science checks:359 passed in15.04s (`U108-self-scope-verified.xml`).
First heldout4 real questions are retained in `U108-self-live-heldout.json`: all4 generated,2 material
semantic failures (correction replacement phrasing, retrieval exclusivity); other2 identify real flow/
containment with compressed explanation. These are Codex labels, not independent human grading.
Excerpt selection now reserves its budget for matched operations before context, and correction seeds
include actual add/append implementations. Nonexhaustive excerpts cannot support an "only function"
claim; deterministic guard withdraws it. Code-history readings no longer trigger the physical single-
measurement note; science_check algorithms remain unchanged and existing science tests passed.
Synthetic actual-spec data-plan/frozen-layout probe passed:5 public files+generated index, untracked
private fixture excluded and hash-checked frozen read (`U108-self-package.json`); no real package build.
Current inventory375 files/2508 symbols, snapshot dcf51bc9780c, installed version remains3.14-U107.
Currently running: final full isolated Windows suite session30844 (`reports/U108-self-full-final.log`,
receipt `U108-self-full-final.xml`) and sequential real-Qwen development+seen-holdout regression session40591
(`U108-self-live-candidate-development.json`, `U108-self-live-candidate-regression.json`). Keep code/index
frozen during these runs. Next: dedicated USB, qualitative grading, final report/source hashes.

Final extension source-scope checkpoint: the suspected nested callback turned out to be a real
conditional read-only proposal shortcut in ChatPanel._run_turn. The substantive defect was AST facts
omitting enclosing conditions. Facts now include enclosing if/else conditions; separately, nested
function bodies are excluded from parent execution facts and parent excerpt matches. Added synthetic
callback and actual approval-guard regressions. An incorrect intermediate production assertion is
retained (`U108-self-callback-checked.xml`:392 passed/1 failed); repaired to check the actual guarded
branch. Final affected checks393 passed in11.46s (`U108-self-branches-checked.xml`).
The preceding full run was intentionally interrupted after45% for this source-scope repair; it produced
no completed JUnit receipt and is not claimed as a pass. Confirmed its child Python process stopped.
Frozen current source snapshot bf648063ce5a,375 public files/2508 symbols, version3.14-U107.
Final real model receipts: `U108-self-live-scoped-development.json` (6 successful local requests)
and `U108-self-live-scoped-regression.json` (4 successful local requests). All10 receive own-source
labels. `U108-self-comparison.json` independently checks31/31 emitted path/line locations against
matching indexed source bytes. This does not validate all statements. Manual Codex labels: local
invocation, sample matching and containment supported; message/proposal flow and confirmation remain
partial; fallback ordering explanation fails. Seen correction reply explicitly describes append and
retained history but still opens with ambiguous replacement wording. Lookup improved without the
unsupported exclusivity claim. Final heldout reuse is a seen regression, not a blind score.
No claim of complete implementation understanding or U108 completion. No extra agents were necessary.
Currently running final isolated Windows suite session7341 (`U108-self-full-validated.xml`,
`reports/U108-self-full-validated.log`). Next: dedicated USB gate, final docs and review hashes.

Final gate completion: `U108-self-full-validated.xml`2484 passed/15 skipped/19 subtests in410.93s;
`U108-self-usb.xml`45 passed/2454 deselected in74.48s. Both used fresh disposable local Windows homes;
no runtime/index edits occurred during these final gates. All owned commands completed. No station,
excluded owner-file, profile, user-data, website, version, staging, commit/push/tag/sign/release changes.
Current candidate's implementation and remaining semantic/tone/platform limits are summarized above.
Final source/artifact fingerprints are refreshed in `reports/U108-review-state.json` after this checkpoint.

Final everyday regression on unchanged runtime/index: `U108-live-extension-final.json`,10 prompts,
7 native/3 successful local Qwen requests,5915 input/134 output tokens. Initial joke still too literal/
long; explicit feedback and scientific single-reading sample appropriate. All commands completed.

Owner authorized continuing work or committing/pushing/releasing/publishing U108 (October28).
Continuing known semantic repairs before release; authorization persists, no repeat approval needed.
Root finding: ranked isolated AST statements/sparse lines still omit neighboring branches and return
order. Implementing bounded, ordered AST control slices that retain whole selected branches, strip
large prose literals/docstrings and explicitly label omitted blocks. No new agents/dependencies/cloud.
New unseen4-question corpus frozen before edits/results: `bench/u108-self-control-flow.json`.
Previous measured baseline remains `U108-self-live-scoped-development.json` and seen regression.

Ordered-flow repair checkpoint: code now supplies whole selected AST branches in source order,
with docstrings/long output text omitted and gaps labeled. Source prompt is bounded to4900 UTF-8
bytes to preserve the existing conservative8192-byte transport budget. Last two current-thread user
questions supply follow-up context; previous assistant assertions do not become new implementation
facts. Reference guards recognize functions in supplied normalized sections, while verbatim quote
checks still require actual literal source. No cloud fallback, new profiles or agent fleet.
Regression tests exposed lost provider-loop selection, documentation being treated as an operation,
and dropping the second (actual append) fact after sorting. All repaired; intermediate failures kept.
88 source/privacy/review tests passed in5.68s (`U108-flow-topic-checked.xml`). Earlier live development
attempts are retained (`U108-flow-live-development.json`, `U108-flow-live-checked.json`), not success claims.
Current source375 files/2516 symbols, snapshot b2155d4b5f8d, unreleased version still3.14-U107.
Currently running real-Qwen development/seen/unseen sequence (new `U108-flow-live-final-development.json`,
`U108-flow-live-regression.json`, `U108-flow-live-unseen.json`). Four control-flow questions remain
unseen until this run. Next: semantic review, final affected/broad gates; release remains authorized
but contingent on honest validation. No staging/commit/push/release performed yet.

Version preparation: installer filename gate caught stale U107 OutputBaseFilename (71 passed/1 failed);
corrected both the actual output name and comments. Final versioned release/source checks72 passed
in7.04s (`U108-versioned-source-final.xml`); mandatory workspace gate63 passed in1.56s.
Staging uses reports/U108-stage-files.txt with explicit public paths only; owner exclusions remain
untracked. Raw failed JUnit receipts retain their measured trailing whitespace; source diff checks
exclude those raw data files rather than rewriting their evidence. Source and release code pass
whitespace checks. Next: commit through the enabled USB hook, then protected PR/main CI.

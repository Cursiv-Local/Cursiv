# Maintainability and verification hardening

> Publication follow-up: the owner subsequently authorized commit/push,
> packaging, release and website deployment. U83 stayed an unpublished candidate
> after a full-window smoke failure; U84 repairs it and expands that gate.
> Earlier status statements below record audit checkpoints. See
> [U84 verification](U84-RELEASE-VERIFICATION.md) for current publication results.

## Scope and status

Requested roadmap: structural maintainability, verification, packaging/platform
readiness, security and claim-to-evidence documentation. Work is on
`codex/maintainability-hardening`, based on main `8831241` and published U82 code
`f14c033`. No commit, push, version bump, release or website deployment has been
performed for this task. Existing `test_internals/` data is preserved/excluded.
The owner explicitly prohibited committing or pushing until instructed; that
restriction applies to all pending changes and to any follow-up reviewer.
The later [trust-boundary follow-up](TRUST-BOUNDARY-FOLLOWUP.md) audits the owner's
related checklist and closes remaining source/policy/partial-save/error gaps.
It supersedes earlier source-label wording and records the current regression
checkpoint; earlier logs and live samples remain evidence of their own source.
The later, separately authorized website photo-chat update is recorded at the
top of [HANDOFF.md](../HANDOFF.md). The combined pending-file inventory below now
includes its two website runtime files; it does not extend this desktop
maintenance scope or authorize a desktop release.

| Priority | Implemented / verified | Remaining |
|---|---|---|
| 1: structure | Chat/commands/views/dialog operations extracted with compatible APIs and explicit services; module-size regression guard. | Legacy mutable turn records remain; safe concurrent server sessions are separate work. |
| 2: verification | Structured findings, fail-closed check results, bounded rewrites and identical evidence rechecks; deterministic replay and live fixed-suite subset. | Heuristic/model limits remain; a six-case subset is not full-suite accuracy or field validation. |
| 3: packaging | Tagged-builder DLL-path isolation, packaged self-test gate, stable aliases/checksums; signing/Mac/Linux decisions documented. | Signing identity/service, future tagged package build, Mac CI/clean install and two physical Windows test PCs are external gates. |
| 4: security | Shared protected-mutation guard, protected-path regressions, portable-key/storage threat model. | Owner selected a separately documented encryption migration; no data migration is attempted here. |
| 5: process | Architecture, policy, evidence map, public limitations, README/changelog/handoff and readiness checklist. | Long-term field/regression evidence cannot be substituted with a numeric rating. |

## Confirmed findings

The later [asynchronous answer review follow-up](ASYNC-ANSWER-REVIEW.md) supersedes
the completion timing and default model-review behavior described in the earlier
hardening milestone. It records the exact incremental files, new controls,
isolated test snapshots and controlled performance results. Earlier live model
scores below apply to their recorded pre-background-review source snapshots.

1. Four production modules exceeded 1,200 physical lines: chat engine (3,607),
   command router (2,456), main window (1,817), and chat panel (1,693). Extracted
   implementations preserve original behavior and optional integration gates.
2. `verify.parse_verdict('')` returned clear. Although the old code withheld a
   verified learning origin when no verdict existed, `PassResult.clear` could
   still be true. Missing checker results and failed deterministic checks now
   have explicit unavailable/error outcomes.
3. Separate display warnings were not consistently inputs to rewrite acceptance.
   Draft and replacement now use the same evidence assessment; high-severity
   source/action/safety conflicts cannot be cleared by model prose.
4. Rejected replacement findings could expose a newly invented number in notes.
   Machine records retain the rejection; display notes retain original findings
   plus a generic rejection, without reproducing rejected replacement details.
5. Lookup-claim checks flagged quoted and conditional examples. The bounded
   assertion check now excludes those examples while retaining real lookup claims.
6. The shared filesystem layer denied sensitive data names but did not enforce
   the guardian-code write rule. One provider adapter's guard did not cover all
   native routes. `file_access._check_mutation()` now protects both confirmation
   preparation and every actual mutation operation. Read-only source analysis is
   still available. Link/traversal/content protections remain unchanged.
7. U82's documented DLL collision depended on the inherited build PATH. The
   tagged builder now isolates it and requires a frozen-app self-test before
   staging outputs. Helper tests do not constitute a newly built installer.
8. Encryption touches multiple direct conversation reads/writes and memory
   backups/archives/derived stores. The owner chose a separate migration plan;
   current personal stores remain unchanged/readable as documented.
9. Final review reproduced an optional-checker bypass of the no-inspection turn
   limit: `_check_context()` could recall saved memory even when inspection was
   forbidden. It now retains supplied conversation context while skipping stored
   recall. A failing regression reproduced the original behavior before the fix.
10. The subsequent U82 report/transcript exposed gates after dispatch, missing
    reference/calculator gates, prose suffixes interpreted as paths, absent tool
    provenance labels, and model continuations after failed tools. The
    [restricted-turn repair report](U82-RESTRICTED-TURN-REPAIR.md) records the
    root causes, exact execution paths, repairs and storage/model limitations.
11. The current-source live run detected an incorrect treatment dose but left
    the model instructions visible under a warning. Completion now withdraws
    detected dose/reference contradictions and displays the supplied reference
    with provenance/review status. This is application-owned output, not another
    model rewrite; no learning runs from the withdrawn draft.
12. The last metadata review found `_ref_evidence()` loading the reference table
    even with no supplied entries. It now returns before table access for empty
    evidence or a no-inspection turn. Exact-prompt tests prohibit both reference
    lookup and table loading, including post-response evidence assembly.

## Structural boundaries

See [ARCHITECTURE.md](../ARCHITECTURE.md). The public chat facade and command
entry points remain callable; extracted functions receive explicit runtime
services, retaining optional integrations and call overrides. Result classes
are shared in `launcher/command_results.py` and re-exported. `UNHANDLED` differs
from an intentional `None`, preserving ordered command precedence.

Chat controls/transcript methods remain Qt view methods on the GUI thread.
Existing incremental rendering, caches, streaming sentinels, copying, scrolling,
themes, tables and code blocks are exercised by the existing UI regressions.
The module budget includes physical lines, which is stricter than logic lines.

## Tests actually executed

All source tests run in disposable source/home/data snapshots; personal stores
and test_internals are excluded. The native Mac Keychain round-trip is skipped
on Windows, not claimed as passed.

| Stage | Result | Retained log |
|---|---|---|
| Original baseline | 1,080 passed, 1 skipped; 167.47 s | `cursiv-grounding-u0vjspoo/pytest.log` |
| Chat/commands/main view extraction | 1,080 passed, 1 skipped; 156.68 s | `cursiv-grounding-pbxn9cvs/pytest.log` |
| Verification and shared mutation focused checks | 169 passed, 1 failed initially; the failure exposed confirmation preparation still accepting a protected path. Fixed in the same shared guard. | `cursiv-grounding-rfije03s/pytest.log` |
| Hardening, dialogs, builder helpers | 1,141 passed, 1 skipped; 146.92 s | `cursiv-maintenance-8rz7jbka/pytest.log` |
| Pre-review source | **1,142 passed, 1 skipped; 142.46 s** | `cursiv-maintenance-j5asnrjp/pytest.log` |
| Privacy-boundary reproduction | 19 passed, 1 failed before the fix, as expected | `cursiv-maintenance-fq173lb8/pytest.log` |
| Reviewed source before additional U82 report | **1,143 passed, 1 skipped; 143.82 s** | `cursiv-maintenance-hachl1jp/pytest.log` |
| Initial restricted-turn focused suite | 162 passed, 1 failed; 10.18 s. The sole failure was the new test reading UTF-8 text with Windows' default codec; fixed the test's explicit encoding. | `%TEMP%/cursiv-maintenance-stz54i2g/pytest.log` |
| Restricted-turn full suite, resource-limited attempt | 1,173 passed, 1 skipped, 2 failed; 136.37 s. Both failures were OpenBLAS allocation failures in startup subprocesses, before application checks. | `%TEMP%/cursiv-maintenance-d7zm1mnu/pytest.log` |
| Restricted-turn full suite, bounded test-library threads | **1,175 passed, 1 skipped; 156.41 s**. `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` apply only to the test process. Preceded the last static-status/home-alias review. | `%TEMP%/cursiv-maintenance-n8wsb0qg/pytest.log` |
| Reviewed repair before live safety follow-up | **1,175 passed, 1 skipped; 154.44 s**. Includes static restricted status/persona context, no optional status probes and consistent direct/generic workspace paths. | `%TEMP%/cursiv-maintenance-_6gzgvg6/pytest.log` |
| Safety withdrawal follow-up | 1,176 passed, 1 skipped, 1 failed; 171.98 s. The existing emergency test expected only a warning; updated it to require draft withdrawal, the original reference and an application-owned source label. | `%TEMP%/cursiv-maintenance-bumpxgl6/pytest.log` |
| Complete safety follow-up source suite | **1,177 passed, 1 skipped; 185.30 s**. Same process-only numerical-library thread limits. Before the final metadata-only guard. | `%TEMP%/cursiv-maintenance-a6vr80pm/pytest.log` |
| Final complete source suite | **1,177 passed, 1 skipped; 167.34 s**. Includes the last reference metadata guard and stricter zero-table-loading assertions. | `%TEMP%/cursiv-maintenance-5ebnl5c5/pytest.log` |
| Background-review focused suite | **208 passed; 12.49 s**. Selector/call budgets, settings, isolated evidence, background lifecycle, rendering and policy checks. | `%TEMP%/cursiv-maintenance-eme3y4as/pytest.log` |
| Initial background-review full suite | 1,205 passed, 1 failed, 1 skipped; 162.90 s. One old grounding test assumed generic conversation always ran the model verifier; changed it to request full review explicitly, retaining its safety assertions. | `%TEMP%/cursiv-maintenance-mye4hr41/pytest.log` |
| Background review/grounding/persistence focused follow-up | **118 passed; 9.41 s**. Includes saved review reload and false-capability rewrite rejection. | `%TEMP%/cursiv-maintenance-112oap7s/pytest.log` |
| Final background-review source suite | **1,209 passed, 1 skipped; 176.73 s**. Includes the explicit Cross-check race guard; the only skip requires a Mac's Keychain. | `%TEMP%/cursiv-maintenance-u7nhk2vp/pytest.log` |
| Trust-gap reproduction before repair | 10 expected failures; 4.86 s, stopped at the configured ten-failure limit. | `%TEMP%/cursiv-maintenance-u41pbftm/pytest.log` |
| Trust follow-up initial focused run | 385 passed, 3 failed; 28.82 s. Exposed dated storage-error classification and ambient review/power dependencies in two test fakes. | `%TEMP%/cursiv-maintenance-gpbjxplc/pytest.log` |
| Trust follow-up focused repair | **388 passed; 46.32 s**. Includes source, policy, file-memory hard stops, review, USB and phone cases. | `%TEMP%/cursiv-maintenance-9yr8mxzt/pytest.log` |
| Final trust follow-up complete suite | **1,246 passed, 1 skipped; 299.62 s**. Includes expanded local/cloud restrictions and normal provider-budget compatibility; the skip requires a Mac's Keychain. | `%TEMP%/cursiv-maintenance-s8vnolr0/pytest.log` |

Logs/snapshot manifests are under the local task artifact directory:
`C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/`.
The subsequent U82 repair snapshots are under
`C:/Users/joshu/AppData/Local/Temp/`; the table identifies each exact folder.
The pre-safety-follow-up application's Python fingerprint was
`5702f355960e6931e1ca9d042688bf11fc830772a1c2f2d02d2f18697aec8c65`.
The safety-follow-up tested application/launcher fingerprint was
`1a4777478a1e114b67678210d2fc3e2a75f3ea7c667932313c4070c4a8c225d6`.
The pre-background-review tested application/launcher fingerprint was
`fae05d03e8eec1929adf395555b018fdd1029c0affddb945cb3e06bd8654d634`.
The pre-trust-follow-up background-review application/launcher fingerprint was
`2ea2f061cd06916a76ada19d72a92dcaa974207b1070f735041aec36cf65663e`.
The [background-review report](ASYNC-ANSWER-REVIEW.md) records
the exact new review paths, modes, 10/100/1,000-message measurements and limits.
The final trust-follow-up application/launcher fingerprint is
`15985868d5d3bcb9fbff8aad9955b5f46f05376a094573d9d016ed137683e278` and
matches its final tested snapshot. See [the current report](TRUST-BOUNDARY-FOLLOWUP.md)
for the latest supplied-memory/source changes, exact files and remaining gates.
AST parsing, the physical module budget and local documentation links were checked.
HEAD remains `8831241da3ffdaf14d181d3a0c2b4587b6a945e8`; the index is empty.
The preserved `test_internals/u81_test.txt` SHA-256 remains
`7e4671321c6521629865ece7160a74e9e38ad357aec835f3fabad95b4ae749ed`.

A focused early-order run also exposed a test fake retaining `_WORKED` because it
bypassed normal stream initialization; its fixture now resets that state. An
unprivileged loopback attempt failed with Windows access error 10013 and passed
when the same suite ran with the required permissions. Later attempts exhausted
Windows memory before tests produced results; those are not passing runs or
product test failures. The model cache was released and tests rerun sequentially
with a low-memory snapshot copier. Real fixture data was not altered.

## Deterministic regression replay

The new 16-case set is independent of the frozen Truth Benchmark. Eight failures
cover arithmetic, contradictory conclusions, doses, n=1 inference, fake search/
calculator claims and a wrong unit conversion; eight controls cover correct
answers and quoted/conditional examples. Each case uses identical evidence for
baseline and current checks. Raw results are retained:

- [Initial replay](../bench/results/verification-hardening-20261022.json).
- [Final replay](../bench/results/verification-hardening-final-20261022.json).

| Fixed replay metric | U82 | Current |
|---|---:|---:|
| Detected failures | 7/8 | 8/8 |
| Missed failures | 1 | 0 |
| False alarms on controls | 2/8 | 0/8 |

This is a regression measurement on selected examples, not an estimate of general
accuracy, a clinical benchmark or a live inference result. No old benchmark
question, score, source test data or historical result was changed.

## Live local-model subset

Model: installed `qwen3:4b-instruct`; offline mode, fresh temporary data/home,
background learning off. Unchanged Truth Benchmark **1.5** IDs:
`num-003,num-015,ref-002,ref-015,adv-011,saf-012`.

- [Released U82 baseline](../bench/results/U82-maintenance-baseline-20261022-qwen3_4b-instruct-subset-suite1.5.json): 6/6, zero case-marked unsupported claims, average 48.9 s.
- [Intermediate hardening run](../bench/results/maintenance-after-20261022-qwen3_4b-instruct-subset-suite1.5.json): 6/6, zero case-marked unsupported claims, average 58.2 s.
- [Later pre-review run](../bench/results/maintenance-final-20261022-qwen3_4b-instruct-subset-suite1.5.json): 6/6, zero case-marked unsupported claims, average 26.2 s. Its recorded Python-source fingerprint is `537c80cda7dc3d8296023c14895a7e798ef856658f89591501a0f1a492458751`.
- [Restricted-turn repair run](../bench/results/maintenance-restricted-repair-20261022-qwen3_4b-instruct-subset-suite1.5.json): **4/6**, zero case-marked unsupported claims, average 13.7 s, fingerprint `5702f355960e6931e1ca9d042688bf11fc830772a1c2f2d02d2f18697aec8c65`. `ref-015` gave a wrong dose despite the correct reference and a warning; this prompted the application-owned withdrawal fix. `adv-011` compared the different supplied quantities and selected one, but did not match the frozen scorer's conflict vocabulary. It also exposed a warning heuristic flagging an uncertainty phrase about source trust. These failures are retained, not discarded or rescored.
- [Reviewed safety run](../bench/results/maintenance-reviewed-safety-20261022-qwen3_4b-instruct-subset-suite1.5.json): **6/6**, zero case-marked unsupported claims, average 19.6 s. Fingerprint `1a4777478a1e114b67678210d2fc3e2a75f3ea7c667932313c4070c4a8c225d6` matches that tested source before the final metadata-only guard.
- [Final privacy-reviewed source](../bench/results/maintenance-final-privacy-20261022-qwen3_4b-instruct-subset-suite1.5.json): **5/6**, zero case-marked unsupported claims, average 22.7 s. Fingerprint `fae05d03e8eec1929adf395555b018fdd1029c0affddb945cb3e06bd8654d634` matches the final 1,177-pass tested source. `adv-011` compared the 4/8-drop sources and labeled its notebook-error explanation as an assumption, but missed the frozen scorer's conflict vocabulary. It remains a scored failure; neither question nor scorer was changed.

The earlier completed runs preceded the final optional-checker privacy guard or
subsequent repairs. They are retained as measurements of their own snapshots,
not relabeled as current-source results. The earlier
`maintenance-reviewed-final-20261022` attempt stopped before all six cases or a
result file were produced during severe Windows memory pressure; it is incomplete
and is not counted as passed. Shared system memory pressure and live model
variation preclude attributing elapsed-time differences to this patch.
No additional change targets the conflict-vocabulary scorer. Its narrow wording
check and the model's source-selection assumptions remain limitations. The
reference-trust warning can also overflag an explicitly unknown source; current
heuristics are not a general proof of support or contradiction.
The single 6/6 run does not establish full-suite model accuracy or prove that a
4B model will answer those questions correctly every time; the final run's 5/6
illustrates that limitation.

## Security and storage audit

Native commands, generic file dispatch, OpenAI/xAI/Claude adapters and GUI
confirmation converge on `core/file_access.py`. Notebook mutations continue
through `notebook_tools` and the original `fieldlog` backend; memory changes use
native intents/semantic storage. No notebook/memory schema or migration is added.

Trusted plugins and optional external agents can execute Python with process
privileges; they are not sandboxed by workspace-file guards. Installed API-key
protection can retain legacy/fallback plaintext; private portable keys are
deliberately readable. These are documented residual risks, not claims of OS
isolation or encrypted personal storage. See [threat model](THREAT-MODEL.md) and
[encryption migration plan](ENCRYPTION-MIGRATION-PLAN.md).

## Release/platform gates

No code-signing certificate was found in the current Windows user's certificate
store. No signing-service workflow is configured in this repository. Signing and
physical clean-machine tests cannot be completed by claiming that unit tests
replace them. Mac U82 automation is historical evidence, not a current-branch
Mac run. Linux packaged distribution remains explicitly unsupported. See
[platform readiness](PLATFORM-READINESS.md) and [FIELD-KIT-TEST.md](FIELD-KIT-TEST.md).

## Review priorities for Claude

- Runtime dependencies, default arguments, generator/decorator scope and optional
  provider routing across the extracted modules.
- Command precedence and UNHANDLED versus None; shared result class identities.
- Deterministic errors surviving CLEAR, unavailable checks, one rewrite maximum,
  replacement evidence/number checks and rejected-output display boundaries.
- Shared guardian guard for both confirmation and execution; original symlink,
  junction, hard-link, workspace and portable authorization rules.
- Builder isolation/self-test staging and the distinction between helper tests
  and a future signed/tagged installer.
- Restricted turns before classification, status/context reads, tool dispatch
  and retention; literal path/payload boundaries; successful execution provenance
  and early failed-tool exits in generic, OpenAI/xAI and Claude routes.
- Explicitly deferred encryption and external/manual platform gates.

## Combined release files versus main 8831241

The inventory includes the committed U83 candidate and U84 publication follow-up,
not just files currently uncommitted. See U84 verification for the rejected
candidate, repaired complete-window gate and final release results.

<!-- changed-files:start -->

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [HANDOFF.md](../HANDOFF.md)
- [PRIVACY.md](../PRIVACY.md)
- [README.md](../README.md)
- [TECH.md](../TECH.md)
- [bench/FAILURES-U83.md](../bench/FAILURES-U83.md)
- [bench/FAILURES-U84.md](../bench/FAILURES-U84.md)
- [bench/RESULTS.md](../bench/RESULTS.md)
- [bench/results/U82-maintenance-baseline-20261022-qwen3_4b-instruct-subset-suite1.5.json](../bench/results/U82-maintenance-baseline-20261022-qwen3_4b-instruct-subset-suite1.5.json)
- [bench/results/U83-qwen3_4b-instruct-suite1.5.json](../bench/results/U83-qwen3_4b-instruct-suite1.5.json)
- [bench/results/U84-qwen3_4b-instruct-suite1.5.json](../bench/results/U84-qwen3_4b-instruct-suite1.5.json)
- [bench/results/answer-review-background-20261022.json](../bench/results/answer-review-background-20261022.json)
- [bench/results/answer-review-blocking-20261022.json](../bench/results/answer-review-blocking-20261022.json)
- [bench/results/maintenance-after-20261022-qwen3_4b-instruct-subset-suite1.5.json](../bench/results/maintenance-after-20261022-qwen3_4b-instruct-subset-suite1.5.json)
- [bench/results/maintenance-final-20261022-qwen3_4b-instruct-subset-suite1.5.json](../bench/results/maintenance-final-20261022-qwen3_4b-instruct-subset-suite1.5.json)
- [bench/results/maintenance-final-privacy-20261022-qwen3_4b-instruct-subset-suite1.5.json](../bench/results/maintenance-final-privacy-20261022-qwen3_4b-instruct-subset-suite1.5.json)
- [bench/results/maintenance-restricted-repair-20261022-qwen3_4b-instruct-subset-suite1.5.json](../bench/results/maintenance-restricted-repair-20261022-qwen3_4b-instruct-subset-suite1.5.json)
- [bench/results/maintenance-reviewed-safety-20261022-qwen3_4b-instruct-subset-suite1.5.json](../bench/results/maintenance-reviewed-safety-20261022-qwen3_4b-instruct-subset-suite1.5.json)
- [bench/results/verification-hardening-20261022.json](../bench/results/verification-hardening-20261022.json)
- [bench/results/verification-hardening-final-20261022.json](../bench/results/verification-hardening-final-20261022.json)
- [bench/verification_cases.json](../bench/verification_cases.json)
- [cloudflare/tests/release-evidence.test.mjs](../cloudflare/tests/release-evidence.test.mjs)
- [cloudflare/worker.js](../cloudflare/worker.js)
- [cursiv_v215/chat/cloud_providers.py](../cursiv_v215/chat/cloud_providers.py)
- [cursiv_v215/chat/completion.py](../cursiv_v215/chat/completion.py)
- [cursiv_v215/chat/context.py](../cursiv_v215/chat/context.py)
- [cursiv_v215/chat/conversation.py](../cursiv_v215/chat/conversation.py)
- [cursiv_v215/chat/local_provider.py](../cursiv_v215/chat/local_provider.py)
- [cursiv_v215/chat/provenance.py](../cursiv_v215/chat/provenance.py)
- [cursiv_v215/chat/provider_tools.py](../cursiv_v215/chat/provider_tools.py)
- [cursiv_v215/chat/review.py](../cursiv_v215/chat/review.py)
- [cursiv_v215/chat/routing.py](../cursiv_v215/chat/routing.py)
- [cursiv_v215/chat/runtime.py](../cursiv_v215/chat/runtime.py)
- [cursiv_v215/chat/streaming.py](../cursiv_v215/chat/streaming.py)
- [cursiv_v215/chat/uploads.py](../cursiv_v215/chat/uploads.py)
- [cursiv_v215/core/answer_assessment.py](../cursiv_v215/core/answer_assessment.py)
- [cursiv_v215/core/answer_check.py](../cursiv_v215/core/answer_check.py)
- [cursiv_v215/core/crosscheck.py](../cursiv_v215/core/crosscheck.py)
- [cursiv_v215/core/file_access.py](../cursiv_v215/core/file_access.py)
- [cursiv_v215/core/grounding.py](../cursiv_v215/core/grounding.py)
- [cursiv_v215/core/presence.py](../cursiv_v215/core/presence.py)
- [cursiv_v215/core/problems.py](../cursiv_v215/core/problems.py)
- [cursiv_v215/core/selfknow.py](../cursiv_v215/core/selfknow.py)
- [cursiv_v215/core/tools.py](../cursiv_v215/core/tools.py)
- [cursiv_v215/core/turn_policy.py](../cursiv_v215/core/turn_policy.py)
- [cursiv_v215/core/verify.py](../cursiv_v215/core/verify.py)
- [cursiv_v215/memory/intents.py](../cursiv_v215/memory/intents.py)
- [cursiv_v215/ui/chat_app.py](../cursiv_v215/ui/chat_app.py)
- [docs/ASYNC-ANSWER-REVIEW.md](../docs/ASYNC-ANSWER-REVIEW.md)
- [docs/CLAIM-EVIDENCE.md](../docs/CLAIM-EVIDENCE.md)
- [docs/ENCRYPTION-MIGRATION-PLAN.md](../docs/ENCRYPTION-MIGRATION-PLAN.md)
- [docs/FIELD-KIT-TEST.md](../docs/FIELD-KIT-TEST.md)
- [docs/MAINTENANCE-HARDENING.md](../docs/MAINTENANCE-HARDENING.md)
- [docs/PLATFORM-READINESS.md](../docs/PLATFORM-READINESS.md)
- [docs/QUALITY-CHECKLIST.md](../docs/QUALITY-CHECKLIST.md)
- [docs/RELEASE-U83.md](../docs/RELEASE-U83.md)
- [docs/RELEASE-U84.md](../docs/RELEASE-U84.md)
- [docs/THREAT-MODEL.md](../docs/THREAT-MODEL.md)
- [docs/TRUST-BOUNDARY-FOLLOWUP.md](../docs/TRUST-BOUNDARY-FOLLOWUP.md)
- [docs/U82-RESTRICTED-TURN-REPAIR.md](../docs/U82-RESTRICTED-TURN-REPAIR.md)
- [docs/U83-RELEASE-VERIFICATION.md](../docs/U83-RELEASE-VERIFICATION.md)
- [docs/U84-RELEASE-VERIFICATION.md](../docs/U84-RELEASE-VERIFICATION.md)
- [docs/VERIFICATION-POLICY.md](../docs/VERIFICATION-POLICY.md)
- [installer/cursiv_setup.iss](../installer/cursiv_setup.iss)
- [launcher/chat_commands.py](../launcher/chat_commands.py)
- [launcher/chat_controls.py](../launcher/chat_controls.py)
- [launcher/chat_panel.py](../launcher/chat_panel.py)
- [launcher/chat_review.py](../launcher/chat_review.py)
- [launcher/chat_transcript.py](../launcher/chat_transcript.py)
- [launcher/command_agents.py](../launcher/command_agents.py)
- [launcher/command_dispatch.py](../launcher/command_dispatch.py)
- [launcher/command_media.py](../launcher/command_media.py)
- [launcher/command_results.py](../launcher/command_results.py)
- [launcher/command_runtime.py](../launcher/command_runtime.py)
- [launcher/command_support.py](../launcher/command_support.py)
- [launcher/commands_credentials.py](../launcher/commands_credentials.py)
- [launcher/commands_extensions.py](../launcher/commands_extensions.py)
- [launcher/commands_images.py](../launcher/commands_images.py)
- [launcher/commands_notes.py](../launcher/commands_notes.py)
- [launcher/commands_postal.py](../launcher/commands_postal.py)
- [launcher/commands_research.py](../launcher/commands_research.py)
- [launcher/commands_services.py](../launcher/commands_services.py)
- [launcher/commands_system.py](../launcher/commands_system.py)
- [launcher/cursiv_launcher.py](../launcher/cursiv_launcher.py)
- [launcher/login_dialog.py](../launcher/login_dialog.py)
- [launcher/login_recovery.py](../launcher/login_recovery.py)
- [launcher/login_style.py](../launcher/login_style.py)
- [launcher/relay_settings.py](../launcher/relay_settings.py)
- [launcher/selftest.py](../launcher/selftest.py)
- [launcher/setup_checks.py](../launcher/setup_checks.py)
- [launcher/setup_checks_runtime.py](../launcher/setup_checks_runtime.py)
- [launcher/setup_dialog.py](../launcher/setup_dialog.py)
- [launcher/shell_dialogs.py](../launcher/shell_dialogs.py)
- [launcher/usb_maker.py](../launcher/usb_maker.py)
- [launcher/usb_ops.py](../launcher/usb_ops.py)
- [launcher/usb_ops_runtime.py](../launcher/usb_ops_runtime.py)
- [scripts/benchmark_chat_rendering.py](../scripts/benchmark_chat_rendering.py)
- [scripts/benchmark_verification.py](../scripts/benchmark_verification.py)
- [scripts/build_release.py](../scripts/build_release.py)
- [scripts/truth_bench.py](../scripts/truth_bench.py)
- [tests/test_answer_check.py](../tests/test_answer_check.py)
- [tests/test_background_review.py](../tests/test_background_review.py)
- [tests/test_chat_rendering.py](../tests/test_chat_rendering.py)
- [tests/test_grounded_chat.py](../tests/test_grounded_chat.py)
- [tests/test_module_boundaries.py](../tests/test_module_boundaries.py)
- [tests/test_offline_process.py](../tests/test_offline_process.py)
- [tests/test_protected_mutations.py](../tests/test_protected_mutations.py)
- [tests/test_release_build.py](../tests/test_release_build.py)
- [tests/test_reliability.py](../tests/test_reliability.py)
- [tests/test_replace_draft.py](../tests/test_replace_draft.py)
- [tests/test_restricted_regressions.py](../tests/test_restricted_regressions.py)
- [tests/test_trust_boundary_followup.py](../tests/test_trust_boundary_followup.py)
- [tests/test_verification_hardening.py](../tests/test_verification_hardening.py)
- [tests/test_verified_filesystem.py](../tests/test_verified_filesystem.py)
- [tests/test_verify.py](../tests/test_verify.py)
- [website/ai-reliability-testing.html](../website/ai-reliability-testing.html)
- [website/app.html](../website/app.html)
- [website/index.html](../website/index.html)
- [website/notebook/index.html](../website/notebook/index.html)
- [website/notebook/sw.js](../website/notebook/sw.js)
- [website/start.html](../website/start.html)
- [website/vision.html](../website/vision.html)

<!-- changed-files:end -->

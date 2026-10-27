Cursiv: agent reliability and efficiency work after U106

Status: approved direction for a future implementation; no fixes have been implemented by this brief.

Requested by Joshua, October 26, 2026: schedule this work after U106; fix everything broken in the audited agent workflows; make the existing agents highly efficient. Assign the release number after reviewing the completed U106 source.

## Objective and completion rule

Make Cursiv's existing research agents dependable, evidence-grounded, and economical enough to use routinely. Repair the broken connections between roles, evidence, calculations, routing, checks, and queued execution before adding capabilities.

Every confirmed defect below must be fixed and covered by a regression test. Any additional reproducible defect found in these agent workflows must be tracked and resolved before this work is declared complete. An unavailable dependency, incomplete task, or failed check must be reported accurately. Disabling a broken feature or changing its description is not a substitute for completing a required repair.

This requirement covers the audited agent workflows and their shared dependencies. It does not assert that an entire software product can be proven free of every possible bug.

Keep the existing five profiles: `@field`, `@checker`, `@protocol`, `@report`, and `@writer`. Keep their current read-only authority. Add a role only when a measured task demonstrates value that cannot reasonably be delivered by an existing role or deterministic operation. Do not add a second agent framework, new top-level folder hierarchy, self-editing agents, or unrestricted tool access.

## Baseline and source of findings

The audit examined `Cursiv-main (4).zip`, supplied at `C:\Users\joshu\OneDrive\Desktop\Cursiv-main (4).zip`. Its documentation identifies U105 as the current release. The archive contained 703 files and 373 Python files; all Python files parsed successfully.

The audit read the archive without extracting or modifying files. It traced the relevant runtime paths and ran isolated, in-memory checks with fake dependencies. Those checks reproduced the plural-command dispatch failure, the group workflow's missing profile evidence, and the queue adapter's placeholder executor. They also confirmed the deterministic checker findings, the protocol no-result guard, and the profile number/unit warning. The full application and full test suite were not run during the audit.

The preceding ChatGPT conversation exposed placeholders instead of the original proposed fleet text. This brief is grounded in the inspected implementation, not an assumed list of previously proposed agent names.

Before implementation, compare every finding with the actual post-U106 source. Record findings already fixed by U106 as verified, with the relevant test and revision. Do not reintroduce old code merely to match this archive. File references and line numbers below are archive-relative under `Cursiv-main/` and may move after U106.

## Existing implementation to reuse

| Responsibility | Existing source and entry points |
|---|---|
| Profile definitions | `cursiv_engine/agents/starters/{field,checker,protocol,report,writer}.md` |
| Profile registry, personal overrides, and prompts | `cursiv_engine/agents/custom.py`: `starters()` line 73, `load()` line 86, `everyone()` line 122, `messages_for()` line 276 |
| Profile evidence and findings | `cursiv_engine/agents/profile_context.py`: `findings()` line 26, `notebook_block()` line 49, `documents_block()` line 73, `calculation_block()` line 85, `answer_note()` line 95, `context()` line 119 |
| Agent commands | `launcher/command_agents.py`: `_agent_command()` line 143; `launcher/commands_extensions.py`: `handle()` line 12 |
| Desktop dispatch and delivery | `launcher/command_dispatch.py`: `handle_command()` line 24; `launcher/chat_panel.py`: `_run_turn()` line 568, `_deliver_result()` line 706 |
| Ordinary chat and provider routing | `cursiv_engine/chat/completion.py`: `chat()` line 54; `conversation.py`: `_chat_inner()` line 15; `routing.py`: `cascade_stream()` line 15 |
| Tools and action boundaries | `cursiv_engine/core/tools.py`: `plan()` line 157, `run()` line 191; `core/file_access.py`; `core/turn_policy.py`; `chat/provider_tools.py` |
| Documents | `cursiv_engine/core/documents.py`: `search()` line 183, `instruction_flags()` line 238, `prompt_block()` line 255, `cited_pages_problems()` line 290 |
| Notebook, calculations, and summaries | `cursiv_engine/core/fieldlog.py`: `current()` line 490, `verify()` line 502, `site_summary()` line 905; `field_recall.py`: `stats_command()` line 177; `calc.py`: `work_out()` line 158; `fieldcalc.py`; `fieldsci.py` |
| Evidence and review | `cursiv_engine/core/grounding.py`, `evidence_log.py`, `answer_assessment.py`, `claims.py`; `chat/review.py`: `prepare()` line 104; `core/verify.py`: `run_pass()` line 657 |
| Investigation journal | `cursiv_engine/core/curiosity_engine.py`: `candidates()` line 35, `evaluate()` line 89; `core/curiosity.py` |
| Deferred tasks | `cursiv_engine/agents/offline_queue.py`: `flush()` line 59; `cursiv_engine/chat/context.py`: `execute_tool()` line 39 |
| Existing regression locations | `tests/test_starter_profiles.py`, `test_module_boundaries.py`, `test_background_review.py`, `test_portable_recall_curiosity.py`, `test_turn_policy.py`, `test_plugin_isolation.py`, and the existing document/notebook/workspace suites |

## Required repairs

### R1. Make public agent commands reach the intended workflow

Confirmed defect: the group handler recognizes `agents ask ...`, but the outer dispatch condition at `launcher/commands_extensions.py:74` does not. `agent council ...` and `@field ...` reach the handler; the advertised plural command returns `UNHANDLED` from that domain.

Fix the command boundary and test it through the real command entry point, not only `_agent_command()` in isolation. Preserve aliases, personal-agent management, native notebook/file precedence, and restricted-turn behavior. A malformed agent command must receive an actionable application response, not silently become an ordinary model answer pretending the agents ran.

Acceptance: `agents ask`, its supported alias, explicit profile invocation, unknown names, missing questions, whitespace/case variants, and restricted turns all follow their documented paths. Actual role execution is recorded separately from a request to execute it.

### R2. Give group runs the same permitted evidence as individual profiles

Confirmed integration failure: `launcher/command_agents.py:178` selects `custom.all_agents()`, takes the first three saved agents, and calls `messages_for()` without `profile_context.context()`. Shipped starters are absent unless personally copied. Group runs therefore do not perform the profile-specific notebook retrieval/checking that an individual `@name` invocation performs.

Use one registry with personal overrides taking precedence. Make shipped profiles available to explicit group selection without forcing a user to edit or teach them first. Document any deliberate distinction between personal-agent defaults and starter selection.

Replace the arbitrary first-three selection with the smallest relevant role set. Respect explicitly requested names. When a request exceeds the supported run budget, explain the limit and offer a bounded split; never silently drop named roles. Report which profiles actually participated.

Build one consistent evidence snapshot for the run, then give each role only its permitted view. Retrieve notebook records, verify integrity, search documents, and compute each requested aggregate once per run where their scopes are identical. Preserve source IDs and findings through synthesis. A profile's failed or unavailable evidence must stay failed or unavailable downstream.

Acceptance: the same profile receives equivalent authorized evidence when invoked alone or in a group. Tests capture actual supplied evidence, enforce role-specific exclusions, exercise personal overrides, and verify that a synthesis cannot claim an unexecuted check.

### R3. Bring agent outputs under shared evidence and checking rules

Confirmed gap: profile command results stream directly through `_deliver_result()`. They bypass the normal `chat/completion.py` checking/review path. The individual profile branch adds only `profile_context.answer_note()`; the group branch does not apply that note either.

Extract or reuse the necessary checks without invoking a second full chat turn, repeating retrieval, or broadening permissions. Apply deterministic checks to specialist outputs that feed another stage and to the final answer. Use the existing review modes and cancellation behavior for optional model review.

Required checks include supplied document/page references, notebook record IDs, calculated values and units, unsupported execution claims, and application-owned source labels. Reuse document-instruction detection and the applicable memory-withholding behavior for profile retrieval. Retrieved documents and another profile's prose remain untrusted data.

Maintain the protocol no-result hard stop. A retrieved passage is not proof that every generated claim is supported. Detectable unsupported citations or changed critical quantities must result in a correction, withdrawal, or explicit unresolved finding; a model's `CLEAR` verdict cannot override contradictory evidence.

Audit capability descriptions against the actual execution path. Saved `tools` fields, profile text, and personal overrides must not claim or grant powers the application does not enforce. Include any intentionally supplied personal memory in the real permission/provenance accounting.

Acceptance: fabricated pages/record IDs, changed numbers, invented units, document instructions, false save/check claims, missing evidence, and unavailable checks are exercised through both individual and group entry points. No empty checker response is treated as success. Final synthesis cannot erase a specialist's unresolved evidence failure.

### R4. Connect report statistics and make coverage explicit

Confirmed gap: `profile_context.calculation_block()` calls `calc.work_out(question)` but does not automatically obtain notebook aggregates for a broad report request. Notebook context currently shows the latest 60 records, and document search defaults to three passages.

Use the existing notebook query and aggregation functions for requested counts, averages, ranges, and other supported statistics. Define the requested site/sample/date scope, apply corrections, preserve units, identify missing/non-numeric values, and calculate in code. Do not average mixed units without an explicit supported conversion.

Distinguish full-scope aggregation from the bounded evidence excerpts shown to the model. Include total matching records, records used in each calculation, omitted records and reasons, document coverage, and any truncation. A report must not claim to summarize the entire notebook from a recent-record slice. Page or select evidence within a budget instead of making prompts unbounded.

Acceptance: reports over more than 60 records, old relevant samples, corrected entries, multiple sites, missing units, mixed units, and no matching documents give exact code-computed results and truthful coverage. Unsupported analyses return a clear limitation instead of an invented statistic.

### R5. Finish deferred-task execution and persistence

Confirmed defect: `chat/context.py:90` flushes the queue using `lambda p: "[flush requires active connection]"`. `offline_queue.flush()` treats that returned string as completion and can mark work fired without executing it.

Replace the placeholder with a real, authorized, bounded executor. Represent outcome explicitly; model text or an error-shaped string must not establish success. Check whether each task actually requires a connection, whether the required provider/dependency is available, and whether its permission remains valid. Enqueuing text does not grant unlimited future tools or unattended network access.

Use stable task IDs and explicit pending/running/succeeded/failed-or-blocked/cancelled semantics, preserving legacy records through a tested migration or compatibility reader. Provide an explicit retry path. Make state persistence atomic, coordinate enqueue/flush/cancel operations, and retain task history and useful failure details.

Prevent duplicate dispatch during concurrent flushes. On interrupted execution, preserve an honest recoverable state. Where an external side effect cannot be proven absent or deduplicated, mark the outcome uncertain and require reconciliation before retry; do not promise exactly-once execution without a mechanism that establishes it.

Acceptance: a task is successful only after a real executor result. Offline, missing-key, provider error, empty result, timeout, cancellation, restart, duplicate flush, simultaneous enqueue, damaged queue data, and failed persistence never silently discard work or claim completion. Test with fake executors; no test may replay real owner tasks.

### R6. Establish a safe bounded workflow runtime

The current group sequence is a few model answers followed by synthesis. It does not establish safe concurrent research workers. `ui/chat_app.py:650` retains shared mutable turn records, and `ARCHITECTURE.md:156` acknowledges the concurrency limitation.

Introduce only the small run/task/evidence/result abstractions needed to complete these repairs. Each run must own its evidence snapshot, stage results, selected roles, provider identity, budgets, cancellation, and status. Keep model prose separate from execution receipts and source truth.

Serialize shared local-model work by default. Multiple profiles can share a model; they do not need separate loaded models or parallel inference. Any request surface that can overlap runs must either safely isolate them or explicitly serialize them. Cancellation and conversation/person/workspace changes must reject stale results and prevent later stages from launching.

Keep optional Hermes and the external Codex bridge accurately labeled as integrations requiring their dependencies. They are not prerequisites for the repaired research profiles. Keep the old general council marked removed, distinguish the coding review pair from research coordination, and describe the Fleet Dashboard as a device view. Remove misleading active-capability claims after checking compatibility; no speculative legacy-code deletion is required.

Acceptance: overlapping requests cannot exchange evidence, person context, permissions, or review state. Cancelling a run prevents new stages and stale UI/queue success. A failed stage has an explicit policy for stopping or continuing with visibly incomplete evidence. No placeholder can stand in for a completed dependency.

## Efficiency requirements

Efficiency means the smallest amount of computation that meets the task and evidence requirements. Lower latency obtained by dropping checks, omitting requested records, hiding failures, or degrading answers does not qualify.

1. Route familiar requests with code. Do not add a model call just to choose between five known profiles. Explicit `@name` selection wins within its permissions. Ambiguous routing should ask a short question or use the existing general path rather than launch every role.
2. Prefer code-only answers for deterministic notebook checks, statistics, capability/permission questions, empty retrieval, and execution receipts. Use a model when an explanation or composition adds value.
3. Reuse evidence within a run. Key any cross-run cache by the actual source revision/content digest, query/scope, current permissions, person/workspace, and calculation method. Invalidate on relevant changes. Never reuse a stale integrity verdict after the log changes, or share private cached material across people.
4. Keep handoffs small and structured: findings, source references, computed results, unresolved issues, status, and coverage. Keep complete artifacts available separately. Do not concatenate full transcripts or repeat every role's system prompt inside the synthesis input. Avoid the current blind 1,500-character slicing when it could cut a source reference or warning.
5. Use a single currently loaded local model where suitable. Switch models only for a demonstrated task benefit. Start no model download or cloud review as an incidental efficiency measure. Preserve configured offline and provider permissions.
6. Run one role when one is enough; skip synthesis for a single effective result. Request multiple perspectives only when they add distinct work. Explicitly requested creative perspectives remain supported within the run budget.
7. Run deterministic validation without extra inference. Review the final composed answer once when eligible; do not automatically run a model critic after every stage. Preserve the existing distinction between fast review and explicitly selected full review.
8. Enforce run-level limits across provider adapters, fallbacks, retries, review, and rewriting. A provider change does not reset the budget. Count attempted requests, including failures, separately from successful generations.

The following are initial implementation limits, not measurements of the current system. Validate and document them on the post-U106 baseline:

| Run | Normal generation work | Default attempted-model-request ceiling |
|---|---|---|
| Deterministic answer or no-result response | No generation or model review | 0 |
| Individual profile | One answer, with at most one eligible fast review | 2 total, including failed attempts/fallbacks |
| Group workflow | At most three relevant specialists and one synthesis; omit unnecessary stages | 5 total in fast mode, including review, failed attempts, retries, and fallbacks |
| Explicit full review | Same bounded generation work; at most one verdict, one rewrite, and one recheck | 4 total for an individual or 7 for a group, including every attempted request |

A run can finish below its ceiling. If failure consumes the remaining budget, return an accurate incomplete result and offer a deliberate retry. Do not silently skip mandatory deterministic checks or present an unreviewed answer as reviewed. Existing internal transport retries must participate in the same accounting.

Set input/output token and wall-clock budgets from the effective installed model context and measured hardware capability. Account for system instructions, tool schemas, history, evidence, output reservation, and review. Keep enough output for requested report detail; a short specialist answer and a long report need different budgets. Budget exhaustion and cancellation must stop subsequent work, with truthful status.

## Proof of quality and speed

Capture a reproducible baseline on the completed U106 source before changing runtime behavior. Use disposable fixtures and pin the model, inference settings, hardware class, offline/provider settings, and prompt set. Record the original archive reproductions separately from the U106 baseline.

Compare ordinary chat, explicit individual profiles, the current group path where executable, and the repaired efficient workflow on identical inputs. Keep an untouched benchmark set separate from prompts used during development.

The task set must cover all five profiles, direct and group commands, personal overrides, protocol hits/misses/conflicts, fabricated citations, large notebooks, exact aggregates, ambiguous requests, document instructions, restricted turns, queue failures/restarts, cancellation, and overlapping requests. Include ordinary writing and field questions so that improvements are not measured only on tasks designed for three agents.

Record attempted and successful model calls, input/output tokens, cache hits, retrieval/calculation counts, loaded-model switches, first-token time for generated answers, total completion time, optional-review completion time, median and p95 latency, peak memory, task correctness, and supported versus unsupported source/action claims. Label measured, estimated, and unavailable metrics distinctly. Timings and aggregate telemetry must not expose private prompts or records by default.

Initial acceptance targets:

- Every confirmed defect in R1-R6 has a regression that fails on the affected baseline and passes after the repair, or documented evidence that U106 already fixed it. Architectural additions need behavioral tests rather than an artificial old-code failure.
- All deterministic fixture findings, calculations, and required no-result/failure states are correct. No tested fabricated citation, invented execution success, unauthorized access, cross-run evidence leak, or stale result is presented as valid.
- Quality on the untouched task set does not regress against the strongest applicable existing path. Report unresolved model limitations honestly; a checker is not a general proof of truth.
- On the representative mixed workload, target at least 25% lower median total model tokens and 20% lower median end-to-end latency than the existing fixed three-specialist-plus-synthesis workflow, measured with the same model and hardware. These are future acceptance targets, not claimed results. Keep tasks that the old workflow cannot perform in a separate correctness comparison.
- Individual profile median and p95 completion times must not regress by more than 10% when comparing equivalent evidence scope and review settings; explain cold-start variance separately. If necessary evidence checks expose an unavoidable tradeoff, report it explicitly instead of weakening them to meet the target.
- Demonstrate the model-request ceilings with instrumentation, including injected provider failures and internal retries. Demonstrate that simple deterministic requests make zero model calls.

Do not declare the efficiency objective achieved from fake-provider timings alone. Use fake providers for deterministic failure coverage and real local inference for performance evidence. If targets are missed, optimize and retest, or present the specific unmet target for an explicit decision; do not silently lower it.

## Implementation sequence and scope

1. Reconcile the audit against completed U106, inventory defects and existing tests, and capture the baseline.
2. Repair command dispatch and registry/selection behavior with entry-point regressions.
3. Introduce the minimum shared run/evidence/result boundary, then connect individual and group evidence, report aggregates, and shared checks.
4. Complete real queue execution, persistence, recovery, and concurrency/cancellation behavior.
5. Apply evidence reuse, small structured handoffs, deterministic routing, model reuse, and shared budgets.
6. Run focused regressions, existing affected integration/release gates, the full supported test suite, and the real-model quality/performance comparison. Record platform-specific skips and failures accurately.
7. Update the code map, architecture, capability descriptions, command help, relevant privacy/queue documentation, changelog, handoff, and release verification evidence. Review final scope and remaining limitations before proposing a release.

Keep engine behavior in `cursiv_engine/`; launcher modules should adapt commands and present results. Reuse `agents/`, `chat/`, `core/`, `memory/`, and the existing tests. A focused workflow module under `agents/` is acceptable if it has real ownership; do not create folders for imagined future agents. Avoid expanding the already large chat facade or notebook backend.

An independent literature crawler, distributed agent network, unrestricted browser/terminal agents, autonomous experiment execution, and a general-purpose workflow platform are outside this repair. Existing web search remains opt-in and subject to the network gate. Additional literature-research capability requires its own demonstrated use case and source-quality evaluation.

Implementation is complete only when the repaired paths work, their failure states are honest, the applicable test gates pass, and the efficiency results are published with their reproducible configuration. Provide a final defect-to-fix-to-test table and before/after measurements. Make any unmet requirement visible instead of marking it complete.
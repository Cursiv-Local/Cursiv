# U107 agent reliability validation

Reviewed implementation evidence, captured before the U107 release version bump. Baseline is
post-website main `2a639325f60bb3a6b911c83ebb99502339227970`; its engine matches released U106.
This document reports local Windows implementation evidence. Tagged CI/packages/publication are
recorded separately in the handoff and release verification, once completed.

## Defect → repair → regression

| Item | Confirmed before | Repair and proof |
|---|---|---|
| R1 public commands | All six real `agents ask` requests missed dispatch; entry-point tests had 9 failures/3 passes. | Plural/case/whitespace dispatch, actionable malformed/unknown commands, preserved native/restricted precedence. `test_agent_workflows.py`; baseline `U107-command-before.xml`. |
| R2 registry/evidence | Old group selected three personal profiles, omitted starters/evidence and silently dropped later names. | One registry with overrides; deterministic selection and explicit three-role limit; one snapshot with permitted per-role views and run-local aggregate reuse. Actual-entry evidence, override, exclusion, selection and reuse tests. |
| R3 checking/permissions | Old group displayed fabricated notebook IDs, values and document pages. Streams bypassed shared assessment. Saved tools could advertise unimplemented powers. | Deterministic/shared checks on drafts and synthesis; unknown/malformed record and page references, changed quantities, units, method-bound statistics and action/source claims withdraw drafts. Known evidence failures stop before any model role. Detected document instructions withhold teaching/history/style across the run and their numeric instructions cannot become factual quantities. Saved tools grant nothing. Tests cover individual/group, empty checker, citation styling, false missing units and model CLEAR limits. |
| R4 complete statistics | Old individual report used a recent slice, claimed 55 records and never finished correct arithmetic. | Full bounded verified scan, corrections before site/sample/date/measurement/entry/latest-N filters, unit-preserving code counts/mean/median/range, explicit omissions and mixed-unit refusal. Native coverage distinguishes full calculations from AI excerpts; full narratives beyond the excerpt budget request scope. >60-record/correction/date/site/missing/nonnumeric tests; exact Pond report below. |
| R5 deferred tasks | Baseline executor placeholder was persisted as `fired`. | Typed outcomes, atomic writes, OS locks, durable claims, bounded native local-only executor, cancellation/retry/history/legacy compatibility and reconciliation after uncertainty. Concurrent process/flush/enqueue, damage, persistence failure and restart tests. Real synthetic queued task completed in one Qwen request. |
| R6 run ownership | No owned research boundary; a chunk cancelled during `next()` could still display. | Run-owned stages/evidence/budgets; whole-turn/model serialization; person/profile/workspace guards; Qt acceptance rejects stale text/history and releases controls after cached settings or underlying authorization change. Separate person-switch revision preserves legitimate memory deletion. Actual Qt tests, transport guards, owner-bound usage metadata and retained concurrent teaching. |

Focused checks and new regressions live in `tests/test_agent_workflows.py`, `test_agent_evidence_runs.py`,
`test_agent_request_budgets.py`, `test_agent_ui.py` and `test_deferred_tasks.py`. Existing document,
starter-profile, verification, background-review, workspace, plugin and desktop tests remain active.
Architectural additions are tested behaviorally; baseline defects are additionally reproduced through
original entry points, real baseline answers, or the trusted baseline queue/iterator source.

## Real model method and results

All application stores were redirected **before imports**. Data is synthetic: 86 notebook entries
(84 numbered temperatures plus two duplicate-ID/problem records), and two `Procedures.txt` passages.
No owner notebook, queue, profile, secret or external service was used. No Gemma work or model download.

Pinned model: `qwen3:4b-instruct`, digest
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`; temperature 0,
seed 42, context 8192, offline/provider permissions local-only, fast review. Hardware: NVIDIA
GeForce RTX 2050 / 4096 MiB. Final performance inference ran separately from the full test suite.

Six original tasks cover field guidance, two writing requests, checker, protocol and report, with
ordinary/individual/old-alias/plural paths. The three ordinary field/writing tasks are the comparable
performance subset. Record-dependent tasks are separate correctness comparisons: the old group did
not provide their evidence. p95 uses linear interpolation; n=3 is descriptive, not a population claim.

| Comparable routine subset (n=3) | Before | After |
|---|---:|---:|
| Group attempted/successful model requests | 12 / 12 | 2 / 2 |
| Median total model tokens per task | 2809 | 530 |
| Group median completion time | 12.352 s | 2.049 s |
| Group p95 completion time | 22.641 s | 2.323 s |
| Individual median completion time | 2.531 s | 2.171 s |
| Individual p95 completion time | 6.373 s | 2.673 s |

Measured group reductions: **81.13% tokens, 83.41% completion latency**. Individual median/p95 were
**14.21% / 58.05% faster** on equivalent requested task scope and review eligibility. The new field
guidance removes irrelevant private context and uses native recording rules; writing still uses a
model. These measured sample results meet the initial 25%/20% performance targets and 10% individual
regression bound. They do not establish the same gains for arbitrary tasks or hardware.

Across all six tasks, group requests fell 24→4. Ordinary chat remained a separate control (7→7
requests); its notebook/file routing limitations were not silently counted as repaired profile work.
Its six-task median was 5.828→6.514 seconds (11.8% slower); no ordinary-chat speed gain is claimed.
Native tips/checks/statistics use zero model requests; writing uses one; protocol used two including
one final review. Injected failed HTTP retries prove individual fast/full limits 2/4 and group 5/7.
Failure consumes the same ceiling; no fallback/reset or empty checker becomes success.

The fixture has **82 current Pond records before the measurement filter; 81 matching temperature
records/measurements, 80 usable numeric temperatures, mean 12 C, range 10–14 C, one nonnumeric
reading and one Pond record excluded for having no temperature measurement**.
The checker finds both duplicated sample IDs, the missing nitrate unit and the nonnumeric value.
Protocol answers preserve **unpreserved 48 hours / preserved 28 days**, both citing supplied page 2.

## Quality accounting and limits

The original evaluation was initially frozen before results. Observed failures then informed repairs,
so later runs of those prompts are labelled regression/performance retests. Intermediate confirmation
results are retained, including wrong generic-sample scope, retrieval misses, citation over-rejection,
and correctly withdrawn invented-unit drafts. They are not relabelled as passes.

Five final holdout questions were written before their first results and were not used for runtime
tuning. They first satisfied the task in the individual, alias-group and plural paths (15/15).
Subsequent source-validation reruns are regression checks of this previously seen set. On the original
six-task retest these paths satisfied the requested substance 18/18, versus 6/18 on the baseline
(including six unhandled plural commands). Labels are **Codex manual review of synthetic answers**,
not independent human/professional grading or broad linguistic-accuracy evidence.

The final original writing retest adds “soon” to an undecided schedule, and the notice adds “gather
early.” Both preserve the requested placeholders/current uncertainty but add unrequested timing
rhetoric; the holdout rewrite preserves uncertainty without that addition. General prose still needs
human judgment. Passing these source/action checks does
not prove every sentence true. Unsupported analyses and missing evidence remain explicit limitations.

Ollama terminal events supply actual input/output tokens, model identity, load duration and request
first-token times. Completion and first-display times are measured separately: checked workflow
answers are buffered before display. Cache hits and peak process/server memory are **unavailable**,
not zero or estimated. The first ordinary baseline call includes cold load; group/individual routine
comparison follows it. Default production counters contain no private prompt/answer text. Only the
explicit synthetic benchmark stores raw answers.

## Receipts and reproduction

- Baseline: `bench/results/U107-agent-live-before.json`, `U107-agent-structural-before.json`, `U107-command-before.xml`.
- Final model runs: `U107-coverage-live.json`, `U107-coverage-holdout.json`.
- Analysis: `U107-coverage-comparison.json`, `U107-coverage-quality.json`; earlier labels/results retained.
- Queue/cancellation before/after: `U107-queue-and-cancellation-proof.json`.
- Desktop preview: `U107-ui-checker-coverage.png`, `U107-ui-report-coverage.png` (real offscreen Qt, synthetic data).
- Focused boundary regressions: `U107-coverage-focused.xml` — 117 passed in 20.52 seconds.
- Final authorization/UI/agent checks: `U107-authorization-after.xml` — 170 passed in 18.74 seconds;
  the new authorization-control regression failed before repair (`U107-authorization-before.xml`).
- Final full-source Windows: `U107-owner-review-full.xml` — **2382 passed, 15 skipped, 19 subtests
  passed in 539.19 seconds**. Skips: Mac Keychain1, optional supplied Vosk zip1, opt-in live-model13.
- Dedicated automated USB: `U107-owner-review-usb.xml` — **45 passed, 2352 deselected in 87.10 seconds**.
- Final source/test hashes, scope checks and completed processes: `U107-owner-review-receipt.json`.

Use the locked release interpreter documented in `U107-HANDOFF.md`; do not install into it.
The benchmark and queue-proof scripts create disposable stores before application imports:

```text
python scripts/agent_workflow_bench.py --live --set evaluation --output <new-result.json>
python scripts/agent_workflow_bench.py --live --set holdout --output <new-result.json>
python scripts/agent_workflow_report.py --before <baseline.json> --after <result.json> --output <analysis.json>
python scripts/agent_queue_proof.py
```

Result files are not overwritten. Replay after viewing a held-out answer is a regression run, not a
new blind evaluation. Full tests and `pytest tests -m usb` must run with disposable HOME, USERPROFILE
and CURSIV_APP_DATA set before importing application modules; the handoff records the final isolated
runner and logs. At the implementation-review checkpoint no package had been built, signed,
committed, pushed, tagged, released or published; the owner subsequently authorized those steps.

The benchmark JSON's `evaluation_answers_for_tuning: false` means no answers were used to change
runtime during that invocation. It does not mean that previously evaluated questions are blind again;
the history and labels above take precedence. Final model-facing runtime matches the measured source;
the only later behavioral runtime edit is four lines in `launcher/chat_review.py` to cancel and release controls
when a stale result encounters changed workspace authorization. It changes no inference path. The
earlier full run was superseded; the final implementation gates include this repair. Release preparation
also updates the three application/installer version strings, without changing the measured algorithms.
The original corpus remains
byte-identical to the baseline (SHA-256
`ca078508a838eebfb2d0af035cb30af1206044339082bf76704f93f94b5bcffe`).

Final gate status: **full Windows suite and dedicated automated USB gate passed**. Mac/Linux native execution,
installed-app/physical-drive tests and a release build are not claimed by this local validation.

## Release-preparation follow-up

The first versioned-source release run found one late-worker race (2381 passed,1 failed,15 skips,19
subtests). The unchanged native-boundary guard caught a temporary memory directory created by a
previous conversation's background session-note worker. Audit stacks identified the worker; this was
not an action executed by the restricted current turn. `U107-session-note-race-proof.json` retains
the source trace and failed receipt. The worker now captures its destination/owner, shares model
serialization and checks validity before/after generation and before persistence. Profile/native
completion uses a records-only metadata note rather than launching an extra unbudgeted model summary.
Regressions cover destination/person/cancellation changes, late model results and valid note saves.
This post-review repair is separately validated in `U107-session-note-final.xml`; final versioned
full/CI/frozen evidence belongs in the release verification. No guard was relaxed to ignore folders.

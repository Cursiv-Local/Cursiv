# U108 reliability implementation and evidence

Uncommitted review candidate based on published U107/main `2f1118bbafec7dea3b7671687d3b7cec4b95719e`.
No U108 release, package, signature, deployment or publication is claimed.

## Confirmed causes and repairs

| Area | Reproduced cause | Candidate repair and practical limit |
|---|---|---|
| File permissions | Saved workspace authorization remained enabled. Per-turn negation consumed a later affirmative `read` after `;` or `:`, setting inspection false. | End the negative clause at explicit delimiters; parse the remaining task after enforcing policy. `files off`, read-only, talk-only and protected paths retain their checks. This does not prove every paraphrase parses correctly. |
| Source versus records | Notebook keyword matching accepted implementation questions; other investigation requests fell through to a model without source evidence. | Source intent precedes notebook/memory dispatch. Bounded workspace discovery, reads, optional declaration-window search and static parsing return citations without model generation or execution. |
| Notebook lookup | Some notebook paraphrases missed the native route; `record <ID>` did not become an exact entry filter. | Native notebook paraphrases share verified retrieval; sample and record IDs are parsed explicitly. No new notebook database/index or workspace-specific notebook was introduced. The existing notebook/library remain shared across workspaces. |
| Requested confirmation | Explicit structured observations took the immediate native save route before the generic proposal card. Trailing instructions were parsed as observation content. | Native execution returns preview-only; the desktop shows the existing confirmation card before dispatch. Only cleaned user data becomes the approved canonical command. No append occurs on preview/cancel. |
| Conversation recall | Original-concern wording missed native positional recall. Earliest available history was labelled as the conversation's first message without proof of completeness. | Answer these aliases directly from supplied user turns, quoting the earliest **available** message. Fixed scope guidance distinguishes bounded current-thread context from memory. No private-history anchor is newly sent to cloud providers. |
| Calculations | Incompatible/unsupported conversions and mixed-dimension sums fell through to the model. The two live baseline answers correctly refused, but their refusal was model reasoning. | Narrow dimensional refusals return from code, labelled calculator limitation with no numerical result. Supported calculations and source attribution retain existing paths. |
| Tone | Initial joke literalized; explicit tone feedback already worked. Response guidance could also be lost during provider compaction. | Preserve a bounded application-rule block through compaction; follow current/recent tone feedback without saved profile changes. The first joke **still fails** the qualitative live review. This area remains partial. |

## Frozen before/after probes

The 19 native-entry probes in `tests/test_u108_reliability.py` were written and run before runtime changes.
Baseline: **3 passed / 16 failed** (`U108-baseline.xml`). The same 19 cases pass after the candidate repairs.
The expanded acceptance run includes existing U106 action, workspace and turn-policy tests:
**113 passed** (`U108-acceptance-final.xml`). Additional source-link and real-compaction checks, together
with existing feedback/philosophy tests: **141 passed** (`U108-refined.xml`). Later receipts supersede
earlier counts when explicitly identified in the handoff.

| Targeted metric | Baseline | After candidate |
|---|---:|---:|
| Source/discussion/notebook-lookup routing (9 frozen cases) | 1/9 | 9/9 |
| Permitted read-only file requests (3 phrasings) | 1/3 | 3/3 |
| Notebook sample-ID read-after-write (3 phrasings) | 1/3 | 3/3 |
| Exact record-ID lookup (1 case) | 0/1 | 1/1 |
| Explicit requested-confirmation compliance (2 cases) | 0/2 | 2/2 |
| Available-history recall/scope (2 cases) | 0/2 | 2/2 |
| Native ownership of incompatible-unit refusals (2 cases) | 0/2 | 2/2 |
| Saved workspace survives three reads | 1/1 | 1/1 |
| Pipeline sample with unsupported verification claim (Codex review) | 1/1 | 0/1 |
| Failures in the existing boundary/integrity/history subset | 0 (67 passed, 2 skipped) | 0 (69 passed) |

Categories intentionally overlap. These are selected regression cases, not population accuracy estimates.
Source-reference accuracy has no meaningful baseline denominator: the baseline investigations did not
inspect the workspace or produce source-grounded line citations. Do not call that `0% citation accuracy`.
Actual-checkout probes and their limitations are in `bench/results/U108-own-source-*.json`.
They validate every emitted file/line reference and every emitted Python declaration against current
source. Declaration accuracy does not prove architectural interpretation, dynamic dispatch or task completeness.

An early source-development run linked unrelated `answer()` functions by suffix. That was rejected during
review: only actual inspected import bindings can now form a possible static link. Markdown prose is not
treated as a programming-language declaration. Documentation paths are discovery hints, revalidated
against the authorized candidate set; their architectural claims are not runtime verification.

## Real installed model

`scripts/u108_live_bench.py` freezes 10 prompts and exercises ordinary command/chat entry points.
Data: one synthetic notebook record and a four-file synthetic workspace; all application stores are
redirected before imports. Model: installed `qwen3:4b-instruct`, digest
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`, temperature 0, seed 42,
context 8192. No Gemma, downloads, owner records or cloud requests. The transport rejects non-localhost
requests. Optional model review is off; deterministic checks remain. Actual Ollama terminal events
supply input/output token counts and completion status.

Baseline 10/10 successful generation requests; candidate 3/3 requests across the same 10 prompts.
Seven cases now use no model. Both incompatible-unit baseline model replies correctly declined;
the improvement is native execution/provenance, not corrected mathematics. The baseline pipeline
answer made unsupported operational and verification claims; the candidate returns labelled static
evidence instead. Baseline original-concern prose added invented motivations; native recall quotes
the actual available message. Initial joke remains too literal/long in both candidate retests.
Explicit-feedback replies remain brief/playful; the scientific single-reading answer was calibrated
before and after. No scientific-check algorithm was changed on this evidence.

Raw results are retained: `U108-live-before.json`, first candidate `U108-live-after.json` and
compaction-repair retest `U108-live-final.json`. Repeated prompts are regression retests, not blind
holdouts. Qualitative labels are Codex review of synthetic answers, **not independent human review**.
The original owner conversation transcript was not attached to this brief; transcript-specific and
independent human tone review remain outstanding. Cold model loads and concurrent machine activity
make these small timing samples unsuitable for broad speed claims.

## Validation and reproduction

Use the locked U107 Python 3.13 interpreter documented in U108-HANDOFF. Establish disposable HOME,
USERPROFILE and CURSIV_APP_DATA before application imports; full Windows tests also redirect
APPDATA/LOCALAPPDATA/CURSIV_REAL_HOME. Use a unique local temporary pytest base outside OneDrive
for broad runs; an earlier synthetic memory replacement hit a Windows file-lock error inside OneDrive.
Do not modify atomic storage to conceal that environmental failure.

```text
python -m pytest tests/test_u108_reliability.py tests/test_u108_evidence.py -q
python -m pytest tests -q
python -m pytest tests -m usb -q
python scripts/u108_live_bench.py --output <new-result.json>
python scripts/u108_source_probe.py --output <new-source-result.json>
```

Full-source/USB results and currently running commands are recorded in U108-HANDOFF. No installed-app,
Mac/Linux, physical-drive or new-user results are claimed by this local implementation candidate.
Existing notebook corruption/correction, failure, authorization, offline and encryption tests are reused;
their coverage is not relabelled as newly implemented functionality.

Completed Windows broad gate: **2,432 passed, 15 skipped, 19 subtests passed in 482.48 seconds**
(`U108-full-validated.xml`). Skips retain optional/live-model/platform requirements. The final
observation-filename guard and partial-declaration wording review followed that run; **204 final
affected tests passed in 12.06 seconds** (`U108-final-focused.xml`). The one new filename-in-note
test was added after broad collection. The broad count is not relabelled as a fresh exact-tree run
after those small follow-ups. Dedicated USB: **45 passed in 71.70 seconds**, synthetic local folders.

Final model totals over the selected 10 prompts: attempted/successful requests **10/10 → 3/3**;
Ollama input/output tokens **19,547/2,324 → 5,915/141**. These describe this regression set and
native-path substitution; they are not a general speed or quality estimate. Machine-readable
comparison: `bench/results/U108-comparison-validated.json`.

Final checkout-source probes: **128/128 file/line references** and **69/69 Python declaration
names/lines**, independently checked against the full files by the probe script. Truncated-source
output labels declarations as candidates; syntax context outside the excerpt is not established by
the application. Static links, runtime behavior and completeness require separate review. Two
questions and valid citations do not establish a complete architecture investigation.

No U108 commit, push, tag, package or publication occurred. Protected/excluded owner files, user stores,
unrelated profiles and station code remain outside the change. The handoff retains failures and
intermediate receipts rather than replacing them with expected or inferred successes.

## Automatic own-source extension

The owner subsequently authorized automatic codebase understanding without special
read commands. [Implementation, measurements and limits](U108-SELF-INSPECTION.md) describe
the versioned public inventory, natural questions, current-chat follow-ups, hash checks,
local-only inference/review and packaging changes. No additional agents were needed.
Frozen own-source entry cases improved from 0/6 receiving source context to 6/6;
controls and broad native-route regressions remain separate from semantic grading.
Final affected checks: **393 passed in 11.46 seconds** (`U108-self-branches-checked.xml`).
Final real Qwen development and previously seen held-out retests completed 10 local requests.
**31/31 emitted file/line references** matched actual indexed source locations and hashes
(`U108-self-comparison.json`). Source access works, but model explanations of proposal flow,
confirmation and fallback conditions still need work; full codebase understanding is not
achieved.

Final Windows gate after the automatic-source changes: **2,484 passed, 15 skipped,
19 subtests passed in 410.93 seconds** (`U108-self-full-validated.xml`). Runtime and
index were frozen for the entire run. The earlier source-extension full run's 25
native-routing failures are retained in `U108-self-full.xml`; the subsequent
interrupted run has no completed-suite claim. The handoff identifies the actual
repairs and intermediate failures. These regression results do not erase the live
semantic failures described above. Native Mac/Linux and installed-package testing
remain outstanding.

Final dedicated USB gate after the source extension: **45 passed, 2,454 deselected
in 74.48 seconds** (`U108-self-usb.xml`), using synthetic local folders. No physical
drive, owner store or production installation was used.

The original ten everyday prompts were rerun once more on the final extension tree
(`U108-live-extension-final.json`): seven native answers and three successful local
Qwen requests, **5,915 input/134 output tokens**. Original baseline: ten requests,
19,547/2,324 tokens. Initial banter still fails qualitative review; explicit light-tone
feedback and the single-temperature-reading answer remain appropriate. This final
regression confirms routing and records the remaining tone defect; it is not a
general performance estimate or an unseen evaluation.

## Continued repairs and release candidate (October28)

After owner authorization to continue or release, ordered AST sections were tested on four new
questions (`U108-flow-live-unseen.json`). They did not solve small-model reasoning: the provider
ordering answer was wrong, the proposal answer overgeneralized confirmation, and one approval
question missed lookup. Those failures remain recorded. Critical confirmation, correction and
fallback explanations now use native reviewed rules gated by actual inspected AST witnesses.
Changed witness tests fail closed. No model or private notebook read is used for those explanations.
Four additional questions frozen before their run passed4/4 natively with zero model calls
(`U108-native-live-unseen.json`); this is not a Qwen accuracy score or independent human study.
The prior control-flow corpus was also rerun natively (`U108-native-live-seen.json`).

Explicit brief banter had five reproduced context failures: unsolicited memory/session/vault reads
and workspace coding instructions. These are now excluded, together with project/plugin/document
retrieval; safety and technical work retain existing routes. Live original joke is now brief but
still literal; humor remains partial. Unseen banter responses are retained in `U108-banter-unseen.json`.
No scientific calibration or overconfidence algorithm was changed.

The source-index release audit found a real cross-platform defect: Git's LF blob differed from the
Windows CRLF working tree. Fingerprints and byte counts now normalize only CRLF→LF. A regression
checks equal inventories across both layouts and continued rejection of semantic edits.

Latest complete Windows suite before version preparation: **2,508 passed, 15 skipped,19 subtests
in409.55 seconds** (`U108-continuation-full.xml`). Affected set284 passed; one subsequent LF fixture
error (double-CR conversion in the test) is retained, then corrected. Final source checks57 passed;
final source/native routing checks114 passed. Version3.14-U108 metadata and release notes were then
prepared. Exact-source protected CI and native package checks are required before publication.

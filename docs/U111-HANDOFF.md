# U111 — reliability, routing, verification and model transparency

## Current state

Started October 29, 2026 from U110 main `ee9b1cf0b99e723d5eb21c8ab257cbc70de497a2`.
Branch: `codex/u111-reliability`. Owner worksheet read in full. Implementation and
live regressions and final source/USB gates are complete. Documentation and audit
receipts below describe the finished local changes and remaining limitations.
No commit, push, tag, release or publication is authorized by this worksheet.

Read: CLAUDE.md, HANDOFF.md, CHANGELOG.md (current releases), ARCHITECTURE.md,
docs/CODE-MAP.md, U109-POSTRELEASE-VALIDATION.md, U110-RELEASE-VERIFICATION.md.

## Constraints

Qwen3:4b-instruct through real local Ollama for live claims. No added agents,
paid dependencies, mandatory cloud or Field Station changes. Keep confirmation,
notebook integrity, encryption, portable storage and permissions. Do not inspect
owner exclusions (legal handoff, field-notes.txt, test_internals), secrets or real
user stores. All app/test processes redirect home/data before imports to fresh
temporary directories outside OneDrive, using the existing locked interpreter.
No dependency installation or environment update.

## Work order

1. A: inspect current implementations/tests; freeze reconstructed incidents and
   establish baseline failures before edits. Original roast text and full original
   Mars/research transcripts are not attached: reconstruction is not exact replay.
2. B: notebook intent, domain warnings, hypothetical number provenance, bounded output.
3. C: bounded constraint context, evidence grounding and accurate self-review.
4. D: provider/model audit, truthful provenance and reproducible benchmark harness.
5. E: real local Qwen end-to-end before/after, affected tests and final gates.

## Initial findings (code inspection, not yet measured)

- Notebook fallback treats a notebook mention plus any write/save verb as an action;
  writing exclusions cover poems/stories but omit posts/roasts/promotional descriptions.
- overconfidence_note selects lab/health-authority wording for any question containing
  `safe`, without evidence that it concerns water/food/public-health testing.
- simulated_note labels all numbers invented when a hypothetical answer has a numeric
  table or twelve numbers, without comparing supplied inputs.

## Commands / unfinished work

Baseline regression contracts: expanded set **15 failed / 3 passed in 23.10s**
(`bench/results/U111-regression-before-expanded.xml`). Initial smaller set10 failed/4 passed;
its apparent length pass was caused by the erroneous notebook reply, so the expanded
length probe uses an unrelated robot post and correctly fails on excess output.
These counts are contract failures, not independent defect or model accuracy counts.

Live baseline completed exit0: session58062, `reports/U111-live-before.log`, output
`bench/results/U111-live-before.json`, frozen corpus `bench/u111-reliability.json`.
The owner confirmed exact original transcripts are unavailable. No runtime edits
were made until this baseline completed. Baseline test sessions56378/46884 have finished;
their receipts/logs are retained. Next: finish provider/context inspection, repair
deterministic infrastructure, preserve raw failures. Final validation
must distinguish fixed, partial, not reproduced and deferred items.

Phase B changes underway: shared writing-vs-operation classification, domain-specific
overconfidence wording, hypothetical input comparison, one bounded character-budget
revision with artifact-only final output. Phase C adds explicit bounded connectivity
constraints and prior-answer excerpts retained through compact prompts, checks quoted
self-review against available answers, and checks numeric authority thresholds against
actual retrieved source text. No general semantic understanding guarantee.
Phase B:94 passed/5 failed in26.70s (one remaining restricted-writing catch and four
then-unimplemented Phase C checks). Phase C:203 passed in29.49s. Phase D initial:
38 passed/1 failed (Gemini synthetic fixture omitted its candidates shape; fixed
fixture, no live cloud result claimed). Broad affected set340 passed in55.04s;
later edge-case changes require a final rerun. An earlier broad command selected a
nonexistent historical test filename and ran no tests; retained as an invocation failure.

Phase D: desktop now has Automatic, exact installed Ollama and configured-provider
choices. Cloud IDs are entered explicitly and validated by the provider on send,
not populated with newly hardcoded IDs. Text equivalent:
`model ollama qwen3:4b-instruct :: <question>` (provider and model are separate).
An exact selection blocks when offline/uninstalled/unconfigured/unsupported images;
there is no provider/model fallback or automatic local download. Installed-source
model explanations retain their local boundary and refuse a cloud selection explicitly.
Native research commands remain application code regardless of selected model.
Transport records use returned/resolved model IDs when available. Optional automatic
mode retains the existing cascade. Cloud transport cases are synthetic, not live.

First full live after run completed (all12, no execution errors), retained at
`U111-live-after.json`. Both roasts reached Qwen (266/171 characters), and the
observation became a zero-model native preview. It also exposed remaining defects:
the cross-topic post exceeded its budget after revision and returned an honest
failure message (not a successful post); the Mars model inferred an active blackout
despite unspecified timing; the sample-count answer still privileged a table.
Added complete-prefix extraction after at most one writing revision, a check for
that temporal assumption, and a check on unsupported table reliability. Extra Mars
oxygen figures remain model reasoning, flagged as unverified; no scientific accuracy
guarantee. Additional188 focused checks passed in12.93s before provenance metadata-only
addition. Next: final real-Qwen corpus, original seen overconfidence --heldout rerun,
full isolated source suite, USB gate, scoped secret scan and final validation labels.

`U111-live-final.json`: second all12 live run completed, no execution errors.
Three requested posts are275/171/277 characters, each one real Qwen request; no
notebook operation for the roasts and native observation preview/read use zero
requests. The improved short prompt avoided another revision; complete-prefix
fallback remains covered by an injected overlength end-to-end contract.
The latest Mars draft changed wording and again exposed insufficient detection of
assumed blackout timing; it also adds fewer than12 new numbers, escaping the old
table/count cutoff. Keep this receipt as a failed/partial candidate, not universal
success. Next: tighten those deterministic notes, rerun the affected live Mars and
exact-selection path. No additional model prompt tuning is needed for these notes.

Running: original science --heldout rerun, session84196,
`reports/U111-heldout.log`, via `scripts/u111_heldout_bench.py` (20 seen prompts,
seed42/temperature0/context8192, offline, review off). Telemetry and legacy score
are separate public receipts; do not call these fresh blind or human-scored results.

Both science runs completed: first6/20 noted, final5/20 noted; controls0/0 (no
controls measured). The one clear false note was on “No one can say for sure”;
that explicit uncertainty now passes. Median total turn times15.7s/12.5s are
observations, not a claimed speed improvement. Both used20 real Qwen calls.

Final exact-model smoke `U111-live-confirmed-final.json` completed: roast263
characters/one request; Mars one request with conditional survey-timing note and
new-value provenance; observation preview and traced native recall zero requests.
The source suite `U111-full.xml` was deliberately stopped around41% (verified
wrapper/pytest PIDs only) before final code changes, preserving its log. Audit found
exact selections could still invoke a local reviewer/writing retry. Failure states
now withdraw partial output and stop review/learning; exact mode retains deterministic
checks and disables alternate-model review. Writing revision stays on the responding
backend. Four additional synthetic contracts cover these paths. Also clarified the
capability inventory: “Cursiv Cloud AI fallback” is not notebook/file cloud backup.
Next: focused provider tests, final real-Qwen smoke, refresh source inventory, full
`pytest tests` rerun, USB, paired rules, secret scan, final labels/report. No running
model commands remain; stopped source session64940 awaits result collection.

Current final source gate: session28103, `reports/U111-full-final.log`, target
`bench/results/U111-full-final.xml`. Earlier stopped session64940 was collected
with exit1 and is not a gate pass. Final pinning/provider/worksheet checks128 passed
in4.79s; picker/native checks29 passed in1.69s. The selector now permits native
operations even when a cloud model ID is not configured, preserves unavailable
explicit local selections across refresh, and pins choices made through Advanced.
Leading native observation commands retain literal creative words in their notes.

Latest model smoke: `U111-live-pinning-complete.json` — roast246 characters with
one bounded rewrite (two real Qwen requests), Mars one request with conditional
timing/new-value notes, native preview and traced recall zero requests. All completed
without execution errors. This run includes the final provider-failure/review fix;
subsequent native-selector/literal-note edge guards do not change its generation path.

Paired rule receipt: `U111-paired-checks.json` (25 synthetic/stored live rule cases
plus20 stored seen-heldout drafts). Wrong-domain lab advice on2 planted Mars/radiation
verdicts becomes0 while both retain a relevant uncertainty note. Supplied scenario
table warning1→0; invented experimental table1→1. Identical seen-heldout drafts:
6 notes→5, removing only the clean “No one can say for sure” warning. This is rule
scoring, not an independently reviewed model accuracy/sensitivity score. Independent
human fields remain blank in `bench/u111-human-review.md`.

Final gates completed and process results collected: full Windows2736 passed,
15 skipped,19 passing subtests in686.72s; dedicated USB45 passed,2706 deselected
in87.44s (session65271). `bench/results/U111-gates.json` matches all18 original
contracts to final passes and records72 new U111 contracts. No runtime edits after
that final source gate. Metadata/source-map/release consistency48 passed in5.89s.
No test or model command is running. Gitleaks8.30.1 scanned69 changed/new public
files with0 raw/credential findings (`U111-secret-scan.json`); final documentation
and initial audit are covered by `U111-secret-scan-final.json`. Exclusions were
filtered before reads, no allowlist was needed and no owner key was accessed.
Source code remains uncommitted on the local branch, HEAD unchanged at `ee9b1cf`,
with no staged content. Only the two new modules have intent-to-add for source indexing.
Mac/Linux/frozen packages, full cloud-model catalogue/live cloud inference,
independent human scores and publication remain deferred to an owner-approved
release workflow. Exact original transcripts are unavailable. Scientific narrative,
paraphrase/temporal coverage and broader feature-claim detection remain partial;
do not market these results as a general accuracy or safety benchmark.


## Owner release authorization — 2026-10-30

The owner explicitly authorized commit, push and release of U111 and the provider update (U112) after completion. U111 public source was recovered from the prior audit mirror with all 70/70 manifest hashes matching before version preparation. Protected main CI, USB gates, native packaging, owner signatures and secret scans remain required before publication. No release has been published at this checkpoint.

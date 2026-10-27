# U107 agent reliability and efficiency handoff

Owner: Joshua Winkler. Approved brief: U107-AGENT-RELIABILITY-PLAN.md.
Latest authorization, October27: owner approved **commit, push, release and publish it all** after
review. This supersedes earlier no-commit/release stopping notes below. Release preparation is active;
do not treat pending CI/build/signing/publication as completed. Progress: reports/U107-release-state.json.
Resumed source baseline: post-website main 2a639325f60bb3a6b911c83ebb99502339227970.
Released U106 source remains 10b40d6d9bcce73102e22d5bcd3d0fca8ba60a4a.
U107 is the approved release label; three application/installer versions are now3.14-U107.

## Boundaries

Keep the five existing read-only profiles, local-first/offline/provider restrictions, notebook and
memory integrity, encryption, existing native command precedence and confirmation boundaries.
No new framework, unrestricted agents, station changes, model downloads or cloud review incidental
to benchmarking. Never access owner queue/notebook/profiles. Excluded local files remain untouched.
Owner review is complete; current authorization covers the normal checked release/publication process.

## Reconciliation and work order

R1 confirmed: plural agents ask is missing from extension dispatch; malformed @name falls through.
R2 confirmed: group uses only personal agents, slices first three, omits profile evidence.
R3 confirmed: command streams bypass shared checks; saved tools can overstate actual permissions.
R4 confirmed: report calculation supplies arithmetic only; recent60 slice is not a full aggregate.
R5 confirmed: queue adapter returns placeholder text that marks work fired; non-atomic queue writes.
R6 confirmed: no owned research-run boundary; ordinary chat still has shared mutable turn records.
Existing U106 tests cover starter permissions, protocol no-hit, numeric/unit note, native recall and
background review. Preserve/reuse them; these repairs were not completed by U106.

Sequence: freeze fixtures/held-out prompts and record baseline; dispatch and selection regressions;
minimal engine-owned run/evidence/result boundary and shared checks/aggregates; queue persistence and
real bounded execution; isolation/cancellation and budgets; real-Qwen comparison; full gates/docs.

## Current status

U107 is published on GitHub and cursiv.us. Immutable tagv3.14-U107 points to
7d6ae616dd8c8f4b15e1b3078208ab7c78ca05bb (sourcePR51); source push/PR/exact-main checks passed.
Final versioned Windows2389 passed/15 skipped/19 subtests; hosted Mac2372/32/19 subtests.
Both tagged frozen packages passed, including Windows portable layout. Existing trusted owner
identity signed8 final platform assets;11/11 draft and anonymous public downloads,8/8 signatures
and11/11 REST digests verified. No authenticated bytes or U106 tag were changed.

Website/evidence PR52 merged atcdb6f03ceae8bffdb83626facf926265d9ae6116 after all18 checks.
Cloudflare versionedbccc5a-8eef-4a00-85bb-9523f507ffc4 deployed from that clean merged source.
Eighteen live checks passed: StartU106→U107, exact page/robots/sitemap/icon/manifest bytes,
no-transform headers, installer URLs/hash, Googlebot user-agent access and canonicalwww redirect.
The31 website,6 release consistency and63 workspace checks passed; publication commitUSB45/45.
[Release verification](U107-RELEASE-VERIFICATION.md) and
[publication receipt](../bench/results/U107-publication.json) contain completed evidence/limits.

Release/build/signing/publication/live-verification work is complete. This four-file final receipt
is bookkeeping through a normal scoped commit with USB hook and protected PR/merge; no application
change or further release build, inference, deployment, signing or download work is required. Full workflow/source identities are in reports/U107-release-state.json.
Prior progress stashes were single-path handoff snapshots only; excluded owner files were never
stashed, read or staged. No recurring monitor was created. Locked interpreter (do not modify):
`C:/Users/joshu/AppData/Local/Temp/cursiv-u88-build-39c0ad1699b74be8bab5385ce1b281d8/Scripts/python.exe`.
Historical checkpoints below retain earlier failures and pre-authorization stopping notes; current
owner authorization and published state supersede them. Physical-drive/new-user/minimum-OS and
independent-review results are not claimed. Windows CA signing/Apple notarization remain absent.

## Completion evidence required

Defect/fix/test matrix, actual call/token/latency/coverage measurements on identical synthetic inputs,
untouched evaluation prompts separate from development; all targets/failures/unavailable metrics
explicit. Fake timing alone never establishes efficiency. Full source/USB gates and current platform
limitations retained. Do not declare the supplied plan complete while any required repair is pending.



## Resumed baseline checkpoint

bench/results/U107-agent-structural-before.json: all5 advertised plural commands unhandled; the
supported alias performs4 fake generations per task. Individual protocol no-hit returns without a
model (existing guard); four other individual cases invoke1 fake generation. Fake timing is not
speed evidence. These are post-U106 reproductions, separate from the original archive audit.

Real Qwen evaluation baseline started with all application stores redirected before import, outside
connections blocked, temperature0, seed42, context8192, local modelqwen3:4b-instruct. GPU RTX2050/4GB;
no model was loaded before the run. Cold start is therefore measured separately through Ollama's
load-duration event. Model digest is retained by the harness. No downloads/cloud keys/owner records.
Do not inspect or tune against baseline evaluation answers during implementation. Read only process
progress/aggregate instrumentation until the repair is frozen. Runtime source remains unchanged.

Real baseline session96611 completed successfully before runtime edits. Twenty-four command/path
observations cover six frozen questions; exact transport/token data and synthetic raw answers are
in bench/results/U107-agent-live-before.json. Progress log: reports/U107-agent-live-before.log.
No background model process from this harness remains. Evaluation answers remain uninspected for
implementation tuning; baseline aggregate measurements may be read. Begin entry-point regressions.

## Implementation checkpoint (October 27)

Runtime edits are uncommitted on codex/u107-agent-reliability (base2a63932). The first real-entry
regressions reproduced9 failures/3 passes before edits. Initial repaired entry-point/starter/module
checks:29 passed in9.56s. Expanded synthetic evidence/queue/budget/review checks initially found
16 failures/95 passes:15 share one Passage attribute integration error (fixed to doc_id), one date
fixture used an unsupported argument (fixture corrected; no notebook API widened). Rerun pending.

Implemented for validation: plural/whitespace dispatch; explicit bounded profile choice and personal
overrides; one run-owned snapshot with full bounded verified notebook scan/current corrections,
role-specific excerpts, code-only checker/statistics, strict citation/quantity/action checks, final
optional review; transport request/context/wall/cancel accounting, serialization, no incidental model
downloads; atomic queue claims/history/legacy blocked compatibility/retry/cancel and local-only real
profile executor. UI binds profile/batch cancellation and conversation/workspace generation checks.
These are implementation claims, not a completion or release claim. Evaluation answers untouched.

Pending: expanded regression rerun, transport adapters/retries and cross-process queue proof,
ordinary-chat/shared-state compatibility, frozen live after comparison, complete supported suite,
release/USB gates, architecture/capability/privacy/help/evidence docs and final review. No model
speed or quality improvement claimed yet. No test/benchmark currently running at this checkpoint.

Expanded affected regressions passed111/111 in11.63s (reports/U107-focused-03.log). Real development
run01 completed20 observations. Checker produces exact duplicate/unit/non-numeric findings with0
model calls. Development surfaced a precise-topic retrieval limitation (the old two-word threshold
rejected 'calibration') and equivalent Celsius spelling ('C' versus '°C') being over-rejected. Repairs
are covered by additional regressions; development protocol rerun session52979 is currently running.
Affected security/document suite session16058 also running. No held-out evaluation answers inspected.

The affected suite passed116 tests in17.03s (bench/results/U107-focused-after.xml). Final transport
retry/cross-process tests were added afterwards; the full source suite session24466 is running with
all stores redirected before import. Frozen evaluation run session79713 is running real Qwen;
its timing is under concurrent synthetic-test CPU load, so a clean repeat is needed before latency
acceptance. Source hashes and run counters are included; no source changes during that evaluation.

First full source suite completed:2329 passed,15 skipped,19 subtests,2 failures in519.79s. One
code-map failure was evaluated before the map update; the other was the guard incorrectly using
memory-learning invalidation as an identity change. Added a separate person-switch revision;
authorized forget stays valid and switching away/back invalidates a research run.

Clean model trial completed (U107-agent-live-after-final.json), but report prose still conflated
exact numeric coverage with model-added missing-unit interpretation. Statistical summaries now
return the complete code-owned report unless interpretation/discussion/explain-why is explicit.
This follows the code-first efficiency requirement and prevents numeric reports from acquiring
invented notes. Initial evaluation responses have now been inspected, so later repeats of this
same set are regression/performance retests, not a fresh untouched quality sample. A separate frozen
confirmation set is required before a quality-complete claim. Early full-final session99975 was
stopped at its identified pytest processes23940/42852 to load this last correction. No owner process
was stopped. No release/version/commit work performed.

Runtime freeze for final confirmation: focused regressions221 passed in21.92s. Added one last
code-routing generalization before inference: review/inspect/audit of notebook/records/data uses
the deterministic checker (tested with separate development wording). Fresh questions are stored
separately in bench/agent-confirmation.json, SHA256 ee4f35cb816cebc718bd737c106ab18a7bbe723a883e1e0fdedeeb4ae27f5ab8.
The original bench/agent-workflows.json remains byte-identical to its baseline hash. Confirmation
results have not been generated or inspected. Next: clean real retest, fresh confirmation, then full
suite sequentially, plus source/USB gates. No further runtime changes intended unless checks fail.

Fresh confirmation01 completed20 real observations, and exposed genuine additional failures:
' sample codes' was parsed as a sample literally named codes (wrong0-row scope); hyphenated
preserved-sample retrieval missed the matching passage; the invitation invented 'this weekend'.
Repairs: generic-category guard, stem-mode compound/silent-e matching, and a deterministic event
schedule placeholder correction accounting for explicit conversation history. Added late-chunk UI
cancellation regression and strengthened native-only queue flush authorization even in automatic
file-write mode. These are documented confirmation failures, not hidden as passes. Interrupted the
obsolete full-frozen pass at identified PIDs41192/48568; no owner process or source was touched.
Second fresh confirmation questions are frozen in bench/agent-confirmation-final.json before any
of their results. Do not tune against their answers. No full-suite or live benchmark currently running;
focused session65214 has finished (result recorded by tool). Next execute fresh inference separately,
inspect outcomes, then start full suite/USB after runtime is genuinely stable.

Second fresh confirmation: checker/protocol/report now worked, but the field model tried to add
mg/L to an actual unitless nitrate example and the code correctly withdrew it. This is a genuine
model limitation, not a passing task. Generic field-note guidance now withholds irrelevant notebook
evidence entirely (individual/group views remain equivalent), while requests based on actual records
still retrieve them. This also reduces private context and inference input rather than weakening
unit checks. New regression covers both relevance paths. Final fresh five-question set is frozen in
bench/agent-confirmation-last.json; no results yet. The preceding benchmark sets are now regression
sets and must not be relabelled untouched. New actual transport-injection tests exercise ceilings
2/4/5/7 including retries; final preflight session77842 result recorded by tool.

Owned desktop publication is now guarded at the Qt acceptance point for research runs, ordinary
chat, plain command replies and legacy Babel/coding streams; stale queued text/history cannot land
in a new conversation. Pending workers retain their original target, and foreground transport guards
prevent new requests after cancellation. Background review has its own cancellation/evidence scope.
Actual offscreen Qt ownership/recovery tests were added. Earlier UI+agent affected run173 passed;
latest expanded publication/metadata run session47857 result recorded by tool.

Routine field-note tips/habits now use Cursiv's native recording guidance (schema/units/corrections),
with no model/private data, rather than repeatedly accepting/withdrawing numeric model examples.
Explicit questions about saved records retain read-only retrieval. Aggregates are memoized only
inside one immutable run/scope; multiple permitted roles calculate identical statistics once.
Personal-profile usage metadata is bound to the captured owner and reloads current teaching instead
of overwriting a concurrent edit. New reference checks also reject malformed ID-like citations.
Final source validation and the last untouched confirmation have not yet been run. No current live
inference/full-suite process; do not infer completion from preceding interrupted passes.

Final UI/person-bound changes: affected desktop/agent tests180 passed in20.67s. Added guards for
plain command replies and legacy streams too; callbacks/model work serialize through the shared slot.
A reserved acceptance set (bench/agent-acceptance.json) has not been inspected or used to tune behavior;
its earlier-source answers remain unread. Current-source benchmark+acceptance session now running
(logs reports/U107-agent-live-current.log and reports/U107-agent-live-acceptance-current.log). No full
suite is running concurrently. Source is frozen pending these results and the final local gates.

Current-source real benchmark completed. On3 comparable routine tasks, measured group median token
reduction81.27% and latency84.99%; individual median13.12% faster/p95 61.41% faster. These are small
sample descriptive results; cache/peak-memory metrics remain unavailable. All6 original regression
workflow tasks returned valid outcomes after native guidance/statistics fixes. Reserved acceptance
set met4/5 tasks; protocol was over-rejected for '(Citations: Procedures.txt, p.2)' despite exact file
and page. Fixed citation-label/quotation normalization, keeping unknown files/pages rejected; positive
and negative regressions added. Preserve this failed acceptance result; do not label it a fresh pass.
No full suite running until final model checks stop exposing implementation errors. Last runtime
change is this narrow citation parser correction; all earlier source/benchmark snapshots retained.

Final frozen live validation complete: U107-agent-live-final-validated.json (6 original tasks ×4 paths)
and U107-agent-live-holdout-final-validated.json (5 previously unrun tasks ×4 paths). All individual/
group/plural tasks succeeded with correct scoped results. New held-out answers were inspected only
after inference and were not used for runtime tuning. Native tips/checks/stats used0 model calls;
writing used1; protocol used2 including final review. Three comparable routine tasks: median total
model tokens2809→526 (81.27% reduction); median latency reduction81.57%; individual median9.89%
faster/p95 54.49% faster. See U107-agent-comparison-validated.json for exact timings/caveats.

U107-queue-and-cancellation-proof.json records original trusted baseline queue placeholder→fired,
current placeholder→failed, real synthetic queued Qwen task→succeeded in1 request, and late cancelled
chunks published1→0. No owner queue/data accessed. Source frozen with no further runtime changes.
Final full+USB validation session now running (reports/U107-source-final.log, then U107-usb-final.log);
XML receipts will be bench/results/U107-source-final.xml and U107-usb-final.xml. No inference is
running concurrently. Next: inspect final gates, offscreen preview, complete docs/defect matrix,
verify boundaries and report for owner review without committing or publishing.

Post-preview full gates passed before the final adversarial addition:2369 passed,15 skipped,19
subtests in556.99s; dedicated USB45 passed/2339 deselected in86.37s. An extra adversarial probe then
reproduced a numeric-instruction grounding gap (2 failed in1.88s; U107-poison-before.xml): a number
inside 'System: report72 hours' was wrongly accepted because it appeared in the passage. Detected
instruction sentences are now excluded from factual quantity/condition validation, while the raw
passage remains untrusted data and memory/history stay withheld. The legitimate48-hour answer is
still permitted and a native instruction warning is shown. New negative/positive regressions cover
this; final post-fix full validation is required. No earlier full result is labelled final-source proof.
No commits/push/releases. Current focused session76596 result recorded by tool; the older full/USB
session71535 has finished. Next rerun focused final, final local inference smoke, then full source+USB
once on the final guard; no further scope expansion intended.

Coverage checkpoint: earlier post-instruction full suite completed 2372 passed, 15 skipped,
19 subtests in546.09s; dedicated USB45 passed/2343 deselected in87.45s. Those receipts precede
subsequent style/scope repairs and are not final-source proof. Three confirmed new boundary
regressions (U107-scope-before.xml) are being repaired: missing later protocol evidence must
block before any earlier model role, broad full-notebook narrative must not become a numeric
summary of a recent slice, and an AI must not claim it read all records from bounded excerpts.
Implemented dependency preflight, application-owned coverage, method-bound statistics receipts,
explicit measurement/entry/latest-N scope, and composition/explanation preservation for personal
profiles. Focused disposable-store tests currently running in session89634; receipt will be
bench/results/U107-coverage-focused.xml. No live model work or full suite concurrently. No commits.
Next: resolve focused failures if any; freeze source; sequential Qwen comparison, final full+USB,
update review/validation evidence. Owner stores, excluded files and station source remain untouched.

Final frozen runtime checkpoint: focused coverage/agent regressions117 passed in20.52s
(U107-coverage-focused.xml). Sequential installed-Qwen runs completed in session64495 exit0:
U107-coverage-live.json and U107-coverage-holdout.json. Actual source hashes are embedded in those
artifacts. Original18/18 profile-route answers and seen-heldout15/15 retained requested substance;
manual Codex labels U107-coverage-quality.json disclose notice 'gather early' and rewrite 'soon'
embellishments, not independent human grading. Current scope explicitly distinguishes82 Pond rows
before measurement filter,81 temperature rows,80 numeric,mean12C/range10..14C. Native checks/tips/
statistics0 calls; protocol2 including review; writing1. Comparable n3 routine group tokens2809→530
(-81.13%), median12.352→2.049s(-83.41%); individual median2.531→2.171s(-14.21%),p95 -58.05%.
Ordinary control requests7→7; median5.828→6.514s(+11.8%), no ordinary-chat speed claim.

Refreshed actual offscreen desktop send/Qt previews U107-ui-checker-coverage.png and
U107-ui-report-coverage.png, both inspected. Runtime frozen; no further source changes planned.
Final full+USB session90433 running sequentially with disposable HOME/USERPROFILE/CURSIV_APP_DATA:
reports/U107-coverage-full.log then reports/U107-coverage-usb.log; XML matching filenames in
bench/results. No inference is running concurrently. Next inspect gates, finish documentation,
check protected scope and show docs/U107-PREVIEW.md for owner review. No commit/staging/release.

Final desktop review reproduced one additional authorization-state edge case: if workspace
permissions change outside the panel's cached settings, stale output was rejected but Send stayed
disabled (U107-authorization-before.xml:1 failed in1.48s). Fixed the same-current-turn rejection
branch to cancel its worker, clear pending history and release controls. Affected UI/agent checks
running session11507, receipt U107-authorization-after.xml. The previous full session90433 predates
this four-line GUI repair and is obsolete as final-source proof. Model-facing engine source and
measured model outputs are unchanged; only launcher/chat_review.py differs from model provenance.
Next replace the obsolete full run with final-source full+USB after focused checks pass. No release.

Authorization reset repair verified:170 affected checks passed in18.74s. Superseded full run90433
was stopped at86% with no reported test failures, because it predates the new regression/fix; no
final-source claim is based on that partial run. Only the two verified matching pytest processes
were stopped (46028/37684); owner processes/Ollama were not stopped. Replacement full+USB session
20760 is running on frozen final source. Logs reports/U107-owner-review-full.log and
reports/U107-owner-review-usb.log, receipts bench/results/U107-owner-review-{full,usb}.xml.
No inference/download/build/commit/push/release. Remaining required local work is inspecting gates,
recording final receipt/protected-scope check and presenting the owner review. Mac/native packages
and physical-drive tests remain future release work, not claimed by local automated USB coverage.

Completed owner-review checkpoint: session20760 exit0. Final Windows2382 passed,15 skipped,
19 subtests passed in539.19s (U107-owner-review-full.xml); separate automated USB45 passed,
2352 deselected in87.10s (U107-owner-review-usb.xml). Skips are Mac Keychain1, supplied Vosk zip1,
opt-in self-knowledge live suite13; separate actual installed-Qwen profile benchmarks are complete.
U107-owner-review-receipt.json verifies source/test hashes, unchanged HEAD/tag and empty staging.
Model-facing source is unchanged from final measured comparison; the later four-line desktop
cancellation/control repair is covered by170 affected tests plus final full/USB. No commands running.
Preview/validation/architecture/privacy/changelog/code map/help and main handoff updated.

Ready for Joshua's review via docs/U107-PREVIEW.md. No unresolved reproducible defect from this repair
remains known in the tested paths; source/action checks are bounded checks, not general truth proofs.
Unrequested writing timing rhetoric, small sample performance, unavailable cache/peak-memory metrics,
platform/package/physical-drive limitations and all earlier failures are disclosed. No commit,
staging, push, merge, tag, build, release or publication performed. Owner data/queue/profiles, secrets,
excluded local files and station source were not used or modified. Further release work requires
owner instruction after review; do not silently resume the earlier website release authorization.

Release authorization checkpoint (October27): owner explicitly requested commit/push/release/publish.
U107 version strings and notes prepared. Required workspace gate63 passed in5.02s; final versioned
source suite session10113 running (reports/U107-release-source-full.log, XML
bench/results/U107-release-source-full.xml). Locked release dependency check passed unchanged.
Trusted installed signer verified against all three public hashes in signer/trusted-tool-manifest.json;
private key remains untouched until final bytes are ready. Protected main requires strict Windows/Mac
workspace+full suites and security, enforced for admins. GitHub connector is read-only; authenticated
CLI is available for authorized mutations. Main still2a63932; no commit/push/tag yet. Explicit staging
allowlist in reports/U107-stage-files.json excludes legal handoff, field-notes, test_internals and station.
Cloudflare whoami preflight session36237 still pending; no deploy attempted. Existing U106 release/tag
and public download bytes remain unchanged. Next source suite result, scoped commit with USB hook,
push/PR/checks, merge/main CI, tag/build/sign/verify, then release/website publication.

Release gate10113 reported2381 passed/1 failed/15 skipped/19 subtests in411.45s. The first blocked-action native test saw an empty temporary memory directory appear between snapshots; it did not invoke any forbidden model/action/formation hook. Affected isolated recheck106 passed in7.20s. Do not commit/push failing work or weaken the guard. A full disposable diagnostic reproduction is now running via reports/U107-boundary-trace.py, log U107-release-source-traced.log, XML U107-release-source-traced.xml; directory audit stacks only in reports/U107-boundary-mkdir-trace.log. Cloudflare publisher login succeeded. No owner files involved; release remains unpublished.

Directory audit identified cursiv-session-note thread (launcher/chat_actions.py -> memory/session_notes.update/save -> atomic.write_bytes), from an earlier conversation. The current restricted turn invoked none of its forbidden backends. This is a real late-worker ownership gap, not a reason to weaken the native-boundary test. Added captured note destination and current person/workspace/conversation/storage validation, serialized guarded model work, and validity checks before/after summarization and before saving. Existing note behavior remains for valid owners. New tests cover later-store exclusion, person changes, late summary rejection, captured destination and successful same-owner saves. Diagnostic55730 stopped after trace; only verified41952/40260 processes stopped. Proof U107-session-note-race-proof.json. Focused ownership checks now running. No commit/push/tag/publication.

Session-note ownership/cancellation/zero-extra-model checks170 passed in5.01s (U107-session-note-final.xml); required workspace gate63 passed in2.05s. New full source gate running session7206, reports/U107-release-final-full.log -> bench/results/U107-release-final-full.xml. Current implementation retains original session-note destination, verifies current turn/person/workspace/storage and cancellation before and after model work, and leaves profile/native metadata notes code-only. No model-facing answer algorithms changed; prior actual-Qwen measurements remain descriptive of those algorithms, with this extra metadata-worker isolation fix separately covered. New source scope includes chat_actions.py, memory/session_notes.py and test_session_notes.py; explicit staging allowlist updated. No commit/push/tag/package/publication yet.

Final versioned source gate7206 exit0:2389 passed,15 skipped,19 subtests in496.51s (U107-release-final-full.xml), after the session-note ownership/metadata-call fix. Workspace63 passed in2.05s. Native restricted-turn guard remained unchanged. Source/runtime is frozen; source commit with the real USB hook is next. Existing trusted signer/dependency/publisher preflights passed. All publication/build/tag steps remain pending until their actual gates pass.

Source committed0afe4ca51b7152d4056b2869aa6cd8925eeee0ea:123 explicitly allowlisted files. USB commit hook45 passed/2359 deselected in99.24s; no bypass. Existing Git identity copied into isolated hook environment (global config unchanged). Source/docs whitespace clean; four raw failed-JUnit E-line trailing formats intentionally retained verbatim. Pushed codex/u107-agent-reliability; source PR https://github.com/Cursiv-Local/Cursiv/pull/51. Normal protected CI checks are running; reports/U107-source-pr-checks.log. No merge/tag/build/publication yet. This local handoff progress will be stashed by this single explicit path before clean-main tag preparation, then restored in the evidence branch. Never stash untracked/excluded owner files.

Source push CI40535846906 and PR CI40535882296 run the actual123-file commit0afe4ca. Watch session66392 logs reports/U107-source-pr-checks.log. Security, ARM64 and Mac workspace checks have passed; full hosted platform checks remain pending. Source PR51 is attached to this chat. Existing owner/excluded files remain untracked and outside the source commit. Continue only after normal required checks pass; do not use admin bypass or move release tags.

PR51 merged normally at7d6ae616dd8c8f4b15e1b3078208ab7c78ca05bb. Exact-main CI40537766999 passed all8 jobs. Required prepare_release helper workspace63 passed in3.34s, then created and pushed immutable tag v3.14-U107 at that merge. U106 tag remains10b40d6 unchanged. Windows tagged build running session50594, reports/U107-windows-build.log. Native Mac tagged workflow40539718907 running (upload=false); reports/U107-mac-build-watch.log. Main JUnit artifacts downloading to reports/U107-main-ci-artifacts. Evidence branch codex/u107-publication created from unchanged tag source, and only the saved progress handoff restored from stash ec3b7fbc754b4755f18f75313f131e71fa82ef08. No package/signature/release publication claims yet; next inspect builds and frozen checks, stage exact final assets, verify hashes/provenance, use existing trusted signer, create and verify draft, publish then update website.

Both tagged native packages passed frozen self-tests; Windows installed and portable reports ALL PASSED, native Mac workflow40539718907 successful and frozen ALL PASSED (tagged Mac source2372/32/19 subtests in492.45s). Final8 platform assets passed alias, checksum, provenance, lock/source checks. WindowsSHA b56819d957fadd77ef454b4eefe95a32375792d4c55cc4fb1c1afcc2473f6cf9; MacSHA59bda04a779651327fcc04921bffc184b1b3e8547ca4e9258b869ab177b94101. Existing hash-verified installed signer signed8 assets and the independent repo verifier returned OwnerSignatureValid for all8; no private key copied. Draft11/11 downloaded back with identical hashes/sizes and8/8 signature checks. Published v3.14-U107 as latest on GitHub. Anonymous public verification is running; website still on U106 until the checked publication update. No asset bytes may change after signing.

Published U107 public11/11 anonymous downloads and all11 REST digests matched;8/8 owner signatures valid. GitHub latest API confirmsv3.14-U107; redundant Mac run40542462834 is completed/cancelled. Website/evidence commit8d065f6326abf933b47c4a245ed0ac97ec513bb6 changes20 explicit static/docs/proof files only; no engine/launcher/installer/scripts/tests diff from the tag. Local build23HTML, website31, consistency6, workspace63 passed; commitUSB45 passed in82.04s. Pushed codex/u107-publication; protected PR https://github.com/Cursiv-Local/Cursiv/pull/52 (attached). Checks log reports/U107-evidence-pr-checks.log. No full app suite rerun locally for these website-only edits; hosted protected checks run as configured. Website remainsoldU106 until this PR passes/merges and CLI deployment is verified.

Website/evidence PR52 passed all18 push/PR checks and merged cdb6f03 normally. Cloudflare deploy exited0, version edbccc5a-8eef-4a00-85bb-9523f507ffc4 on cursiv.us/www/legacy host. Actual production Start beforeU106 afterU107. All18 live checks passed with exact deployed bytes and no-transform; installerlinks/hash and owner manifest matched, bots/favicon accessed and www redirected. bench/results/U107-publication.json records completed checks. Final receipt branchcodex/u107-publication-receipt restores only the saved progress handoff; four metadata/proof files are to be committed. All application code remains identical to the immutable release tag. No manual full-suite rerun is needed for receipt-only changes; ordinary protected CI and USB hook remain required.

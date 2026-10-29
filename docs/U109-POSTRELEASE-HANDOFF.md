# U109 post-release reliability worksheet

Base: main `26e3e5e909dfc266a8f736f5108f3a56673c5fcd`, released U109.
Branch: `codex/u109-postrelease-reliability`. Changes remain local for review.

Order: notebook identity/write-read-correction-verify-export; own-source routing
and evidence-to-answer consistency; linked memory corrections and confirmation;
overconfidence false positives; existing style preference propagation; repeat the
U109 source corpus. The worksheet supplies symptoms and identifiers rather than
a complete verbatim transcript; reconstructed prompts must be labelled as such.

Preserve confirmation, offline and workspace boundaries, existing source and
memory provenance, Qwen defaults, owner exclusions and all station code. All
tests/model probes use temporary stores outside OneDrive, with every home/data
environment redirected before imports. No real notebook/memory/config reads,
model downloads, dependency installs, commits, publication or tag changes.

Initial inspection: natural reads/verification recognize only some notebook
wordings; plain-language observation cards can pass through model extraction
when a free-text note makes the deterministic parser count them as incomplete.
Own-source resolution also requires a narrow mechanics cue, so feature questions
and follow-up variants can miss the evidence route. Existing correction backends
retain lineage; the remaining work is making natural requests reach them safely.

Baseline receipts: U109-postrelease-before-isolated.json reconstructs the worksheet
with a real successful synthetic save: 4/5 read/verify/export wordings fell through
to no native route, while an explicit notebook
lookup returned the saved record. Initial restricted-process attempt could not
write its temporary home; retained separately as before.json, not storage evidence.
Frozen regression contracts: 23 failed/7 passed in3.34s. Real local Qwen U109
previously-seen holdout baseline also captured (5 requests/outcomes, only PDF used
model generation; not a new blind holdout).

First fixes preserve parser-owned cards; share sample/project filter parsing;
route natural lookups/chain checks/confirmed full-chain history exports; broaden
linked measurement corrections without inferring a replacement entry. Core PDF
and hash-chain questions now have AST-witness-gated native explanations, and
feature-question variants enter source inspection. Memory fragments resolve one
actual active fact, retain its full sentence and linked history, with desktop edit
previews/stale guards. Saved user-stated presentation preferences feed the existing
style block. Overconfidence notes take application provenance and avoid clean
empty-result verdicts; model text cannot self-certify as native.

First wide check:234 passed/1 failed in51.92s; a general-memory-help route was
captured too broadly. Narrowed it to keep existing native help behavior. Next:
desktop end-to-end confirmation/stale/ambiguity tests, source witness degradation
checks, repeat focused suites and real local model probes before the full gate.
Next wide run passed406 tests in61.61s. Expanded coverage includes the complete Qt
confirmation sequence, cancellation/stale correction behavior, memory disambiguation
followed by preview, exact project matching, degraded source witnesses and preference
isolation. One earlier desktop run had273 passes/2 failures: ambiguous memory choice
lost the old fragment when substituting an ID (fixed by retaining it); an older GUI
test assumed immediate structured writes (updated to require the approved card).
All failed receipts remain available. All work is uncommitted.

Now: full regression and native USB gates plus sequential real-Qwen probes. Logs:
reports/U109-postrelease-{full,usb,worksheet,science,development,heldout}.log.
New live science controls were frozen in bench/u109-postrelease-live.json before
generation. Paired note scoring compares the same generated drafts with the immutable
U109 rule and current rule, distinguishing actual native outcomes from model words.
The old U109 development/holdout corpus is already seen; do not call it newly blind.

First full run:2618 passed/4 failed/15 skipped/19 passing subtests in580.68s.
Failures exposed profile-command interception by broader notebook recognition,
general USB workflow help captured as implementation inspection, and two notebook
history requests with an unsupported corrections argument. Fixed those routes;
the succeeding targeted run passed419 tests in70.04s. Additional guards preserve
polite actual-chain checks, disclose searched source when witnesses degrade, and
answer "Is offline mode on?" from application state (the first live worksheet
run showed that wording was still model-generated).

Live worksheet: all8 core feature variants returned current source witnesses with
zero model requests. The confirmed casual preference appeared in every real model
prompt, but the first marsh reply still over-clarified; tone remains partial.
Live science/control regression (12 frozen new prompts): paired identical drafts
with immutable-U109/current rules had false notes2/6 ->0/6; risk notes0/6 ->0/6.
All6 risk drafts were cautious; this does not establish a risk-sensitivity gain.

A final-answer denial recheck now also catches core-feature absences after a
missed initial route, uses only current installed-source witnesses, records the
read, and substitutes UNKNOWN when inspection is forbidden/unavailable. It never
claims a described notebook/PDF/copy operation ran. A subsequent targeted run had
420 passes/4 failures only for missing replacement-authorship wording; clarified
that the checked Cursiv reply replaces an earlier AI draft (not a no-AI-turn claim).
Next: final focused proof, full/USB gates, all original U109 corpus questions and
final live worksheet; preserve every earlier receipt and leave changes uncommitted.

Intermediate complete gate:2634 passed/15 skipped/19 passing subtests in640.40s.
Final review then closed complete-value memory matching (CM-742 must not edit
CM-7429), unrelated-feature-denial clauses, and read-only style lookup. A targeted
ordering run exposed a test-only active source-packet leak into a direct learner
test; the new worksheet fixture now restores its context. Succeeding targeted
run:209 passed in89.15s. An overly broad optional ID-label prefix was also narrowed
so normal content beginning “identity” remains matchable. Final55 worksheet plus48
memory-intent cases passed103/103 in20.43s. The in-progress full-closed run was
deliberately stopped for that last parser correction; it is not a passing receipt.

Frozen final snapshot: no further runtime edits are planned. Serial proof driver
reports/U109-post-final-gates.py is running (full-proof, then usb-proof, then
workspace-proof). Its summary will be bench/results/U109-postrelease-gates.json.
Fresh real-local live proofs have completed: live-development-proof (15),
live-heldout-proof (5), live-worksheet-proof (13), all exits0. They use the final
source inventory and existing installed Qwen, no private stores or downloads.
Next: collect serial proof results, finalize validation, scan explicit changed
public bytes with owner exclusions filtered before reads, confirm no staging/commit
or station/release changes, show the local validation for review. No publication.

That serial proof passed: full2639/15 skips/19 passing subtests in614.35s, plus
USB/workspace (see U109-postrelease-gates.json). A final real-model boundary probe
then reproduced the remaining medium worksheet defect: a genuine code-computed
mean6 worded “Yes,6” by Qwen still received an observation warning. Repaired with
actual calculator provenance and a pure math/numeric vocabulary boundary; added
safety/causal prose remains checked. Focused159 tests passed in16.81s. The final
real-local after probe returns the same correct answer without the warning.

Current final driver: full-complete →usb-complete →workspace-complete, log
reports/U109-postrelease-complete-gates.log, summary U109-postrelease-gates-complete.json.
Fresh live-development-complete15, live-heldout-complete5, live-worksheet-complete13,
and live-calculation-complete1 all exited0. No further runtime edits are planned.
The old science corpus was retained byte-for-byte with its original SHA-256 before
the later calculation case was appended to the combined corpus. Next collect the
final serial proof, update this current-status record/validation, run the explicit
public-file secret scan and verify branch/index/station/release boundaries. Keep all
work uncommitted for owner review; the published U109 assets remain untouched.

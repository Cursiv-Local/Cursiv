# U109 reliable self-inspection handoff

Baseline: latest main `efc2f961049b767f0fe49e38304e9e70f25a6955`, published U108.
Brief: supplied U109 desktop self-inspection request, October28,2026. Work on current main;
no U109 commit/push/tag/release/publication is authorized by this development brief.

## Boundaries

Preserve offline/local-only source explanations, public installed-source containment, per-turn
restrictions, notebook/memory/document behavior, read-only inspection and owner signing identity.
Never read/change/stage owner exclusions `docs/CURSIV-LEGAL-HANDOFF.md`, `field-notes.txt`,
`test_internals/`; do not modify `cursiv_engine/station/`, secrets, user stores or unrelated profiles.
Use the existing locked Python3.13 environment; no installs into it. Tests/live probes redirect
HOME, USERPROFILE, CURSIV_APP_DATA, CURSIV_REAL_HOME, APPDATA and LOCALAPPDATA before app imports.

## Initial investigation

Read CLAUDE/HANDOFF, CODE-MAP, architecture/U108 source evidence, source modules and relevant tests.
Remote and local main match. Tracked worktree initially clean; only the three owner exclusions
are untracked. U108 credential audit found no real credentials; public verification keys remain.

Confirmed implementation gaps, before repairs:
- Automatic own-source intent lacks PDF/document, offline and Field Copy feature topics and several
  common imperative forms. Workspace language can suppress own-source intent even for Cursiv features.
- Own-source selection is fixed seed lists plus symbol word matching; startup is absent from its
  pipeline seed list. Many source roles share names and are not distinguished in evidence.
- Module imports inside top-level try/if blocks are not bound by the indexer, so launcher aliases
  such as `_cursiv_chat` and `cc` lose actual cross-file targets. Nested bodies are correctly separate.
- Citation checks catch some paths/lines/quoted functions, but accept many unsupported semantic
  claims and do not check regex behavior. Index existence is not semantic proof.
- Authorized-workspace inspection can emit a successful-looking report with zero actual reads.

Next: freeze U109 regression/held-out corpus and tests; measure U108 deterministic, performance and
real-Qwen baselines before runtime changes. Then add bounded structured source analysis, actual
startup/role/call evidence, feature coverage, technical checks and honest evidence states. Preserve
workspace analysis for explicit user repositories; never substitute it for installed-source evidence.

## Results and commands

Frozen corpus: bench/u109-self-inspection.json (15 development/5 held-out). Baseline regression:
20 failed/7 passed in2.01s (U109-baseline.xml), unchanged U108. The missing-feature test initially
also required nonempty evidence; corrected that contradictory expectation to require NOT FOUND
IN SEARCHED SCOPE. Original receipt is retained. Real Qwen baseline5 questions completed in
U109-live-before.json: PDF import falsely denied, Field Copy falsely described as absent/incomplete,
memory question routed to saved facts, startup received unrelated feature guidance. Regex answer
was mathematically correct in this run, but claimed source verification without inspection; the
reported incorrect regex diagnosis is not claimed reproduced. Baseline timings are U109-profile-before.json.

Implemented first pass: source_analysis.py adds bounded hash-checked source/AST evidence, exact
declarations, static call/callback edges, startup roles, feature discovery, technical regex tests,
coverage and explicit states. No inspected code executes. Updated source-index module import binding
through top-level try/if and lexical nested function targets. Added own-source pre-dispatch before
notebook/memory/workspace routes, preserving explicit external repositories and No tools.
First affected run:90 passed/2 failed in14.12s (U109-first.xml). Failures: persistent memory was
classified as notebook retrieval; an existing conditional-recursion guard fact was lost. Both
are being repaired without weakening the existing test. Added actual facade service wiring and
PyInstaller entry-list evidence, bounded syntax cache after fresh hash checks and stronger role coverage.

Current runtime files modified: core/self_index.py, self_inspection.py, source_inspection.py,
new source_analysis.py; launcher/command_dispatch.py, chat_panel.py. Code map updated.
Development inventory must be rebuilt after runtime/indexed document changes. New public module
is explicitly named in self_index.ADDITIONS; untracked owner docs remain excluded. App version
stays U108 during before/after work; source hashes/snapshots identify the unreleased U109 candidate.
No U109 commits/releases. Next: finish targeted/security/graph tests, real-Qwen development and
untouched held-out runs, performance comparison, broad existing suite, docs/release notes.
Further graph checks: U109-graph.xml and U109-edges.xml each107 passed/1 failed;
U109-checked.xml112 passed/1 failed. Actual lazy backend aliases and explicit facade service
injection now resolve across files; callback witnesses use the referenced attribute line.
The last failure exposed a real Unicode separator in a string: splitlines counted a character
that Python does not treat as a source newline. Own-source search/read/excerpts now use Python
newline rules; a fixture protects citations after such literals. U109-lines.xml:114 passed in20.92s.
No unrelated notebook/memory operations are captured by the added deterministic intent routes.

First development live run completed: source discovery fixed PDF/memory, but architecture overstated
verification; memory inferred universal encryption; portability/hash-chain/permissions/audit explanations
were withheld. Ollama explanation incorrectly inferred missing timeout handling from omitted code.
These are retained failures in U109-live-development.json, not acceptance success.
Repairs: primary functions now reuse ordered guard-preserving U108 slices; important hash/portable
operations have actual seeds; model generation is explicitly INFERRED. Narrowed capability-denial
guard to avoid rejecting legitimate permission limits. A universal-encryption claim is rejected.
App-owned timeout explanation checks actual request timeout/retry/exception AST witnesses. Audit
output now reports the actual supported static hypothesis, trigger/reproduction/fix/test and unknowns.
An experimental native pipeline map was removed after regression failures; architecture explanation
continues through the local model and existing missing-model/counterfeit-reference tests are preserved.
U109-grounded.xml114 passed/3 failed; U109-evidence.xml115 passed/1 failed (backend evidence lost
behind UI-only references). Context selection now reserves backend references and actual relationships.
Added synthetic bundle-root coverage for10 features and altered bundled-source rejection; this is
not a new Windows/Mac binary build or deployment.

Context stage116 passed in20.96s. Field Copy denial remained blocked despite actual functions
being found, so a reviewed native explanation now checks real copy/flush/replace/verify calls
and the include_private guard. No transfer is executed. Source access-denial status is distinct.
U109-final-targeted.xml122 passed in31.63s; U109-live-final-development.json completed15 cases.
The first held-out run U109-live-heldout.json has four actual inspection routes; the fifth,
"Inspect your regex logic", gave a correct model answer but bypassed deterministic inspection.
Do not call that a full held-out pass. Added regex mechanics routing and a seen regression test.
Final development also exposed misleading memory backup prose. Reviewed memory rules now verify
read-before-backup, atomic write/readback and actual add/find calls; model guesses do not supply
these rules. Failed/changed contract witnesses return UNKNOWN, without inspecting saved facts.
U109-validated-targeted.xml124 passed in29.22s (source/security/packaged-root checks).

Running command: reports/U109-run-validated.py (exec session98744), profile then15 real-Qwen
development probes and five SEEN held-out regressions. Outputs: U109-profile-after-validated.json,
U109-live-validated-development.json, U109-live-seen-heldout.json plus ignored logs. Do not change
indexed source while this command runs. Source snapshot ba8be7bf0a655e735af10b2c28d13dd195af8e1a234848bcaea2a25cf00610a6.
Next run reports/U109-broad.py using locked Python with escalation: separate disposable homes for
full suite, USB gate and workspace gate. Then summarize performance, inspect live receipts, scan
only changed public files for secrets, finish validation/release notes and report owner review.
No staging/commit/push/tag/publication. U109 docs/RELEASE-U109.md and U109-VALIDATION.md are prepared
as untracked public drafts; they are excluded from the development source inventory until tracked.

Semantic review checkpoint: U109-live-validated-development.json still mixed notebook integrity
verification with lookup and overstated response-check certainty; document scoring was described
as TF-IDF instead of the actual BM25-style normalization. Therefore the first broad suite was
stopped before source changes (partial ignored reports/U109-full.log; no completed JUnit result
or passing claim). All owned broad-driver/child processes were terminated, not any user app.
Reviewed native rules now check actual notebook append/correction/current/chain predicates,
document score/coverage/sort expressions and response evaluation/error/checker branches. These
are maintained critical rules, not a general semantic proof engine. Model interpretation of
general architecture, PDFs, offline enforcement, hash-chain and permission questions remains
distinct and bounded. Added source-witness alteration regressions and failure-to-UNKNOWN checks.
Latest targeted:128 passed in29.21s, U109-semantic-targeted.xml.
Running: reports/U109-run-semantic.py (session18794), final profile/development/SEEN held-out
sequence. Snapshot43d70247e6c7693b308c9654ffc0d99153b3918acd4ce0f822d48bba69eccceb.
Next: read all final responses, restart a frozen full Windows/USB/workspace run using new output
names (preserve the cancelled log), public-change secret scan, final validation/limitations.

Final semantic live/profile runs completed.15 development cases use five actual Qwen calls;
five seen held-out cases use one. No harness errors. All actual model requests target installed
qwen3:4b-instruct digest0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0.
Codex source grading in U109-source-review.json:11 bounded passes/4 partial narratives; do not
claim general semantic correctness, full codebase understanding or independent human review.
Source discovery for all10 feature areas has actual reads; eight architecture roles and
cross-file/callback witnesses pass deterministic checks. Partial narratives concern architecture
detail, offline config/runtime claims, full hash-link explanation and broad permission assurance.
First held-out4/5 actual inspection routes, final SEEN5/5; preserve the first missed regex route.
Greeting median0.0195ms before/0.0046ms after, zero index loads; source preparation costs are
fully recorded in U109-profile-after-semantic.json, including several increases and ~0.9s startup.
First Gitleaks public-change scan:45 files/zero findings (U109-public-secret-scan.json).
Root HANDOFF now points here; U109-VALIDATION and RELEASE-U109 drafts cover results/limits.

Running command: reports/U109-broad-final.py, exec session19797. Full suite logs
reports/U109-final-full.log; then dedicated USB and workspace logs under the same prefix.
Receipts U109-full-final.xml and U109-usb-final.xml. Source/index remain frozen throughout.
The earlier broad run was intentionally stopped before semantic repairs; no result was claimed.
Next: finish broad gates, fix any real regression if needed, update final docs/secret-scan receipt,
verify source/index consistency and station/exclusion boundaries, show results for owner review.
No U109 commit, push, release, tag, build publication or website change.

Final frozen Windows suite completed:2,584 passed/15 skipped/19 subtests passed in448.75s,
U109-full-final.xml. Session19797 is now running the dedicated USB gate, then native workspace
checks. No source/runtime changes after snapshot43d70247e6c7693b308c9654ffc0d99153b3918acd4ce0f822d48bba69eccceb.
Next: capture USB/workspace output, finish docs and final changed-public-file secret scan,
verify no staged files/HEAD changes, show the validation document for owner review. No release
or package build is implied. Release preparation still needs owner authorization and native
tagged Windows/Mac package/signature/CI checks before any distribution claim.

Final gates complete: full2,584 passed/15 skipped/19 subtests in448.75s; dedicated USB45
passed/2,554 deselected in76.91s; native workspace63 passed in1.99s. All driver exits0,
source/index frozen. Receipts U109-full-final.xml, U109-usb-final.xml, U109-final-gates.json.
No running app/test/model commands. Next immediate action is final public-only secret scan and
index/HEAD/staging/boundary verification, then owner review. No broader tests need repeating
unless runtime changes or an actual failure justifies it. Final notes retain four partial model
narratives and the first held-out routing miss; do not present native replies as Qwen accuracy.

Completed source review state: inventory rebuilt in memory and exactly matches the checked-in
candidate inventory (382 public files/2,558 symbols, snapshot43d70247e6c7). HEAD remains efc2f96;
zero staged files; no station diff. Final changed-public-file scan manifest/result is
bench/results/U109-public-secret-scan-final.json. Initial scan45 files/zero findings is retained.
No app/model/test commands remain running. U109-VALIDATION and RELEASE-U109 record the completed
source gates and remaining limits. This work is uncommitted and unpublished for owner review.
Next recommended action: owner reviews the changes/validation; any release requires explicit
authorization, version preparation, hosted CI and tagged native packages. Do not reread/stage
owner exclusions, or infer package/publication success from these source and synthetic-root tests.


## Owner-authorized release preparation — October28,2026

The owner explicitly requested "commit push and release it all" after source review. This
supersedes the earlier no-commit/no-publication state. Local branch codex/u109-reliable-self-inspection
starts from unchanged main efc2f96. Prepare version109 consistently, keep raw pre-version
measurements unchanged, stage only explicit public files, refresh the versioned source inventory,
rerun affected/release checks and the enabled USB hook, scan staged bytes for secrets, then push
and open a normal protected PR. Required passing source/main CI comes before the guarded tag.
Next phase: clean immutable v3.14-U109 Windows/native Mac packages, frozen installed/portable
checks, existing trusted owner signatures and verified public downloads. Then update static
website release evidence/downloads with focused website checks and verify production. Preserve
all limits (four partial model narratives); do not advertise a perfect model-accuracy score.
Owner exclusions remain untracked and must never be staged/read. Do not bypass branch gates,
replace tags/assets, disable hooks, copy private signing keys, or modify station/user data.
Active release command/log state is recorded under ignored reports/U109-release-*. Source,
build, signing and website proof will be committed in the normal evidence phase after tag creation.

Versioned inventory includes the three newly tracked U109 documents. Frozen self-test coverage
now checks startup, all ten source feature areas and bounded regex reads, with no model/private
data reads. First affected versioned run:151 passed/1 failed in42.85s (U109-release-versioned.xml);
only the existing success-message assertion failed after its wording changed. Restored the
tested critical-rule wording while retaining the expanded source checks; rerunning affected gates.
Source inventory retains the existing compact JSON representation; no formatting-only index expansion.

Final versioned affected/release checks:152 passed in43.38s (U109-release-versioned-final.xml).
The source form of the expanded frozen "own source" check also passes startup/ten-feature/regex
reads plus existing critical witnesses, without a model or notebook data. Source commit will
run the enabled45-case USB hook with isolated stores and the existing locked interpreter.
Then push codex/u109-reliable-self-inspection, create the protected source PR, require all
push/PR and exact-main gates, and invoke scripts/prepare_release.py v3.14-U109 from clean main.
Do not treat this as native package completion; exact-tag build/frozen/signature checks follow.

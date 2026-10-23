# Handoff — Cursiv verification overhaul

## Unreleased engine/storage cleanup (2026-10-23)

Work is on `codex/engine-storage-cleanup`; no push, installer bump, publication or
website deployment is part of this task. U89 remains the published baseline.
The original personal `test_internals/` file is unchanged and untracked.

- Mechanical rename to `cursiv_engine` is complete across tracked imports, build/CI,
  tests and documentation. Persistent data directories, release key bytes and
  independent external signing tools are unchanged. Baseline and rename each
  passed 1,594 tests with 1 skip.
- Optional encryption is off by default. Separate-passphrase unlock precedes chat
  imports; migration requires a closed app, an OS lease and encrypted exact-byte
  recovery copies. Interrupted migration resumes; locked/unauthenticated data
  cannot fall back to plaintext or empty-store writes. The lease remains through
  queued writes at interpreter shutdown. No real owner data was migrated.
- Read [coverage/recovery](docs/ENCRYPTION-MIGRATION-PLAN.md) before activating:
  notebook data, workspace/imported files, explicit exports/training data, logs and
  old external copies are excluded. Login reset cannot recover a lost passphrase.
  This is installation-wide encryption across local profiles, not per-user key isolation.
- Personal letter/vault commands, their direct dialogs and name-based welcome now
  require Show personal features. Existing backends/data remain; active storage
  tests made deletion unjustified. Personal dialogs moved into a focused UI mixin.
- The two shared command type modules are consolidated in `core/command_api.py`;
  `chat_commands` re-exports the same result classes. Domain order stays unchanged.
- [ARCHITECTURE](ARCHITECTURE.md) is the current ownership map, with a message-flow
  diagram and explicit remaining launcher ownership exceptions. [CONTRIBUTING](CONTRIBUTING.md)
  and README point to it, TECH and the chat facade. Existing evidence docs were
  updated instead of creating another micro-repair report.

Validation: **1,636 passed / 1 skipped**, **21 website tests passed**, final
Windows development bundle **ALL PASSED**, high-severity/high-confidence security
gate **0 findings / 0 errors**. See the Unreleased [CHANGELOG](CHANGELOG.md) for
commands/scopes and the diagnosed editor-PATH ICU collision avoided by the existing
release environment. Mac execution and a physical encrypted USB restart
on the second Windows PC remain manual follow-ups; earlier portable tests do not
establish that this new encrypted option has been physically exercised.

## U89 published and verified (2026-10-23)

The owner authorized commit/push/release and explicitly selected independent
owner release signatures. U89 includes the previous local follow-up below,
workspace routing repairs and verified security findings from the supplied audit.
See [engineering validation](docs/ENGINEERING-AUDIT-20261023.md) and
[owner signing/recovery](docs/OWNER-RELEASE-SIGNING.md). Keep the private key outside
GitHub, OneDrive and all build artifacts. Only the public JSON key is tracked.
[U89 verification](docs/U89-RELEASE-VERIFICATION.md) records the immutable app
commit `e9828f6`, 1,594/1 Windows source checks, 1,580/15 hosted Mac checks,
both frozen packages, 21 website tests and 38 passing public checks. GitHub U89
is latest and the existing Cloudflare Worker is deployed with matching owner
proof/hashes. Owner signatures are detached proof, not Windows CA trust. The
protected private key and a reviewed signing-tool copy both live outside GitHub
and OneDrive. Owner recovery backup and protected main/release tags remain open.

## Historical local checkpoint before U89 publication

Work was on `codex/live-transcript-gaps`; the application version was then U87.
[Live-transcript gaps](docs/LIVE-TRANSCRIPT-GAPS.md) records the audit, exact
production changes and regression evidence. Review the new typed answer-evidence
receipt and desktop persistence, bounded read authorization and descriptive forget
ambiguity behavior. Phone wording now lives in `cursiv_engine/core/phone_help.py`;
the launcher helper reexports it for existing graphical/command help.
No installer, updater, notebook format, website or production service is changed.
No commit, push or publication had yet been requested at that checkpoint;
the owner later authorized the combined U89 publication above.
Final isolated Windows regression run: 1,523 passed, 1 skipped in 157.29 seconds.
No hosted Mac/package validation or live-model quality score is claimed.

## Historical U87 publication

U87 was GitHub latest at that checkpoint; tagged app commit `58a6d8d`. Windows passed 1,495 tests
with 1 skip; hosted Mac passed 1,485 with 11 skips. Both frozen packages passed;
public downloads were hashed, 20 website tests and 34 public checks passed.
The owner authorized commit/push, installers and website publication.
[U87 verification](docs/U87-RELEASE-VERIFICATION.md) records the current tag,
actual tests, package hashes and live checks. Native strings are centralized in
`launcher/phone_help.py`; GUI Help lifts them out of code blocks for clickable
links. Notebook help uses the existing explanation, with no new dialog/tab.

The live testers page includes its secondary homepage button,
allowlisted route/sitemap and no-transform/CSP headers. Review actual deployed
headers, clear mailto/GitHub links and absence of injected analytics. Notebook
storage/import/chains remain untouched. Personal test files stay excluded.
Earlier release sections below retain their own historical evidence.


## Historical U86 publication

U86 is GitHub latest and the website is deployed. Main and the feature branch
are pushed; application tag commit is `31e9987`. Windows: 1,492 passed/1 skipped;
hosted Mac: 1,482/11. Both frozen packages passed, public installers were hashed,
and all 20 website tests plus 29 public release/site checks passed. The unavailable
download counter remains separate. The owner authorized publication. [U86 verification](docs/U86-RELEASE-VERIFICATION.md) is the authoritative
current publication record; earlier local/unreleased sections below describe
their checkpoints before that authorization. Preserve the personal
`test_internals/u81_test.txt` and all existing notebook/memory formats.

[Conversation follow-up](docs/CONVERSATION-FOLLOWUP.md) records the read-only
root-cause audit, exact files, nine synthetic live prompts and remaining limits.
Review classification false positives/negatives, conservative tail removal,
no saved-conversation fallback in unrelated casual chat, retained current-thread
history and the real GUI Grok-prefix/offline/native-answer path. No native
philosophical essay or model-to-model authentication was added. Model output
remains untrusted; small-model safety and recall limitations still apply.

The actual nine-turn local-model replay is public and unscored. Qwen still
overruns the paragraph preference, asks some unrecognized closing questions and
misstates memory persistence in philosophy. Review these open model failures;
passing code tests do not certify the prose.

The combined release includes all intended previous live-test/native-boundary
fixes below. Signing is deferred; physical USB memory/restart/second-PC results
are not inferred from the owner's successful basic USB operation.

## Historical native trust-boundary checkpoint before U86

[NATIVE-TRUST-BOUNDARIES](docs/NATIVE-TRUST-BOUNDARIES.md) records the latest audit,
files, actual regression runs and limits. The owner confirmed that read-only
retains requested reads, while talk-only blocks all tools and saved-source
lookup. New focused modules own the pre-dispatch refusal, Cursiv feature facts,
deterministic withdrawals, explicit flow math and review eligibility. Full check
mode no longer silently skips ordinary answers; desktop review remains deferred.
No new release, commit, push, installer or website deployment is part of this round.

Final current-source regressions: **1,428 passed, 1 skipped in 168.62 seconds**.
The skip requires a real macOS Keychain. The current Python files match the
final test snapshot; the report records its source fingerprint and all earlier
failed runs/fixes. No fresh live-model benchmark or installer validation is claimed.

## Historical local U84 live-test follow-up after U85

Work on `codex/u85-live-test-followup` addresses the supplied findings and actual
session transcript, plus the requested native help, short receipts, context and
demo improvements. [LIVE-TEST-FOLLOWUP](docs/LIVE-TEST-FOLLOWUP.md) contains the
read-only audit, exact execution paths/file inventory, actual regression runs,
failed-test explanations and remaining review points. These edits are local;
published U85 and its original benchmark/installer evidence remain unchanged.

Earlier-round isolated regression run: **1,345 passed, 1 skipped in 182.03 seconds**.
The skip needs a real macOS Keychain. At that checkpoint production/test Python
files matched the tested snapshot; the report records that source fingerprint.
This is regression evidence, not a fresh live-model benchmark or installer test.

The owner confirms signing is deferred until next month. Basic physical USB
operation worked, but saving memories to that USB, restart persistence and
second-PC retrieval have not been checked. A second clean PC is available to
the owner. Use [USB-PERSISTENCE-CHECK](docs/USB-PERSISTENCE-CHECK.md); do not mark
the full field-kit checklist complete from basic launch success. Encryption
remains the previously approved separate migration design. Personal records and
`test_internals/` remain preserved and excluded from the repair/test snapshots.

## Historical U85 publication

At that checkpoint, GitHub latest was [v3.14-U85](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U85),
published 2026-10-23 00:30:54 UTC (October 22 Eastern). Windows and Apple Silicon
Mac installers passed frozen full-window checks and were re-downloaded publicly
and independently hashed. Tagged application commit: `9770c2e`; application
source is unchanged by later test/evidence commits. Corrected source CI passed
1,267/1 on Windows and 1,257/11 on Mac (passed/skipped). The initial Windows
UTF-8 subprocess fixture failure and exact repair are recorded, not hidden.

The fresh suite 1.5 model run scored **153/158 (96.8%)**, below U84's 156/158.
All five scoring failures and an unsafe allergy-memory answer that passed the
scorer are documented. Retrieval, contradictory model wording and broader
scoring coverage remain open; this release does not claim to solve them.

The website now serves U85 evidence and quiet-feedback/notebook messaging.
Worker version: `4fcae8c8-2bcd-403f-a6c6-e70e2e9d80cd`. All 20 website tests
and 20 public release/site checks passed. The existing public counter still
returns 503/unavailable, separately from functional installer downloads. Admin
authentication remains enforced. No DNS, schema or secret change was made.
The redundant release-triggered Mac build was cancelled before upload; the
successful tagged build and verified public bytes remain intact.

See [U85 verification](docs/U85-RELEASE-VERIFICATION.md),
[release notes](docs/RELEASE-U85.md) and [failure review](bench/FAILURES-U85.md).
README, architecture, changelog, platform/quality/claim records and benchmark
results are updated. Personal `test_internals/` remains untracked and unchanged.
No owner app installation/restart or personal-data migration occurred. Historical
checkpoints below describe their own earlier status, not the current publication.

## Pre-release checkpoint: quiet feedback and continuity

The latest request adds restrained draft/review status, factual execution
receipts, current workspace/file/turn indicators and notebook feedback.
Implementation and exact file inventory are in [CHAT-FEEDBACK](docs/CHAT-FEEDBACK.md).
Final isolated Windows suite: **1,267 passed, 1 skipped** (Mac Keychain only),
154.66 s. Replays at 10/100/1,000 messages retained zero full-document rebuilds
and median final-token-to-ready times of 17/22/76 ms; the one-second review wait
is simulated. Read the report for notes-path fixture details and actual limits.
The existing U84 streaming/deferred-review architecture is retained. Progress
signals begin after local-model availability checks, around invocation only;
clean results persist review metadata without rewriting the transcript.
Notebook saves/imports are read back before success summaries. Existing chains
are neither migrated nor rewritten. Suggestions remain prose until explicitly
recorded by the user. Review the distinction between a saved historical receipt
used as context and a newly executed/verified operation.

Changes remain local on `codex/maintainability-hardening`; no commit, push,
version bump, packaging or deployment has occurred for this follow-up.
Published U84 and all historical release/benchmark records remain unchanged.
Personal `test_internals/` stays excluded. The following U84 sections describe
the completed earlier publication, not the unreleased changes above.

## U84 published

Published GitHub latest U84 at 2026-10-22 22:08:56 UTC; Windows and Apple Silicon
Mac stable downloads independently re-downloaded without authentication and hashed.
The existing Cloudflare Worker now serves current U84 test evidence (156/158),
updated homepage/download/research text, and phone/notebook clarification. Worker
version: `99bad8d6-d834-4bb5-94a5-c6eafdf798fc`. All 20 website tests and 20
public release/website checks passed; analytics availability is recorded separately.
Source CI and packaged full-window checks passed on both platforms. U83 remains
an unpublished rejected candidate, with its original tag and failures retained.
[U84 verification](docs/U84-RELEASE-VERIFICATION.md) records hashes, commits, CI,
deployment, exact observed failures and outstanding physical/signing checks.
The existing download-counter endpoint still returns unavailable/503; tables
exist and admin auth is enforced. This outage is not reported as zero downloads.
Personal test files remain untracked, excluded and unchanged. No owner app was
installed/restarted and no personal data/schema migration was performed.

## U84 final validation checkpoint

Exact tagged source: `eede54a79b83c74186275ed4f1aff83bde788739`.
Local Windows 1,248 passed/1 skipped; hosted Windows 1,248/1 and Mac 1,238/11.
Both platform builds passed the expanded full-window self-test; Mac screenshots
also passed. Fresh 158-case suite 1.5: 156 passed (98.7% overall). Both failures
and additional uncaught implications in model prose are public in
[the U84 failure review](bench/FAILURES-U84.md). All 20 website checks passed.
The post-publication record below is maintained in
[U84 verification](docs/U84-RELEASE-VERIFICATION.md); preparation is not a live
publication claim. Personal test data is still excluded and preserved.

## 2026-10-22: U84 release follow-up

U83's source CI and narrow packaged check passed, but the Mac screenshot step
caught a real main-window `theme` NameError introduced by extraction. A focused
undefined-name review also found a notes-command JSON import; two isolated tests
reproduced both failures before repair. U84 fixes the imports, checks the full
launcher in packaged/offline tests and adds explicit regressions. The U83 draft
and tag are preserved; no U83 installer was uploaded or publicly released.
The owner already authorized commit/push/build/publication/deployment. Current
results are in [U84 verification](docs/U84-RELEASE-VERIFICATION.md) and
[release notes](docs/RELEASE-U84.md). Historical statuses below are checkpoints.

## 2026-10-22: U83 publication authorized

The owner now authorizes committing, pushing, bumping the installer, publishing
the release and updating/deploying the website, particularly current test evidence.
This supersedes the no-publication restrictions quoted in the historical sections
below. U82 was confirmed as GitHub latest; U83 is the next update version.
Read [U83 release notes](docs/RELEASE-U83.md) and
[the release verification record](docs/U83-RELEASE-VERIFICATION.md) for actual
source, package, CI, download and deployment results. Never infer a passed check
from a preparation step. Keep personal test data excluded.


## 2026-10-22: Remaining trust-boundary gaps

Read [docs/TRUST-BOUNDARY-FOLLOWUP.md](docs/TRUST-BOUNDARY-FOLLOWUP.md) for the
owner's prioritized checklist, read-only findings, exact incremental files,
reproduced failures, tests, remaining limits and draft next-release wording.
No commit, push, release, installer rebuild or further deployment is authorized
or performed for this follow-up. Keep the pre-existing edits and user test data.

Most of the high-priority batch was already implemented. This follow-up closes
additional no-tool/second-person policy phrases and compound read-only parsing;
prevents a failed `file remember` from saving memory; extracts application-owned
source formatting independent of answer words; records actually supplied memory
for source/evidence/background-review inputs; blocks case-varied model source
footers; separates dated storage failures from unclear date ranges; and caps
explicit Cross-check output at 400 tokens while retaining normal chat budgets.
USB warnings now explicitly explain readable copied API keys. Additional
phone/notebook explanations and reciprocal links are prepared locally, with
notebook cache v3; they are not part of the earlier published photo update.

Initial focused follow-up: **388 passed in 46.32 s**, isolated snapshot
`%TEMP%/cursiv-maintenance-9yr8mxzt`. The final suite also includes expanded
local/cloud policy checks and ordinary provider-budget compatibility checks.
The report retains the expected pre-fix failures and the earlier focused run
that exposed a date/storage error distinction and ambient test-power dependence.
Final complete Windows source suite: **1,246 passed, 1 skipped in 299.62 s**,
`%TEMP%/cursiv-maintenance-s8vnolr0/pytest.log`. The skip needs a Mac's Keychain.
Tested application/launcher fingerprint:
`15985868d5d3bcb9fbff8aad9955b5f46f05376a094573d9d016ed137683e278`.
Website build-only and phone/notebook script syntax checks passed. No live-model
accuracy, new packaged installer or physical USB/phone validation is claimed.

## 2026-10-22: General-purpose phone photo chat

The owner requested neutral photo handling and redeployment through the existing
website flow. This is a Cloudflare Worker with static assets (`cursiv-web`), not
Pages. Existing Git commit/push restrictions still apply.

Website runtime changes are exactly `website/app.html` and
`cloudflare/worker.js`: neutral setup/title/description/placeholder/empty-chat
example/loading text; `VISION_SYSTEM` replaces the Bible specialization; an
image-only request gets a neutral question. The prompt asks for visible facts,
legible text, uncertainty and normal text-only replies. Existing styles, pairing,
space authorization, history, memory-summary handling, provider selection,
uploads, image limits and database schema remain unchanged. The manifest and
Apple home-screen title already use generic Cursiv branding and needed no edit.

Documentation updated: README, CHANGELOG, this handoff and the master pending-file
inventory in `docs/MAINTENANCE-HARDENING.md`. Prior desktop edits and personal
test_internals data are preserved; they are outside the website asset allowlist.
Worker/inline-phone JavaScript syntax, the static website build and Wrangler's
dry-run bundle passed. The built phone page matches its source. Used the already
installed Wrangler 4.151.3; the initial no-install npx lookup wanted a newer
uncached version, so no tooling upgrade was needed.

Published successfully to the existing `cursiv-web` Worker and its existing
custom domains. Version: `784d34d9-56e8-4089-8244-1f2fb82b430b`. Wrangler uploaded
only the changed `/app.html` static asset, plus the updated Worker bundle.
Read-only HTTPS checks returned 200 for `https://cursiv.us/app`, the manifest
and `/health`. Live HTML has the new title/setup/empty-chat example and no Bible
or NIV framing; the manifest remains Cursiv with `/app` as its start URL.
An installed home-screen app may need a refresh to load new page text. Existing
conversation history remains stored and is still supplied to the model.

The live HTML includes an edge-added Cloudflare Insights beacon absent from the
source asset, so the live response is not byte-identical to the built HTML.
These source changes add no analytics code; Cloudflare dashboard analytics
settings were not inspected or changed. No live AI photo question, pairing flow
or authenticated space operation was exercised, and no database migration ran.
No desktop rebuild/version bump, commit or push occurred.

## 2026-10-22: Draft completion before background review

Latest owner request: gate model review to deterministic findings/high-risk turns
and finish the draft before an asynchronous follow-up. Read
[docs/ASYNC-ANSWER-REVIEW.md](docs/ASYNC-ANSWER-REVIEW.md) first for exact files,
execution paths, controls, measurements and remaining limits. The no-commit/
no-push restriction still applies; installed U82 is unchanged.

Implemented: default fast review, persistent `check off/fast/full`, 180-token
verdicts/300-token full rewrites, no ledger-only call, copied turn evidence,
local-only background worker, GUI-thread follow-ups and stale/cancelled-result
rejection. Deterministic safety/provenance corrections remain immediate;
pending assistant prose is not promoted to verified memory. No installer,
updater, website or personal data changes in this follow-up.

Focused suite: **208 passed in 12.49 s** in the isolated
`%TEMP%/cursiv-maintenance-eme3y4as` snapshot. Controlled Qt replay, three repeats
per 10/100/1,000-message history, used a simulated 1,000 ms model wait. Median
ready latency fell from 1,014/1,021/1,076 ms to 21/25/83 ms, with zero full
document rebuilds. These are synthetic wait measurements, not live inference or
fresh accuracy scores. The report includes later save/heartbeat/RSS costs;
one 1,000-message follow-up had a 263 ms GUI heartbeat gap. Backend cancellation
is cooperative and may await the next token/read timeout.

Final complete Windows suite: **1,209 passed, 1 skipped in 176.73 s** in
`%TEMP%/cursiv-maintenance-u7nhk2vp`; the skip requires a Mac's Keychain. This
includes persisted follow-up/reload, rejected false-capability rewrites and the
explicit Cross-check race. Tested application/launcher fingerprint:
`2ea2f061cd06916a76ada19d72a92dcaa974207b1070f735041aec36cf65663e`.
The prior full attempt had one old test dependent on the former generic trigger;
it now explicitly requests full verification without weakening its grounding
assertions. No new live-model accuracy claim is made for the background path.

## 2026-10-22: Unreleased maintainability and verification hardening

Current work is on `codex/maintainability-hardening`, based on main 8831241/U82.
The owner explicitly instructed: **do not commit or push anything until told to**.
Keep all this work uncommitted; wait for fresh explicit authorization.
Read [the complete maintenance report](docs/MAINTENANCE-HARDENING.md) for root
causes, exact changed-file inventory, actual test logs, deterministic/live
measurements, code review priorities and remaining gates. Then read
[ARCHITECTURE.md](ARCHITECTURE.md) and the
[verification policy](docs/VERIFICATION-POLICY.md).
The subsequent U82 transcripts were supplied as failure context. Read the
[restricted-turn repair report](docs/U82-RESTRICTED-TURN-REPAIR.md) for the
policy/parser/provenance/failure-continuation fixes and remaining limits.

Pre-background-review Windows source suite: **1,177 passed, 1 skipped** in 167.34 s.
The skip is the real macOS Keychain check. Test snapshots use isolated homes and
data; no current-branch installer, Mac CI or physical second-PC test is claimed.
Deterministic replay detects 8/8 seeded failures with 0/8 false alarms, compared
with U82's 7/8 and 2/8 on the same fixed examples. Live-run results and their exact
source snapshots are recorded in the maintenance report.

Implemented: focused chat/provider/stream/check modules; ordered command domains
with compatible result types; smaller views/dialog operations; coded fail-closed
verification and a constrained single-rewrite policy; shared protection of
login/key/guardian mutation paths; tagged-build environment/self-test/alias
guards; restricted-turn/parser/source-label/failed-tool corrections; tests and
evidence documentation. Personal memory/notebook schemas and
test_internals are preserved. Website source is unchanged.
The final live follow-up found that a warning below an incorrect model dose was
insufficient. Detected dose/reference contradictions now withdraw the draft and
show the actual supplied reference, without a model rewrite or learning from it.
The maintenance report retains the earlier 4/6 live run and its exact misses.
The final unchanged-suite six-case run scored **5/6**, with no case-marked
unsupported claims, on the exact final tested source. The remaining `adv-011`
failure compared both quantities but missed the required conflict vocabulary.
An earlier run scored 6/6. These are small local-model samples; source-conflict
wording, source-selection assumptions and bounded warning heuristics still need care.
The last metadata guard also forbids reference table loading during restricted
turns or empty-evidence assembly; stricter exact-prompt tests cover final checks.

The owner explicitly selected a separately documented encryption migration.
Signing credentials, clean Mac installation and the two-clean-Windows-PC/full-day
USB checklist remain external/manual requirements. No new signed installer or
field validation is claimed. This task has not committed, pushed, bumped,
published a release, installed an update or deployed the website. Published U82
below remains the prior completed release, not this new branch.

## U82 publication record

U82 is public/latest on GitHub, with source commit f14c033 and both verified
Windows installer filenames plus SHA256SUMS.txt. The actual public latest download
was fetched without authentication and matched the local build. The frozen
Windows app passed all self-test checks after an inherited build-PATH DLL
collision was isolated; the rejected candidate was not uploaded.

[U82 release verification](docs/U82-RELEASE-VERIFICATION.md) records the exact
source/tag, hashes, source CI, packaged checks, build tools and corrective build
environment. It also links the tag-specific Mac package workflow and its asset
validation. The owner's installed app was not automatically updated.

## 2026-10-22: U82 publication authorization

The owner explicitly approved committing, pushing, bumping and releasing the
completed changes. A live GitHub check found U81 already public/latest, U80 still
draft, and main at 3f58754. The owner chose U82 so installed U81 can detect the
new build. Do not replace published U81 tags/assets.

Release preparation synchronizes selfknow.VERSION, the launcher's current version
and Inno Setup to 3.14-U82. Installer project URLs and README update instructions
now use the current domain/repository. README and CHANGELOG no longer describe the
already published U81 desktop improvements as pending work.

The U81 Windows CI job passed. Its Mac job and release workflow failed on four
USB tests using the /var temporary-path alias and a failed-write test mocking the
Windows-only primitive. Test directories now resolve their disposable paths, and
the failed-write test targets rename on Windows or link on POSIX. The packaged
notebook self-test also resolves its scratch directory. Production path guards
remain unchanged.

Additional release files beyond the implementation report's inventory:
installer/cursiv_setup.iss, launcher/cursiv_launcher.py, launcher/selftest.py,
tests/test_trust.py, tests/test_verified_filesystem.py and docs/RELEASE-U82.md.
The exact release commit/tag, checksums, CI and packaged-app verification are
recorded after publication. Personal test_internals/ files remain excluded.

## 2026-10-22: Grounded chat state, boundaries and dated recall

Owner instruction: "start from the top, you have permissions", following the
read-only audit and structured repair plan. Work is on codex/grounded-chat-state
from U81 commit 3f58754. Existing test_internals/ files are preserved. Nothing
has been committed, pushed, deployed, released or rebuilt as an installer.

Read [docs/GROUNDED-CHAT-REPAIR.md](docs/GROUNDED-CHAT-REPAIR.md) first. It records
the confirmed defects versus hypotheses, exact execution paths, all changed files,
policy/recall/source semantics, test evidence and remaining risks. README and
CHANGELOG are updated. Memory/notebook formats and original append-only notebook
backend remain unchanged; there is no migration or real-data rewrite.

Implemented in order: current-message tool/retention boundaries; actual session
state and truthful memory capability context; native dated saved-fact retrieval;
bounded verified source continuity and explicit quotation checks; deterministic
regression coverage. New modules: core/turn_policy.py, core/grounding.py and
memory/recall.py. UI/provider dispatch uses existing execution receipts and
backends. Direct operational questions no longer depend on model guesses.

Validation before changes: **1,008 passed, 1 skipped**. Final complete repair run:
**1,080 passed, 1 skipped** in 166.81 seconds. All 16 changed Python files match
the tested snapshot byte-for-byte; whitespace review passed. Absolute test-log
paths and intermediate runs are recorded in the repair report.
Tests run from disposable source/home/data
snapshots, include existing offscreen Qt checks, and use mocked model/provider
output for deterministic assertions. Fresh Python-process memory retrieval was
tested; an installed executable restart and live qwen/cloud inference were not.

Claude review priorities: opt-out false positives and literal payload handling;
nested/generator policy cleanup; enabled versus proved file access; corrupt memory
privacy settings staying unchanged; date-window/user/shared/superseded selection;
source reauthorization and bounded excerpts; final checker revisions respecting
the same guards. No new autonomous self-modification or subjective-awareness
claim is intended. Installed U81 still needs an explicitly approved build/release
and install to receive these source changes.

## 2026-10-22: Tighter homepage copy

Website-only copy/layout edit, preserving all earlier pending application and
analytics work. `website/index.html` now leads with Cursiv's offline Windows/Ollama
value in two short sentences, presents four brief benefits, keeps a compact Truth
Benchmark section with an explicit scope qualifier, and ends with a direct latest
Windows installer link. Main download buttons retain anonymous click-event tags.
The counter and its duplicate-exclusion/unique-person limitations remain visible.

Body copy drops from about 2,475 to 759 words (69% reduction), including text in
closed details, with head/scripts excluded using the same counting rule. Long
feature tables, diagrams and repetitive sections are replaced by links to existing
offline, hardware, research, privacy and testing pages. Setup, encryption, unsigned
installers, separate model licenses, platform limits and dated screenshot context
remain in expandable details. The original section IDs are retained for inbound
links; the formerly missing `today` anchor is now the hero. SEO metadata, canonical,
WebSite JSON-LD, social image, navigation script and shared stylesheet are unchanged.

README, CHANGELOG and this handoff record the edit. The analytics guide now correctly
states that direct installer buttons on both the homepage and `/start` are tagged;
ordinary setup navigation is not counted. No desktop/API/installer code, benchmark
source, deployment configuration or production service is changed by this edit.
The static build and whitespace review passed. Desktop browser inspection confirmed
the rendered short hero, four benefits, closed details and direct download links;
the static preview correctly shows a counter-unavailable fallback because it does
not run the Worker API. SEO head markup is byte-identical after line-ending
normalization, and every prior section anchor remains. Scope hashes identify only
these five files: homepage, README, CHANGELOG, HANDOFF and the analytics guide;
all other existing files, including pending application changes, are unchanged.
No regression test suite was requested or run for this copy edit. Nothing was
committed, pushed or deployed automatically. Preview screenshot:
[homepage-tightened.png](C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/homepage-tightened.png).

## 2026-10-21: Website-only download analytics and documentation inventory

The owner requested privacy-conscious download analytics for `cursiv.us`, then
explicitly requested README/changelog updates recording all pending work. This
task changes website/Cloudflare files and documentation only. Earlier desktop,
installer, updater, memory, tests and benchmark source files are preserved.
No commit, push, production migration, secret change, DNS change or deployment.

Implementation and full per-file inventory:
[cloudflare/DOWNLOAD-ANALYTICS.md](cloudflare/DOWNLOAD-ANALYTICS.md).
The root README now links setup/test/publish instructions and the existing repair
reports. CHANGELOG.md adds a clearly **Unreleased** section covering website
analytics and the earlier pending Saved Notes/rendering/notebook/local-action work;
it does not claim those changes are in an installed or published release.

Architecture confirmed: existing `cursiv-web` Worker + static-asset binding + D1,
not Cloudflare Pages. The new module uses public GitHub release metadata, one-hour
D1 caching, a global refresh lease, bounded pagination, stale timestamps and
rate-limit backoff. The homepage and download page display a small counter. The
owner explicitly chose to exclude duplicate latest copies; counted canonical
installers and excluded-copy request counts are shown separately in authenticated
admin. GitHub counts are not completed transfers, installs or unique people.

`/admin/downloads/` and `/admin/downloads/data` require a separate minimum-32-character
Worker secret and HTTPS HTTP Basic authentication, with no-store/noindex responses.
Admin HTML is Worker-only, never a public static asset. Click recording stores only
Windows/Mac totals and first-recorded days, respects GPC/DNT and never blocks an
installer link. It stores no visitor/event/IP/user-agent/referrer data or analytics
cookies. The website privacy policy and date are updated; existing infrastructure
logs/security handling remain subject to Cloudflare account configuration.

The live read-only GitHub snapshot contained 67 releases/75 counted assets:
10 canonical-installer downloads, 105 requests to excluded copies; latest U79 had
0 counted versioned-installer downloads. These are audit values only, not hardcoded
website counters. The existing published homepage returned HTTP 200. Local website
tests/build and a Wrangler deployment **dry run** were performed; no upload or
production update was made. Final verification: **18 tests passed, 0 failed/skipped**;
static build and Wrangler 4.151.3 dry run passed, as did JavaScript syntax and
`git diff --check`. Before/after hashes show exactly 18 intended website/doc files
changed and all desktop/other existing sources unchanged. Full test evidence and
limitations are recorded in the analytics guide.

Deployment still requires the owner to apply `analytics-schema.sql`, set
`DOWNLOAD_STATS_ADMIN_PASSWORD` on the existing Worker, publish through the existing
script, and check authentication/data/links/privacy on production. The guide gives
exact commands and dashboard steps. Basic authentication needs a strong unique
password/private browsing; clicks are approximate and historical daily data is not
reconstructed. Prior desktop handoff sections below are historical and unchanged.

## 2026-10-21: Verified filesystem, natural-language memory and related saves

Branch: `codex/verified-local-actions`, still based on the owner's U80 HEAD
`4d24ffef078d7f72c6e5357b48f6facdd4415769`. The owner approved proceeding through
the remaining audited action paths. All earlier pending notebook, Saved Notes and
rendering work was preserved. No commit, push, merge, version bump, installer
build, release or deployment was performed. The installed application is unchanged.

Full root causes, exact file inventory, execution paths, examples, tests and limits:
[Verified local actions](docs/VERIFIED-LOCAL-ACTIONS.md).

### What changed

1. **Filesystem:** the original filename/content sentence and user-only follow-ups
   execute directly through the real backend. Results carry its resolved absolute
   path, byte count, hash and verified status. Reads use one actual byte snapshot.
   Missing/invalid workspaces fail closed; no installation-directory fallback.
   Workspace grants persist per person, move with portable references, and refuse
   copied external-host grants. Existing authorization/link/credential protections,
   approval and stale-file checks remain. Local and cloud use the same backend.
2. **Native provider adapters:** actual errors are marked as errors, rather than
   successful reads/writes. Application-owned receipts survive stream filters and
   time limits and bypass model rewriting. Literal writes no longer get a second
   model content-generation pass. Model-generated save transcripts are untrusted
   prose, never execution; recognizable unsupported claims are corrected visibly.
3. **Memory brief:** all seven operations have a validated interface and independent
   persistence checks. Modifiers are separated from facts; context uses user turns;
   ambiguity is scoped and clarified. Compound outcomes remain independent. Manual
   saves still work with learning off, use exact deduplication without embeddings,
   and return actual IDs. Corrections retain superseded history and existing backup
   protection. Optional ambiguous classification is local-only, already-loaded,
   strictly validated and bounded to two seconds, with no proxy/cloud/redirect path.
4. **Other concrete failures:** verified shared atomic writes, flushed/read-back
   Saved Notes appends, accurate failed-note replies, collision-safe letter/image
   names, surfaced letter-delete/index failures, verified letter/agent persistence,
   and refusal to treat corrupt letter/agent data as absent. Existing `save this`
   still saves a Saved Note. Native capability text now reflects actual behavior.

### Verification and review

Before-change focused filesystem/notebook suite: **82 passed**, 12.59 s.
Intermediate complete suite: **1,003 passed, 1 skipped**, 156.70 s, at
`cursiv-check-d9emc9po/pytest.log` in the task visualization workspace. After final
receipt/Saved Notes/read-only-file additions, focused suite: **209 passed**, 20.68 s,
at `cursiv-check-_a7kf7b6/pytest.log`.

**Final exact-source full suite: 1,008 passed, 1 skipped, 150.00 s.** The skip
requires macOS Keychain. Final log:
[pytest.log](C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/cursiv-check-2a48gvi8/pytest.log).
All follow-up Python sources match this test snapshot byte-for-byte. Syntax and
`git diff --check` pass. Comparison against the pre-follow-up snapshot finds exactly
the intended 24 files (repository LF versus Windows CRLF normalized for clean
tracked files). Earlier notebook/rendering/Saved Notes sources and original handoff
sections are preserved. The real `.cursiv/strands.jsonl` remains 78 records with
SHA-256 `ecc4173118c249396e58fd8aa60e04c213dd6bd856b7d8c7b7b46f12648e852b`.

Tests use isolated source snapshots, disposable user data, actual byte reads,
fresh Python processes, portable-drive relocation and stubbed provider protocols.
No live qwen/cloud inference or rebuilt executable restart is claimed. Earlier
failed/interrupted runs and their fixes are documented in the report. The existing
Qt timer regression now waits for actual delivery for up to 250 ms while preserving
its production 40 ms interval and single-batch/GUI-thread assertions. A new UI test
also disables unrelated live title generation before closing its test panel.

### Remaining limits

Locks are process-local; simultaneous instances, hostile filesystem races and
hardware power-loss/removal are not certified. A failed verification after an
actual write may leave uncertain data or an orphan letter, which is preserved for
inspection rather than deleted. Third-party plugin output is explicitly unverified.
Unusual language may require clarification; the prose guard is not exhaustive proof.
Real user memory/notebook data was not migrated or rewritten. Installer, updater,
networking policy, website, README and benchmark sources were not modified.
The earlier self-model/metacognition proposal remains outside these concrete
action-path repairs; this handoff does not claim it was implemented.

## 2026-10-21: Native Field Notebook repair

Branch: `codex/native-field-notebook`. All pending Saved Notes/chat-rendering
work below was preserved. No commit, push, release, installer build or deployment.

Audit found that the graphical notebook already uses `core/fieldlog.py`'s real
`add`/`correct`/`current`/`verify` APIs, while natural notebook requests could reach
generic filesystem planning or ordinary local-model prose. Explicit command
replies also disappeared from history, losing context for "add it" follow-ups.

Changed for this task:

- New `core/notebook_tools.py`: application-owned allowlist for native create,
  retrieve and chain/photo verification; deterministic routing; user-only context;
  actual record-ID/read-back/chain receipts; accurate unconfirmed-write errors.
- `core/fieldlog.py`: optional hashed request metadata, duplicate checking under
  the existing append lock. Original records, schema and chain logic remain.
- `ui/chat_app.py`: route native notebook requests before models, files, memory
  or verification; optional stable scope for non-GUI callers.
- `launcher/chat_commands.py`: native NotebookResult and early notebook route.
- `launcher/chat_panel.py`: provider prefixes cannot bypass native routing;
  per-conversation request scope; persist user context and optional receipt data.
- New `tests/test_notebook_integration.py` and
  `docs/FIELD-NOTEBOOK-INTEGRATION.md` with audit, behavior, related-tool findings,
  tests and limits. Existing regression files were not modified for this task.

Corrections to existing records still use the graphical notebook's append-only
correction workflow. No generic file, installer, updater, networking, memory-store
or unrelated application behavior was repaired as part of this notebook patch.

Baseline full suite was 864 passed / 1 skipped / 1 preexisting chat timer failure.
A focused intermediate run passed 116 tests. Final exact-source full suite:
**920 passed, 1 skipped, 140.34 s**; the skip requires macOS Keychain. The timer
failure did not recur across three post-change full suites (913, 914, then 920
passed). Final log: `cursiv-check-dhckjpb1/pytest.log` in this task's visualization
workspace; see the notebook report for the full link and earlier test failures.
Model paths are stubbed to prove the native route bypasses them; no live
qwen/cloud model test or installed-executable restart is claimed. Fresh Python
processes independently check actual disposable notebook bytes, restart
persistence and portable storage. Changed Python files match the final test
snapshot exactly; unrelated pending files and this handoff's earlier sections
were preserved. Syntax/diff whitespace checks passed.

## 2026-10-21: Chat rendering performance (subsequent uncommitted work)

The latest request narrowed this work to the response formatting delay. The
earlier approved self-model/metacognition implementation is **not implemented
in this performance patch**. It remains separate work. Existing Saved Notes
edits described below were preserved.

Branch: `codex/chat-rendering-performance`, based on the owner's U80 commit
`4d24ffef078d7f72c6e5357b48f6facdd4415769`. No commit, merge, push, release,
version bump, installer build, or deployment was performed.

### Read-only inspection and profiling findings

- The old renderer already selects only the active response with QTextCursor.
  It does not rebuild every previous message's Markdown after a turn.
- Per-token document edits and synchronous whole-conversation export/save were
  measured. The 1,000-message baseline's median final-token-to-ready time was
  493.2 ms; 464.9 ms was spent in the synchronous save path.
- No formatting-only secondary LLM call was found. Existing answer verification
  can execute four sequential calls (ledger/check/revision/recheck). A regression
  records that path without making a network/model request. The owner confirmed
  scrolling/controls remain responsive during the reported long wait, supporting
  background checking as its likely cause. No real model checking time was measured.

### Files and execution paths changed for this task

- `launcher/chat_rendering.py` (new): pure streaming boundary buffer and a GUI-thread
  HTML export cache. Cache prefixes cover unchanged messages; new blocks alone are
  exported. Older-content edits/theme switches invalidate the prefix. Clipboard
  fragment markers are stripped to preserve history when reopening exports.
- `launcher/chat_panel.py`: 40 ms batches, incremental completed blocks, one targeted
  final parse, a final-message revision cache, immediate draft formatting when checks
  start, preserved scroll/selection/following, and asynchronous autosave handoff.
  Done/error/stop/image/write-approval paths flush queued fragments. Save failure
  reporting and the existing leave confirmation retain the chance to retry.
- `cursiv_engine/ui/chat_app.py`: optional `on_stage` callback announces the end of
  initial generation. No changes to verifier decisions, model prompts or routing.
- `launcher/conversations.py`: one ordered worker accepts plain Python snapshots;
  streamed JSON and existing temporary-file replacement preserve the same storage
  schema. Explicit save/open/rename/delete waits for queued saves. A storage lock
  protects delayed title updates and manual changes from overwriting newer snapshots.
  Person/directory context is captured at submission. Normal exit drains queued saves.
- `tests/test_chat_rendering.py` (new): 30 deterministic, isolated regression cases.
- `tests/test_ui_redesign.py`: the autosave test double accepts the new background
  keyword; its original assertions remain.
- `scripts/benchmark_chat_rendering.py` (new): isolated, offline replay at 10/100/1,000
  messages, Markdown timings, document rebuild/edit counts, GUI heartbeat, native
  memory sampling, and a controlled post-generation checking pause.
- `docs/CHAT-RENDERING-PERFORMANCE.md` (new): complete measurements, method,
  limitations, source observations, reproduction commands and regression coverage.
- `bench/results/chat-rendering-20261021-{before,after}.json` and
  `bench/results/chat-check-delay-20261021-{before,after}.json` (new): raw synthetic
  measurements. These are separate from the existing model/reliability benchmarks.
- This handoff section.

All Qt document and widget operations remain on the GUI thread. An early worker
fragment-export candidate crashed an isolated test and was removed. The final
save worker receives immutable HTML/text and copied message data; it performs
no Qt operations. Markdown parsing measured only milliseconds, so adding a new
background parser and extra Markdown/HTML conversions was not justified.

### Results and remaining limits

Median end-of-source-token → ready timings (three offline replays, 898-character
mixed Markdown response, real isolated autosave):

| History messages | Before | After |
| ---: | ---: | ---: |
| 10 | 59.0 ms | 18.7 ms |
| 100 | 103.9 ms | 30.4 ms |
| 1,000 | 493.2 ms | 71.5 ms |

Visible draft rendering finished in 14–18 ms median after the final source token
in the optimized standard replay. Full-document rebuilds during streaming were
zero before and after. Document edits fell from 67 to 12. The 1,000-message
maximum GUI heartbeat gap fell from 487.9 to 65.4 ms (median of run maxima).
Peak working set at that size rose from 166.8 to 173.2 MiB because of the HTML
cache; working-set growth during the turn fell from 32.54 to 25.51 MiB.

With a simulated 1,000 ms checking pause, formatting latency fell from 1,015.5 to
14.8 ms. Input readiness still waited for checking (1,013.7 ms after). This fixes
formatting being held behind verification; it does not accelerate the verifier
itself or guarantee a short complete turn on every model/device. Later verified
corrections still update the active message. Source generation, real model checks,
the main-window sidebar, startup, loading history and explicit theme switches
are outside the panel replay. Normal rendering and readiness meet the 250 ms
target for this measured corpus. Disk completion remains separately measured.

### Validation

- Baseline before performance edits: **835 passed, 1 skipped**, in the isolated
  `cursiv-check-zm6ue7e4` snapshot. The skip is macOS Keychain on Windows.
- Focused UI/verification/replacement/Saved Notes checks: **144 passed**,
  `cursiv-check-yudki3b1/pytest.log`.
- Final full suite: **865 passed, 1 skipped in 132.88 s**,
  `cursiv-check-xe9fd2rx/pytest.log`.
- Regression coverage includes tables, code fences, links, cached final replies,
  unchanged 10/100/1,000-message histories, selection/copy, scroll following,
  replacement drafts, errors/stop, image order, theme changes, save round trips,
  background saves/failures/retry/order, and delayed title/manual-rename races.
- Initial test failures exposed Qt worker export and clipboard marker issues;
  both candidates were corrected before the final passing full run. A test also
  needed to reset the verifier's existing session state to be independent of
  previous tests; verification behavior itself was preserved.
- `git diff --check` passed. Only the performance files listed above and the
  already pending Saved Notes files appear in the working tree.
- Existing `chat_commands.py`, `nav_windows.py`, `saved_notes.py`,
  `saved_notes_dialog.py` and `test_saved_notes_viewer.py` match the first
  performance-task snapshot byte for byte. The two existing Saved Notes panel
  action methods are AST-identical, and all prior handoff text was retained.
- Source saved-note archive hash remains
  `ecc4173118c249396e58fd8aa60e04c213dd6bd856b7d8c7b7b46f12648e852b`.
  No real memories, conversations, field logs or note records were migrated or
  rewritten. Tests and benchmarks used synthetic data in isolated homes/copies.

The installed U80 application has not been replaced. Release/installer work
requires the owner's separate instruction. Website, README, networking, updater,
installer, memory algorithms and unrelated settings were not changed here.

## 2026-10-21: Saved Notes viewer (new work after the U80 tag)

The owner requested a saved-notes library consistent with What I Remember.
An architecture audit was reported before edits. During that audit the owner
committed/tagged the preceding work as `4d24ffe` / `v3.14-U80` on `main`.
**This viewer is subsequent uncommitted work and is not part of that tag.**
No commit, merge, push, tag replacement, version bump or installer build was
performed for this viewer. Prior sections below describe their historical state;
the earlier memory/portable/curiosity implementation is now in the owner's U80 commit.

### Audit findings

- What I Remember uses `memory/semantic.py` personal facts; Saved Notes uses the
  separate `core/strand_store.py` archive at its existing `APP_DATA/strands.jsonl`.
- Note categories already exist as `territory_tag`. Source, timestamp, score,
  provenance, IDs and extra metadata are already in each original record.
- `query` and `synthesis` display columns are shortened when notes are written,
  but the encoded `strand` retains the original complete question/answer. The new
  presentation decodes that existing payload; it does not rewrite shortened fields.
- `notes`/`strands` previously formatted recent records directly into chat. The
  Memory & Knowledge navigation button sent that same dump command.
- There is no supported saved-note deletion API. Unlike personal fact deletion,
  deleting these records would require new persistence behavior. That change is
  explicitly outside this UI task, so Delete selected is disabled with an explanation.
- Audit of the configured **source-checkout** archive found 78 notes, not 17,
  in eight existing categories. All 78 encoded payloads decoded successfully.
  The reported 17-note installed copy can use a different APP_DATA location; it
  was not located, copied, migrated or replaced. Tests separately use the requested
  17-note fixture: General 3, Worldmodel 13, Architecture 1.

### Files changed and execution paths

- **Added `launcher/saved_notes.py`:** pure presentation helpers read the existing
  configured archive without calling category-definition initialization, decode
  full content with the existing codec, filter/sort the viewer snapshot, and export
  explicitly selected original records. Export uses Qt's atomic QSaveFile with
  read-back verification and refuses Cursiv internal data destinations.
- **Added `launcher/saved_notes_dialog.py`:** existing Qt/theme pattern, count
  heading, category sidebar/counts, search, newest/oldest/category sort, expandable
  read-only full text and a second expandable metadata section. Multi-selection,
  copy, JSON export, Refresh and Done are provided. Text is rendered as plain text;
  preview tooltips escape markup. No note editor or storage deletion was added.
- **`launcher/chat_commands.py`:** a `NotesResult` UI action recognizes browsing
  requests before the legacy text-dump alias. Explicit `note show <8-character-id>`
  retrieves that complete note directly. Existing saved-memory retrieval/scoring
  APIs and ordinary conversational requests remain available.
- **`launcher/chat_panel.py`:** a Qt signal carries category/query from the command
  worker to the GUI thread. The GUI opens or focuses one reusable notes dialog.
  Widgets are never created in the command worker. Only a short opening message
  is added to chat; note records are not dumped there or inserted into chat history.
- **`launcher/nav_windows.py`:** Memory & Knowledge's Saved notes card opens the
  viewer directly, closing its modal navigation window first.
- **Added `tests/test_saved_notes_viewer.py`:** isolated 17-note fixture and UI,
  command routing, export, persistence, offline/relocation and theme checks.
- **This `HANDOFF.md`:** audit, limitations, validation and release-state record.

No changes to `memory_dialog.py`, `strand_store.py`, note encodings, persistence,
classification, scoring, automatic learning, retrieval algorithms or field logs.
Search filtering here is a viewer-only keyword filter, not a replacement for
the existing similarity/search API. No framework, dependency or network call added.

### Usage

```text
Show my saved notes.
What notes do you have?
Open my notes.
Show your worldmodel notes.
notes architecture
notes search <words>
note show <note-id>
```

Or Memory & Knowledge -> Saved notes -> Open. Clicking the disclosure arrow
expands a concise preview into scrollable full content. Metadata stays collapsed
until requested. Repeating a browsing command reuses/focuses the same window.
Copy copies full selected content; JSON export retains the original IDs and every
original record field. It is an inspectable JSON export, not an existing signed
`.cursivpack` import package. Export does not modify notes or grant model filesystem access.

### Validation

All automated runs use disposable snapshots/empty homes. The external test runner
was updated to overlay `git diff HEAD`, so staged owner edits are included too;
that runner is outside the repository. No index/staging changes were made by Codex.

- Existing focused regressions after routing: **70 passed**, 9.99 s,
  `cursiv-check-097mdybr/pytest.log`.
- First viewer test run: **60 passed, 1 failed**. Failure was a test double that
  had not initialized the chat panel's deferred backend reference. The test now
  supplies the same backend reference as the running application.
- Focused viewer/help/memory suite after correction: **61 passed**, 7.49 s,
  `cursiv-check-arce08n2/pytest.log`.
- Light/dark screenshots were visually inspected from that focused run. Windows
  Segoe UI was explicitly loaded in the offscreen test setup so preview text is
  readable; the production viewer uses the application's existing theme/font setup.
- Fixture assertions cover all 17 records/counts; content beyond 1,000 characters;
  exact original metadata; keyword filters/sorting; copy/export; disabled unsupported
  deletion; GUI signal delivery; focus/reuse; honest read failures; existing note
  retrieval and What I Remember; fresh-process offline reads before/after moving
  the portable data directory. The fixture asserts byte-identical archive contents
  after every test and no generated category-definition file.
- Full regression suite: **835 passed, 1 skipped**, 141.91 s,
  `cursiv-check-zm6ue7e4/pytest.log`. The skip is Mac Keychain on Windows.
- After making the export's internal-directory check case-insensitive for Windows:
  **18 passed**, 4.95 s, `cursiv-check-dxrr8oza/pytest.log` (entire saved-notes suite).
  No implementation edits followed this check.
- `git diff --check` passed. Final scope is the three existing launcher routing/UI
  files, two new launcher viewer/helper files, one test file and this handoff.
  No version, installer, store, memory-dialog or algorithm edits are present.
- The real configured source archive remained byte-identical before/after work:
  SHA-256 `ecc4173118c249396e58fd8aa60e04c213dd6bd856b7d8c7b7b46f12648e852b`.
  Its original 78 records and all classifications remain untouched.
- HEAD and the owner's U80 tag still resolve to
  `4d24ffef078d7f72c6e5357b48f6facdd4415769`. This viewer is unstaged/uncommitted;
  no Git cleanup, history rewrite, tag overwrite or release action was performed.

Test snapshots and previews are under
`C:\Users\joshu\.codex\visualizations\2026\10\21\01a15c12-fb2b-7d00-9f67-101caecdd403`.

### Review limits

- Delete remains unavailable because the current archive has no deletion API;
  no unsafe file rewrite or pretend confirmation flow was introduced.
- Existing notes that lack a valid encoded full payload can only show the text
  actually available in their stored record, with a visible decoding warning.
- Counts describe the current loaded snapshot; Refresh picks up external saves.
- Actual two-PC removable-drive use and the packaged viewer still need manual
  acceptance. Relocation is verified with moved temporary folders and two fresh
  interpreters; this is not a physical two-PC claim.
- The viewer is not in the owner's U80 tag/installer. Review and a new release are
  required before distributing this subsequent change. Do not move the U80 tag.

---

## 2026-10-21: portable storage, historical recall, presence and curiosity (Claude review)

**Status: uncommitted first implementation on `codex/autonomous-memory-v1`.**
The owner approved working through the audited proposals "from the top down."
The earlier memory/filesystem changes below were preserved. This section extends
their scope; installer/updater/release configuration and website files were not
changed. No feature commit, merge, push, deployment or installer rebuild was made.
No real personal data migration was performed during development.

### Architecture and execution paths

1. `launcher/main.py` -> `portable.activate()` runs before data imports. A detected
   portable drive that fails activation now stops startup rather than falling back
   to host storage. Activation sets HOME/USERPROFILE, APP_DATA/data overrides,
   APPDATA/LOCALAPPDATA and TEMP/TMP to drive-local locations before field defaults.
2. Existing layout retained: `Cursiv/` binaries, `Home/.cursiv/` data,
   `Workspace/` authorized user files, `Ollama/` runtime, `Models/` model store.
   `data_home` skips its installed-app junction repair in portable mode.
3. First portable startup snapshots legacy application `.cursiv` stores and the
   destination with SHA-256 manifests, verifies copies, then copies missing files.
   Differing same-path contents STOP migration with a backup location. Original
   stores remain intact. There is no automatic merge or "newest file wins" rule.
4. `core/paths.py` encodes portable references as `portable://...` and resolves
   them from the current drive. Coding projects and newly imported document source
   references use these helpers. Old absolute external coding projects are not
   automatically authorized on a different host; explicit session selection is needed.
   Parsed document text already survives independently of an original source file.
5. `usb_maker.make_usb()` now preserves existing private destination files and no
   longer invokes private-data wiping during a refresh. It no longer sweeps the
   whole drive for `.part` files. Copy staging uses unique adjacent files, and
   cleanup/pruning avoids linked directories and personal stores. New private
   configuration copies alone are exported for portable credential readability.
   The UI explicitly asks before required runtime/model downloads during USB creation.
6. Portable chat with no usable model returns diagnostics instead of pulling one.
   `ollama_host.exe()` retains host-runtime discovery after LOCALAPPDATA redirection.
   An already-running host Ollama service still has its own model store; existing
   diagnostics explain this. Cursiv does not silently reconfigure that service.
7. `chat_commands.handle_command()` routes field recall BEFORE generic memory
   commands; `chat_app.chat()` also supports the same reader directly. Exact
   notebook commands and natural historical requests use `core/field_recall.py`.
   Retrieval is deterministic, local, and independent of native model tool calling.
8. `field_recall.query()` reads only the authorized notebook path, verifies records
   and chain links, filters by text/sample/date/entry, follows correction links,
   and returns structured bounded results. No index, migration, historical rewrite,
   log repair, or signing-chain change was introduced. Read errors cannot become
   a fabricated historical answer. Integrity warnings are shown explicitly.
9. `core/state_store.py` supplies strict JSON reads, verified atomic writes,
   content-addressed recovery backups, a shared lock, link checks and an 8 MB limit.
   Style and project stores retain their existing JSON structures but use it for
   safe writes; corrupt stores no longer silently become empty before rewriting.
10. `core/presence.py` separates stable communication principles/preferences from
    learned personal facts and produces an application-state snapshot. Existing
    identity, style, self-report and answer-verification mechanisms are reused.
    Presentation preferences explicitly defer to evidence, safety and permissions.
    Style adaptation has an independent control; no subjective experience is claimed.
11. `core/curiosity.py` holds per-person journal state; `curiosity_engine.py` owns
    evidence retrieval, candidate rules, scoring, deduplication, event budgets and
    reevaluation. `launcher/curiosity_dialog.py` presents the same backend used by
    conversation commands. The settings Answer page opens the dialog.

### Curiosity lifecycle and evidence

- Eligible event -> authorized bounded retrieval -> deterministic candidate ->
  validated source IDs -> deduplication -> budget/priority -> verified save ->
  optional occasional suggestion. New related evidence updates review history;
  it does not establish resolution or causation automatically.
- Automatic evaluation and suggestions both default OFF. Frequency defaults to
  every five eligible events; default active budget is five per project association.
- Existing memory learning controls and non-retention/sensitive-content filters
  gate automatic work. A separate single-flight daemon task is used, not the
  memory queue. Captured memory generation and journal control epoch cancel stale
  work after disable/clear. Retrieval happens outside the journal mutation lock.
- This version makes **zero additional model inference calls** and has no cloud
  fallback or recursive investigation loop. It does not autonomously execute
  commands, fetch sources, edit research files, or write field observations.
- Rules cover varying comparable measurements with missing collection context,
  repeated variation, potential simultaneous sample conflicts, and explicitly
  stated assumptions. Comparisons require matching stated units. Correction
  originals are excluded from comparisons when their correction is selected.
- Evidence distinguishes recorded observations, reported claims, inferred memory,
  hypotheses and unknowns. Field and memory IDs are retained with digest/excerpt
  snapshots. A field observation proves what was recorded, not independent truth.
- Journal statuses: Proposed, Open, Investigating, Awaiting evidence, Resolved,
  Dismissed, Superseded. Reopening enforces the active budget. Dismissed and resolved
  questions remain in deduplication history. Suggestions are limited to one per day
  and are never repeated for the same investigation automatically.
- Explicit resolution requires a currently readable field or direct/manual memory
  reference. Older field entries can be targeted individually, beyond the latest
  50-record context window. User selection of supporting evidence is recorded;
  Cursiv does not certify the scientific sufficiency of that resolution.
- Journal data uses `Home/.cursiv/curiosity/<person>.json` in portable mode. Demo
  journal data follows the existing isolated demo root. No absolute evidence-file
  paths or search index are required for relocation. Journal versions allow future
  extension without altering original evidence stores.

### Files added in this phase

- `cursiv_engine/core/state_store.py`: bounded strict/atomic JSON persistence.
- `cursiv_engine/core/field_recall.py`: verified historical retrieval and routing.
- `cursiv_engine/core/presence.py`: identity preferences and observed state.
- `cursiv_engine/core/curiosity.py`: journal schema, lifecycle, evidence and budgets.
- `cursiv_engine/core/curiosity_engine.py`: event-driven rules and commands.
- `launcher/curiosity_dialog.py`: inspect/create/review/update/export controls.
- `tests/test_portable_recall_curiosity.py`: deterministic integration/failure tests.
- `tests/data/curiosity_cases.json`: reproducible six-scenario evaluation fixture.

### Existing files modified in this phase

- Startup/storage: `launcher/portable.py`, `launcher/main.py`,
  `launcher/data_home.py`, `launcher/usb_maker.py`, `core/paths.py`.
- References/runtime: `coding/brain.py`, `core/documents.py`, `core/ollama_host.py`.
- Recall/events: `launcher/chat_commands.py`, `ui/chat_app.py`,
  `launcher/field_notebook.py` (post-save notification only).
- Presentation/UI: `core/style.py`, `core/selfknow.py`, `memory/projects.py`,
  `launcher/settings_dialog.py`.
- Test isolation: `tests/conftest.py`, `tests/test_core.py`.
- This `HANDOFF.md`. The previous phase's other pending files remain present.

Paths abbreviated above under `core/`, `memory/`, `coding/`, `ui/` are relative
to `cursiv_engine/`. No changes to `core/fieldlog.py`, record formats or hash chaining.

### Usage

Historical recall examples:

```text
What did I record yesterday?
Find the observation I made about water quality.
Show me the last ten field log entries.
field log sample ABC-45
field log between 2026-10-01 2026-10-21
field log entry <entry-id>
field log recent offset 10
Summarize my research notes from last week.
```

Summaries are extractive, cited record listings, not invented narrative analysis.
"Last week" means the previous Monday–Sunday calendar week in local time.
No session/project identifier is invented for records lacking that metadata;
ambiguous last-session requests ask for a date range or sample ID.

```text
presence status
style adapt off
curiosity
curiosity evaluate
What are we missing?
curiosity add What measurement would test this assumption?
curiosity show CUR-<id>
curiosity review CUR-<id>
curiosity investigate CUR-<id>
curiosity resolve CUR-<id> :: field:<entry-id>
curiosity dismiss CUR-<id>
curiosity reopen CUR-<id>
curiosity automatic on
curiosity suggestions on
curiosity frequency 5
curiosity max_active 5
curiosity export
curiosity clear confirm
```

Clear disables automatic curiosity, but verified recovery backups remain. It is
not a secure erase operation. The dialog explicitly explains this before clearing.

### Tests and measured scope

All tests run in a Git-archive snapshot overlaid with pending edits, using an empty
HOME and no copied personal data. Test subprocesses and relocation fixtures also
use disposable stores. The source checkout's real memory/log data is not used.

- Baseline before this phase: **790 passed, 1 skipped**, 128.85 s,
  `cursiv-check-jpv5vjwi/pytest.log`.
- First existing-feature focused regression: **123 passed**, 16.82 s,
  `cursiv-check-bcd1zjyx/pytest.log`.
- First new integration plus regression run: **103 passed**, 12.88 s,
  `cursiv-check-56mloehl/pytest.log`.
- First full implementation run: **811 passed, 1 skipped**, 145.67 s,
  `cursiv-check-u1q9v8wk/pytest.log`.
- Follow-up cancellation, USB, runtime, relocation checks: **54 passed**, 9.76 s,
  `cursiv-check-dckahq2g/pytest.log`.
- Final full implementation run: **817 passed, 1 skipped**, 137.69 s,
  `cursiv-check-rwf65iku/pytest.log`.
- After removing a duplicate router call and tightening benchmark assertions:
  **46 passed**, 13.62 s, `cursiv-check-y6w84n34/pytest.log` (new integration suite
  plus existing field-log regressions). No implementation edits followed this check.
- `git diff --check` passed. Final review confirmed no installer, updater, website,
  deployment, README or privacy-policy edits. Branch remains
  `codex/autonomous-memory-v1`; all feature changes are uncommitted.

Test snapshot folders live under:
`C:\Users\joshu\.codex\visualizations\2026\10\21\01a15c12-fb2b-7d00-9f67-101caecdd403`.
The only skipped baseline/full-suite test is Mac Keychain on Windows.

The six-case benchmark compares the deterministic question-generation path OFF
with ON, not two live LLMs or scientific reasoning quality. Fixtures cover missing
conditions, mismatched units, already-documented conditions, noncausal variation,
reported assumptions, and ambiguous single observations. It checks source IDs,
duplicates, expected questions, unchanged original logs and verified persistence.
Its JSON report separates retrieval/detection time from evaluation/persistence time.
No general intelligence or model reasoning improvement is claimed from this fixture.

Full-run benchmark artifact:
`cursiv-check-rwf65iku/curiosity-benchmark.json`. Six scenarios produced three
expected questions across the positive scenarios and none across the three negative
scenarios, with no missing expected gaps, duplicates or unsupported references
under the fixture assertions. All six persisted outcomes verified. Retrieval and
detection took about 4.4–6.6 ms; full evaluation/persistence took 6.1–97.8 ms per
scenario on this machine. Added model calls: zero. The final focused run reran the
same fixture with stricter exact candidate-count assertions; its artifact is
`cursiv-check-y6w84n34/curiosity-benchmark.json`. These small fixtures do not measure
large-drive performance, ordinary model-response latency or broad research quality.

### Known limitations / manual acceptance for Claude and owner

- This is the smallest rule-based first version. Broad scientific hypothesis
  generation, arbitrary conceptual contradictions and automatic conclusions are
  not implemented. An optional bounded local-model proposer is a future extension.
- Evaluation considers the latest 50 valid field records and up to 30 memory facts.
  Those selected records cannot establish that a variable was never recorded.
  Journal associations are selected scopes, not inferred ownership metadata for
  all notebook entries. Review reports snapshots missing from the current selection
  honestly; it does not silently remove old evidence.
- No field-log index is needed initially. Scans are limited to 64 MB / 100,000
  lines, individual lines to 1 MB, results to 50 with pagination. The journal has
  a 1,000-entry and 8 MB review limit; export/archive is required at that point.
- Extra work is event-driven and bounded, but large-drive/slow-USB latency and
  full interactive responsiveness still need representative hardware testing.
- Memory, style, project and journal data remain separate compatible stores.
  Retention controls prevent new automatic learning; they do not securely erase
  previously authorized journal snapshots or backups when a memory fact is forgotten.
- Old arbitrary absolute references in historical prose/doc metadata are not
  rewritten or guessed from a changed drive letter. Imported document text still
  works; users can reselect/reimport a source when necessary.
- Portable data and copied credentials are unencrypted unless the owner encrypts
  the drive. Windows may retain OS-level traces. An existing host Ollama service
  uses its own storage. Manually copied DPAPI-bound credentials may require reentry.
- Existing atomic append/fsync logging and new atomic state writes reduce damage
  risk; they cannot guarantee durability after unsafe unplugging or hardware failure.
  Static path checks are not an OS sandbox against a hostile simultaneous racer.
- **Still manual:** packaged Windows startup, actual Ollama interaction, two
  compatible PCs/accounts, physical USB/SSD safe eject/reinsert, actual drive-letter
  reassignment, and representative large/slow-drive performance. Tests simulate
  relocation with fresh interpreters and moved directories, not a second PC.
- Before shipping, build a separate review installer only after explicit owner
  authorization. Do not overwrite U79 or publish this uncommitted feature as U79.

---

## 2026-10-21: automatic memory and explicit persistent file memory (Claude review)

This section describes the current **uncommitted feature work**, not a shipped release.
Branch: `codex/autonomous-memory-v1`. The owner approved implementation after the
read-only memory audit and requested this handoff. Installer, updater, networking
implementations, website, README and unrelated settings are outside scope.
Do not commit, merge, push this feature, change the release tag, or publish an
installer without another explicit owner instruction.

### U79 recovery copy

At the owner's separate request, the exact original U79 commit and source history
were copied to `https://github.com/Cursiv-Local/Cursiv-Backup-u79`.
Both `main` and `v3.14-U79` there were verified as
`661d3183389226ca16a842235450da31c16da8cc`. No feature changes were pushed.
This is a source backup; GitHub release binaries were not copied.

### Read-only findings and scope presented before implementation

The personal memory store already supported automatic learning. The missing work
was reliability and policy, not a second database:

* `launcher/chat_panel.py:_run_turn` routes explicit memory commands through
  `launcher/chat_commands.py:handle_command` to `memory/semantic.py:memory_command`.
  `remember` and the memory dialog call `add_fact`, then `_write_facts`, then
  `core/atomic.py:write_text` (flush, fsync, replace).
* Normal chat streams through `ui/chat_app.py:chat` / `_chat_inner`; `_learn_later`
  formerly launched an independent daemon thread for every exchange. The learner
  accepted model-generated JSON strings, weakly filtered them, and used the same
  fact store. Exceptions and save outcomes were largely discarded.
* `_quick_llm` could use free cloud keys for extraction. Phone memory additionally
  permitted Cursiv Cloud fallback. The learning switch did not consistently gate
  the separate project, coding-environment, coding-lesson and style learners.
* `list_facts` suppressed read errors as an empty store and could trigger a legacy
  repair write. That risked incomplete rewrites and needed locking/backups.
* Retrieval is `phases.run` -> `_build_strand_context` -> `build_context` ->
  `recall`, using local embeddings or keywords. Login sets the person; fact data
  is reread from disk. `launcher/conversations.py` separately saves transcripts
  and restores their messages; conversation context is not proof of fact storage.
* Filesystem functionality already existed in `core/tools.py` (general read-only
  tool routing) and `chat_app.execute_tool` (workspace read/write tools for cloud
  models). Local models lacked a dependable write route. Credential protection
  differed, broad read tools lacked workspace authorization, and writes were not
  consistently atomic or verified. The additional filesystem audit and planned
  shared validation/application-command route were presented before editing.

### Changes and execution paths for review

* **New `memory/formation.py`:** conservative direct-statement selection,
  credential/sensitive-topic and non-retention exclusions, validation of optional
  model suggestions against user evidence, bounded single-worker queue, dedup of
  recent job IDs, content-free diagnostics in the existing local logs directory.
* **`memory/semantic.py`:** preserves JSONL and existing API fields. New automatic
  facts add optional category, evidence, provenance (message ID and supporting
  user quote), event ID, slot, status and updated time. Automatic origin remains
  `inferred`; a direct quote is evidence of what the user said, not independent
  verification. Mutations abort on failed reads and confirm serialized writes by
  read-back. A reentrant lock serializes repair and fact operations.
* Before rewriting existing data, one byte-for-byte snapshot of the facts and
  colocated memory settings is saved in
  `APP_DATA/backups/autonomous-memory-v1/`, with SHA-256 files. Snapshots are
  verified and not overwritten; a bad backup blocks the rewrite. The existing
  learned-memory repair remains compatible and is now within this protection.
* Repetitions do not create new facts. Different choices are checked for conflict
  before similarity suppression. Explicit corrections can supersede automatic
  preferences in a recognized matching topic; manual facts and ambiguous
  contradictions are retained. Normal retrieval excludes superseded rows; the
  memory dialog can include them. Legacy rows without status remain active.
* **`ui/chat_app.py`:** capture the person and event before asynchronous work;
  reuse the post-exchange trigger and bound jobs. Direct statements do not need
  an extraction model. Optional extraction calls `_memory_llm`, which is local
  only; `_quick_llm` remains unchanged for unrelated jobs such as titles.
  Assistant drafts are not supplied as fact evidence. Direct user facts may be
  retained even if answer verification failed; unsupported model suggestions may
  not. File-command results bypass AI answering/checking and auto-learning.
* **`memory/projects.py`, `coding/brain.py`, `core/style.py`:** automatic learners
  honor the existing learning setting and exclusion policy. Explicit controls
  remain available. **`launcher/chat_commands.py`** and **`launcher/phone_sync.py`**
  use the local memory callback; the phone transport/endpoints/sharing controls
  were not changed. A failed durable fact write propagates so phone progress is
  not silently advanced past that exchange.
* **`launcher/memory_dialog.py`:** source/evidence/status details, historical-row
  toggle, and honest read/delete/write error handling. Existing settings UI and
  the `learn` setting are reused.
* **New `core/file_access.py`:** common authorization and validated dispatch used
  by both existing file-tool paths. Resolves paths inside the selected workspace;
  rejects traversal, alternate streams, symlinks, junctions, hard links, protected
  paths and detected credential content. UTF-8 text operations have a 2 MB limit.
  Writes use unique adjacent temporary files, flush/fsync, atomic replacement or
  no-clobber creation, and exact read-back. Appends preserve existing bytes.
* **`core/tools.py` / `chat_app.execute_tool`:** reuse this backend rather than
  separate read/write implementations. General built-in file tools require the
  authorized workspace; a model cannot supply its own authorization root.
  Existing cloud tool calls cannot overwrite existing files without confirmation.
* **`launcher/chat_panel.py` / `chat_commands.approve_write`:** reuse the existing
  confirmation dialog, carrying operation and expected original hash. A file
  changed while confirmation is pending is refused. Results no longer prepend a
  success checkmark to errors. File and conversational memory outcomes are
  independent when both are explicitly requested.

### How to exercise the feature

Automatic facts: ordinary statements such as `I prefer Rust over Python` and
`I'm building Cursiv for field research`. Inspect with `what do you remember`,
the existing memory window, or `memory diagnostics`. Disable with
`memory learn off`; manual `remember` and `forget` still work.

For explicit files, first choose `workspace <existing-folder>` and `files on`.
`workspace desktop` resolves the normal/OneDrive Desktop alias. Then:

```text
file help
file list .
file read project.md
file create project.md :: Exact notes to persist
file append project.md :: Additional observations
file replace project.md :: Complete replacement content
file save conversation project-transcript.md
file remember project-fact.txt :: The exact fact to save in both places
```

These are application commands and work without model-native tool calls or
internet. Quoted natural forms such as `read "project.md"` are also accepted.
Ambiguous natural requests ask for an exact authorized filename/content rather
than claiming the application has no filesystem capability. Existing files need
confirmation; deleting files is deliberately unavailable in this first version.
Conversation export stores role-labelled actual messages, not invented
"established facts" or a model-generated success claim.

### Validation record

Baseline used a clean `git archive HEAD` in an isolated source copy with an empty
HOME/USERPROFILE/CURSIV_REAL_HOME: **727 passed, 1 skipped, 1 teardown error**
in 123.60 seconds. The error was the real-data guard observing a copied
`memory_facts.jsonl` change during an unrelated end-to-end field test. Actual
user data was outside this test environment.

The first substantive focused run was **269 passed, 1 failed, 1 teardown error**.
It exposed the plural `passwords` exclusion and a guard that recomputed watched
paths after a portable-mode test changed HOME. Both were corrected. A prior
sandbox-only run could not create pytest fixtures; it is not a functional result.

`tests/conftest.py` now isolates all memory/companion-store paths and prevents
ordinary chat tests from starting background jobs that outlive monkeypatches.
Dedicated tests explicitly exercise worker submission. The real-data guard
keeps its original watched paths, including settings and embedding cache.

New deterministic tests are in `tests/test_autonomous_memory.py` and
`tests/test_file_access.py`; `tests/test_persistence.py` adds a genuinely fresh
process auto-save/retrieval test with no conversation history. Existing memory,
verification, reliability, network-gate, storage-failure and full-suite checks
must remain green. Final executed results and log paths follow below.

Final full-suite check of the reviewed implementation: **790 passed, 1 skipped**
in 128.47 seconds. The only skip was
`tests/test_keychain.py:33: needs a Mac's Keychain`. Windows symlink, junction,
hard-link, socket-blocked offline and offscreen memory-dialog checks executed.
This full run includes the final privacy-setting, pending-job invalidation,
legacy-repair and native-model memory-authorization safeguards.

Full-suite log:
`C:\Users\joshu\.codex\visualizations\2026\10\21\01a15c12-fb2b-7d00-9f67-101caecdd403\cursiv-check-08hw6lfo\pytest.log`.
The test snapshot has its own `src/` and empty test home. Source and real user
memory were never used as writable test data. A local snapshot runner used for
the checks is beside those test artifacts as `check_cursiv_memory.py`.

After that full run, the unsupported `delete_file` declaration was removed from
the native-model tool list (the backend already refused deletion), and a
regression assertion was added. The final filesystem/UI/help result is recorded
as **57 passed in 10.44 seconds**. Its log is
`C:\Users\joshu\.codex\visualizations\2026\10\21\01a15c12-fb2b-7d00-9f67-101caecdd403\cursiv-check-zzateuty\pytest.log`.
No other runtime changes followed the 790-pass full run.

`git diff --check`, AST parsing of changed Python files, and an explicit
17-file scope allowlist passed during review. Installer, updater, networking
implementations, website, README, release versions and conversation-storage
format have no changes. HEAD remains the original U79 commit; feature work is
uncommitted and unpushed on `codex/autonomous-memory-v1`.

### Limits and review priorities

* This is conservative v1 selection, not perfect semantic understanding. Unknown
  or ambiguous facts are skipped or remain labelled inferred. Sensitive-content
  filters are conservative heuristics, not a promise to detect every secret.
* Non-retention wording excludes that exchange. For continuing conversations,
  `memory learn off` is the persistent global control; no new permanent per-topic
  exclusion manager was introduced. This does not disable transcript autosave or
  remove existing memories/files; those existing controls are separate.
* Pending jobs are bounded in memory, not a durable queue. Closing Cursiv before
  evaluation finishes can discard a pending candidate; no success is reported.
  Confirmed fact/file writes survive restart. Model-call latency is optional and
  background; direct common statements need no model call.
  Forget/disable actions invalidate older queued or in-flight fact extraction;
  the main fact writer rechecks that generation while holding its mutation lock.
* Earlier releases ignore `superseded` metadata, so rollback can resurface older
  facts. The original snapshot and U79 source recovery copy are retained.
* Inspect read/repair locking, backup verification, correction topic matching,
  filesystem authorization and confirmation, and the UI integration carefully.
  Static path/reparse checks are not a full operating-system sandbox against a
  hostile process racing filesystem changes; do not broaden the workspace grant.
* No new dependency, mandatory cloud service or telemetry was added. Existing
  explicit phone-memory sharing remains a separate pre-existing capability.
* Real Ollama selection quality, a packaged installer, and interactive Qt/native
  cloud-tool flows require manual review; deterministic tests do not prove those.

---

Repo: `C:\Users\joshu\OneDrive\Documents\GitHub\Cursiv-v3`
Remote: `https://github.com/winklersllc2026-bit/Cursiv.git` (branch `main`)
This is the winklersllc checkout. Do not edit `Cursiv-v2`, Desktop `Cursiv-V3`, or `joshua1993winkler-jpg/Cursiv`.

Status: **committed and released** (eb8ddc1, v3.14-U59); every release since builds on it. Latest: v3.14-U70. Read this before changing chat, memory, phases, or tests.

## What the user asked for

A quick overhaul so Cursiv stops declaring an answer correct without checking. Five pieces, in this order:

1. A real verification pass after the draft exists.
2. An assumption / evidence ledger on complex turns, stored with the turn.
3. Memory origin tags, dates, safety precedence, and conflict surfacing.
4. A small benchmark suite in `tests/`.
5. Proportional triggering so casual chat stays fast.

## Where the draft actually comes from

`chat()` in `cursiv_engine/ui/chat_app.py` does **not** call `cascade_stream()`. The desktop window streams `_chat_inner` via `_chat_stream`, which collects the draft in the `reply` list while yielding tokens. `cascade_stream()` is the one-shot helper used by Babel, council, and other commands.

The verification pass runs in `chat()` **after** `_chat_stream` returns and after `speed.chat_finished()`, so the local model is free. The user already sees the streamed draft. The pass then appends either nothing, a revised answer, or notes.

Verifier calls go through `_router_llm`: the local model when one is ready, no idle wait. The user's free Groq/Gemini key is used only when there is no local model, and a local call that fails does not fall back to the cloud (C-008, 2026-10-17; `_quick_llm` for learning follows the same order). The check runs before `chat_finished()`, so background learning cannot take the local model in the middle of it. Paid keys and Cursiv Cloud are not used for the check.

Since 2026-10-17 (Lane 1, see `AUDIT-2026-10-17.md`), `run_pass` also receives:
- `context`: the last six messages and the memory block recalled for the question (`_check_context`). The checker, the rewrite and the ledger-fill call all see it (C-024).
- `sources`: text actually looked up this turn (web search, plugin context, local tool results), collected in `chat_app._RETRIEVED`.
- The draft is the model's text with Cursiv's status lines stripped (no `*[Answered by …]*`), so the footer no longer triggers the pass.

Two deterministic checks were added (C-025): `known_problems` (a Known item with a number nobody gave, or mostly words nobody used, is an inference or an assumption) and `citation_problems` (a named source such as the CDC, WHO or "the local government report" may only be cited when its text was looked up this turn, or the person brought it up).

## Files

| File | Role |
|---|---|
| `cursiv_engine/core/verify.py` | Triggers, ledger, deterministic checks, one revise, session ledgers |
| `cursiv_engine/ui/chat_app.py` | Prompt addendum at the end of prompt build; `chat()` runs `verify.run_pass` |
| `cursiv_engine/core/phases.py` | Grounding trace notes when a ledger is required |
| `cursiv_engine/memory/semantic.py` | `origin`, `date`, conflict surfacing, safety quarantine |
| `cursiv_engine/codex/system_prompt.md` | Hard rule in Section 2 (kept by the compact persona) |
| `launcher/memory_dialog.py` | “What I remember” shows the origin tag |
| `tests/test_verify.py` | Benchmarks. No network. |

`tests/test_core.py` and `tests/test_honesty.py` were not rewritten. They still pass.

## Behavior

### 1. Verification pass

`verify.run_pass(user_text, draft, ask)`:

- Deterministic checks always run when the pass is triggered: number/definition drift, assumed items stated as facts, missing ledger on a complex turn.
- Then one verifier call. The instruction is exactly: “List concrete problems only: unsupported claims, changed definitions, contradictions, assumptions presented as facts, answers to the wrong question. If none, say CLEAR.”
- A model reply of `CLEAR` does **not** erase a deterministic problem. That is the “declared itself correct” fix.
- If anything is wrong, **one** rewrite is requested, then the same checks run again.
- If the rewrite is clean, `chat()` yields `Revised after check:` plus the rewrite. Learning treats extracted facts as `verified`.
- If the rewrite is missing or still wrong, the original draft stays, and `chat()` yields `Draft + notes:` with the original problems. Learning is skipped for that turn so the bad draft is not stored as memory.
- If no model is available, deterministic problems are still surfaced. There is no fake `CLEAR`.

### 2. Ledger

Complex / high-stakes questions (`needs_ledger`) get this block appended (since U63 the persona no longer asks for it on every answer, and `verify.exact_format()` requests skip it and get `FORMAT_RULE` instead) to the system prompt, after the coding-brain swap so it is not dropped:

```
Known: ...
Inferred: ...
Assumed: ...
Unknown: ...
```

Known is only what the person stated. Inferred is a conclusion. Assumed is a gap the model filled. Those must not be stated as facts.

`extract_ledger` pulls the block off the draft or the rewrite and stores it in process (`verify._ledgers`). The next turn’s prompt includes `prior_ledger_block()`. The block is also part of the assistant text, so the chat window stores it in conversation history (`launcher/chat_panel.py` saves the full streamed reply).

If the only problem is a missing ledger, the pass tries one short “fill the ledger only” call before a full rewrite.

Emergency / crisis text does not get a ledger and is not verified.

### 3. Memory

Every new fact has:

- `origin`: `user_said` (manual / “remember”), `inferred` (learned, plugins), or `verified` (learned from a turn the pass cleared)
- `date`: `YYYY-MM-DD`
- `created`: unchanged `YYYY-MM-DD HH:MM`
- `source`: unchanged (`manual`, `learned`, `verified`, `plugin:…`)

Old rows with no `origin` are labeled from `source` by `origin_of()`. A duplicate save does not upgrade origin. Repeating a claim does not turn `user_said` into `verified`.

`build_context` (what the model actually reads):

- Prefixes the safety line: preferences and repeated claims never outrank safety and are not known facts.
- Tags each fact `[you said]`, `[inferred]`, or `[verified]`.
- If two recalled facts conflict (one negates the other, or they give different numbers on the same topic), both are included with an explicit conflict note. Retrieval does not drop one.
- A fact that tells Cursiv to ignore or override safety / the constitution is listed under “Not applied” and is not given as a usable memory.

The memory window (`launcher/memory_dialog.py`) and `what do you remember` use `fact_subtitle()`, which shows date, origin, and family.

### 4. Benchmarks

`python -m pytest tests/test_verify.py tests/test_core.py tests/test_honesty.py`

Ran with Python 3.13 on 2026-10-16: `tests/test_verify.py` and `tests/test_honesty.py` passed. `tests/test_core.py` has one failure that was already there and is not part of this change: `test_portable_mode_points_home_models_and_ollama_at_the_drive`. The test sets `CURSIV_REAL_HOME` to an empty string, and `launcher/portable.py` uses `setdefault`, so it stays empty. Do not “fix” that while working on verification.

`tests/test_verify.py` covers constraint drift, definition drift, assumption-vs-fact, self-correction that introduces a new number, memory conflict, safety precedence, origin not upgrading, seeded `CLEAR` that still loses to the deterministic check, proportional triggers, crisis skip, ledger stored for the next turn, and one `chat()` pass with `_chat_stream` and `_router_llm` faked. The memory window was not opened; `fact_subtitle()` is what it renders.

### 5. Proportional trigger

`should_verify` is true when any of these hold:

- The draft contains a digit, a recommendation (“I recommend”, “you should”, “I suggest”), or a technical claim (API, retry, server, dosage, and the other words in `_TECH`).
- The user asks “is this correct?” / for a review (`_REVIEW`).
- The user is stating a memory (`remember that`, `my name is`, `I prefer`, `from now on`, `I always want`).
- The previous pass failed (`verify._previous_failed`). The next turn is checked even if it looks casual. A clean pass clears the flag.

Casual chat (“hey how are you”) does not call the verifier.

Not every turn that background-learning might touch is verified. Learning still runs on those turns, and the facts stay `inferred`. A failed pass skips learning. Do not “fix” this by verifying every message; the user asked for casual chat to stay fast.

## What not to change

- Do not route verification through paid xAI / OpenAI / Claude or Cursiv Cloud.
- Do not buffer the whole answer before the first token. The check is after the draft.
- Do not auto-revise more than once.
- Do not let a `CLEAR` string override number drift, a changed definition, or an assumption stated as fact.
- Do not let a saved preference override `cursiv_engine/core/constitution.py` or the Section 2 safety paragraph.
- The 8 phase names stay as they are. The ledger is an extra note on the Grounding trace, not a 9th phase.

## Not done

- `cascade_stream()` callers (Babel, council, codex commands) are not wrapped. Only `chat()`.
- Conflict detection is lexical (shared content words + negation or different numbers). It will miss paraphrases embeddings would catch.
- No browser or Qt run of the memory window. `fact_subtitle()` is what the dialog renders; that function is tested.

## Network gate (Lane 2, 2026-10-17)

`cursiv_engine/core/netgate.py` is the one switch for connections off this computer (AUDIT C-009, C-010, C-011). Settings live in `.cursiv/config.json` next to the keys:

| Setting | Default | Command | What it does |
|---|---|---|---|
| `offline_mode` | off | `offline on/off` | Closes the gate. Persists across restarts. |
| `web_search_auto` | off | `websearch on/off` | Trigger words ("today", "right now", "this week") search the web. Off: only a message starting `search:` / `search ` does. |
| `update_check_auto` | off | `autoupdate on/off` | GitHub update check 10 s after login. The Check for Updates button always works (unless offline). |

All three are also checkboxes in Settings.

While the gate is closed:
- `allowed()` is False. `_needs_search`, `_web_search`, `_is_online`, `_post_json`, `cloud_enabled`, `_free_key_llm`, the free-key fallback, `cascade_stream`, the forced providers (`grok`/`claude`/`openai`/`council` answer locally with a note), `_pull_ollama_model`, the Setup and USB model pulls, the embedding-model pull and the update check all stop first.
- An audit hook (installed when netgate is imported, which `chat_app` does at import) raises `NetworkBlocked` (an OSError) on any non-loopback `socket.connect`, `sendto` or DNS lookup. That's the backstop for anything that forgot to ask. Ollama is on 127.0.0.1, so it keeps working. Saved keys are kept; they're just not used.

The Connectivity phase no longer probes 8.8.8.8 on every message. `_connectivity_probe` returns None ("not checked") when the gate is closed, or when the local model is ready and no cloud key or `web_search_auto` is set. A None isn't cached.

Proof: `tests/test_netgate.py` (records and refuses every outside connection with an audit hook) and `py -3.13 scripts/net_audit.py --offline` (a fresh copy of the source, an empty home, real `chat()` against the real local Ollama, logs every connection).

Not changed: Cursiv Cloud is still on by default for people with no local model (`_cloud_settings` writes `enabled: True`). With the gate open and Ollama running, a missing `nomic-embed-text` is still pulled automatically. That's Ollama's traffic, not Cursiv's process.

## Answer quality (2026-10-17, U61 draft)

- `core/reference.py`: chat looks up `reference_data/` for each message. A match puts the entry in the prompt (cite `[category/slug]`), and first-aid and survival entries are shown word for word in a status line, because a 1.5B model misquoted the numbers live. Three unreviewed entries (`NOT_IN_CHAT`) are only shown by `ref`.
- `phases.emergency_kind`: "medical" keeps the normal prompt plus first-aid instructions; "crisis" and "danger" keep the care-first crisis prompt.
- `chat()` skips the verify pass on any emergency turn (`_EMERGENCY_TURN`), and shows failed-check notes compactly (`_compact_notes`: at most three one-line items, under "Checked, with notes"). `verify.py` itself is unchanged.
- `chat(replace_draft=True)` (the chat window only): a clean revision replaces the draft on screen and in history (`REPLACE_SENTINEL`).

## Answer safety (2026-10-18, U63)

From a review of real answers (a bleeding answer said not to bandage or use a tourniquet) and the first-time-user findings.

- `reference_data/sources.json`: source, URL, check date and `reviewed` (all false) per entry; `reference.source()`; `note_line` shows "Based on ... (checked ...)". Bleeding, tourniquet, water, hypothermia rewritten from Stop the Bleed / EPA / CDC.
- `reference.ALIASES` entries may be tuples: all words needed (`("bleach", "gallon")`), so cleaning questions don't get the water card.
- `agents/reference_brain._bundled_search` (the online-AI tool) uses `reference.lookup`. Its old any-shared-word scoring was the cause of unrelated cards.
- `phases._MEDICAL` covers spurting / pouring blood, bleeding out, won't stop bleeding. Persona rule 3 separates crisis care from medical emergencies.
- `core/answer_check.py`: no model call, runs on every turn including emergencies, from `chat()` right after the draft. `contradictions()` (a negated `KEY_STEPS` step for a shown entry; "unless trained") and `unsupported_actions()` (claimed database/web search when `_WEB_SEARCHED` is false). Lines start "Cursiv's check:" and render amber.
- `chat_panel.split_details`: ledger lines and "Checked, with notes" go behind a "Show reasoning and checks" link (`cursiv://details/<text>`, opens a dialog). Medical and survival cards render at normal size.
- `verify.py` changed only by adding `exact_format` / `FORMAT_RULE`; the pass itself is unchanged.
- Benchmark: suites 1.1 (new cases, 4 defective checks fixed) and 1.2 (checks only: curly apostrophes, ledger "Unknown:" lines no longer count as admitting it can't know, negations before unsafe phrases). `truth_bench.py --model / --source <ref>`, `truth_rescore.py`, `compare_models.py`. Open failures: `bench/FAILURES-U63-pre.md` (rea-009 arithmetic, ref-015 dose merge, amb-002 assumed "it").
- Not done: the six Phase 1 prompts need to be re-run once the owner supplies them; a dose-number comparison against the card; the model comparison run.

- U76: `verify.constraint_problems(user_text, draft, sources)` takes the turn's sources; a number is
  drift only if it restates the question differently. Worked results ("So, 9 eggs"), numbers in Cursiv's
  sources, ranges, bracketed equivalents and repeated results are not. `arithmetic_problems` skips the tail of a
  longer chain and reads "7/8". Measure with `scripts/verify_replay.py <results.json>` (bench/FAILURES-U75.md).

## Releases

Build every installer with `py -3.13 scripts/build_release.py <tag>`: it checks that the version in `core/selfknow.py`, `launcher/cursiv_launcher.py` and `installer/cursiv_setup.iss` matches the tag, builds in a fresh git worktree of the tag, and copies the installer to `installer/Output/`. Don't build from the working tree (U59 was built from uncommitted code; U63's first build picked up edits made during the build). `tests/test_versions.py` keeps the three version strings equal; CI runs the tests on every push to main and every PR. A release needs a GitHub release with `Cursiv-Setup-<version>.exe` and `Cursiv-Setup-latest.exe`, not just a push. Before tagging, check CI is green on the commit (`gh run list --workflow tests.yml --limit 1`): U67–U71 were tagged while CI was red because the workflow's own package list lacked pypdf; it now installs from `requirements.txt`. Upload `SHA256SUMS-<version>.txt` as `SHA256SUMS.txt`.

## U64 (2026-10-18): speed, Standard / Deep Think, Phase A fixes

- Speed (`core/speed.py`): `gpu_options()` sets `num_gpu` (whole model if its file fits 90% of the card, else its share); `make_room()` unloads other models first; one retry with Ollama's own split if a load fails. Measured on a 4 GB RTX 2050 in the comments.
- Modes: `chat/status.py` `menu_choices()` / `choose()` / `current_choice()`; `answer_mode` "deep" uses `speed.DEEP_THINK_MODEL` with `think: true`; checks and background jobs pass `standard=True`. `chat_model` counts only while `show_all_models` is on.
- `core/calc.py` (clock and plain arithmetic into the prompt, checked after), `core/clarify.py` (vague first message), `reference_data/doses.json` + `answer_check.dose_problems()`.
- Memory: learned facts always "inferred"; `semantic.learnable()`; `repair_learned()` runs once (settings key `learned_repair_2026_10_18`), moving non-facts to `memory_facts.removed.jsonl`.
- verify: C-001/002/004/005/006 closed; `_ledger_span()` reads emoji headings and items on following lines; numbers with thousands separators.
- Field copy: `portable.FIELD_MARKER`, `apply_field_defaults()`; `usb_maker` "Field copy" box.
- Evidence: `bench/phase1/` (original + replays), `scripts/phase1_replay.py`, `scripts/compare_models.py --source`, `tests/test_persistence.py`.
- Open: model comparison result decides Standard / Deep Think defaults; coop advice has no reference entry; CPU-only speed unmeasured; field notes export doesn't exist.

## U65 (2026-10-18): knowledge packs, model choice, demo evidence

- Knowledge packs: `reference_data/packs/*.json` (entries with aliases, source name/url/licence/checked, `reviewed`, optional `doses`). `reference.packs()`, `pack_problems()` (licence must be in `PACK_LICENSES`), a pack entry replaces a legacy entry with the same title. `docs/REFERENCE.md` is generated by `scripts/reference_report.py` and tested. Alias phrases don't match inside hyphenated words. Adding entries: write from a public-domain page, add everyday and look-alike questions to `tests/test_packs.py`, run the report script.
- Unsourced on purpose: CPR technique, choking, fractures, shock, severe allergic reaction (federal pages point to copyrighted Red Cross / AHA guidance), wound care (only a 2005 CDC pamphlet found).
- Model: `speed.chat_model_prefs()` is the same on every card (qwen3:4b-instruct first); `DEEP_THINK_OFFERED = False` (`CURSIV_DEEP_THINK=1` for the benchmark). Evidence: `bench/MODEL-COMPARISON.md`.
- `chat()`: a vague first message gets `clarify.question()` without the model (`_CURSIV_REPLY` skips the check). `verify.parse_verdict` treats all-"X: none" replies as clear; `citation_problems` skips "I don't have a ..." sentences.
- Website screenshots: `scripts/site_shots.py ask|draw|windows` (real answers saved in `website/assets/shots/answers.json`).

## Field science (after U65): research roadmap R1, R2, R5

Roadmap: `docs/RESEARCH-ROADMAP.md`.
- R1 `core/fieldlog.py` (append-only JSONL with fsync, SHA-256 chain `prev`/`hash`, `correct()` adds an entry, `verify()`, `export()` CSV/JSON/GeoJSON, `parse()`/`command()` for `log ...`); window `launcher/field_notebook.py`, first sidebar button. The AI never writes the log.
- R2 `core/fieldcalc.py` (units, DMS/decimal, `to_utm` Snyder series tested against a Kruger series, dilution, stats with a t table); `calc.work_out` falls through to it; `calc.Worked.value/tol` checks with rounding allowed. Field cases are in the benchmark (suites 1.3 and 1.4).
- R5 `core/atomic.write_text` (temp file, fsync, os.replace) for settings, keys, memories, conversations; battery saver in `speed.battery_saver()` / `keep_alive()` / `num_ctx()`, skips the model check in `chat()`; `scripts/hardware_check.py` writes docs/HARDWARE.md.

## U66–U70 (2026-10-18): field teams, safer answers, ready for a research group

- U66 field notebook and calculations (above). R4 sample IDs (`fieldlog.new_sample_id`, `sample_history`, `labels_html`).
- R3 `core/documents.py`: imported PDFs/text kept offline, BM25 with a coverage threshold, answers quote pages,
  `cited_pages_problems`, documents-only mode (never in an emergency); `ASKS_ABOUT_DOCS` + `nothing_found_*` when a
  question about "our protocol" matches nothing.
- R6 `core/fieldsync.py`: share/import field logs by USB or shared folder; each laptop's chain kept separately in
  `fieldlog/team/`; changed or cut-off copies refused; differing histories kept side by side, never resolved; sample-ID
  clashes reported; `team log`, `team log export`. Only the field log moves.
- `fieldcalc`: Vincenty distance/bearing, `bleach_dose` from `doses.json` (the model said 16 drops/L three runs out of
  three); `calc`: 24-hour times. `answer_check`: cloudy-water doses must be the card's or double, doses read across
  sentences, `flip_flop` / `lead_warning` (a "Yes, it's safe … don't go" answer gets a warning above it via
  `replace_draft`), a model citing the offline reference when none was given.
- Benchmark suite 1.4 (153 cases): U66 145, U67 147, U68 149. `bench/FAILURES-suite1.4.md`. Known scoring defects
  for a 1.5: num-027 ("20 + 1" in correct working), adv-016 ("eight" in words).
- U69: dark mode by default (`theme.saved_mode()` unset = dark; "system" = match Windows).
- U70 (MRS feedback): `status.network_status()` labels (`LOCAL ONLY · internet blocked` only when offline), model named
  in the menu, `chat_app.sources_line()` on every answer from Cursiv's own records (`_REF_SHOWN`, `_DOCS_SHOWN`,
  `_WORKED`, `_WEB_SEARCHED`, `_MEMORY_RECALLED`), `fieldlog.report_html` / `field report`, `core/demo.py` (sample data in
  `~/.cursiv/demo/`; `fieldlog.log_dir()` and `documents.lib_dir()` switch while it's on), `PRIVACY.md`,
  `docs/FIELD-DEMO.md`, installer version info + `installer/BEFORE-INSTALL.txt`, `build_release.py` writes
  `SHA256SUMS-<version>.txt` (upload it to the release as `SHA256SUMS.txt`).
- Open: code signing (owner's decision, costs money); professional review of first-aid entries (43 of 80 medical and
  survival entries unsourced); SSD field-kit test (`docs/FIELD-KIT-TEST.md`); team sync not yet tried by a real team;
  the model still opens "Yes, it's safe" on the lightning case; weekday arithmetic; small-sample comparisons.

## macOS (early, after U71)

- Apple Silicon only, unsigned (owner's decision, 2026-10-18; an Apple Developer account would allow signing and
  notarization). No Mac in hand: everything is checked on GitHub's macOS runners.
- `core/ollama_host.py`: finds/starts/restarts/installs Ollama on Windows and macOS (Ollama-darwin.zip into
  ~/Applications with `ditto`, no admin). `core/paths.py`: program data in ~/Library/Application Support/Cursiv inside
  the Mac app (a Mac app is replaced whole on update); unchanged elsewhere. Keys in the login Keychain
  (`keystore` "keychain:<id>", secret passed on stdin). Battery from `pmset`. USB maker is Windows-only.
- `.github/workflows/tests.yml` runs on Windows and macOS. `.github/workflows/mac-build.yml` builds Cursiv.app on a
  published release (or by hand): tests, `Cursiv --selftest`, `scripts/mac_shots.py` screenshots, an unsigned .dmg
  plus `Cursiv-mac-latest.dmg` and `SHA256SUMS-mac.txt`, attached to the release. Check that run after publishing.
- Not verified by a person: the first-open Gatekeeper flow, Ollama install on a real Mac, Keychain prompts, the
  frameless window's feel on macOS, voice input.


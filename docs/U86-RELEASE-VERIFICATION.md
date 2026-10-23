# U86 release verification

**Published and publicly verified.** GitHub latest is
[v3.14-U86](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U86),
published 2026-10-23 02:49:16 UTC (October 22, 10:49 pm Eastern).

The owner authorized commit, push, version bump, installers, release publication
and website updates. Before publication, GitHub latest was verified as U85;
remote main was `b2321f0f4a1e3ec120d9703cf0747bd0bf9b917d`. This release keeps
the existing U85 tag and assets immutable and uses the dedicated feature branch
`codex/u85-live-test-followup`.

## Scope

Combine [native trust boundaries](NATIVE-TRUST-BOUNDARIES.md),
[notebook/live-test fixes](LIVE-TEST-FOLLOWUP.md) and
[conversation follow-up](CONVERSATION-FOLLOWUP.md). Application, launcher and
Inno Setup versions/output names agree on `3.14-U86`. Personal `test_internals/`
stays excluded. No private settings, memory data, encryption migration or owner
installation is changed. Builds must use the new immutable tag.

## Final versioned source checks

Full isolated Windows suite: **1,492 passed, 1 skipped in 182.21 s**.
Snapshot, manifest and log: `%TEMP%/cursiv-live-followup-rlvht_im`. The skip
requires a real Mac Keychain. Every application/launcher Python file matches the
passing snapshot after newline normalization; no module exceeds the existing
1,200-line limit. Application fingerprint:
`64668a508c8d8e95b820e49d53898f34c6808585a9bb1cd94320df25c11737b6`.

The personal test-file SHA-256 remains
`7e4671321c6521629865ece7160a74e9e38ad357aec835f3fabad95b4ae749ed`
and its directory is excluded from commits/packages. Package, hosted CI and
publication checks are recorded after execution; pending is not a pass. The old U85 benchmark remains historical; current controlled regressions
do not establish general model accuracy.

## Retained limits

Windows remains unsigned; Apple Silicon Mac remains unsigned/unnotarized.
The owner deferred signing until next month. Basic physical USB operation is
owner-reported working, but memory persistence/restart/second-PC retrieval are
unverified. Conversation history is separate from per-turn memory restrictions.
Existing local conversations/memories/backups remain plaintext. Small-model
errors, unrecognized wording and missed deterministic contradictions remain
possible; this release makes no medical or general-safety certification claim.

## Local-model smoke evidence

The final-source nine-turn replay is [retained unscored](../bench/results/U86-conversation-smoke-20261022.json).
Its application fingerprint is recorded in the artifact. Saved-memory context
was empty for every turn; two replies were native. Model verbosity, unrecognized
closing questions and philosophical memory-denial claims remain failures,
explicitly documented in [the conversation report](CONVERSATION-FOLLOWUP.md).
No new 158-case score or model-quality pass is inferred from regressions.

## Tagged source and publication jobs

`v3.14-U86` resolves to `31e99873c88dbf05719466ec683fd657106a2966`.
The tag fingerprint matches the final passing source snapshot and real-model
replay. Main and the feature branch were pushed atomically with the new tag;
no published tag was moved and no remote force-push was used. Local main was
fast-forwarded to this source. The actual updater comparison functions offer
U86 to U79/U81/U82/U83/U84/U85 and reject same-version U86.

- Hosted source checks: [39890646566](https://github.com/Cursiv-Local/Cursiv/actions/runs/39890646566).
- Tagged Mac package: [39890675880](https://github.com/Cursiv-Local/Cursiv/actions/runs/39890675880).
- Windows build: `%TEMP%/cursiv-u86-clean-build.log`.
- Frozen Windows report: `%TEMP%/cursiv_release_w8gh6cfg/frozen-selftest.txt`.

The Windows frozen report says `ALL PASSED`, including full launcher/chat/tray,
notebook persistence/chain/signed export, documents, calculations and imports.
The owner application was not installed or restarted. Hosted final outcomes,
installer hashes and public checks follow after completion.

## Website gate and existing availability

All **20 website tests passed**, including analytics counting/cache/rate limits,
admin authentication and separate current-regression/historical-model evidence.
The allowlisted build completed with 14 pages plus assets/notebook/privacy; the
four edited marketing pages match generated HTML and JSON-LD parses. Local
Markdown links, Python syntax, module-size budget and diff whitespace checks pass.

Before deployment, HTTPS health and marketing routes return 200. Both private
statistics routes return 401/no-store anonymously. The pre-existing public
download counter still returns 503, `available:false`, `total:null`. It is not
reported as zero downloads and does not prevent installer navigation. No DNS,
Worker code, secrets or database migration is required for this copy update.

## Exact combined change inventory

The immutable application commit includes these intended files, relative to
the prior published/evidence baseline `b2321f0`. The personal fixture and local
logs/build outputs are excluded. Later publication-evidence updates affect
documentation only; the application tag remains unchanged.

- `ARCHITECTURE.md`
- `CHANGELOG.md`
- `HANDOFF.md`
- `README.md`
- `bench/results/U86-conversation-smoke-20261022.json`
- `cloudflare/tests/release-evidence.test.mjs`
- `cursiv_engine/chat/completion.py`
- `cursiv_engine/chat/context.py`
- `cursiv_engine/chat/conversation.py`
- `cursiv_engine/chat/response_style.py`
- `cursiv_engine/chat/review.py`
- `cursiv_engine/core/action_gate.py`
- `cursiv_engine/core/calc.py`
- `cursiv_engine/core/conversation_kind.py`
- `cursiv_engine/core/demo.py`
- `cursiv_engine/core/deterministic_overrides.py`
- `cursiv_engine/core/feature_answers.py`
- `cursiv_engine/core/feedback.py`
- `cursiv_engine/core/fieldlog.py`
- `cursiv_engine/core/fieldmath.py`
- `cursiv_engine/core/file_access.py`
- `cursiv_engine/core/native_answers.py`
- `cursiv_engine/core/notebook_tools.py`
- `cursiv_engine/core/presence.py`
- `cursiv_engine/core/resources.py`
- `cursiv_engine/core/review_policy.py`
- `cursiv_engine/core/selfknow.py`
- `cursiv_engine/core/turn_policy.py`
- `cursiv_engine/core/verify.py`
- `cursiv_engine/memory/intents.py`
- `docs/CLAIM-EVIDENCE.md`
- `docs/CONVERSATION-FOLLOWUP.md`
- `docs/FIELD-KIT-TEST.md`
- `docs/LIVE-TEST-FOLLOWUP.md`
- `docs/NATIVE-TRUST-BOUNDARIES.md`
- `docs/PLATFORM-READINESS.md`
- `docs/RELEASE-U86.md`
- `docs/U86-RELEASE-VERIFICATION.md`
- `docs/USB-PERSISTENCE-CHECK.md`
- `installer/cursiv_setup.iss`
- `launcher/chat_commands.py`
- `launcher/chat_feedback.py`
- `launcher/chat_panel.py`
- `launcher/chat_transcript.py`
- `launcher/commands_system.py`
- `launcher/cursiv_launcher.py`
- `tests/test_answer_check.py`
- `tests/test_chat_feedback.py`
- `tests/test_conversation_followup.py`
- `tests/test_fieldlog.py`
- `tests/test_grounded_chat.py`
- `tests/test_live_test_followup.py`
- `tests/test_native_boundaries.py`
- `tests/test_notebook_workflows.py`
- `tests/test_phase_a.py`
- `tests/test_storage_failures.py`
- `tests/test_verify.py`
- `website/ai-reliability-testing.html`
- `website/index.html`
- `website/start.html`
- `website/vision.html`

## Completed package and hosted checks

Hosted source CI 39890646566 succeeded at the tagged application commit:
Windows **1,492 passed, 1 skipped in 150.07 s**; macOS **1,482 passed,
11 skipped in 396.43 s**. The tagged Mac package job also succeeded, with
**1,482 passed, 11 skipped in 368.30 s**, followed by the frozen full-window
self-test (`ALL PASSED`), main/Tools/Settings/Notebook captures and DMG build.
All four downloaded captures were inspected. These are hosted checks, not an
independent owner installation on a clean Mac.

The Windows clean build used Python 3.13.13, PyInstaller 6.22.3 and the existing
clean dependency environment (37 exact versions in `U86-build-dependencies.txt`).
Inno Setup compile: 79.391 s. Embedded installer file/product versions agree on
`3.14-U86`. Authenticode reports **NotSigned**. Both Windows installer names
are identical, **53,505,869 bytes**, SHA-256:
`93e5a510c9dc4c1afacca4acef87244e5be97ad1c0137e261398911f8faa3094`.
Both names are listed in `SHA256SUMS.txt` and uploaded to the draft.

Both Mac asset names are **68,615,264 bytes**, SHA-256:
`28860ae6eb8146f8944437cc2d985a4394da8699e866fb2e8f0d51a34423a686`.
The downloaded workflow DMG matches `SHA256SUMS-mac.txt` and both draft assets
GitHub digests. Mac is unsigned/unnotarized. Windows/Mac share the immutable
source tag; published U85 assets remain untouched.

GitHub draft lookup by REST tag returned 404 before publication; the authenticated
release lookup resolved draft ID 421395410 with `tagName:v3.14-U86`, all seven
expected assets and matching digests. No missing asset was assumed present.
Anonymous publication/deployment checks follow below only after execution.

## Publication and public verification

Evidence/website commit `6d79750` followed the immutable application tag with
documentation/copy changes only. Both main and the feature branch are pushed.
The existing Cloudflare `cursiv-web` Worker was deployed with Wrangler 4.152.0:
version `d7ed4d08-6450-4912-99ac-047db6ab9554`. Five static assets were uploaded
(the four edited marketing pages and the existing committed `/app` asset).
Worker source, domains, D1/AI bindings, variables, secrets and schema are preserved.
The publisher uses unpinned npx; this run installed Wrangler 4.152.0, rather
than the 4.151.3 used previously. No application dependency was changed by that.

All **29 anonymous public release/site checks passed** at 2026-10-23T02:54:42.758335+00:00:

- GitHub latest is stable U86 and its tag resolves to the tested application commit.
- Both stable installers were downloaded in full without credentials. Received
  sizes/hashes match the versioned aliases, public checksums and asset digests.
- Eight marketing/policy pages return HTTPS 200 with correct canonical URLs,
  indexability and parsed JSON-LD. Four pages serve the current generated U86 copy.
- Homepage Open Graph/Twitter URLs are absolute and unique; the dedicated
  1200×630 PNG is public. Phone app/notebook, health, robots and sitemap work.
- Both private statistics routes return 401 and no-store anonymously.
- The legacy hostname gives a 301 to the matching new-domain evidence path.

The initial strict byte-comparison harness flagged four HTML mismatches: the
edge inserts a Cloudflare Insights beacon. The exact same insertion was verified
in the saved pre-deployment baseline. The corrected comparison removes only that
known insertion and normalizes line endings, then compares all remaining HTML.
No other difference is ignored and no tracking was added by the source changes.
The first default-agent legacy request also failed its assertion; the explicit
release-verification agent/no-cache request verified the 301 destination. Initial
and corrected raw outcomes are retained under `cloudflare/.wrangler/u86-release-review/`.

The existing download-counter 503/unavailable with `total:null` persists. It is
reported separately from the 29 passing release checks, never as zero downloads.
The pre-existing edge analytics setting and unavailable counter remain owner
review items; this release did not change analytics settings or database state.

Publishing triggered redundant Mac run 39891655805. Normal cancellation completed
during its tests; build/DMG/release-upload steps were skipped. A later force-cancel
request raced that completion and returned 409 (already completed). The successful
tagged job is separate. All four published binary digests remained unchanged.

The release includes `u86-release-verification.json` with these recorded outcomes.
The owner app was not installed/restarted. Online update checks can now offer U86;
physical USB persistence and independent clean-machine checks remain unverified.

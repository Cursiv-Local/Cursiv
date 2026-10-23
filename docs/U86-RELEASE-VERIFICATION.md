# U86 release verification

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
- `cursiv_v215/chat/completion.py`
- `cursiv_v215/chat/context.py`
- `cursiv_v215/chat/conversation.py`
- `cursiv_v215/chat/response_style.py`
- `cursiv_v215/chat/review.py`
- `cursiv_v215/core/action_gate.py`
- `cursiv_v215/core/calc.py`
- `cursiv_v215/core/conversation_kind.py`
- `cursiv_v215/core/demo.py`
- `cursiv_v215/core/deterministic_overrides.py`
- `cursiv_v215/core/feature_answers.py`
- `cursiv_v215/core/feedback.py`
- `cursiv_v215/core/fieldlog.py`
- `cursiv_v215/core/fieldmath.py`
- `cursiv_v215/core/file_access.py`
- `cursiv_v215/core/native_answers.py`
- `cursiv_v215/core/notebook_tools.py`
- `cursiv_v215/core/presence.py`
- `cursiv_v215/core/resources.py`
- `cursiv_v215/core/review_policy.py`
- `cursiv_v215/core/selfknow.py`
- `cursiv_v215/core/turn_policy.py`
- `cursiv_v215/core/verify.py`
- `cursiv_v215/memory/intents.py`
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

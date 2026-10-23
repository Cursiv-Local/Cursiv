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

# U85 release verification

**Preparation in progress. Not yet published.** The owner authorized commit,
push, installer version bump, release publication and website deployment.
GitHub latest was confirmed as U84; main and the feature branch both pointed
to `d3922a48f74518997ccaea0390a771aed6f03513` before this follow-up.

## Scope and source

Carry the completed [quiet feedback/notebook changes](CHAT-FEEDBACK.md), bump
application, launcher and Inno Setup/output names together to `3.14-U85`.
Preserve personal `test_internals/`, existing records, private settings, published
tags and historical benchmark artifacts. No owner app installation or data/schema
migration is part of publication. Build installers only from an immutable tag.

The pre-bump source checkpoint passed **1,267 tests with one Mac-only skip**
in 154.66 s. This is not a claim that the versioned package or hosted CI passed.
Fresh versioned tests, exact tag/commit, Windows/Mac artifacts/hashes, hosted
CI, unchanged-suite model results and production website checks are recorded
below only when completed. No pending or unavailable result is treated as zero
downloads, a passed check or a live deployment.

## Final versioned source checks

Full isolated Windows suite: **1,267 passed, 1 skipped in 174.29 s**.
Snapshot/manifest/log: `%TEMP%/cursiv-maintenance-04f7ytj7`.
The skip requires a real Mac Keychain. All application/launcher Python files
match the passing versioned snapshot. Application, launcher and installer/output
names agree on `3.14-U85`. Normalized Python source fingerprint (the benchmark
runner's path-and-content method):
`b26a43519a6170ad3b1c5d98a27703122ef2cabf1cfc28c4915c69784556f1e2`.

The actual updater comparison functions offer U85 to U79/U81/U82/U83/U84 and
reject same-version U85. The full suite includes offline-network enforcement;
no installed owner's application or personal settings were changed. The personal
`test_internals/u81_test.txt` hash matches its original value. Tagged package,
hosted CI, live-model and public-download results are still pending here.

## Retained limitations

Unsigned installers; Mac is not notarized. Automated checks do not establish
clean-machine installation, physical portable-drive/phone behavior, professional
safety validation or independent field use. Model checks are finite and may
miss factual/safety errors. Existing cancellation is cooperative during a backend
read. Conversation history is separate from memory restrictions. Existing local
conversation/memory copies remain unencrypted; no encryption migration is included.

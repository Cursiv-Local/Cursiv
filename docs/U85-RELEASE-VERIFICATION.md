# U85 release verification

**Release gates complete; public checks pending.** The owner authorized commit,
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
`test_internals/u81_test.txt` hash matches its original value. Completed package, hosted CI and live-model results follow below; public checks
are recorded after publication.

## Tagged source and running jobs

`v3.14-U85` resolves to `9770c2ebc5a65baaa1e35933d3e574cfa6db7178`.
The tag and commit were pushed together to main and
`codex/maintainability-hardening`; no force-push or retag was used.
The release is a draft until the remaining gates complete.

- Hosted source CI: [39874348318](https://github.com/Cursiv-Local/Cursiv/actions/runs/39874348318).
- Tagged Mac package: [39874465964](https://github.com/Cursiv-Local/Cursiv/actions/runs/39874465964).
- Windows clean build log: `%TEMP%/cursiv-u85-clean-build.log`.
- Full tagged suite 1.5 log: `%TEMP%/cursiv-u85-truth-bench.log`, installed
  `qwen3:4b-instruct`, isolated empty data, offline mode and learning disabled.

Windows packaging and the model benchmark run concurrently on this computer;
benchmark wall times include that activity. Pending jobs do not establish a pass.

## Hosted Windows test-harness correction

The first Windows CI job at the tagged commit finished **1,266 passed, 1 failed,
1 skipped** in 109.90 s. `test_dated_recall_survives_a_fresh_python_process`
explicitly decoded UTF-8 while the child inherited a Windows cp1252 pipe. The
new recall separator was byte 0xB7, causing a reader-thread UnicodeDecodeError
and absent captured output. This was an encoding mismatch in the regression
harness, not a missing saved memory or changed application backend.

The test now deliberately inherits cp1252 and explicitly configures UTF-8 for
the child it decodes as UTF-8. Its actual record-ID/content/restart assertions
remain. Focused isolated checks: **62 passed in 8.89 s**,
`%TEMP%/cursiv-maintenance-svzk_em6`. This test/documentation-only correction
is committed after the immutable tag. Application/launcher source and package
inputs are unchanged; the tag is not moved. The corrected hosted CI is recorded separately below.

The corrected source CI [39875079798](https://github.com/Cursiv-Local/Cursiv/actions/runs/39875079798)
at `ddce0f7d7a0f137deed49956f7f7356c1f5217a7` completed successfully:

- Windows: **1,267 passed, 1 skipped, 118.64 s**.
- macOS: **1,257 passed, 11 skipped, 387.26 s**.

Both hosted jobs use Python 3.13.16. Application/launcher source is byte-equivalent
after newline normalization to the immutable tagged/package source; only the
UTF-8 regression contract and verification documentation differ in this commit.
The original failed Windows CI record is retained above rather than hidden.

## Windows artifact

The clean tagged build passed its frozen full-launcher/titlebar/tray/chat
self-test, notebook persistence/chain/signed-export checks and required imports.
Report: `%TEMP%/cursiv_release_dykweq_z/frozen-selftest.txt` (`ALL PASSED`).
Python 3.13.13, PyInstaller 6.22.3, PyQt6 6.11.0 / Qt 6.11.2; the existing
clean dependency environment was reused, with 36 exact package versions saved
as release asset `U85-build-dependencies.txt`. Inno Setup compile: 95.953 s.

Both installer names are identical, **53,455,197 bytes**:
`Cursiv-Setup-3.14-U85.exe` and `Cursiv-Setup-latest.exe`.
SHA-256:
`3ba7af935d4faae5e8662e651418a62ad89f2605d05fc9a21b29331335943c22`.
`SHA256SUMS.txt` lists both. Embedded file/product version is `3.14-U85`
(numeric 3.14.85.0). Authenticode: **NotSigned**. The verified bytes, checksums
and dependency list were uploaded to the U85 draft; this is not yet a public
download verification.

As with the prior release, the builder reported the legacy optional `httpx`
hidden import missing (the clean SDK uses `httpx2`), plus optional `tzdata`.
Required imports and the frozen gate passed; no dependency was added simply
to silence optional collection warnings.

## Mac artifact

Tagged package workflow [39874465964](https://github.com/Cursiv-Local/Cursiv/actions/runs/39874465964)
completed **successfully**. Its source suite passed **1,257 tests, 11 skipped
in 377.26 s**, followed by the PyInstaller app, frozen full-window self-test
(`ALL PASSED`), all four window captures, DMG construction and draft uploads.
Windows/macOS skip differences reflect platform-specific checks; this is not
an independent owner's clean-machine installation.

Both Mac names have **67,676,723 bytes**:
`Cursiv-3.14-U85-mac-arm64.dmg` and `Cursiv-mac-latest.dmg`.
SHA-256:
`b97cb76e1fcb58bfb7390367fbbd9451119a3be4701b483ef48dd9ad9a477325`.
The authenticated draft download was independently hashed against
`SHA256SUMS-mac.txt` and GitHub's asset digests; both aliases agree. The downloaded
workflow evidence includes its self-test and main/Tools/Settings/Notebook
screenshots, which were inspected. Package is unsigned/unnotarized.

## Production baseline before deployment

The existing site returns health 200. Both private admin endpoints return 401
without credentials and `no-store`. The pre-existing public download counter
still returns 503, `available:false`, `total:null`, `status:unavailable`. This
is not reported as zero downloads. No new schema migration, DNS or secret change
is part of this release; final website responses are checked after deployment.

## Retained limitations

Unsigned installers; Mac is not notarized. Automated checks do not establish
clean-machine installation, physical portable-drive/phone behavior, professional
safety validation or independent field use. Model checks are finite and may
miss factual/safety errors. Existing cancellation is cooperative during a backend
read. Conversation history is separate from memory restrictions. Existing local
conversation/memory copies remain unencrypted; no encryption migration is included.

## Fresh full model run

Exact tagged suite 1.5, 158 unique cases in nine categories, no runner errors:
**153 passed, 5 failed (96.8% overall)**. Answerable accuracy: 98.1%;
case-marked unsupported claims: 0.6%; unknown handling: 95%; safety patterns:
100%. Average 77 words, 13.3 s/case, 35.0 minutes. Application fingerprint
matches the tagged packages. Case/scoring hashes in the raw artifact match the
unchanged suite. [Raw answers](../bench/results/U85-qwen3_4b-instruct-suite1.5.json)
and [failure review](../bench/FAILURES-U85.md) are retained without rescoring.

This is below U84's 156/158 on the same suite. All five scoring failures and
selected passing safety/memory/calculation cases were inspected. A passing
allergy-memory answer starts with unsafe advice despite its seeded synthetic
allergy fact; bounded allergy-word detection missed that error. Several memory
cases took 64–71 seconds; the run does not isolate the cause. No complete memory
reliability, safety certification or causal score/performance gain is claimed.
These gaps remain open for focused investigation and a versioned scorer revision.

## Website release gate

All **20 website tests passed** (18 analytics/security/cache/counting, two current
release/identity/evidence checks). The allowlisted production build completed
with 14 pages plus assets/notebook/privacy. The four changed HTML files match
the generated output; their JSON-LD parses, canonical/social metadata remain
consistent, and local documentation links resolve. Existing signing warnings,
SignPath note, download URLs, phone routes and privacy text are retained.
No Worker code, DNS, secrets or database schema changes are needed for U85.

Only website copy, documentation and the new unedited benchmark output/summary
are being added after the test-only CI correction. The tagged application
fingerprint still matches both package inputs. Personal test-file hash is
unchanged and the directory stays excluded. `git diff --check` passed.

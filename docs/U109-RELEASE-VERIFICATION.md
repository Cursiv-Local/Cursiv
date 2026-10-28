# U109 release verification — October 28, 2026

[U109 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U109).
All11 release assets were downloaded anonymously and matched staged bytes and GitHub
REST digests; all8 platform owner signatures verified independently against the existing
pinned identity. Website deployment is established separately by the
[publication receipt](../bench/results/U109-publication.json). A missing receipt means
production deployment has not yet been verified.

## Immutable source and protected gates

- Source PR57: https://github.com/Cursiv-Local/Cursiv/pull/57. Reviewed head
  `53b878be9c3aa759c3c69bcc6905c6359f658df3`; the merged file tree exactly matched it.
- Immutable tag `v3.14-U109`: `bdf2737446f77a81e14a19f774c99c12a4bb3bcf`.
- Exact-main CI40773195207 passed all8 jobs:
  https://github.com/Cursiv-Local/Cursiv/actions/runs/40773195207.
- Normal protected merge, administrator enforcement and existing hooks remained enabled.
  The source commit's USB hook passed45 cases in81.00s. Guarded tag preparation reran
  the mandatory63 workspace checks in2.90s. No tag replacement or gate bypass was used.

Full isolated Windows suite: **2,584 passed, 15 skipped, 19 subtests passed**.
The digest-checked downloaded JUnit records contain zero failures/errors. Regular
counts use actual testcase elements; the additional19 subtests are counted separately.

| Exact-main source suite | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows | 2,584 | 15 | 19 |
| Mac | 2,567 | 32 | 19 |
| Linux | 2,566 | 33 | 19 |
| Hosted ARM64 engine/station checks | 114 | 0 | 0 |

[Windows XML](../bench/results/U109-main-windows.xml),
[Mac XML](../bench/results/U109-main-mac.xml),
[Linux XML](../bench/results/U109-main-linux.xml),
[ARM64 XML](../bench/results/U109-main-arm64.xml),
[machine summary](../bench/results/U109-main-ci-summary.json).
Skips retain optional live-model/platform/archive requirements. Hosted ARM64 checks
are not physical Raspberry Pi validation; station code was unchanged.

Initial Mac workspace jobs on the source push/PR failed to acquire a hosted runner,
with zero steps or tests. The unchanged PR retry passed on attempt2; the push retry
passed on attempt3. Both complete Mac source suites had already passed. The failed
infrastructure attempts remain in Actions history; they were not relabelled as passes.
All exact-main jobs passed on their first attempt.

## Behavior, real-model evidence and limits

[U109-VALIDATION](U109-VALIDATION.md) retains baseline failures, measurements and
remaining limitations. U109 separates installed source from authorized workspaces,
imported documents, external Field Copy data and runtime state. Source evidence uses
fresh fingerprints, parsed declarations, conditional cross-file calls, registered
callbacks, coverage and explicit unknown/denied/not-found states. Startup comes from
the actual build entry list and module guard. No inspected code is executed or edited.

Reviewed critical explanations are conditional on current AST witnesses, including
memory storage, portable copy, notebook correction/integrity, document scoring,
response-check limits, local timeout/retry behavior and bounded regex tests. These
maintained rules are not a general Python theorem prover. Audit output stays a
hypothesis with a source location, trigger, reproduction and regression plan.

Installed qwen3:4b-instruct supplied actual local-model responses, temperature0/seed42/
context8192, with outside requests/model switches/downloads blocked.15 development
probes used five real Qwen requests and ten native/scoped outcomes. Codex source review
graded11 as meeting their bounded goal and4 as partial; this is not an independent
human study or general model-accuracy result. First held-out inspection routing was4/5;
the missed regex wording was repaired and later5/5 runs are explicitly seen regressions.
No incorrect mathematical regex result is claimed reproduced in the live baseline.

Greeting preparation measured0.0195ms before/0.0046ms after with zero index loads;
other source routes include real increases and previously unhandled requests. The
validation table reports those costs without claiming a universal speed improvement.
Pre-version Windows2584/15/19 passed in448.75s, focused source128 passed, and versioned
source/release152 passed. Early failed receipts and imprecise model answers are retained.

## Tagged native packages and owner authentication

Windows was built from a clean temporary checkout of the immutable tag using the
existing locked environment. Installed and portable frozen checks passed before Inno
Setup staged identical versioned/latest installers. The build and both self-test
stores were isolated from actual user data. [Installed report](../bench/results/U109-windows-frozen-selftest.txt),
[portable report](../bench/results/U109-windows-portable-selftest.txt).

[Tagged Apple Silicon build40774780284](https://github.com/Cursiv-Local/Cursiv/actions/runs/40774780284)
passed its source tests and native frozen app self-test, then produced the DMG.
[Mac frozen report](../bench/results/U109-mac-frozen-selftest.txt).
Both native bundles exercise versioned source, existing critical rules and U109
startup/all ten feature areas/regex reads without a model or private notebook reads.
Frozen tests also cover plugin isolation, notebook chain/export/signature, document
retrieval, calculations and window construction. Mac CI does not claim live Ollama
inference. The earlier Windows pre-tag package is separately labelled as preflight.

All8 platform assets passed exact alias equality, checksum coverage and exact-tag
source provenance. Native lock hashes match only the Git lock bytes or their complete
LF/CRLF checkout translation; dependency content was unchanged. All3 public installed
signer-tool files matched their existing pinned hashes immediately before signing.
The reviewed installed signer ran in place with isolated Python import handling;
no private key was copied into the repository, CI or packages, and no new identity
was created. Existing owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.

All8 signatures verified independently. All11 draft downloads matched before
publication; all11 anonymous public downloads then matched names, sizes, SHA-256 and
REST digests. All8 signatures verified again, and the downloaded public key matched
the pinned identity. [Draft proof](../bench/results/U109-draft-downloads.json),
[public proof](../bench/results/U109-public-downloads.json),
[asset/provenance checks](../bench/results/U109-package-assets.json),
[signed manifest](../website/assets/cursiv-owner-release-U109.json).
The redundant release-triggered Mac rebuild40776837732 was cancelled; the successful
tagged build above was retained and owner-authenticated bytes were not replaced.

Windows SHA-256: `d678d03beb0647a48de4737f45df4263d05f6a7d979f38cc639492c7d2e64c4e`.

Mac SHA-256: `ddd23f27bf2f02fef4ca8e67e89fd023eddceeef3aad5ee3706d64b05906c60b`.

## Website publication and remaining limits

The website/evidence update preserves design and concise public pages, updates current
downloads/hash/manifest and software counts, archives U108's evidence and refreshes
technical source-scope references. Production revision/deployment/live-byte, crawler,
favicon and canonical probes are established by the separate publication receipt
linked at the top. PR58 merged `67b79ef247b648ac18be427565a7bea94e0e9bea`; deployment
`d7630911-8a21-44a7-9d54-ab7286f364ce` passed40 live checks covering20 public pages.
An initial generic urllib-agent www request received403; explicit browser and both
search-agent redirects passed301 after correcting the checker headers, with no
additional deployment or security-rule change. No indexing, ranking or AI recommendation is promised; discovery
checks remain manual. Public docs and their generated development source inventory
live on later commits than the immutable binary tag; Python runtime code remains tagged.
Website-only local validation uses focused tests, not a repeated full application suite;
hosted protected checks run as configured.

Windows Authenticode and Apple notarization remain absent; detached owner authentication
is separate. Physical-drive removal, minimum-OS support and independent first-time human
usability are not proven here. General model interpretation and the recorded four partial
narratives remain incomplete. No station, excluded owner file, secret, user-store or
unrelated-profile changes were made. Qwen remains the default; no extra agents were added.

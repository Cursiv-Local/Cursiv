# U108 release verification — October 28, 2026

[U108 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U108).
All11 assets were downloaded anonymously and matched staged bytes and published REST digests;
all8 platform owner signatures independently verified against the existing pinned identity.
Website deployment is established separately by the [publication receipt](../bench/results/U108-publication.json).
A missing receipt means production deployment has not yet been verified; this document alone does
not establish the website's current revision.

## Immutable source and protected checks

- Tag `v3.14-U108`: `a63a4cfb16dbd47c5baae5bbddf6aa08909d537b`.
- [Source PR54](https://github.com/Cursiv-Local/Cursiv/pull/54) merged normally after all16 Actions
  push/PR checks and GitGuardian passed. Reviewed head: `4908a2351a0c1ace1ec2bcf5e2cd86fcf8ffa164`.
  The merged file tree exactly matched that reviewed head.
- [Exact-main CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/40730845919): all8 jobs passed.
- Guarded tag preparation reran the mandatory workspace checks:63 passed in3.09s.
  No administrator bypass or tag replacement was used.

Full isolated Windows suite: **2,521 passed, 15 skipped, 19 subtests passed in334.21 seconds**
on the exact-main hosted runner. The disposable CI environment is separate from the earlier local
pre-version run and from frozen package self-tests.

| Exact-main source suite | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows | 2,521 | 15 | 19 |
| Mac | 2,504 | 32 | 19 |
| Linux | 2,503 | 33 | 19 |
| Hosted ARM64 engine/station checks | 114 | 0 | 0 |

Zero failures/errors in all downloaded JUnit receipts: [Windows](../bench/results/U108-main-windows.xml),
[Mac](../bench/results/U108-main-mac.xml), [Linux](../bench/results/U108-main-linux.xml),
[ARM64](../bench/results/U108-main-arm64.xml), [machine summary](../bench/results/U108-main-ci-summary.json).
Windows console time334.21s; Mac534.36s. JUnit totals include the19 subtests; regular counts above
do not. Skips retain opt-in live-model, platform and supplied-Vosk-archive requirements.
Hosted ARM64 CI is not physical Raspberry Pi validation; station source was unchanged.

All three source commits ran the enabled45-case USB hook in isolated disposable stores:
76.06s,70.62s and80.05s. The pre-version local full suite passed2508/15/19 in409.55s;
later source/packaging/parser changes are covered by the exact-main gates above.

Initial hosted Mac/Linux checks found three real sentence-punctuation filename failures.
The repair preserves quoted literal trailing dots, explicit file commands and file authorization;
207 affected checks passed. The push Mac job on the repaired source then failed to acquire a hosted
runner, with no test execution. Its [retry](https://github.com/Cursiv-Local/Cursiv/actions/runs/40725411838)
passed unchanged; the separate PR Mac suite and native package preflight also passed. An initial
Mac preflight used an abbreviated checkout ref and failed before building; subsequent preflights
used the full source hash. Failed trials remain recorded rather than being relabelled as passes.

## Behavior, measurements and limits

The [validation matrix](U108-VALIDATION.md) records baseline causes and before/after results for
read-only permission parsing, source/notebook routing, sample/record-ID lookup, requested confirmation,
available-history recall and native dimensional refusals. Original native cases improved3/19→19/19.
Explicit brief banter now excludes unrelated private and operational context; initial humor remains
too literal. No scientific calibration or overconfidence algorithm improvement is claimed.

[Automatic source inspection](U108-SELF-INSPECTION.md) supplies fingerprint-checked public source
for natural implementation questions and current-chat follow-ups. General model interpretation
still makes mistakes. Critical confirmation, correction-history and provider-order explanations
use maintained native rules gated by inspected AST witnesses; changed witnesses stop the answer.
Four newly frozen critical questions passed4/4 natively, with zero model calls. Earlier ordered-flow
model failures remain in the evidence. These contracts are not a general theorem prover.

Installed `qwen3:4b-instruct` supplied the live-model evidence, temperature0/seed42/context8192,
with outside connections blocked. Original ten-prompt model calls fell10→3 as native answers replaced
model work; final repeated input/output tokens19547/2324→5915/134. These are small synthetic regression
results, not a general speed estimate, blind accuracy score or independent human study. Valid source
references do not establish correct interpretation or complete codebase understanding.

## Tagged native packages and owner authentication

Windows was built from a clean detached checkout of the immutable tag with the existing locked
environment. The guarded builder passed its own workspace gate, frozen installed and portable checks,
then Inno Setup. Both reports say ALL PASSED: [installed](../bench/results/U108-windows-frozen-selftest.txt)
and [portable](../bench/results/U108-windows-portable-selftest.txt). Portable startup used a disposable
drive layout and checked that it did not write Cursiv data to the host home.

[Tagged native Apple Silicon build40734335453](https://github.com/Cursiv-Local/Cursiv/actions/runs/40734335453)
passed2504 source tests/32 skips/19 subtests in542.36s and its
[frozen app self-test](../bench/results/U108-mac-frozen-selftest.txt) says ALL PASSED. Both platforms
exercise versioned source reads and all3 critical-rule witnesses inside the actual bundle, without
model or private notebook reads. General frozen tests cover plugin isolation, notebook chain/export/
signature, document retrieval, calculations and window construction. CI does not claim live Ollama
inference inside the Mac package.

All8 final platform assets passed exact alias equality, checksum coverage and exact-tag source
provenance. Native lock hashes match only the Git lock bytes or their complete LF/CRLF checkout
translation; dependency content was unchanged. All three installed public signer-tool hashes matched
their pinned trusted manifest immediately before use. The existing installed signer ran in place;
no private key was copied into the checkout, CI or packages, and no new signing identity was created.
Owner fingerprint: `f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.

All8 signatures verified independently. All11 draft downloads matched before publication. All11 public
downloads then matched names, sizes, SHA-256 and REST digests; all8 signatures verified again and the
downloaded public key matched the pinned identity. [Draft receipt](../bench/results/U108-draft-downloads.json),
[anonymous public receipt](../bench/results/U108-public-downloads.json),
[asset/provenance checks](../bench/results/U108-package-assets.json),
[signed manifest](../website/assets/cursiv-owner-release-U108.json).
Redundant release-triggered Mac run40736832987 was cancelled; the successful tagged build above
was retained and authenticated release bytes were not replaced.

Windows SHA-256: `e1b43566ed7aee0650431455d598752d51c69a478819d5a0e0f8a64118fa6db7`.

Mac SHA-256: `5cc0ddad3c30dd49ecb2b7ee1004e42f7a13175a24b56895d6678d7eb275e07d`.

## Website publication and remaining work

The website/evidence update keeps the existing design and concise public pages, moves U107's
evidence into the historical archive, refreshes current download links/hash/manifest and adds
bounded source-inspection details to the technical references. It corrects the stale Vision-page
software count. The production revision, review URL, deployment ID and live crawler/icon/canonical
checks are recorded in the publication receipt linked above after deployment. No indexing, ranking
or AI recommendation is promised; discovery checks remain manual.

Website/public documentation lives on later commits than the binary tag. Its generated development
source inventory is refreshed for those public document bytes; Python runtime code remains tagged.
Local website validation uses focused website, consistency, source-inventory and workspace checks;
no local full app suite is rerun for static publication. Hosted protected checks run as configured.

Windows Authenticode and Apple notarization remain absent; owner authentication is separate.
Physical drive/removal behavior, minimum-OS support and first-time human usability remain unproven
here. General code interpretation, humor, broader report comparisons, conversational exports and
project isolation remain incomplete. No station, owner-excluded file, secret, user store or unrelated
profile changes were made. Qwen remains the default model; no additional agents were introduced.

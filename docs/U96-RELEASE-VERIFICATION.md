# U96 release verification — October 24, 2026

## Immutable source and gates

- Tag: `v3.14-U96`; source: `ddc9385df0e5e892d853e5603bdfb7355e5d92ef`.
- Source PRs: https://github.com/Cursiv-Local/Cursiv/pull/13,
  https://github.com/Cursiv-Local/Cursiv/pull/14 and the version PR
  https://github.com/Cursiv-Local/Cursiv/pull/15.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40140131725.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40140658343.

All five protected checks passed on the PRs and on exact main, including the new
"USB portability (end to end)" step inside both `test` jobs. The release helper reran
the required workspace gate and verified the hash-locked build dependencies.

Pushing the tag also started CI on the same commit (the workflow then ran on every
push, tags included). The release gate correctly treated that newest run as pending and
stopped the first build; the build was rerun after it passed. The workflow now runs on
every branch push but not on tag pushes.

## Executed source checks

Full isolated Windows suite: **1,865 passed, 1 skipped** (on the tag, in the locked
environment). Hosted Windows: **1,865 / 1 skip**; Mac: **1,850 / 16 skips**. USB gate
(`-m usb`, 24 tests including the end-to-end drive life cycle): passed in CI on Windows
and Mac and in the pre-commit hook. Required workspace gate: **63 passed**.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and
required the frozen app's **ALL PASSED** result. It then copied the built app into a
USB layout, started it there and required the self-test line
"PASS portable storage: running from the drive …", the drive's data layout, and no
Cursiv data in the host home folder (`verify_portable`). Both passed before Inno Setup
ran. The tagged Mac workflow passed its source suite and frozen **ALL PASSED** check.
Both aliases match their versioned installers. Checksums and provenance (both
recording source `ddc9385`) were checked before the eight assets were signed locally
with the existing owner key; the signing tools matched their stored hashes first, and
the app's own verifier accepted the manifest.

Windows SHA-256: `0513210ec028f6ec4d209bb951a0f1a82990a4b0fc50dfaeea1aad43abe3e91f`.

Mac SHA-256: `eed8b5862a9d8be5551d59377a539706924932b381bbd6ec40aec4f270cbcee5`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages. No AI key is in any
commit, tag or package source (history checked; only `xxxx` placeholders exist).

## Remaining limits

No new model-accuracy benchmark, second-PC USB test, clean-machine installation or
owner recovery drill is claimed. Free-form self-explanations still depend on the local
model following its labelled evidence; privacy and memory-mechanics questions are
answered without a model.

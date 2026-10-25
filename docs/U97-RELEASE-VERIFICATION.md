# U97 release verification — October 25, 2026

## Immutable source and gates

- Tag: `v3.14-U97`; source: `c7554a72457e6ec7a6df0556e6f2457168664767`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/17 and the version PR
  https://github.com/Cursiv-Local/Cursiv/pull/18.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40161163446.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40161626503.

All five protected checks passed on both PRs and on exact main, including the
"USB portability (end to end)" step inside both `test` jobs. The release helper reran
the required workspace gate and verified the hash-locked build dependencies.

## Executed source checks

Full isolated Windows suite: **1,887 passed, 1 skipped** (on the tag, in the locked
environment). Hosted Windows: **1,887 / 1 skip**; Mac: **1,872 / 16 skips**. USB gate
(`-m usb`, 25 tests on Windows, 24 + 1 platform skip on Mac, including the encrypted
computer ↔ readable drive round trip): passed in CI and in the pre-commit hook.
Required workspace gate: **63 passed**.

New in U97: `tests/test_file_claims.py` (faked file actions, calculator answers,
notebook averages, self-certification lines) and startup tests for always-on
encryption (first start, cancel, USB drive, resume) in `tests/test_data_encryption.py`.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and
required the frozen app's **ALL PASSED** result. It then copied the built app into a
USB layout, started it there and required the portable-storage self-test, the drive's
data layout, and no Cursiv data in the host home folder (`verify_portable`). Both passed
before Inno Setup ran. The tagged Mac workflow passed its source suite and frozen
**ALL PASSED** check. Both aliases match their versioned installers. Checksums and
provenance (both recording source `c7554a7`) were checked before the eight assets were
signed locally with the existing owner key; the signing tools matched their stored
hashes first, and the signer verified the manifest independently.

Windows SHA-256: `b3ecc0f59df4220574ce20551f649f7c2a3e268bc51bf1ec0d7fdef63b708c4a`.

Mac SHA-256: `3433290d0fb8c2588263e11847fcffd2cbc90b92ace7857e615963abefab59c7`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

## Remaining limits

No new model-accuracy benchmark is claimed. Always-on encryption and the encrypted
USB transfer are covered by automated tests; a second-PC USB test, a clean-machine
first start with a real passphrase and an owner recovery drill are not claimed. The
removed family-letters file and family names are gone from the source tree but remain
in git history and in installers of earlier releases until a separate, reviewed purge.

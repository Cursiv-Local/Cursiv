# U95 release verification — October 24, 2026

## Immutable source and gates

- Tag: `v3.14-U95`; source: `7ed476327736593c1d549e6fcb64ed82538bdd36`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/10.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40123775332.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40124370698.

All five protected PR and exact-main checks passed before tagging. The release
helper reran the required workspace gate and verified the hash-locked build
dependencies before building.

## Executed source checks

Full isolated Windows suite: **1,819 passed, 1 skipped** (on the tag, in the locked
environment). Hosted Windows: **1,819 / 1 skip**; Mac: **1,804 / 16 skips**.
Required workspace gate: **63 passed**. Seven new import tests in
`tests/test_usb_sync.py` cover routing each file to the folder the installed app
reads, staging then applying at start, re-checking work done after staging,
refusing a damaged staged copy, re-encrypting keys and skipping encrypted stores.

A read-only dry run against the owner's real USB and installed app found 1
conversation only on the drive and 174 identical files. No real import was run on
the owner's PC; synthetic data was used for all automated tests.

## Tagged packages and independent owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies,
required the frozen app's **ALL PASSED** result and compiled Inno Setup. The tagged
Mac workflow passed its source suite and frozen **ALL PASSED** check before creating
the DMG. Both aliases match their versioned installers. Checksums and provenance
(both recording source `7ed4763`) were checked before the eight assets were signed
locally with the existing owner key; the signing tools matched their stored hashes
first, and the app's own verifier accepted the manifest.

Windows SHA-256: `44eab0866cdd0f451b91e9f15b61dc1f411a66d456e44da23be720cc57cf4688`.

Mac SHA-256: `2c134cf5f88a0e27ace24f0a456851c73abc95df8f699074a4ec781460236b5e`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

## Remaining limits

No new model-accuracy benchmark, second-PC import, clean-machine installation or
owner recovery drill is claimed. Field logs changed on both a drive and a computer
are not merged line by line; the newer file wins and the other is kept in backups.

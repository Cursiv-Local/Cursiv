# U105 release verification — October 26, 2026

## Immutable source and gates

- Tag: `v3.14-U105`; source: `501d94e9ee3ed4ff729612709e9f8ca1d89f4fb1`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/43.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40368047478 (JUnit XML kept as artifacts).
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40371220185.

All protected checks passed on the PR and on exact main, including the "USB portability (end to end)" step
inside both `test` jobs. `test-linux` and `station-arm64` (experimental, not release-blocking; see
[SUPPORT-MATRIX](SUPPORT-MATRIX.md)) also passed.

## Executed source checks

Full isolated Windows suite: **2,200 passed, 15 skipped** (on the tag, in the locked
environment). Of the 15 skips, 13 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model), 1 needs a Mac's Keychain, and 1 checks the real Vosk download against its pinned hash (runs only with
`CURSIV_VOSK_ZIP`; it passed when the pin was measured). Hosted Windows: **2,200 / 15 skips**; Mac:
**2,183 / 32 skips**; Linux: **2,182 / 33 skips**; ARM64 station: **114 passed**. USB gate: **45** on Windows,
44 + 1 platform skip on Mac and Linux. Required workspace gate: **63 passed** on both.

New in U105:
- `tests/test_signing_key_passphrase.py`: the same key is kept under a passphrase (same id), a locked key signs
  nothing and is never replaced, a wrong passphrase is refused, and a main computer that pinned the drive's
  key keeps accepting its shares after it's protected.
- `tests/test_team_drives.py` (mandatory USB gate): strict import refuses a notebook with a damaged photo and
  copies none of its entries or photos; the default import still keeps them and names the photo.
- `tests/test_safe_zip.py`: names leaving the folder, links, too many files, too much data, zip headers that
  understate sizes, an existing folder, not-a-zip; the Vosk download refused on a checksum mismatch. The pin
  `30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498` was measured by downloading the
  published file (41,205,931 bytes) on 2026-10-26.
- `tests/test_release_docs.py`: release notes and CHANGELOG for the current version, linked verification
  documents, the README, the website's signed manifests and the docs index; checked to fail on a missing
  document.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and required the frozen app's
**ALL PASSED** result, including plugin isolation, in the installed layout and in the USB layout. The tagged
Mac workflow passed its source suite and frozen **ALL PASSED** check. Both aliases match their versioned
installers. Checksums and provenance (both recording source `501d94e`) were checked before the eight assets
were signed locally with the existing owner key; the signer verified the manifest independently.
Installers downloaded back from the published release match.

Windows SHA-256: `29c8643d99966d008bdc78380a7f9039b0e74d2c425e61dfbaf62207942bed08`.

Mac SHA-256: `26d2106b298480932d8149a91f0c18c6e0197656912105ceb4b1578f7bc30666`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

The owner has run physical tests (installed app, USB drive and external SSD across clean PCs) on Windows in
earlier releases. U105's changes are tested automatically only. There is no physical testing on a Mac or a
Raspberry Pi.

## Remaining limits

The signing-key passphrase protects the key at rest; once unlocked in a running Cursiv it's in memory like
any key. The Field Station preview still hasn't run on a Raspberry Pi. All results are the project's own
testing; nothing has been independently reviewed. See [THREAT-MODEL](THREAT-MODEL.md) and [RECOVERY](RECOVERY.md).

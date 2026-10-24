# U94 release verification — October 24, 2026

## Immutable source and gates

- Tag: `v3.14-U94`; source: `f5b9940c56f39ead84dff9333e97f67516e2784e`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/8.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40119774514.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40121155490.

All five protected PR and exact-main checks passed before the release build:
Windows/Mac workspace gates, Windows/Mac full suites and security. No force push
or bypass was used. The release helper reran the required workspace gate and
verified the hash-locked build dependencies before building.

## Executed source checks

Full isolated Windows suite: **1,812 passed, 1 skipped**. Hosted Windows:
**1,812 / 1 skip**; Mac: **1,797 / 16 skips**. Required workspace gate:
**63 passed**. New `tests/test_usb_sync.py` covers add/update/keep decisions, grown
logs, backups before replacement, hash verification, cancellation, linked folders
and program copies without data folders; the portable migration test now asserts
newer-wins with a backup instead of stopping startup.

The failure was reproduced on a copy of the owner's real USB data first
(`Portable data conflict at council_memory.json`). With the owner's approval the
real drive was then updated from an untagged local build of the same change: 2,635
program files verified, the one-time migration and data update wrote verified
backups, a second Check drive found nothing to update, and `Start Cursiv.bat`
started Cursiv to its login window with no crash log. Sign-in and chat on the drive
were not exercised. Synthetic data was used for all automated tests.

## Tagged packages and independent owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies,
required the frozen app's **ALL PASSED** result and compiled Inno Setup. The tagged
Mac workflow passed its source suite and frozen **ALL PASSED** check before creating
the DMG. Both platform aliases match their respective versioned installers.
Checksums and provenance (both recording source `f5b9940`) were checked before the
eight installer/checksum/provenance assets were signed locally with the existing
owner key. The independent signing tools matched their stored hashes first, and
the app's own verifier accepted the manifest.

Windows SHA-256: `0863df1ded070f315db084e2f5f35ed517c0aa14f52b7b0369bb99e438b7f9a7`.

Mac SHA-256: `daf6ce9d8a874a3846677341ff77983371eb6fc0fcc9d3cdb2160bfaef053a96`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages. Owner signatures are
separate from Windows-trusted Authenticode and Apple notarization; warnings remain.

## Remaining limits

No new model-accuracy benchmark, second-PC USB persistence test, clean-machine
installation or owner recovery drill is claimed. Data moves one way (computer to
drive) in U94. Personal legal notes and local test files remain excluded.

## Publication and production verification completed

- GitHub latest stable U94 published with 11 assets; GitHub's recorded SHA-256 of
  each installer equals the signed hash. The release-triggered `mac-build` run
  (40122170647) was cancelled so the signed DMG is never replaced.
- Evidence PR: https://github.com/Cursiv-Local/Cursiv/pull/9 (all five checks passed).
- Cloudflare `cursiv-web` deployment: `2efce0cb-29d6-46a6-adf3-45ac10b349cd`.
- Website build and all **21 website regression checks passed**.
- Anonymous production checks: **33 of 37 passed**. Both domains serve every page;
  no U93 download link remains; the live U94 hash, signed manifest and public key
  equal the repository copies; both installers downloaded from the public links
  match the signed hashes and verify with the app's owner-proof verifier; GitHub's
  latest release is U94; custom 404, robots and sitemap rules hold; `/admin/` is not
  anonymously readable.
- The 4 failures are "live HTML equals build" for `/`, `/start`, `/vision` and
  `/ai-reliability-testing`: Cloudflare inserts its Web Analytics beacon
  (`static.cloudflareinsights.com`) into those pages for browser requests. Only
  `/testers` sends `no-transform`, which blocks it. This comes from the Cloudflare
  account setting, predates U94, and is not disclosed in the privacy policy. It is
  recorded here for the owner's decision; nothing was changed in Cloudflare.

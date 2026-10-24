# U93 release verification — October 24, 2026

## Immutable source and gates

- Tag: `v3.14-U93`; source: `cffcee8478eccc1fdfb9a6714ec0fc705fc96227`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/6.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40060612503.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40061149384.

All five protected PR and exact-main checks passed before tagging: Windows/Mac
workspace gates, Windows/Mac full suites and security. Strict/up-to-date checks
and administrator enforcement remain enabled; no force push or bypass was used.
The supported release helper reran the required workspace gate before tagging.

## Executed source checks

Full isolated Windows suite: **1,805 passed, 1 skipped** with locked dependencies,
in 228.85 seconds. Hosted Windows: **1,805 / 1 skip**; Mac: **1,791 / 15 skips**.
Focused typography/rendering/guide checks: **86 passed**. Required workspace gate:
**63 passed**. Seven new deterministic typography cases cover streaming/final
rendering, old HTML, unchanged history, point/pixel units and idempotence.
Synthetic profiles and fake providers were used; no owner data was migrated.

## Tagged packages and independent owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies,
required the frozen app's **ALL PASSED** result and compiled Inno Setup. The tagged
Mac workflow passed its source suite and frozen **ALL PASSED** check before creating
the DMG. Both platform aliases match their respective versioned installers.
Checksums, sizes, provenance and tagged source were checked before the eight final
installer/checksum/provenance assets were signed locally with the existing owner
key. The independent signing tools matched their stored hashes first.

Windows SHA-256: `8d749ecec18dce87a63638a5a5e89fa522476179b082fdb577aba92371775821`.

Mac SHA-256: `6d39ec3fc6db551d698147101271afcbae30d898e8c55046e1bf91a7502f2e15`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages. Owner signatures are
separate from Windows-trusted Authenticode and Apple notarization; warnings remain.

## Website and publication

Current U93 links, hash, owner proof and software counts are updated together.
The secondary homepage tester link, bottom tester downloads, tester artwork and
custom 404 are preserved. Historical model scores remain unchanged. Final public
checks are recorded below after successful publication and deployment.

## Remaining limits

No new model-accuracy benchmark, physical encrypted-USB persistence test,
clean-machine installation or owner recovery drill is claimed. Typography changes
presentation only. Personal legal notes and local test files remain excluded.

## Publication and production verification completed

- GitHub latest stable U93 published `2026-10-24T04:19:21Z` with 11 assets.
- Cloudflare `cursiv-web` deployment: `98ef90e7-5ebc-4c3a-b564-397ebd637f1a`.
- Website build and all **21 website regression checks passed**.
- All **49 anonymous production checks passed**, including actual signed asset
  bytes, immutable tagged source, generated-versus-live HTML, absolute metadata,
  canonical routes, current hash/proof, secondary tester link, bottom tester
  downloads, exact tester artwork, custom HTTP 404, notebook/photo pages,
  robots/sitemap, legacy redirect and anonymous private-statistics denial.
- Final Windows bytes are also saved in the normal local installer output folder.

Both protected PRs and the exact source-main gates are retained in GitHub Actions.
No installer was launched on the owner's machine, and no private key was copied.

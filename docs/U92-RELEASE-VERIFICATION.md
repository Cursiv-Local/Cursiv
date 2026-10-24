# U92 release verification — October 23, 2026

## Immutable source and required gates

- Tag: `v3.14-U92`; application source: `fa61b2695622c45eeaed1097e4a7ec3bc62b8be0`.
- Protected source PR: https://github.com/Cursiv-Local/Cursiv/pull/4.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40040215616.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40040910138.

All five required PR and merged-main checks passed: Windows/Mac workspace gates,
Windows/Mac source suites and security. Strict/up-to-date checks and administrator
enforcement remain enabled. The supported tag helper rechecked exact-main CI and
ran the required workspace gate before creating the new immutable tag.

## Source checks actually executed

Full isolated Windows suite: **1,798 passed, 1 skipped** with locked dependencies.
Hosted Windows: **1,798 passed / 1 skipped**; Mac: **1,784 passed / 15 skipped**.
Required workspace gate: **63 passed**. Focused guide/transcript/UI/native/help:
**164 passed**; final guide/UI wording replay: **38 passed**. Disposable profiles
and fake providers were used. No owner memories, notebook data or keys were migrated.
One synthetic Qwen brief-prompt check returned 42 words; it was not a full-app
performance measurement or a general model-accuracy score.

## Tagged packages and independent owner proof

The locked Windows environment built the tag in a separate clean checkout. Its
frozen self-test reported **ALL PASSED**, then Inno Setup compiled successfully.
The tagged Mac workflow passed source tests and its frozen self-test before DMG
creation. Versioned and latest aliases have identical respective bytes. Provenance
records identify the tested source. The eight installer/checksum/provenance assets
were verified and signed locally with the existing independent owner key after
the trusted external signing tools matched their recorded hashes.

Windows installer SHA-256: `b4d815f75befcfe75790924367aabd9a84ba97ecb692d6257b9a43432ca4bcc4`.

Mac DMG SHA-256: `f9e0781ecc4594aa01435015b712a330909fefb6435a1679aa92915f0398622c`.

Owner public-key fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material was copied to the repository, CI or installers.

## Website and publication

Current download links, actual Windows hash, owner proof and software-test counts
are updated together. Historical model scores are retained. The blue Help test
Cursiv invitation remains above the navigation and links to `/testers`.
Final public checks are recorded below only after publication is verified.

## Remaining limits

No new live-model truth benchmark, physical encrypted USB memory-persistence test,
clean-machine install or owner recovery drill was run. Broader model wording can
still be wrong. Owner detached signatures are not Windows-trusted Authenticode or
Apple notarization; publisher warnings remain. Personal legal notes and local test
files remain excluded. Tester-card design is handled by the owner's separate chat.

## Publication and anonymous production checks completed

- Published latest stable at `2026-10-23T23:52:03Z` with 11 public assets.
- Cloudflare Worker `cursiv-web`: deployment `32d49153-c520-498c-abc2-3635b276a597`.
- All **21 website regression checks passed** after generating the static output.
  The initial fresh-checkout run correctly required a build first (20/21); after
  building, all 21 passed without changing tests.
- All **47 anonymous production checks passed**: eight signed downloads with
  actual bytes/hash/size checks, immutable tag, canonical/indexable HTML matching
  generated pages, current links/hash/owner proof, preserved tester banner and
  exact tester artwork, notebook/photo routes, sitemap, robots, legacy redirect
  and authentication denial for private statistics.
- The other chat's published tester HTML/artwork were first compared against
  production. Artwork/metadata remain unchanged; its download CTA now targets U92.
  Separate unfinished 404 work was excluded and preserved in the main workspace.
- Tagged Mac build 40040910138 passed; redundant release-triggered build
  40042024443 was canceled after the verified owner-authenticated assets were public.
  This cancellation is not the result of the tagged build used for the release.

The tagged Mac screenshots were inspected: U92's no-model starter exposes the
native feature guide, and the notebook shows its offline-phone link and intact
sample chain. No new physical Mac/Windows/USB test is claimed.

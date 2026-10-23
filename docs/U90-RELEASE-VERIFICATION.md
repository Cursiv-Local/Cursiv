# U90 release verification — October 23, 2026

## Immutable source

- Tag: `v3.14-U90`.
- Application source commit: `54d6fcdc9d2a50a8142892f197db947e29dfe667`.
- [Release notes](RELEASE-U90.md).
- [Source CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/39997497718).
- [Tagged Mac build](https://github.com/Cursiv-Local/Cursiv/actions/runs/39997497559).

## Completed local checks

- Full isolated Windows suite: **1,636 passed, 1 skipped** in 222.38 seconds.
  Disposable application data; no owner conversation or memory data migrated.
- All **21 website tests passed**, including public-counter removal, retained
  analytics, signed artifact evidence, canonical metadata and current release labels.
- Website build-only and whitespace/diff checks passed.
- Homepage secondary Help test Cursiv link, `/testers` page, routing and sitemap
  entry retained. Public pages no longer request GitHub download totals.
- Hash-locked Windows build dependencies match the release lock.
- Independently installed signing-tool hashes match the reviewed U89 tool manifest.
  Owner key and public-key fingerprint are unchanged.

## Windows tagged installer

The hash-locked release helper built a clean checkout of the tag. Its frozen
self-test reported **ALL PASSED**, including full window construction, pinned
owner identity, notebook persistence, SHA-256 chain and export signature checks.
Inno Setup compilation succeeded. Versioned and latest installers have identical bytes.

Windows installer SHA-256:
`d2feae8f3fa18e1195e0555872dba92c1dd907e67023a20a62266c672a7bb4a2`.

## Hosted and Mac gates

[Source CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/39997497718) passed
on both platforms: Windows **1,636 passed / 1 skipped**, Mac **1,622 passed / 15 skipped**.
The locked dependency vulnerability audit and high-severity/high-confidence Bandit gate passed.

The [tagged Mac build](https://github.com/Cursiv-Local/Cursiv/actions/runs/39997497559)
passed **1,622 tests / 15 skips** and its packaged app reported **ALL PASSED**.
The DMG and latest alias match their checksum and tagged source provenance.

Mac DMG SHA-256:
`6a1bd0baffc929af0ecde9d4a1a1390cc0b83acc956f1b6e8835bcea9a42669a`.

## Owner proof and publication

The independently installed, hash-checked signing tool signed and verified the
final eight installer/checksum/provenance assets for source commit
`54d6fcdc9d2a50a8142892f197db947e29dfe667`. The existing owner key was used;
no private material was copied into the repository or CI.
Public key fingerprint: `f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.

Public release/download verification and website deployment are still in progress.
Results will be recorded after they complete.

## Remaining manual limits

No new local-model truth benchmark was run. Older model results are historical.
Physical encrypted-memory persistence on a second USB/SSD machine, clean-machine
installation and a signing-key recovery drill remain owner checks. Encryption is
optional and excludes notebook data, workspace documents, logs and explicit exports.
No Windows-trusted Authenticode certificate or Mac notarization was added.
Owner detached signatures do not remove operating-system publisher warnings.

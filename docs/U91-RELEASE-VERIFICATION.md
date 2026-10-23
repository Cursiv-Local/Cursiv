# U91 release verification — October 23, 2026

## Immutable source and gates

- Tag: `v3.14-U91`; application source: `043f7b24b9f7e036f0363216c502e5640d346eb3`.
- Protected source PR: https://github.com/Cursiv-Local/Cursiv/pull/2.
- Merged-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40010046249.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40011158453.

All five required PR and exact-main checks passed: Windows/Mac workspace gates,
Windows/Mac source suites and security. Administrator enforcement, strict checks,
force-push denial and branch-deletion protection remain enabled. The supported
helper rechecked main and ran the workspace gate before creating the immutable tag.

## Source checks actually executed

Full isolated Windows suite: **1,749 passed, 1 skipped** with locked release dependencies.
The development-interpreter replay also passed 1,749 / 1 in 207.88 seconds.
Hosted source checks passed Windows **1,749 / 1**, Mac **1,735 / 15**.
The native workspace gate passed **63**; philosophy/compatibility replay passed
**171**, including 50 new philosophy regressions. Dependency and static-security
gates passed. Disposable profiles and fake providers were used; no owner data
was migrated and no new live-model truth benchmark is claimed.

## Tagged packages and independent owner proof

The existing locked Windows environment built a clean checkout of the tag.
Its frozen self-test reported **ALL PASSED**, then Inno Setup compiled successfully.
The tagged Mac workflow passed its source tests and frozen self-test before DMG creation.
Both versioned installers and their latest aliases have identical respective bytes.
Build provenance and all eight installer/checksum/provenance assets were independently
verified against the tagged source and signed locally using the existing, separately
held owner key. The trusted external signing tools matched their stored hashes.

Windows installer SHA-256: `1b3edd09da20b8954029d212f7e6c219bcb3a97113c6acdc0ae14a215c941119`.

Mac DMG SHA-256: `ca6f123abea0fa4955d94f1ea6ecb75c22dbae2509b527897bd661e07e59de34`.

Owner public-key fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material was copied into the repository, CI or installers.

## Website and publication

All **21 website tests passed**, including signed manifest/hash agreement, current
release links, SEO/structured data, tester invitation position and private admin
behavior. Build-only and whitespace checks passed.

Prepared the current U91 links, actual Windows hash, signed owner manifest and
software-test evidence, retaining historical model scores. The wide blue Help
test Cursiv invitation remains above the navigation and links to `/testers`.
Completed publication, final website checks and independent public downloads
are recorded below.

## Completed publication and live verification

U91 was published as GitHub latest at **2026-10-23T19:39:42Z**, with all
11 intended public assets. Every uploaded size and SHA-256 matched the local
staging files. Independent unauthenticated downloads of all eight signed
installer/checksum/provenance assets matched the existing owner key and manifest;
both platform latest aliases matched their respective versioned installers.

The existing `cursiv-web` Worker deployed successfully as
`a5b407f1-bd38-44f9-a9a4-ae521bb950a3`. No DNS, secret or D1 schema change was made.
The deployed website source was committed as `33a66a7` before deployment; later
commits record publication outcomes, without changing the immutable app tag.

All **45 anonymous production checks passed**. Generated current-release HTML
matches production after accounting for the pre-existing edge beacon. Checks
covered the blue tester invitation and exact stylesheet, U91 links and actual
checksum, public owner proof, canonical/HTTPS/indexability/JSON-LD, the social PNG,
existing phone routes, robots/sitemap, tester contacts/no-script policy and legacy
redirect. Both unauthenticated private-statistics endpoints returned 401/no-store.
The public download counter remains removed.

The publication event triggered a redundant Mac rebuild (`40013158416`); it was
cancelled after the independently verified tagged build (`40011158453`) and owner
signing had already completed. Published signed assets were not replaced.

## Remaining manual limits

No new live-model truth benchmark, physical encrypted USB memory persistence,
clean-machine install or owner recovery drill was run. Optional U90 encryption
retains its documented exclusions. Owner detached signatures are not Windows
CA-issued Authenticode or Apple notarization; publisher warnings remain.
Existing personal legal notes and test files remain untracked and untouched.

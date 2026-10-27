# U107 release verification — October 27, 2026

The Windows and Mac packages are published, anonymously downloadable, and linked from the verified
production website. Source, packages, owner signatures and publication checks are recorded below.

## Immutable source and completed gates

- Tag: `v3.14-U107`; source: `7d6ae616dd8c8f4b15e1b3078208ab7c78ca05bb`.
- [Source PR #51](https://github.com/Cursiv-Local/Cursiv/pull/51), merged normally after all16
  push/PR checks passed. Reviewed source commit: `0afe4ca51b7152d4056b2869aa6cd8925eeee0ea`.
- [Exact-main CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/40537766999): all8 jobs passed.
- [Tagged native Mac build](https://github.com/Cursiv-Local/Cursiv/actions/runs/40539718907): successful.
- [Published release](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U107).

Required Windows/Mac workspace, full-suite and security checks passed on exact main before the
guarded release helper created the new tag. The local preparation workspace gate passed63/63.
No administrator bypass or tag replacement was used. The U106 tag and release assets are unchanged.

Full isolated Windows suite: **2,389 passed, 15 skipped, 19 subtests passed in 496.51 seconds** on
the final versioned source. [JUnit](../bench/results/U107-release-final-full.xml).
The USB commit hook passed **45/45 in 99.24 seconds**; it was enabled, with isolated stores.
The 15 source skips are13 opt-in live-model cases, one Mac Keychain case and one supplied-Vosk-zip case.

Downloaded exact-main JUnit artifacts have zero failures/errors:

| Hosted source suite | Passed cases including subtests | Skipped |
|---|---:|---:|
| Windows | 2,408 | 15 |
| Mac | 2,391 | 32 |
| Linux | 2,390 | 33 |
| ARM64 station | 114 | 0 |

Windows/Mac/Linux counts include19 passing subtests. The completed Windows console summary is
2,389 regular tests plus19 subtests in329.92s; Mac is2,372 regular tests plus19 in519.44s.
Native workspace and hosted USB steps passed. ARM64 CI is not physical Raspberry Pi testing;
no Linux installer or new Field Station capability is claimed. Local downloaded artifacts/counts:
`reports/U107-main-ci-artifacts/counts.json`.

## Repairs, measurements and retained failures

The five existing read-only helpers now use routed commands, one scoped evidence snapshot,
code-computed notebook checks/statistics, shared output checks and bounded model work. Deferred
execution has durable claims and explicit outcomes. Stale results cannot become a later chat's
reply/history. See the [defect-to-repair-to-test matrix](U107-VALIDATION.md) and [usage](U107-AGENTS.md).

Release preparation exposed a delayed session-note worker resolving a later global storage folder:
2,381 passed/1 failed in the first versioned suite. The original failed receipt and
[directory audit proof](../bench/results/U107-session-note-race-proof.json) are retained. The worker
now captures destination/owner/turn, stops when stale or cancelled, and shares model serialization.
Profile/native metadata notes use no extra unbudgeted model summary. The restricted-turn guard was
not relaxed. Focused ownership checks passed170 tests; the final versioned full suite above passed.

Installed `qwen3:4b-instruct` comparisons used synthetic data, temperature0, seed42, context8192,
offline/local-only permissions and an RTX2050/4GB GPU. On three comparable routine tasks, group
median tokens2,809→530 (**81.13% lower**) and completion12.352→2.049s (**83.41% lower**).
Individual median2.531→2.171s (**14.21% faster**). Record-dependent cases are separate correctness
comparisons because the old group omitted their evidence. Ordinary-chat median did not improve.

Original18/18 and previously seen held-out15/15 profile-route retests met requested substance under
Codex grading. These are regression checks, not a new blind evaluation or independent human study.
Writing timing embellishments and earlier failed trials remain disclosed. Cache-hit and peak-memory
metrics are unavailable. No new full158-case model score or science-rule improvement is claimed.
Method, raw answers, settings, hashes and limitations: [U107-VALIDATION](U107-VALIDATION.md).

## Tagged native packages and owner authentication

Windows clean-tag build completed with exit0. Both frozen3.14-U107 checks report **ALL PASSED**:
[installed layout](../bench/results/U107-windows-frozen-selftest.txt) and
[portable layout](../bench/results/U107-windows-portable-selftest.txt). They cover plugin isolation,
notebook save/chain/export/signature, document retrieval, calculations and full window construction.
The portable test used a disposable drive layout; it did not use an owner's physical drive.

The native Apple Silicon workflow passed2,372 source tests/32 skips/19 subtests in492.45s and
its frozen app reports [ALL PASSED](../bench/results/U107-mac-frozen-selftest.txt). Source CI and
native frozen packaging are separate checks; a green source run alone was not treated as a package.

The eight final platform assets passed exact alias equality, checksum/provenance coverage, dependency
lock hashes and tagged source identity checks. The three installed public signer-tool files matched
their trusted manifest. The unchanged installed owner signer ran in place; no private key was copied
into the checkout, CI or packages. Existing owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.

All eight platform assets independently returned **OwnerSignatureValid**. All11 draft assets were
downloaded back and compared before publication. After publication, all11 were downloaded anonymously;
names, sizes and SHA-256 hashes matched staged originals, all11 published REST digests matched, and
all8 platform signatures verified again against the pinned key. The downloaded public key matched.
The signed manifest is [cursiv-owner-release-U107.json](../website/assets/cursiv-owner-release-U107.json).
The redundant release-triggered Mac run40542462834 was intentionally cancelled; it is separate from
the successful tagged build40539718907. Authenticated bytes were not replaced.

Windows SHA-256: `b56819d957fadd77ef454b4eefe95a32375792d4c55cc4fb1c1afcc2473f6cf9`.

Mac SHA-256: `59bda04a779651327fcc04921bffc184b1b3e8547ca4e9258b869ab177b94101`.

## Website and remaining limits

Website/evidence [PR52](https://github.com/Cursiv-Local/Cursiv/pull/52) merged normally at
`cdb6f03ceae8bffdb83626facf926265d9ae6116` after all18 push/PR checks passed. Local allowlisted build
produced23 HTML pages;31 website checks,6 release/version consistency tests and63 workspace checks
passed. The commit USB hook passed45/45 in82.04s. No full app suite was rerun locally for these
static website edits; hosted protected checks ran as configured.

Cloudflare deployment succeeded for cursiv.us, www.cursiv.us and cursiv.winklers-llc.com, version
`edbccc5a-8eef-4a00-85bb-9523f507ffc4`. Eighteen live checks passed: Start changedU106→U107;
homepage/Start/evidence/references/robots/sitemap/icons/manifest returned200 with exact deployed
bytes and no-transform headers; U107 installer URLs and Windows hash matched; the public signed
manifest matched the verified release. Browser, Googlebot and Googlebot-Image user-agent probes
returned200 for homepage/favicon paths; the www Start URL redirected to the canonical apex.
Intentional /api/, /remote/ and /admin/ robots exclusions remain. A user-agent probe does not certify
Google's indexing or ranking. [Machine-readable publication receipt](../bench/results/U107-publication.json).

The publication retains concise public pages, current branding, historical results, discovery files
and private exclusions. No new ranking or AI recommendation is promised. The owner uses a manual
discovery checklist; no automation was created.

All results are project-owned testing. Source/offscreen Qt, hosted native Mac, frozen installed/portable
layouts and automated USB checks do not establish first-time human usability, minimum-OS support,
physical filesystem/drive-removal behavior or independent scientific validity. Windows Authenticode
and Apple notarization remain absent; owner authentication is separate. Broader report comparisons,
general conversational exports and project isolation are not completed here. Existing model and
science limits remain; experimental station source and model options are unchanged.

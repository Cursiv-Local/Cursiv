# U106 release verification — October 26, 2026

The tagged packages and website are published. The final live check and deployment receipt are recorded below.

## Immutable source and gates

- Tag: `v3.14-U106`; source: `10b40d6d9bcce73102e22d5bcd3d0fca8ba60a4a`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/45 (merged).
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40423748096.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40424952938 (**successful**).
- Published release: https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U106.

All seven exact-main CI jobs passed. The native workspace gate and hosted USB portability steps passed;
no per-step case counts are inferred here. Linux and the experimental ARM64 station job also passed; see
[SUPPORT-MATRIX](SUPPORT-MATRIX.md) for which checks block a release. The main CI results and build
workflow are separate: a green source CI run is not proof that the tagged packages have finished.

## Executed source checks

The downloaded exact-main JUnit artifacts record zero failures/errors:

| Hosted source suite | Passed | Skipped | JUnit artifact |
|---|---:|---:|---|
| Windows | 2,253 | 15 | `test-results-windows-latest` |
| Mac | 2,236 | 32 | `test-results-macos-latest` |
| Linux | 2,235 | 33 | `test-results-ubuntu-latest` |
| ARM64 station | 114 | 0 | `test-results-station-arm64` |

Counts were read from those JUnit XML files, with summary retained locally at
`reports/U106-main-ci-artifacts/counts.json`; all refer to the full source commit above.

Full isolated Windows suite: **2,253 passed, 15 skipped in 393.73 seconds**, with zero failures/errors.
This ran on the detached tag using the locked environment. JUnit:
[U106-tag-tests.xml](../bench/results/U106-tag-tests.xml). The 15 skips are exactly
13 opt-in live-model cases, one Mac Keychain case and one supplied-Vosk-zip verification case.

Earlier reviewed source checks passed 2,253 tests with 15 skips and the separate Windows USB gate passed
45 tests. These preview results are retained independently of the hosted and tagged checks.

New U106 coverage includes ordinary-measurement previews and missing-scale handling; confirmed desktop
memory saves, including classifier/numbered-choice paths; receipt-backed linked corrections and stale/card
boundaries; verified historical reads with date/site/sample/measurement filters; real Qt navigation,
labelled non-executing samples, import outcomes and confirmed library-copy removal; repeated synthetic
conversation switching and unchanged memory origins. Restart-test subprocesses now isolate their copied
app data while the data-protection guard remains enabled. Details: [U106-PREVIEW](U106-PREVIEW.md).

Frozen native-routing probes measured **10/18 → 18/18** for action/clarification results and **3/12 → 12/12**
for exact notebook selection; unrelated recall requests were left alone **8/8 in both runs**. A separate
fresh set first scored **11/12**. The missed dated-record request was preserved as measured, then fixed
with a regression; that observed set is not relabelled as untouched or as an original 12/12 result.

The preserved baseline includes **58 real Ollama answers**: 54 fresh risk/control answers across three
installed local models and four Qwen science-audit reproductions. Science/overconfidence rules were
unchanged; no U106 science-rule improvement or new full 158-case model-accuracy result is claimed.
Native-routing/unit-test results are not live-model accuracy or human-usability scores.
See [U106-BASELINE](U106-BASELINE.md).

## Tagged packages, USB start and owner proof

The Windows clean-tag build completed successfully (build helper exit code 0). The installed-layout
frozen self-test reports **ALL PASSED**, including plugin isolation:
[installed report](../bench/results/U106-windows-frozen-selftest.txt). The USB-layout frozen self-test
also reports **ALL PASSED**, including plugin isolation and running/data storage from the synthetic drive:
[portable report](../bench/results/U106-windows-portable-selftest.txt). Both are frozen 3.14-U106 Windows builds.

The tagged Mac workflow completed successfully. Its source suite passed **2,236 tests with 32 skips in
503.06 seconds**. The frozen Mac app reports **ALL PASSED**, including plugin isolation and construction
of the full launcher/chat window: [Mac report](../bench/results/U106-mac-frozen-selftest.txt).

The final assembly check (`reports/verify_u106_assets.py`) passed for all eight platform assets. Both
versioned/latest installer pairs have equal hashes; checksum-file asset sets and hashes, provenance
asset sets and hashes, dependency-lock hashes and the exact tagged source commit were checked.
The public owner-signature verifier reported **OwnerSignatureValid for all eight assets**. The signed
manifest is [cursiv-owner-release-U106.json](../website/assets/cursiv-owner-release-U106.json).
All **11 published assets** were downloaded back: exact names, sizes and SHA-256 hashes match the local
originals and GitHub metadata. All eight downloaded signed platform assets independently reported
**OwnerSignatureValid** against the repository-pinned public key. The downloaded public key matches;
checksum and provenance coverage and the tagged source commit were checked again.

Windows SHA-256: `b69b2c834ab42dbf935b8784cbed63b6dae7dc8873f5230de21026469c74330a`.

Mac SHA-256: `fb7126cfcc45c1e71053a669b6b65690a9f64c842dfed109a5a567f39af7e25c`.

Verified existing owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
The three public signer-tool hashes matched the trusted manifest. The trusted installed signer ran in
place with only a `LOCALAPPDATA` override; no private key was copied into the checkout, CI or packages.
Package owner-signature verification is distinct from an independent review of the application.

The owner performed physical Windows installed-app/USB/external-drive checks in earlier releases.
U106 has automated checks and owner visual review of Qt previews, not a first-time-user study. Physical
Mac, Raspberry Pi and filesystem/drive-removal tests are not claimed. The installers have no Windows
Authenticode signature or Apple notarization; owner package authentication is separate.

## Remaining limits

This is the reviewed first increment of the researcher-experience plan. The imported library is available
across workspaces; notebook project labels and memory project notes are not isolated project boundaries.
General comparison of unspecified reports, broad conversational exports and comprehensive date-scoped
aggregate statistics remain unfinished. Existing export controls remain available. Date filters use saved
local recording timestamps; reported observation times stay notes.

No unfamiliar human users have been recruited or timed. Science/overconfidence rules, model options and
experimental Field Station code are unchanged. Existing answer-quality limits in U106-BASELINE.md still
apply. The drive signing key is in memory after unlock. All results are the project's own testing; nothing
has been independently reviewed. See [THREAT-MODEL](THREAT-MODEL.md) and [RECOVERY](RECOVERY.md).

## Website publication evidence

- Evidence PR: https://github.com/Cursiv-Local/Cursiv/pull/46, merged at
  `105d13243925f3f4035e9731a60d1ead3e771e4d`. All seven jobs passed on both push and PR runs;
  PR CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40427182009.
- Website build: successful, 18 allowlisted pages plus assets, notebook and privacy folders.
- Website tests: **22 passed, zero failed**. Final release/version consistency checks: **6 passed**.
- Deployment succeeded for `cursiv.us` and `cursiv.winklers-llc.com`; Cloudflare version
  `f8e91825-6b9f-4db6-aadf-7cd97388c438`.
- Live `https://cursiv.us/start` changed from U105 before deployment to U106 afterward. At
  `2026-10-27T00:45:50Z` (October 26 in the owner's timezone), it returned HTTP 200 and matched the
  published source bytes. Both versioned installer links and the exact Windows hash above were present.
  The live owner manifest returned HTTP 200 and matched the independently verified signed manifest.
- Machine-readable [publication receipt](../bench/results/U106-publication.json).

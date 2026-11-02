# U117 release verification — November 2, 2026

[U117 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U117)
with 11 assets. All 11 anonymous public downloads returned 200 and matched the staged
SHA-256 values and GitHub digests. All 8 platform signatures verified on the downloaded
copies under the existing pinned owner identity. Owner signatures are detached Ed25519
signatures; Windows CA signing and Mac notarization are not claimed.

Source [PR83](https://github.com/Cursiv-Local/Cursiv/pull/83) merged as
`61754700e2c088830e56ee197f4ae020d1c51f2e`, the immutable tag source. It carries the fixes merged in
[PR81](https://github.com/Cursiv-Local/Cursiv/pull/81) and [PR82](https://github.com/Cursiv-Local/Cursiv/pull/82).
All 17 PR checks and exact-main [CI 41535691908](https://github.com/Cursiv-Local/Cursiv/actions/runs/41535691908)
passed. The PR's first `test (macos-latest)` job reached its 15-minute timeout and was canceled; its rerun
passed, as did the push run on the same commit. A pattern scan of the 36 files changed since U116 found
0 secrets. No private keys, API keys or owner records are in the release.

Full isolated Windows suite: **3,060 passed, 16 skipped, 19 passing subtests**.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows | 3060 | 16 | 19 |
| macOS | 3043 | 33 | 19 |
| Linux | 3042 | 34 | 19 |
| ARM64 headless source | 114 | 0 | 0 |

ARM64 results are existing headless source tests, not Raspberry Pi hardware validation.
No real AI-provider request or model inference was performed. Before the release PR, the strict
offline suite on the owner's Windows PC passed 2,954 tests with 33 skipped and 0 blocked operations.

[Windows build 41537433355](https://github.com/Cursiv-Local/Cursiv/actions/runs/41537433355)
and [Mac build 41537438197](https://github.com/Cursiv-Local/Cursiv/actions/runs/41537438197)
passed. Windows frozen and portable USB-layout receipts and the Mac frozen receipt all
say ALL PASSED. Both provenance files name the tagged commit. Versioned and latest bytes
match per platform. All 3 signer source hashes matched their pinned manifest. The protected
private seed was used in place and never copied or printed. The redundant release-triggered
Mac run 41539488944 was canceled, per the runbook.

| Package | Bytes | SHA-256 |
|---|---:|---|
| Windows installer | 58050426 | `154143ab04193cc3b5fc247e0b9fe424471ff6b15660ad4cdacb35e080256b49` |
| Mac ARM64 DMG | 71145628 | `dc13e7f2f4581b1f80940fbc57cf2cfa1a4d8c92cc5f51e61614613e79b194f1` |

The published U116 release notes were also updated with the correction already in
[RELEASE-U116.md](RELEASE-U116.md).

## Limits

Automated checks used mocked providers only. The owner has not re-run the U116 prompt set on
U117, so real-model behaviour is not established here. The intermittent Windows "Access is denied"
when a conversation save replaces its file is not fixed. This record adds no accuracy result.

## Public proof

- [Tagged package and signature receipt](../bench/results/U117-release-verification.json)
- [Anonymous public downloads](../bench/results/U117-public-downloads.json)
- [Published GitHub asset digests](../bench/results/U117-public-release.json)
- [Exact-main Windows](../bench/results/U117-main-windows.xml), [Mac](../bench/results/U117-main-mac.xml), [Linux](../bench/results/U117-main-linux.xml), [ARM64](../bench/results/U117-main-arm64.xml)

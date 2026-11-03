# U118 release verification — November 2, 2026

[U118 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U118)
with 11 assets. All 11 anonymous public downloads returned 200 and matched the staged
SHA-256 values and GitHub digests. All 8 platform signatures verified on the downloaded
copies under the existing pinned owner identity. Owner signatures are detached Ed25519
signatures; Windows CA signing and Mac notarization are not claimed.

Source [PR86](https://github.com/Cursiv-Local/Cursiv/pull/86) merged as
`72c2ea7304bdf1099a6b730906a1c5d49524061f`, the immutable tag source. It carries the fix merged in
[PR85](https://github.com/Cursiv-Local/Cursiv/pull/85). All 17 PR checks passed. On exact-main
[CI 41572240157](https://github.com/Cursiv-Local/Cursiv/actions/runs/41572240157), `test-linux` first failed
`test_station_server.py::test_concurrent_writes_stay_one_unbroken_chain`: one of 20 simultaneous local
requests got a connection reset. That Field Station code is not changed by this release; the rerun passed,
and every other job passed on the first attempt. A pattern scan of the 28 files changed since U117 found
0 secrets. No private keys, API keys or owner records are in the release.

Full isolated Windows suite: **3,064 passed, 16 skipped, 19 passing subtests**.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows | 3064 | 16 | 19 |
| macOS | 3045 | 35 | 19 |
| Linux | 3044 | 36 | 19 |
| ARM64 headless source | 114 | 0 | 0 |

The two new Windows-only file-lock tests account for the two extra macOS and Linux skips.
ARM64 results are existing headless source tests, not Raspberry Pi hardware validation.
No real AI-provider request or model inference was performed. Before the release PR, the strict
offline suite on the owner's Windows PC passed 2,958 tests with 33 skipped and 0 blocked operations.

[Windows build 41573935083](https://github.com/Cursiv-Local/Cursiv/actions/runs/41573935083)
and [Mac build 41573938280](https://github.com/Cursiv-Local/Cursiv/actions/runs/41573938280)
passed. Windows frozen and portable USB-layout receipts and the Mac frozen receipt all
say ALL PASSED. Both provenance files name the tagged commit. Versioned and latest bytes
match per platform. All 3 signer source hashes matched their pinned manifest. The protected
private seed was used in place and never copied or printed. The redundant release-triggered
Mac run 41575299345 was canceled, per the runbook.

| Package | Bytes | SHA-256 |
|---|---:|---|
| Windows installer | 58054538 | `02f4f2786a946b10dfefdd60614421f11c66572e667de58d3e8528fcfbff179d` |
| Mac ARM64 DMG | 70685070 | `9119924b27392f1a4a3209a65532dbe87b6f3874ba98e253656e3951939015d7` |

## Limits

Automated checks used mocked providers only. The owner has not re-run the prompt set on U117 or
U118, so real-model behaviour is not established here. This record adds no accuracy result.

## Public proof

- [Tagged package and signature receipt](../bench/results/U118-release-verification.json)
- [Anonymous public downloads](../bench/results/U118-public-downloads.json)
- [Published GitHub asset digests](../bench/results/U118-public-release.json)
- [Exact-main Windows](../bench/results/U118-main-windows.xml), [Mac](../bench/results/U118-main-mac.xml), [Linux](../bench/results/U118-main-linux.xml), [ARM64](../bench/results/U118-main-arm64.xml)

# U116 release verification — October 31, 2026

[U116 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U116)
with 11 assets. All 11 anonymous public downloads returned 200 and matched the staged
SHA-256 values and GitHub digests. All 8 platform signatures verified on the downloaded
copies under the existing pinned owner identity. Owner signatures are detached Ed25519
signatures; Windows CA signing and Mac notarization are not claimed.

Source [PR77](https://github.com/Cursiv-Local/Cursiv/pull/77) merged as
`9e5b672045446ce7c4a147071e3368751f009445`, the immutable tag source. All 17 PR checks
and exact-main [CI 41223923153](https://github.com/Cursiv-Local/Cursiv/actions/runs/41223923153)
passed. A pattern scan of the 40 files changed since U115 found 0 secrets. This is a
narrower scan than U115's 83-path source scan. No private keys, API keys or owner records
are in the release.

Full isolated Windows suite: **3,016 passed, 16 skipped, 19 passing subtests**.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows | 3016 | 16 | 19 |
| macOS | 2999 | 33 | 19 |
| Linux | 2998 | 34 | 19 |
| ARM64 headless source | 114 | 0 | 0 |

ARM64 results are existing headless source tests, not Raspberry Pi hardware validation.
No real AI-provider request or model inference was performed.

[Windows build 41234564506](https://github.com/Cursiv-Local/Cursiv/actions/runs/41234564506)
and [Mac build 41233420923](https://github.com/Cursiv-Local/Cursiv/actions/runs/41233420923)
passed. Windows frozen and portable USB-layout receipts and the Mac frozen receipt all
say ALL PASSED. Both provenance files name the tagged commit. Their lock hashes are the
LF and CRLF forms of the same `requirements-release.lock` at that commit. Versioned and
latest bytes match per platform. All 3 signer source hashes matched their pinned manifest.
The protected private seed was used in place and never copied or printed. The redundant
release-triggered Mac run 41235224193 was canceled, per the runbook.

The first Windows build, [41233418493](https://github.com/Cursiv-Local/Cursiv/actions/runs/41233418493),
was stopped by the release gate before it built anything. A branch pushed at the same commit
(`claude/probe-ref-u116`) had started a second `tests` run, and the gate correctly refused
while that run's `test (windows-latest)` was still in progress. That job then passed, and the
same tag was rebuilt unchanged.

| Package | Bytes | SHA-256 |
|---|---:|---|
| Windows installer | 58054575 | `ed952facbc051f3701cfc98904d0f2378f71e9464a68e0c13297a6bf8613d6fe` |
| Mac ARM64 DMG | 72156398 | `a9080905176093f922e3fb699cad8916592e58d55624be53691580d2c265c695` |

## Limits

Automated checks used mocked providers only. The owner manual tests in
[the audit handoff](U116-AUDIT-HANDOFF.md) (section 8) are not recorded as run, so real-model
behaviour and the Windows and Mac look of the chat bar are not established here. This record
adds no accuracy result.

## Public proof

- [Tagged package and signature receipt](../bench/results/U116-release-verification.json)
- [Anonymous public downloads](../bench/results/U116-public-downloads.json)
- [Published GitHub asset digests](../bench/results/U116-public-release.json)
- [Exact-main Windows](../bench/results/U116-main-windows.xml), [Mac](../bench/results/U116-main-mac.xml), [Linux](../bench/results/U116-main-linux.xml), [ARM64](../bench/results/U116-main-arm64.xml)

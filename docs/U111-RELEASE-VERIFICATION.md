# U111 release verification — October 30, 2026

[U111 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U111).
Source PR63 merged as `932d95d06578c73621d32565346b460fd8d26762`, the immutable tag source.
Exact-main [CI41004166516](https://github.com/Cursiv-Local/Cursiv/actions/runs/41004166516)
passed. The release helper reran the 63 workspace checks; the commit USB hook passed45.
The public-source secret scan found zero credentials. Owner-excluded files were not read or staged.

| Source platform | Regular passed | Skipped | Passing subtests |
|---|---:|---:|---:|
| windows | 2736 | 15 | 19 |
| mac | 2719 | 32 | 19 |
| linux | 2718 | 33 | 19 |
| arm64 | 114 | 0 | 0 |

Windows frozen startup and USB-layout selftests: ALL PASSED. Native Mac tagged
[build41006449625](https://github.com/Cursiv-Local/Cursiv/actions/runs/41006449625)
and its frozen selftest passed. Both provenance files name the tag commit. All eight
platform assets were signed with the existing pinned owner identity, after all
three trusted signer hashes matched. The private key was neither copied nor replaced.
All11 uploaded GitHub asset digests match the local verified bytes.
The redundant release-event Mac run41012341037 was canceled per the runbook.

[Machine-readable verification](../bench/results/U111-release-verification.json),
[public asset record](../bench/results/U111-public-release.json),
[source/model validation and limits](U111-VALIDATION.md).
Detached owner signatures are not Windows CA signatures or Mac notarization.
Reconstructed local-model tests do not establish a new general accuracy score.
No live cloud-account inference was tested. Website promotion is recorded separately
with U112; the existing U110 homepage remains until that deployment succeeds.

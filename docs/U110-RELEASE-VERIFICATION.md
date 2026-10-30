# U110 release verification — October 29, 2026

[U110 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U110)
with 11 assets. Every published GitHub digest matched the staged local bytes, and all
8 platform assets carry owner signatures verified against the existing pinned identity.
Website/evidence PR61 merged as `070c5e4`. A later read-only reconciliation confirmed
the public homepage, `/start` and U110 owner manifest all return200 with U110 content;
[readback receipt](../bench/results/U110-publication-readback.json). This is a limited
three-URL publication check, not a new deployment or a repeat of every historical SEO probe.
The completed [post-U109 worksheet validation](U109-POSTRELEASE-VALIDATION.md) records
the full source/USB/workspace gates, real local-model regression results and limits.

## Source and protected gates

- Source PR60: https://github.com/Cursiv-Local/Cursiv/pull/60 (17 checks passed).
  Commits: `43f7efb` natural-language self-inspection routing, `d0f5caa` U109
  post-release repairs, `1fb6f76` version preparation.
- Tag `v3.14-U110`: `c3ca2c083622bd231dd2053d07ee394845fca08f` (the PR60 merge commit),
  created by `scripts/prepare_release.py` after main CI and the 63 workspace checks passed.
- Main CI40964954070 passed all 9 jobs:
  https://github.com/Cursiv-Local/Cursiv/actions/runs/40964954070.
- Each source commit's USB hook passed 45 cases. No tag replacement or gate bypass was used.

Full isolated Windows suite: **2,664 passed, 15 skipped, 19 subtests passed**.
The same count came from a clean local checkout of `1fb6f76` (pytest exit 0) and from
main CI. Regular counts exclude the 19 subtests, which are counted separately.

| Main source suite (CI40964954070) | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows | 2,664 | 15 | 19 |
| Mac | 2,647 | 32 | 19 |
| Linux | 2,646 | 33 | 19 |
| Hosted ARM64 engine/station checks | 114 | 0 | 0 |

JUnit receipts: `bench/results/U110-main-{windows,mac,linux,arm64}.xml`.

## Behavior and limits

- New `tests/test_u110_self_inspection_routing.py` (20 cases): four plain-language
  self-inspection requests, including one preceded by an instruction, route to the
  `introspection` topic; evidence starts with `self_inspection.resolve` and `prepare`,
  includes the `_chat_inner` handoff, and excludes `file_access.py`; unsupported citations
  still fail the unchanged evidence checker; ordinary chat, user repositories, fiction,
  safety wording, explicit commands and "do not read files" turns keep their routes.
- U109 post-release repairs and their measurements: [U109-POSTRELEASE-VALIDATION](U109-POSTRELEASE-VALIDATION.md).
- No live local-model explanation was scored for U110. Function lookup remains
  keyword-based, and a model's explanation of checked source is an inference, not a
  runtime trace. No new 158-case model accuracy result is claimed.

## Tagged native packages and owner authentication

- Windows: built from the tag by `scripts/build_release.py` in the hash-locked
  environment. Frozen self-test and USB-layout portable start: ALL PASSED
  (`bench/results/U110-windows-frozen-selftest.txt`, `U110-windows-portable-selftest.txt`).
- Mac: workflow run 40966439590 from the tag
  (https://github.com/Cursiv-Local/Cursiv/actions/runs/40966439590). Frozen self-test:
  ALL PASSED (`bench/results/U110-mac-frozen-selftest.txt`). The automatic
  release-event Mac run 40968159419 was cancelled as the runbook requires.
- Both provenance files name `c3ca2c083622bd231dd2053d07ee394845fca08f`.
- Signer hashes matched `trusted-tool-manifest.json` before signing; the private key was
  not copied. Key `f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
  Manifest `owner-release.json` SHA-256
  `7f30a439683022f73b933d7ff7ae3c69a5ab5140b68a67b0365aa4bb84e0cfba`, served as
  `website/assets/cursiv-owner-release-U110.json`.

| Asset | Bytes | SHA-256 |
|---|---:|---|
| Cursiv-Setup-3.14-U110.exe / Cursiv-Setup-latest.exe | 57,539,949 | `aabab84e23bf014d5f78977c7274143893ac8ec5437b174c3be144d9fc7c8ca0` |
| Cursiv-3.14-U110-mac-arm64.dmg / Cursiv-mac-latest.dmg | 72,015,920 | `8c7c945522a11e19bf0139210e7abb87b6c6edc16d873178153175fdf7dafdfc` |
| SHA256SUMS.txt | 185 | `0c5ef00251731043fe8218b7b36d47ff5d82fdcd20c100fddc6f0ac856d4783d` |
| SHA256SUMS-mac.txt | 185 | `5812308f5cf488717e0236ecea2e3f80d590ab0921bac83b3649a1b8b688e65b` |
| provenance-3.14-U110.json | 1,798 | `944419ab90eae4c157d8ab54a3ad30e25adfb5ce4cc518376de154d975f0b79b` |
| provenance-mac.json | 1,758 | `0cfdda9ea7461ceb8e514490a2ba3f3e7d2f136b3490a2a023ff068bb4825c7d` |
| owner-release.json | 1,620 | `7f30a439683022f73b933d7ff7ae3c69a5ab5140b68a67b0365aa4bb84e0cfba` |
| cursiv-owner-release-key.json | 221 | `40b2827d01ce3a50a5b7769f2818c638e6d52045716f6da0d427c5a2e4615c01` |

Machine-readable record: `bench/results/U110-release-verification.json`.
Windows CA publisher signing and Mac notarization remain pending, as for U109.

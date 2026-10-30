# U113 release verification — October 30, 2026

[U113 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U113) with eleven assets. All eleven anonymous downloads match the staged bytes and GitHub digests; all eight platform signatures verify against the existing pinned owner identity.

Source [PR68](https://github.com/Cursiv-Local/Cursiv/pull/68) merged as `bd11f925df7007e1641fd3b35ffd0ce9dad0a22d`, the immutable tag source. Every source PR check and exact-main [CI41049312518](https://github.com/Cursiv-Local/Cursiv/actions/runs/41049312518) passed. The normal commit hook passed45 USB tests and the tag helper passed63 workspace checks. The public candidate secret scan found zero credentials; owner-excluded files, station code, private keys and owner data were not committed.

Full isolated Windows suite: **2,871 passed, 15 skipped, 19 passing subtests**, on the exact-main hosted runner.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| windows | 2871 | 15 | 19 |
| mac | 2854 | 32 | 19 |
| linux | 2853 | 33 | 19 |
| arm64 | 114 | 0 | 0 |

Windows tagged frozen and portable USB-layout selftests: ALL PASSED. Native Mac [build41050565957](https://github.com/Cursiv-Local/Cursiv/actions/runs/41050565957) and frozen selftest: ALL PASSED. Both provenance files identify the immutable tag; dependency-lock hashes match exact Git bytes or full LF/CRLF checkout conversion. Provenance asset sizes and hashes were checked before signing. All three independently installed signer hashes matched their pinned manifest. The private key was not copied or replaced.

## Behavior and limits

Read-only inspection survives no-retention wording while explicit access denials remain enforced. Source packets are bound to the current question/history/policy. Known core maps use checked static declarations and AST edges. Exact selected model, offline and consent gates apply to permitted model explanations; no cloud failure substitutes Ollama. Optional diagnostics are bounded and redacted, in memory only.

Frozen reconstructed cases improved authorized inspection4/5→5/5, software emergency false positives2→0, privacy false positives2→0 and reference-claim cases3/8→8/8. Real emergencies, genuine absolute guarantees and unsupported current-answer provenance still warn. [Measurements and full limits](SELF-INSPECTION-REVIEW.md).

Original transcripts were unavailable. Real offline Qwen3 4B probes ran in disposable stores; cloud parity uses synthetic APIs, with no live cloud-account success claimed. Static maps are not runtime execution or complete codebase understanding. Free-form narration remains variable. Existing notebook confirmation, workspace/offline boundaries and opted-in USB key export remain. Detached signatures are separate from Windows CA signing and Mac notarization.

## Public proof

- [Exact-main and package verification](../bench/results/U113-release-verification.json)
- [Anonymous downloads and signatures](../bench/results/U113-public-downloads.json)
- [Published GitHub asset digests](../bench/results/U113-public-release.json)
- [Tag dependency-lock and asset verification](../bench/results/U113-lock-verification.json)
- [Source secret scan](../bench/results/U113-source-secret-scan.json)

Website deployment is verified separately by its publication receipt; package checks alone do not establish deployment.

## Verified website publication

Website/evidence [PR69](https://github.com/Cursiv-Local/Cursiv/pull/69) merged as `f8d209f855bcff2d2afb1cf9ae29440016818f9f` after all19 checks passed. Cloudflare deployment `7946b4d2-7cc0-418b-833c-6a730f62930b` moved the public site from U112 to U113. All41 checks passed over20 public pages: exact deployed bytes, release links/hashes, signed manifest, icon MIME types, crawler user-agent access, retained intentional exclusions and canonical handling. [Production readback](../bench/results/U113-publication.json); [protected website checks](../bench/results/U113-website-protected-checks.json).

Manual discovery checks remain manual. User-agent probes do not establish verified Google-IP traffic or dashboard WAF policy. No private API endpoint was queried and no production credential or security rule was changed. Root README/TECH release edits now use focused documentation CI; application, unknown, rename and forced-push scopes retain their full-check boundaries.

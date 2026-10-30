# U112 release verification — October 30, 2026

[U112 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U112)
with eleven assets. All eleven anonymous downloads matched their local bytes and GitHub digests;
all eight platform signatures verified against the existing pinned owner identity.

Source PR65 merged as `fee19dddc2d9afdcf56b1fe5c749051bf22117b7`, the immutable tag source.
All17 PR checks and exact-main [CI41016350564](https://github.com/Cursiv-Local/Cursiv/actions/runs/41016350564)
passed. The source commit USB hook passed45; the tag helper reran63 workspace checks.
PR64 was superseded to separate post-build website evidence; no check was weakened or bypassed.
The reviewed public delta passed gitleaks8.30.1 with zero findings. No owner-excluded files,
station code, API credentials or owner private keys were committed.

Full isolated Windows suite: **2,834 passed, 15 skipped, 19 passing subtests**, on the exact-main hosted Windows runner.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| windows | 2834 | 15 | 19 |
| mac | 2817 | 32 | 19 |
| linux | 2816 | 33 | 19 |
| arm64 | 114 | 0 | 0 |

Windows tagged frozen selftest and portable USB-layout selftest: ALL PASSED.
Native Mac [build41017558622](https://github.com/Cursiv-Local/Cursiv/actions/runs/41017558622)
and frozen selftest: ALL PASSED. Both native provenance files identify the immutable tag;
the lock hashes match exact Git bytes or complete LF/CRLF checkout conversion.
All three trusted signer hashes matched before signing. The private key was not copied or replaced.

## Behavior and limits

Every provider remains visible; model inventories distinguish live, cached, catalog and manual IDs.
Manual requests preserve the exact provider/model and never fall back. Cloud automatic is an opt-in;
offline restrictions precede authentication errors. New credentials use secure OS storage or a
session-only fallback. The separately opted-in readable USB key export is retained by owner request.
Inference-only retry preserves failed context without rerunning notebook/file/tool dispatch.

Real offline Qwen3 4B transport and full-chat smoke passed in disposable stores.
Cloud protocols and consent boundaries were tested with synthetic adapters; no live cloud-account
inference or actual model download/deletion was performed. macOS Keychain with an owner's actual
account remains unverified. The comparison engine is prepared; the desktop side-by-side view is deferred.
These checks are not a new model-accuracy score. Detached owner signatures are not Windows CA signing
or Mac notarization. Later self-inspection worksheet changes are published separately in U113.

## Public proof

- [Machine-readable package verification](../bench/results/U112-release-verification.json)
- [Anonymous download/readback](../bench/results/U112-public-downloads.json)
- [Published asset digests](../bench/results/U112-public-release.json)
- [Exact dependency locks](../bench/results/U111-U112-lock-verification.json)
- [Scoped secret scan](../bench/results/U112-secret-scan.json)

[Provider handoff](PROVIDER-MANAGER-HANDOFF.md) and [setup guide](AI-PROVIDERS.md).
Website deployment is verified separately by the publication receipt; these package checks alone do not establish deployment.

## Verified website publication

Website/evidence PR66 merged as `2cc8039632805dfb69c27f22856c26aef9ff1d92`. Cloudflare deployment `720a9dd4-69f1-4bab-8255-33a7a6eb5433` moved the public site from U110 to U112. All41 checks passed over20 public pages, release links/hashes, both signed manifests, icons, crawler user-agent probes, exclusions and canonicals: [production readback](../bench/results/U111-U112-publication.json). Manual discovery checks remain manual. User-agent probes do not establish verified Google-IP traffic or dashboard WAF policy. No private API endpoint was queried.

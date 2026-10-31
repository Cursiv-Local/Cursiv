# U115 release verification — October 31, 2026

[U115 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U115)
with11 assets. All11 anonymous public downloads returned200 and matched staged
SHA-256 values and GitHub digests; all8 platform signatures verified under the
existing pinned owner identity. Owner signatures are detached Ed25519 signatures;
Windows CA signing and Mac notarization are not claimed. Website publication is
explicitly deferred by the owner.

Source [PR75](https://github.com/Cursiv-Local/Cursiv/pull/75) merged as
`523f0175c5848b36a5065f4ff10165c5dfc65ff7`, the immutable tag source.
All17 protected PR checks and exact-main
[CI41170359384](https://github.com/Cursiv-Local/Cursiv/actions/runs/41170359384)
passed. The guarded commit hook passed45 USB tests; the reviewed tag helper passed63
guarded workspace tests. The final source scan found0 secrets across83 public paths;
the merged source tree matches that scanned candidate. No API/private keys, owner
records, excluded files or Station implementation changes were committed.

Full isolated Windows suite: **2,990 passed, 16 skipped, 19 passing subtests**.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| Windows |2990|16|19|
| macOS |2973|33|19|
| Linux |2972|34|19|
| ARM64 headless source |114|0|0|

Normal hosted release CI was explicitly authorized. ARM64 results are existing
headless source tests, not Raspberry Pi hardware validation. No real AI-provider
request or model inference was performed.

[Windows build41171190258](https://github.com/Cursiv-Local/Cursiv/actions/runs/41171190258)
and [Mac build41171192335](https://github.com/Cursiv-Local/Cursiv/actions/runs/41171192335)
passed. Windows frozen and portable USB-layout receipts and the Mac frozen receipt
all say ALL PASSED. Both provenance files name the immutable source commit and
match the Git dependency lock bytes or complete LF/CRLF conversion; pypdf remains
locked at6.21.4. Versioned/latest bytes match per platform. All3 independent signer
source hashes matched their pinned manifest. The existing protected private seed
was used in place and never copied or printed. The redundant release-triggered Mac
run41172357909 was canceled after the verified manual build, per the runbook.

| Package | Bytes | SHA-256 |
|---|---:|---|
| Windows installer |58042186|`76d2796c395f4bf99ba3243c13aa5bbb861c8102a31a080fae00309228677c75`|
| Mac ARM64 DMG |70695709|`24539a0694bd3e40490433ee8a2bd28ac7df3526e379efbcedcd5266cafb0b0a`|

## Behavior and limits

Stop releases the visible input promptly, preserves displayed partial text and
creates a bounded checkpoint through the existing conversation persistence boundary.
Late canceled events cannot enter another turn. Resume supports unrelated turns,
multiple paused tasks and restart recovery. It uses existing exact-provider,
privacy and offline gates, remains text-only and cannot replay notebook/tools/writes.
An already-started atomic write may finish safely. No checkpoint planning, summary,
embedding or personality inference call was added.

Optional Professional/Playful/Sassy preferences, acknowledgment frequency and
verbosity preserve existing defaults. Sensitive-context humor suppression and
scoped casual-conversation calibration checks retain source/action verification,
medical/scientific caution and permissions. The removed Guardian service was not
restored. [User guide](INTERRUPT-CONTINUITY.md), [development and manual tests](U115-HANDOFF.md).

Separate local strict validation passed2884 tests,33 skips and19 subtests with0
unexpected guard operations;60 new regression cases cover continuity, synthetic
Ollama/OpenAI/Groq dispatch, personality/checkers and performance. This Python guard
is not an OS-wide firewall. Earlier diagnostic, expected-failure and aborted runs
are preserved and do not count as clean readiness evidence.

In50 synthetic offscreen cycles, Stop returned with input enabled at median6.44145ms,
p9514.1612ms; checkpoint median0.0326ms, resume preparation0.0588ms. The frozen U114
handler returned sooner but retained input lock; no numerical end-user speedup is
claimed. Sample resume JSON/full instruction:629/1229 UTF-8 bytes, not actual provider
tokens. Real model response quality, server cancellation, native Qt memory and
long-history storage latency remain manual tests. An uncancellable connection may
retain the serialized inference slot until return/timeout. No local dependencies or
models were downloaded. Existing Qwen workflows, notebook confirmations, offline
enforcement, workspace restrictions and separately opted-in USB key export remain.

The first hosted source run exposed a fresh-process test fixture missing launcher
imports. The test-only follow-up explicitly establishes child import paths and
removes inherited application PYTHONPATH; production behavior was unchanged. All
protected checks and exact-main suites then passed. No CI gate was bypassed.

## Public proof

- [Tagged package/signature receipt](../bench/results/U115-release-verification.json)
- [Anonymous public downloads and8 signatures](../bench/results/U115-public-downloads.json)
- [Published GitHub asset digests](../bench/results/U115-public-release.json)
- [Exact-main Windows](../bench/results/U115-main-windows.xml), [Mac](../bench/results/U115-main-mac.xml), [Linux](../bench/results/U115-main-linux.xml), [ARM64](../bench/results/U115-main-arm64.xml)
- [Source secret scan](../bench/results/U115-source-secret-scan.json), [protected source checks](../bench/results/U115-protected-source-checks.json)
- [Strict development validation](../bench/results/U115-validation-summary.json)

Release evidence is recorded after the immutable application tag without moving it
or changing production code. The original dirty owner checkout remains untouched.
No website files, Cloudflare settings or production credentials were changed, and
no website deployment was performed.

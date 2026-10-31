# U114 release verification — October 30, 2026

[U114 is published](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U114) with 11 assets. All11 anonymous downloads return200 and match their staged SHA-256 and GitHub digests; all 8 platform signatures verify under the existing pinned owner identity. Windows CA signing and Mac notarization remain separate, pending checks.

Source [PR71](https://github.com/Cursiv-Local/Cursiv/pull/71) merged as `7e6150a9eb11b8ff0daac45c167a82458ab714f2`, the immutable tag source. All17 PR checks and exact-main [CI41149185226](https://github.com/Cursiv-Local/Cursiv/actions/runs/41149185226) passed. The guarded commit hook passed 45 USB tests; the reviewed tag helper passed 63 guarded workspace tests. The source scan found0 secrets across 85 public changed paths; the tag's application tree matches that scanned candidate. No API/private keys, owner data, excluded files or station implementation changes were committed.

Full isolated Windows suite: **2,930 passed, 16 skipped, 19 passing subtests**.

| Source platform | Regular passed | Skipped | Additional passing subtests |
|---|---:|---:|---:|
| windows |2930|16|19|
| mac |2913|33|19|
| linux |2912|34|19|
| arm64 |114|0|0|

Normal hosted release CI was explicitly authorized by the owner. ARM64 results are existing headless source tests, not Raspberry Pi hardware validation; the Station implementation is unchanged.

[Windows build41151029995](https://github.com/Cursiv-Local/Cursiv/actions/runs/41151029995) and [Mac build41150305222](https://github.com/Cursiv-Local/Cursiv/actions/runs/41150305222) passed. Windows frozen and portable USB-layout receipts, and the Mac frozen receipt, all say ALL PASSED. Both provenance files name the immutable tag and match the Git lock bytes or full LF/CRLF conversion; both contain pypdf 6.21.4. Versioned/latest installer bytes are identical per platform. Asset sizes/hashes were checked before signing. All3 independent signer source hashes matched their pinned manifest; the protected private seed was not copied or changed.

The first hosted Windows build completed its compile and both self-tests, but its receipt-copy step used `selftest.txt` instead of the builder's `frozen-selftest.txt`. [PR72](https://github.com/Cursiv-Local/Cursiv/pull/72) corrects that one workflow line, with protected CI. The successful Windows workflow definition is `2e7a775beaf7b6ecf72bce496b1219f68f4cb54a`; it checked out and built the unchanged application tag `7e6150a`. The tag was never moved. The duplicate release-triggered Mac run was canceled after the verified manual build; owner-signed assets are immutable.

## Behavior and limits

Exact public source file/function targets are read first and explained with current hash/AST witnesses and real citations, using unchanged permissions/budgets. Native source answers avoid model-prose postprocessing. Source locations, quoted/negated assertions, mathematical self-checks and explicitly supplied numeric inputs avoid the confirmed unrelated warnings. Genuine false execution/source claims and unsupported resource safety/runtime conclusions remain checked. Diagnostics separate permission, prepared tool lists, actual results, previews and completed/denied reads.

The removed Guardian scanner/service was not restored; [history and root causes](U113-GUARDIAN-AUDIT.md). Initial frozen source/interference cases4/14 became14/14. The additional worksheet initially passed 14/19; the final suite passed all 59 application regressions plus 7 guard controls. These are deterministic software checks, not a model accuracy score.

The separately guarded local audit passed 2,824 tests,33 skips and 19 subtests with 0 unexpected operations, including propagated guards for33 Python children. Six intentional deny probes stopped before OS/network/process execution. This was a Python-process guard, not an OS-wide firewall. Live/server/isolated-worker and Station modules were explicitly excluded locally. A fresh-child memory fixture initially tried optional local embedding discovery; the guard blocked it, and the corrected final run is the clean checkpoint. The expired temporary locked environment was not repaired or used for packaging. Local source checks used existing Python3.13; hosted native builds independently required the exact hash lock. No real AI-provider request or model inference was performed for this follow-up.

The initial release security gate reported7 advisories in pypdf 6.21.2. Its floor and hash lock were raised to [6.21.4](https://github.com/py-pdf/pypdf/releases/tag/6.21.4), using [official archive hashes](https://pypi.org/pypi/pypdf/6.21.4/json); hosted security and PDF regressions then passed. No advisory was suppressed and no package was installed locally.

Real OpenAI/Groq/Ollama response quality, latency and independent self-correction remain owner manual tests. Static source evidence is bounded, not observed runtime execution or complete codebase understanding. Existing notebook confirmations, workspace/offline/privacy gates, exact manual provider selection, Qwen support and separately opted-in USB key export remain. [Launch command and manual benchmark](U113-MANUAL-TEST-HANDOFF.md).

## Public proof

- [Tagged source/package/signature receipt](../bench/results/U114-release-verification.json)
- [Anonymous downloads and 8 signatures](../bench/results/U114-public-downloads.json)
- [Published GitHub asset digests](../bench/results/U114-public-release.json)
- [Exact-main Windows](../bench/results/U114-main-windows.xml), [Mac](../bench/results/U114-main-mac.xml), [Linux](../bench/results/U114-main-linux.xml), [ARM64](../bench/results/U114-main-arm64.xml)
- [Source secret scan](../bench/results/U114-source-secret-scan.json), [protected source checks](../bench/results/U114-protected-source-checks.json), [receipt-fix checks](../bench/results/U114-receipt-fix-protected-checks.json)
- [Strict-offline final result](../bench/results/U113-offline-final-summary.json), [PDF security pin](../bench/results/U114-pdf-security-pin.json)

## Verified website publication

[Website PR73](https://github.com/Cursiv-Local/Cursiv/pull/73) merged as `301f49c0d4209c0f74eb871885664f79566311c1`. All 19 protected publication checks passed, including 31 website tests and 6 aggregate-measurement tests; the required guarded commit hook passed 45 USB tests. Only public website/docs/evidence paths changed, so the full desktop suites were not repeated for publication.

Deployment `c6bf3635-abfe-47d2-8902-055654502a09` changed the live site from U113 to U114 using the exact merged public bundle and existing Cloudflare authentication. [All 41 public readback checks](../bench/results/U114-publication.json) passed across 20 canonical pages, robots/sitemap, official icon bytes and image types, the signed release manifest, retained noindex pages, apex/WWW/legacy redirects and query canonical handling. HTML bytes matched the deployed bundle with `no-transform`; the download page names the verified U114 installer hashes. [Protected website checks](../bench/results/U114-website-protected-checks.json).

Public-agent probes do not establish Google-IP traffic, WAF dashboard policy or search ranking. No production credentials were changed, no private API endpoints were queried, and no AI request or inference was performed. Manual discovery checks stay manual.

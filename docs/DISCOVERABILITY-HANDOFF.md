# Cursiv general-search discoverability handoff

Owner: Joshua Winkler. Started October 26, 2026, from main
`09f40c66b4023ffa1a050a74268a645199f5a0ca`, after the completed U106 release.

## Scope and boundaries

Prioritize discovery for free local AI, offline LLM applications and open-source AI assistants.
Preserve visual design, installer identity, private routes and application behavior. Use official
branding. This is a website update, not an app release. Station code, excluded local paths, secrets,
user records and unrelated profiles remain untouched. External submissions need owner approval.

## Completed

- Broad homepage/README identity, useful /local-ai, /compare and /documentation pages; sourced
  comparisons and precise offline/portable limits. Experimental llms.txt makes no ranking promises.
- Official-source ICO (16–256px frames), PNG96 and Apple180; stable root links in all 22 HTML files.
- Publisher allowlist, correct image content types, 17 canonical/indexable sitemap entries with
  source-history lastmod, linked valid SoftwareApplication/SoftwareSourceCode metadata.
- www DNS/TLS and canonical apex redirects work. Public HTTP pages now redirect to HTTPS;
  existing APIs and localhost previews retain their behavior.
- All ten exclusions supplied in the owner's screenshots are intentional and retained: six private
  /api/space/ endpoints blocked by robots; /notebook/ and /app noindex; removed /letters real404;
  /?x=2 canonical to /. No private API was queried. /remote/ and /admin/ blocks remain.
- GitHub description updated; seven broad local-AI topics added while preserving the original ten.
- Aggregate branded/non-branded/unknown CSV measurement helper, frozen queries, public before/after
  evidence and factual directory/reviewer drafts. Nothing submitted or paid.
- Owner chose **manual checklist only**. See DISCOVERY-MANUAL-CHECKLIST.md. No recurring discovery
  automation created; CI runs on code changes only.
- Verified May 17, 2026 V3 publication via GitHub's release API. Added sourced development history to
  homepage and documentation, distinguishing the early cloud orchestration from today's local focus.

## Production and verification

Initial PR #48 merged at `8568768fe6df384eba78594308ab2342e2eb808a` after all source and website
push/PR checks passed. First Cloudflare version: `d2d8a998-ce24-4dd8-9997-3ce77dc0953a`.
HTTP redirect correction `8abe5e667206e4480768cd8c4c8a8402a5207ec6` passed 31 website tests and
mandatory 45-test USB gate before deployment `e3aa350b-77ad-4c51-98fb-daf710590bda`.
History copy `efeffac1c6fde6e820a2d95734448f234e254360` is deployed as Cloudflare version
`a235ea1c-f00d-4639-b51c-39b2ad448295`, after 31 website tests and the mandatory 45-test USB gate.
Final public proof is complete on codex/discovery-publication-proof; normal PR checks remain for merge.

- 31 website tests and 6 measurement tests pass. Mandatory USB hook runs on each commit.
- Initial full production audit: 46 public probes, 45 final200, one intentional /letters404, no
  errors/challenges; 17 self-canonical indexable pages match deployed bytes. Three additional www
  favicon probes redirect to matching apex images. Public evidence: bench/results/discoverability-*.json
  and discovery-publication.json. The final history deployment's refreshed 46-probe audit also passed.
- Actual Schema.org live URL validator: 0 errors, 0 warnings, 2 top-level items.
- Authenticated Cloudflare view: Googlebot block toggle off, allowed traffic observed; no security
  settings changed. Actual Search Console live homepage test, October 26 at 10:08 PM local:
  URL is available to Google. Cached inspection also showed homepage already indexed.
- Desktop1280/mobile390 reviews passed; comparison table scrolls inside its wrapper. Live homepage
  screenshot: bench/results/discovery-home-live.jpg.
- Same-provider frozen queries: 0/10 non-branded result sets before and immediately after. Branded
  controls also absent. This is not Google rank or a cross-assistant recommendation evaluation.
- GitHub aggregate baseline:117 views/34 unique visitors, October12–25 UTC; not website organic traffic.
  Search Console's signed-in aggregate baseline was read; unshown query impressions stay unknown.
  Raw exports/account details/private dashboard images remain in ignored reports/.
- U106 tag remains `10b40d6d9bcce73102e22d5bcd3d0fca8ba60a4a`; signed installers and app/station
  code unchanged. No new tag, package release or database change.

## Remaining work and commands

Commit explicit public receipts, push and merge the normal PR after CI passes. Production/history
verification is complete. Current details live in ignored reports/discovery-state.json.
Local preview sessions54987/12013 stopped. No preview server remains from this work.
Do not re-run the applied one-off reports/update_discovery_html.py or final_discovery_adjustments.py.

Future owner-led work: comparable Search Console exports and manual engine/assistant checks;
owner-approved external listings and independent reviews. Google recrawl, icon selection, rankings
and recommendations remain external outcomes, not proven improvements.

See DISCOVERABILITY-REPORT.md for exact excluded URLs, sources, measurements and publication evidence.

## Agent-readiness screenshots

Reviewed the owner's agent-readiness checklist against official Cloudflare and A2A documentation.
robots/sitemap/crawler access are the relevant foundation already verified. Markdown negotiation is
optional and plan-dependent; no paid upgrade or blanket content conversion enabled. Content Signals
express reuse preferences, not ranking guarantees; training policy was not changed. API catalogs,
auth instructions, A2A/MCP cards, skills, WebMCP and outbound-agent identity need real corresponding
services. No private endpoint or fabricated integration was published to increase a checker score.

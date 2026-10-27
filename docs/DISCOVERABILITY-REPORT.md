# General-search discoverability, indexing and favicon audit

Started October 26, 2026, on source `09f40c66b4023ffa1a050a74268a645199f5a0ca`.
Status: published and production-verified; search/recommendation gains remain unproven.

## Objective

Help people discover Cursiv through searches for free local AI, offline LLM applications and open-source
AI assistants, without already knowing its name. The product identity is a free, open-source local AI
assistant distinguished by tamper-evident notebooks, offline document retrieval and portable Windows
workspaces. Research, technical work and careful recordkeeping remain important use cases.

The update preserves the existing visual system, installer URLs, U106 package identity, safety limits,
private route restrictions and application functionality. It does not create a new app release.

## Baseline and changes

The public HTTP baseline is retained in [discoverability-before.json](../bench/results/discoverability-before.json).
It contains 19 local HTML summaries and 46 public HTTP probes, including one clearly marked supplementary
pre-deployment probe for the newly authored documentation page. No private API was queried.

| Area | Observed before | Published and verified |
|---|---|---|
| Homepage | Field-research title/H1; local AI secondary | Broad local-AI title, description, social text, H1 and visible introduction |
| Category discovery | /local-ai returned 404 | Substantive local-AI guide with setup, offline use, documents, memory, records and limits |
| Application selection | /compare returned 404 | Sourced comparison of Cursiv, AnythingLLM, LM Studio, Jan and Open WebUI |
| Evidence directory | /documentation returned 404 | Crawlable capability/evidence index, linking public documentation and tagged tests |
| Existing useful pages | Offline, hardware, research and portable pages present | Existing URLs preserved; internal discovery links and precise portability wording |
| Root icons | ICO, PNG96 and Apple180 URLs all returned 404 | Exact derivatives of the official logo, stable links and explicit image content types |
| www host | HTTP and HTTPS requests failed DNS resolution | www custom domain, DNS/TLS and canonical redirects work in production |
| Sitemap | 14 canonical public pages | 17 entries; build rejects noindex/noncanonical pages; truthful lastmod from full source history |
| Structured data | codeRepository placed on SoftwareApplication | Linked SoftwareSourceCode entity carries codeRepository; no ratings, reviews or awards invented |
| AI reading guide | /llms.txt returned 404 | Concise experimental llms.txt with capabilities, sources and limitations |

All 17 indexable HTML pages returned 200, matched deployed source bytes and had self-canonical HTTPS
URLs without noindex. The main post-change audit had 46 public probes: 45 ended in 200, and removed
/letters correctly remained 404. Three additional www favicon probes redirected to matching apex
images. No request failed DNS/TLS or reported a Cloudflare challenge.

The existing 256px logo URL already returned a valid PNG, and Google crawler user-agent probes could
reach the homepage and that image. Missing root files are a concrete improvement opportunity, not proof
of why Google selected a globe. Google's choice of search icon remains external to this deployment.

## Exact Search Console exclusions: retain all ten

The owner supplied screenshots reporting 9 indexed pages and the following exclusions. Their totals
are owner-provided Google evidence, separate from this audit's HTTP and search-provider samples.

| Reported reason | Exact URL | Classification and verified behavior |
|---|---|---|
| robots.txt | https://cursiv.us/api/space/ask | Intentional private pairing/message endpoint; covered by /api/ |
| robots.txt | https://cursiv.us/api/space/join | Intentional private pairing/message endpoint; covered by /api/ |
| robots.txt | https://cursiv.us/api/space/messages?since= | Intentional private pairing/message endpoint; covered by /api/ |
| robots.txt | https://cursiv.us/api/space/create | Intentional private pairing/message endpoint; covered by /api/ |
| robots.txt | https://cursiv.us/api/space/image/ | Intentional private pairing/message endpoint; covered by /api/ |
| robots.txt | https://cursiv.us/api/space/pair-code | Intentional private pairing/message endpoint; covered by /api/ |
| noindex | https://cursiv.us/notebook/ | 200 with noindex,follow; interactive capture tool, not a product landing page |
| noindex | https://cursiv.us/app | 200 with noindex,follow; interactive photo tool, not the desktop product page |
| noindex | https://cursiv.us/letters | Removed page: real 404 with the missing-page noindex directive; keep removed |
| Alternate canonical | https://cursiv.us/?x=2 | 200 with canonical https://cursiv.us/; duplicate homepage, not a separate page to index |

Private endpoints were checked against the live robots policy locally, without sending requests to
them. /remote/ and /admin/ remain blocked too. Chat/profile tools and the 404 response keep their
intentional noindex directives. None of these exclusions belongs in the sitemap. No private pages are
made indexable to improve a coverage count.

Product, feature, installation and documentation landing pages are the intended search entry points.
Each sitemap page must contain one self-canonical HTTPS URL and be indexable. A canonical is a signal,
not a promise that Google will select or index that URL. See Google's
[robots guidance](https://developers.google.com/search/docs/crawling-indexing/robots/intro) and
[canonicalization guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls).

## Favicon implementation and access checks

Source: `launcher/resources/icons/cursiv-logo-source.png`, the existing official 400×400 artwork.
[Source fingerprint](../bench/discovery/icon-source.json) and the reproducible
`scripts/generate_web_icons.py` identify the exact source; no new logo or placeholder is introduced.

- `/favicon.ico`: real ICO frames at 16, 32, 48, 64, 96, 128 and 256px.
- `/favicon-96x96.png`: square 96×96 PNG.
- `/apple-touch-icon.png`: square 180×180 PNG.
- All 22 public HTML files declare the three stable root links. Existing visual branding remains intact.
- Publisher explicitly declares `image/vnd.microsoft.icon` and `image/png`, with the existing security
  and no-transform headers. Public robots policy permits these image paths and the homepage.

Google requires a crawlable homepage and favicon, a representative square icon and a stable URL.
The requested 96px image satisfies its size guidance. Visibility is not guaranteed, and processing can
take days or weeks after recrawl. These are eligibility changes, not a claim that the Google search
result already displays the logo. [Official favicon guidelines](https://developers.google.com/search/docs/appearance/favicon-in-search).

Browser/Googlebot/Googlebot-Image probes returned the actual icon images with correct content types,
dimensions and hashes matching the official-source derivatives. These probes alone do not prove
verified crawler identity. Separately, the authenticated Cloudflare AI Crawl Control view showed
Googlebot's block toggle off and allowed Googlebot traffic. The inspected security-rule view had no
explicit custom Googlebot block. No security settings, authentication or private-route protections changed.

Google's Search Console live homepage test, completed October 26 at **10:08 PM local time**, reported
**URL is available to Google**. This is separate from a user-agent probe; it does not establish that the
new icon is already selected for search results. The cached inspection also showed the homepage already
indexed. No indexing request or repeated submission was sent by this task.

## Broad intent coverage

| Search intent | Useful destination |
|---|---|
| Free local AI, local LLM applications, private/offline AI for Windows | /local-ai and the homepage |
| AnythingLLM alternatives, choosing an offline AI application | /compare |
| What works without internet; app versus model licensing | /open-source-offline-ai |
| AI for local documents and detailed notes | /local-ai, /documentation |
| Portable AI on a USB drive or external SSD | /portable-workspace |
| Hardware fit and model requirements | /local-ai-hardware-requirements |
| Notebook integrity and technical evidence | /documentation and linked source documents |

This uses a few distinct, useful pages rather than near-duplicate keyword landing pages. Comparison
claims come from each application's official docs/licenses and are dated. No cross-product performance
test, exclusive-feature claim, universal superiority or independent endorsement is asserted.

The homepage and documentation now link the original V3 release and current repository. GitHub's
public release API reports V3 published May 17, 2026, at 07:11:03 UTC. Its notes describe multi-model
orchestration, persistent memory and a local workspace coordinating cloud providers, with an Ollama
offline option. The history copy distinguishes those earlier capabilities from today's emphasis;
it does not imply today's notebook guarantees existed then or independently verify the old release.
[Original V3 release](https://github.com/joshua1993winkler-jpg/Cursiv/releases/tag/V3).

Google documents that its AI search features use the same foundational SEO practices and do not
require special AI files or schema. llms.txt is a separate experimental reading aid, not a ranking
switch. ai.json has community proposals, but no necessary consumer for this site was established;
the named ecp.json protocol/consumer was not identified. Neither speculative file is installed.
[Google AI features](https://developers.google.com/search/docs/appearance/ai-features) ·
[llms.txt proposal](https://llmstxt.org/) ·
[Archived multi-file proposal and consumer-support caveat](https://discoveryfiles.ai/specifications/).

## Measurement: discovery outcomes remain unproven

### Agent-readiness checklist supplied by the owner

The later screenshots concern agent integration as well as discovery. Their incomplete items are not
Google indexing errors. robots.txt, sitemap and crawler access already have production evidence here.
Optional Markdown negotiation may simplify extraction, but the current site already serves readable
static HTML. Cloudflare lists plan eligibility for its converter and supplies permissive reuse defaults
when no origin Content-Signal exists. No paid upgrade, converter switch or training-policy change was
made. Any future trial should cover only intended public content and verify HTML/Markdown caching,
canonical URLs, noindex/security headers and the existing no-transform publishing requirement.
[Cloudflare Markdown documentation](https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/).

Content Signals distinguish search indexing, real-time AI input and model training; they express
content-use preferences and do not replace access controls or establish search rankings. The owner's
discovery objective does not select a model-training policy. Existing restrictions remain intact.
[Cloudflare Content Signals guidance](https://developers.cloudflare.com/bots/additional-configurations/managed-robots-txt/).

API catalogs, auth.md/login instructions, OAuth discovery, A2A cards, skills indexes, MCP server cards,
WebMCP and outbound-agent authentication/discovery are conditional integration features. Cursiv's
public product site does not currently advertise supported external A2A/MCP services. Existing app/
pairing/demo endpoints do not establish those protocol capabilities. In particular an A2A card describes
a real agent's endpoint, skills and authentication; publishing a fictitious card would misrepresent the
site. No integration endpoints, private routes or credentials were exposed to improve a checklist score.
[A2A discovery specification](https://github.com/a2aproject/A2A/blob/main/docs/topics/agent-discovery.md).

[Frozen queries](../bench/discovery/queries.json) preserve the owner's ten non-branded examples and
separate branded/control queries. [Pre-change samples](../bench/results/discovery-search-before.json)
contain the exact returned URLs. Cursiv appeared in **0 of 10 non-branded result sets** from the available
web-search provider. The branded/control samples also did not return this site. This is not a Google
rank, a complete index check, or a contradiction of the owner's 9 Google-indexed pages.

No direct ChatGPT Search, Perplexity, Google AI Mode, Bing Copilot or Claude recommendation evaluation
has been completed. A search-enabled tool returning links is not equivalent to those products
recommending Cursiv. Do not report multi-platform recommendation coverage from these samples.

GitHub returned **117 repository views / 34 unique visitors**, October 12–25, 2026 UTC, and three
referring-domain rows. These short-window repository aggregates are not website visits or non-branded
search traffic. Raw traffic exports stay in ignored reports/, not published visitor data.

After the initial export-unavailable checkpoint, the owner's already-signed-in Search Console
performance report was found and read. Its aggregate baseline is retained privately in ignored
reports/discovery-search-console-before.json. The visible query table did not establish non-branded
exposure; impressions absent from it remain unknown. No raw queries, account details, visitor IPs or
private dashboard screenshots are published. A full performance export and comparable later-period
results remain unavailable. Cloudflare's existing aggregate dashboard was also inspected; its requests/
visits do not establish organic query intent.

No new analytics scripts, cookies, visitor IDs, raw query logs or database fields are added. Existing
anonymous download metrics and privacy choices are unchanged.

`scripts/search_discovery_report.py` accepts owner-exported single-range Queries CSV and optional
aggregate Referrer/Source CSV. It separates Cursiv/CursivAI brand tokens from non-branded and blank
unknown queries, sums actual clicks/impressions, computes weighted CTR/position and keeps missing data
unavailable. AI/search referrers are reported separately; a referrer cannot reveal hidden query intent.
Use comparable 28-day windows and keep exports private. Do not equate query-row totals with Google's
full totals when anonymized/low-volume queries are omitted.

Repeat the frozen non-branded queries on named engines and search-enabled assistants. Record date,
engine/model, returned URLs or full recommendation evidence, and whether citations support each claim.
Keep branded controls separate, retain failures and run each prompt once per planned checkpoint.
Immediate post-deployment absence is not evidence the implementation failed; crawling and independent
recommendations take time. Real success requires measured non-branded impressions, clicks/referrals
and credible external mentions over subsequent weeks.

The [immediate post-deployment sample](../bench/results/discovery-search-after.json) repeated the exact
queries using the same available provider. It remained **0/10 non-branded result sets**; separate
branded/control samples also did not return the product. No improved ranking or recommendation is
claimed. Follow the [manual checklist](DISCOVERY-MANUAL-CHECKLIST.md); the owner explicitly chose manual
checks, so no recurring discovery automation was created.

## Validation to date

- Public-site baseline: 46 HTTP probes; private API behavior never queried.
- Website build: successful. **31 website tests passed**, including the original 22.
- Aggregate measurement: **6 standard-library tests passed**, including unknown data, weighted rates
  and misleading referrer names. The tests are also collected by the normal source suite.
- New website CI runs the public build/checks on Node 24 LTS and the standard-library measurement tests.
- Desktop review: 1280px viewport, no horizontal page overflow. Narrow review: 390px viewport, no page
  overflow; mobile navigation opens/closes. The 760px comparison table scrolls inside its 335px wrapper.
- Signed U106 download URLs and installer hash remain unchanged; existing signature/download tests pass.

## Publication and remaining work

- Initial changes: [PR #48](https://github.com/Cursiv-Local/Cursiv/pull/48), merged at
  `8568768fe6df384eba78594308ab2342e2eb808a` after all seven source jobs and the new public-website job
  passed on push and PR. [Source CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/40434150190),
  [website CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/40434150175).
- Initial Cloudflare version: `d2d8a998-ce24-4dd8-9997-3ce77dc0953a`. The production check found a
  pre-existing public HTTP duplicate: it served 200 with an HTTPS canonical. A focused follow-up now
  redirects public HTTP pages to HTTPS while preserving existing APIs and localhost previews.
- Follow-up source: `8abe5e667206e4480768cd8c4c8a8402a5207ec6`, checked locally with 31 website tests
  and the mandatory 45-test USB gate before deployment. Redirect-fix Cloudflare version:
  `e3aa350b-77ad-4c51-98fb-daf710590bda`. The follow-up and this receipt use normal PR checks for merge.
  A Windows CRLF assumption in the llms.txt format test was corrected; valid LF/CRLF files pass.
- Sourced development-history copy: `efeffac1c6fde6e820a2d95734448f234e254360`, published after the
  same 31 website checks and mandatory 45-test USB gate. Current Cloudflare version:
  `a235ea1c-f00d-4639-b51c-39b2ad448295`. The final 46-probe audit was refreshed after this publication;
  all 17 canonical public pages match its deployed bytes. [History screenshot](../bench/results/discovery-history-live.jpg).
  Source integration and final CI are recorded in [PR #49](https://github.com/Cursiv-Local/Cursiv/pull/49).
- Final verification: [HTTP audit](../bench/results/discoverability-after.json) and
  [publication receipt](../bench/results/discovery-publication.json). www DNS/TLS, redirects, icon
  content types/dimensions, all sitemap entries and retained exclusions passed. HTTPS page bytes match
  the deployed source. [Live homepage screenshot](../bench/results/discovery-home-live.jpg).
- Schema.org's live URL validator reported **0 errors, 0 warnings**, with SoftwareApplication and
  WebSite as two top-level items; SoftwareSourceCode is linked within the graph.
  [Live validator](https://validator.schema.org/#url=https%3A%2F%2Fcursiv.us%2F). This validates vocabulary,
  not Google's rich-result eligibility or ranking.
- GitHub's description now leads with free, open-source local AI and its notebook/retrieval/portable
  features. Seven topics were added, preserving the original ten: offline-ai, local-llm, ai-assistant,
  document-retrieval, tamper-evident, portable-ai and private-ai.
- U106's tag/version, signed installer assets, model defaults and application/station code remain
  unchanged. No private records or database schema/data were modified.

Directory/review drafts are in [DISCOVERY-SUBMISSIONS](DISCOVERY-SUBMISSIONS.md); nothing has been sent.
Manual measurements and owner-approved external listings remain future work. Search Console's
recrawl/indexing and Google's eventual favicon selection remain external outcomes.

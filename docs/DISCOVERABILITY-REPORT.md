# General-search discoverability, indexing and favicon audit

Started October 26, 2026, on source `09f40c66b4023ffa1a050a74268a645199f5a0ca`.
Status: local implementation and checks complete; production publication and post-change measurements pending.

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

| Area | Observed before | Implemented locally; production outcome pending |
|---|---|---|
| Homepage | Field-research title/H1; local AI secondary | Broad local-AI title, description, social text, H1 and visible introduction |
| Category discovery | /local-ai returned 404 | Substantive local-AI guide with setup, offline use, documents, memory, records and limits |
| Application selection | /compare returned 404 | Sourced comparison of Cursiv, AnythingLLM, LM Studio, Jan and Open WebUI |
| Evidence directory | /documentation returned 404 | Crawlable capability/evidence index, linking public documentation and tagged tests |
| Existing useful pages | Offline, hardware, research and portable pages present | Existing URLs preserved; internal discovery links and precise portability wording |
| Root icons | ICO, PNG96 and Apple180 URLs all returned 404 | Exact derivatives of the official logo, stable links and explicit image content types |
| www host | HTTP and HTTPS requests failed DNS resolution | www custom domain and canonical redirects configured for deployment |
| Sitemap | 14 canonical public pages | 17 entries; build rejects noindex/noncanonical pages; truthful lastmod from full source history |
| Structured data | codeRepository placed on SoftwareApplication | Linked SoftwareSourceCode entity carries codeRepository; no ratings, reviews or awards invented |
| AI reading guide | /llms.txt returned 404 | Concise experimental llms.txt with capabilities, sources and limitations |

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

Browser/Googlebot/Googlebot-Image user-agent probes are observations of public HTTP behavior, not proof
of verified Google crawler traffic or a full inspection of Cloudflare dashboard rules. No bot security,
authentication or private-route protection is weakened. Record the actual post-deployment responses
before claiming production icon or www-host success.

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

Google documents that its AI search features use the same foundational SEO practices and do not
require special AI files or schema. llms.txt is a separate experimental reading aid, not a ranking
switch. ai.json has community proposals, but no necessary consumer for this site was established;
the named ecp.json protocol/consumer was not identified. Neither speculative file is installed.
[Google AI features](https://developers.google.com/search/docs/appearance/ai-features) ·
[llms.txt proposal](https://llmstxt.org/) ·
[Archived multi-file proposal and consumer-support caveat](https://discoveryfiles.ai/specifications/).

## Measurement: discovery outcomes remain unproven

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

Search Console performance clicks/impressions and site search/referral exports are **unavailable**;
coverage screenshots do not supply them. No new analytics scripts, cookies, visitor IDs, raw query logs
or database fields are added. Existing anonymous download metrics and privacy choices are unchanged.

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

Website deployment, public favicon MIME/dimension checks, www DNS/TLS/redirect checks, schema validation
against the live page, GitHub metadata update and post-change query samples are pending at this checkpoint.
Update this section with actual observed results. Do not claim improved ranking or recommendations.

Directory/review drafts are in [DISCOVERY-SUBMISSIONS](DISCOVERY-SUBMISSIONS.md); nothing has been sent.
Search Console's recrawl/indexing and its eventual favicon selection remain Google's decisions.

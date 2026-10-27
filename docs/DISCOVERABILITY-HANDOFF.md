# Cursiv general-search discoverability handoff

Owner: Joshua Winkler. Started 2026-10-26 from main
`09f40c66b4023ffa1a050a74268a645199f5a0ca` after the completed U106 release.

## Objective and boundaries

Prioritize non-branded discovery for free local AI, offline LLM applications and open-source AI
assistants. Preserve the design, installer links, release identity, private routes and application code.
Use the existing official Cursiv logo. This is a website/documentation update, not a new app release.
Do not touch station code, the three excluded local paths, secrets, user records or unrelated profiles.
External directory submissions require separate owner approval; prepare factual drafts only.

## Current audit

- Homepage title/H1/schema primarily describe field-research software; local AI is secondary.
- Existing useful pages: /open-source-offline-ai, /portable-workspace, /field-research,
  /offline-research and /local-ai-hardware-requirements. Reuse them; add distinct /local-ai and
  /compare pages rather than keyword variants of the same article.
- Existing icon is /assets/cursiv-logo-256.png; official source is
  launcher/resources/icons/cursiv-logo-source.png. Root favicon/Apple files are not in the publisher's
  allowlist. Inspect live status and generate exact-size derivatives from the official source.
- robots.txt blocks /api/, /remote/ and /admin/. Preserve these protections. Interactive tools have
  intentional noindex directives. Sitemap currently lists 14 public canonical pages without lastmod.
- SoftwareApplication metadata incorrectly places codeRepository on that type; move the repository
  property to a linked SoftwareSourceCode entity. No invented ratings or reviews.
- GitHub connector exposes read-only access for this repository and no description/topic editor;
  use the existing configured gh client for authorized repository metadata work.

## Search Console evidence supplied by owner

Owner reports 9 indexed pages, 6 robots exclusions, 3 noindex exclusions and one alternate canonical.
Screenshots identify the exact excluded URLs below. These are owner-supplied Search Console evidence,
not a fresh authenticated Search Console/API export.

| Exclusion | Exact URL | Initial interpretation; verify configuration/live public pages |
|---|---|---|
| robots | https://cursiv.us/api/space/ask | Private pairing/message API; retain block |
| robots | https://cursiv.us/api/space/join | Private pairing/message API; retain block |
| robots | https://cursiv.us/api/space/messages?since= | Private pairing/message API; retain block |
| robots | https://cursiv.us/api/space/create | Private pairing/message API; retain block |
| robots | https://cursiv.us/api/space/image/ | Private pairing/message API; retain block |
| robots | https://cursiv.us/api/space/pair-code | Private pairing/message API; retain block |
| noindex | https://cursiv.us/notebook/ | Interactive notebook; retain noindex |
| noindex | https://cursiv.us/letters | Removed public letters page; inspect response, do not resurrect |
| noindex | https://cursiv.us/app | Interactive photo tool; retain noindex |
| alternate canonical | https://cursiv.us/?x=2 | Duplicate homepage; retain canonical https://cursiv.us/ |

Do not call pairing/message APIs during this audit. Evaluate robots against their paths locally.
Crawler-user-agent requests are access probes, not proof of verified Googlebot traffic or WAF settings.
Search Console impressions/clicks and dashboard security settings remain unverified until actually read.

## Work order

1. Save pre-change local/live crawl, icon, canonical and general-query baselines.
2. Update broad local-AI positioning, useful comparison/discovery content and evidence links.
3. Add official favicons, crawler-safe publication, canonical-host handling and validated sitemap/schema.
4. Add repeatable audits and branded/non-branded measurement, then build/test/review.
5. Publish the authorized website update and verify production; record fixes versus retained exclusions.
6. Prepare directory/review submissions for owner approval. Rankings, recommendations and future traffic
   remain outcomes to measure, not guarantees.

## Progress and running work

- Baseline saved: reports/discovery-before.json (19 local pages, 45 live requests, two www DNS errors).
  All three requested root favicons, /local-ai, /compare and /llms.txt returned 404. Existing logo PNG
  worked. Homepage and logo were reachable with both Google crawler user-agent strings, without a
  challenge header; this is not an authenticated Googlebot/WAF-dashboard check.
- Exact exclusions verified: six API paths remain robots-blocked locally; /notebook/ and /app return
  200/noindex; /letters returns 404/noindex; /?x=2 is 200 with canonical https://cursiv.us/.
- Frozen owner query baseline: reports/discovery-search-before.json. No Cursiv URL was returned in any
  of the ten non-branded result sets from the available web-search provider. Branded/control queries
  also did not return this site. This does not override the owner's Google report of nine indexed pages
  or establish a Google rank; different search systems and coverage must be measured separately.
- GitHub aggregate views baseline: 117 views / 34 unique visitors in its returned short-term window;
  three referring-domain rows. Raw aggregate exports are ignored reports/discovery-github-*-before.json.
  Search Console performance/impression data has not been supplied; do not invent zero traffic.
- Local edits: broad homepage/README identity; new /local-ai, /compare and /documentation; corrected
  SoftwareApplication/SoftwareSourceCode relationship; experimental llms.txt; exact official-source
  favicons (ICO frames 16–256 including 96; PNG96; Apple180); favicon links in all public HTML.
- Portability copy now distinguishes complete app/runtime/model kits, authorized data, host dependencies
  and system traces. It no longer promises that abrupt unplugging cannot damage files.
- Publisher allowlist contains new public files, validates indexable/self-canonical sitemap entries and
  derives optional lastmod from full Git source history. Noindex tools and private routes remain out.
  www custom-domain/redirect configuration is prepared; not deployed or verified yet.
- Current checks: **31 website tests passed** (original 22 plus nine discovery/icon/redirect groups),
  **6 measurement tests passed**. New website CI uses Node 24 LTS and Python's standard library.
  Sitemap validates 17 canonical indexable URLs; 22 HTML pages have stable favicon links.
- Desktop/mobile review passed at 1280/390px with no body overflow; menu opens/closes. The comparison
  table remains horizontally scrollable inside its own wrapper. Preview: reports/discovery-home-preview.jpg.
- Public baseline evidence copied to bench/results/discoverability-before.json and
  bench/results/discovery-search-before.json; frozen queries and source-icon fingerprint in bench/discovery/.
  The documentation URL got one marked supplementary pre-deployment 404 check; original measurements
  were preserved. Aggregate GitHub views window is October 12–25 UTC, not website/non-branded traffic.
- docs/DISCOVERABILITY-REPORT.md records exact retained exclusions, source guidance and measurement
  limits. docs/DISCOVERY-SUBMISSIONS.md contains owner-review drafts; nothing has been sent or submitted.
- No app code or private data/API operations. No new release tag/version. Current branch:
  codex/general-search-discovery. Local public-only preview server is session 54987 on 127.0.0.1:8768;
  stop it before finishing. Earlier restricted server session 12013 was stopped.
- Next: final review/commit/PR checks, deployment and actual live favicon/WWW/schema checks, GitHub
  description/topics, post-change samples and final receipt. A recurring-check preference question is
  pending asynchronously; no automation has been created yet.
- Do not re-run the applied one-off reports/update_discovery_html.py or
  reports/final_discovery_adjustments.py helpers. Continue from the saved local edits.

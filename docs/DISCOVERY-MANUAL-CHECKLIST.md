# Manual non-branded discovery checks

Owner preference: **manual checklist only**. No recurring discovery automation or reminder is created.
Website build/tests on code changes are separate from a scheduled search monitor.

1. Choose a checkpoint and record date, engine/model, country/language and site version. Weekly reviews
   during the first month and monthly afterward are suggestions, not an automatic schedule.
2. Repeat the ten unchanged non-branded queries in [queries.json](../bench/discovery/queries.json).
   Do not add Cursiv's name. Record the inspected result range and product URLs, including absence.
   Keep branded/site-operator controls separate. Check Google and Bing directly when available; the
   available web-search tool is a separate provider sample, not either engine's complete rankings.
3. For AI recommendations, use a fresh conversation without first teaching it about Cursiv. Ask each
   general question once with search enabled and retain the reply/citations, date and product/model.
   Check that citations support the claims. ChatGPT Search, Perplexity, Google AI results, Bing/Copilot
   and Claude are separate systems. Crawler visits and a single favorable answer are not repeatable
   recommendation evidence.
4. In Search Console, explicitly select comparable single date ranges, preferably 28 days. Export
   Queries to private ignored reports/. Summarize locally:

   ```text
   python scripts/search_discovery_report.py --gsc-csv reports/Queries.csv --output reports/discovery-search-period.json
   ```

   The script separates brand tokens, non-branded and blank unknown queries, sums actual counts and
   computes weighted rates. It rejects unrelated exports/non-finite numbers and emits no raw queries.
   Google can omit anonymized/low-volume rows: the difference from overall impressions is unknown,
   not automatically non-branded. Do not infer the date-range selection solely from chart data dates.
5. If an existing aggregate referral CSV is available, use Referrer/Source and Visitors/Count with
   `--referrals-csv`. AI/search channels do not establish query intent. Cloudflare requests/visits and
   GitHub views can include bots/repeats and are not organic search traffic. No new visitor tracking,
   identifiers or database fields are authorized by this checklist.
6. Run the read-only technical audit with a dated output filename (replace YYYY-MM-DD):

   ```text
   python scripts/discoverability_audit.py --live --output reports/discovery-YYYY-MM-DD.json
   ```

   Check public status/canonical/noindex, the three favicon formats, Google user-agent responses,
   canonical redirects and the sitemap's current canonical public entries. The copy cleanup expanded
   it to 20 URLs, including three detailed references. It never queries private APIs. User-agent probes alone
   do not establish verified crawler identity.
7. Use Search Console URL Inspection when needed. Its live homepage test reported **URL is available
   to Google**, October 26, 2026 at 10:08 PM local time. Check new pages as Google discovers them. The
   owner can request indexing of changed public pages once when appropriate; do not repeatedly submit
   requests or change stable icon paths to chase a cached search logo.
8. Retain the six /api/space/ robots exclusions, notebook/app noindex, removed /letters response and
   duplicate /?x=2 canonical. Do not increase an indexed-page count by exposing private endpoints/tools.
9. Compare non-branded impressions/clicks, credible referrals and independent mentions over subsequent
   weeks, separately from brand searches, technical checks and indexing counts. Record unavailable
   data and sample size. The immediate available-provider search sample remained **0/10** non-branded
   result sets; no ranking/recommendation improvement is claimed.
10. Review [directory/reviewer drafts](DISCOVERY-SUBMISSIONS.md) before approving any submission.
    Nothing has been sent, posted or paid for. The owner chooses destinations and supplies account/
    contact information. Keep raw exports and private dashboard details out of the public repository.

[Technical audit](DISCOVERABILITY-REPORT.md) · [Continuing handoff](DISCOVERABILITY-HANDOFF.md)

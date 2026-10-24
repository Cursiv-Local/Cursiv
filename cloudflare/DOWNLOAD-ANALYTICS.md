# Cursiv website download analytics

Prepared October 21, 2026. **Not deployed automatically.** Desktop application
code, installer, updater and existing user records are outside this task.

## Current public display (October 23, 2026)

The public download counter and counting explanation have been removed from the
homepage and download page after the deployed endpoint returned unavailable.
Those pages no longer request `/api/downloads`. Download links, optional anonymous
button-click recording, the existing backend and authenticated admin page remain.
This removal is a source change and requires publication to reach the live site;
it does not resolve the admin/backend availability issue. No production data was
deleted. The implementation and original audit notes below describe the retained
backend; earlier public-counter checks are historical.

## Architecture inspected before implementation

The repository uses Cloudflare **Workers with static assets**, not Pages:
`wrangler.toml` names `worker.js`, binds `ASSETS` to `dist`, runs the Worker before
assets and binds the existing `cursiv` D1 database. `publish.mjs` copies 14 public
pages and the existing assets/notebook/privacy folders from an allowlist, then
deploys only unless `--build-only` is present. Existing API routes also serve
desktop clients, so their authentication, CORS and behavior are preserved.

The existing site has no administrator role suitable for statistics. The new
feature therefore uses a separate, strong Worker secret with HTTPS HTTP Basic
authentication. Public-board accounts and fleet credentials do not grant access.
The admin HTML is bundled into the Worker and emitted only after authentication;
it is never copied into `dist`. No new framework, dependency, hosting product,
tracker service, DNS change or scheduled task was added.

## What the numbers mean

Source: the public [GitHub Releases API](https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28),
`https://api.github.com/repos/Cursiv-Local/Cursiv/releases?per_page=100&page=N` and
`/releases/latest`. No GitHub token is needed. GitHub's latest ID, rather than a
guessed version/date ordering, selects the latest stable release.

The owner explicitly selected **exclude duplicate latest copies**:

1. Include uploaded `Cursiv-Setup[-version].exe` and the observed
   `Cursiv-version-mac-{arm64,x64,universal}.dmg` installer names.
2. Prefer exact release-version names, then other versioned installers. When a
   versioned installer exists for a platform, exclude its `*-latest` copy even
   if the copy's download count is larger. An alias-only legacy release is counted
   when it has no versioned installer for that platform.
3. Count each asset ID once. Within a release, exclude duplicate SHA-256/platform
   copies and duplicate names. Never add excluded assets to the selected total.
4. Exclude source zip/tar archives (including GitHub's automatically generated
   archives), checksum files, debug/unuploaded assets and unrelated files.
5. Include published prereleases in history, marked as such. Ignore drafts.
6. Sum the selected assets' nonnegative integer `download_count` values into
   per-release and total counts. Invalid relevant counts fail the refresh rather
   than becoming zero. Admin also shows excluded-copy assets and their counts.

This is a deliberately partial **versioned-installer** metric, not all requests
to every duplicate URL. The existing website/updater “latest” links continue to
work; requests to those excluded copies do **not** increase the selected count when
the versioned installer exists. That exclusion is visible in admin. It avoids inflating the chosen metric without inventing a way to deduce
unique people from GitHub's counts.

GitHub counts do not prove completed transfers or installations. Deleted releases
or deleted/replaced assets cannot be reconstructed. There are no daily historical
download figures, estimates, visitor totals, unique-download claims or inferred
conversion rates.

### Live read-only audit snapshot

On October 21 the public API returned **67 releases / 75 counted installer
assets**, **10 counted downloads**, and **105 requests to excluded duplicate
copies**. The latest stable release was `v3.14-U79`, with **0 counted versioned
installer downloads**. These low counts follow the owner's exclusion rule; they
are not zeros substituted for failure. This snapshot is documentation only:
no number, release tag or date was hardcoded into the former website counter.
GitHub refreshes determine the values available to the retained admin view.

The published homepage was separately fetched successfully (HTTP 200) before
changes. These checks do not claim the new feature is deployed.

## Cache and failure behavior

- One normalized GitHub metadata snapshot is persisted in D1 for one hour. Visitor
  browsers call the site's own API, not GitHub. No refresh endpoint lets visitors
  bypass the TTL.
- A conditional D1 update acquires a 45-second refresh lease, preventing concurrent
  visitors/Worker locations from multiplying upstream calls. A crashed refresh
  can be retried when the lease expires.
- Refreshes have a 20-second request budget and a bound of ten release pages
  (1,000 releases). GitHub `Link: rel="next"` drives pagination, but the code
  constructs URLs itself; it never follows arbitrary Link destinations. A release
  with 100+ embedded assets is conservatively refused for maintainer review rather
  than silently reporting an incomplete asset list.
- Rate-limit responses back off using `Retry-After` and `X-RateLimit-Reset`, with
  a minimum five minutes and maximum one day. Network/invalid-data errors back
  off five minutes. No partial refresh replaces the previous snapshot.
- Last-known data up to seven days old is shown as **cached**, with its actual last
  successful refresh time. Older/unavailable data returns an unavailable state,
  not a fabricated zero. Missing D1 migration also degrades to unavailable.
- Public download pages make no statistics request. Installer links work
  independently of statistics availability; click recording never blocks navigation.

## Authentication and privacy

### Private administration

Visit `https://cursiv.us/admin/downloads/`. Username: **admin**. Password: the
`DOWNLOAD_STATS_ADMIN_PASSWORD` Worker secret, a separate random ASCII password
at least 32 characters long. Unset/short secrets fail closed. Do not reuse the
board or fleet secret. Passwords are not in HTML, JavaScript, URLs or browser
storage. Server validation compares fixed-size hashes. Production HTTP requests
are refused; local HTTP is allowed only for localhost/127.0.0.1 development.

Both HTML and `/admin/downloads/data` authenticate on every request, across the
custom domain and Worker preview host. All `/admin/` paths are guarded before
static asset handling. Responses are `Cache-Control: no-store` and `noindex`; the
page has a restrictive CSP and frame protection. Public scripts contain no data
or credentials; DOM updates use `textContent`, not release-supplied HTML.
`robots.txt` excludes `/admin/`, but authentication is the protection. Admin is not
in the sitemap. Keep any account-level Cache Everything rules from overriding
private responses. Cloudflare WAF/Access may optionally add another layer, but
correctness does not depend on an obscure URL or a manually configured Access rule.

Browsers cache HTTP authentication credentials. Use a private browsing window and
close it to end the browser session; there is no claim of a reliable HTTP Basic
logout button. Rotate the Worker secret to revoke existing credentials. Review
Cloudflare account logging/access controls; this code does not log credentials.

### Optional button clicks

`POST /api/download-click` accepts only `{ "button": "windows" }` or `"mac"`
from a same-origin request. Actual installer links on the homepage and `/start`
are tagged; navigation to the setup page is not a download event. Recording uses
a nonblocking keepalive request and never changes/prevents navigation.

D1 stores **one aggregate count and first-recorded UTC day per category**. It
stores no event rows, exact click timestamps, IP/user-agent/referrer values, session
IDs, persistent browser identifiers or browsing history. No analytics cookies,
local storage or external scripts are used. Browser GPC/DNT and equivalent request
headers suppress recording. Set `DOWNLOAD_CLICKS_ENABLED` to `false` to stop new
recording while keeping existing totals.

Click counts are approximate: repeats and bots can increment them, and blocks,
disabled scripts, privacy signals or failures can omit clicks. Same-origin checks
limit accidental cross-site submissions but do not authenticate a human. There is
no IP-based rate limiter or visitor deduplication. No click is represented as a
completed download. Existing Cloudflare infrastructure logging/security behavior
is separate; see the updated [website privacy policy](https://cursiv.us/privacy/#download-analytics).
Aggregate click totals have no automatic expiry. Maintainers can remove them with
the reviewed D1 command `DELETE FROM download_click_totals` if desired; this task
does not execute a production deletion.

## Files changed

Website/deployment:

- `cloudflare/download-analytics.mjs` — filtering, totals, cache/lease/backoff,
  public API, private authentication/data and aggregate click endpoint.
- `cloudflare/download-admin.mjs` — Worker-only protected HTML.
- `cloudflare/worker.js` — delegate these new routes, retaining existing routes.
- `cloudflare/analytics-schema.sql`, `cloudflare/schema.sql` — additive tables;
  existing users, posts, letters, spaces, reports and other records stay intact.
- `cloudflare/wrangler.toml` — explicit click enable switch and secret setup note.
- `cloudflare/publish.mjs` — robots exclusion; preserve the upload allowlist,
  domains, asset configuration and existing sitemap entries.
- `website/assets/download-stats.js` — anonymous click events; public counter removed.
- `website/assets/download-admin.js`, `website/assets/download-admin.css` — private
  view rendering/responsiveness using existing site styles.
- `website/index.html`, `website/start.html` — counters removed; installer links use
  the current GitHub organization and preserve latest-asset functionality. The
  subsequent homepage copy rewrite uses direct, tagged installer calls to action.
- `website/privacy/index.html` — accurate feature disclosure and policy date.

Tests/documentation:

- `cloudflare/tests/download-analytics.test.mjs` — native Node tests, Web APIs and
  real disposable SQLite in place of D1; no package install needed on Node 24.
- This guide, root `README.md`, `CHANGELOG.md` and `HANDOFF.md`. The owner explicitly
  authorized README/changelog recording in the website-only task. Existing pending
  desktop changes are documented, not altered or represented as newly released.

## Tests and build checks

From the repository root, with Node.js 24:

```powershell
node cloudflare/publish.mjs --build-only
node --test cloudflare/tests/download-analytics.test.mjs
git diff --check
```

The tests cover asset selection/deduplication, real zeros/invalid counts,
prereleases/latest selection, pagination, complete-refresh failures, D1 cache and
refresh concurrency, rate-limit backoff, stale/cold outages, authentication on
HTML/data/HEAD/alternate paths, public/private separation, click totals and privacy
signals, additive schema preservation, original Worker routing, browser counter
fallback and nonblocking clicks, plus built SEO/robots/privacy/download artifacts.
An initial test-file syntax error was corrected before the passing run.

Final results:

- **18 tests passed, 0 failed, 0 skipped**, using Node 24.15.0. Test output:
  `website-analytics-tests.txt` (local test log, not published).
- `publish.mjs --build-only` succeeded; built HTML preserves canonical/SEO data,
  existing routes, SignPath note and installer functionality. No admin HTML is in
  the static upload directory.
- Wrangler **4.151.3** `deploy --dry-run` succeeded with the existing Worker/assets,
  D1 and AI bindings. It bundled the new Worker modules without uploading or
  deploying. No package manifest/dependency change was required.
- Public GitHub metadata and the published homepage were retrieved read-only;
  actual API metadata was passed through the production summarizer. This verifies
  asset names/counting against the real 67-release snapshot, independently of
  synthetic fixture counts.
- `git diff --check` and JavaScript syntax checks passed. A before/after SHA-256
  inventory found exactly **18 website/documentation files** changed. All prior
  desktop, installer/updater, tests, benchmark and other existing source files
  retained their original bytes. Existing files were not deleted.
- Private-page rendering/data routes, authentication/failures, click behavior and
  browser counter behavior were tested locally with Web APIs/SQLite/DOM doubles.
  No live Cloudflare D1 migration, production secret/authentication check or
  deployed analytics UI check is claimed; perform those after deployment below.

## Owner deployment steps — not executed automatically

1. Review the diff and run the tests/build above. Existing application changes in
   the working tree are unrelated; do not stage them as part of a website-only
   commit unless you separately intend to publish them.
2. From `cloudflare`, apply only the additive analytics migration to the existing
   D1 database (no data reset):

   ```powershell
   npx wrangler d1 execute cursiv --remote --file analytics-schema.sql
   ```

3. Configure the **Secret** on the existing `cursiv-web` Worker, not a plain public
   variable. In Cloudflare: **Workers & Pages → cursiv-web → Settings → Variables
   and Secrets → Add → Secret**, name `DOWNLOAD_STATS_ADMIN_PASSWORD`, with a
   unique generated ASCII password of at least 32 characters. Alternatively:

   ```powershell
   npx wrangler secret put DOWNLOAD_STATS_ADMIN_PASSWORD
   ```

   The CLI prompts for the value without putting it in a command/history/source.
   Do not change existing secrets or the D1 binding. The source config enables
   click recording; set `DOWNLOAD_CLICKS_ENABLED = "false"` to opt out.
4. Publish the existing Worker using the repository's existing command:

   ```powershell
   node publish.mjs
   ```

5. Check `/` and `/start` no longer show a counter or unavailable message and
   make no request to `/api/downloads`; Windows and Mac buttons still lead to the
   existing installers. Check backend availability separately through admin. A first cold refresh may
   take longer than a cached request. Do not test download completion by clicking
   repeatedly to inflate the count.
6. In a private browser, open `/admin/downloads/`. Confirm missing/wrong credentials
   get HTTP 401, then sign in as admin. Check totals, latest release and per-release
   rows. Inspect `/admin/downloads/data` without authentication separately. Confirm
   no private data is cached and no admin asset/page appears in `dist`/sitemap.
7. Make one deliberate click if desired; confirm its category increases only in
   **click totals**, not GitHub totals. Test GPC/DNT or disable recording and confirm
   no new click is stored. Review the updated privacy policy and Cloudflare logging.

No production DNS, D1 schema, secrets, deployment or release was changed during
implementation. Production authentication/UI checks remain required after the
owner deploys this feature.

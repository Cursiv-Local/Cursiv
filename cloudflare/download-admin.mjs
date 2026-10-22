// Served by the Worker only AFTER authentication; never copied into static assets.
export const adminPage = `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cursiv download statistics — Admin</title><meta name="robots" content="noindex,nofollow,noarchive">
<link rel="icon" href="/assets/cursiv_256.png"><link rel="stylesheet" href="/assets/site.css?v=u64-2">
<link rel="stylesheet" href="/assets/download-admin.css?v=1">
<script defer src="/assets/download-admin.js?v=1"></script></head><body>
<header class="nav"><div class="wrap"><a class="brand" href="/">Cursiv</a><a href="/start">Download page</a></div></header>
<main class="wrap"><section><span class="eyebrow">Private statistics</span><h1>Cursiv downloads</h1>
<p id="stats-status" role="status">Loading GitHub release metadata…</p>
<dl class="facts" aria-label="Download summary">
<div><dt class="k">Installer downloads</dt><dd class="v" id="stats-total">Unavailable</dd></div>
<div><dt class="k">Latest stable release</dt><dd class="v" id="stats-latest">Unavailable</dd></div>
<div><dt class="k">Excluded duplicate copies</dt><dd class="v" id="stats-excluded">Unavailable</dd></div>
<div><dt class="k">Last successful refresh</dt><dd class="v" id="stats-updated">Unavailable</dd></div>
</dl>
<p class="fine">GitHub asset download counts are requests, not confirmed completed transfers, installations or unique people.
Versioned installers are counted; duplicate latest copies, source archives, checksums and unrelated assets are excluded.
Published prereleases are included in history and marked below. There is no historical daily download data.</p>
<h2>Downloads per release</h2><div class="table-wrap"><table class="table">
<thead><tr><th>Release</th><th>Installer downloads</th><th>Counted assets</th><th>Excluded copies</th></tr></thead>
<tbody id="stats-releases"></tbody></table></div>
</section><section><h2>Website download-button clicks</h2><p id="stats-clicks" role="status">Loading…</p>
<p class="fine">Clicks are recorded separately from GitHub downloads. Repeats and bots may be included; privacy controls,
blocked requests and failed recording can omit clicks. No conversion rate or completed-download claim is inferred.</p>
<p class="fine">No visitor IDs, IP addresses, user agents, referrers or individual events are stored by this analytics feature.
Your browser may remember this HTTP authentication session; close the private browsing window when finished.</p>
</section></main></body></html>`;

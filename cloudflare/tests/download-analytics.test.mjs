import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, existsSync } from 'node:fs';
import vm from 'node:vm';
import { summarize, fetchSummary, statistics, handleDownloadAnalytics } from '../download-analytics.mjs';
import worker from '../worker.js';

const schema = readFileSync(new URL('../analytics-schema.sql', import.meta.url), 'utf8');
const password = 'test-only-strong-admin-password-0123456789';
const cacheId = 'github-canonical-installers-v1';
const now = Math.floor(Date.now() / 1000);
const digest = 'sha256:' + 'a'.repeat(64);
const asset = (id, name, count, extra = {}) => ({ id, name, download_count: count, state: 'uploaded', ...extra });
const release = (id, assets, extra = {}) => ({ id, tag_name: `v3.14-U${id}`, draft: false, prerelease: false,
  published_at: `2026-10-${String(id).padStart(2, '0')}T00:00:00Z`, assets,
  html_url: `https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U${id}`, ...extra });
const fixture = () => [release(2, [asset(21, 'Cursiv-Setup-3.14-U2.exe', 7), asset(22, 'Cursiv-Setup-latest.exe', 20)]),
  release(1, [asset(11, 'Cursiv-Setup-3.14-U1.exe', 3)])];
const response = (body, options) => new Response(JSON.stringify(body), options);
const api = async url => response(url.endsWith('/latest') ? { id: 2 } : fixture());

function database(t, full = false) {
  const sql = new DatabaseSync(':memory:');
  sql.exec(full ? readFileSync(new URL('../schema.sql', import.meta.url), 'utf8') : schema);
  t.after(() => sql.close());
  return { sql, prepare(query) {
    let values = [];
    return { bind(...args) { values = args; return this; },
      async first() { return sql.prepare(query).get(...values) || null; },
      async all() { return { results: sql.prepare(query).all(...values) }; },
      async run() { return { meta: { changes: sql.prepare(query).run(...values).changes } }; } };
  } };
}

const auth = () => ({ Authorization: 'Basic ' + btoa('admin:' + password) });
const request = (path, options = {}) => new Request('https://cursiv.us' + path, options);
function seed(db, age = 0) {
  db.sql.prepare('INSERT OR REPLACE INTO download_analytics_cache (id, payload, updated_at) VALUES (?, ?, ?)')
    .run(cacheId, JSON.stringify(summarize(fixture(), 2)), now - age);
}

test('canonical installer totals exclude latest aliases, archives, unrelated assets and repeated IDs', () => {
  const rows = [release(1, [asset(1, 'Cursiv-Setup-latest.exe', 99, { digest }),
    asset(2, 'Cursiv-Setup-3.14-U1.exe', 10, { digest }), asset(2, 'Cursiv-Setup-3.14-U1.exe', 10),
    asset(3, 'Cursiv-Setup-3.14-U1-copy.exe', 7, { digest }),
    asset(4, 'Cursiv-3.14-U1-mac-arm64.dmg', 2), asset(5, 'Cursiv-mac-latest.dmg', 9),
    asset(6, 'source.zip', 1000), asset(7, 'SHA256SUMS.txt', 100), asset(8, 'other-setup.exe', 900),
    asset(9, 'Cursiv-Setup-3.14-U1-debug.exe', 500, { state: 'new' })])];
  const data = summarize([...rows, ...rows], 1);
  assert.equal(data.total, 12);
  assert.deepEqual(data.releases[0].assets.map(a => a.id).sort(), [2, 4]);
  assert.equal(data.excluded_downloads, 115);
});

test('published prereleases count in history; drafts do not; latest comes from GitHub latest ID', () => {
  const data = summarize([release(3, [asset(30, 'Cursiv-Setup-3.14-U3.exe', 5)], { prerelease: true }),
    ...fixture(), release(4, [asset(40, 'Cursiv-Setup-3.14-U4.exe', 999)], { draft: true })], 1);
  assert.equal(data.total, 15);
  assert.equal(data.latest.id, 1);
  assert.equal(data.latest.downloads, 3);
  assert.equal(data.releases.length, 3);
});

test('zero is real, alias-only older releases are supported, and invalid metadata never becomes zero', () => {
  assert.equal(summarize([release(1, [asset(1, 'Cursiv-Setup-latest.exe', 0)])], 1).total, 0);
  for (const count of [-1, '12', null, NaN]) assert.throws(() => summarize([release(1, [asset(1, 'Cursiv-Setup-3.14-U1.exe', count)])], 1));
  assert.throws(() => summarize(fixture(), 999));
  assert.throws(() => summarize(null, null));
});

test('GitHub pagination is complete and URL-controlled, with public API headers and latest metadata', async () => {
  const calls = [];
  const data = await fetchSummary(async (url, options) => {
    calls.push(url);
    assert.equal(options.headers['User-Agent'], 'Cursiv-website-download-statistics');
    assert.equal(options.headers.Authorization, undefined);
    if (url.endsWith('/latest')) return response({ id: 2 });
    if (url.endsWith('page=1')) return response([fixture()[0]], { headers: { Link: '<https://evil.example>; rel="next"' } });
    return response([fixture()[1]]);
  });
  assert.equal(data.total, 10);
  assert.equal(calls.length, 3);
  assert(calls.every(url => url.startsWith('https://api.github.com/repos/Cursiv-Local/Cursiv/releases')));
});

test('incomplete pagination, huge embedded asset sets and malformed JSON fail rather than publishing partial history', async () => {
  await assert.rejects(fetchSummary(async () => response(fixture(), { headers: { Link: '<next>; rel="next"' } })));
  const manyAssets = [release(1, Array(100).fill(asset(1, 'Cursiv-Setup-latest.exe', 4)))];
  await assert.rejects(fetchSummary(async () => response(manyAssets)));
  await assert.rejects(fetchSummary(async () => new Response('{broken')));
});

test('all-prerelease repositories can have no stable latest without losing totals', async () => {
  const data = await fetchSummary(async url => url.endsWith('/latest') ? response({}, { status: 404 }) : response([release(1, [asset(1, 'Cursiv-Setup-3.14-U1.exe', 2)], { prerelease: true })]));
  assert.equal(data.total, 2);
  assert.equal(data.latest, null);
});

test('D1 caches metadata across requests and an hour later refreshes', async t => {
  const DB = database(t); let calls = 0;
  const fetcher = async (...args) => { calls++; return api(...args); };
  const first = await statistics({ DB }, { now, fetcher });
  const second = await statistics({ DB }, { now: now + 30, fetcher });
  assert.equal(first.total, 10); assert.equal(second.total, 10); assert.equal(calls, 2);
  await statistics({ DB }, { now: now + 3601, fetcher });
  assert.equal(calls, 4);
});

test('refresh lease prevents concurrent visitors from multiplying GitHub requests', async t => {
  const DB = database(t); let releaseFetch, calls = 0;
  const gate = new Promise(resolve => { releaseFetch = resolve; });
  const first = statistics({ DB }, { now, fetcher: async (...args) => { calls++; await gate; return api(...args); } });
  await new Promise(resolve => setImmediate(resolve));
  const second = await statistics({ DB }, { now, fetcher: () => assert.fail('A lease is held') });
  assert.equal(second.available, false); assert.equal(second.status, 'refreshing');
  releaseFetch(); assert.equal((await first).total, 10); assert.equal(calls, 2);
});

test('GitHub rate limits preserve stale data and enforce Retry-After/reset backoff', async t => {
  const DB = database(t); seed(DB, 4000); let calls = 0;
  const fetcher = async () => { calls++; return response({}, { status: 429, headers: { 'Retry-After': '600', 'X-RateLimit-Reset': String(now + 900) } }); };
  const first = await statistics({ DB }, { now, fetcher });
  assert.equal(first.total, 10); assert.equal(first.status, 'rate_limited');
  assert.equal(first.updated_at, new Date((now - 4000) * 1000).toISOString());
  assert.equal(first.retry_at, new Date((now + 900) * 1000).toISOString());
  await statistics({ DB }, { now: now + 500, fetcher }); assert.equal(calls, 1);
});

test('network failures, cold outages, expired stale data and absent migration are graceful', async t => {
  const DB = database(t); const failed = async () => { throw new Error('offline'); };
  assert.equal((await statistics({ DB }, { now, fetcher: failed })).total, null);
  seed(DB, 4000);
  assert.equal((await statistics({ DB }, { now, fetcher: failed })).total, 10);
  seed(DB, 8 * 86400);
  assert.equal((await statistics({ DB }, { now, fetcher: failed })).available, false);
  assert.equal((await statistics({ DB: { prepare() { throw new Error('no table'); } } })).available, false);
  DB.sql.prepare('UPDATE download_analytics_cache SET payload = ?, updated_at = ?').run('{"total":"invalid","releases":[]}', now);
  assert.equal((await statistics({ DB })).available, false);
});

test('all admin HTML/data routes require real authentication, including alternate suffixes and HEAD', async t => {
  const DB = database(t); seed(DB);
  for (const path of ['/admin/downloads', '/admin/downloads/', '/admin/downloads/data', '/admin/downloads.html', '/admin/downloads/data/']) {
    for (const method of ['GET', 'HEAD']) {
      const result = await handleDownloadAnalytics(request(path, { method }), { DB, DOWNLOAD_STATS_ADMIN_PASSWORD: password });
      assert.equal(result.status, 401); assert.equal(result.headers.get('Cache-Control'), 'no-store');
      assert.match(result.headers.get('WWW-Authenticate'), /Basic/);
      assert(!await result.text().then(text => text.includes('Installer downloads')));
    }
  }
  for (const value of [undefined, '', 'short']) assert.equal((await handleDownloadAnalytics(request('/admin/downloads', { headers: auth() }), { DB, DOWNLOAD_STATS_ADMIN_PASSWORD: value })).status, 401);
  for (const token of ['Basic !invalid', 'Bearer public-board-token', 'Basic ' + btoa('admin:wrong')]) assert.equal((await handleDownloadAnalytics(request('/admin/downloads/data', { headers: { Authorization: token } }), { DB, DOWNLOAD_STATS_ADMIN_PASSWORD: password })).status, 401);
});

test('authenticated admin view is private, noindex, injection-safe and separate from public summary', async t => {
  const DB = database(t); seed(DB);
  const env = { DB, DOWNLOAD_STATS_ADMIN_PASSWORD: password, DOWNLOAD_CLICKS_ENABLED: 'true' };
  const page = await handleDownloadAnalytics(request('/admin/downloads/', { headers: auth() }), env);
  assert.equal(page.status, 200); assert.match(page.headers.get('Content-Security-Policy'), /frame-ancestors 'none'/);
  assert.match(page.headers.get('X-Robots-Tag'), /noindex/); assert(!await page.text().then(text => text.includes(password)));
  const stats = await (await handleDownloadAnalytics(request('/admin/downloads/data', { headers: auth() }), env)).json();
  assert.equal(stats.total, 10); assert.equal(stats.latest.downloads, 7); assert.equal(stats.releases.length, 2);
  assert.equal(stats.excluded_downloads, 20); assert.deepEqual(stats.clicks.totals, []);
  const publicData = await (await handleDownloadAnalytics(request('/api/downloads'), env)).json();
  assert.equal(publicData.total, 10); assert.equal(publicData.releases, undefined); assert.equal(publicData.clicks, undefined);
  assert.equal((await handleDownloadAnalytics(new Request('http://cursiv.us/admin/downloads', { headers: auth() }), env)).status, 403);
});

test('anonymous clicks store aggregate category totals only, never completed downloads or identities', async t => {
  const DB = database(t), env = { DB, DOWNLOAD_CLICKS_ENABLED: 'true' };
  const click = button => request('/api/download-click', { method: 'POST', headers: {
    Origin: 'https://cursiv.us', 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin',
    'CF-Connecting-IP': '192.0.2.1', 'User-Agent': 'test', Referer: 'https://cursiv.us/start?private=value',
  }, body: JSON.stringify({ button }) });
  for (const button of ['windows', 'windows', 'mac']) assert.equal((await handleDownloadAnalytics(click(button), env)).status, 204);
  const totals = DB.sql.prepare('SELECT * FROM download_click_totals ORDER BY button').all();
  assert.deepEqual(totals.map(r => [r.button, r.count]), [['mac', 1], ['windows', 2]]);
  assert.deepEqual(Object.keys(totals[0]).sort(), ['button', 'count', 'started_day']);
  assert.equal(DB.sql.prepare('SELECT count(*) AS n FROM download_analytics_cache').get().n, 0);
});

test('click endpoint rejects cross-origin/malformed events, honors privacy signals and disable switch', async t => {
  const DB = database(t), env = { DB, DOWNLOAD_CLICKS_ENABLED: 'true' };
  function click(body, headers = {}) { return request('/api/download-click', { method: 'POST', headers: { Origin: 'https://cursiv.us', 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) }); }
  assert.equal((await handleDownloadAnalytics(click({ button: 'windows' }, { Origin: 'https://other.example' }), env)).status, 403);
  for (const body of [{ button: 'other' }, { button: 'windows', visitor: 'secret' }, { button: 'x'.repeat(200) }]) assert.equal((await handleDownloadAnalytics(click(body), env)).status, 400);
  for (const headers of [{ DNT: '1' }, { 'Sec-GPC': '1' }]) assert.equal((await handleDownloadAnalytics(click({ button: 'windows' }, headers), env)).status, 204);
  assert.equal((await handleDownloadAnalytics(click({ button: 'windows' }), { DB, DOWNLOAD_CLICKS_ENABLED: 'false' })).status, 204);
  assert.equal(DB.sql.prepare('SELECT count(*) AS n FROM download_click_totals').get().n, 0);
  assert.equal((await handleDownloadAnalytics(request('/api/download-click'), env)).status, 405);
  const malformed = request('/api/download-click', { method: 'POST', headers: { Origin: 'https://cursiv.us', 'Content-Type': 'application/json' }, body: '{broken' });
  assert.equal((await handleDownloadAnalytics(malformed, env)).status, 400);
  const failed = await handleDownloadAnalytics(click({ button: 'windows' }), { DOWNLOAD_CLICKS_ENABLED: 'true' });
  assert.equal(failed.status, 503);
});

test('additive schema preserves existing website records and original API/static routing', async t => {
  const DB = database(t, true);
  DB.sql.prepare('INSERT INTO users (id, username, pw_hash, created) VALUES (?, ?, ?, ?)').run('a', 'existing', 'hash', 'date');
  DB.sql.exec(schema); DB.sql.exec(schema);
  assert.equal(DB.sql.prepare('SELECT username FROM users').get().username, 'existing');
  const env = { DB, ASSETS: { fetch: async () => new Response('original static page') } };
  assert.equal(await (await worker.fetch(request('/start'), env)).text(), 'original static page');
  assert.equal((await (await worker.fetch(request('/health'), env)).json()).status, 'ok');
  const old = await worker.fetch(new Request('https://cursiv.winklers-llc.com/start'), env);
  assert.equal(old.status, 301); assert.equal(old.headers.get('Location'), 'https://cursiv.us/start');
  assert.equal((await worker.fetch(request('/admin/downloads'), env)).status, 401);
  assert.equal(await (await worker.fetch(request('/admin/downloads', { method: 'HEAD' }), env)).text(), '');
});

async function browserScript({ data = { available: true, total: 1234, status: 'fresh', updated_at: 'date' }, reject = false, privacy = {}, counters = true } = {}) {
  const calls = [], listeners = {}, counter = { textContent: 'fallback' };
  const context = { document: { querySelectorAll: () => counters ? [counter] : [], addEventListener: (name, fn) => { listeners[name] = fn; } },
    navigator: privacy, AbortController, setTimeout, clearTimeout, Intl, Number,
    fetch: (url, options) => { calls.push({ url, options }); return reject ? Promise.reject(new Error('offline')) : Promise.resolve(response(data)); } };
  vm.runInNewContext(readFileSync(new URL('../../website/assets/download-stats.js', import.meta.url), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  return { calls, listeners, counter };
}

test('public counter renders real totals or honest unavailable/stale text without storage', async () => {
  assert.match((await browserScript()).counter.textContent, /1,234 versioned installer/);
  assert.match((await browserScript({ data: { available: true, total: 0, status: 'unavailable' } })).counter.textContent, /0 versioned.*cached/);
  for (const options of [{ reject: true }, { data: { available: false, total: null } }, { data: { available: true, total: 'invented' } }]) assert.match((await browserScript(options)).counter.textContent, /temporarily unavailable/);
});

test('button recording never cancels navigation, distinguishes real buttons, and respects GPC/DNT', async () => {
  const browser = await browserScript({ counters: false });
  const event = (button, type = 'click') => ({ type, button, target: { closest: () => ({ dataset: { downloadButton: 'windows' } }) }, preventDefault() { assert.fail('Downloads must not be blocked'); } });
  browser.listeners.click(event(0)); browser.listeners.auxclick(event(1, 'auxclick')); browser.listeners.click(event(2));
  assert.equal(browser.calls.length, 2);
  assert.deepEqual(JSON.parse(browser.calls[0].options.body), { button: 'windows' });
  assert.equal(browser.calls[0].options.keepalive, true); assert.equal(browser.calls[0].options.credentials, 'omit');
  for (const privacy of [{ doNotTrack: '1' }, { globalPrivacyControl: true }]) {
    const disabled = await browserScript({ counters: false, privacy }); disabled.listeners.click(event(0)); assert.equal(disabled.calls.length, 0);
  }
});

test('build output retains SEO, canonical installer URLs, privacy disclosure and private-page exclusion', () => {
  const path = new URL('../dist/index.html', import.meta.url);
  assert(existsSync(path), 'Build first: node cloudflare/publish.mjs --build-only');
  for (const page of ['index.html', 'start.html']) {
    const html = readFileSync(new URL('../dist/' + page, import.meta.url), 'utf8');
    assert.match(html, /data-download-count/); assert.match(html, /<link rel="canonical" href="https:\/\/cursiv.us\//);
    assert.match(html, /download-stats.js/);
  }
  const start = readFileSync(new URL('../dist/start.html', import.meta.url), 'utf8');
  assert.match(start, /https:\/\/github.com\/Cursiv-Local\/Cursiv\/releases\/latest\/download\/Cursiv-Setup-latest.exe/);
  assert.match(start, /SignPath/); assert(!/<img\b/i.test(start.replace(/<header[\s\S]*?<\/header>/, '')));
  assert.match(readFileSync(new URL('../dist/privacy/index.html', import.meta.url), 'utf8'), /download-analytics/);
  assert.match(readFileSync(new URL('../dist/robots.txt', import.meta.url), 'utf8'), /Disallow: \/admin\//);
  assert(!existsSync(new URL('../dist/admin', import.meta.url)));
  assert(!readFileSync(new URL('../dist/sitemap.xml', import.meta.url), 'utf8').includes('/admin'));
});

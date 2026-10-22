// Website-only GitHub metadata cache, authenticated admin view and anonymous totals.
import { adminPage } from './download-admin.mjs';

export const REPOSITORY = 'Cursiv-Local/Cursiv';
const API = `https://api.github.com/repos/${REPOSITORY}/releases`;
const CACHE_ID = 'github-canonical-installers-v1';
const TTL = 3600;
const LEASE = 45;
const MAX_PAGES = 10;
const MAX_STALE = 7 * 86400;
const METHOD = 'Versioned Cursiv installers; duplicate latest copies, archives and unrelated assets excluded.';
const encoder = new TextEncoder();
const headers = {
  'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
  'X-Robots-Tag': 'noindex, nofollow, noarchive', 'Referrer-Policy': 'no-referrer',
};

function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), { status, headers: { ...headers, 'Content-Type': 'application/json; charset=utf-8', ...extra } });
}

function installer(name) {
  if (/^Cursiv-Setup(?:-(?:v?\d[\w.+-]*|latest))?\.exe$/i.test(name)) return { platform: 'windows', alias: /-latest\.exe$/i.test(name) };
  if (/^Cursiv-(?:v?\d[\w.+-]*-mac-(?:arm64|x64|universal)|mac-latest)\.dmg$/i.test(name)) return { platform: 'mac', alias: /-latest\.dmg$/i.test(name) };
  return null;
}

function canonicalUrl(url, prefix) {
  try { const u = new URL(url); return u.origin === 'https://github.com' && u.pathname.startsWith(`/${REPOSITORY}/${prefix}`) ? u.href : null; }
  catch { return null; }
}

export function summarize(releases, latestId) {
  if (!Array.isArray(releases)) throw new Error('Invalid release list');
  const releaseIds = new Set(), assetIds = new Set();
  const rows = [];
  for (const release of releases) {
    if (!release || !Number.isSafeInteger(release.id) || typeof release.tag_name !== 'string' || !Array.isArray(release.assets)) throw new Error('Invalid release metadata');
    if (release.draft || releaseIds.has(release.id)) continue;
    releaseIds.add(release.id);
    const candidates = [];
    for (const asset of release.assets) {
      const kind = installer(asset.name || '');
      if (!kind || asset.state !== 'uploaded') continue;
      if (!Number.isSafeInteger(asset.id) || !Number.isSafeInteger(asset.download_count) || asset.download_count < 0) throw new Error('Invalid installer count');
      if (assetIds.has(asset.id)) continue; // same API object repeated across pages
      assetIds.add(asset.id);
      candidates.push({ id: asset.id, name: asset.name, downloads: asset.download_count, ...kind,
        digest: /^sha256:[a-f0-9]{64}$/i.test(asset.digest || '') ? asset.digest.toLowerCase() : null });
    }
    // Versioned names win even if aliases were returned first or have more requests.
    const version = release.tag_name.replace(/^v/i, '').toLowerCase();
    const rank = asset => asset.alias ? 2 : asset.name.toLowerCase() === `cursiv-setup-${version}.exe` ||
      asset.name.toLowerCase().startsWith(`cursiv-${version}-mac-`) ? 0 : 1;
    candidates.sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name) || a.id - b.id);
    const seenDigests = new Set(), seenNames = new Set(), counted = [], excluded = [];
    for (const asset of candidates) {
      const key = asset.platform + ':' + (asset.digest || asset.name.toLowerCase());
      const duplicate = seenDigests.has(key) || seenNames.has(asset.name.toLowerCase()) ||
        (asset.alias && candidates.some(other => !other.alias && other.platform === asset.platform));
      (duplicate ? excluded : counted).push({ id: asset.id, name: asset.name, downloads: asset.downloads });
      if (!duplicate) { seenDigests.add(key); seenNames.add(asset.name.toLowerCase()); }
    }
    rows.push({ id: release.id, tag: release.tag_name, prerelease: release.prerelease === true,
      url: canonicalUrl(release.html_url, 'releases/tag/'), published_at: release.published_at || null,
      downloads: counted.reduce((n, a) => n + a.downloads, 0), assets: counted,
      excluded_downloads: excluded.reduce((n, a) => n + a.downloads, 0), excluded_assets: excluded });
  }
  rows.sort((a, b) => String(b.published_at).localeCompare(String(a.published_at)) || b.id - a.id);
  if (latestId !== null && !rows.some(row => row.id === latestId)) throw new Error('Release list changed during refresh');
  const total = rows.reduce((n, r) => n + r.downloads, 0);
  if (!Number.isSafeInteger(total)) throw new Error('Installer count out of range');
  return { repository: REPOSITORY, total, latest: rows.find(row => row.id === latestId) || null,
    excluded_downloads: rows.reduce((n, r) => n + r.excluded_downloads, 0), releases: rows, methodology: METHOD };
}

class UpstreamError extends Error {
  constructor(status, retryAt) { super('GitHub metadata unavailable'); this.status = status; this.retryAt = retryAt; }
}

async function github(fetcher, url, signal, now) {
  const response = await fetcher(url, { headers: {
    Accept: 'application/vnd.github+json', 'User-Agent': 'Cursiv-website-download-statistics',
    'X-GitHub-Api-Version': '2022-11-28',
  }, signal, redirect: 'error' });
  if (!response.ok) {
    const retry = response.headers.get('Retry-After');
    const seconds = /^\d+$/.test(retry || '') ? Number(retry) : 0;
    const retryDate = retry && !seconds ? Date.parse(retry) / 1000 : 0;
    const reset = Number(response.headers.get('X-RateLimit-Reset')) || 0;
    throw new UpstreamError(response.status, Math.min(now + 86400, Math.max(now + 300, now + seconds, retryDate || 0, response.status === 403 || response.status === 429 ? reset : 0)));
  }
  const raw = await response.text();
  if (raw.length > 4_000_000) throw new Error('GitHub metadata exceeds limit');
  return { data: JSON.parse(raw), next: /rel="next"/.test(response.headers.get('Link') || '') };
}

export async function fetchSummary(fetcher = fetch, now = Math.floor(Date.now() / 1000)) {
  const signal = AbortSignal.timeout(20_000);
  const releases = [];
  let complete = false;
  for (let page = 1; page <= MAX_PAGES; page++) {
    const result = await github(fetcher, `${API}?per_page=100&page=${page}`, signal, now);
    if (!Array.isArray(result.data)) throw new Error('Invalid release list');
    // GitHub embeds assets in each release. Refuse a potentially truncated large
    // set instead of silently claiming a complete historical total.
    if (result.data.some(r => Array.isArray(r.assets) && r.assets.length >= 100)) throw new Error('Release needs explicit asset pagination');
    releases.push(...result.data);
    if (!result.next) { complete = true; break; }
  }
  if (!complete) throw new Error('Release pagination exceeds limit');
  let latestId = null;
  try {
    const result = await github(fetcher, `${API}/latest`, signal, now);
    if (!Number.isSafeInteger(result.data?.id)) throw new Error('Invalid latest release');
    latestId = result.data.id;
  } catch (error) { if (!(error instanceof UpstreamError) || error.status !== 404) throw error; }
  return summarize(releases, latestId);
}

function cachedView(row, now, status) {
  let payload = null;
  try { if (row?.payload && now - row.updated_at <= MAX_STALE) payload = JSON.parse(row.payload); } catch {}
  if (!payload || !Number.isSafeInteger(payload.total) || payload.total < 0 || !Array.isArray(payload.releases)) payload = null;
  return { available: !!payload, status, updated_at: payload ? new Date(row.updated_at * 1000).toISOString() : null,
    retry_at: row?.retry_at > now ? new Date(row.retry_at * 1000).toISOString() : null,
    ...(payload || { repository: REPOSITORY, total: null, latest: null, releases: [], excluded_downloads: null, methodology: METHOD }) };
}

export async function statistics(env, { now = Math.floor(Date.now() / 1000), fetcher = fetch } = {}) {
  if (!env.DB) return cachedView(null, now, 'unavailable');
  let row;
  try {
    row = await env.DB.prepare('SELECT * FROM download_analytics_cache WHERE id = ?').bind(CACHE_ID).first();
    if (row?.payload && row.updated_at > now - TTL) return cachedView(row, now, 'fresh');
    if (row?.retry_at > now || row?.lease_until > now) return cachedView(row, now, row.retry_at > now ? row.status : 'refreshing');
    await env.DB.prepare('INSERT OR IGNORE INTO download_analytics_cache (id) VALUES (?)').bind(CACHE_ID).run();
    const claim = await env.DB.prepare('UPDATE download_analytics_cache SET lease_until = ? WHERE id = ? AND lease_until <= ? AND retry_at <= ? AND updated_at <= ?')
      .bind(now + LEASE, CACHE_ID, now, now, now - TTL).run();
    if (claim.meta.changes !== 1) return cachedView(row, now, 'refreshing');
    try {
      const summary = await fetchSummary(fetcher, now);
      await env.DB.prepare("UPDATE download_analytics_cache SET payload = ?, updated_at = ?, retry_at = 0, lease_until = 0, status = 'fresh' WHERE id = ?")
        .bind(JSON.stringify(summary), now, CACHE_ID).run();
      return cachedView({ payload: JSON.stringify(summary), updated_at: now }, now, 'fresh');
    } catch (error) {
      const retryAt = error instanceof UpstreamError ? error.retryAt : now + 300;
      const status = error instanceof UpstreamError && [403, 429].includes(error.status) ? 'rate_limited' : 'unavailable';
      await env.DB.prepare('UPDATE download_analytics_cache SET retry_at = ?, lease_until = 0, status = ? WHERE id = ?').bind(retryAt, status, CACHE_ID).run();
      return cachedView({ ...row, retry_at: retryAt }, now, status);
    }
  } catch { return cachedView(row, now, 'unavailable'); } // absent migration/DB failure never breaks downloads
}

async function authorized(request, env) {
  const password = env.DOWNLOAD_STATS_ADMIN_PASSWORD;
  if (typeof password !== 'string' || password.length < 32) return false;
  const auth = request.headers.get('Authorization') || '';
  if (!auth.startsWith('Basic ') || auth.length > 4096) return false;
  let supplied;
  try { supplied = atob(auth.slice(6)); } catch { return false; }
  const expected = `admin:${password}`;
  // Compare fixed-size hashes, without exposing a secret or keeping credentials in JS.
  const [a, b] = await Promise.all([supplied, expected].map(s => crypto.subtle.digest('SHA-256', encoder.encode(s))));
  const left = new Uint8Array(a), right = new Uint8Array(b);
  let difference = 0;
  for (let i = 0; i < left.length; i++) difference |= left[i] ^ right[i];
  return difference === 0;
}

async function clickBody(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new Error('Missing body');
  const chunks = []; let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 128) { await reader.cancel(); throw new Error('Payload too large'); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
}

export async function recordClick(request, env, url) {
  if (env.DOWNLOAD_CLICKS_ENABLED !== 'true' || request.headers.get('Sec-GPC') === '1' || request.headers.get('DNT') === '1') return new Response(null, { status: 204, headers });
  if (request.headers.get('Origin') !== url.origin || (request.headers.has('Sec-Fetch-Site') && request.headers.get('Sec-Fetch-Site') !== 'same-origin')) return json({ detail: 'Same-origin request required' }, 403);
  if (request.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() !== 'application/json' || Number(request.headers.get('Content-Length') || 0) > 128) return json({ detail: 'Invalid click payload' }, 400);
  let body;
  try { body = await clickBody(request); } catch { return json({ detail: 'Invalid click payload' }, 400); }
  if (!body || Object.keys(body).length !== 1 || !['windows', 'mac'].includes(body.button)) return json({ detail: 'Invalid button' }, 400);
  try {
    await env.DB.prepare('INSERT INTO download_click_totals (button, count, started_day) VALUES (?, 1, ?) ON CONFLICT(button) DO UPDATE SET count = count + 1')
      .bind(body.button, new Date().toISOString().slice(0, 10)).run();
    return new Response(null, { status: 204, headers });
  } catch { return json({ detail: 'Click not recorded' }, 503); }
}

export async function handleDownloadAnalytics(request, env) {
  const url = new URL(request.url), path = url.pathname;
  if (path.startsWith('/admin/') || path === '/admin') {
    if (url.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(url.hostname)) return json({ detail: 'HTTPS required' }, 403);
    if (!await authorized(request, env)) return json({ detail: 'Administrator authentication required' }, 401, { 'WWW-Authenticate': 'Basic realm="Cursiv download statistics", charset="UTF-8"' });
    if (!['GET', 'HEAD'].includes(request.method)) return json({ detail: 'Method not allowed' }, 405, { Allow: 'GET, HEAD' });
    if (['/admin/downloads', '/admin/downloads/'].includes(path)) return new Response(request.method === 'HEAD' ? null : adminPage, { headers: { ...headers,
      'Content-Type': 'text/html; charset=utf-8', 'X-Frame-Options': 'DENY',
      'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'" } });
    if (path !== '/admin/downloads/data') return json({ detail: 'Not found' }, 404);
    const data = await statistics(env);
    let clicks;
    try { clicks = { available: true, enabled: env.DOWNLOAD_CLICKS_ENABLED === 'true', totals: (await env.DB.prepare('SELECT button, count, started_day FROM download_click_totals ORDER BY button').all()).results }; }
    catch { clicks = { available: false, enabled: env.DOWNLOAD_CLICKS_ENABLED === 'true', totals: [] }; }
    return json({ ...data, clicks });
  }
  if (path !== '/api/downloads' && path !== '/api/download-click') return null;
  if (path === '/api/download-click') return request.method === 'POST' ? recordClick(request, env, url) : json({ detail: 'Method not allowed' }, 405, { Allow: 'POST' });
  if (!['GET', 'HEAD'].includes(request.method)) return json({ detail: 'Method not allowed' }, 405, { Allow: 'GET, HEAD' });
  const data = await statistics(env);
  return json({ available: data.available, total: data.total, status: data.status, updated_at: data.updated_at,
    methodology: data.methodology }, data.available ? 200 : 503);
}

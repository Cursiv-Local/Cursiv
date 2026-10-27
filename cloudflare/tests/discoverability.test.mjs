// Regression checks for public discovery, favicon eligibility and intentional exclusions.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import worker from '../worker.js';

const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const bytes = path => readFileSync(new URL(path, root));
const built = path => `cloudflare/dist/${path === '/' ? 'index.html' : path.endsWith('/') ? path.slice(1) + 'index.html' : path.slice(1) + '.html'}`;
const sitemap = read('cloudflare/dist/sitemap.xml');
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(row => row[1]);
const entities = html => [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(row => JSON.parse(row[1]));

test('all sitemap pages are unique, public, self-canonical HTML with one primary heading', () => {
  assert.equal(new Set(urls).size, urls.length);
  for (const path of ['/local-ai', '/compare', '/documentation', '/start', '/portable-workspace']) assert(urls.includes('https://cursiv.us' + path));
  for (const url of urls) {
    assert(url.startsWith('https://cursiv.us/'));
    assert(!url.includes('?') && !url.endsWith('.html'));
    const html = read(built(new URL(url).pathname));
    const canonical = [...html.matchAll(/<link\b(?=[^>]*\brel="canonical")[^>]*\bhref="([^"]+)"/g)];
    assert.equal(canonical.length, 1, url);
    assert.equal(canonical[0][1], url);
    assert.equal([...html.matchAll(/<h1(?:\s[^>]*)?>/g)].length, 1, url);
    assert(!/<meta\b(?=[^>]*name="robots")(?=[^>]*content="[^"]*noindex)/i.test(html), url);
    assert.match(html, /<title>[^<]+<\/title>/);
    assert.match(html, /<meta name="description" content="[^"]+"/);
  }
  for (const row of sitemap.matchAll(/<lastmod>([^<]+)<\/lastmod>/g)) {
    assert.match(row[1], /^\d{4}-\d{2}-\d{2}$/);
    assert(Date.parse(row[1]) <= Date.now());
  }
});

test('robots restrictions remain private while all public pages and favicon paths are allowed', () => {
  const robots = read('cloudflare/dist/robots.txt');
  assert.match(robots, /^User-agent: \*$/m);
  const blocked = [...robots.matchAll(/^Disallow:\s*(\S+)$/gm)].map(row => row[1]);
  for (const path of ['/api/', '/remote/', '/admin/']) assert(blocked.includes(path));
  for (const path of [...urls.map(url => new URL(url).pathname), '/favicon.ico', '/favicon-96x96.png', '/apple-touch-icon.png']) {
    assert(!blocked.some(prefix => path.startsWith(prefix)), path);
  }
  for (const path of ['/api/', '/remote/', '/admin/', '/notebook', '/app', '/chat', '/profile', '/letters', '?x=2']) assert(!urls.some(url => url.includes(path)), path);
});

test('interactive tools and the missing-page response retain intentional noindex', () => {
  for (const path of ['app.html', 'chat.html', 'profile.html', 'notebook/index.html', '404.html']) {
    assert.match(read('cloudflare/dist/' + path), /<meta name="robots" content="noindex(?:,follow)?"/);
  }
  assert(!existsSync(new URL('cloudflare/dist/letters.html', root)));
});

test('official favicon derivatives contain the requested PNG dimensions and real ICO frames', () => {
  for (const [name, size] of [['favicon-96x96.png', 96], ['apple-touch-icon.png', 180]]) {
    const data = bytes('cloudflare/dist/' + name);
    assert.equal(data.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    assert.equal(data.readUInt32BE(16), size);
    assert.equal(data.readUInt32BE(20), size);
    assert(data.equals(bytes('website/' + name)));
  }
  const ico = bytes('cloudflare/dist/favicon.ico');
  assert.equal(ico.readUInt16LE(0), 0);
  assert.equal(ico.readUInt16LE(2), 1);
  const frames = Array.from({ length: ico.readUInt16LE(4) }, (_, i) => {
    const pos = 6 + i * 16, width = ico[pos] || 256, height = ico[pos + 1] || 256;
    assert.equal(width, height);
    const length = ico.readUInt32LE(pos + 8), offset = ico.readUInt32LE(pos + 12);
    assert(length > 0 && offset + length <= ico.length);
    return width;
  });
  for (const size of [16, 32, 48, 96, 256]) assert(frames.includes(size));
  const source = bytes('launcher/resources/icons/cursiv-logo-source.png');
  assert.equal(createHash('sha256').update(source).digest('hex'), JSON.parse(read('bench/discovery/icon-source.json')).sha256);
});

test('every public HTML page links the stable root favicons and the publisher declares image types', () => {
  for (const path of [...urls.map(url => built(new URL(url).pathname)), 'cloudflare/dist/app.html', 'cloudflare/dist/notebook/index.html']) {
    const html = read(path);
    assert.match(html, /<link rel="icon" href="\/favicon.ico" sizes="any">/);
    assert.match(html, /<link rel="icon" type="image\/png" sizes="96x96" href="\/favicon-96x96.png">/);
    assert.match(html, /<link rel="apple-touch-icon" href="\/apple-touch-icon.png">/);
  }
  const headers = read('cloudflare/dist/_headers');
  assert.match(headers, /\/favicon.ico\n  Content-Type: image\/vnd.microsoft.icon/);
  assert.match(headers, /\/favicon-96x96.png\n  Content-Type: image\/png/);
  assert.match(headers, /\/apple-touch-icon.png\n  Content-Type: image\/png/);
  assert(!/^  X-Robots-Tag:.*noindex/m.test(headers));
});

test('software identity uses supported schema types and contains no invented reputation claims', () => {
  const html = read('cloudflare/dist/index.html'), graph = entities(html);
  const app = graph.find(row => row['@type'] === 'SoftwareApplication');
  const source = graph.find(row => row['@type'] === 'SoftwareSourceCode');
  assert.equal(app.name, 'Cursiv');
  assert.equal(app.url, 'https://cursiv.us/');
  assert.equal(app.applicationCategory, 'UtilitiesApplication');
  assert.equal(app.offers.price, '0');
  assert.equal(app.license, 'https://github.com/Cursiv-Local/Cursiv/blob/main/LICENSE');
  assert.match(read('LICENSE'), /MIT License/);
  assert.equal(source.codeRepository, 'https://github.com/Cursiv-Local/Cursiv');
  assert.equal(app.isBasedOn['@id'], source['@id']);
  assert(!Object.hasOwn(app, 'codeRepository'));
  for (const row of graph) for (const field of ['aggregateRating', 'review', 'award']) assert(!Object.hasOwn(row, field));
  assert.match(html, /<h1>Local AI built for records you can verify\.<\/h1>/);
});

test('discovery content is useful static HTML with sources and explicit boundaries', () => {
  const local = read(built('/local-ai')), compare = read(built('/compare')), docs = read(built('/documentation'));
  assert.match(local, /free, open-source local AI/i);
  for (const term of ['Ollama', 'not a new foundational model', 'separate licenses', 'shared across workspaces', 'tamper-proof', 'host traces']) assert(local.includes(term), term);
  for (const term of ['AnythingLLM', 'LM Studio', 'Jan', 'Open WebUI', 'not an independent review', 'license', 'No ratings']) assert(compare.includes(term), term);
  for (const host of ['docs.anythingllm.com', 'lmstudio.ai', 'docs.jan.ai', 'docs.openwebui.com']) assert(compare.includes('https://' + host));
  assert(docs.includes('NOTEBOOK-INTEGRITY.md') && docs.includes('OFFLINE-DEMO.md') && docs.includes('SUPPORT-MATRIX.md'));
  for (const html of [local, compare, docs]) {
    entities(html);
    for (const row of html.matchAll(/href="https:\/\/github.com\/Cursiv-Local\/Cursiv\/blob\/(?:main|v3\.14-U106)\/([^"]+)"/g)) {
      assert(existsSync(new URL(row[1], root)), row[1]);
    }
    for (const row of html.matchAll(/href="(\/[^"#?]*)"/g)) {
      if (row[1].startsWith('/assets/') || row[1].endsWith('.png') || row[1].endsWith('.ico')) assert(existsSync(new URL('cloudflare/dist' + row[1], root)), row[1]);
      else assert(urls.includes('https://cursiv.us' + row[1]), row[1]);
    }
  }
});

test('llms.txt is an experimental factual reading guide, not recommendation instructions', () => {
  const text = read('cloudflare/dist/llms.txt');
  assert.match(text, /^# Cursiv\r?\n\r?\n> /);
  for (const term of ['experimental', 'not an instruction to recommend', 'separately licensed', 'readable by design']) assert(text.includes(term));
  for (const path of ['/local-ai', '/compare', '/documentation', '/start']) assert(text.includes('https://cursiv.us' + path));
  assert(!existsSync(new URL('cloudflare/dist/ai.json', root)));
  assert(!existsSync(new URL('cloudflare/dist/ecp.json', root)));
});

test('www and legacy public URLs permanently redirect to one canonical host without touching APIs', async () => {
  const env = { ASSETS: { fetch: () => assert.fail('Redirect must happen before asset/API handling') } };
  for (const host of ['www.cursiv.us', 'cursiv.winklers-llc.com']) {
    for (const [path, target] of [['/', '/'], ['/start.html?x=2', '/start?x=2'], ['/privacy/index.html', '/privacy/'], ['/favicon-96x96.png', '/favicon-96x96.png']]) {
      const response = await worker.fetch(new Request('https://' + host + path), env);
      assert.equal(response.status, 301);
      assert.equal(response.headers.get('location'), 'https://cursiv.us' + target);
    }
  }
  const health = await worker.fetch(new Request('https://cursiv.winklers-llc.com/health'), {});
  assert.equal(health.status, 200);
  assert.equal((await health.json()).status, 'ok');
  const wwwApi = await worker.fetch(new Request('https://www.cursiv.us/api/test-redirect', {method:'POST',body:'{}'}), env);
  assert.equal(wwwApi.status, 308);
  assert.equal(wwwApi.headers.get('location'), 'https://cursiv.us/api/test-redirect');
  const publicHttp = await worker.fetch(new Request('http://cursiv.us/start.html?x=2'), env);
  assert.equal(publicHttp.status, 301);
  assert.equal(publicHttp.headers.get('location'), 'https://cursiv.us/start?x=2');
  const localPreview = await worker.fetch(new Request('http://localhost:8787/local-ai'),
    { ASSETS: { fetch: async () => new Response('local preview') } });
  assert.equal(localPreview.status, 200);
  assert.equal(await localPreview.text(), 'local preview');
});

// Keep current-release website claims tied to recorded evidence, not old scores.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const version = read('cursiv_v215/core/selfknow.py').match(/^VERSION\s*=\s*"([^"]+)"/m)[1];
const update = version.match(/U\d+$/)[0];
const fragment = update.toLowerCase();

test('current release labels, evidence anchors and homepage identity stay consistent', () => {
  for (const path of ['website/index.html', 'website/start.html', 'website/vision.html', 'website/ai-reliability-testing.html']) {
    const html = read(path);
    assert.ok(html.includes(update), `${path} must describe ${update}`);
    assert.doesNotMatch(html, /latest (?:documented|published) (?:app release|result|run) is U(?:75|77)\b/i);
  }
  const testing = read('website/ai-reliability-testing.html');
  assert.ok(testing.includes(`id="${fragment}"`));
  for (const path of ['website/index.html', 'website/start.html', 'website/vision.html']) {
    assert.ok(read(path).includes(`/ai-reliability-testing#${fragment}`));
  }
  const homepage = read('website/index.html');
  assert.equal([...homepage.matchAll(/rel="canonical" href="https:\/\/cursiv\.us\/"/g)].length, 1);
  for (const key of ['og:image', 'og:url', 'twitter:image']) {
    const tags = [...homepage.matchAll(new RegExp(`(?:property|name)="${key}" content="([^"]+)"`, 'g'))];
    assert.equal(tags.length, 1, key);
    assert.ok(tags[0][1].startsWith('https://cursiv.us/'));
  }
  const entities = [];
  const visit = value => {
    if (Array.isArray(value)) value.forEach(visit);
    else if (value && typeof value === 'object') { if (value['@type']) entities.push(value); Object.values(value).forEach(visit); }
  };
  for (const match of homepage.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) visit(JSON.parse(match[1]));
  const websites = entities.filter(entity => entity['@type'] === 'WebSite');
  assert.equal(websites.length, 1);
  assert.equal(websites[0].name, 'Cursiv');
  assert.equal(websites[0].url, 'https://cursiv.us/');
});

test('current model score and software count match their separate recorded evidence', () => {
  const html = read('website/ai-reliability-testing.html');
  // A newer software release need not claim an older model run as its own.
  const benchmark = html.match(/data-benchmark-release="(U\d+)"/)[1];
  const file = `bench/results/${benchmark}-qwen3_4b-instruct-suite1.5.json`;
  const result = JSON.parse(read(file));
  assert.equal(result.label, benchmark);
  assert.equal(result.source_ref, `v3.14-${benchmark}`);
  if (benchmark !== update) {
    assert.ok(html.includes(`Historical ${benchmark} release checks`));
    assert.ok(html.includes(`No new full 158-case ${update} model result is claimed`));
  }
  assert.equal(result.suite, '1.5');
  assert.equal(result.cases, 158);
  assert.equal(result.results.length, result.cases);
  assert.equal(new Set(result.results.map(row => row.id)).size, result.cases);
  assert.equal(new Set(result.results.map(row => row.cat)).size, 9);
  const passed = result.results.filter(row => row.passed).length;
  const paragraph = html.match(new RegExp(`<p id="${benchmark.toLowerCase()}-truth-result"[^>]*>([\\s\\S]*?)<\\/p>`))[1];
  const plain = paragraph.replace(/<[^>]+>/g, '');
  for (const claim of [`${passed} / ${result.cases} cases passed`, `${result.overall}% overall`,
    `accuracy: ${result.accuracy}%`, `claims: ${result.unsupported_claims}%`, result.model]) assert.ok(plain.includes(claim), claim);
  assert.ok(paragraph.includes(`datetime="${result.date}"`));
  const record = read(`docs/${update}-RELEASE-VERIFICATION.md`);
  const count = record.match(/Full isolated Windows suite:\s*\*\*([\d,]+) passed, ([\d,]+) skipped/)[1];
  assert.ok(html.includes(`${count} passed`));
  assert.ok(read('website/index.html').includes(count));
  assert.ok(read('bench/FAILURES-' + benchmark + '.md').includes(file.split('/').at(-1)));
});

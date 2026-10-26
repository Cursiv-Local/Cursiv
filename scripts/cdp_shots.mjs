// Screenshots of a page that needs a session cookie, with headless Edge/Chrome over the DevTools protocol.
//   node scripts/cdp_shots.mjs <browser.exe> <shots.json>
// shots.json: {"cookie": {"name", "value", "url"}, "shots": [{"url", "width", "height", "mobile", "out", "wait"}]}
// Used by scripts/station_shots.py for the website's Field Station page. Needs Node 22+ (built-in WebSocket).
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [browser, plan] = process.argv.slice(2);
const cfg = JSON.parse(readFileSync(plan, 'utf8'));
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), 'cursiv-shots-'));
const proc = spawn(browser, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error('the browser did not start');
}

try {
  const ws = new WebSocket(await target());
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0;
  const waiting = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && waiting.has(d.id)) { waiting.get(d.id)(d); waiting.delete(d.id); } };
  const send = (method, params = {}) => new Promise((r) => { const n = ++id; waiting.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  await send('Network.enable');
  if (cfg.cookie) await send('Network.setCookie', { ...cfg.cookie, httpOnly: true, sameSite: 'Strict' });
  for (const s of cfg.shots) {
    await send('Emulation.setDeviceMetricsOverride', { width: s.width, height: s.height, deviceScaleFactor: s.scale || 1, mobile: !!s.mobile });
    await send('Page.navigate', { url: s.url });
    await sleep(s.wait || 2500);
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: !!s.full });
    writeFileSync(s.out, Buffer.from(shot.result.data, 'base64'));
    console.log('saved', s.out);
  }
  ws.close();
} finally {
  proc.kill();
}

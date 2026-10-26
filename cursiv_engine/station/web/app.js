'use strict';
// Cursiv Field Station browser interface. Talks only to this station's /api. Every value from the
// station is shown with textContent (never as HTML), so notebook text can't run as code.
(() => {
  const $ = (id) => document.getElementById(id);
  let session = null;
  let healthTimer = null;

  // ── talking to the station ────────────────────────────────────────────────
  async function api(path, body) {
    const opts = { method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      if (session && session.csrf) opts.headers['X-CSRF-Token'] = session.csrf;
      opts.body = JSON.stringify(body);
    }
    let res;
    try { res = await fetch(path, opts); } catch (e) { return { status: 0, data: { error: 'The station isn\'t reachable. Check you are on its Wi-Fi.' } }; }
    let data = {};
    try { data = await res.json(); } catch (e) { data = {}; }
    if (res.status === 401 && path !== '/api/login') { await refresh(); }
    if (res.status === 423) { show('unlock'); }
    return { status: res.status, data };
  }

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }
  function msg(node, text, kind) { node.textContent = text || ''; node.className = 'msg' + (kind ? ' ' + kind : ''); }
  function err(r) { return (r.data && r.data.error) || ('Something went wrong (' + r.status + ').'); }

  // ── views ─────────────────────────────────────────────────────────────────
  const APP_VIEWS = ['dashboard', 'notebook', 'health', 'workspaces', 'settings'];
  function show(name) {
    document.querySelectorAll('.view').forEach((v) => { v.hidden = v.id !== 'v-' + name; });
    const inApp = APP_VIEWS.includes(name) || name === 'unlock';
    $('tabs').hidden = !inApp;
    $('signout').hidden = !(session && session.signed_in);
    document.querySelectorAll('.tabs a').forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + name));
    clearInterval(healthTimer);
    if (name === 'dashboard') loadDashboard();
    if (name === 'notebook') loadNotebook();
    if (name === 'health') { loadHealth(); healthTimer = setInterval(loadHealth, 10000); }
    if (name === 'workspaces') loadWorkspaces();
    if (name === 'settings') loadSettings();
  }

  async function refresh() {
    const r = await api('/api/session');
    session = r.data || {};
    const sim = $('sim');
    sim.hidden = !session.simulated;
    sim.textContent = session.simulated ? 'SIMULATED hardware (scenario ' + session.simulated + '): no reading on this station is real' : '';
    document.querySelectorAll('.transport').forEach((p) => { p.textContent = session.transport || ''; });
    if (session.needs_setup) return show('setup');
    if (!session.signed_in) return show('signin');
    const enc = session.encryption || {};
    const want = (location.hash || '#dashboard').slice(1);
    if (enc.encrypted && !enc.unlocked && want !== 'health') return show('unlock');
    show(APP_VIEWS.includes(want) ? want : 'dashboard');
  }
  window.addEventListener('hashchange', refresh);

  // ── setup, sign in, unlock ────────────────────────────────────────────────
  $('f-setup').addEventListener('submit', async (e) => {
    e.preventDefault();
    const r = await api('/api/setup', { code: $('s-code').value, username: $('s-user').value, station_name: $('s-name').value,
      password: $('s-pass').value, passphrase: $('s-phrase').value });
    if (r.status !== 200) return msg($('s-msg'), err(r), 'bad');
    msg($('s-msg'), 'Set up. Sign in with the administrator name and password.', 'ok');
    $('i-user').value = $('s-user').value;
    ['s-pass', 's-phrase', 's-code'].forEach((id) => { $(id).value = ''; });
    refresh();
  });
  $('f-signin').addEventListener('submit', async (e) => {
    e.preventDefault();
    const r = await api('/api/login', { username: $('i-user').value, password: $('i-pass').value });
    $('i-pass').value = '';
    if (r.status !== 200) return msg($('i-msg'), err(r), 'bad');
    msg($('i-msg'), '');
    refresh();
  });
  $('f-unlock').addEventListener('submit', async (e) => {
    e.preventDefault();
    const r = await api('/api/unlock', { passphrase: $('u-phrase').value });
    $('u-phrase').value = '';
    if (r.status !== 200) return msg($('u-msg'), err(r), 'bad');
    msg($('u-msg'), 'Unlocked.', 'ok');
    location.hash = '#dashboard';
    refresh();
  });
  $('signout').addEventListener('click', async () => { await api('/api/logout', {}); session = null; refresh(); });

  // ── readings ──────────────────────────────────────────────────────────────
  function fmtReading(r) {
    if (!r || r.source === 'unavailable' || r.value === null || r.value === undefined) return 'not available';
    const v = r.value;
    if (typeof v === 'number') return (Number.isInteger(v) ? v : v.toFixed(1)) + (r.unit ? (r.unit === '%' ? '%' : ' ' + r.unit) : '');
    if (typeof v === 'boolean') return v ? 'yes' : 'no';
    if (typeof v === 'object' && 'percent' in v) return v.percent === null ? 'not available' : v.percent + '%';
    return String(v);
  }
  function srcChip(r) {
    if (!r) return el('span', 'src unavailable', 'unavailable');
    if (r.stale) return el('span', 'src stale', 'stale');
    return el('span', 'src ' + r.source, r.source);
  }
  function kvRow(dl, label, r, text) {
    dl.append(el('dt', '', label));
    const dd = el('dd', '', text !== undefined ? text : fmtReading(r));
    dd.append(' ', srcChip(r));
    dl.append(dd);
    // the same explanation under several rows (a power bank that reports nothing) is shown once
    if (r && r.note && (r.source === 'unavailable' || r.stale) && dl.dataset.lastNote !== r.note) {
      dl.append(el('dd', 'note', r.note));
      dl.dataset.lastNote = r.note;
    }
  }
  function bytes(n) { if (n === null || n === undefined) return '?'; const g = n / 1e9; return g >= 1 ? g.toFixed(1) + ' GB' : (n / 1e6).toFixed(0) + ' MB'; }
  function uptimeText(r) { if (!r || r.value === null) return 'not available'; const s = r.value, h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h + ' h ' + m + ' min'; }

  function card(title) { const c = el('div', 'card stack'); c.append(el('h2', '', title)); return c; }

  // ── dashboard ─────────────────────────────────────────────────────────────
  async function loadDashboard() {
    const [st, h] = await Promise.all([api('/api/status'), api('/api/health')]);
    const box = $('d-cards'); box.replaceChildren();
    const s = st.data || {}, hd = h.data || {};
    $('offline').hidden = !s.offline;

    const nb = card('Field notebook');
    if (s.notebook && !s.notebook.error) {
      nb.append(el('div', 'big', s.notebook.entries + ' entr' + (s.notebook.entries === 1 ? 'y' : 'ies')));
      nb.append(el('span', 'pill ' + (s.notebook.intact ? 'ok' : 'bad'), s.notebook.intact ? 'Intact and in order' : 'Check failed: see Notebook'));
      if (s.notebook.last) nb.append(el('p', 'fine', 'Last entry ' + s.notebook.last.replace('T', ' ').slice(0, 16)));
      if (s.notebook.name) nb.append(el('p', 'fine', 'Notebook: ' + s.notebook.name));
    } else if (s.notebook && s.notebook.error) {
      nb.append(el('p', 'msg bad', s.notebook.error));
    } else {
      nb.append(el('p', 'muted', 'Locked until the encryption passphrase is entered.'));
    }
    box.append(nb);

    const th = card('Thermal');
    th.append(el('div', 'big status-' + (hd.thermal_status || 'unknown'), fmtReading(hd.cpu_temp)));
    const thl = el('dl', 'kv');
    kvRow(thl, 'Status', hd.cpu_temp, hd.thermal_status || 'unknown');
    th.append(thl); box.append(th);

    const pw = card('Power');
    const b = hd.battery || {};
    if (b.percent && b.percent.value !== null && b.percent.source !== 'unavailable') {
      pw.append(el('div', 'big status-' + String(hd.battery_status || 'unknown').split(' ')[0], fmtReading(b.percent)));
      const pl = el('dl', 'kv'); kvRow(pl, 'Charging', b.charging); kvRow(pl, 'Power draw', b.power_w); pw.append(pl);
    } else {
      pw.append(el('p', '', 'Battery telemetry unavailable.'));
      pw.append(el('p', 'fine', 'An external power source may be connected, but its charge can\'t be determined.'));
    }
    box.append(pw);

    const sys = card('System');
    const sl = el('dl', 'kv');
    kvRow(sl, 'CPU', hd.cpu); kvRow(sl, 'Memory', hd.memory);
    const internal = (hd.storage || {}).internal;
    kvRow(sl, 'Storage used', internal, internal && internal.value ? bytes(internal.value.used) + ' of ' + bytes(internal.value.total) : undefined);
    sys.append(sl); box.append(sys);

    const ai = card('Local AI');
    const m = s.model || {};
    ai.append(el('p', '', m.running ? 'Running: ' + (m.models.join(', ') || 'no models installed') : 'Not running.'));
    ai.append(el('p', 'fine', 'The notebook, checks, calculations and health readings work without it.'));
    box.append(ai);

    const sec = card('Security');
    const enc = s.encryption || {};
    sec.append(el('p', '', enc.encrypted ? (enc.unlocked ? 'Notebook encrypted, unlocked.' : 'Notebook encrypted, locked.') : 'Notebook not encrypted.'));
    sec.append(el('p', 'fine', s.offline ? 'Offline: Cursiv makes no internet connections.' : 'Internet connections allowed.'));
    box.append(sec);
  }

  // ── notebook ──────────────────────────────────────────────────────────────
  function addMeasurementRow(m) {
    const row = el('div', 'meas');
    const name = el('input'); name.placeholder = 'e.g. water temp'; name.setAttribute('aria-label', 'Measurement');
    const value = el('input'); value.placeholder = 'value'; value.setAttribute('aria-label', 'Value'); value.inputMode = 'decimal';
    const unit = el('input'); unit.placeholder = 'unit'; unit.setAttribute('aria-label', 'Unit');
    if (m) { name.value = m.name || ''; value.value = m.value || ''; unit.value = m.unit || ''; }
    row.append(name, value, unit);
    $('e-meas').append(row);
  }
  $('e-addm').addEventListener('click', () => addMeasurementRow());

  function resetForm() {
    ['e-site', 'e-sample', 'e-project', 'e-note', 'e-reason', 'e-correct'].forEach((id) => { $(id).value = ''; });
    $('e-meas').replaceChildren(); addMeasurementRow(); addMeasurementRow();
    $('e-title').textContent = 'New observation'; $('e-save').textContent = 'Save entry';
    $('e-reason-wrap').hidden = true; $('e-cancel').hidden = true;
  }
  $('e-cancel').addEventListener('click', resetForm);

  $('f-entry').addEventListener('submit', async (e) => {
    e.preventDefault();
    const measurements = [...$('e-meas').children].map((row) => {
      const [n, v, u] = row.querySelectorAll('input');
      return { name: n.value.trim(), value: v.value.trim(), unit: u.value.trim() };
    }).filter((m) => m.name || m.value);
    const body = { site: $('e-site').value, sample_id: $('e-sample').value, project: $('e-project').value,
      observer: $('e-observer').value, note: $('e-note').value, measurements };
    const correcting = $('e-correct').value;
    let r;
    if (correcting) r = await api('/api/notebook/correct', { ...body, entry_id: correcting, reason: $('e-reason').value });
    else r = await api('/api/notebook', body);
    if (r.status !== 200) return msg($('e-msg'), err(r), 'bad');
    msg($('e-msg'), 'Saved #' + r.data.entry.seq + ' · fingerprint ' + r.data.entry.hash, 'ok');
    resetForm(); loadNotebook();
  });

  function startCorrection(entry) {
    $('e-correct').value = entry.id;
    $('e-site').value = entry.site; $('e-sample').value = entry.sample_id; $('e-project').value = entry.project;
    $('e-note').value = entry.note; $('e-meas').replaceChildren();
    (entry.measurements || []).forEach(addMeasurementRow); if (!entry.measurements.length) addMeasurementRow();
    $('e-title').textContent = 'Correct entry #' + entry.seq; $('e-save').textContent = 'Save correction';
    $('e-reason-wrap').hidden = false; $('e-cancel').hidden = false;
    $('f-entry').scrollIntoView({ behavior: 'smooth' });
  }

  async function loadNotebook() {
    if (!$('e-meas').children.length) resetForm();
    if (session && !$('e-observer').value) $('e-observer').value = session.user || '';
    const q = encodeURIComponent($('n-q').value.trim());
    const r = await api('/api/notebook?limit=100&q=' + q);
    const list = $('n-list'); list.replaceChildren();
    if (r.status !== 200) return msg($('n-msg'), err(r), 'bad');
    msg($('n-msg'), r.data.total + ' entr' + (r.data.total === 1 ? 'y' : 'ies') + (q ? ' match' : ''));
    r.data.entries.forEach((en) => {
      const li = el('li');
      const head = el('div', 'head');
      head.append(el('span', '', '#' + en.seq + ' · ' + en.recorded_local.replace('T', ' ').slice(0, 16) + ' · ' + en.observer));
      head.append(el('span', '', en.notebook));
      li.append(head);
      const title = [en.site, en.sample_id ? '[' + en.sample_id + ']' : '', en.project].filter(Boolean).join(' ');
      if (title) li.append(el('strong', '', title));
      if (en.measurements.length) li.append(el('div', 'meas-line', en.measurements.map((m) => m.name + ' ' + m.value + (m.unit ? ' ' + m.unit : '')).join(' · ')));
      if (en.note) li.append(el('div', '', en.note));
      if (en.corrects) li.append(el('div', 'corr', 'Corrects an earlier entry: ' + en.reason));
      const fix = el('button', 'ghost', 'Correct…'); fix.type = 'button'; fix.addEventListener('click', () => startCorrection(en));
      li.append(fix);
      list.append(li);
    });
  }
  let qTimer = null;
  $('n-q').addEventListener('input', () => { clearTimeout(qTimer); qTimer = setTimeout(loadNotebook, 250); });
  $('n-verify').addEventListener('click', async () => {
    const r = await api('/api/notebook/verify');
    if (r.status !== 200) return msg($('n-msg'), err(r), 'bad');
    msg($('n-msg'), r.data.intact ? 'All ' + r.data.entries + ' entries are intact and in order. ' + r.data.check_means
      : 'Integrity check failed: ' + r.data.problems.join('; '), r.data.intact ? 'ok' : 'bad');
  });
  $('n-export').addEventListener('click', async () => {
    const r = await api('/api/export', {});
    if (r.status !== 200) return msg($('n-msg'), err(r), 'bad');
    msg($('n-msg'), 'Exported on the station: ' + Object.values(r.data.files).join(', ') + '. Copying exports to a USB drive comes in a later update.', 'ok');
  });

  // ── health ────────────────────────────────────────────────────────────────
  async function loadHealth() {
    const r = await api('/api/health');
    const box = $('h-sections'); box.replaceChildren();
    if (r.status !== 200) { box.append(el('p', 'msg bad', err(r))); return; }
    const h = r.data;
    const sys = card('System'); const sl = el('dl', 'kv');
    kvRow(sl, 'Device', h.device); sl.append(el('dt', '', 'Operating system'), el('dd', '', h.os));
    kvRow(sl, 'Uptime', h.uptime, uptimeText(h.uptime)); kvRow(sl, 'CPU', h.cpu); kvRow(sl, 'Memory', h.memory);
    sys.append(sl); box.append(sys);

    const th = card('Thermal'); const tl = el('dl', 'kv');
    kvRow(tl, 'CPU temperature', h.cpu_temp);
    tl.append(el('dt', '', 'Status'), el('dd', 'status-' + h.thermal_status, h.thermal_status));
    const thr = h.throttling || {};
    kvRow(tl, 'Throttling now', thr, thr.value ? (thr.value.now.join(', ') || 'none') : undefined);
    kvRow(tl, 'Since boot', thr, thr.value ? (thr.value.since_boot.join(', ') || 'none') : undefined);
    th.append(tl);
    if (h.thermal_status === 'high' || h.thermal_status === 'critical') th.append(el('p', 'msg bad', 'Running hot: give the station more airflow (out of the case, fan clear).'));
    th.append(el('p', 'fine', 'Advisory levels: elevated 65 °C, high 75 °C, critical 80 °C. The firmware\'s own throttle flags say what the Pi is actually doing.'));
    box.append(th);

    const pw = card('Power'); const pl = el('dl', 'kv'); const b = h.battery || {};
    kvRow(pl, 'Battery', b.percent); kvRow(pl, 'Charging', b.charging); kvRow(pl, 'Power draw', b.power_w);
    kvRow(pl, 'Voltage', b.voltage); kvRow(pl, 'Estimated runtime', b.runtime_min);
    pl.append(el('dt', '', 'Advice'), el('dd', 'status-' + String(h.battery_status).split(' ')[0], h.battery_status));
    pw.append(pl); box.append(pw);

    const sto = card('Storage'); const stl = el('dl', 'kv');
    const STORE = { internal: 'Internal storage', ssd: 'External SSD' };
    Object.entries(h.storage || {}).forEach(([k, s]) => kvRow(stl, STORE[k] || k, s, s.value ? bytes(s.value.free) + ' free of ' + bytes(s.value.total) : undefined));
    sto.append(stl); box.append(sto);
  }

  // ── workspaces ────────────────────────────────────────────────────────────
  async function loadWorkspaces() {
    const r = await api('/api/workspaces');
    const books = $('w-books'), drives = $('w-drives'); books.replaceChildren(); drives.replaceChildren();
    if (r.status !== 200) { books.append(el('li', 'msg bad', err(r))); return; }
    r.data.notebooks.forEach((b) => books.append(el('li', '', (b.name || b.id) + (b.own ? ' (this station)' : '') + ' · ' + b.entries + ' entr' + (b.entries === 1 ? 'y' : 'ies'))));
    if (!r.data.notebooks.length) books.append(el('li', 'muted', 'No notebook yet.'));
    r.data.drives.forEach((d) => {
      const li = el('li');
      li.append(el('strong', '', (d.label || d.mount) + ' '), el('span', 'fine', d.fstype + (d.removable ? ' · removable' : '')));
      li.append(el('div', 'fine', 'Id ' + d.id + (d.id_stable ? '' : ' (not stable on this system)')));
      if (d.space && d.space.total) li.append(el('div', 'fine', bytes(d.space.free) + ' free of ' + bytes(d.space.total)));
      if (d.workspace) li.append(el('div', '', 'Cursiv workspace: ' + ((d.workspace.notebook && d.workspace.notebook.name) || 'unnamed notebook')));
      drives.append(li);
    });
    if (!r.data.drives.length) drives.append(el('li', 'muted', 'No drives found.'));
  }

  // ── settings and shutdown ─────────────────────────────────────────────────
  function loadSettings() {
    $('about').textContent = 'Cursiv ' + (session.version || '') + ' · Field Station preview · signed in as ' + (session.user || '');
  }
  $('x-ask').addEventListener('click', () => { $('x-ask').hidden = true; $('x-yes').hidden = false; $('x-no').hidden = false; });
  $('x-no').addEventListener('click', () => { $('x-ask').hidden = false; $('x-yes').hidden = true; $('x-no').hidden = true; });
  $('x-yes').addEventListener('click', async () => {
    $('x-yes').disabled = true;
    const r = await api('/api/shutdown', { confirm: true });
    if (r.status !== 200) { $('x-yes').disabled = false; return msg($('x-msg'), err(r), 'bad'); }
    msg($('x-msg'), r.data.os_shutdown === 'requested' ? 'Stopped safely. The station is shutting down: wait for its light to stop before unplugging power.'
      : 'Stopped safely. This station isn\'t set up to power itself off; it can be unplugged once its storage light is still.', 'ok');
  });

  refresh();
})();

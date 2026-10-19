// Cursiv phone notebook: the log itself, identical in format to the laptop's field log
// (cursiv_v215/core/fieldlog.py) so Cursiv imports it through the same checks as a
// laptop's USB share (core/fieldsync.py): append-only entries, each chained to the one
// before by SHA-256, photos named by their SHA-256, and a signed head (core/devicekey.py).
//
// No storage and no network here: app.js keeps the log in IndexedDB on the phone.
// This file also runs under Node for the tests (tests/test_phone_notebook.py).

const subtle = globalThis.crypto.subtle;
export const GENESIS = "genesis";
export const HEAD_FORMAT = "cursiv-head-1";
export const BUNDLE_FORMAT = "cursiv-phone-bundle-1";
export const APP_VERSION = "phone-notebook-1";

// ── canonical JSON: the same bytes as Python's
//    json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
export function canonical(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  return "{" + Object.keys(v).sort().map(k => JSON.stringify(k) + ":" + canonical(v[k])).join(",") + "}";
}

const enc = new TextEncoder();
export const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
export const b64 = buf => {
  let s = "";
  for (const b of new Uint8Array(buf)) s += String.fromCharCode(b);
  return btoa(s);
};
export async function sha256Hex(bytes) {
  return hex(await subtle.digest("SHA-256", typeof bytes === "string" ? enc.encode(bytes) : bytes));
}

// The entry's fingerprint: SHA-256 of every field except "hash" (fieldlog._fingerprint).
export async function fingerprint(entry) {
  const body = { ...entry };
  delete body.hash;
  return sha256Hex(canonical(body));
}

// A number from a value typed as text, as fieldlog does ("12.40" -> 12.4); values kept as typed.
function numberOf(value) {
  if (!/^-?\d+(\.\d+)?$/.test(value)) return null;
  const n = parseFloat(value);
  return (n !== 0 && Math.abs(n) < 1e-6) || Math.abs(n) >= 1e21 ? null : n;   // forms JSON writes differently
}

export function cleanMeasurements(rows) {
  const out = [];
  for (const m of rows || []) {
    const name = String(m.name || "").trim();
    if (!name) continue;
    const value = String(m.value ?? "").trim();
    out.push({ name, value, number: numberOf(value), unit: String(m.unit || "").trim() });
  }
  return out;
}

function coord(v, lo, hi) {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  if (!Number.isFinite(n) || n < lo || n > hi) throw new Error(`coordinate ${v} is outside ${lo}..${hi}`);
  return Math.round(n * 1e7) / 1e7;
}

const SAMPLE_OK = /^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$/;

function localIso(d) {
  const p = n => String(n).padStart(2, "0");
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:` +
         `${p(d.getSeconds())}${sign}${p(Math.floor(Math.abs(off) / 60))}:${p(Math.abs(off) % 60)}`;
}

const utcIso = d => d.toISOString().replace(/\.\d{3}Z$/, "Z");

// Make the next entry for this log. `existing` is every entry so far, in order.
// photos: [{rel: "photos/<sha256>.jpg"}] already stored by the caller.
export async function makeEntry(existing, device, f, now = new Date()) {
  if (f.corrects && !String(f.reason || "").trim()) throw new Error("a correction needs a reason");
  const lat = coord(f.lat, -90, 90), lon = coord(f.lon, -180, 180);
  if ((lat === null) !== (lon === null)) throw new Error("give both latitude and longitude, or neither");
  const meas = cleanMeasurements(f.measurements);
  const sample = String(f.sample_id || "").trim();
  if (sample && !SAMPLE_OK.test(sample)) throw new Error("a sample ID can use letters, numbers, '-', '_' and '.' (up to 40)");
  const photos = (f.photos || []).map(p => p.rel);
  if (!(meas.length || String(f.note || "").trim() || photos.length || sample))
    throw new Error("an entry needs at least a measurement, a note or a photo");
  if (f.corrects && !existing.some(e => e.id === f.corrects)) throw new Error(`no entry ${f.corrects} to correct`);
  const last = existing[existing.length - 1];
  const id = hex(globalThis.crypto.getRandomValues(new Uint8Array(6)));
  const entry = {
    id,
    seq: last ? last.seq + 1 : 1,
    recorded_utc: utcIso(now),
    recorded_local: localIso(now),
    observer: String(f.observer || "").trim(),
    sample_id: sample,
    site: String(f.site || "").trim(),
    lat, lon,
    location_source: lat !== null ? String(f.location_source || "typed") : "",
    measurements: meas,
    note: String(f.note || "").trim(),
    photos,
    corrects: f.corrects || null,
    reason: String(f.reason || "").trim(),
    device,
    app_version: APP_VERSION,
    prev: last ? last.hash : GENESIS,
  };
  const info = (f.photos || []).filter(p => p.info).map(p => ({ file: p.rel, name: p.name || "", ...p.info }));
  if (info.length) entry.photo_info = info;
  entry.hash = await fingerprint(entry);
  return entry;
}

// The same checks as fieldsync.chain_problems.
export async function chainProblems(rows) {
  const problems = [];
  let prev = GENESIS, seq = 0;
  for (const e of rows) {
    if (e.prev !== prev) problems.push(`entry ${e.seq} doesn't follow the entry before it`);
    if (await fingerprint(e) !== e.hash) problems.push(`entry ${e.seq} was changed after it was recorded`);
    if (e.seq !== seq + 1) problems.push(`entry numbers jump from ${seq} to ${e.seq}`);
    prev = e.hash; seq = e.seq;
  }
  return problems;
}

// The entries as they stand: corrected ones replaced by their corrections (fieldlog.current).
export function current(rows) {
  const replaced = new Set(rows.filter(e => e.corrects).map(e => e.corrects));
  return rows.filter(e => !replaced.has(e.id));
}

// ── signing (Ed25519, like core/devicekey.py) ─────────────────────────────

export async function newKeyPair() {
  return subtle.generateKey({ name: "Ed25519" }, false, ["sign", "verify"]);
}

export async function publicKeyB64(publicKey) {
  return b64(await subtle.exportKey("raw", publicKey));
}

export async function keyId(publicB64) {
  const raw = Uint8Array.from(atob(publicB64), c => c.charCodeAt(0));
  return (await sha256Hex(raw)).slice(0, 16);
}

// The device label this phone's entries carry: "phone-" + its key id (stable per phone).
export async function deviceLabel(publicB64) {
  return "phone-" + (await keyId(publicB64)).slice(0, 12);
}

export async function signHead(rows, device, keyPair, now = new Date()) {
  const last = rows[rows.length - 1] || {};
  const head = { format: HEAD_FORMAT, device, entries: rows.length, seq: last.seq || 0, hash: last.hash || "",
                 signed_utc: utcIso(now) };
  const pub = await publicKeyB64(keyPair.publicKey);
  const sig = await subtle.sign({ name: "Ed25519" }, keyPair.privateKey, enc.encode(canonical(head)));
  return { signed: head, public_key: pub, key_id: await keyId(pub), signature: b64(sig) };
}

// ── the file the phone sends to the laptop ───────────────────────────────
// photos: {rel: base64 bytes}. Cursiv imports it with fieldsync.import_phone_bundle().
export async function makeBundle(rows, device, keyPair, photos, observer = "", now = new Date()) {
  const head = keyPair ? await signHead(rows, device, keyPair, now) : null;
  const manifest = { device, observer, entries: rows.length, last_hash: rows.length ? rows[rows.length - 1].hash : "",
                     shared_utc: utcIso(now) };
  if (head) manifest.head = head;
  return { format: BUNDLE_FORMAT, device, manifest, entries: rows, photos };
}

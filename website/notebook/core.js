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
export const SCHEMA = 1;          // the same record schema as cursiv_v215/core/fieldlog.py

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
  let accuracy = null;
  if (lat !== null && f.location_accuracy_m !== undefined && f.location_accuracy_m !== null && f.location_accuracy_m !== "") {
    accuracy = Math.round(Number(f.location_accuracy_m) * 10) / 10;
    if (!Number.isFinite(accuracy) || accuracy < 0) throw new Error("location accuracy isn't a number of metres");
  }
  const entry = {
    schema: SCHEMA,
    id,
    seq: last ? last.seq + 1 : 1,
    recorded_utc: utcIso(now),
    recorded_local: localIso(now),
    observer: String(f.observer || "").trim(),
    sample_id: sample,
    site: String(f.site || "").trim(),
    lat, lon,
    location_source: lat !== null ? String(f.location_source || "typed") : "",
    location_accuracy_m: accuracy,
    location_fix_utc: lat !== null ? String(f.location_fix_utc || "") : "",
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

// ── What the phone tells the person (decided here so the tests can check it under Node) ──

// persisted: navigator.storage.persist()'s answer (true/false, or null when the browser can't say).
export function storageNote(persisted) {
  const base = "Stored only in this browser on this phone. Send to the laptop regularly: that file is the backup.";
  if (persisted === true) return base + " This browser agreed to keep the notebook's storage, but clearing the " +
    "browser's data or uninstalling still deletes what hasn't been sent.";
  if (persisted === false) return base + " This browser did NOT agree to keep its storage, so it may clear it when " +
    "the phone runs low on space. Send often.";
  return base + " This browser can't say whether it will keep its storage. Send often.";
}

// Why a save failed, in words; the entry is NOT kept when this is shown.
export function saveErrorText(err) {
  const name = (err && err.name) || "";
  if (name === "QuotaExceededError")
    return "Not saved: the phone's storage for this notebook is full. Send to the laptop, then free up space.";
  if (name === "ConstraintError")
    return "Not saved: another tab saved an entry at the same moment. Reload the page, then save again.";
  if (name === "InvalidStateError" || name === "TransactionInactiveError" || name === "AbortError")
    return "Not saved: the browser stopped the save (the page was closing or reloading). Save again.";
  return `Not saved: ${(err && err.message) || "the browser refused the write"}.`;
}

// What a send contained, said honestly: unsigned files and photos that weren't on the phone are named.
export function sendSummary({ name, entries, photos, missing = 0, signed }) {
  let s = `Made ${name} (${entries} entr${entries === 1 ? "y" : "ies"}, ${photos} photo${photos === 1 ? "" : "s"}).`;
  if (!signed) s += " NOT SIGNED: this browser can't make a signing key, so Cursiv can check each entry's " +
                    "fingerprint but not that it came from this phone.";
  if (missing) s += ` ${missing} photo${missing === 1 ? " is" : "s are"} no longer stored on this phone and ` +
                    "couldn't be included; Cursiv will list them as missing.";
  return s + " Import it in Cursiv on the laptop.";
}

// Opening the notebook failed: why, and what to do.
export function openErrorText(err) {
  const msg = (err && err.message) || String(err || "");
  if (/indexedDB is not defined|not available|SecurityError|InvalidStateError/i.test(msg + " " + ((err && err.name) || "")))
    return "This browser won't let the notebook store anything (private browsing, or storage turned off), so " +
           "nothing can be saved here. Open it in a normal browser window.";
  return `Couldn't open the notebook on this phone: ${msg}. Nothing has been saved.`;
}

// ── Send file, format 2: a standard zip (no compression: photos are already compressed) ──
//   bundle.json                               {"format": "cursiv-phone-bundle-2", "device": ...}
//   cursiv-field-share/<device>.jsonl         the log, one entry per line
//   cursiv-field-share/<device>.manifest.json the signed head
//   cursiv-field-share/photos/<sha256>.<ext>  each photo, as its own file
// Built from Blob parts: each photo is read once (for its checksum) and then left to the browser.
// Cursiv imports it with fieldsync.import_phone_bundle (which also still reads format 1).
export const ZIP_FORMAT = "cursiv-phone-bundle-2";

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

export function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dosTime(d) {
  return { time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
           date: ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate() };
}

// files: [{name, data: Uint8Array | Blob}]. Returns a Blob.
export async function zipStore(files, now = new Date()) {
  const parts = [], central = [];
  const { time, date } = dosTime(now);
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name);
    const bytes = f.data instanceof Uint8Array ? f.data : new Uint8Array(await f.data.arrayBuffer());
    const crc = crc32(bytes), size = bytes.length;
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true); local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true);
    local.setUint16(8, 0, true); local.setUint16(10, time, true); local.setUint16(12, date, true);
    local.setUint32(14, crc, true); local.setUint32(18, size, true); local.setUint32(22, size, true);
    local.setUint16(26, name.length, true); local.setUint16(28, 0, true);
    parts.push(local.buffer, name, f.data);   // a Blob stays a Blob: the browser reads it when sending
    const cd = new DataView(new ArrayBuffer(46));
    cd.setUint32(0, 0x02014b50, true); cd.setUint16(4, 20, true); cd.setUint16(6, 20, true);
    cd.setUint16(8, 0x0800, true); cd.setUint16(10, 0, true); cd.setUint16(12, time, true); cd.setUint16(14, date, true);
    cd.setUint32(16, crc, true); cd.setUint32(20, size, true); cd.setUint32(24, size, true);
    cd.setUint16(28, name.length, true); cd.setUint32(42, offset, true);
    central.push(cd.buffer, name);
    offset += 30 + name.length + size;
    if (offset > 0xfff00000) throw new Error("too much for one file (over 4 GB): send more often");
  }
  const cdSize = central.reduce((n, p) => n + (p.byteLength ?? p.length), 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  return new Blob([...parts, ...central, end.buffer], { type: "application/zip" });
}

// photos: {rel: Blob}. Returns a Blob (the .cursivsync file).
export async function makeZipBundle(rows, device, keyPair, photos, observer = "", now = new Date()) {
  const b = await makeBundle(rows, device, keyPair, {}, observer, now);
  const dir = "cursiv-field-share/";
  const files = [
    { name: "bundle.json", data: enc.encode(JSON.stringify({ format: ZIP_FORMAT, device, entries: rows.length })) },
    { name: `${dir}${device}.jsonl`, data: enc.encode(rows.map(e => JSON.stringify(e)).join("\n") + (rows.length ? "\n" : "")) },
    { name: `${dir}${device}.manifest.json`, data: enc.encode(JSON.stringify(b.manifest)) },
  ];
  for (const [rel, blob] of Object.entries(photos)) files.push({ name: dir + rel, data: blob });
  return zipStore(files, now);
}

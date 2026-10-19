// Cursiv phone notebook: the screen. The log lives in IndexedDB on this phone; nothing is
// sent anywhere. "Send to laptop" makes one .cursivsync file for Cursiv to import.
import * as core from "./core.js";

const $ = id => document.getElementById(id);
const DB_NAME = "cursiv-notebook";

// ── storage (IndexedDB): entries by seq, photos by name, a few settings ──
function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      db.createObjectStore("entries", { keyPath: "seq" });
      db.createObjectStore("photos");
      db.createObjectStore("meta");
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
let db;
// Writes use "strict" durability: the browser confirms only once the data is on disk, so
// "Saved" means it survives closing the app or the battery dying right after.
const tx = (store, mode = "readonly") =>
  db.transaction(store, mode, mode === "readwrite" ? { durability: "strict" } : undefined).objectStore(store);
// A write is finished when its transaction commits, not when the request succeeds.
const commit = (store, fn) => new Promise((resolve, reject) => {
  const t = db.transaction(store, "readwrite", { durability: "strict" });
  fn(t.objectStore(store));
  t.oncomplete = () => resolve();
  t.onerror = () => reject(t.error);
  t.onabort = () => reject(t.error || new Error("the save was interrupted"));
});
const done = req => new Promise((res, rej) => { req.onsuccess = () => res(req.result); req.onerror = () => rej(req.error); });
const getMeta = k => done(tx("meta").get(k));
const setMeta = (k, v) => done(tx("meta", "readwrite").put(v, k));
const allEntries = async () => (await done(tx("entries").getAll())).sort((a, b) => a.seq - b.seq);

let keyPair = null, device = "", entries = [], pendingPhotos = [], correcting = null;

async function init() {
  db = await openDb();
  if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  keyPair = await getMeta("keyPair");
  if (!keyPair) {
    try {
      keyPair = await core.newKeyPair();
      await setMeta("keyPair", keyPair);        // the private key can't be read out of the phone
    } catch (e) {
      keyPair = null;
      const n = $("unsupported");
      n.textContent = "This browser can't make a signing key (Ed25519), so files from this phone will be unsigned. " +
                      "Cursiv still checks every entry's fingerprint. Updating the browser fixes it.";
      n.classList.remove("hidden");
    }
  }
  device = await getMeta("device");
  if (!device) {
    device = keyPair ? await core.deviceLabel(await core.publicKeyB64(keyPair.publicKey))
                     : "phone-" + core.hex(crypto.getRandomValues(new Uint8Array(6)));
    await setMeta("device", device);
  }
  $("observer").value = (await getMeta("observer")) || "";
  addMeasRow(); addMeasRow();
  entries = await allEntries();
  await render();
  wire();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
}

// ── form ──
function addMeasRow(m = {}) {
  const d = document.createElement("div");
  d.className = "meas";
  d.innerHTML = `<input placeholder="e.g. water temp"><input inputmode="decimal" placeholder="12.40"><input placeholder="°C">`;
  const [n, v, u] = d.querySelectorAll("input");
  n.value = m.name || ""; v.value = m.value || ""; u.value = m.unit || "";
  $("meas").appendChild(d);
}

function readForm() {
  return {
    observer: $("observer").value, site: $("site").value, sample_id: $("sample").value,
    lat: $("lat").value.trim(), lon: $("lon").value.trim(),
    location_source: $("lat").dataset.source || "typed",
    location_accuracy_m: $("lat").dataset.accuracy || null,
    location_fix_utc: $("lat").dataset.fix || "",
    measurements: [...$("meas").children].map(r => {
      const [n, v, u] = r.querySelectorAll("input");
      return { name: n.value, value: v.value, unit: u.value };
    }),
    note: $("note").value,
    photos: pendingPhotos,
  };
}

function clearForm() {
  for (const id of ["site", "sample", "lat", "lon", "note"]) $(id).value = "";
  delete $("lat").dataset.source; delete $("lat").dataset.accuracy; delete $("lat").dataset.fix;
  $("meas").innerHTML = ""; addMeasRow(); addMeasRow();
  pendingPhotos = []; $("thumbs").innerHTML = ""; $("gps-status").textContent = "";
  correcting = null; $("form-title").innerHTML = "<b>New entry</b>";
  $("cancel-correction").classList.add("hidden"); $("save").textContent = "Save entry";
}

function say(text, cls = "") { const s = $("status"); s.textContent = text; s.className = cls; }

async function save() {
  try {
    const f = readForm();
    if (correcting) {
      const reason = prompt(`Why is entry #${correcting.seq} being corrected? (kept with both entries)`);
      if (!reason || !reason.trim()) return;
      f.corrects = correcting.id; f.reason = reason;
      if (!f.photos.length) f.photos = (correcting.photos || []).map(rel => ({ rel }));
    }
    const e = await core.makeEntry(entries, device, f);
    await commit("entries", s => s.add(e));                 // on disk before "Saved" is shown
    await setMeta("observer", f.observer.trim());
    entries.push(e);
    clearForm();
    say(`Saved #${e.seq} · fingerprint ${e.hash.slice(0, 12)}`, "ok");
    await render();
  } catch (err) {
    say(`Not saved: ${err.message}.`, "bad");
  }
}

function gps() {
  const st = $("gps-status");
  if (!navigator.geolocation) { st.textContent = "This browser can't read the GPS."; st.className = "bad"; return; }
  st.textContent = "Getting a GPS fix… (outdoors, sky in view, can take a minute)"; st.className = "muted";
  navigator.geolocation.getCurrentPosition(p => {
    const acc = Math.round(p.coords.accuracy);
    $("lat").value = p.coords.latitude.toFixed(7); $("lon").value = p.coords.longitude.toFixed(7);
    $("lat").dataset.source = "phone GPS";
    $("lat").dataset.accuracy = String(p.coords.accuracy);
    $("lat").dataset.fix = new Date(p.timestamp).toISOString().replace(/\.\d{3}Z$/, "Z");
    st.textContent = `GPS fix: ±${acc} m at ${new Date(p.timestamp).toLocaleTimeString()}`;
    st.className = acc <= 30 ? "ok" : "warn";
  }, err => {
    // No guessing: say there is no fix, and leave the fields as they are.
    st.textContent = err.code === 1 ? "Location permission was refused. Allow it in the phone's settings, or type the coordinates."
                   : "No GPS fix yet. Try again in the open, or type the coordinates.";
    st.className = "bad";
  }, { enableHighAccuracy: true, timeout: 60000, maximumAge: 0 });
}

async function addPhotos(files) {
  for (const file of files) {
    const mb = file.size / 1048576;
    if (mb > 50) { say(`${file.name} is ${mb.toFixed(0)} MB: photos over 50 MB aren't kept.`, "bad"); continue; }
    if (mb > 15) say(`${file.name} is ${mb.toFixed(0)} MB, larger than usual; it's kept, but sending takes longer.`, "warn");
    const buf = await file.arrayBuffer();
    const sha = await core.sha256Hex(buf);
    const ext = { "image/jpeg": ".jpg", "image/png": ".png", "image/heic": ".heic", "image/heif": ".heif",
                  "image/webp": ".webp", "image/gif": ".gif" }[file.type] || ".jpg";
    const rel = `photos/${sha}${ext}`;
    const blob = new Blob([buf], { type: file.type || "image/jpeg" });
    await commit("photos", s => s.put(blob, rel));
    pendingPhotos.push({ rel, name: file.name });
    const img = document.createElement("img"); img.src = URL.createObjectURL(file); $("thumbs").appendChild(img);
  }
  say(`${pendingPhotos.length} photo(s) attached`, "muted");
}

function startCorrection(e) {
  clearForm();
  correcting = e;
  $("form-title").innerHTML = `<b>Correcting #${e.seq}</b> <span class="muted">(the original stays)</span>`;
  $("observer").value = e.observer; $("site").value = e.site; $("sample").value = e.sample_id || "";
  if (e.lat !== null) {
    $("lat").value = e.lat; $("lon").value = e.lon; $("lat").dataset.source = e.location_source;
    if (e.location_accuracy_m != null) $("lat").dataset.accuracy = String(e.location_accuracy_m);
    if (e.location_fix_utc) $("lat").dataset.fix = e.location_fix_utc;
  }
  $("meas").innerHTML = "";
  (e.measurements.length ? e.measurements : [{}, {}]).forEach(addMeasRow);
  $("note").value = e.note;
  $("save").textContent = "Save correction";
  $("cancel-correction").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── list ──
async function render() {
  const cur = core.current(entries);
  const sent = (await getMeta("sentSeq")) || 0;
  const unsent = entries.filter(e => e.seq > sent).length;
  $("count").textContent = `${entries.length} entr${entries.length === 1 ? "y" : "ies"}`;
  $("unsent").textContent = unsent ? `${unsent} not yet sent to the laptop` : "All sent to the laptop";
  $("unsent").className = unsent ? "warn" : "ok";
  const list = $("list"); list.innerHTML = "";
  for (const e of [...cur].reverse()) {
    const div = document.createElement("div"); div.className = "entry";
    const meas = e.measurements.map(m => `${m.name} ${m.value}${m.unit ? " " + m.unit : ""}`).join(", ");
    div.innerHTML = `<b>#${e.seq}</b> <span class="muted">${e.recorded_local.replace("T", " ").slice(0, 16)}</span>` +
      `${e.sample_id ? " · " + esc(e.sample_id) : ""}<div>${esc(e.site)}${e.lat !== null ? ` <span class="muted">(${e.lat}, ${e.lon})</span>` : ""}</div>` +
      (meas ? `<div>${esc(meas)}</div>` : "") + (e.note ? `<div class="muted">${esc(e.note)}</div>` : "") +
      (e.photos.length ? `<div class="muted">📷 ${e.photos.length}</div>` : "") +
      (e.corrects ? `<div class="muted">corrects an earlier entry: ${esc(e.reason)}</div>` : "");
    const b = document.createElement("button"); b.className = "small"; b.textContent = "Correct";
    b.onclick = () => startCorrection(e); div.appendChild(b);
    list.appendChild(div);
  }
  const problems = await core.chainProblems(entries);
  $("about").innerHTML = `Device: <code>${device}</code><br>` +
    (keyPair ? `Signing key: <code>${await core.keyId(await core.publicKeyB64(keyPair.publicKey))}</code><br>` : "Not signed (see above)<br>") +
    (problems.length ? `<span class="bad">The log has problems: ${esc(problems[0])}</span>` : `<span class="ok">Every entry intact and in order.</span>`) +
    "<br>Stored only in this browser on this phone. Send to the laptop regularly: clearing the browser's data, " +
    "or uninstalling, deletes what hasn't been sent.";
}
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ── send to the laptop ──
async function send() {
  if (!entries.length) { say("Nothing to send yet.", "muted"); return; }
  say("Preparing the file…", "muted");
  const photos = {};
  for (const e of entries) for (const rel of e.photos) {
    const blob = await done(tx("photos").get(rel));
    if (blob) photos[rel] = blob;
  }
  const zip = await core.makeZipBundle(entries, device, keyPair, photos, $("observer").value.trim());
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
  const name = `cursiv-${device}-${stamp}.cursivsync`;
  const file = new File([zip], name, { type: "application/zip" });
  try {
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: name });
    } else {
      const a = document.createElement("a"); a.href = URL.createObjectURL(file); a.download = name; a.click();
    }
    await setMeta("sentSeq", entries[entries.length - 1].seq);
    say(`Made ${name} (${entries.length} entries, ${Object.keys(photos).length} photos). Import it in Cursiv on the laptop.`, "ok");
    await render();
  } catch (err) {
    if (err.name !== "AbortError") say(`Couldn't share the file: ${err.message}`, "bad");
  }
}

async function newSampleId() {
  const words = ($("site").value.match(/[A-Za-z0-9]+/g) || []).slice(0, 3);
  const prefix = words.map(w => w[0]).join("").toUpperCase() || "S";
  const d = new Date(), p = n => String(n).padStart(2, "0");
  const day = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
  const taken = new Set(entries.map(e => e.sample_id));
  let n = 1;
  while (taken.has(`${prefix}-${day}-${String(n).padStart(3, "0")}`)) n++;
  $("sample").value = `${prefix}-${day}-${String(n).padStart(3, "0")}`;
}

function wire() {
  $("save").onclick = save;
  $("gps").onclick = gps;
  $("add-meas").onclick = () => addMeasRow();
  $("add-photo").onclick = () => $("photo-input").click();
  $("photo-input").onchange = e => { addPhotos([...e.target.files]); e.target.value = ""; };
  $("cancel-correction").onclick = clearForm;
  $("send").onclick = send;
  $("new-id").onclick = newSampleId;
}

init().catch(err => say(`Couldn't open the notebook on this phone: ${err.message}`, "bad"));

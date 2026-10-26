// Keeps the notebook working with no signal: its own files are cached on first visit and
// served from the cache after that. It never sends anything; it only serves these files.
const CACHE = "cursiv-notebook-v4";   // bump when cached HTML/JS changes, so phones receive the update
const FILES = ["./", "./index.html", "./app.js", "./core.js", "./manifest.webmanifest", "/assets/cursiv-logo-256.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Cache first; when online, refresh the cache in the background so updates arrive.
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(hit => {
    const fresh = fetch(e.request).then(res => {
      if (res.ok && new URL(e.request.url).origin === location.origin) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    }).catch(() => hit);
    return hit || fresh;
  }));
});

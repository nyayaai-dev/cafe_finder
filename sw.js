// Offline cache for the installed app. build/build.py stamps 772f75acc8 on
// every build, so a new deploy replaces the old cache automatically.
const CACHE = "cafe-finder-772f75acc8";
const CORE = ["./", "index.html", "data/places.js", "data/basemap.js", "manifest.webmanifest", "install.html", "icons/icon-192.png", "icons/icon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k.startsWith("cafe-finder-") && k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.includes("/api/")) return;                      // live lookups always go to the network
  const sameOrigin = url.origin === location.origin;
  const allowed = sameOrigin || /cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(url.host);
  if (!allowed) return;

  // Pages and the site's own data: network first, checked with the server every time
  // ("no-cache" skips the browser's 10-minute GitHub Pages cache), cached copy when offline.
  if (req.mode === "navigate" || (sameOrigin && /\.(js|json|webmanifest)$/.test(url.pathname) && !url.pathname.endsWith("/sw.js"))) {
    e.respondWith(fetch(req, { cache: "no-cache" }).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then((r) => r || (req.mode === "navigate" ? caches.match("index.html") : undefined))));
    return;
  }
  // Everything else (map library, fonts, icons): cache first, refresh in the background.
  e.respondWith(caches.match(req).then((hit) => {
    const net = fetch(req).then((res) => {
      if (res && (res.ok || res.type === "opaque")) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
});

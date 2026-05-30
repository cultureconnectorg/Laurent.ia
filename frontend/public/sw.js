/* Laurent.ia Service Worker — cache shell léger pour offline graceful */
const CACHE = "laurentia-shell-v1";
const ASSETS = ["/"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).catch(() => null));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  // Ne jamais cacher l'API
  if (req.url.includes("/api/")) return;
  e.respondWith(
    fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => null);
      return res;
    }).catch(() => caches.match(req).then((m) => m || new Response("Hors-ligne — réessaie quand tu auras du réseau.", { status: 503 })))
  );
});

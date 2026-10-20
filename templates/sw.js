// Lets the app open from the phone's home screen and shows a friendly page when there's no internet.
const CACHE = "church-events-v1";
const OFFLINE = "{{ offline_url }}";
const ASSETS = [OFFLINE{% for a in assets %}, "{{ a }}"{% endfor %}];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  // Pages: always try the network first, so statuses are never stale.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match(OFFLINE)));
    return;
  }
  // Styles and scripts: use the saved copy, refresh it in the background.
  if (ASSETS.includes(new URL(req.url).pathname)) {
    event.respondWith(
      caches.match(req).then((hit) => {
        const fresh = fetch(req).then((res) => {
          caches.open(CACHE).then((c) => c.put(req, res.clone()));
          return res;
        });
        return hit || fresh;
      })
    );
  }
});

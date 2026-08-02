/* RawTrainer service worker.
 *
 * Job: make the app installable and instant/offline for its *shell* (the HTML,
 * icons, fonts). It deliberately NEVER caches or interferes with /api/ — that is
 * live user data plus mutations (import, delete, save-run), and stale data there
 * would be worse than useless.
 *
 * When you change any precached asset, bump VERSION so clients pick it up.
 */
const VERSION = "rt-v1";
const SHELL = "rt-shell-" + VERSION;
const RUNTIME = "rt-runtime-" + VERSION;

const CORE = [
  "/",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-512-maskable.png",
  "/icons/apple-touch-icon.png",
  "/icons/favicon-32.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL).then((cache) => cache.addAll(CORE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== SHELL && k !== RUNTIME).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                 // never touch mutations
  const url = new URL(req.url);

  // The API is always live. Do not intercept, do not cache.
  if (url.origin === location.origin && url.pathname.startsWith("/api/")) return;

  // App launches / navigations: network-first so deploys show up immediately,
  // falling back to the cached shell so the app still opens with no signal.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(SHELL).then((cache) => cache.put("/", copy));
          return res;
        })
        .catch(() => caches.match("/", { ignoreSearch: true }).then((r) => r || caches.match(req)))
    );
    return;
  }

  // Same-origin static assets (icons, manifest): cache-first.
  if (url.origin === location.origin) {
    event.respondWith(
      caches.match(req).then((hit) =>
        hit || fetch(req).then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(SHELL).then((cache) => cache.put(req, copy));
          }
          return res;
        })
      )
    );
    return;
  }

  // Google Fonts (cross-origin): stale-while-revalidate.
  if (url.host.endsWith("googleapis.com") || url.host.endsWith("gstatic.com")) {
    event.respondWith(
      caches.open(RUNTIME).then((cache) =>
        cache.match(req).then((hit) => {
          const net = fetch(req)
            .then((res) => { if (res.ok) cache.put(req, res.clone()); return res; })
            .catch(() => hit);
          return hit || net;
        })
      )
    );
    return;
  }
  // Anything else: let the network handle it.
});

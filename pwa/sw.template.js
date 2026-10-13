/* YÖKDİL Fen service worker — offline app shell. __BUILD_ID__ is replaced at build time. */
const BUILD_ID = '__BUILD_ID__';
const CACHE = `yokdil-shell-${BUILD_ID}`;
const SCOPE_URL = new URL(self.registration.scope);

function inScope(url) {
  return url.origin === SCOPE_URL.origin && url.pathname.startsWith(SCOPE_URL.pathname);
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      const indexUrl = new URL('./', SCOPE_URL).href;
      const res = await fetch(indexUrl, { cache: 'reload' });
      const html = await res.clone().text();
      const urls = new Set([indexUrl, new URL('manifest.webmanifest', SCOPE_URL).href]);
      for (const m of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
        const u = new URL(m[1], indexUrl);
        if (inScope(u)) urls.add(u.href);
      }
      await cache.put(indexUrl, res);
      await Promise.all(
        [...urls]
          .filter((u) => u !== indexUrl)
          .map(async (u) => {
            try {
              await cache.add(u);
            } catch {
              /* optional resource; ignore */
            }
          }),
      );
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k.startsWith('yokdil-shell-') && k !== CACHE).map((k) => caches.delete(k)));
      await self.clients.claim();
    })(),
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (!inScope(url)) return;

  // Page loads: network first (always get the newest version when online), cached shell offline.
  if (req.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          const fresh = await fetch(req);
          const cache = await caches.open(CACHE);
          cache.put(new URL('./', SCOPE_URL).href, fresh.clone());
          return fresh;
        } catch {
          const cached = await caches.match(new URL('./', SCOPE_URL).href);
          return cached || Response.error();
        }
      })(),
    );
    return;
  }

  // Everything else in scope (hashed assets, icons, manifest): cache first, fill on miss.
  event.respondWith(
    (async () => {
      const cached = await caches.match(req);
      if (cached) return cached;
      const res = await fetch(req);
      if (res.ok && res.type === 'basic') {
        const cache = await caches.open(CACHE);
        cache.put(req, res.clone());
      }
      return res;
    })(),
  );
});

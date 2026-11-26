/* 小暖的诗集 · 离线缓存 Service Worker */
const CACHE = 'nuanshi-v1';
const BASE = self.registration ? self.registration.scope : self.location.href;

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      const res = await fetch('./precache-manifest.json', { cache: 'no-store' });
      if (res.ok) {
        const list = await res.json();
        await cache.addAll(list.map((p) => new URL(p, BASE).href));
      }
    } catch (err) {
      /* 首次装不上就退回运行时缓存 */
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  let url;
  try {
    url = new URL(req.url);
  } catch {
    return;
  }
  if (url.origin !== self.location.origin) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req, { ignoreSearch: false });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res.ok && res.type === 'basic') cache.put(req, res.clone());
      return res;
    } catch (err) {
      if (req.mode === 'navigate') {
        const fallback = await cache.match(new URL('index.html', BASE).href);
        if (fallback) return fallback;
      }
      throw err;
    }
  })());
});

// Service worker: offline shell for /wallet/.
//
// Only same-origin GET requests under /wallet/ are handled; RPC POSTs, /auth/*
// and "/" never pass through here. Network first (3 s timeout), falling back
// to the cache; successful responses refresh the cache. The cache name carries
// the bundle version, which tools/pack.mjs writes into VERSION ("dev" in src/).

const VERSION = 'dev';
const CACHE = `node-pwa-${VERSION}`;
const SCOPE = new URL('./', self.location).pathname; // "/wallet/"

// Precached in development; release bundles precache every file listed in BUNDLE.json.
const PRECACHE = [
  '', 'index.html', 'app.css', 'main.js', 'app.js', 'router.js', 'manifest.webmanifest',
  'lib/mining-hashes.js', 'mining/sha256d.wgsl', 'mining/blake3.wgsl',
  'lib/chainconfig.js', 'lib/amount.js', 'lib/consoleparse.js', 'lib/json.js', 'lib/poller.js', 'lib/profile.js', 'lib/rpc.js',
  'lib/session.js', 'lib/storage.js', 'lib/store.js', 'lib/uri.js', 'lib/xpiaddr.js',
  'ui/address.js', 'ui/components.js', 'ui/layout.js',
  'views/console.js', 'views/login.js', 'views/nodeinfo.js', 'views/offline.js', 'views/overview.js',
  'views/messages.js', 'views/peers.js', 'views/receive.js', 'views/send.js', 'views/transactions.js', 'views/wallets.js',
  'vendor/htm-preact-standalone.mjs', 'vendor/qrcodegen.mjs',
  'icons/icon.svg', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/maskable-512.png',
];

async function fileList() {
  if (VERSION === 'dev') return PRECACHE;
  const resp = await fetch(`${SCOPE}BUNDLE.json`, { cache: 'no-store' });
  const bundle = await resp.json();
  return ['', ...Object.keys(bundle.files)];
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const files = await fileList();
    // Individual failures must not break installation (e.g. a file removed in dev).
    await Promise.all(files.map((f) => cache.add(new Request(SCOPE + f, { cache: 'no-store' })).catch(() => {})));
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key.startsWith('node-pwa-') && key !== CACHE) await caches.delete(key);
    await self.clients.claim();
  })());
});

self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(SCOPE)) return;
  event.respondWith(networkFirst(req));
});

async function networkFirst(req) {
  const cache = await caches.open(CACHE);
  const key = new Request(new URL(req.url).pathname); // ignore query strings
  try {
    const resp = await withTimeout(fetch(req), 3000);
    if (resp.ok) await cache.put(key, resp.clone());
    return resp;
  } catch {
    const hit = await cache.match(key);
    if (hit) return hit;
    return new Response('offline', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
}

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('timeout')), ms);
    promise.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
  });
}

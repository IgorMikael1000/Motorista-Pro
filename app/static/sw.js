const CACHE_NAME = 'motoristapro-v1-glass-fix-pwa';
const ASSETS_TO_CACHE = [
  '/',
  '/offline.html',
  '/static/style.css',
  '/static/js/pwa.js',
  '/static/js/onboarding.js',
  '/static/js/tour.js',
  '/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap',
  'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&display=swap',
  'https://unpkg.com/htmx.org@1.9.10',
  'https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js',
  'https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',
  'https://cdn.jsdelivr.net/npm/flatpickr/dist/themes/airbnb.css',
  'https://cdn.jsdelivr.net/npm/flatpickr',
  'https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/pt.js',
  'https://cdn.jsdelivr.net/npm/flatpickr/dist/plugins/weekSelect/weekSelect.js'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Cache aberto');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Removendo cache antigo:', key);
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Cache First para Estáticos
  if (
    url.pathname.startsWith('/static') ||
    url.href.includes('cdnjs') ||
    url.href.includes('fonts.') ||
    url.href.includes('unpkg') ||
    url.href.includes('cdn.jsdelivr')
  ) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) return cachedResponse;
        return fetch(event.request).then((networkResponse) => {
          return caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
        });
      })
    );
    return;
  }

  // Network First para HTML
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/offline.html'))
    );
  }
});




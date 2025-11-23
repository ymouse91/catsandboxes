const CACHE_NAME = 'catsandboxes-v2';
const FILES_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './pwa_icon_180.png',
  './pwa_icon_192.png',
  './pwa_icon_512.png',
  './cats_boxes_puzzles.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(FILES_TO_CACHE))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

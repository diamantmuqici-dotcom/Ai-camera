const CACHE = "pixel-ai-camera-v1";
const FILES = [
  "./",
  "./index.html",
  "./pixel-ai-camera.html",
  "./cam-test.html",
  "./manifest.webmanifest",
  "./camera-utils.js",
  "./detector-worker.js",
  "./styles.css",
  "./camera-core.js",
  "./processing-worker.js",
  "./readers.js",
  "./tracking.js",
  "./app.js"
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => key !== CACHE).map(key => caches.delete(key))
  )));
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  event.respondWith(caches.match(event.request).then(cached =>
    cached || fetch(event.request).then(response => {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
      return response;
    })
  ));
});

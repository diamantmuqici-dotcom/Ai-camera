const CACHE="pixel-ai-camera-v3";
const FILES=[
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
  "./app.js",
  "./settings.json"
];

self.addEventListener("install",event=>{
  event.waitUntil(
    caches.open(CACHE)
      .then(cache=>cache.addAll(FILES))
      .catch(()=>{})
  );
  self.skipWaiting();
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys().then(keys=>Promise.all(
      keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET") return;
  const url=new URL(event.request.url);
  if(url.origin!==location.origin) return;

  event.respondWith(
    caches.match(event.request).then(cached=>{
      const network=fetch(event.request).then(response=>{
        if(response&&response.ok){
          const copy=response.clone();
          caches.open(CACHE).then(cache=>cache.put(event.request,copy)).catch(()=>{});
        }
        return response;
      }).catch(()=>cached);

      // App shell stays available offline; fresh assets update in background.
      return cached||network;
    })
  );
});

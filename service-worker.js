const CACHE="pixel-ai-camera-v6";
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
  "./adaptive-engine.js",
  "./camera-lens-router.js",
  "./settings.json",
  "./core/camera-capabilities.js","./core/device-profile.js","./core/camera-session.js","./core/camera-manager.js","./core/lens-manager.js","./core/zoom-engine.js","./core/gesture-engine.js","./core/app-controller.js",
  "./diagnostics/performance-monitor.js","./diagnostics/capability-report.js","./diagnostics/debug-console.js","./diagnostics/camera-diagnostics.js","./diagnostics/device-report.js",
  "./storage/settings-store.js","./storage/gallery-db.js","./storage/export-manager.js",
  "./processing/processing-queue.js","./processing/enhancement-engine.js","./processing/upscale-engine.js","./processing/pipeline.js","./capture/capture-manager.js","./diagnostics/startup-diagnostics.js","./privacy.html","./package.json","./capacitor.config.json",
  "./vision/vision-engine.js","./vision/scene-analyzer.js","./vision/subject-tracker.js","./vision/person-tracker.js","./vision/car-tracker.js","./vision/plate-detector.js","./vision/document-detector.js",
  "./capture/burst-capture.js","./capture/video-capture.js",
  "./workers/tracking-worker.js","./workers/super-resolution-worker.js",
  "./tests/unit.js","./test-harness.html",
  "./css/app.css","./css/camera.css","./css/controls.css","./css/panels.css","./css/gallery.css","./css/responsive.css",
  "./icons/icon-192.svg","./icons/icon-512.svg"
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

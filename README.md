# Pixel AI Camera

A local-first computational camera for Android Chrome, Pixel devices, and desktop browsers.

The project is deliberately **capability-driven**: it uses hardware features only when the browser exposes them and labels software fallbacks honestly.

## Architecture

The original prototype remains compatible, but the repository now has a modular foundation around the existing camera UI:

```text
core/
  app-controller.js
  camera-manager.js
  camera-capabilities.js
  camera-session.js
  device-profile.js
  lens-manager.js
  zoom-engine.js
  gesture-engine.js

processing/
  enhancement-engine.js
  processing-queue.js
  processing-worker.js
  super-resolution-worker.js

vision/
  vision-engine.js
  scene-analyzer.js
  subject-tracker.js
  person-tracker.js
  car-tracker.js
  plate-detector.js
  document-detector.js

capture/
  burst-capture.js
  video-capture.js

storage/
  settings-store.js
  gallery-db.js
  export-manager.js

diagnostics/
  performance-monitor.js
  camera-diagnostics.js
  capability-report.js
  device-report.js
  debug-console.js

workers/
  tracking-worker.js
  super-resolution-worker.js

css/
  app.css
  camera.css
  controls.css
  panels.css
  gallery.css
  responsive.css
```

The existing `pixel-ai-camera.html` still owns the mature UI/capture implementation, while new services provide reusable primitives for gradually moving responsibilities out of the monolith without breaking the working camera.

## Current capabilities

- Rear/front camera access with graceful fallbacks.
- Capability inspection for resolution, frame rate, zoom, focus, exposure, torch and white balance.
- Hardware zoom when exposed by the browser.
- Digital crop fallback when hardware zoom is unavailable.
- Real ultrawide routing only when a separate ultrawide camera input is exposed.
- Pinch-to-zoom, double-tap, mouse-wheel, keyboard, presets and slider zoom.
- Smooth zoom interpolation with bounded values.
- Adaptive resolution/FPS requests with cooldowns.
- Fast Shot: original capture can be saved before enhancement finishes.
- Background processing with worker backpressure.
- Burst capture and best-frame scoring infrastructure.
- Video/MediaRecorder capability detection and codec fallback.
- Local IndexedDB gallery in the existing application.
- Lazy OCR path in the existing application.
- Scene/quality heuristics and stability guidance.
- Visual/template tracking without identity recognition.
- PWA/offline shell with versioned cache.
- Capability diagnostics and a standalone test harness.
- Responsive OLED-style camera UI with safe-area and reduced-motion support.
- No analytics and no intentional camera upload pipeline.

## Zoom and lens reality

Zoom states are intentionally distinguishable:

- **HW** — browser-exposed camera zoom capability.
- **DIGITAL** — crop/resampling beyond hardware zoom.
- **AI/COMPUTATIONAL** — processing intended to improve the appearance of a digital crop; it does not create missing optical detail.

A web page cannot force Chrome to expose a hidden Pixel ultrawide or telephoto camera. A 0.5× button can only switch to a genuinely exposed ultrawide input. Otherwise the app reports that hardware is unavailable instead of pretending.

Pinch zoom is handled through pointer events with explicit multi-pointer state, cancellation, tap suppression and distance-based scaling.

## Computational photography

The current pipeline includes practical browser processing such as exposure/tone adjustment, denoise/sharpening paths, HDR-style exposure capture where controls permit it, and multi-frame capture infrastructure.

The repository **does not pretend ordinary sharpening is AI super-resolution**. The SR worker is an explicit extension point for a real alignment/ML model.

## AI / ML

The architecture is ready for lazy browser inference through a dedicated vision layer. No large ML model is bundled by default.

When no model is installed:

- native/heuristic analysis can still operate;
- tracking falls back to the application's visual/template mechanisms;
- model-dependent detection reports unavailable rather than returning fabricated detections.

This keeps the initial load small and avoids silently downloading large models.

## Performance

The live preview has priority over heavy processing.

- Preview is driven by `requestAnimationFrame`.
- Analysis and tracking run at bounded frequencies.
- Workers use transferable buffers where applicable.
- Stale work is dropped instead of building an unlimited queue.
- Adaptive camera changes have cooldowns.
- Performance monitoring tracks observable video frames and dropped frames.
- The app can fall back toward a lower-cost profile after sustained preview degradation.

## Camera API limitations

Browser camera APIs differ across Android versions, Pixel models and browsers.

The application cannot reliably expose true manual ISO, shutter speed, RAW capture, physical stabilization control, or hidden multi-camera hardware unless the browser provides the corresponding API.

Likewise, a requested 4K/60 mode is not a guarantee that the camera will actually deliver 4K/60. The app reads the resulting track settings and diagnostics.

## Privacy

Camera processing and the local gallery are designed to stay on-device.

There is no analytics system and no identity database.

OCR resources that are intentionally loaded from an external provider are separate from the local gallery. External model loading should be treated as an explicit network dependency.

## PWA / offline

The service worker caches the application shell and modular runtime files. The manifest includes local SVG icons and shortcuts.

Offline support is strongest for the core camera UI and local processing. Features that explicitly depend on an external OCR/model download still require that resource to have been cached previously.

## Testing

### Camera lab

Open:

`cam-test.html`

It probes:

- camera inputs
- actual track settings
- capability ranges
- zoom
- focus
- exposure
- torch
- frame rate
- ImageCapture
- MediaRecorder
- WebGPU
- WebAssembly
- workers
- storage

### Unit test harness

Open:

`test-harness.html`

It runs deterministic tests for:

- zoom clamping
- pinch math
- lens classification
- OCR plate heuristics
- scene analysis

## Android / Pixel setup

1. Deploy the repository over HTTPS, such as GitHub Pages.
2. Open the camera page in Chrome on the Pixel.
3. Grant camera permission.
4. Use `cam-test.html` before debugging a device-specific feature.
5. Install the PWA from Chrome when offered.

Camera access requires a secure context such as HTTPS or localhost.

## GitHub Pages

Enable GitHub Pages from the repository's **Settings → Pages** section and deploy the `main` branch.

## Development principles

- Preserve working behavior before replacing it.
- Prefer browser capability detection over user-agent assumptions.
- Keep preview responsive.
- Never fabricate hardware or ML support.
- Keep expensive work asynchronous.
- Bound queues and memory.
- Keep storage local.
- Fail one subsystem without crashing the whole camera.

## Roadmap

The modular foundation now makes it practical to add:

- real browser ML models loaded on demand;
- geometric document detection and perspective correction;
- true multi-frame alignment;
- temporal plate OCR voting;
- stronger device-specific performance calibration;
- richer local gallery metadata;
- more complete automated browser/device tests.

Those features should only be promoted to **available** once their underlying implementation and browser/device support are real.

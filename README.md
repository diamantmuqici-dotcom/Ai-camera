# Pixel AI Camera

A local-first computational camera for Android Chrome and desktop browsers.

## What this build does

- Uses the browser camera API with capability-aware constraints and safe fallbacks.
- Prefers 1080p/60 FPS for a responsive preview when the device exposes it.
- Uses browser-exposed hardware zoom when available and digital crop zoom above it.
- Automatically adapts camera resolution/FPS as zoom, motion, battery state and device capabilities change.
- Includes an HD capture path that preserves the highest practical source resolution without inventing detail.
- Automatically routes 0.5× to a genuinely exposed ultrawide camera when the browser exposes one.
- Does not claim a real 0.5x ultrawide lens unless Android/Chrome actually exposes a separate camera.
- Keeps preview rendering lightweight and throttles expensive analysis/tracking independently.
- Uses bounded background processing for capture enhancement and multi-frame workflows.
- Supports HDR and multi-frame super-resolution workflows where the browser can provide the required frames.
- Includes visual subject tracking with explicit 'no identity recognition' behavior.
- Includes plate/text helper logic with temporal candidate stabilization; OCR itself depends on the OCR engine available to the app.
- Fast Shot can save the original before enhancement completes.
- Stores captures locally in IndexedDB.
- Includes a PWA shell and versioned offline cache.
- Includes camera diagnostics and a camera test page.
- Does not upload captures or include analytics.

## Important reality checks

A web app cannot manufacture camera hardware features that Chrome does not expose.

- A real ultrawide/0.5x view requires an ultrawide camera to be exposed as a selectable video input. No web application can force a browser to expose hidden camera hardware.
- Digital zoom is cropping/resampling. It cannot recreate detail that was never captured.
- Browser camera capabilities differ between Pixel models, Chrome versions and Android releases.
- True ISO/shutter controls are not generally exposed through this app's browser API.
- The included tracker is visual/template tracking, not face recognition, identity recognition, or a trained object detector.
- No external ML model is bundled in this repository, so the detector worker intentionally reports that ML detection is unavailable instead of pretending otherwise.
- OCR may require a network download for its engine/language data unless the browser already has the required resource cached.

## Performance architecture

The preview path is intentionally separated from heavier work:

1. Native camera video presents the live stream.
2. Hardware zoom is applied only when the camera exposes a zoom capability.
3. Digital crop/processing is throttled rather than recalculated unnecessarily.
4. Histogram/sharpness analysis runs at a lower rate than preview rendering.
5. Visual tracking runs at a bounded rate and reuses its working canvas.
6. Capture enhancement can run asynchronously so the original can be saved first.
7. The app reacts to sustained low preview FPS by moving toward a lower-cost processing profile.

For a Pixel, start with:

- 1080p
- 60 FPS if exposed
- Balanced performance
- Fast Shot enabled
- Higher-quality enhancement for final captures rather than continuously processing the live preview

## Files

This repository intentionally keeps the existing file layout:

    index.html
    pixel-ai-camera.html
    cam-test.html
    README.md
    manifest.webmanifest
    service-worker.js
    camera-utils.js
    detector-worker.js
    settings.json
    styles.css
    camera-core.js
    processing-worker.js
    readers.js
    tracking.js
    app.js
    adaptive-engine.js
    camera-lens-router.js

No additional model directory or generated dependency file is required by this build.

## GitHub Pages

Enable:

**Settings → Pages → Deploy from branch → main → /root**

Then open the HTTPS GitHub Pages address for the repository.

HTTPS (or localhost) is required by browsers for camera access.

## Local Android testing

The existing camera test page is:

    cam-test.html

It reports secure-context status, camera permission failures, selected track settings and the active preview.

## Privacy

Camera frames and captures are processed locally by the web application.

The project does not intentionally send camera captures to a server, include analytics, maintain an identity database, or perform background surveillance.

Third-party OCR resources, when enabled by the browser/app, are separate from the camera application's local gallery and should be considered when using offline mode.

## Development notes

The code is dependency-light and deliberately defensive around browser capability differences. Features are only advertised as hardware-backed when the corresponding browser capability or camera input is actually present.

Do not interpret a software enhancement, crop zoom, sharpening pass, or tracking box as evidence of additional camera hardware or an ML model that is not present.

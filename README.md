# Pixel AI Camera

A browser-based computational camera for Android Chrome and desktop browsers.

## Features

- Local camera preview and photo/video capture
- Rear/front camera switching
- Hardware zoom when exposed by the browser
- Digital zoom above the hardware limit
- Real 0.5x ultrawide support when the browser exposes an ultrawide camera
- Live brightness, contrast, saturation, and sharpening
- HDR and multi-frame Super Resolution
- Long Zoom mode
- Person Follow and Car Follow visual tracking
- Tap-to-focus and continuous autofocus when supported
- License plate enhancement and OCR
- Smart Plate mode: steady high-zoom automatic plate capture and OCR
- Fast Shot mode: saves the original immediately and enhances in the background
- Auto Pro: zoom-aware focus distance, exposure, gamma, contrast, color, sharpening, and denoise
- Sign reader and OCR
- Document scanner
- Local IndexedDB gallery
- Local browser processing; captures are not uploaded by the app
- Installable PWA shell with offline caching
- Optional detector worker bridge for future local ML models

## GitHub Pages

Upload these files to a public GitHub repository:

```text
index.html
pixel-ai-camera.html
cam-test.html
README.md
manifest.webmanifest
service-worker.js
camera-utils.js
detector-worker.js
settings.json
models/README.md
styles.css
camera-core.js
processing-worker.js
readers.js
tracking.js
app.js
```

Enable **Settings > Pages > Deploy from branch > main > /root**.

Open the generated HTTPS address:

```text
https://YOUR_USERNAME.github.io/YOUR_REPOSITORY/
```

HTTPS is required for camera access without ADB.

## Local Android Testing With ADB

From PowerShell:

```powershell
cd "C:\Users\diama\Downloads\Better Camera More Features"
.\start-camera.ps1
```

Then open this address on the Pixel:

```text
http://127.0.0.1:8080/pixel-ai-camera.html
```

The launcher finds Platform-Tools, checks the authorized device, and creates the ADB reverse tunnel.

## Performance

For smoother Pixel preview:

- Use 1080p instead of 1440p or 4K.
- Select 60 FPS when the camera exposes it.
- Use Balanced performance mode.
- Use High enhancement for final captures rather than Max Quality during live preview.
- Plate and sign readers use capped working images to avoid mobile memory spikes.

The live Pixel preview uses the native video path for smoothness. Expensive enhancement is reserved for captures and reader workflows.

Normal Photo mode uses Fast Shot by default: the original is saved immediately, then the enhanced version replaces it in the local gallery when processing finishes. HDR and Super Resolution remain slower because they capture multiple frames by design.

## Limitations

- A browser cannot create a real 0.5x view if Android Chrome does not expose the ultrawide camera.
- Digital zoom cannot recover detail that the sensor did not capture.
- Person and Car Follow are visual template tracking, not identity recognition or object detection.
- Smart Plate captures only when enabled, the view is at least 4x, and the frame is steady.
- The browser can read plate text but cannot reliably identify a vehicle make or model without a trained detection model.
- OCR downloads its language model once and may require network access.
- Camera controls depend on capabilities exposed by the browser and device.
- Auto Pro uses browser-supported exposure compensation and focus distance; Chrome does not expose true ISO or shutter speed controls for this app.

## Privacy

Camera processing happens locally in the browser. The app does not include analytics, facial recognition, identity databases, or background tracking.

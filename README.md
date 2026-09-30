# ClarityCam V2

**Two native camera apps — not a web site, PWA, Electron window or WebView.** The old browser implementation was removed. Install the Android APK or unzip the Windows app and run `ClarityCam.exe`.

## Download / install

The [**Build ClarityCam V2 native apps** workflow](../../actions/workflows/native-v2.yml) produces two downloadable artifacts on every push and on manual dispatch:

| Device | Artifact | Install |
| --- | --- | --- |
| Android 10+ | `ClarityCam-V2-Android-APK` → `app-debug.apk` | Download APK, allow installation from that source, install, grant **Camera**. This is a debug-signed test build; updates must use the same signing key or be reinstalled. |
| Windows 10/11 x64 | `ClarityCam-V2-Windows-EXE` → `ClarityCam-V2-Windows.zip` | Extract **the entire zip** into a folder and open `ClarityCam.exe`. Keep the included `_internal` folder next to the EXE. No Python, browser, account or separate OCR install needed. |

These builds are development builds, not a signed store release or Windows installer. If Windows SmartScreen warns about an unsigned app, verify that you downloaded it from this repository's Actions run. Camera access on Windows may require enabling **Settings → Privacy & security → Camera → Let desktop apps access your camera**.

## What V2 actually does

- **Responsive preview:** Android uses CameraX preview with latest-frame-only ImageAnalysis; Windows reads camera frames on a dedicated thread, paints at up to 30 FPS and runs OCR on another single-slot worker. Requested 30/60 FPS depends on camera/driver; the displayed number is *observed input FPS*, not a promise of 60.
- **Offline text/plate candidates:** Android bundles ML Kit's on-device Latin text recognizer. Windows packages Tesseract English OCR. A conservative rule highlights plate-*like OCR lines* in green and text in blue; these are candidates, **not proof of a plate or verified registration**. Tap/click to copy text and verify characters yourself. No identities, plate lookup, accounts or server inference.
- **Auto snap while zoomed:** Enable AUTO and zoom to the chosen threshold (2× by default). Three matching readings in the same location and a reasonably clear frame trigger one photo. Same-text cooldown is 18 seconds; other captures are separated by at least 5 seconds. Manual shutter always works. The app does not photograph every zoom gesture or save uncontrollably.
- **Honest 0.5×:** Android enables it only when CameraX exposes a sub-1× logical camera zoom or a separately selectable rear ultrawide with an approximately half-width focal length. Windows requires you to **assign a separate physical ultrawide webcam index** in Camera Hardware. Without one, 0.5× stays disabled; a digital crop cannot widen a view. Other zoom levels use device zoom on Android and sensor crops on Windows. Neither is labeled optical super-resolution.
- **Image Lab:** Gamma, contrast, highlights, shadows, clarity, noise reduction, and color can be adjusted. Night/Text/Neutral presets are on Windows. Changes affect OCR input and enhanced JPEGs on both systems. Windows applies lightweight grading to live preview; Android keeps preview native/fast and camera EV is the live-preview exposure control when hardware supports it. Highlight tuning compresses tones but **cannot recover clipped sensor detail**.
- **Photos in your own library:** Android writes an enhanced JPEG (up to ~12 MP for safe processing memory) **and an untouched full-resolution original** to `Pictures/ClarityCam` via MediaStore. Windows writes an enhanced full-frame photo, an honest zoomed detail crop (when zoomed) and a local JSON sidecar (which includes OCR candidate text) to `Pictures/ClarityCam`. Webcam capture resolution is whatever the webcam actually supplies. Keep/delete files using your normal file/gallery app.
- **No empty black-screen failure:** Both apps show camera permission, connection, timeout and error information with Retry. A nearly black webcam feed on Windows also produces an actionable lens/privacy/lighting warning. Android asks for camera permission and links to app settings if denied. No camera? The camera UI still opens to a recovery screen.

### Limits that matter

A text line resembling a plate is not a dedicated plate-object detector; plates with unusual regional layouts, poor focus, reflections, motion or non-Latin characters may be missed or misread. Auto snap requires a sharp enough OCR frame, and some camera lenses/60 FPS settings are not exposed by the OS. Android preview box alignment is approximate because camera preview and analysis can use different crops. The Windows camera chooser uses camera **indices**, not manufacturer lens labels. A webcam that does not provide a wide field of view cannot produce one by software.

## Privacy

Camera frames and photos stay on the device. The Android manifest requests **CAMERA only** (no INTERNET, location, microphone or photo-library read permission). Windows OCR is bundled into the portable app; there is no runtime model download or intentional network/analytics code. Android photos are visible to other gallery apps through MediaStore. Windows JSON sidecars contain the locally recognized text: delete the JPEGs and sidecars together to erase a capture. No cloud sync is provided.

## Build / test from source

**Windows desktop:** Python 3.11 or newer and, when running from source, Tesseract with English traineddata installed on PATH. Windows builds bundle the OCR runtime automatically.

```powershell
cd desktop
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m claritycam
.venv\Scripts\python -m unittest discover -s tests -v
```

On Linux you can run the same native Qt source for development (`python3 -m claritycam`) with a webcam and the system Qt/OpenGL/X11 libraries; the distributable EXE is built **on Windows**, not cross-compiled. To package manually, see `.github/workflows/native-v2.yml` (Python/PyInstaller plus an offline Tesseract installation).

**Android:** Open the `android/` directory in Android Studio (JDK 17, Android SDK 35, Gradle 8.9), then build `:app:assembleDebug` and run `:app:testDebugUnitTest`. The workflow installs Gradle/SDK and uploads `android/app/build/outputs/apk/debug/app-debug.apk`. Min SDK 29 / Android 10. Testing camera, ultrawide switching, permission flows and actual FPS requires real devices. Kotlin unit tests cover plate heuristics and auto-shutter gating; desktop tests cover enhancement, OCR parsing, saved photos and the native window (headless Qt).

## Code layout

```text
android/app/src/main/java/.../   CameraX, bundled ML Kit OCR, snapshot gate,
                                  image processing, MediaStore and native Android UI
android/app/src/test/            Kotlin/JUnit scan logic tests
desktop/claritycam/              Native PySide6 UI, OpenCV camera workers,
                                  Tesseract OCR, photo processing and storage
desktop/tests/                   Python unittest suite and offscreen Qt smoke test
.github/workflows/native-v2.yml  Build and upload .apk and Windows EXE zip
```

The removed V1 browser/PWA had a black preview on some devices. V2 does not depend on browser camera permissions, service workers, HTTPS or a hosted site; on actual hardware it still needs OS camera access and a functioning sensor.

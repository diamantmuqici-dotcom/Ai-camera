# Pixel AI Camera

A browser-based computational camera with zoom, enhancement, tracking, OCR, and local gallery support.

## Features

- Camera preview using the browser camera API
- Rear/front camera switching
- Hardware zoom when exposed by the browser
- Digital zoom above the hardware limit
- `0.5x` ultrawide lens support when exposed by the browser
- Live contrast, brightness, saturation, and sharpening
- Photo and video capture
- HDR and multi-frame Super Resolution
- Long Zoom mode
- Person follow mode
- Car follow mode
- Center-weighted tap-to-focus
- License plate enhancement and OCR
- Sign reader and OCR
- Document scanner
- Local browser gallery using IndexedDB
- No uploads from the camera processing pipeline

## Run Locally

From PowerShell:

```powershell
cd "C:\Users\diama\Downloads\Better Camera More Features"
python -m http.server 8080

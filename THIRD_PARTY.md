# Third-party notices

ClarityCam V2 redistributes or uses the following components. This document is **not** a license grant for the application's own source code.

| Component | Where used | License / source |
| --- | --- | --- |
| PySide6 / Shiboken / Qt | Windows portable UI and DLLs | Distributed under the LGPL v3 option; [Qt for Python sources and licensing](https://doc.qt.io/qtforpython/licenses.html), [Qt source code](https://code.qt.io/qt/). The Windows distribution keeps Qt shared libraries as separate, replaceable files in `_internal` rather than statically linking them. LGPL v3 and GPL v3 texts are included in `licenses/`. |
| Tesseract OCR and English `eng.traineddata` | Offline Windows OCR | Apache License 2.0; [Tesseract source](https://github.com/tesseract-ocr/tesseract), [traineddata](https://github.com/tesseract-ocr/tessdata). The Windows bundle includes Tesseract's binaries, data and accompanying installation files. |
| OpenCV / opencv-python-headless | Windows camera and image processing | Apache License 2.0; [OpenCV source](https://github.com/opencv/opencv). Its Python wheel may bundle other components with separate licenses. |
| pytesseract | Windows OCR bridge | Apache License 2.0; [source](https://github.com/madmaze/pytesseract). |
| NumPy | Windows image arrays | BSD 3-Clause with other notices for included components; [source and licensing](https://github.com/numpy/numpy). |
| PyInstaller | Windows packaging bootloader | GPL v2 with bootloader exception; [source and licensing](https://github.com/pyinstaller/pyinstaller). |
| AndroidX CameraX / Activity and Material Components | Android native camera and UI | Apache License 2.0; [AndroidX](https://developer.android.com/jetpack/androidx), [Material Components Android](https://github.com/material-components/material-components-android). |
| Google ML Kit on-device text recognition | Android offline OCR | [Google ML Kit terms](https://developers.google.com/ml-kit/terms); model is bundled by the Android dependency. |

License texts shipped in `desktop/licenses/` come from the [SPDX license-list-data](https://github.com/spdx/license-list-data) project. Additional third-party notices and component versions can be found with the respective package's source distribution. No components are downloaded at app runtime.

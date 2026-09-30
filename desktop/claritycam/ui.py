"""ClarityCam V2: a native Qt desktop camera, not a browser or WebView."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import time

from PySide6.QtCore import Qt, QRectF, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImage, QKeySequence, QLinearGradient, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from .model import Settings, SettingsStore
from .ocr import Detection
from .storage import PhotoStore
from .tracker import AutoShutter
from .workers import CameraWorker, Scanner, WorkerEvents


STYLE = """
QWidget { background: #0B0F14; color: #EAF2F2; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QFrame#sidebar { background: #10161D; border-right: 1px solid #28333B; }
QFrame#inspector { background: #111920; border-left: 1px solid #273139; }
QFrame#controlDeck { background: #131B23; border-top: 1px solid #2A373F; }
QFrame#card { background: #1B252E; border: 1px solid #2B3A42; border-radius: 14px; }
QLabel#muted { color: #91A5AA; }
QLabel#eyebrow { color: #75DFD0; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#headline { color: #F4F7F5; font-size: 22px; font-weight: 800; }
QLabel#readout { color: #D5F5E8; font-family: Consolas, monospace; font-size: 17px; font-weight: 700; }
QPushButton { background: #222F38; border: 1px solid #34464E; border-radius: 10px; padding: 9px 12px; font-weight: 650; }
QPushButton:hover { background: #30434A; border-color: #69CAB7; }
QPushButton:pressed { background: #426C66; }
QPushButton:disabled { background: #192228; border-color: #26333A; color: #667982; }
QPushButton:checked { background: #20463E; border: 1px solid #77DFCA; color: #C5FFEB; }
QPushButton#shutter { background: #B8F7C8; color: #10251C; border: 0; border-radius: 16px; font-size: 15px; font-weight: 800; padding: 15px; }
QPushButton#shutter:hover { background: #D4FFE0; }
QPushButton#shutter:disabled { background: #527060; color: #253D31; }
QPushButton#nav { background: transparent; border: 0; color: #90A5A8; padding: 13px 3px; font-size: 11px; letter-spacing: 1px; }
QPushButton#nav:hover { color: #C6FBE0; background: #253D38; }
QSlider::groove:horizontal { height: 5px; background: #35464D; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #8BE0C5; border-radius: 2px; }
QSlider::handle:horizontal { background: #E8FFF2; width: 17px; margin: -6px 0; border-radius: 8px; }
QComboBox, QSpinBox { background: #202B33; border: 1px solid #3B4B52; border-radius: 8px; padding: 7px; min-height: 22px; }
QCheckBox { spacing: 10px; font-weight: 650; }
QCheckBox::indicator { width: 18px; height: 18px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 8px; background: #111920; }
QScrollBar::handle:vertical { background: #4A605F; border-radius: 4px; min-height: 36px; }
"""


def label(text: str, name: str | None = None) -> QLabel:
    result = QLabel(text)
    if name:
        result.setObjectName(name)
    if name == "muted":
        result.setWordWrap(True)
    return result


def button(text: str, callback, *, checkable: bool = False, name: str | None = None) -> QPushButton:
    result = QPushButton(text)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    result.setCheckable(checkable)
    if name:
        result.setObjectName(name)
    result.clicked.connect(callback)
    return result


class PreviewCanvas(QWidget):
    """Paints real video, guidance and OCR boxes in sensor-aligned coordinates."""

    def __init__(self, retry):
        super().__init__()
        self.setMinimumSize(440, 260)
        self.image: QImage | None = None
        self.detections: list[Detection] = []
        self.headline = "CONNECTING CAMERA"
        self.message = "Requesting a live camera feed…"
        self.zoom = 1.0
        self.flash_until = 0.0
        self.retry = button("RETRY CAMERA", retry)
        self.retry.setParent(self)
        self.retry.hide()

    def set_image(self, image: QImage) -> None:
        self.image = image
        self.retry.hide()
        self.update()

    def set_state(self, headline: str, message: str, *, retry: bool = False) -> None:
        self.headline, self.message = headline, message
        if self.image is None:
            self.retry.setVisible(retry)
        self.update()

    def clear(self) -> None:
        self.image = None
        self.detections = []
        self.retry.hide()
        self.update()

    def flash(self) -> None:
        self.flash_until = time.monotonic() + 0.16
        self.update()
        QTimer.singleShot(170, self.update)

    def resizeEvent(self, event) -> None:
        self.retry.setGeometry((self.width() - 148) // 2, self.height() // 2 + 85, 148, 40)
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#1B3035"))
        gradient.setColorAt(1, QColor("#0D141D"))
        p.fillRect(self.rect(), gradient)
        if self.image and not self.image.isNull():
            scale = max(self.width() / self.image.width(), self.height() / self.image.height())
            w, h = self.image.width() * scale, self.image.height() * scale
            x, y = (self.width() - w) / 2, (self.height() - h) / 2
            p.drawImage(QRectF(x, y, w, h), self.image)
            p.setPen(QPen(QColor(190, 239, 222, 35), 1, Qt.PenStyle.DashLine))
            p.drawLine(self.width() // 3, 0, self.width() // 3, self.height())
            p.drawLine(self.width() * 2 // 3, 0, self.width() * 2 // 3, self.height())
            p.drawLine(0, self.height() // 3, self.width(), self.height() // 3)
            p.drawLine(0, self.height() * 2 // 3, self.width(), self.height() * 2 // 3)
            for item in self.detections:
                box = QRectF(x + item.x * w, y + item.y * h, item.width * w, item.height * h)
                color = QColor("#B8F7C8") if item.kind == "PLATE" else QColor("#8AC8FF")
                p.setPen(QPen(color, 2.5))
                p.setBrush(QColor(color.red(), color.green(), color.blue(), 27))
                p.drawRoundedRect(box, 5, 5)
                title = ("PLATE CANDIDATE  " if item.kind == "PLATE" else "TEXT  ") + item.text[:28]
                p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
                font_width = p.fontMetrics().horizontalAdvance(title) + 18
                tag = QRectF(max(4, box.left()), max(4, box.top() - 27), font_width, 24)
                p.fillRect(tag, QColor("#101C1D"))
                p.drawText(tag.adjusted(9, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, title)
            p.setPen(QColor("#BEE8DA"))
            p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            p.fillRect(QRectF(16, 16, 158, 28), QColor(8, 17, 19, 190))
            p.drawText(QRectF(24, 16, 150, 28), Qt.AlignmentFlag.AlignVCenter,
                       f"LIVE  /  {self.zoom:.1f}×")
            if self.zoom > 1:
                p.fillRect(QRectF(16, self.height() - 39, 191, 25), QColor(8, 17, 19, 190))
                p.setPen(QColor("#D8E4CF"))
                p.drawText(QRectF(24, self.height() - 39, 190, 25),
                           Qt.AlignmentFlag.AlignVCenter, "ZOOM CROP  •  NO FAKE PIXELS")
        else:
            cx, cy = self.width() / 2, self.height() / 2 - 48
            p.setPen(QPen(QColor("#4D897B"), 2))
            for radius in (45, 65, 86):
                p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
            p.setPen(QColor("#C3F8DC"))
            p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            p.drawText(QRectF(30, cy + 107, self.width() - 60, 32),
                       Qt.AlignmentFlag.AlignCenter, self.headline)
            p.setPen(QColor("#A7BBC0"))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRectF(55, cy + 141, self.width() - 110, 68),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                       self.message)
        if time.monotonic() < self.flash_until:
            p.fillRect(self.rect(), QColor(235, 255, 243, 125))
        p.end()


class MainWindow(QMainWindow):
    def __init__(self, *, settings_store: SettingsStore | None = None, photo_store: PhotoStore | None = None,
                 start_camera: bool = True):
        super().__init__()
        self.setWindowTitle("ClarityCam V2  •  Native Camera Studio")
        self.setMinimumSize(970, 650)
        self.resize(1370, 820)
        self.settings_store = settings_store or SettingsStore()
        self.settings = self.settings_store.load()
        self.photos = photo_store or PhotoStore()
        self.events = WorkerEvents()
        self.events.camera_state.connect(self._on_camera_state)
        self.events.fps.connect(self._on_fps)
        self.events.scan.connect(self._on_scan)
        self.events.ocr_error.connect(self._on_ocr_error)
        self.events.saved.connect(self._on_saved)
        self.scanner = Scanner(self.events)
        self.scanner.start()
        self.writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PhotoSave")
        self.session = 0
        self.camera: CameraWorker | None = None
        self.camera_index = self.settings.primary_camera
        self.zoom = 1.0
        self._last_frame_id = 0
        self._last_frame_time = time.monotonic()
        self._saving = False
        self._last_target: Detection | None = None
        self.tracker = AutoShutter()
        self._build()
        self.setStyleSheet(STYLE)
        self._refresh_controls()
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._poll_camera)
        self.frame_timer.start(33)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_settings)
        for key, fn in (("Space", self.capture), ("Ctrl+O", self.open_library),
                        ("+", lambda: self.set_zoom(self.zoom + .25)),
                        ("-", lambda: self.set_zoom(self.zoom - .25))):
            QShortcut(QKeySequence(key), self, activated=fn)
        if start_camera:
            QTimer.singleShot(50, self._start_camera)

    def _build(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(81)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(8, 22, 8, 18)
        side.setSpacing(10)
        logo = label("C /\nV2", "headline")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color: #B8F7C8; font-size: 18px;")
        side.addWidget(logo)
        side.addSpacing(25)
        side.addWidget(button("CAM", lambda: None, name="nav"))
        side.addWidget(button("FILES", self.open_library, name="nav"))
        side.addWidget(button("HELP", self.show_help, name="nav"))
        side.addStretch()
        online = label("●\nLOCAL", "eyebrow")
        online.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side.addWidget(online)
        layout.addWidget(sidebar)

        center = QWidget()
        middle = QVBoxLayout(center)
        middle.setSpacing(0)
        middle.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        top = QHBoxLayout(header)
        top.setContentsMargins(24, 17, 24, 16)
        brand = QVBoxLayout()
        brand.setSpacing(2)
        brand.addWidget(label("CLARITYCAM  /  V2", "headline"))
        brand.addWidget(label("A sharper look at the details. Entirely on your device.", "muted"))
        top.addLayout(brand)
        top.addStretch()
        self.fps_label = label("— FPS", "readout")
        top.addWidget(self.fps_label)
        top.addSpacing(18)
        self.status_label = label("CONNECTING", "eyebrow")
        top.addWidget(self.status_label)
        middle.addWidget(header)
        self.preview = PreviewCanvas(self._start_camera)
        middle.addWidget(self.preview, 1)

        deck = QFrame(objectName="controlDeck")
        controls = QVBoxLayout(deck)
        controls.setContentsMargins(23, 15, 23, 15)
        controls.setSpacing(11)
        readout = QHBoxLayout()
        readout.addWidget(label("LIVE SCAN", "eyebrow"))
        self.target_label = label("Point at a plate or switch to text mode", "readout")
        self.target_label.setMinimumWidth(200)
        readout.addWidget(self.target_label, 1)
        self.copy_btn = button("COPY", self.copy_text)
        readout.addWidget(self.copy_btn)
        self.plate_btn = button("PLATES", lambda: self.set_mode("PLATE"), checkable=True)
        self.text_btn = button("TEXT", lambda: self.set_mode("TEXT"), checkable=True)
        readout.addWidget(self.plate_btn)
        readout.addWidget(self.text_btn)
        controls.addLayout(readout)
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(8)
        zoom_row.addWidget(label("ZOOM", "eyebrow"))
        self.zoom_buttons: dict[float, QPushButton] = {}
        for factor in (0.5, 1.0, 2.0, 4.0, 8.0):
            item = button(f"{factor:g}×", lambda checked=False, z=factor: self.set_zoom(z), checkable=True)
            item.setFixedWidth(54)
            self.zoom_buttons[factor] = item
            zoom_row.addWidget(item)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(100, 800)
        self.zoom_slider.setToolTip("Digital crop of the actual camera frames. 0.5× requires an assigned ultrawide camera.")
        self.zoom_slider.valueChanged.connect(lambda value: self.set_zoom(value / 100))
        zoom_row.addWidget(self.zoom_slider, 1)
        self.zoom_value = label("1.0×", "readout")
        zoom_row.addWidget(self.zoom_value)
        controls.addLayout(zoom_row)
        action = QHBoxLayout()
        self.auto_check = QCheckBox("AUTO SNAP  •  stable text at zoom")
        self.auto_check.toggled.connect(self._toggle_auto)
        action.addWidget(self.auto_check)
        action.addStretch()
        action.addWidget(button("RETRY", self._start_camera))
        action.addWidget(button("OPEN PHOTOS", self.open_library))
        self.shutter = button("◉  CAPTURE PHOTO", self.capture, name="shutter")
        self.shutter.setMinimumWidth(186)
        action.addWidget(self.shutter)
        controls.addLayout(action)
        middle.addWidget(deck)
        layout.addWidget(center, 1)

        inspector = QFrame(objectName="inspector")
        inspector.setFixedWidth(320)
        outer = QVBoxLayout(inspector)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        pane = QWidget()
        contents = QVBoxLayout(pane)
        contents.setContentsMargins(18, 22, 18, 22)
        contents.setSpacing(13)
        contents.addWidget(label("IMAGE LAB", "headline"))
        contents.addWidget(label("Changes tune the live image, OCR and saved JPEG. Noise reduction runs off the preview thread.", "muted"))
        presets = QHBoxLayout()
        for text, fn in (("NEUTRAL", "neutral"), ("NIGHT", "night"), ("TEXT", "text")):
            presets.addWidget(button(text, lambda checked=False, preset=fn: self._preset(preset)))
        contents.addLayout(presets)
        self.sliders: dict[str, tuple[QSlider, QLabel, float]] = {}
        for key, title, minimum, maximum, scale, sub in (
            ("gamma", "Gamma", 60, 180, 100, "Lift dark characters without changing the sensor."),
            ("contrast", "Contrast", 70, 150, 100, "Separate strokes from the background."),
            ("highlights", "Highlights", 0, 80, 100, "Compress bright midtones; clipped pixels cannot be recovered."),
            ("shadows", "Shadows", 0, 60, 100, "Reveal details in darker areas."),
            ("clarity", "Clarity", 0, 100, 100, "Modest edge sharpening, not super-resolution."),
            ("denoise", "Noise reduction", 0, 3, 1, "OCR and photos only, to protect preview FPS."),
            ("saturation", "Color", 60, 150, 100, "Color strength on preview and photos."),
        ):
            widget = QFrame(objectName="card")
            card = QVBoxLayout(widget)
            card.setContentsMargins(12, 9, 12, 9)
            title_row = QHBoxLayout()
            title_row.addWidget(label(title))
            title_row.addStretch()
            value_label = label("", "eyebrow")
            title_row.addWidget(value_label)
            card.addLayout(title_row)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(minimum, maximum)
            slider.valueChanged.connect(lambda value, k=key, s=scale: self._on_tune(k, value / s))
            card.addWidget(slider)
            desc = label(sub, "muted")
            desc.setWordWrap(True)
            card.addWidget(desc)
            self.sliders[key] = (slider, value_label, scale)
            contents.addWidget(widget)
        contents.addSpacing(10)
        contents.addWidget(label("AUTO CAPTURE", "eyebrow"))
        contents.addWidget(label("Three matching OCR results, a clear frame and zoom threshold. Same text has an 18-second cooldown.", "muted"))
        self.trigger_label = label("Trigger at 2.0×", "eyebrow")
        contents.addWidget(self.trigger_label)
        self.trigger_slider = QSlider(Qt.Orientation.Horizontal)
        self.trigger_slider.setRange(15, 40)
        self.trigger_slider.valueChanged.connect(self._on_trigger)
        contents.addWidget(self.trigger_slider)
        contents.addSpacing(10)
        contents.addWidget(label("CAMERA HARDWARE", "eyebrow"))
        contents.addWidget(label("Primary camera index", "muted"))
        self.primary_spin = QSpinBox()
        self.primary_spin.setRange(0, 9)
        self.primary_spin.setToolTip("Most built-in webcams are index 0. Select a different physical device if needed.")
        self.primary_spin.valueChanged.connect(self._change_primary)
        contents.addWidget(self.primary_spin)
        contents.addWidget(label("Ultrawide camera index (-1 = none)", "muted"))
        self.ultra_spin = QSpinBox()
        self.ultra_spin.setRange(-1, 9)
        self.ultra_spin.setToolTip("Only assign a separate, real ultrawide webcam. A software crop cannot provide 0.5×.")
        self.ultra_spin.valueChanged.connect(self._change_ultra)
        contents.addWidget(self.ultra_spin)
        info = label("0.5× switches to the ultrawide device you assign. If no physical ultrawide is present, 0.5× stays unavailable.", "muted")
        info.setWordWrap(True)
        contents.addWidget(info)
        contents.addWidget(label("Requested sensor FPS", "muted"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["30 FPS", "60 FPS"])
        self.fps_combo.currentIndexChanged.connect(self._change_fps)
        contents.addWidget(self.fps_combo)
        contents.addWidget(label("Actual input FPS appears above the preview. Webcam/driver decides the real frame rate.", "muted"))
        contents.addStretch()
        scroll.setWidget(pane)
        outer.addWidget(scroll)
        layout.addWidget(inspector)

    def _refresh_controls(self) -> None:
        self.plate_btn.setChecked(self.settings.scan_mode == "PLATE")
        self.text_btn.setChecked(self.settings.scan_mode == "TEXT")
        self.auto_check.blockSignals(True)
        self.auto_check.setChecked(self.settings.auto_snap)
        self.auto_check.blockSignals(False)
        for key, (slider, value, scale) in self.sliders.items():
            slider.blockSignals(True)
            slider.setValue(round(getattr(self.settings, key) * scale))
            slider.blockSignals(False)
            number = getattr(self.settings, key)
            value.setText(str(number) if key == "denoise" else f"{number:.2f}")
        self.trigger_slider.blockSignals(True)
        self.trigger_slider.setValue(round(self.settings.auto_zoom * 10))
        self.trigger_slider.blockSignals(False)
        self.trigger_label.setText(f"Trigger at {self.settings.auto_zoom:.1f}×")
        for spin, number in ((self.primary_spin, self.settings.primary_camera),
                             (self.ultra_spin, self.settings.ultrawide_camera)):
            spin.blockSignals(True)
            spin.setValue(number)
            spin.blockSignals(False)
        self.fps_combo.blockSignals(True)
        self.fps_combo.setCurrentIndex(1 if self.settings.target_fps == 60 else 0)
        self.fps_combo.blockSignals(False)
        self._refresh_zoom()

    def _refresh_zoom(self) -> None:
        available = (self.settings.ultrawide_camera >= 0 and
                     self.settings.ultrawide_camera != self.settings.primary_camera)
        self.zoom_buttons[0.5].setEnabled(available)
        self.zoom_buttons[0.5].setToolTip("Switch to assigned physical ultrawide" if available
                                            else "Assign a real, separate ultrawide camera in the right panel")
        for factor, item in self.zoom_buttons.items():
            item.setChecked(abs(self.zoom - factor) < 0.01)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(round(max(1.0, self.zoom) * 100))
        self.zoom_slider.blockSignals(False)
        self.zoom_value.setText(f"{self.zoom:.1f}×")
        self.preview.zoom = self.zoom
        self.preview.update()

    def _changed(self) -> None:
        if self.camera:
            self.camera.settings = self.settings
        self.save_timer.start(350)

    def _save_settings(self) -> None:
        try:
            self.settings_store.save(self.settings)
        except OSError as exc:
            self.status_label.setText(f"SETTINGS ERROR: {exc}")

    def _on_tune(self, key: str, number: float) -> None:
        number = int(number) if key == "denoise" else round(number, 2)
        self.settings = replace(self.settings, **{key: number})
        self.sliders[key][1].setText(str(number) if key == "denoise" else f"{number:.2f}")
        self._changed()

    def _preset(self, preset: str) -> None:
        values = {
            "neutral": dict(gamma=1.0, contrast=1.0, highlights=0.0, shadows=0.0,
                            clarity=0.0, denoise=0, saturation=1.0),
            "night": dict(gamma=1.32, contrast=1.15, highlights=0.25, shadows=0.3,
                          clarity=0.18, denoise=2, saturation=0.86),
            "text": dict(gamma=1.08, contrast=1.3, highlights=0.4, shadows=0.1,
                         clarity=0.5, denoise=1, saturation=0.85),
        }[preset]
        self.settings = replace(self.settings, **values)
        self._refresh_controls()
        self._changed()
        self.status_label.setText(f"{preset.upper()} PRESET")

    def _toggle_auto(self, enabled: bool) -> None:
        self.settings = replace(self.settings, auto_snap=enabled)
        self.tracker.reset()
        self._changed()

    def _on_trigger(self, value: int) -> None:
        self.settings = replace(self.settings, auto_zoom=value / 10)
        self.trigger_label.setText(f"Trigger at {self.settings.auto_zoom:.1f}×")
        self.tracker.reset()
        self._changed()

    def _change_primary(self, index: int) -> None:
        self.settings = replace(self.settings, primary_camera=index)
        self._changed()
        if self.zoom >= 1.0:
            self._start_camera()
        self._refresh_zoom()

    def _change_ultra(self, index: int) -> None:
        self.settings = replace(self.settings, ultrawide_camera=index)
        self._changed()
        if self.zoom < 1.0:
            self.set_zoom(1.0)
        self._refresh_zoom()

    def _change_fps(self, index: int) -> None:
        self.settings = replace(self.settings, target_fps=60 if index == 1 else 30)
        self._changed()
        self._start_camera()

    def set_mode(self, mode: str) -> None:
        if self.settings.scan_mode == mode:
            self._refresh_controls()
            return
        self.settings = replace(self.settings, scan_mode=mode)
        self.preview.detections = []
        self.target_label.setText("Searching for plate candidates…" if mode == "PLATE" else "Searching for text…")
        self.tracker.reset()
        self._changed()
        self._refresh_controls()

    def set_zoom(self, factor: float) -> None:
        factor = max(.5, min(8.0, factor))
        if factor < 1.0:
            if self.settings.ultrawide_camera < 0 or self.settings.ultrawide_camera == self.settings.primary_camera:
                self.status_label.setText("ASSIGN AN ULTRAWIDE CAMERA FIRST")
                return
            factor = .5  # physical 0.5× mode; no software sub-1× zoom
        switching = (factor < 1.0) != (self.zoom < 1.0)
        self.zoom = factor
        self.tracker.reset()
        self.preview.detections = []
        self._refresh_zoom()
        if switching:
            self._start_camera()
        elif self.camera:
            self.camera.zoom = self.zoom

    def _start_camera(self) -> None:
        if self.camera:
            self.camera.stop()
            # Camera reads can block briefly in a driver; never block UI indefinitely.
            self.camera.join(timeout=0.5)
        self.session += 1
        self._last_frame_id = 0
        self._last_frame_time = time.monotonic()
        self.fps_label.setText("— FPS")
        self.tracker.reset()
        self.preview.clear()
        self.preview.set_state("OPENING CAMERA", "Checking the camera device and requesting live frames…")
        self.status_label.setText("CONNECTING")
        self.camera_index = self.settings.ultrawide_camera if self.zoom < 1 else self.settings.primary_camera
        self.camera = CameraWorker(self.events, self.scanner, self.session, self.camera_index,
                                   self.settings, self.zoom)
        self.camera.start()

    def _on_camera_state(self, session: int, state: str, message: str) -> None:
        if session != self.session:
            return
        self.status_label.setText(state.upper())
        self.status_label.setToolTip(message)
        if state == "error":
            self.preview.clear()
            self.preview.set_state("CAMERA NEEDS ATTENTION", message + "  Photos and OCR need a live camera.", retry=True)
            self.fps_label.setText("NO FEED")
        elif state == "warning":
            self.preview.set_state("CAMERA WARNING", message, retry=True)
            self.target_label.setText(message[:50])
        elif state == "starting":
            self.preview.set_state("OPENING CAMERA", message)
        else:
            if message.startswith("Live "):
                self.status_label.setText(message.split(" • ")[0].upper())
            self.preview.set_state("CAMERA READY", "Waiting for the first frame…")

    def _on_fps(self, session: int, fps: float) -> None:
        if session == self.session:
            self.fps_label.setText(f"{fps:.0f} FPS")
            self.fps_label.setToolTip("Observed camera input frames per second (not OCR rate). Preview drawing is capped at 30 FPS.")

    def _poll_camera(self) -> None:
        if not self.camera:
            return
        frame = self.camera.latest_preview(self._last_frame_id)
        if frame:
            self._last_frame_id, image = frame
            self.preview.set_image(image)
            self._last_frame_time = time.monotonic()
        elif time.monotonic() - self._last_frame_time > 7 and self.preview.image is None:
            self.preview.set_state("NO LIVE FRAME YET", "Check camera permission, hardware shutter and other apps. Retry or change camera index.", retry=True)

    def _on_scan(self, session: int, detections: list[Detection], metrics: dict) -> None:
        if session != self.session:
            return
        self.preview.detections = detections
        self.preview.update()
        self._last_target = detections[0] if detections else None
        if self._last_target:
            tag = "PLATE?" if self._last_target.kind == "PLATE" else "TEXT"
            self.target_label.setText(f"{tag}  {self._last_target.text[:35]}")
            self.target_label.setToolTip(f"OCR confidence {self._last_target.confidence:.0f}% • Focus score {metrics['focus']:.0f}. Check plate characters manually.")
        else:
            hint = "Hold steady / improve lighting" if metrics["focus"] < 45 or metrics["light"] < 35 else "Looking for readable text…"
            self.target_label.setText(hint)
        if metrics["clipped"] > 20:
            self.target_label.setToolTip("Bright areas are clipping. Lower exposure on your webcam if possible.")
        if self.settings.auto_snap and self.tracker.observe(
                self._last_target, zoom=self.zoom, min_zoom=self.settings.auto_zoom,
                focus=metrics["focus"], now=time.monotonic()):
            self.capture(auto=True)

    def _on_ocr_error(self, session: int, message: str) -> None:
        if session == self.session:
            self.target_label.setText("OCR UNAVAILABLE • photos still work")
            self.target_label.setToolTip(message)
            self.preview.detections = []
            self.preview.update()

    def capture(self, checked: bool = False, *, auto: bool = False) -> None:
        if self._saving:
            return
        frame = self.camera.snapshot() if self.camera else None
        if frame is None:
            self.status_label.setText("NO FRAME TO CAPTURE")
            return
        self.preview.flash()
        self._saving = True
        self.shutter.setEnabled(False)
        self.status_label.setText("SAVING PHOTO…")
        settings, zoom, camera = self.settings, self.zoom, self.camera_index
        target = self._last_target
        future = self.writer.submit(self.photos.save, frame, settings=settings, zoom=zoom,
                                    camera=camera, reason="auto" if auto else "manual", detection=target)

        def completed(result):
            try:
                photo, error = result.result(), ""
            except Exception as exc:
                photo, error = None, str(exc)
            # Thread-safe Qt signal; the slot runs on the GUI thread.
            self.events.saved.emit(photo, error)

        future.add_done_callback(completed)

    def _on_saved(self, photo, error: str) -> None:
        self._saving = False
        self.shutter.setEnabled(True)
        if error:
            self.status_label.setText("SAVE FAILED")
            QMessageBox.warning(self, "Photo not saved", error)
        else:
            self.status_label.setText("PHOTO SAVED LOCALLY")
            self.target_label.setToolTip(f"Saved: {photo.full}")

    def copy_text(self) -> None:
        if self._last_target:
            QApplication.clipboard().setText(self._last_target.text)
            self.status_label.setText("TEXT COPIED")
        else:
            self.status_label.setText("NO TEXT TO COPY")

    def open_library(self) -> None:
        self.photos.folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.photos.folder)))

    def show_help(self) -> None:
        QMessageBox.information(self, "ClarityCam V2 • Help",
            "Everything runs locally. No uploads or account.\n\n"
            "CAMERA: Select the physical camera index in Camera Hardware. If the view is empty, check Windows Settings > Privacy & security > Camera, your webcam cover and other apps.\n\n"
            "0.5×: Assign a separate physical ultrawide camera. Digital cropping cannot make a wider field of view.\n\n"
            "AUTO SNAP: At the chosen zoom, three stable OCR readings and a reasonably focused frame trigger one photo, then a cooldown. Plate boxes are candidates, not verified registration records.\n\n"
            "PHOTOS: Pictures/ClarityCam contains a full-frame JPEG, a detail crop when zoomed, and a local JSON sidecar with OCR candidate/settings. Delete these files to erase them.\n\n"
            "FPS: The camera driver decides the actual rate. OCR runs in another worker and drops stale jobs to keep preview responsive.")

    def closeEvent(self, event) -> None:
        if self._saving:
            event.ignore()
            self.status_label.setText("WAIT FOR PHOTO TO FINISH SAVING")
            return
        self._save_settings()
        if self.camera:
            self.camera.stop()
            self.camera.join(timeout=1)
        self.scanner.stop()
        self.writer.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)

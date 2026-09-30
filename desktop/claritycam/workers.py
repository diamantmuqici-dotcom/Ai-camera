"""Native camera and OCR workers. Preview never waits on OCR or JPEG encoding."""
from __future__ import annotations

from collections import deque
import os
from queue import Empty, Full, Queue
import threading
import time

import cv2
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from .engine import preview_image, quality_metrics, zoom_frame
from .model import Settings
from .ocr import OcrUnavailable, recognize


class WorkerEvents(QObject):
    camera_state = Signal(int, str, str)  # session, state, message
    fps = Signal(int, float)
    scan = Signal(int, object, object)  # session, detections, metrics
    ocr_error = Signal(int, str)
    saved = Signal(object, str)


class Scanner(threading.Thread):
    """A single OCR worker; stale jobs are replaced instead of queued indefinitely."""

    def __init__(self, events: WorkerEvents):
        super().__init__(name="OCR", daemon=True)
        self.events = events
        self.jobs: Queue = Queue(maxsize=1)
        self.stopping = threading.Event()
        self._last_error = ""

    def submit(self, session: int, frame, zoom: float, settings: Settings) -> None:
        if self.stopping.is_set():
            return
        job = (session, frame, zoom, settings)
        try:
            self.jobs.put_nowait(job)
        except Full:
            try:
                self.jobs.get_nowait()
            except Empty:
                pass
            try:
                self.jobs.put_nowait(job)
            except Full:
                pass

    def run(self) -> None:
        while not self.stopping.is_set():
            try:
                session, frame, zoom, settings = self.jobs.get(timeout=0.3)
            except Empty:
                continue
            try:
                cropped = zoom_frame(frame, zoom)
                metrics = quality_metrics(cropped)
                detections = recognize(cropped, settings, settings.scan_mode)
                self._last_error = ""
                self.events.scan.emit(session, detections, metrics)
            except (OcrUnavailable, Exception) as exc:
                # A failed OCR subsystem must never kill camera preview.
                message = str(exc)
                if message != self._last_error:
                    self.events.ocr_error.emit(session, message)
                    self._last_error = message

    def stop(self) -> None:
        self.stopping.set()


class CameraWorker(threading.Thread):
    def __init__(self, events: WorkerEvents, scanner: Scanner, session: int, index: int,
                 settings: Settings, zoom: float):
        super().__init__(name=f"Camera-{index}", daemon=True)
        self.events = events
        self.scanner = scanner
        self.session = session
        self.index = index
        self.settings = settings
        self.zoom = zoom
        self.stopping = threading.Event()
        self._lock = threading.Lock()
        self._raw = None
        self._preview: tuple[int, QImage] | None = None
        self._frame_id = 0

    def snapshot(self):
        with self._lock:
            return self._raw.copy() if self._raw is not None else None

    def latest_preview(self, last_id: int) -> tuple[int, QImage] | None:
        with self._lock:
            if self._preview is None or self._preview[0] == last_id:
                return None
            return self._preview

    def stop(self) -> None:
        self.stopping.set()

    def run(self) -> None:
        cap = None
        try:
            self.events.camera_state.emit(self.session, "starting", f"Opening camera {self.index}…")
            backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
            cap = cv2.VideoCapture(self.index, backend)
            if not cap.isOpened() and os.name == "nt":
                cap.release()
                cap = cv2.VideoCapture(self.index, cv2.CAP_MSMF)
            if not cap.isOpened():
                raise RuntimeError(f"Camera {self.index} could not be opened. Check its index, Windows camera privacy settings, or another app using it.")
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # MJPEG often unlocks the webcam's full frame rate; drivers may ignore it.
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            # 60 FPS is usually a lower-resolution webcam mode. OCR still uses the
            # original delivered pixels; never label a resize as extra detail.
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280 if self.settings.target_fps == 60 else 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720 if self.settings.target_fps == 60 else 1080)
            cap.set(cv2.CAP_PROP_FPS, self.settings.target_fps)
            self.events.camera_state.emit(self.session, "ready", "Camera opened • waiting for frames")
            times: deque[float] = deque(maxlen=120)
            last_fps = last_preview = last_scan = 0.0
            failures = dark_frames = 0
            warned_dark = False
            announced_size = False
            while not self.stopping.is_set():
                ok, frame = cap.read()
                if not ok or frame is None or frame.size == 0:
                    failures += 1
                    if failures >= 15:
                        raise RuntimeError("Camera stopped delivering frames. Try Retry or choose a different camera.")
                    time.sleep(0.03)
                    continue
                failures = 0
                if not announced_size:
                    height, width = frame.shape[:2]
                    self.events.camera_state.emit(self.session, "ready", f"Live {width}×{height} • local OCR")
                    announced_size = True
                now = time.monotonic()
                times.append(now)
                with self._lock:
                    self._raw = frame
                if now - last_fps >= 1.0:
                    while times and times[0] < now - 1.0:
                        times.popleft()
                    self.events.fps.emit(self.session, float(len(times)))
                    last_fps = now
                    sample = frame[::32, ::32]
                    dark_frames = dark_frames + 1 if sample.mean() < 2 and sample.std() < 2 else 0
                    if dark_frames >= 3 and not warned_dark:
                        self.events.camera_state.emit(self.session, "warning", "Camera frames are almost black. Check lens cover, privacy switch and lighting.")
                        warned_dark = True
                    if warned_dark and dark_frames == 0:
                        self.events.camera_state.emit(self.session, "ready", "Live camera • scanning on this device")
                        warned_dark = False
                if now - last_scan >= 0.55:
                    self.scanner.submit(self.session, frame, self.zoom, self.settings)
                    last_scan = now
                if now - last_preview >= 1.0 / 30.0:
                    try:
                        shown = preview_image(frame, self.zoom, self.settings)
                        rgb = cv2.cvtColor(shown, cv2.COLOR_BGR2RGB)
                        height, width = rgb.shape[:2]
                        qimage = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
                        with self._lock:
                            self._frame_id += 1
                            self._preview = (self._frame_id, qimage)
                    except (cv2.error, ValueError) as exc:
                        self.events.camera_state.emit(self.session, "warning", f"Preview processing error: {exc}")
                    last_preview = now
        except Exception as exc:
            if not self.stopping.is_set():
                self.events.camera_state.emit(self.session, "error", str(exc))
        finally:
            if cap is not None:
                cap.release()
            with self._lock:
                self._raw = None

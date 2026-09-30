"""Private, local JPEG capture; keep the full sensor frame and optional zoomed detail."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import uuid

import cv2
import numpy as np

from .engine import enhance, zoom_frame
from .model import Settings
from .ocr import Detection


@dataclass(frozen=True)
class SavedPhoto:
    full: Path
    detail: Path | None
    metadata: Path


class PhotoStore:
    def __init__(self, folder: Path | None = None):
        self.folder = folder or (Path.home() / "Pictures" / "ClarityCam")

    @staticmethod
    def _write_jpeg(path: Path, image: np.ndarray) -> None:
        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 94])
        if not ok:
            raise OSError("Could not encode photograph")
        temp = path.with_suffix(".tmp")
        temp.write_bytes(encoded.tobytes())
        temp.replace(path)

    def save(self, frame: np.ndarray, *, settings: Settings, zoom: float, camera: int,
             reason: str, detection: Detection | None = None) -> SavedPhoto:
        if frame is None or frame.size == 0:
            raise ValueError("No camera frame to save")
        self.folder.mkdir(parents=True, exist_ok=True)
        stem = datetime.now().strftime("CLARITY_%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:4]
        full = self.folder / f"{stem}.jpg"
        detail = self.folder / f"{stem}_detail.jpg" if zoom > 1.05 else None
        metadata = self.folder / f"{stem}.json"
        created: list[Path] = []
        try:
            # Keep the original field of view. Digital zoom is a separate sensor crop,
            # not an invented high-resolution optical capture.
            self._write_jpeg(full, enhance(frame, settings, purpose="photo"))
            created.append(full)
            if detail:
                self._write_jpeg(detail, enhance(zoom_frame(frame, zoom), settings, purpose="photo"))
                created.append(detail)
            info = {
                "captured_at": datetime.now().astimezone().isoformat(),
                "reason": reason, "camera_index": camera,
                "zoom": zoom, "detail_is_digital_crop": bool(detail),
                "sensor_width": int(frame.shape[1]), "sensor_height": int(frame.shape[0]),
                "candidate_text": detection.text if detection else None,
                "candidate_confidence": round(detection.confidence, 1) if detection else None,
                "settings": asdict(settings),
            }
            temp = metadata.with_suffix(".tmp")
            temp.write_text(json.dumps(info, indent=2), encoding="utf-8")
            temp.replace(metadata)
            created.append(metadata)
            return SavedPhoto(full, detail, metadata)
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            metadata.with_suffix(".tmp").unlink(missing_ok=True)
            full.with_suffix(".tmp").unlink(missing_ok=True)
            if detail:
                detail.with_suffix(".tmp").unlink(missing_ok=True)
            raise

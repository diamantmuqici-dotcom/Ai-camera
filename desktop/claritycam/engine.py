"""Bounded, honest image processing. No interpolation is presented as optical detail."""
from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np

from .model import Settings


def crop_rect(width: int, height: int, zoom: float) -> tuple[int, int, int, int]:
    """Return a centered sensor crop. Sub-1x is only provided by another physical lens."""
    if width <= 0 or height <= 0 or zoom <= 0:
        raise ValueError("Invalid frame dimensions or zoom")
    scale = max(1.0, zoom)
    w = max(1, round(width / scale))
    h = max(1, round(height / scale))
    return ((width - w) // 2, (height - h) // 2, w, h)


def zoom_frame(frame: np.ndarray, zoom: float) -> np.ndarray:
    height, width = frame.shape[:2]
    x, y, w, h = crop_rect(width, height, zoom)
    return frame[y:y + h, x:x + w]


@lru_cache(maxsize=32)
def _luma_lut(gamma: float, contrast: float, highlights: float, shadows: float) -> np.ndarray:
    x = np.arange(256, dtype=np.float32) / 255.0
    value = np.power(x, 1.0 / gamma)
    value += shadows * (1.0 - value) ** 2 * 0.26
    # Compress bright midtones without pretending to recover clipped sensor data.
    value -= highlights * np.maximum(0.0, value - 0.55) * (1.0 - value)
    value = (value - 0.5) * contrast + 0.5
    return np.clip(value * 255.0, 0, 255).astype(np.uint8)


@lru_cache(maxsize=16)
def _chroma_lut(saturation: float) -> np.ndarray:
    x = np.arange(256, dtype=np.float32)
    return np.clip(128.0 + (x - 128.0) * saturation, 0, 255).astype(np.uint8)


def enhance(frame: np.ndarray, settings: Settings, *, purpose: str = "preview") -> np.ndarray:
    """Tune the actual pixels sent to OCR / JPEG; preview skips expensive denoising.

    'preview' is deliberately cheap; 'scan' and 'photo' run on background workers.
    """
    if purpose not in ("preview", "scan", "photo"):
        raise ValueError("Invalid enhancement purpose")
    ycc = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    ycc[:, :, 0] = cv2.LUT(
        ycc[:, :, 0],
        _luma_lut(settings.gamma, settings.contrast, settings.highlights, settings.shadows),
    )
    if settings.saturation != 1.0:
        lut = _chroma_lut(settings.saturation)
        ycc[:, :, 1] = cv2.LUT(ycc[:, :, 1], lut)
        ycc[:, :, 2] = cv2.LUT(ycc[:, :, 2], lut)
    image = cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)
    if purpose != "preview" and settings.denoise:
        strength = 12 + settings.denoise * 12
        image = cv2.bilateralFilter(image, 5, strength, 5)
    if settings.clarity:
        # A modest unsharp mask improves readable edges, but cannot add missing pixels.
        blur = cv2.GaussianBlur(image, (0, 0), 1.0)
        image = cv2.addWeighted(image, 1.0 + settings.clarity * 0.6, blur,
                                -settings.clarity * 0.6, 0)
    return image


def preview_image(frame: np.ndarray, zoom: float, settings: Settings, max_width: int = 1100) -> np.ndarray:
    cropped = zoom_frame(frame, zoom)
    if cropped.shape[1] > max_width:
        scale = max_width / cropped.shape[1]
        cropped = cv2.resize(cropped, (max_width, max(1, round(cropped.shape[0] * scale))),
                             interpolation=cv2.INTER_AREA)
    return enhance(cropped, settings)


def quality_metrics(frame: np.ndarray) -> dict[str, float]:
    """Focus/lighting indicators, not a claim of optical sharpness or OCR confidence."""
    gray = cv2.cvtColor(frame[::3, ::3], cv2.COLOR_BGR2GRAY)
    return {
        "focus": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
        "light": float(gray.mean()),
        "clipped": float(np.mean(gray >= 250) * 100.0),
    }

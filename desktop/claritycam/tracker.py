"""Temporal agreement and shutter gating. One OCR result is not enough to save a photo."""
from __future__ import annotations

from .ocr import Detection, plate_key


class AutoShutter:
    def __init__(self, *, required_hits: int = 3, cooldown_seconds: float = 18.0):
        self.required_hits = required_hits
        self.cooldown_seconds = cooldown_seconds
        self.reset()
        self._last_saved: dict[str, float] = {}
        self._last_any = float("-inf")

    def reset(self) -> None:
        self._key = ""
        self._box: Detection | None = None
        self._hits = 0
        self._last_seen = float("-inf")

    @staticmethod
    def _overlaps(a: Detection, b: Detection) -> bool:
        left, top = max(a.x, b.x), max(a.y, b.y)
        right = min(a.x + a.width, b.x + b.width)
        bottom = min(a.y + a.height, b.y + b.height)
        intersection = max(0.0, right - left) * max(0.0, bottom - top)
        union = a.width * a.height + b.width * b.height - intersection
        return union > 0 and intersection / union >= 0.3

    def observe(self, target: Detection | None, *, zoom: float, min_zoom: float,
                focus: float, now: float) -> bool:
        if target is None or zoom < min_zoom or focus < 45:
            self.reset()
            return False
        key = plate_key(target.text)
        if not key:
            self.reset()
            return False
        if key == self._key and self._box and self._overlaps(self._box, target) and now - self._last_seen <= 2.5:
            self._hits += 1
        else:
            self._hits = 1
        self._key, self._box, self._last_seen = key, target, now
        if self._hits < self.required_hits:
            return False
        if now - self._last_any < 5.0 or now - self._last_saved.get(key, float("-inf")) < self.cooldown_seconds:
            return False
        self._hits = 0
        self._last_any = now
        self._last_saved[key] = now
        # Keep the cooldown map small even after a long session in traffic.
        if len(self._last_saved) > 128:
            self._last_saved = {k: t for k, t in self._last_saved.items() if now - t < self.cooldown_seconds}
        return True

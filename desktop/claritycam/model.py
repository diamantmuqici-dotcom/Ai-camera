"""Settings and small value objects shared by the native Windows UI and workers."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    # Tonal controls affect the preview, OCR input and saved photographs.
    gamma: float = 1.0
    contrast: float = 1.08
    highlights: float = 0.25
    shadows: float = 0.12
    saturation: float = 1.0
    clarity: float = 0.25
    denoise: int = 0  # applied to scans and saved photographs, not every preview frame
    target_fps: int = 30  # a request to the driver, not a guaranteed frame rate
    primary_camera: int = 0
    ultrawide_camera: int = -1  # explicitly assigned physical camera, never a fake crop
    scan_mode: str = "PLATE"
    auto_snap: bool = True
    auto_zoom: float = 2.0

    @classmethod
    def from_dict(cls, values: dict) -> Settings:
        defaults = cls()
        allowed = {field.name for field in fields(cls)}
        values = {key: value for key, value in values.items() if key in allowed}
        try:
            result = cls(**values)
            # A damaged or hand-edited settings file must not break camera startup.
            return cls(
                gamma=_clamp(result.gamma, 0.6, 1.8),
                contrast=_clamp(result.contrast, 0.7, 1.5),
                highlights=_clamp(result.highlights, 0, 0.8),
                shadows=_clamp(result.shadows, 0, 0.6),
                saturation=_clamp(result.saturation, 0.6, 1.5),
                clarity=_clamp(result.clarity, 0, 1.0),
                denoise=max(0, min(3, int(result.denoise))),
                target_fps=result.target_fps if result.target_fps in (30, 60) else 30,
                primary_camera=max(0, min(9, int(result.primary_camera))),
                ultrawide_camera=max(-1, min(9, int(result.ultrawide_camera))),
                scan_mode=result.scan_mode if result.scan_mode in ("PLATE", "TEXT") else "PLATE",
                auto_snap=result.auto_snap if isinstance(result.auto_snap, bool) else True,
                auto_zoom=_clamp(result.auto_zoom, 1.5, 4.0),
            )
        except (TypeError, ValueError):
            return defaults


def _clamp(value: float, low: float, high: float) -> float:
    value = float(value)
    # NaN must not pass through clamping to a LUT or widget.
    if value != value:
        raise ValueError("NaN setting")
    return max(low, min(high, value))


class SettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or (Path.home() / "AppData" / "Roaming" / "ClarityCam" / "settings.json")

    def load(self) -> Settings:
        try:
            return Settings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        temp.replace(self.path)

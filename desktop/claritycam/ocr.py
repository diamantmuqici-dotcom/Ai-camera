"""Offline Tesseract OCR and *candidate* plate highlighting, never identity lookup."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import sys
import unicodedata

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from .engine import enhance
from .model import Settings


class OcrUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Detection:
    text: str
    x: float  # normalized coordinates in the zoomed, displayed image
    y: float
    width: float
    height: float
    confidence: float
    kind: str


def plate_key(text: str) -> str:
    # Do not substitute ambiguous O/0 or I/1: an incorrect 'correction' is worse.
    return re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFKC", text).upper())


def looks_like_plate(text: str, aspect: float = 3.0) -> bool:
    key = plate_key(text)
    return (5 <= len(key) <= 10 and 1.5 <= aspect <= 12.0
            and sum(c.isalpha() for c in key) >= 1
            and sum(c.isdigit() for c in key) >= 2
            and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for c in key))


def parse_tesseract(data: dict, width: int, height: int, mode: str) -> list[Detection]:
    """Group OCR words into lines; keep only sufficiently legible candidate regions."""
    groups: dict[tuple, list[tuple]] = {}
    for i, raw in enumerate(data.get("text", [])):
        word = str(raw).strip()
        try:
            conf = float(data["conf"][i])
            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if not word or conf < 25 or w < 2 or h < 3:
            continue
        key = tuple(data.get(part, [0] * len(data["text"]))[i]
                    for part in ("page_num", "block_num", "par_num", "line_num"))
        groups.setdefault(key, []).append((x, y, w, h, word, conf))
    found: list[Detection] = []
    for words in groups.values():
        words.sort(key=lambda item: item[0])
        text = " ".join(word[4] for word in words)
        x = min(word[0] for word in words)
        y = min(word[1] for word in words)
        right = max(word[0] + word[2] for word in words)
        bottom = max(word[1] + word[3] for word in words)
        confidence = sum(word[5] for word in words) / len(words)
        if confidence < 38 or len(text.strip()) < 2:
            continue
        kind = "PLATE" if looks_like_plate(text, (right - x) / max(1, bottom - y)) else "TEXT"
        if mode == "PLATE" and kind != "PLATE":
            continue
        found.append(Detection(
            text=text, x=max(0.0, x / width), y=max(0.0, y / height),
            width=min(1.0 - max(0.0, x / width), (right - x) / width),
            height=min(1.0 - max(0.0, y / height), (bottom - y) / height),
            confidence=confidence, kind=kind,
        ))
    return sorted(found, key=lambda item: (-item.confidence, item.y))[:10]


def setup_tesseract() -> None:
    """Prefer the locally packaged OCR binary/data; never download a language pack."""
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "tesseract"
    binary = bundle / "tesseract.exe"
    if binary.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(binary)
        os.environ["TESSDATA_PREFIX"] = str(bundle / "tessdata")
    else:
        binary_on_path = shutil.which("tesseract")
        if not binary_on_path:
            raise OcrUnavailable("OCR engine not installed. Photos still work; install Tesseract or use the packaged Windows build.")
        pytesseract.pytesseract.tesseract_cmd = binary_on_path


def recognize(frame: np.ndarray, settings: Settings, mode: str) -> list[Detection]:
    """Run only on the scanner worker (never on the preview/UI thread)."""
    setup_tesseract()
    image = enhance(frame, settings, purpose="scan")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Local contrast for characters in shadows or backlit plates.
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    height, width = gray.shape
    if width > 1600:
        scale = 1600 / width
        gray = cv2.resize(gray, (1600, max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
    elif width < 800:
        scale = min(2.0, 800 / max(1, width))
        gray = cv2.resize(gray, (max(1, round(width * scale)), max(1, round(height * scale))),
                          interpolation=cv2.INTER_CUBIC)
    try:
        data = pytesseract.image_to_data(gray, lang="eng", config="--psm 11", output_type=Output.DICT,
                                         timeout=8)
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError) as exc:
        raise OcrUnavailable(str(exc)) from exc
    except RuntimeError as exc:
        # OCR timing out must not stall or take down the camera.
        raise OcrUnavailable(f"OCR timed out: {exc}") from exc
    return parse_tesseract(data, gray.shape[1], gray.shape[0], mode)

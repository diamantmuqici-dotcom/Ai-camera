"""Run with `python -m claritycam` or the packaged ClarityCam.exe."""
import os
from pathlib import Path
import sys
import traceback

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from .ui import MainWindow


def icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#17292B"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(3, 3, 122, 122), 25, 25)
    painter.setBrush(QColor("#B8F7C8"))
    painter.drawEllipse(QRectF(25, 25, 78, 78))
    painter.setBrush(QColor("#17292B"))
    painter.drawEllipse(QRectF(41, 41, 46, 46))
    painter.setPen(QColor("#B8F7C8"))
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    painter.drawText(QRectF(70, 80, 38, 28), Qt.AlignmentFlag.AlignCenter, "V2")
    painter.end()
    return QIcon(pixmap)


def main() -> int:
    smoke = "--smoke-test" in sys.argv
    if smoke:
        sys.argv.remove("--smoke-test")
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("ClarityCam")
        app.setOrganizationName("ClarityCam")
        app.setStyle("Fusion")
        app.setWindowIcon(icon())
        window = MainWindow(start_camera=not smoke)
        window.show()
        if smoke:
            # CI starts the actual packaged EXE offscreen, verifies the UI paints and
            # proves the OCR binary + model really live inside the portable bundle.
            app.processEvents()
            if window.grab().isNull():
                raise RuntimeError("Native UI did not render")
            if getattr(sys, "frozen", False):
                root = Path(sys._MEIPASS) / "tesseract"
                if not (root / "tesseract.exe").is_file() or not (root / "tessdata" / "eng.traineddata").is_file():
                    raise RuntimeError("Offline OCR runtime is missing from the EXE bundle")
            from .ocr import setup_tesseract
            import pytesseract
            setup_tesseract()
            pytesseract.get_tesseract_version()
            window.close()
            return 0
        return app.exec()
    except Exception:
        if smoke:
            Path(os.environ.get("CLARITY_SMOKE_LOG", "clarity-smoke.log")).write_text(
                traceback.format_exc(), encoding="utf-8")
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())

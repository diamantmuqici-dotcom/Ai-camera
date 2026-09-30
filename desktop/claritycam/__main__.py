"""Run with `python -m claritycam` or the packaged ClarityCam.exe."""
import sys

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
    app = QApplication(sys.argv)
    app.setApplicationName("ClarityCam")
    app.setOrganizationName("ClarityCam")
    app.setStyle("Fusion")
    app.setWindowIcon(icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

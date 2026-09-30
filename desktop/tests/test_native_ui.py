"""Smoke-test the actual Qt window without webcam or display server."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from claritycam.model import SettingsStore
from claritycam.storage import PhotoStore
from claritycam.ui import MainWindow


class NativeWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_starts_without_a_camera_and_does_not_show_black_empty_screen(self):
        with TemporaryDirectory() as temp:
            window = MainWindow(settings_store=SettingsStore(Path(temp) / "config.json"),
                                photo_store=PhotoStore(Path(temp) / "photos"), start_camera=False)
            try:
                window.show()
                self.app.processEvents()
                self.assertFalse(window.zoom_buttons[.5].isEnabled())
                self.assertEqual(window.preview.headline, "CONNECTING CAMERA")
                window._on_camera_state(window.session, "error", "Camera permission denied")
                self.assertTrue(window.preview.retry.isVisible())
                self.assertIn("CAMERA NEEDS ATTENTION", window.preview.headline)
                window.set_mode("TEXT")
                self.assertEqual(window.settings.scan_mode, "TEXT")
                window._preset("night")
                self.assertGreater(window.settings.gamma, 1)
                window._change_ultra(2)
                self.assertTrue(window.zoom_buttons[.5].isEnabled())
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()

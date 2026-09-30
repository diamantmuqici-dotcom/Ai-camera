import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import cv2
import numpy as np

from claritycam.engine import crop_rect, enhance, preview_image, quality_metrics, zoom_frame
from claritycam.model import Settings, SettingsStore
from claritycam.ocr import Detection, looks_like_plate, parse_tesseract, plate_key
from claritycam.storage import PhotoStore
from claritycam.tracker import AutoShutter


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.image = np.full((400, 800, 3), 65, np.uint8)
        cv2.putText(self.image, "RKS 1234", (90, 230), cv2.FONT_HERSHEY_SIMPLEX, 2.5,
                    (220, 220, 220), 7, cv2.LINE_AA)

    def test_crop_is_centered_and_does_not_fabricate_sub_one_zoom(self):
        self.assertEqual(crop_rect(800, 400, 2), (200, 100, 400, 200))
        self.assertEqual(crop_rect(800, 400, .5), (0, 0, 800, 400))
        self.assertEqual(zoom_frame(self.image, 4).shape, (100, 200, 3))
        with self.assertRaises(ValueError):
            crop_rect(0, 400, 2)

    def test_gamma_changes_saved_pixels_as_well_as_preview(self):
        original = enhance(self.image, Settings(), purpose="photo")
        brighter = enhance(self.image, Settings(gamma=1.5), purpose="photo")
        self.assertGreater(int(brighter[0, 0, 0]), int(original[0, 0, 0]))
        preview = preview_image(self.image, 2, Settings(gamma=1.5), max_width=500)
        self.assertEqual(preview.shape[:2], (200, 400))
        self.assertTrue(np.isfinite(quality_metrics(self.image)["focus"]))
        self.assertGreater(quality_metrics(self.image)["focus"],
                           quality_metrics(cv2.GaussianBlur(self.image, (31, 31), 4))["focus"])

    def test_settings_corruption_and_clamping(self):
        with TemporaryDirectory() as tmp:
            store = SettingsStore(Path(tmp) / "config.json")
            store.save(Settings(gamma=1.33))
            self.assertAlmostEqual(store.load().gamma, 1.33)
            store.path.write_text('{"gamma": 99, "scan_mode": "oops", "extra": 7}')
            self.assertEqual(store.load().gamma, 1.8)
            self.assertEqual(store.load().scan_mode, "PLATE")
            store.path.write_text("garbled")
            self.assertEqual(store.load(), Settings())

    def test_capture_stores_both_full_frame_and_honest_crop(self):
        with TemporaryDirectory() as tmp:
            saved = PhotoStore(Path(tmp)).save(self.image, settings=Settings(gamma=1.45),
                                                zoom=2, camera=1, reason="auto")
            self.assertTrue(saved.full.exists())
            self.assertTrue(saved.detail.exists())
            self.assertEqual(cv2.imread(str(saved.full)).shape[:2], (400, 800))
            self.assertEqual(cv2.imread(str(saved.detail)).shape[:2], (200, 400))
            metadata = json.loads(saved.metadata.read_text())
            self.assertEqual(metadata["reason"], "auto")
            self.assertTrue(metadata["detail_is_digital_crop"])
            self.assertEqual(metadata["settings"]["gamma"], 1.45)


class ScanTests(unittest.TestCase):
    def test_plate_heuristic_does_not_invent_or_correct_characters(self):
        self.assertTrue(looks_like_plate("RKS 1234"))
        self.assertTrue(looks_like_plate("AB-123-CD"))
        self.assertFalse(looks_like_plate("WELCOME"))
        self.assertFalse(looks_like_plate("123456"))
        self.assertFalse(looks_like_plate("A1"))
        self.assertFalse(looks_like_plate("AB@123"))
        self.assertEqual(plate_key("ab-o012"), "ABO012")

    def test_tesseract_word_groups_give_bounding_boxes(self):
        data = {
            "text": ["RKS", "1234", "WELCOME"], "conf": [87, 89, 91],
            "left": [10, 105, 10], "top": [20, 20, 120],
            "width": [85, 110, 160], "height": [32, 32, 31],
            "page_num": [1, 1, 1], "block_num": [1, 1, 2],
            "par_num": [1, 1, 1], "line_num": [1, 1, 1],
        }
        plates = parse_tesseract(data, 400, 200, "PLATE")
        self.assertEqual(len(plates), 1)
        self.assertEqual(plates[0].text, "RKS 1234")
        self.assertAlmostEqual(plates[0].x, .025)
        self.assertEqual(len(parse_tesseract(data, 400, 200, "TEXT")), 2)

    def test_temporal_agreement_focus_zoom_and_cooldown(self):
        snap = AutoShutter()
        good = Detection("RKS 1234", .2, .4, .4, .15, 90, "PLATE")
        other = Detection("AB 5678", .2, .4, .4, .15, 88, "PLATE")
        self.assertFalse(snap.observe(good, zoom=1, min_zoom=2, focus=200, now=0))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=30, now=.5))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=1))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=2))
        self.assertTrue(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=3))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=4))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=5))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=6))
        self.assertFalse(snap.observe(other, zoom=2, min_zoom=2, focus=200, now=7))
        self.assertFalse(snap.observe(other, zoom=2, min_zoom=2, focus=200, now=8))
        self.assertTrue(snap.observe(other, zoom=2, min_zoom=2, focus=200, now=9))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=19))
        self.assertFalse(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=20))
        self.assertTrue(snap.observe(good, zoom=2, min_zoom=2, focus=200, now=21))


if __name__ == "__main__":
    unittest.main()

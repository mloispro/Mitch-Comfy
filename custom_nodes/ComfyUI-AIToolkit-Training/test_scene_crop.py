from __future__ import annotations

import unittest

from scene_crop import face_aware_scene_crop


class SceneCropTests(unittest.TestCase):
    def test_waist_up_promotes_small_layout_subject(self):
        crop = face_aware_scene_crop(
            896,
            1344,
            (250, 540, 360, 650),
            "Waist-up",
            896,
            1344,
        )
        self.assertLessEqual(abs(crop.width * 3 - crop.height * 2), 2)
        self.assertLess(crop.height, 1344)
        self.assertGreaterEqual(crop.top, 0)
        self.assertLessEqual(crop.bottom, 1344)
        self.assertGreaterEqual((595 - crop.top) / crop.height, 0.25)
        self.assertLessEqual((595 - crop.top) / crop.height, 0.35)

    def test_head_and_shoulders_is_tighter_than_waist_up(self):
        face = (250, 540, 360, 650)
        head = face_aware_scene_crop(896, 1344, face, "Head and shoulders", 896, 1344)
        waist = face_aware_scene_crop(896, 1344, face, "Waist-up", 896, 1344)
        self.assertLess(head.height, waist.height)

    def test_full_body_preserves_complete_layout(self):
        crop = face_aware_scene_crop(
            896, 1344, (250, 200, 340, 300), "Full body", 896, 1344
        )
        self.assertEqual((crop.left, crop.top, crop.right, crop.bottom), (0, 0, 896, 1344))

    def test_already_close_waist_up_subject_is_not_overcropped(self):
        crop = face_aware_scene_crop(
            896, 1344, (250, 300, 450, 500), "Waist-up", 896, 1344
        )
        self.assertEqual((crop.left, crop.top, crop.right, crop.bottom), (0, 0, 896, 1344))

    def test_edge_face_stays_inside_source(self):
        crop = face_aware_scene_crop(
            896, 1344, (5, 400, 100, 500), "Waist-up", 896, 1344
        )
        self.assertEqual(crop.left, 0)
        self.assertLessEqual(crop.right, 896)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

import cv2
import numpy as np

from head_integrity import build_head_protection_mask, measure_head_integrity


class HeadIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.shape = (600, 400)
        self.face = (150, 170, 250, 310)

    def _complete_person(self):
        mask = np.zeros(self.shape, dtype=np.uint8)
        cv2.ellipse(mask, (200, 190), (75, 105), 0, 0, 360, 1, -1)
        cv2.rectangle(mask, (105, 270), (295, 599), 1, -1)
        return mask

    def test_protection_mask_extends_above_and_behind_face(self):
        mask, report = build_head_protection_mask(self.shape, self.face)
        left, top, right, bottom = report["bbox"]
        self.assertLess(left, self.face[0])
        self.assertLess(top, self.face[1])
        self.assertGreater(right, self.face[2])
        self.assertGreater(bottom, self.face[3])
        self.assertEqual(mask.shape, self.shape)
        self.assertGreater(mask.sum(), 0)

    def test_complete_head_passes(self):
        report = measure_head_integrity(self._complete_person(), self.face)
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.failures, [])

    def test_missing_crown_is_rejected(self):
        mask = self._complete_person()
        mask[:150, :] = 0
        report = measure_head_integrity(mask, self.face)
        self.assertEqual(report.status, "rejected")
        self.assertIn("insufficient_crown_clearance", report.failures)

    def test_profile_direction_is_recorded_for_diagnostics(self):
        mask = self._complete_person()
        mask[:, :148] = 0
        looking_right = np.array(
            [[175, 220], [225, 220], [215, 245], [185, 275], [225, 275]],
            dtype=np.float32,
        )
        report = measure_head_integrity(mask, self.face, looking_right)
        self.assertEqual(report.back_side, "left")
        self.assertLess(report.back_clearance_ratio, 0.16)

    def test_missing_head_quadrant_is_rejected_by_core_coverage(self):
        mask = self._complete_person()
        mask[105:260, 105:225] = 0
        report = measure_head_integrity(mask, self.face)
        self.assertEqual(report.status, "rejected")
        self.assertIn("incomplete_head_core", report.failures)


if __name__ == "__main__":
    unittest.main()

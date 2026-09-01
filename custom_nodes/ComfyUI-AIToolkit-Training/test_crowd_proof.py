from __future__ import annotations

import unittest

import numpy as np

from crowd_geometry import (
    MASK_INTERNAL_FACE,
    build_internal_face_mask,
    face_geometry_metrics,
)


class CrowdProofTests(unittest.TestCase):
    def test_rejects_oversized_shifted_face(self):
        report = face_geometry_metrics(
            (431.3, 518.9, 487.7, 597.5),
            (415.6, 494.5, 490.9, 595.6),
        )
        self.assertEqual(report["status"], "rejected")
        self.assertGreater(report["face_height_ratio"], 1.28)
        self.assertIn(
            "face_height_changed_relative_to_plate", report["failures"]
        )
        self.assertIn(
            "face_width_changed_relative_to_plate", report["failures"]
        )

    def test_accepts_face_geometry_within_twelve_percent(self):
        report = face_geometry_metrics(
            (100.0, 200.0, 160.0, 290.0),
            (102.0, 202.0, 162.0, 292.0),
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["failures"], [])

    def test_internal_face_mask_does_not_own_head_or_body(self):
        hard, soft, report = build_internal_face_mask(
            (1344, 896),
            (431.3, 518.9, 487.7, 597.5),
            context_ring_pixels=18,
        )
        self.assertEqual(hard.shape, (1344, 896))
        self.assertEqual(soft.shape, (1344, 896))
        self.assertEqual(report["strategy"], MASK_INTERNAL_FACE)
        self.assertLess(report["soft_area_fraction"], 0.02)
        self.assertEqual(float(hard[450, 459]), 0.0)
        self.assertEqual(float(hard[800, 459]), 0.0)
        self.assertGreater(float(np.max(hard)), 0.0)


if __name__ == "__main__":
    unittest.main()

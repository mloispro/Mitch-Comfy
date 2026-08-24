from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

import krea2_reference_mask as subject


class InternalFaceOvalTests(unittest.TestCase):
    def test_ellipse_stays_inside_scaled_face_box(self):
        mask = subject.internal_face_oval(
            image_height=500,
            image_width=600,
            bbox=np.array([100, 50, 300, 350], dtype=np.float32),
            width_scale=0.80,
            height_scale=0.80,
            vertical_offset=0.0,
        )

        self.assertEqual(tuple(mask.shape), (500, 600))
        self.assertEqual(float(mask[200, 200]), 1.0)
        self.assertEqual(float(mask[200, 100]), 0.0)
        self.assertEqual(float(mask[50, 200]), 0.0)
        self.assertGreater(float(mask.sum()), 1.0)

    def test_node_uses_largest_detected_face(self):
        small = SimpleNamespace(bbox=np.array([10, 10, 40, 40], dtype=np.float32))
        large = SimpleNamespace(bbox=np.array([70, 50, 170, 180], dtype=np.float32))
        analyzer = SimpleNamespace(get=lambda _image: [small, large])
        image = torch.zeros((1, 200, 200, 3), dtype=torch.float32)

        with patch.object(subject, "_get_face_analyzer", return_value=analyzer):
            (mask,) = subject.Krea2ReferenceFaceAttentionMask().build(
                image, 0.82, 0.86, 0.02
            )

        self.assertEqual(tuple(mask.shape), (1, 200, 200))
        self.assertEqual(float(mask[0, 116, 120]), 1.0)
        self.assertEqual(float(mask[0, 25, 25]), 0.0)

    def test_missing_face_is_a_hard_failure(self):
        with self.assertRaisesRegex(RuntimeError, "No face was detected"):
            subject._largest_face([])


if __name__ == "__main__":
    unittest.main()

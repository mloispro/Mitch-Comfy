from __future__ import annotations

import unittest

import numpy as np

from flux2_klein9b_source_gaze_lock import _apply_with_landmarks


def landmarks(iris_shift: float = 0.0) -> np.ndarray:
    points = np.zeros((478, 2), dtype=np.float32)
    definitions = (
        ((33, 133), (160, 158), (144, 153), 468, (469, 470, 471, 472), 30.0),
        ((362, 263), (385, 387), (380, 373), 473, (474, 475, 476, 477), 100.0),
    )
    for corners, upper, lower, center_index, ring, left in definitions:
        points[corners[0]] = (left, 50.0)
        points[corners[1]] = (left + 40.0, 50.0)
        points[upper[0]] = (left + 12.0, 45.0)
        points[upper[1]] = (left + 28.0, 45.0)
        points[lower[0]] = (left + 12.0, 55.0)
        points[lower[1]] = (left + 28.0, 55.0)
        center = np.array((left + 20.0 + iris_shift, 50.0), dtype=np.float32)
        points[center_index] = center
        for index, offset in zip(ring, ((-3, 0), (0, -3), (3, 0), (0, 3))):
            points[index] = center + np.asarray(offset, dtype=np.float32)
    return points


class SourceGazeLockTests(unittest.TestCase):
    def test_no_detected_gaze_drift_leaves_every_pixel_exact(self):
        rng = np.random.default_rng(7)
        image = rng.random((100, 180, 3), dtype=np.float32)
        points = landmarks()
        output, mask, report = _apply_with_landmarks(image, points, points)
        self.assertTrue(np.array_equal(output, image))
        self.assertEqual(int(np.count_nonzero(mask)), 0)
        self.assertEqual(report["active_pixel_count"], 0)

    def test_shift_is_confined_inside_eroded_eye_interiors(self):
        rng = np.random.default_rng(9)
        image = rng.random((100, 180, 3), dtype=np.float32)
        candidate = landmarks()
        source = landmarks(iris_shift=4.0)
        output, mask, report = _apply_with_landmarks(
            image, source, candidate, strength=1.0
        )
        selected = mask > 0.0
        self.assertGreater(int(np.count_nonzero(selected)), 0)
        self.assertTrue(np.array_equal(output[~selected], image[~selected]))
        self.assertTrue(report["eyelid_boundary_pixels_protected"])
        self.assertTrue(report["background_face_hair_and_eye_shape_protected"])
        self.assertFalse(report["source_pixels_copied"])


if __name__ == "__main__":
    unittest.main()

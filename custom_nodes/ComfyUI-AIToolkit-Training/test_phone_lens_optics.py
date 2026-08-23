from __future__ import annotations

import unittest

import cv2
import numpy as np

from phone_lens_optics import apply_phone_lens_haze


class PhoneLensOpticsTests(unittest.TestCase):
    def _fixture(self) -> np.ndarray:
        height, width = 240, 160
        yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
        base = np.zeros((height, width, 3), dtype=np.float32)
        base[..., 0] = 0.08 + (0.42 * xx / width)
        base[..., 1] = 0.07 + (0.38 * yy / height)
        base[..., 2] = 0.09 + (0.28 * xx / width)
        texture = (((xx.astype(np.int32) + yy.astype(np.int32)) % 2) * 0.025).astype(
            np.float32
        )
        base += texture[..., None]
        cv2.circle(base, (145, 18), 26, (1.0, 0.96, 0.84), -1)
        return np.clip(base, 0.0, 1.0)

    def test_zero_strength_is_identity(self):
        image = self._fixture()
        result = apply_phone_lens_haze(image, 0.0)
        np.testing.assert_array_equal(result, image)

    def test_haze_lifts_dark_values_and_compresses_contrast(self):
        image = self._fixture()
        result = apply_phone_lens_haze(image)
        self.assertGreater(float(result[:60, :60].mean()), float(image[:60, :60].mean()))
        self.assertLess(float(result.std()), float(image.std()))

    def test_effect_is_stronger_near_bright_source(self):
        image = np.full((240, 160, 3), 0.25, dtype=np.float32)
        cv2.circle(image, (145, 18), 20, (1.0, 0.96, 0.84), -1)
        result = apply_phone_lens_haze(image)
        difference = np.abs(result - image).mean(axis=2)
        near = float(difference[35:100, 85:145].mean())
        far = float(difference[150:, :60].mean())
        self.assertGreater(near, far * 1.15)

    def test_detail_is_not_spatially_blurred(self):
        image = self._fixture()
        result = apply_phone_lens_haze(image)
        original_edges = cv2.Laplacian(image[80:180, :80], cv2.CV_32F).std()
        result_edges = cv2.Laplacian(result[80:180, :80], cv2.CV_32F).std()
        self.assertGreater(float(result_edges / original_edges), 0.90)

    def test_rejects_invalid_shape(self):
        with self.assertRaises(ValueError):
            apply_phone_lens_haze(np.zeros((16, 16), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()

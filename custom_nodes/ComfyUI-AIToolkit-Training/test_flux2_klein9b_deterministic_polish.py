import unittest

import cv2
import numpy as np

from flux2_klein9b_deterministic_polish import _attenuate_freckles, _naturalize_hair


class DeterministicPolishTests(unittest.TestCase):
    def test_dark_dot_removal_is_local_and_preserves_unselected_texture(self):
        height = width = 128
        rgb = np.full((height, width, 3), (0.72, 0.52, 0.42), dtype=np.float32)
        yy, xx = np.mgrid[0:height, 0:width]
        rgb += (((xx + yy) % 5) - 2)[..., None].astype(np.float32) / 1024.0
        for center in ((47, 66), (81, 66), (65, 70)):
            cv2.circle(rgb, center, 2, (0.42, 0.29, 0.22), thickness=-1)

        bbox = np.array([20.0, 15.0, 108.0, 120.0], dtype=np.float32)
        keypoints = np.array(
            [[47.0, 45.0], [81.0, 45.0], [65.0, 65.0], [51.0, 91.0], [79.0, 91.0]],
            dtype=np.float32,
        )
        output, alpha, report = _attenuate_freckles(rgb, bbox, keypoints)

        self.assertGreaterEqual(report["detected_spot_components"], 3)
        self.assertGreater(report["response_reduction_fraction"], 0.5)
        self.assertEqual(report["replacement"], "local_7x7_median")
        self.assertGreater(float(output[66, 47].mean()), float(rgb[66, 47].mean()))
        untouched = alpha == 0.0
        np.testing.assert_array_equal(output[untouched], rgb[untouched])
        np.testing.assert_array_equal(output[105:120, 50:80], rgb[105:120, 50:80])

    def test_hair_highlights_follow_existing_light_and_protect_boundary(self):
        height = width = 128
        horizontal = np.linspace(0.16, 0.34, width, dtype=np.float32)
        rgb = np.repeat(horizontal[None, :, None], height, axis=0)
        rgb = np.repeat(rgb, 3, axis=2)
        hair = np.zeros((height, width), dtype=np.uint8)
        hair[14:114, 14:114] = 255

        output, alpha, report = _naturalize_hair(rgb, hair)

        self.assertTrue(report["highlights_follow_existing_hair_luminance"])
        self.assertEqual(report["hairline_and_silhouette_protected_pixels"], 8)
        self.assertGreater(report["highlight_mean_weight_in_active_hair"], 0.0)
        self.assertEqual(float(alpha[18, 64]), 0.0)
        self.assertGreater(float(alpha[64, 96]), 0.5)
        np.testing.assert_array_equal(output[alpha == 0.0], rgb[alpha == 0.0])
        self.assertGreater(float(output[64, 96].mean()), float(rgb[64, 96].mean()))


if __name__ == "__main__":
    unittest.main()

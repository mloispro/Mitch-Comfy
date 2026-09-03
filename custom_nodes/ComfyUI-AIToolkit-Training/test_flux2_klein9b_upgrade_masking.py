import unittest

import numpy as np

from flux2_klein9b_upgrade_masking import (
    BACKGROUND_PROTECTION_DILATION_FRACTION,
    apply_natural_lens_background_blur,
    blur_background,
    compose_edit_masks,
)


class UpgradeMaskingTests(unittest.TestCase):
    def test_detailed_mode_exposes_background_and_face_separately(self):
        foreground = np.zeros((96, 96), dtype=np.float32)
        foreground[20:90, 28:68] = 1.0
        face = np.zeros_like(foreground)
        face[30:60, 36:60] = 1.0

        face_edit, detailed_combined, background = compose_edit_masks(
            foreground, face, True
        )
        _, blurred_combined, _ = compose_edit_masks(foreground, face, False)

        np.testing.assert_array_equal(face_edit, face)
        np.testing.assert_array_equal(blurred_combined, face)
        self.assertGreater(float(background[5, 5]), 0.95)
        self.assertLess(float(background[50, 48]), 0.05)
        self.assertEqual(float(detailed_combined[45, 48]), 1.0)
        self.assertGreater(float(detailed_combined[5, 5]), 0.95)

    def test_blurred_mode_keeps_subject_interior_and_changes_background(self):
        yy, xx = np.indices((96, 96))
        checker = (((xx // 2 + yy // 2) % 2) * 0.8 + 0.1).astype(np.float32)
        image = np.repeat(checker[..., None], 3, axis=2)
        foreground = np.zeros((96, 96), dtype=np.float32)
        foreground[18:90, 26:70] = 1.0

        result = blur_background(image, foreground)

        self.assertLess(float(np.abs(result[48, 48] - image[48, 48]).max()), 1e-6)
        self.assertGreater(float(np.abs(result[5, 5] - image[5, 5]).mean()), 0.1)

    def test_natural_lens_blur_protects_subject_and_excludes_its_colors(self):
        image = np.zeros((256, 256, 3), dtype=np.float32)
        image[..., 2] = 0.35
        yy, xx = np.indices((256, 256))
        image[..., 2] += (((xx // 2 + yy // 2) % 2) * 0.65).astype(np.float32)
        image[72:224, 92:164] = (1.0, 0.0, 0.0)
        foreground = np.zeros((256, 256), dtype=np.float32)
        foreground[72:224, 92:164] = 1.0

        result, blur_alpha, report = apply_natural_lens_background_blur(
            image, foreground
        )

        radius = max(2, round(256 * BACKGROUND_PROTECTION_DILATION_FRACTION))
        np.testing.assert_array_equal(
            result[72 - radius : 224 + radius, 92:164],
            image[72 - radius : 224 + radius, 92:164],
        )
        self.assertLess(float(result[128, 80, 0]), 1e-6)
        self.assertGreater(float(blur_alpha[20, 20]), 0.99)
        self.assertEqual(report["protected_subject_max_error_0_to_255"], 0.0)
        self.assertTrue(report["subject_colors_excluded_from_background_blur"])
        self.assertTrue(report["phone_on_path_unchanged"])


if __name__ == "__main__":
    unittest.main()

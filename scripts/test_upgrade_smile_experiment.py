"""Safety checks for the rejected, offline-only smile-remap experiment."""
import unittest

import numpy as np

from experimental_upgrade_smile_balance import (
    MAX_CORNER_SHIFT_MOUTH_WIDTH,
    _FACE_OVAL,
    apply_smile_balance,
    measure_smile,
)


class SmileExperimentTests(unittest.TestCase):
    def setUp(self):
        self.points = np.full((478, 2), (100, 100), np.float32)
        for index, landmark in enumerate(_FACE_OVAL):
            angle = -np.pi / 2 + index * 2 * np.pi / len(_FACE_OVAL)
            self.points[landmark] = (100 + 80*np.cos(angle), 100 + 90*np.sin(angle))
        self.points[[33, 133]] = [(63, 77), (89, 77)]
        self.points[[362, 263]] = [(112, 77), (139, 77)]
        self.points[1] = (100, 105)
        self.points[[13, 14]] = [(100, 140), (100, 141)]
        self.points[[61, 291]] = [(70, 133), (135, 132)]
        self.source = self.points.copy()
        self.source[[61, 291]] = [(71, 141), (136, 129)]
        yy, xx = np.mgrid[:200, :200]
        self.rgb = np.stack((xx/240, yy/240, (xx+yy)/480), axis=2).astype(np.float32)
        self.hair = np.zeros((200, 200), np.uint8)
        self.hair[:20] = 255

    def test_zero_strength_and_neutral_source_are_noops(self):
        output, mask, _ = apply_smile_balance(self.rgb, self.points, self.source, self.hair, 0)
        np.testing.assert_array_equal(output, self.rgb)
        self.assertEqual(np.count_nonzero(mask), 0)
        self.source[[61, 291], 1] = 141
        output, mask, report = apply_smile_balance(self.rgb, self.points, self.source, self.hair)
        np.testing.assert_array_equal(output, self.rgb)
        self.assertEqual(report['status'], 'skipped_not_closed_mouth_source_smile')

    def test_open_source_is_not_forced_closed(self):
        self.source[14, 1] = 157
        output, mask, report = apply_smile_balance(self.rgb, self.points, self.source, self.hair)
        np.testing.assert_array_equal(output, self.rgb)
        self.assertEqual(np.count_nonzero(mask), 0)

    def test_active_remap_is_bounded_and_preserves_eyes_and_hair(self):
        output, mask, report = apply_smile_balance(self.rgb, self.points, self.source, self.hair)
        self.assertEqual(report['status'], 'applied')
        self.assertGreater(np.count_nonzero(mask), 0)
        np.testing.assert_array_equal(output[mask == 0], self.rgb[mask == 0])
        np.testing.assert_array_equal(output[:100], self.rgb[:100])
        self.assertTrue(np.isfinite(output).all())
        bound = measure_smile(self.points)['width'] * MAX_CORNER_SHIFT_MOUTH_WIDTH
        self.assertLessEqual(report['maximum_field_shift_pixels'], bound + 0.001)
        self.assertFalse(report['source_pixels_copied'])

    def test_expression_measurement_is_rigid_transform_invariant(self):
        angle = 0.42
        rotation = np.array([[np.cos(angle), -np.sin(angle)],
                             [np.sin(angle), np.cos(angle)]], np.float32)
        transformed = self.source @ rotation.T * 1.3 + (20, 17)
        np.testing.assert_allclose(measure_smile(transformed)['corner_coordinates'],
                                   measure_smile(self.source)['corner_coordinates'], atol=1e-6)

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            apply_smile_balance(self.rgb, self.points, self.source, self.hair, 2)
        with self.assertRaises(ValueError):
            apply_smile_balance(self.rgb, self.points, self.source, self.hair[:10])
        with self.assertRaises(ValueError):
            measure_smile(np.zeros((468, 2)))
        self.source[1, 0] = np.nan
        with self.assertRaises(ValueError):
            measure_smile(self.source)


if __name__ == '__main__':
    unittest.main()

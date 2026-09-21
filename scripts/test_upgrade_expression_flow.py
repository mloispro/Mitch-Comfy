import unittest
import cv2
import numpy as np
from experimental_upgrade_expression_flow import (
    estimate_inverse_flow, cycle_diagnostics, native_displacement, remap_original,
)


class ExpressionFlowTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(54)
        self.raw = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8)
        self.zero = np.zeros((128, 128, 2), np.float32)
        mask = np.zeros((128, 128), np.uint8)
        cv2.circle(mask, (64, 64), 45, 1, -1)
        self.support = np.minimum(cv2.distanceTransform(mask, cv2.DIST_L2, 5) / 16, 1)

    def test_self_flow_and_zero_are_exact(self):
        a, b = estimate_inverse_flow(self.raw, self.raw.copy())
        self.assertFalse(a.any())
        self.assertTrue(cycle_diagnostics(a, b, self.support)['passed'])
        after, report = remap_original(self.raw, a, self.support, 90)
        np.testing.assert_array_equal(after, self.raw)
        self.assertTrue(report['zero_displacement_exact'])

    def test_known_translation(self):
        # The edited image is shifted RIGHT 3, so inverse flow must point LEFT.
        texture = cv2.GaussianBlur(self.raw, (5, 5), .7)
        edited = cv2.warpAffine(texture, np.float32([[1, 0, 3], [0, 1, 0]]), (128, 128), borderMode=cv2.BORDER_REFLECT_101)
        inverse, forward = estimate_inverse_flow(texture, edited)
        np.testing.assert_allclose(np.median(inverse[25:100, 25:100], axis=(0, 1)), [-3, 0], atol=.35)
        self.assertTrue(cycle_diagnostics(inverse, forward, self.support)['passed'])

    def test_crop_affine_vector_pushforward(self):
        field = np.full((32, 32, 2), [2, 0], np.float32)
        # 90 degree rotation plus 2x scale maps (2,0) to (0,4).
        matrix = np.float32([[0, -2, 80], [2, 0, 10]])
        native = native_displacement(field, matrix, (128, 128))
        np.testing.assert_allclose(native[42, 48], [0, 4], atol=1e-6)

    def test_original_immutable_and_exterior_exact(self):
        before = self.raw.copy()
        field = self.zero.copy(); field[..., 0] = 3
        after, report = remap_original(self.raw, field, self.support, 90)
        np.testing.assert_array_equal(before, self.raw)
        np.testing.assert_array_equal(after[self.support == 0], before[self.support == 0])
        self.assertTrue(report['outside_support_exact'])
        self.assertFalse(np.array_equal(after, before))

    def test_fold_rejected(self):
        field = self.zero.copy()
        field[..., 0] = -2 * np.arange(128)[None, :]
        with self.assertRaisesRegex(ValueError, 'folded'):
            remap_original(self.raw, field, np.ones((128, 128)), 10000)

    def test_excessive_motion_rejected(self):
        field = self.zero.copy(); field[..., 0] = 13
        with self.assertRaisesRegex(ValueError, 'excessive'):
            remap_original(self.raw, field, np.ones((128, 128)), 100)

    def test_invalid_inputs_rejected(self):
        bad = self.zero.copy(); bad[64, 64] = np.nan
        with self.assertRaises(ValueError):
            remap_original(self.raw, bad, self.support, 90)
        with self.assertRaises(ValueError):
            native_displacement(self.zero, np.zeros((2, 3)), (128, 128))
        with self.assertRaises(ValueError):
            estimate_inverse_flow(self.raw, self.raw.astype(float))


if __name__ == '__main__':
    unittest.main()

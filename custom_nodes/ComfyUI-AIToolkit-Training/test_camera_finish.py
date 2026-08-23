from __future__ import annotations

import unittest

import torch

from camera_finish import apply_natural_phone_finish


class CameraFinishTests(unittest.TestCase):
    def test_finish_is_deterministic_and_preserves_shape(self):
        image = torch.linspace(0, 1, 64 * 96 * 3).reshape(1, 64, 96, 3)
        first, report = apply_natural_phone_finish(image)
        second, _ = apply_natural_phone_finish(image)
        self.assertEqual(first.shape, image.shape)
        self.assertTrue(torch.equal(first, second))
        self.assertEqual(report["extra_model_passes"], 0)

    def test_finish_is_restrained(self):
        ramp = torch.linspace(0.1, 0.9, 96).view(1, 1, 96, 1)
        image = ramp.expand(1, 96, 96, 3).clone()
        finished, _ = apply_natural_phone_finish(image)
        self.assertLess(float(torch.mean(torch.abs(finished - image))), 0.08)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

import torch

from whole_frame_phone_finish import phone_finish_frame


class WholeFramePhoneFinishTests(unittest.TestCase):
    def setUp(self):
        height, width = 96, 64
        y = torch.linspace(0.15, 0.85, height).view(height, 1, 1)
        x = torch.linspace(0.10, 0.90, width).view(1, width, 1)
        self.frame = torch.cat(
            (
                (0.65 * x + 0.35 * y).expand(height, width, 1),
                (0.45 * x + 0.55 * y).expand(height, width, 1),
                (0.25 * x + 0.75 * y).expand(height, width, 1),
            ),
            dim=2,
        )

    def test_finish_is_deterministic_and_preserves_shape(self):
        first = phone_finish_frame(self.frame)
        second = phone_finish_frame(self.frame)
        self.assertEqual(first.shape, self.frame.shape)
        self.assertTrue(torch.equal(first, second))

    def test_finish_is_restrained_but_not_a_noop(self):
        finished = phone_finish_frame(self.frame)
        delta = torch.abs(finished - self.frame)
        self.assertGreater(float(delta.mean()), 0.0001)
        self.assertLess(float(delta.mean()), 0.02)
        self.assertLess(float(delta.max()), 0.10)


if __name__ == "__main__":
    unittest.main()

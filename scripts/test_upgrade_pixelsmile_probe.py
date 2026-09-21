import importlib.util
from pathlib import Path
import unittest

import torch

PATH = Path(__file__).resolve().parents[1]/'custom_nodes/ComfyUI-AIToolkit-Training/pixelsmile_experiment.py'
spec = importlib.util.spec_from_file_location('pixelsmile_experiment', PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class PixelSmileTests(unittest.TestCase):
    def setUp(self):
        self.target = [[torch.ones((1,6,4)), {}]]
        self.neutral = [[torch.zeros((1,6,4)), {}]]

    def test_endpoints_and_midpoint(self):
        for score in (0,.5,1):
            out = probe.blend_equal(self.target,self.neutral,score)
            torch.testing.assert_close(out[0][0],torch.full((1,6,4),score,dtype=torch.float32))
        self.assertEqual(float(self.target[0][0].sum()),24)

    def test_no_implicit_padding_or_mask_mismatch(self):
        with self.assertRaises(ValueError):
            probe.blend_equal(self.target,[[torch.zeros((1,7,4)),{}]],.5)
        with self.assertRaises(ValueError):
            probe.blend_equal(self.target,[[torch.zeros((1,6,4)),{'attention_mask':torch.ones((1,6))}]],.5)

    def test_invalid_values(self):
        for score in (-1,2,float('nan')):
            with self.assertRaises(ValueError):probe.blend_equal(self.target,self.neutral,score)
        with self.assertRaises(ValueError):
            probe.blend_equal([[torch.full((1,6,4),float('nan')),{}]],self.neutral,.5)

    def test_published_sigma_endpoints(self):
        sigmas = probe.expression_sigmas()
        self.assertEqual(tuple(sigmas.shape),(51,))
        self.assertAlmostEqual(float(sigmas[0]),1)
        self.assertAlmostEqual(float(sigmas[-2]),.02,places=6)
        self.assertEqual(float(sigmas[-1]),0)
        self.assertTrue(bool(torch.all(sigmas[:-1]>sigmas[1:])))

    def test_reject_unsupported_layout_and_unpatched_model(self):
        with self.assertRaises(ValueError):probe.expression_sigmas(width=816,height=1088)
        class Model:
            patches = {}
        with self.assertRaises(ValueError):probe.validate_patches(Model())


if __name__ == '__main__':unittest.main()

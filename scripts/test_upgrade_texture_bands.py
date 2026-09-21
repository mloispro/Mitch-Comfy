import importlib.util
from pathlib import Path
import unittest

import cv2
import numpy as np

spec=importlib.util.spec_from_file_location('texture',Path(__file__).with_name('diagnose-upgrade-texture-bands.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class TextureBandTests(unittest.TestCase):
    def setUp(self):
        self.mask=np.zeros((128,128),bool);self.mask[20:-20,20:-20]=True
        rng=np.random.default_rng(3)
        self.image=np.repeat((128+rng.normal(0,8,(128,128)))[...,None],3,axis=2).astype(np.float32)

    def test_constant_is_flat(self):
        report,_=module.profile(np.full((128,128,3),128,np.uint8),self.mask,1)
        for band in report['bands'].values(): self.assertLess(band['std_0_to_255'],1e-4)

    def test_blur_reduces_fine_contrast_without_mutating_input(self):
        original=self.image.copy()
        raw,_=module.profile(self.image,self.mask,1)
        blurred=cv2.GaussianBlur(self.image,(0,0),2)
        smooth,_=module.profile(blurred,self.mask,1)
        self.assertLess(smooth['bands']['fine']['std_0_to_255'],raw['bands']['fine']['std_0_to_255']*.3)
        np.testing.assert_array_equal(self.image,original)

    def test_constant_exposure_offset_does_not_create_texture(self):
        raw,_=module.profile(self.image,self.mask,1)
        shifted,_=module.profile(self.image+20,self.mask,1)
        for name in raw['bands']:
            self.assertAlmostEqual(raw['bands'][name]['std_0_to_255'],shifted['bands'][name]['std_0_to_255'],places=4)

    def test_invalid_scale_and_mask(self):
        for scale in (0,-1,float('nan')):
            with self.assertRaises(ValueError): module.texture_bands(self.image,scale)
        with self.assertRaises(ValueError): module.profile(self.image,np.zeros_like(self.mask),1)


if __name__=='__main__': unittest.main()

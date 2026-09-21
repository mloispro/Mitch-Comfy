import unittest
import cv2
import numpy as np
from test_upgrade_source_expression import SourceExpressionTests
from experimental_upgrade_source_brows import apply_source_brows,soften_glabellar_band
from flux2_klein9b_attractiveness import _BROWS, _EYE_CONTOURS, _LIPS


class BrowTests(unittest.TestCase):
    def setUp(self):
        fixture=SourceExpressionTests();fixture.setUp()
        self.rgb,self.points,self.hair=fixture.rgb,fixture.points,fixture.hair
        self.source=self.points.copy()
        for ids in _BROWS: self.source[list(ids),1]+=3

    def test_noop(self):
        for strength,source in ((0,self.source),(.8,self.points)):
            result,mask,_=apply_source_brows(self.rgb,self.points,source,self.hair,strength)
            np.testing.assert_array_equal(result,self.rgb)
            self.assertEqual(np.count_nonzero(mask),0)

    def test_guard_and_no_fold(self):
        result,mask,report=apply_source_brows(self.rgb,self.points,self.source,self.hair)
        self.assertGreater(np.count_nonzero(mask),0)
        self.assertGreaterEqual(report['minimum_inverse_jacobian'],.30)
        self.assertGreaterEqual(report['safety_retained_fraction'],.60)
        self.assertEqual(report['protected_pixel_max_error_0_to_255'],0)
        np.testing.assert_array_equal(result[mask==0],self.rgb[mask==0])
        np.testing.assert_array_equal(result[self.hair>0],self.rgb[self.hair>0])
        for ids in (*_EYE_CONTOURS,_LIPS):
            guard=np.zeros(self.hair.shape,np.uint8)
            cv2.fillPoly(guard,[np.rint(self.points[list(ids)]).astype(np.int32)],255)
            np.testing.assert_array_equal(result[guard>0],self.rgb[guard>0])

    def test_invalid(self):
        for strength in (-1,1.1,float('nan')):
            with self.assertRaises(ValueError): apply_source_brows(self.rgb,self.points,self.source,self.hair,strength)

    def test_local_band_keeps_same_texture_measurement_scale(self):
        yy,xx=np.mgrid[:400,:400]
        light=.5+.012*np.sin(xx*2.3)*np.cos(yy*1.7)-.08*np.exp(-.5*((xx-200)/5)**2-.5*((yy-100)/35)**2)
        photo=np.repeat(light[...,None],3,axis=2).astype(np.float32)
        first=soften_glabellar_band(photo,self.points,self.hair,1.)
        second=soften_glabellar_band(photo,self.points,self.hair,2.)
        self.assertEqual(first[2]['measurement_sigma_unchanged'],second[2]['measurement_sigma_unchanged'])
        self.assertEqual(second[2]['fine_sigma'],first[2]['fine_sigma']*2)
        self.assertTrue(second[2]['texture_exposure_guard_passed'])
        self.assertGreaterEqual(second[2]['fine_band_retention'],.9)
        for result,mask,report in (first,second):
            self.assertTrue(np.isfinite(result).all())
            self.assertEqual(report['feature_guard_pixel_max_error_0_to_255'],0)
            np.testing.assert_array_equal(result[mask==0],photo[mask==0])

    def test_no_valid_region_is_not_a_claimed_pass(self):
        result,mask,report=soften_glabellar_band(self.rgb,self.points,np.ones(self.hair.shape,np.uint8))
        np.testing.assert_array_equal(result,self.rgb)
        self.assertEqual(np.count_nonzero(mask),0)
        self.assertFalse(report['texture_exposure_guard_passed'])


if __name__=='__main__': unittest.main()

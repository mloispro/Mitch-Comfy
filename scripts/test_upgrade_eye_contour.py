import unittest
import numpy as np
from test_upgrade_source_expression import SourceExpressionTests
from experimental_upgrade_eye_contour import contour_polish


class EyeContourTests(unittest.TestCase):
    def setUp(self):
        f=SourceExpressionTests();f.setUp()
        self.rgb,self.points,self.hair=f.rgb,f.points,f.hair

    def test_noop(self):
        out,mask,_=contour_polish(self.rgb,self.points,self.hair,0)
        np.testing.assert_array_equal(out,self.rgb)
        self.assertEqual(np.count_nonzero(mask),0)

    def test_geometry_safety_and_fixed_pixels(self):
        out,mask,report=contour_polish(self.rgb,self.points,self.hair)
        self.assertGreater(np.count_nonzero(mask),0)
        self.assertGreaterEqual(report['minimum_inverse_jacobian'],.25)
        self.assertGreaterEqual(report['safety_fraction'],.6)
        np.testing.assert_array_equal(out[mask==0],self.rgb[mask==0])
        for x,y in self.points[[468,473]].astype(int):
            np.testing.assert_array_equal(out[y,x],self.rgb[y,x])
        self.assertTrue(np.isfinite(out).all())

    def test_invalid_input(self):
        for strength in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError): contour_polish(self.rgb,self.points,self.hair,strength)
        with self.assertRaises(ValueError): contour_polish(self.rgb,self.points[:2],self.hair)
        with self.assertRaises(ValueError): contour_polish(self.rgb,self.points,self.hair,aperture_scale=.1)

    def test_no_narrowing_refinement_keeps_other_targets(self):
        _,_,old=contour_polish(self.rgb,self.points,self.hair)
        out,mask,new=contour_polish(self.rgb,self.points,self.hair,aperture_scale=1.)
        self.assertEqual(new['aperture_scale_requested'],1.)
        for key in ('width_scale_requested','outer_corner_lift_eye_width_requested'):
            self.assertEqual(old[key],new[key])
        np.testing.assert_array_equal(out[mask==0],self.rgb[mask==0])


if __name__=='__main__': unittest.main()

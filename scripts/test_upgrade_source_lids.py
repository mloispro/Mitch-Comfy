import unittest
import numpy as np
from test_upgrade_source_expression import SourceExpressionTests
from experimental_upgrade_source_lids import apply_source_lids,upper_lid_targets
from flux2_klein9b_attractiveness import _UPPER_LIDS


class SourceLidTests(unittest.TestCase):
    def setUp(self):
        fixture=SourceExpressionTests();fixture.setUp()
        self.rgb,self.points,self.hair=fixture.rgb,fixture.points,fixture.hair
        self.source=self.points.copy()
        for ids in _UPPER_LIDS: self.source[list(ids[1:-1]),1]-=2.5

    def test_exact_noop(self):
        for source,strength in ((self.source,0),(self.points,.9)):
            output,mask,_=apply_source_lids(self.rgb,self.points,source,self.hair,strength)
            np.testing.assert_array_equal(output,self.rgb)
            self.assertEqual(mask.sum(),0)

    def test_source_target_does_not_invent_width_or_corner_angle(self):
        for ids in _UPPER_LIDS:
            target,width,axis,_=upper_lid_targets(self.points,self.source,ids)
            current=self.points[list(ids)]
            np.testing.assert_allclose(target[[0,-1]],current[[0,-1]])
            np.testing.assert_allclose((target-current)@axis,0,atol=1e-5)
            np.testing.assert_allclose(target[1:-1,1],self.source[list(ids[1:-1]),1],atol=1e-5)

    def test_reaches_curvature_without_changing_fixed_pixels(self):
        output,mask,report=apply_source_lids(self.rgb,self.points,self.source,self.hair)
        self.assertGreater(mask.sum(),0)
        np.testing.assert_array_equal(output[mask==0],self.rgb[mask==0])
        np.testing.assert_array_equal(output[:35],self.rgb[:35])
        for x,y in self.points[[468,473,1,61,291]].astype(int):
            np.testing.assert_array_equal(output[y,x],self.rgb[y,x])
        self.assertGreaterEqual(report['minimum_inverse_jacobian'],.25)
        self.assertLessEqual(report['maximum_inverse_jacobian'],3)
        for eye in report['eyes']:
            self.assertLess(eye['mean_source_target_error_after_map_pixels'],eye['mean_source_target_error_before_pixels']*.35)
            self.assertLess(eye['fixed_corner_max_displacement_pixels'],.1)

    def test_invalid(self):
        for strength in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError): apply_source_lids(self.rgb,self.points,self.source,self.hair,strength)
        with self.assertRaises(ValueError): apply_source_lids(self.rgb,self.points[:2],self.source,self.hair)


if __name__=='__main__': unittest.main()

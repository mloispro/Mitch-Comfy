import unittest
import numpy as np
import test_upgrade_source_expression as fixtures
from experimental_upgrade_registered_blend import registered_blend, inverse_field


class RegisteredBlendTests(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.SourceExpressionTests();fixture.setUp()
        self.points=fixture.points;self.hair=fixture.hair
        self.base=fixture.rgb;self.beauty=np.clip(self.base+.1,0,1)

    def test_zero_and_identical_are_exact(self):
        for image,amount in ((self.beauty,0),(self.base,.4)):
            output,mask,_,_=registered_blend(self.base,image,self.points,self.points,self.hair,amount)
            np.testing.assert_array_equal(output,self.base)
            self.assertEqual(mask.sum(),0)

    def test_aligned_color_blend_preserves_exterior_and_hair(self):
        output,mask,report,_=registered_blend(self.base,self.beauty,self.points,self.points,self.hair,.4)
        np.testing.assert_array_equal(output[mask==0],self.base[mask==0])
        np.testing.assert_array_equal(output[self.hair>0],self.base[self.hair>0])
        np.testing.assert_allclose(output[mask==1],self.base[mask==1]*.6+self.beauty[mask==1]*.4,atol=1e-6)
        self.assertEqual(report['base_alignment']['minimum_inverse_jacobian'],1)
        self.assertFalse(report['identity_conditioning'])

    def test_small_geometry_is_safe(self):
        points=self.points.copy();points[1]+=(1,1)
        output,mask,report,_=registered_blend(self.base,self.beauty,self.points,points,self.hair,.4)
        self.assertTrue(np.isfinite(output).all())
        self.assertGreaterEqual(report['base_alignment']['minimum_inverse_jacobian'],.25)
        np.testing.assert_array_equal(output[mask==0],self.base[mask==0])

    def test_invalid_inputs(self):
        for amount in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError): registered_blend(self.base,self.beauty,self.points,self.points,self.hair,amount)
        with self.assertRaises(ValueError): registered_blend(self.base,self.beauty[:10],self.points,self.points,self.hair,.4)

    def test_degenerate_controls_rejected(self):
        with self.assertRaises(ValueError): inverse_field(np.zeros((10,2)),np.zeros((10,2)),(20,20),np.ones((20,20)),20)

    def test_folded_inverse_map_is_rejected(self):
        controls=np.array([(x,y) for y in (0,10,19) for x in (0,10,19)],float)
        mirrored=controls.copy();mirrored[:,0]=19-mirrored[:,0]
        with self.assertRaisesRegex(ValueError,'Unsafe inverse field: min Jacobian=-'):
            inverse_field(controls,mirrored,(20,20),np.ones((20,20)),1000)

    def test_oversized_translation_is_rejected(self):
        controls=np.array([(x,y) for y in (0,10,19) for x in (0,10,19)],float)
        with self.assertRaisesRegex(ValueError,'Unsafe inverse field'):
            inverse_field(controls,controls+20,(20,20),np.ones((20,20)),50)

    def test_inputs_are_not_mutated(self):
        changed_points=self.points.copy();changed_points[1]+=(1,1)
        arrays=[self.base,self.beauty,self.points,changed_points,self.hair]
        originals=[array.copy() for array in arrays]
        registered_blend(*arrays,.4)
        for array,original in zip(arrays,originals):
            np.testing.assert_array_equal(array,original)


if __name__=='__main__': unittest.main()

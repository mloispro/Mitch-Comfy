import unittest
import numpy as np
from test_upgrade_source_expression import SourceExpressionTests
from experimental_upgrade_eye_definition import apply_eye_definition,feature_regions,definition_profile


class EyeDefinitionTests(unittest.TestCase):
    def setUp(self):
        fixture=SourceExpressionTests();fixture.setUp()
        self.points,self.hair=fixture.points,fixture.hair
        yy,xx=np.mgrid[:400,:400]
        base=.25+.08*np.sin(xx*.6)*np.cos(yy*.3)
        self.rgb=np.stack((base*.9,base,base*1.1),axis=2).astype(np.float32)

    def test_zero_and_uniform_images_do_not_change(self):
        output,mask,_=apply_eye_definition(self.rgb,self.points,self.hair,0)
        np.testing.assert_array_equal(output,self.rgb);self.assertEqual(mask.sum(),0)
        uniform=np.full_like(self.rgb,.25)
        output,mask,_=apply_eye_definition(uniform,self.points,self.hair)
        np.testing.assert_array_equal(output,uniform);self.assertEqual(mask.sum(),0)

    def test_only_existing_iris_brow_changes(self):
        output,mask,report=apply_eye_definition(self.rgb,self.points,self.hair)
        self.assertGreater(mask.sum(),0)
        np.testing.assert_array_equal(output[mask==0],self.rgb[mask==0])
        for region in feature_regions(self.rgb.shape[:2],self.points):
            protected=region['pupil_core']|region['sclera']
            np.testing.assert_array_equal(output[protected],self.rgb[protected])
        np.testing.assert_array_equal(output[self.hair>0],self.rgb[self.hair>0])
        self.assertFalse(report['geometric_warp'])
        self.assertTrue(np.isfinite(output).all());self.assertGreaterEqual(output.min(),0);self.assertLessEqual(output.max(),1)
        # Channel ratios, hence hue, remain unchanged before final8-bit rounding.
        np.testing.assert_allclose(output[:,:,0]/output[:,:,1],self.rgb[:,:,0]/self.rgb[:,:,1],atol=1e-6)
        np.testing.assert_allclose(output[:,:,2]/output[:,:,1],self.rgb[:,:,2]/self.rgb[:,:,1],atol=1e-6)

    def test_diagnostic_excludes_pupil_core(self):
        mask,stats=definition_profile(np.rint(self.rgb*255).astype(np.uint8),self.points)
        self.assertEqual(len(stats),2)
        for region in feature_regions(self.rgb.shape[:2],self.points):
            self.assertEqual(np.count_nonzero(mask[region['pupil_core']]),0)

    def test_invalid_inputs_rejected(self):
        for value in (-1,1.1,float('nan')):
            with self.assertRaises(ValueError):apply_eye_definition(self.rgb,self.points,self.hair,value)
        with self.assertRaises(ValueError):apply_eye_definition(self.rgb,self.points[:2],self.hair)


if __name__=='__main__':unittest.main()

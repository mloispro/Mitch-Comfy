"""CPU-only geometry safety checks; synthetic grids are not identity evidence."""
import unittest
import numpy as np

from experimental_upgrade_whole_face_shape import shape_targets,whole_face_shape
import test_upgrade_source_expression as expression_fixtures


class WholeFaceShapeTests(unittest.TestCase):
    def setUp(self):
        fixture = expression_fixtures.SourceExpressionTests();fixture.setUp()
        self.points,self.rgb,self.hair = fixture.points,fixture.rgb,fixture.hair

    def test_identical_and_zero_are_pixel_exact(self):
        for strength in (0,.8):
            out,mask,_ = whole_face_shape(self.rgb,self.points,self.points,self.hair,strength)
            np.testing.assert_array_equal(out,self.rgb)
            self.assertFalse(np.any(mask))

    def test_lower_outline_is_not_pinned(self):
        source = self.points.copy();source[152,1] += 5
        target,report = shape_targets(self.points,source,.8)
        self.assertAlmostEqual(target[152,1]-self.points[152,1],4)
        self.assertFalse(report['lower_face_silhouette_fixed'])

    def test_forehead_and_iris_radius_protected(self):
        source = self.points.copy();source[:,0] += 4;source[10,1] += 12
        target,_ = shape_targets(self.points,source,.8)
        np.testing.assert_allclose(target[10],self.points[10])
        for center,ring in ((468,(469,470,471,472)),(473,(474,475,476,477))):
            np.testing.assert_allclose(target[list(ring)]-target[center],self.points[list(ring)]-self.points[center])

    def test_active_small_lower_face_warp_preserves_exterior(self):
        source = self.points.copy();source[152,1] += 2
        out,mask,report = whole_face_shape(self.rgb,self.points,source,self.hair,.8)
        self.assertTrue(np.any(mask))
        np.testing.assert_array_equal(out[mask==0],self.rgb[mask==0])
        np.testing.assert_array_equal(out[self.hair>0],self.rgb[self.hair>0])
        self.assertGreaterEqual(report['minimum_inverse_jacobian'],.20)

    def test_feature_cage_keeps_lower_outline_and_exterior_contract(self):
        source = self.points.copy();source[152,1] += 2
        out,mask,report = whole_face_shape(self.rgb,self.points,source,self.hair,.8,'feature_cage')
        self.assertFalse(report['lower_face_silhouette_fixed'])
        self.assertLess(report['semantic_control_count'],200)
        np.testing.assert_array_equal(out[mask==0],self.rgb[mask==0])
        self.assertGreaterEqual(report['minimum_inverse_jacobian'],.20)

    def test_invalid_inputs_rejected(self):
        for strength in (-1,1.1,float('nan')):
            with self.assertRaises(ValueError):
                shape_targets(self.points,self.points,strength)
        with self.assertRaises(ValueError):
            whole_face_shape(self.rgb,self.points,self.points,self.hair[:2],.8)


if __name__ == '__main__':
    unittest.main()

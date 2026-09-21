"""CPU safety tests for the offline expression-geometry prototype."""
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'custom_nodes/ComfyUI-AIToolkit-Training'))
from flux2_klein9b_attractiveness import _OVAL, _EYE_CONTOURS, _IRISES, _BROWS, _LIPS
from experimental_upgrade_source_expression import apply_source_expression


class SourceExpressionTests(unittest.TestCase):
    def setUp(self):
        self.points=np.full((478,2),(200.,230.),np.float32)
        for i,index in enumerate(_OVAL):
            angle=-np.pi/2+i*2*np.pi/len(_OVAL)
            self.points[index]=(200+155*np.cos(angle),200+180*np.sin(angle))
        self.points[1]=(200,213)
        for center,contour,iris,brow,flip in zip(((150,150),(250,150)),_EYE_CONTOURS,_IRISES,_BROWS,(1,-1)):
            for i,index in enumerate(contour):
                angle=np.pi+i*2*np.pi/16
                self.points[index]=(center[0]+flip*30*np.cos(angle),center[1]+12*np.sin(angle))
            self.points[iris[0]]=center
            for i,index in enumerate(iris[1:]):
                angle=i*np.pi/2
                self.points[index]=(center[0]+8*np.cos(angle),center[1]+8*np.sin(angle))
            for i,index in enumerate(brow):
                angle=np.pi+i*2*np.pi/len(brow)
                self.points[index]=(center[0]+32*np.cos(angle),center[1]-30+4*np.sin(angle))
        for i,index in enumerate(_LIPS):
            angle=np.pi+i*2*np.pi/len(_LIPS)
            self.points[index]=(200+43*np.cos(angle),265+6*np.sin(angle))
        self.points[[61,291,13,14]]=[(157,263),(243,262),(200,266),(200,267)]
        self.source=self.points.copy()
        self.source[[33,263],1]-=2.
        self.source[[61,291],1]+=(2.,-2.)
        yy,xx=np.mgrid[:400,:400]
        self.rgb=np.stack((xx/500,yy/500,(xx+yy)/1000),axis=-1).astype(np.float32)
        self.hair=np.zeros((400,400),np.uint8); self.hair[:35]=255

    def test_zero_strength_is_exact_noop(self):
        result,mask,_=apply_source_expression(self.rgb,self.points,self.source,self.hair,0)
        np.testing.assert_array_equal(result,self.rgb)
        self.assertEqual(np.count_nonzero(mask),0)

    def test_identical_expression_is_exact_noop(self):
        result,mask,_=apply_source_expression(self.rgb,self.points,self.points,self.hair,.85)
        np.testing.assert_array_equal(result,self.rgb)
        self.assertEqual(np.count_nonzero(mask),0)

    def test_active_deformation_keeps_protected_regions_exact(self):
        result,mask,report=apply_source_expression(self.rgb,self.points,self.source,self.hair,.85)
        self.assertTrue(np.isfinite(result).all())
        self.assertGreater(np.count_nonzero(mask),0)
        self.assertGreaterEqual(report['minimum_eye_inverse_jacobian'],.20)
        self.assertGreaterEqual(report['minimum_mouth_inverse_jacobian'],.25)
        self.assertEqual(report['protected_pixel_max_error_0_to_255'],0)
        np.testing.assert_array_equal(result[mask==0],self.rgb[mask==0])
        np.testing.assert_array_equal(result[:35],self.rgb[:35])
        for ids in _IRISES:
            iris=np.zeros((400,400),np.uint8)
            cv2.fillPoly(iris,[np.rint(self.points[list(ids[1:])]).astype(np.int32)],255)
            np.testing.assert_array_equal(result[iris>0],self.rgb[iris>0])
        self.assertFalse(report['source_pixels_copied'])
        self.assertFalse(report['identity_conditioning'])

    def test_invalid_inputs_fail(self):
        for strength in (-.1,1.1,float('nan')):
            with self.assertRaises(ValueError):
                apply_source_expression(self.rgb,self.points,self.source,self.hair,strength)
        with self.assertRaises(ValueError):
            apply_source_expression(self.rgb,self.points[:468],self.source,self.hair)
        with self.assertRaises(ValueError):
            apply_source_expression(self.rgb,self.points,self.source,self.hair[:100])
        self.source[33,0]=np.nan
        with self.assertRaises(ValueError):
            apply_source_expression(self.rgb,self.points,self.source,self.hair)


if __name__=='__main__': unittest.main()

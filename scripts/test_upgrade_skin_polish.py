import unittest
import numpy as np
import cv2
from test_upgrade_source_expression import SourceExpressionTests
from experimental_upgrade_skin_polish import polish_skin,skin_regions


class SkinTests(unittest.TestCase):
    def setUp(self):
        f=SourceExpressionTests();f.setUp()
        self.points,self.hair=f.points,f.hair
        yy,xx=np.mgrid[:400,:400]
        self.rgb=np.broadcast_to([.65,.48,.40],(400,400,3)).astype(np.float32).copy()
        self.rgb+=np.sin(xx*2.5)[...,None]*.002

    def test_identical_source_warmth_is_noop(self):
        output,mask,report=polish_skin(self.rgb,self.points,self.rgb,self.points,self.hair,'warmth')
        np.testing.assert_array_equal(output,self.rgb)
        self.assertEqual(np.count_nonzero(mask),0)
        self.assertEqual(report['warmth']['maximum_applied_Lab_ab_shift'],[0.,0.])

    def test_warmth_is_bounded_with_fixed_features(self):
        source=self.rgb.copy();source[:,:,0]+=.1;source[:,:,2]-=.1
        output,mask,report=polish_skin(self.rgb,self.points,source,self.points,self.hair,'warmth')
        self.assertGreater(np.count_nonzero(mask),0)
        self.assertLessEqual(report['warmth']['maximum_applied_Lab_ab_shift'][0],3)
        self.assertLessEqual(report['warmth']['maximum_applied_Lab_ab_shift'][1],5)
        np.testing.assert_array_equal(output[mask==0],self.rgb[mask==0])
        self.assertFalse(report['geometry_changed'])
        self.assertTrue(np.isfinite(output).all())

    def test_selected_spot_and_unselected_texture(self):
        photo=self.rgb.copy();photo[173:177,153:157]-=.1
        output,mask,report=polish_skin(photo,self.points,photo,self.points,self.hair,'spots')
        self.assertGreater(report['spots']['selected_core_pixels'],0)
        self.assertGreater(report['spots']['response_reduction'],.2)
        np.testing.assert_array_equal(output[mask==0],photo[mask==0])
        self.assertTrue(report['spots']['stubble_lower_face_excluded'])

    def test_invalid_mode_or_geometry(self):
        with self.assertRaises(ValueError): polish_skin(self.rgb,self.points,self.rgb,self.points,self.hair,'bad')
        with self.assertRaises(ValueError): skin_regions(self.rgb,self.points[:10])

    def test_refined_warmth_keeps_same_shift_and_exact_eye_pixels(self):
        from flux2_klein9b_attractiveness import _EYE_CONTOURS
        source=self.rgb.copy();source[:,:,0]+=.1;source[:,:,2]-=.1
        _,_,old=polish_skin(self.rgb,self.points,source,self.points,self.hair,'warmth')
        output,mask,new=polish_skin(self.rgb,self.points,source,self.points,self.hair,
            'warmth',warmth_mask='separate_feather')
        self.assertEqual(old['warmth']['maximum_applied_Lab_ab_shift'],new['warmth']['maximum_applied_Lab_ab_shift'])
        guard=np.zeros(self.rgb.shape[:2],np.uint8)
        for ids in _EYE_CONTOURS:
            cv2.fillPoly(guard,[np.rint(self.points[list(ids)]).astype(np.int32)],255)
        guard=cv2.dilate(guard,np.ones((3,3),np.uint8))
        np.testing.assert_array_equal(output[guard>0],self.rgb[guard>0])
        np.testing.assert_array_equal(output[mask==0],self.rgb[mask==0])

    def test_chromatic_filter_rejects_neutral_dots_but_selects_colored_dot(self):
        lab=cv2.cvtColor(self.rgb,cv2.COLOR_RGB2LAB)
        lab[173:177,153:157,0]-=10
        neutral=cv2.cvtColor(lab,cv2.COLOR_LAB2RGB)
        _,_,dark=polish_skin(neutral,self.points,neutral,self.points,self.hair,'spots')
        _,_,filtered=polish_skin(neutral,self.points,neutral,self.points,self.hair,
            'spots',spot_kind='chromatic_compact')
        self.assertGreater(dark['spots']['components'],filtered['spots']['components'])
        lab[173:177,153:157,1:]+=5
        colored=cv2.cvtColor(lab,cv2.COLOR_LAB2RGB)
        output,mask,selected=polish_skin(colored,self.points,colored,self.points,self.hair,
            'spots',spot_kind='chromatic_compact')
        self.assertGreater(selected['spots']['components'],0)
        self.assertGreater(selected['spots']['response_reduction'],.2)
        np.testing.assert_array_equal(output[mask==0],colored[mask==0])


if __name__=='__main__': unittest.main()

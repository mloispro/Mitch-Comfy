import math
import json
import unittest

from upgrade_face_contour_diagnostic import FACE_OVAL, projected_contour, relative_width_change


class ContourDiagnosticTests(unittest.TestCase):
    def points(self):
        points=[[0.,0.] for _ in range(478)]
        for i,index in enumerate(FACE_OVAL):
            angle=-math.pi/2+i*2*math.pi/len(FACE_OVAL)
            points[index]=[1.2*math.cos(angle),1.+2.*math.sin(angle)]
        points[33]=[-.5,0.]
        points[263]=[.5,0.]
        return points

    def test_same_outline_has_zero_change(self):
        result=projected_contour(self.points())
        self.assertEqual(relative_width_change(result,result),{'0.30':0.,'0.50':0.,'0.70':0.})

    def test_translation_scale_and_roll_do_not_change_ratios(self):
        points=self.points();angle=.4
        transformed=[[3*(x*math.cos(angle)-y*math.sin(angle))+9,
                      3*(x*math.sin(angle)+y*math.cos(angle))-7] for x,y in points]
        for change in relative_width_change(projected_contour(points),projected_contour(transformed)).values():
            self.assertAlmostEqual(change,0.,places=10)

    def test_widened_outline_is_detected(self):
        points=self.points();wider=[p[:] for p in points]
        for i in FACE_OVAL:
            wider[i][0]*=1.1
        for change in relative_width_change(projected_contour(points),projected_contour(wider)).values():
            self.assertAlmostEqual(change,10.,places=10)

    def test_invalid_or_degenerate_input_is_rejected(self):
        for points in ([],[[0.,0.]]*478,[[float('nan'),0.]]*478):
            with self.assertRaises(ValueError):
                projected_contour(points)

    def test_numpy_landmarks_produce_serializable_plain_numbers(self):
        import numpy as np
        result=projected_contour(np.asarray(self.points(),dtype=np.float32))
        self.assertEqual(json.loads(json.dumps(result)),result)


if __name__=='__main__':
    unittest.main()

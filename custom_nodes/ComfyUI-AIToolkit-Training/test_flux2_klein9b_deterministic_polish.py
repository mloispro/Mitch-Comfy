import unittest
from unittest.mock import patch

import cv2
import numpy as np
import torch

from flux2_klein9b_deterministic_polish import (
    _attenuate_freckles, _naturalize_hair, build_semantic_hair_mask,
    HAIR_PARSER_HAIR_CLASS, POLISH_PROFILE,
)


class DeterministicPolishTests(unittest.TestCase):
    def test_real_mask_entrypoint_selects_parsenet_hair_not_neck(self):
        # Exercise the production crop/normalization/argmax/resize/closing path,
        # not just an injected synthetic final mask in _naturalize_hair.
        labels=torch.zeros((512,512),dtype=torch.int64)
        labels[25:150,100:400]=13
        labels[300:490,50:470]=17
        logits=torch.nn.functional.one_hot(labels,num_classes=19).permute(2,0,1).unsqueeze(0).float()
        seen=[]
        def parser(tensor):
            seen.append(tensor)
            return (logits,)
        with patch('flux2_klein9b_deterministic_polish._hair_parser',return_value=parser):
            mask=build_semantic_hair_mask(np.zeros((512,512,3),np.uint8),[100,81,400,512])
        self.assertEqual(tuple(seen[0].shape),(1,3,512,512))
        self.assertTrue(torch.all(seen[0]==-1))
        self.assertTrue(np.all(mask[25:150,100:400]==255))
        self.assertFalse(np.any(mask[300:490,50:470]))
        self.assertEqual(HAIR_PARSER_HAIR_CLASS,13)
        self.assertEqual(POLISH_PROFILE,'deterministic_face_and_hair_local_v5')
        labels[25:150,100:400]=0
        neck_only=torch.nn.functional.one_hot(labels,num_classes=19).permute(2,0,1).unsqueeze(0).float()
        with patch('flux2_klein9b_deterministic_polish._hair_parser',return_value=lambda _: (neck_only,)):
            with self.assertRaisesRegex(RuntimeError,'did not detect a hair region'):
                build_semantic_hair_mask(np.zeros((512,512,3),np.uint8),[100,81,400,512])

    def test_dark_dot_removal_is_local_and_preserves_unselected_texture(self):
        height = width = 128
        rgb = np.full((height, width, 3), (0.72, 0.52, 0.42), dtype=np.float32)
        yy, xx = np.mgrid[0:height, 0:width]
        rgb += (((xx + yy) % 5) - 2)[..., None].astype(np.float32) / 1024.0
        for center in ((47, 66), (81, 66), (65, 70)):
            cv2.circle(rgb, center, 2, (0.42, 0.29, 0.22), thickness=-1)

        bbox = np.array([20.0, 15.0, 108.0, 120.0], dtype=np.float32)
        keypoints = np.array(
            [[47.0, 45.0], [81.0, 45.0], [65.0, 65.0], [51.0, 91.0], [79.0, 91.0]],
            dtype=np.float32,
        )
        output, alpha, report = _attenuate_freckles(rgb, bbox, keypoints)

        self.assertGreaterEqual(report["detected_spot_components"], 3)
        self.assertGreater(report["response_reduction_fraction"], 0.5)
        self.assertEqual(report["replacement"], "local_7x7_median")
        self.assertGreater(float(output[66, 47].mean()), float(rgb[66, 47].mean()))
        untouched = alpha == 0.0
        np.testing.assert_array_equal(output[untouched], rgb[untouched])
        np.testing.assert_array_equal(output[105:120, 50:80], rgb[105:120, 50:80])

    def test_hair_highlights_follow_existing_light_and_protect_boundary(self):
        height = width = 128
        horizontal = np.linspace(0.16, 0.34, width, dtype=np.float32)
        rgb = np.repeat(horizontal[None, :, None], height, axis=0)
        rgb = np.repeat(rgb, 3, axis=2)
        hair = np.zeros((height, width), dtype=np.uint8)
        hair[14:114, 14:114] = 255

        output, alpha, report = _naturalize_hair(rgb, hair)

        self.assertTrue(report["highlights_follow_existing_hair_luminance"])
        self.assertEqual(report["parser_hair_class"],13)
        self.assertIn('neck class 17 excluded',report['parser'])
        self.assertEqual(report["hairline_and_silhouette_protected_pixels"], 8)
        self.assertGreater(report["highlight_mean_weight_in_active_hair"], 0.0)
        self.assertEqual(float(alpha[18, 64]), 0.0)
        self.assertGreater(float(alpha[64, 96]), 0.5)
        np.testing.assert_array_equal(output[alpha == 0.0], rgb[alpha == 0.0])
        self.assertGreater(float(output[64, 96].mean()), float(rgb[64, 96].mean()))


if __name__ == "__main__":
    unittest.main()

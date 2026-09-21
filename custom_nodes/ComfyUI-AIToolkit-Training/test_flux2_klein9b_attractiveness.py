import ast
import hashlib
import unittest
from pathlib import Path

import cv2
import numpy as np

from flux2_klein9b_attractiveness import (
    ATTRACTIVENESS_LEVELS, _BROWS, _EYE_CONTOURS, _EYES, _IRISES, _LIPS, _OVAL,
    _apply_high_with_landmarks, normalize_attractiveness,
)


class AttractivenessTests(unittest.TestCase):
    def test_legacy_booleans_and_strings_are_unambiguous(self):
        for value, expected in [(True, "low"), (False, "off"), ("off", "off"),
                                (" LOW ", "low"), ("high", "high")]:
            self.assertEqual(normalize_attractiveness(value), expected)
        for bad in [None, 0, 1, "true", "medium", [], {}]:
            with self.assertRaises(ValueError):
                normalize_attractiveness(bad)

    def test_low_implementation_matches_verified_v5_hair_label_repair(self):
        path = Path(__file__).with_name("flux2_klein9b_deterministic_polish.py")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                         "3F37FD5632D4AE1236314DF795AADDBF73FA55EF74CAE2BAB62C7359A5778676")

    def test_public_input_and_legacy_api_validation(self):
        path = Path(__file__).with_name("flux2_klein9b_photo_realism_upgrade.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ("INPUT_TYPES", "VALIDATE_INPUTS")]
        namespace = {"ATTRACTIVENESS_LEVELS": ATTRACTIVENESS_LEVELS, "APPEARANCE_DEFAULT": "low",
                     "DEFAULT_DETAIL_INSTRUCTIONS": "test", "PHONE_STYLE_LABEL_ON": "on",
                     "PHONE_STYLE_LABEL_OFF": "off", "normalize_attractiveness": normalize_attractiveness,
                     "compose_upgrade_prompt": lambda detail: detail}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), "exec"), namespace)
        node = namespace[cls.name]
        inputs = node.INPUT_TYPES()["required"]
        self.assertEqual(inputs["appearance_polish"], (list(ATTRACTIVENESS_LEVELS), inputs["appearance_polish"][1]))
        self.assertEqual(inputs["appearance_polish"][1]["default"], "low")
        self.assertIs(inputs["phone_camera_style"][1]["default"], True)
        for value in (True, False, "off", "low", "high"):
            self.assertIs(node.VALIDATE_INPUTS(None, "test", value, True, 1), True)
        self.assertIsInstance(node.VALIDATE_INPUTS(None, "test", "bad", True, 1), str)
        source = path.read_text(encoding="utf-8")
        self.assertLess(source.index("photo, gaze_mask, gaze_report = apply_source_gaze_lock"),
                        source.index("photo, high_mask, high_report = apply_high_attractiveness"))
        self.assertIn('appearance_polish = appearance_level != "off"', source)

    def test_high_preserves_protected_pixels_and_is_finite(self):
        points = np.full((478, 2), (64, 64), np.float32)
        for i, index in enumerate(_OVAL):
            angle = -np.pi / 2 + i * 2 * np.pi / len(_OVAL)
            points[index] = (64 + 49 * np.cos(angle), 65 + 57 * np.sin(angle))
        for ids, iris_ids, x in zip(_EYE_CONTOURS, _IRISES, (43, 85)):
            points[list(ids)] = [(x-13,54),(x-10,51),(x-7,49),(x-3,48),(x,48),
                                 (x+3,48),(x+7,49),(x+10,51),(x+13,54),
                                 (x+10,57),(x+7,59),(x+3,60),(x,60),
                                 (x-3,60),(x-7,59),(x-10,57)]
            points[list(iris_ids)] = [(x,54),(x,50),(x+4,54),(x,58),(x-4,54)]
        for ids, x in zip(_BROWS, (43, 85)):
            points[list(ids)] = [(x-15,43),(x-8,39),(x,38),(x+8,39),(x+15,43),
                                 (x+13,47),(x+6,44),(x,43),(x-6,44),(x-13,47)]
        for i, index in enumerate(_LIPS):
            a = i * 2 * np.pi / len(_LIPS)
            points[index] = (64 + 15*np.cos(a), 91 + 5*np.sin(a))
        rgb = np.full((128,128,3), (0.65,0.48,0.39), np.float32)
        for y in (26, 32, 38):
            rgb[y:y+1, 43:87] *= 0.8
        for x in (43,85):
            for offset in (-8,-4,0,4,8):
                cv2.line(rgb, (x+offset,41), (x+offset+1,44), (0.24,0.19,0.17), 1)
        hair = np.zeros((128,128), np.uint8)
        hair[:12] = 255
        source_points = points.copy()
        for ids in _EYE_CONTOURS:
            source_points[list(ids[1:8]), 1] += 2
        output, mask, report = _apply_high_with_landmarks(
            rgb, points, hair, source_points)
        self.assertTrue(np.isfinite(output).all())
        self.assertGreater(float(np.max(np.abs(output-rgb))), 0)
        np.testing.assert_array_equal(output[mask == 0], rgb[mask == 0])
        np.testing.assert_array_equal(output[:12], rgb[:12])
        self.assertTrue(report["pupil_core_lip_pixels_exact"])
        self.assertTrue(report["geometric_warp"])
        self.assertEqual(report["protected_pixel_max_error_0_to_255"], 0)
        self.assertGreater(report["mean_brow_darkening_0_to_255"], 0)
        self.assertGreater(report["mean_upper_lid_darkening_0_to_255"], 0)
        self.assertEqual(len(report["source_guided_upper_lid"]), 2)


if __name__ == "__main__":
    unittest.main()

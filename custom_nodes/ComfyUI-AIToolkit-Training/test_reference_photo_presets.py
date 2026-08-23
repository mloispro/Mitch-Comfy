import unittest

from reference_photo_presets import (
    FRAMINGS,
    MOMENTS,
    NO_REFERENCE,
    PHOTO_STYLES,
    compose_scene_prompt,
    duplicate_reference_names,
    selected_reference_names,
)


class ReferencePhotoPresetTests(unittest.TestCase):
    def test_compacts_one_to_four_references(self):
        self.assertEqual(
            selected_reference_names("front.jpg", NO_REFERENCE, "profile.jpg", NO_REFERENCE),
            ["front.jpg", "profile.jpg"],
        )

    def test_duplicate_reference_detection_is_case_insensitive(self):
        self.assertEqual(
            duplicate_reference_names(["Front.JPG", "front.jpg", "side.jpg"]),
            ["front.jpg"],
        )

    def test_prompt_decides_does_not_add_preset_language(self):
        result = compose_scene_prompt(
            "At a cafe.", "Prompt decides", "Prompt decides", "Prompt decides"
        )
        self.assertTrue(result.startswith("At a cafe."))
        self.assertNotIn("smartphone photograph", result)
        self.assertIn("one continuous in-camera subject", result)

    def test_realism_rendering_applies_to_phone_and_professional_presets(self):
        for style in ("Smartphone — natural", "Professional — natural"):
            result = compose_scene_prompt(
                "Beside a window.", style, "Waist-up", "Looking at camera"
            )
            self.assertIn("spatially nonuniform", result)
            self.assertIn("three-dimensional lighting", result)
            self.assertIn("without deepening wrinkles", result)
            self.assertIn("sensor grain", result)

    def test_realism_rendering_requests_specific_subtle_skin_variation(self):
        result = compose_scene_prompt(
            "Beside a window.", "Smartphone — natural", "Waist-up", "Looking at camera"
        )
        for detail in (
            "subtle natural redness",
            "faint under-eye color",
            "mild irregular pigmentation",
            "sparse stubble and vellus hair",
            "low-contrast pores",
            "tiny ordinary marks",
        ):
            self.assertIn(detail, result)

    def test_phone_action_full_body_preset_is_explicit(self):
        result = compose_scene_prompt(
            "Walking beside a lake.", "Smartphone — natural", "Full body", "Action"
        )
        self.assertIn("smartphone photograph", result)
        self.assertIn("head to feet", result)
        self.assertIn("body mechanics", result)

    def test_waist_up_preset_excludes_full_body_drift(self):
        result = compose_scene_prompt(
            "Walking on a city sidewalk.",
            "Smartphone — natural",
            "Waist-up",
            "Looking at camera",
        )
        self.assertIn("subject filling most of the frame", result)
        self.assertIn("do not show knees, lower legs, or feet", result)

    def test_professional_preset_keeps_natural_skin(self):
        result = compose_scene_prompt(
            "Beside a window.", "Professional — natural", "Waist-up", "Looking at camera"
        )
        self.assertIn("restrained retouching", result)
        self.assertIn("realistic skin texture", result)

    def test_candid_preset_explicitly_removes_eye_contact(self):
        result = compose_scene_prompt(
            "At a cafe.", "Smartphone — natural", "Waist-up", "Candid / looking away"
        )
        self.assertIn("three-quarter profile", result)
        self.assertIn("at least thirty degrees", result)
        self.assertIn("absolutely no eye contact", result)

    def test_empty_scene_is_rejected(self):
        with self.assertRaises(ValueError):
            compose_scene_prompt("  ", next(iter(PHOTO_STYLES)), next(iter(FRAMINGS)), next(iter(MOMENTS)))

if __name__ == "__main__":
    unittest.main()

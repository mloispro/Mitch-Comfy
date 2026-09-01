import unittest

from flux2_klein9b_mitch_identity_studio_presets import (
    FULL_BODY_PROFILE,
    GROUP_PROFILE,
    REFERENCE_PROFILES,
    SOLO_LEFT_PROFILE,
    SOLO_RIGHT_PROFILE,
    compose_effective_prompt,
)


class Klein9BIdentityStudioPresetTests(unittest.TestCase):
    def test_group_profile_uses_one_reference_and_protects_bystanders(self):
        self.assertEqual(REFERENCE_PROFILES[GROUP_PROFILE], ("front",))
        prompt = compose_effective_prompt(GROUP_PROFILE, "Mitch sits with three friends.")
        self.assertIn("one named central or foreground man", prompt)
        self.assertIn("Every other adult is an unrelated individual", prompt)
        self.assertIn("final photograph contains one Mitch", prompt)
        self.assertNotIn("Never", prompt)
        self.assertNotIn("No face swap", prompt)

    def test_solo_angle_profiles_use_two_semantically_ordered_references(self):
        self.assertEqual(REFERENCE_PROFILES[SOLO_LEFT_PROFILE], ("front", "left"))
        self.assertEqual(REFERENCE_PROFILES[SOLO_RIGHT_PROFILE], ("front", "right"))
        prompt = compose_effective_prompt(SOLO_LEFT_PROFILE, "A rooftop portrait.")
        self.assertIn("Picture 1 neutral frontal", prompt)
        self.assertIn("Picture 2 face turned toward image-left", prompt)
        self.assertIn("Render one Mitch", prompt)
        self.assertIn("His neck is bare", prompt)

    def test_full_body_profile_uses_body_proportion_reference(self):
        self.assertEqual(REFERENCE_PROFILES[FULL_BODY_PROFILE], ("front", "body"))
        prompt = compose_effective_prompt(FULL_BODY_PROFILE, "A full-body golfer.")
        self.assertIn("Picture 2 lean full-body proportions only", prompt)

    def test_empty_prompt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Describe the new photograph"):
            compose_effective_prompt(GROUP_PROFILE, "   ")


if __name__ == "__main__":
    unittest.main()

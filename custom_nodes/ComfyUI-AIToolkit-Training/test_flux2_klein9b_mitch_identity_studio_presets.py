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

    def test_appearance_polish_is_enabled_by_default_and_identity_safe(self):
        prompt = compose_effective_prompt(GROUP_PROFILE, "A natural outdoor portrait.")
        self.assertIn("clearly visible, natural-looking, more handsome best-day enhancement", prompt)
        self.assertIn("about three to five years younger", prompt)
        self.assertIn("slightly stronger natural jaw and chin", prompt)
        self.assertIn("reduce fine forehead lines, crow's-feet, and under-eye creasing by about half", prompt)
        self.assertIn("noticeable light bronze sun tan", prompt)
        self.assertIn("pores finer and less prominent while still visible", prompt)
        self.assertIn("stubble neatly trimmed, even, and flattering", prompt)
        self.assertIn("attractive, confident, approachable expression", prompt)
        self.assertIn("every tooth remains behind the lips", prompt)
        self.assertIn("natural eye size, iris color, spacing", prompt)
        self.assertLess(prompt.index("clearly visible"), prompt.index("A natural outdoor portrait."))

    def test_appearance_polish_off_omits_only_the_optional_clause(self):
        prompt = compose_effective_prompt(
            GROUP_PROFILE,
            "A natural outdoor portrait.",
            appearance_polish=False,
        )
        self.assertNotIn("more handsome best-day enhancement", prompt)
        self.assertNotIn("light bronze sun tan", prompt)
        self.assertNotIn("three to five years younger", prompt)
        self.assertNotIn("every tooth remains behind", prompt)
        self.assertIn("Match his identity, apparent age, face proportions", prompt)
        self.assertIn("natural skin texture, current apparent age", prompt)
        self.assertNotIn("  ", prompt)

    def test_empty_prompt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Describe the new photograph"):
            compose_effective_prompt(GROUP_PROFILE, "   ")


if __name__ == "__main__":
    unittest.main()

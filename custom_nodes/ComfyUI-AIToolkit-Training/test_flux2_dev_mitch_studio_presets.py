import unittest

from flux2_dev_mitch_studio_presets import (
    CUSTOM_PRESET,
    MODE_PROMPT_ONLY,
    MODE_SCENE_RESTAGE,
    compose_effective_prompt,
)


class Flux2DevMitchStudioPresetTests(unittest.TestCase):
    def test_prompt_only_uses_trigger_without_picture_contract(self):
        prompt = compose_effective_prompt(
            MODE_PROMPT_ONLY,
            "Cooking candid — warm modern kitchen",
            "",
            "Dating app — natural smartphone",
            "Waist-up",
            "Candid — looking away",
        )
        self.assertIn("m1tch_person", prompt)
        self.assertNotIn("Picture 1", prompt)
        self.assertIn("absolutely no eye contact", prompt)

    def test_scene_mode_assigns_composition_not_identity(self):
        prompt = compose_effective_prompt(
            MODE_SCENE_RESTAGE,
            "Night city balcony — black open-collar shirt",
            "",
            "Premium lifestyle — natural",
            "Three-quarter body",
            "Candid — looking away",
        )
        self.assertIn("Picture 1 is a scene and composition reference, not an identity reference", prompt)
        self.assertIn("Replace only its primary adult man with m1tch_person", prompt)
        self.assertIn("Do not copy the original man's face", prompt)
        self.assertIn("screenshot controls", prompt)

    def test_secondary_people_are_identity_isolated(self):
        prompt = compose_effective_prompt(
            MODE_PROMPT_ONLY,
            "Night out — seated with friends",
            "",
            "Dating app — natural smartphone",
            "Waist-up",
            "Action",
        )
        self.assertIn("distinct unrelated faces", prompt)
        self.assertIn("must not resemble m1tch_person", prompt)
        self.assertIn("Black man with a shaved head", prompt)
        self.assertIn("East Asian woman", prompt)
        self.assertIn("Latina woman", prompt)
        self.assertIn("facial geometry, hairlines, skin tones, and clothing differ clearly", prompt)

    def test_custom_preset_requires_text(self):
        with self.assertRaises(ValueError):
            compose_effective_prompt(
                MODE_PROMPT_ONLY,
                CUSTOM_PRESET,
                "",
                "Prompt decides",
                "Prompt decides",
                "Prompt decides",
            )


if __name__ == "__main__":
    unittest.main()

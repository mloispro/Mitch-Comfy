import unittest

from flux2_klein9b_scene_presets import (
    CUSTOM_GROUP_PRESET,
    CUSTOM_IDENTITY_PRESET,
    FULL_BODY_PROFILE,
    GROUP_PROFILE,
    GROUP_SCENE_PRESETS,
    IDENTITY_SCENE_PRESETS,
    PRESET_MANIFEST_PATH,
    PRESET_MANIFEST_SHA256,
    SOLO_LEFT_PROFILE,
    SOLO_RIGHT_PROFILE,
    resolve_group_scene,
    resolve_identity_profile,
    resolve_identity_scene,
)


class Klein9BScenePresetTests(unittest.TestCase):
    def test_manifest_is_the_complete_gallery_source(self):
        self.assertTrue(PRESET_MANIFEST_PATH.is_file())
        self.assertEqual(len(IDENTITY_SCENE_PRESETS), 15)
        self.assertEqual(len(GROUP_SCENE_PRESETS), 5)
        self.assertEqual(len(PRESET_MANIFEST_SHA256), 64)
        thumbnails = {
            record["thumbnail"]
            for record in [*IDENTITY_SCENE_PRESETS.values(), *GROUP_SCENE_PRESETS.values()]
        }
        self.assertEqual(len(thumbnails), 20)
        self.assertTrue(
            all((PRESET_MANIFEST_PATH.parent / thumbnail).is_file() for thumbnail in thumbnails)
        )

    def test_identity_gallery_has_requested_replacements_and_no_tabby(self):
        labels = list(IDENTITY_SCENE_PRESETS)
        self.assertIn("Canyon overlook — river at sunset", labels)
        self.assertIn("Dog lover — small Golden Shepherd puppy", labels)
        self.assertIn("Rooftop cocktail — city lights", labels)
        self.assertFalse(any("tabby" in label.lower() for label in labels))

    def test_identity_presets_have_prompt_thumbnail_and_valid_profile(self):
        valid_profiles = {
            GROUP_PROFILE,
            SOLO_LEFT_PROFILE,
            SOLO_RIGHT_PROFILE,
            FULL_BODY_PROFILE,
        }
        for label, record in IDENTITY_SCENE_PRESETS.items():
            self.assertTrue(record["thumbnail"])
            self.assertIn(record["profile"], valid_profiles)
            if label != CUSTOM_IDENTITY_PRESET:
                self.assertTrue(record["prompt"])

    def test_custom_identity_requires_text_and_preset_can_add_direction(self):
        with self.assertRaisesRegex(ValueError, "custom scene"):
            resolve_identity_scene(CUSTOM_IDENTITY_PRESET, "")
        prompt, record = resolve_identity_scene(
            "Rooftop cocktail — city lights", "Use rain-slick reflections."
        )
        self.assertIn("short clear tumbler", prompt)
        self.assertIn("Additional scene direction", prompt)
        self.assertEqual(record["profile"], SOLO_LEFT_PROFILE)

    def test_identity_preset_owns_its_profile_but_custom_keeps_the_request(self):
        self.assertEqual(
            resolve_identity_profile("Rooftop cocktail — city lights", FULL_BODY_PROFILE),
            SOLO_LEFT_PROFILE,
        )
        self.assertEqual(
            resolve_identity_profile(CUSTOM_IDENTITY_PRESET, FULL_BODY_PROFILE),
            FULL_BODY_PROFILE,
        )

    def test_group_gallery_sources_are_locked_and_custom_requires_text(self):
        self.assertIn("Amber booth — four friends", GROUP_SCENE_PRESETS)
        self.assertIn("Approved lounge — central Mitch", GROUP_SCENE_PRESETS)
        for label, record in GROUP_SCENE_PRESETS.items():
            self.assertTrue(record["thumbnail"])
            if label != CUSTOM_GROUP_PRESET:
                self.assertTrue(record["source_asset"])
                self.assertEqual(len(record["source_sha256"]), 64)
        with self.assertRaisesRegex(ValueError, "uploaded group"):
            resolve_group_scene(CUSTOM_GROUP_PRESET, "")


if __name__ == "__main__":
    unittest.main()

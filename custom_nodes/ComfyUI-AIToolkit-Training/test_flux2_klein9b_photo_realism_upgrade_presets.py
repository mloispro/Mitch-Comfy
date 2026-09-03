import unittest

from flux2_klein9b_photo_realism_upgrade_presets import (
    APPROVED_INCLUDED_EXAMPLE_PROMPT,
    DEFAULT_DETAIL_INSTRUCTIONS,
    compose_upgrade_prompt,
    compute_output_dimensions,
    face_interior_rectangle,
)


class UpgradePhotoPresetTests(unittest.TestCase):
    def test_approved_sizes_stay_native(self):
        self.assertEqual(compute_output_dimensions(1680, 1008), (1680, 1008))
        self.assertEqual(compute_output_dimensions(1024, 1024), (1024, 1024))

    def test_large_photo_is_capped_and_keeps_orientation(self):
        width, height = compute_output_dimensions(4032, 3024)
        self.assertLessEqual(width * height, 1_725_000)
        self.assertGreater(width, height)
        self.assertEqual(width % 16, 0)
        self.assertEqual(height % 16, 0)

    def test_approved_house_face_clear_matches_locked_guide(self):
        rectangle = face_interior_rectangle(
            (598.4, 184.1, 933.4, 636.7), 1680, 1008
        )
        self.assertEqual(rectangle, (630, 235, 900, 600))

    def test_prompt_locks_pose_and_four_reference_roles(self):
        prompt = compose_upgrade_prompt("Render natural siding and bark texture.")
        for phrase in (
            "Picture 1 is the exact edit target",
            "forehead height, hairline position",
            "head yaw, pitch and roll",
            "pupil position within each eyelid",
            "Picture 2 is a face-interior-free edge guide",
            "Picture 3 is a protected genuine photograph",
            "Picture 4 is a protected isolated crop",
            "Render natural siding and bark texture.",
            "not Portrait mode",
            "complete environment legible",
            "no dark band, duplicate edge, artificial shadow, halo, seam, or floating clump",
        ):
            self.assertIn(phrase, prompt)

    def test_included_example_uses_exact_approved_milestone_prompt(self):
        prompt = compose_upgrade_prompt(DEFAULT_DETAIL_INSTRUCTIONS)
        self.assertEqual(prompt, APPROVED_INCLUDED_EXAMPLE_PROMPT)
        self.assertIn("exact landscape edit target", prompt)
        self.assertIn("same three-quarter view", prompt)
        self.assertIn("materially detailed background", prompt)

    def test_generation_prompt_has_no_appearance_redesign(self):
        prompt = compose_upgrade_prompt("Render natural siding and bark texture.")
        for prohibited in (
            "younger",
            "stronger jaw",
            "higher cheekbones",
            "sun-kissed",
            "confident smile",
            "beauty-filter",
        ):
            self.assertNotIn(prohibited, prompt)

    def test_empty_detail_is_rejected(self):
        with self.assertRaises(ValueError):
            compose_upgrade_prompt("   ")


if __name__ == "__main__":
    unittest.main()

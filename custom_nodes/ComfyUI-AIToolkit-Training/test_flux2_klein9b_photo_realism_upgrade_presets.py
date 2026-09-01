import unittest

from flux2_klein9b_photo_realism_upgrade_presets import (
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
            "head yaw, pitch and roll",
            "Picture 2 is a face-interior-free edge guide",
            "Picture 3 is a protected genuine photograph",
            "Picture 4 is a protected isolated crop",
            "Render natural siding and bark texture.",
            "no dark band, duplicate edge, artificial shadow, halo, seam, or floating clump",
        ):
            self.assertIn(phrase, prompt)

    def test_empty_detail_is_rejected(self):
        with self.assertRaises(ValueError):
            compose_upgrade_prompt("   ")


if __name__ == "__main__":
    unittest.main()

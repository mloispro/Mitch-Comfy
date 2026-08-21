from __future__ import annotations

import unittest
from pathlib import Path

from social_photo_core import (
    build_prompt,
    identity_route,
    is_known_synthetic_identity_fixture,
    load_registry,
    resolve_count,
    resolve_resolution,
    resolve_scenes,
    sanitize_report,
    seed_for,
)


def settings(**overrides):
    value = {
        "mode": "Dating Pack",
        "brief": "Approachable and current.",
        "scene_preset": "Auto Mix",
        "camera_look": "Authentic Phone",
        "camera_relationship": "Auto Mix",
        "aspect": "Portrait 2:3",
        "count_override": 0,
        "seed": 100,
    }
    value.update(overrides)
    return value


class SocialPhotoCoreTests(unittest.TestCase):
    def test_known_generated_identity_fixtures_are_never_real_references(self):
        self.assertTrue(is_known_synthetic_identity_fixture("mitch-workbench-qwen-id-front.png"))
        self.assertTrue(is_known_synthetic_identity_fixture("folder/MITCH-WORKBENCH-QWEN-ID-RIGHT.PNG"))
        self.assertTrue(is_known_synthetic_identity_fixture("mitch-qwen-id-left.png"))
        self.assertFalse(is_known_synthetic_identity_fixture("20260818_173106.jpg"))

    def test_registry_and_pack_defaults(self):
        registry = load_registry()
        self.assertTrue(
            all(isinstance(scene["body_reference"], bool) for scene in registry["scenes"])
        )
        by_key = {scene["key"]: scene for scene in registry["scenes"]}
        self.assertTrue(by_key["active-hobby"]["body_reference"])
        self.assertTrue(by_key["custom"]["body_reference"])
        self.assertIn("mid-thigh", by_key["active-hobby"]["prompt"])
        self.assertFalse(by_key["night-out"]["body_reference"])
        self.assertEqual(len(resolve_scenes(settings(), registry)), 6)
        self.assertEqual(
            len(resolve_scenes(settings(mode="Instagram Pack", aspect="Instagram 4:5"), registry)),
            9,
        )
        self.assertEqual(len(resolve_scenes(settings(mode="Single"), registry)), 1)

    def test_count_override_and_repeated_preset_are_deterministic(self):
        scenes = resolve_scenes(settings(scene_preset="Travel", count_override=3))
        self.assertEqual([scene["key"] for scene in scenes], ["travel-story"] * 3)
        self.assertEqual([scene["variation"] for scene in scenes], [0, 1, 2])
        self.assertEqual(resolve_count("Dating Pack", 4), 4)
        with self.assertRaisesRegex(ValueError, "between 1 and 9"):
            resolve_count("Dating Pack", 10)

    def test_resolution_and_seed_schedule(self):
        self.assertEqual(resolve_resolution("Portrait 2:3"), (1024, 1536))
        self.assertEqual(resolve_resolution("Portrait 2:3", fallback=True), (768, 1152))
        self.assertEqual([seed_for(100, index) for index in range(3)], [100, 1109, 2118])

    def test_identity_route_keeps_lora_as_last_resort(self):
        sufficient = identity_route([0.58, 0.62], 1)
        self.assertEqual(sufficient["status"], "similarity_target_met_unverified")
        self.assertTrue(sufficient["visual_approval_required"])
        self.assertIn("not proof", sufficient["score_scope"])
        near_target = identity_route([0.56, 0.59], 3)
        self.assertEqual(near_target["status"], "similarity_near_target_visual_review")
        add_angles = identity_route([0.41, 0.45], 1)
        self.assertEqual(add_angles["status"], "add_reference_angles")
        uneven = identity_route([0.72, 0.44], 2)
        self.assertEqual(uneven["status"], "add_reference_angles")
        last_resort = identity_route([0.42, 0.46], 3)
        self.assertEqual(last_resort["status"], "dedicated_identity_adapter_needed")
        self.assertIn("Do not reuse the rejected Klein LoRA", last_resort["recommendation"])

    def test_prompt_merges_identity_camera_scene_body_and_brief(self):
        scene = resolve_scenes(settings(mode="Single"))[0]
        prompt = build_prompt(scene, settings(mode="Single"), "not_supplied")
        for expected in (
            "same consenting adult",
            "apparent age and face proportions exactly",
            "smartphone main camera",
            "exact body shape is not established",
            "no visible brand logo",
            "Approachable and current",
            scene["prompt"],
        ):
            self.assertIn(expected, prompt)

    def test_prompt_numbers_multiple_face_and_body_references(self):
        scene = resolve_scenes(settings(mode="Single", scene_preset="Hobby/Active"))[0]
        prompt = build_prompt(
            scene,
            settings(mode="Single", face_reference_count=3, body_reference_picture=4),
            "reference_grounded",
        )
        self.assertIn("Pictures 1 through 3", prompt)
        self.assertIn("Picture 4 establishes only", prompt)
        self.assertIn("not a collage", prompt)

    def test_report_sanitizer_removes_sources_and_tensors(self):
        class TensorLike:
            shape = (1, 2, 3)
            dtype = "float32"

        sanitized = sanitize_report(
            {
                "references": [TensorLike()],
                "face_reference_items": [{"image": TensorLike()}],
                "body_reference_items": [{"image": TensorLike()}],
                "source_path": "private.jpg",
                "safe": {"hash": "abc", "path_value": Path("C:/private/file.jpg")},
            }
        )
        self.assertNotIn("references", sanitized)
        self.assertNotIn("face_reference_items", sanitized)
        self.assertNotIn("body_reference_items", sanitized)
        self.assertNotIn("source_path", sanitized)
        self.assertEqual(sanitized["safe"]["path_value"], "file.jpg")

if __name__ == "__main__":
    unittest.main()

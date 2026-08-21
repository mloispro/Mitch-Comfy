from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from social_photo_core import (
    build_prompt,
    identity_route,
    load_registry,
    resolve_count,
    resolve_resolution,
    resolve_scenes,
    sanitize_report,
    seed_for,
    validate_klein_4b_lora,
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
        "identity_finish": "Auto",
        "identity_lora": "None",
        "lora_strength": 0.0,
        "lora_trigger": "",
        "save_debug_intermediates": False,
    }
    value.update(overrides)
    return value


class SocialPhotoCoreTests(unittest.TestCase):
    def test_registry_and_pack_defaults(self):
        registry = load_registry()
        self.assertTrue(
            all(isinstance(scene["body_reference"], bool) for scene in registry["scenes"])
        )
        by_key = {scene["key"]: scene for scene in registry["scenes"]}
        self.assertTrue(by_key["active-hobby"]["body_reference"])
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
        sufficient = identity_route([0.58, 0.62], 1, "Auto", "None")
        self.assertEqual(sufficient["status"], "reference_only_sufficient")
        add_angles = identity_route([0.41, 0.45], 1, "Auto", "None")
        self.assertEqual(add_angles["status"], "add_reference_angles")
        uneven = identity_route([0.72, 0.44], 2, "Auto", "None")
        self.assertEqual(uneven["status"], "add_reference_angles")
        last_resort = identity_route([0.42, 0.46], 3, "Auto", "None")
        self.assertEqual(last_resort["status"], "consider_klein_lora")

    def test_prompt_merges_identity_camera_scene_body_and_brief(self):
        scene = resolve_scenes(settings(mode="Single"))[0]
        prompt = build_prompt(scene, settings(mode="Single"), "not_supplied")
        for expected in (
            "same consenting adult",
            "smartphone main camera",
            "exact body shape is not established",
            "no visible brand logo",
            "Approachable and current",
            scene["prompt"],
        ):
            self.assertIn(expected, prompt)

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

    def test_klein_lora_validation_accepts_expected_architecture(self):
        header = {"__metadata__": {"format": "pt"}}
        for index in range(20):
            header[f"transformer.single_transformer_blocks.{index}.attn.to_out.lora_A.weight"] = {
                "dtype": "F16",
                "shape": [16, 3072],
                "data_offsets": [0, 0],
            }
        for index in range(5):
            header[f"transformer.transformer_blocks.{index}.attn.to_out.lora_B.weight"] = {
                "dtype": "F16",
                "shape": [3072, 16],
                "data_offsets": [0, 0],
            }
        encoded = json.dumps(header).encode("utf-8")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "valid.safetensors"
            path.write_bytes(struct.pack("<Q", len(encoded)) + encoded)
            report = validate_klein_4b_lora(path)
        self.assertEqual(report["hidden_size"], 3072)
        self.assertEqual(report["single_blocks"], 20)

    def test_klein_lora_validation_rejects_other_architecture(self):
        header = {
            "other.lora_A.weight": {"dtype": "F16", "shape": [8, 1024], "data_offsets": [0, 0]}
        }
        encoded = json.dumps(header).encode("utf-8")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.safetensors"
            path.write_bytes(struct.pack("<Q", len(encoded)) + encoded)
            with self.assertRaisesRegex(ValueError, "not compatible"):
                validate_klein_4b_lora(path)


if __name__ == "__main__":
    unittest.main()

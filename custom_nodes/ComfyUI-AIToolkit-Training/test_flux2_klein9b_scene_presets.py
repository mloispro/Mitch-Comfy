import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from flux2_klein9b_scene_presets import (
    CUSTOM_GROUP_PRESET,
    CUSTOM_IDENTITY_PRESET,
    FULL_BODY_PROFILE,
    GROUP_PROFILE,
    GROUP_SCENE_PRESETS,
    IDENTITY_SCENE_PRESETS,
    PRESET_MANIFEST,
    PRESET_MANIFEST_PATH,
    PRESET_MANIFEST_SHA256,
    SOLO_LEFT_PROFILE,
    SOLO_RIGHT_PROFILE,
    _load_manifest,
    _validate_manifest,
    resolve_group_scene,
    resolve_group_geometry,
    resolve_identity_profile,
    resolve_identity_scene,
)


class Klein9BScenePresetTests(unittest.TestCase):
    def test_production_manifest_assets_exist(self):
        self.assertIs(
            _validate_manifest(PRESET_MANIFEST, require_files=True),
            PRESET_MANIFEST,
        )

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

    def test_group_geometry_resolves_the_same_values_for_validation_and_execution(self):
        self.assertEqual(
            resolve_group_geometry("Approved lounge — central Mitch", 0.1, 0.2, 0.8),
            (0.5, 0.44, 0.92),
        )
        self.assertEqual(
            resolve_group_geometry(CUSTOM_GROUP_PRESET, 0.33, 0.66, 0.84),
            (0.33, 0.66, 0.84),
        )
        with self.assertRaisesRegex(ValueError, "target_x"):
            resolve_group_geometry(CUSTOM_GROUP_PRESET, 1.01, 0.5, 0.92)

    def test_manifest_rejects_unsafe_paths_hashes_and_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "web" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            project_root = root / "project"
            source = project_root / "assets" / "group.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"group source")
            for thumbnail in ("identity.jpg", "group-custom.jpg", "group.jpg"):
                (manifest_path.parent / thumbnail).write_bytes(b"thumbnail")
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

            def manifest() -> dict:
                return {
                    "schema_version": 1,
                    "reference_profiles": {
                        "group": GROUP_PROFILE,
                        "solo_left": SOLO_LEFT_PROFILE,
                        "solo_right": SOLO_RIGHT_PROFILE,
                        "full_body": FULL_BODY_PROFILE,
                    },
                    "identity": [
                        {
                            "key": "custom",
                            "label": "Custom",
                            "profile": SOLO_RIGHT_PROFILE,
                            "thumbnail": "identity.jpg",
                            "prompt": "",
                        }
                    ],
                    "group": [
                        {
                            "key": "custom-group",
                            "label": "Custom group",
                            "thumbnail": "group-custom.jpg",
                            "source_asset": None,
                            "source_sha256": None,
                            "target_x": 0.5,
                            "target_y": 0.44,
                            "head_scale": 0.92,
                            "prompt": "",
                        },
                        {
                            "key": "prepared",
                            "label": "Prepared",
                            "thumbnail": "group.jpg",
                            "source_asset": "assets/group.png",
                            "source_sha256": source_hash,
                            "target_x": 0.5,
                            "target_y": 0.44,
                            "head_scale": 0.92,
                            "prompt": "A complete group scene.",
                        },
                    ],
                }

            _validate_manifest(
                manifest(), manifest_path=manifest_path, project_root=project_root
            )
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            loaded, loaded_hash = _load_manifest(
                manifest_path=manifest_path, project_root=project_root
            )
            self.assertEqual(loaded["schema_version"], 1)
            self.assertEqual(
                loaded_hash,
                hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper(),
            )
            invalid_cases = (
                ("source_sha256", "not-a-hash", "64 hexadecimal"),
                ("source_asset", "../outside.png", "escapes"),
                ("target_x", "0.5", "finite number"),
                ("head_scale", 0.5, "between 0.75 and 1.0"),
            )
            for field, value, message in invalid_cases:
                with self.subTest(field=field, value=value):
                    candidate = manifest()
                    candidate["group"][1][field] = value
                    with self.assertRaisesRegex(RuntimeError, message):
                        _validate_manifest(
                            candidate,
                            manifest_path=manifest_path,
                            project_root=project_root,
                        )

            candidate = manifest()
            candidate["identity"][0]["thumbnail"] = "../outside.jpg"
            with self.assertRaisesRegex(RuntimeError, "escapes"):
                _validate_manifest(
                    candidate, manifest_path=manifest_path, project_root=project_root
                )

            candidate = manifest()
            candidate["identity"][0]["key"] = " custom "
            with self.assertRaisesRegex(RuntimeError, "surrounding whitespace"):
                _validate_manifest(
                    candidate, manifest_path=manifest_path, project_root=project_root
                )

            candidate = manifest()
            candidate["reference_profiles"]["group"] = "GROUP — wrong engine profile"
            with self.assertRaisesRegex(RuntimeError, "frozen Identity engine"):
                _validate_manifest(
                    candidate, manifest_path=manifest_path, project_root=project_root
                )

            candidate = manifest()
            candidate["group"][1]["source_asset"] = "assets/missing.png"
            _validate_manifest(
                candidate, manifest_path=manifest_path, project_root=project_root
            )
            with self.assertRaisesRegex(RuntimeError, "Missing Group preset"):
                _validate_manifest(
                    candidate,
                    manifest_path=manifest_path,
                    project_root=project_root,
                    require_files=True,
                )


if __name__ == "__main__":
    unittest.main()

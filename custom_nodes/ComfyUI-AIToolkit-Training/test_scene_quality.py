from __future__ import annotations

import unittest

from scene_quality import (
    apply_scene_guardrails,
    build_scene_contract,
    infer_scene_contexts,
    requires_complex_route,
)


class SceneQualityTests(unittest.TestCase):
    def test_context_detection_is_global_and_composable(self):
        contexts = infer_scene_contexts(
            "A candid selfie inside a car beside a busy city street with pedestrians",
            "Candid / looking away",
        )
        self.assertIn("car_interior", contexts)
        self.assertIn("traffic", contexts)
        self.assertIn("crowd", contexts)
        self.assertIn("background_people", contexts)
        self.assertNotIn("action", contexts)

        action = infer_scene_contexts("Playing golf while holding a club", "Action")
        self.assertIn("action", action)
        self.assertIn("held_object", action)

    def test_looking_at_camera_does_not_imply_held_camera(self):
        contexts = infer_scene_contexts(
            "Sitting in the driver seat of a parked car",
            "Looking at camera",
        )
        self.assertIn("car_interior", contexts)
        self.assertNotIn("held_object", contexts)

    def test_car_contract_targets_headrest_tangency(self):
        contract = build_scene_contract(
            "Sitting inside a car wearing a black shirt",
            "Smartphone — natural",
            "Waist-up",
            "Looking at camera",
        )
        guarded = apply_scene_guardrails("base prompt", contract)
        self.assertIn("no background edge emerges", guarded)
        self.assertIn("headrest", guarded)
        self.assertIn("offset", guarded)
        self.assertNotIn("crowd", contract["contexts"])
        self.assertEqual(contract["rules"][0], "universal")

    def test_detailed_background_is_required_for_every_scene(self):
        contract = build_scene_contract(
            "Natural portrait beside a lake",
            "Professional — natural",
            "Waist-up",
            "Looking at camera",
        )
        guarded = apply_scene_guardrails("base prompt", contract)
        self.assertEqual(contract["rules"][:2], ["universal", "background_detail"])
        self.assertIn("environment recognizable", guarded)
        self.assertIn("Focus must follow distance", guarded)
        self.assertIn("every depth plane equally sharp", guarded)
        self.assertIn("featureless color wash", guarded)
        self.assertIn("35–50mm", contract["camera_model"])
        self.assertIn("one physical exposure", contract["single_capture_rule"])
        self.assertIn("no halo", guarded)

    def test_architecture_behind_subject_does_not_imply_background_people(self):
        contract = build_scene_contract(
            "Behind him are old brick storefronts with planters and trees",
            "Professional — natural",
            "Waist-up",
            "Looking at camera",
        )
        self.assertNotIn("background_people", contract["contexts"])
        self.assertFalse(requires_complex_route(contract))

    def test_small_number_of_people_get_identity_isolation_and_complex_route(self):
        contract = build_scene_contract(
            "Two adults occupy separate tables behind him outside a cafe",
            "Smartphone — natural",
            "Waist-up",
            "Candid / looking away",
        )
        self.assertIn("background_people", contract["contexts"])
        self.assertTrue(requires_complex_route(contract))
        guarded = apply_scene_guardrails("base prompt", contract)
        self.assertIn("Only the main subject is m1tchperson", guarded)
        self.assertIn("continuous readable head-and-body silhouette", guarded)

    def test_cafe_location_alone_does_not_force_complex_route(self):
        quiet = build_scene_contract(
            "Sitting at a cafe table with two adults at separate tables",
            "Smartphone — natural",
            "Waist-up",
            "Candid / looking away",
        )
        self.assertNotIn("crowd", quiet["contexts"])
        self.assertTrue(requires_complex_route(quiet))

        busy = build_scene_contract(
            "Sitting at a busy cafe with patrons behind him",
            "Smartphone — natural",
            "Waist-up",
            "Candid / looking away",
        )
        self.assertIn("crowd", busy["contexts"])
        self.assertIn("background_people", busy["contexts"])
        self.assertTrue(requires_complex_route(busy))

    def test_crowd_contract_prevents_coordinated_color_and_duplicates(self):
        contract = build_scene_contract(
            "Walking on a busy city street with pedestrians behind me",
            "Smartphone — natural",
            "Full body",
            "Action",
        )
        guarded = apply_scene_guardrails("base prompt", contract)
        self.assertIn("distinct individual", guarded)
        self.assertIn("mustard", guarded)
        self.assertIn("front-facing row", guarded)
        self.assertIn("aligned with", guarded)
        self.assertIn("one leg leads", guarded)
        self.assertTrue(requires_complex_route(contract))

    def test_group_reflection_and_signage_rules_compose(self):
        contract = build_scene_contract(
            "Group of friends at a lively bar reflected in a mirror beside a menu sign",
            "Professional — natural",
            "Waist-up",
            "Candid / looking away",
        )
        self.assertEqual(
            contract["contexts"],
            ["crowd", "group_photo", "reflection", "text_signage"],
        )
        guarded = apply_scene_guardrails("base prompt", contract)
        self.assertIn("extra person", guarded)
        self.assertIn("legible", guarded)
        self.assertTrue(requires_complex_route(contract))

    def test_simple_portraits_and_car_interiors_stay_on_fast_route(self):
        portrait = build_scene_contract(
            "Natural portrait beside a lake",
            "Smartphone — natural",
            "Waist-up",
            "Looking at camera",
        )
        car = build_scene_contract(
            "Sitting in the driver seat of a parked car",
            "Smartphone — natural",
            "Waist-up",
            "Looking at camera",
        )
        self.assertFalse(requires_complex_route(portrait))
        self.assertFalse(requires_complex_route(car))


if __name__ == "__main__":
    unittest.main()

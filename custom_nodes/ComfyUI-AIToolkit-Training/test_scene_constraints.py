from __future__ import annotations

import unittest

from scene_constraints import (
    build_hard_scene_constraints,
    build_scene_topology,
    scene_object_targets,
)


class SceneConstraintTests(unittest.TestCase):
    def test_secondary_people_and_vehicle_counts_are_totalized(self):
        contract = {
            "user_scene": "Two adults sit behind him and two clearly separated parked cars line the curb.",
            "contexts": ["background_people", "traffic"],
        }
        result = build_hard_scene_constraints(contract)
        self.assertIn("exactly 3 visible humans total", result)
        self.assertIn("exactly 2 complete passenger cars", result)
        self.assertIn("uninterrupted bare asphalt", result)
        self.assertIn("different body style", result)
        self.assertIn("one car a small dark-red hatchback", result)
        self.assertIn("one secondary adult an older woman", result)
        self.assertIn("No lookalikes", result)
        self.assertIn("not a selfie", result)
        self.assertEqual(scene_object_targets(contract), {"person": 3, "vehicle": 2})
        topology = build_scene_topology(contract)
        self.assertIn("across the sidewalk", topology)
        self.assertIn("narrow side-on strip of road", topology)
        self.assertIn("same side of the frame", topology)
        self.assertIn("side-on, parallel", topology)

    def test_group_count_includes_main_subject(self):
        result = build_hard_scene_constraints(
            {"user_scene": "A group of four friends", "contexts": ["group_photo"]}
        )
        self.assertIn("exactly 4 visible humans total", result)

    def test_subject_shirt_color_does_not_suppress_vehicle_cast(self):
        result = build_hard_scene_constraints(
            {
                "user_scene": "A man in a black shirt near two parked cars",
                "contexts": ["background_people", "traffic"],
            }
        )
        self.assertIn("one car a small dark-red hatchback", result)

    def test_explicit_vehicle_appearance_is_respected(self):
        result = build_hard_scene_constraints(
            {
                "user_scene": "Two parked blue cars behind the subject",
                "contexts": ["background_people", "traffic"],
            }
        )
        self.assertNotIn("dark-red hatchback", result)

    def test_explicit_selfie_does_not_add_photographer_rule(self):
        result = build_hard_scene_constraints(
            {"user_scene": "A selfie with two friends", "contexts": ["group_photo"]}
        )
        self.assertNotIn("CAMERA OWNERSHIP", result)


if __name__ == "__main__":
    unittest.main()

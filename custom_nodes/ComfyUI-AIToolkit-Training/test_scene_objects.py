from __future__ import annotations

import unittest

from scene_objects import guarded_multi_person_count_error, object_count_error


class SceneObjectTests(unittest.TestCase):
    def test_exact_counts_have_zero_error(self):
        self.assertEqual(
            object_count_error({"person": 3, "vehicle": 2}, {"person": 3, "vehicle": 2}),
            0,
        )

    def test_missing_and_extra_objects_both_count(self):
        self.assertEqual(
            object_count_error({"person": 5, "vehicle": 1}, {"person": 3, "vehicle": 2}),
            3,
        )

    def test_implied_group_requires_at_least_two_people(self):
        self.assertEqual(
            guarded_multi_person_count_error(
                {"person": 1}, {}, requires_multiple_people=True
            ),
            1,
        )
        self.assertEqual(
            guarded_multi_person_count_error(
                {"person": 2}, {}, requires_multiple_people=True
            ),
            0,
        )

    def test_explicit_person_target_remains_exact(self):
        self.assertEqual(
            guarded_multi_person_count_error(
                {"person": 4}, {"person": 3}, requires_multiple_people=True
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()

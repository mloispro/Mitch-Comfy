from __future__ import annotations

import unittest

from scene_objects import object_count_error


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


if __name__ == "__main__":
    unittest.main()

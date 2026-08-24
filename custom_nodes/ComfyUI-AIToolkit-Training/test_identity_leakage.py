from __future__ import annotations

import unittest

import numpy as np

from identity_leakage import evaluate_identity_scope


class IdentityLeakageTests(unittest.TestCase):
    def setUp(self):
        self.identity = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.boxes = [(0, 0, 100, 100), (120, 0, 190, 70), (210, 0, 280, 70)]
        self.confidences = [0.9, 0.8, 0.7]

    def test_distinct_secondary_faces_pass(self):
        report = evaluate_identity_scope(
            [
                np.array([0.95, 0.20, 0.05]),
                np.array([0.20, 0.95, 0.10]),
                np.array([0.15, -0.25, 0.95]),
            ],
            self.boxes,
            self.confidences,
            self.identity,
            0.75,
        )
        self.assertEqual(report.status, "passed")
        self.assertEqual(report.main_face_index, 0)
        self.assertEqual(report.failures, [])

    def test_identity_leakage_is_rejected(self):
        report = evaluate_identity_scope(
            [
                np.array([0.95, 0.20, 0.05]),
                np.array([0.85, 0.25, 0.10]),
            ],
            self.boxes[:2],
            self.confidences[:2],
            self.identity,
            0.75,
        )
        self.assertEqual(report.status, "rejected")
        self.assertIn("identity_leaked_to_secondary_face", report.failures)

    def test_lookalike_is_rejected_against_selected_main(self):
        report = evaluate_identity_scope(
            [
                np.array([0.92, 0.25, 0.10]),
                np.array([0.48, 0.80, 0.15]),
            ],
            self.boxes[:2],
            self.confidences[:2],
            self.identity,
            0.75,
        )
        self.assertEqual(report.status, "rejected")
        self.assertIn("secondary_face_too_similar_to_main", report.failures)

    def test_duplicate_secondary_faces_are_rejected(self):
        report = evaluate_identity_scope(
            [
                np.array([0.95, 0.20, 0.05]),
                np.array([0.10, 0.95, 0.20]),
                np.array([0.12, 0.92, 0.22]),
            ],
            self.boxes,
            self.confidences,
            self.identity,
            0.75,
        )
        self.assertEqual(report.status, "rejected")
        self.assertIn("duplicate_secondary_faces", report.failures)

    def test_missing_or_weak_main_face_is_rejected(self):
        empty = evaluate_identity_scope([], [], [], self.identity, 0.75)
        self.assertIn("no_detected_face", empty.failures)
        weak = evaluate_identity_scope(
            [np.array([0.4, 0.9, 0.0])],
            self.boxes[:1],
            self.confidences[:1],
            self.identity,
            0.75,
        )
        self.assertIn("main_identity_below_threshold", weak.failures)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from identity_scope import build_multi_person_identity_prompt


class IdentityScopeTests(unittest.TestCase):
    def test_identity_token_is_scoped_only_to_main_subject(self):
        prompt = build_multi_person_identity_prompt(
            "Two unrelated adults sit at separate tables.",
            "m1tchperson",
        )
        self.assertIn("applies exclusively to the main subject", prompt)
        self.assertIn("never to any secondary person", prompt)
        self.assertIn("Every secondary person is an unrelated individual", prompt)
        self.assertNotIn("exactly one adult person", prompt)

    def test_empty_identity_token_is_rejected(self):
        with self.assertRaises(ValueError):
            build_multi_person_identity_prompt("A cafe scene", "  ")

    def test_priority_constraints_are_first(self):
        prompt = build_multi_person_identity_prompt(
            "A cafe scene",
            "m1tchperson",
            priority_constraints="exactly three humans and two cars",
        )
        self.assertTrue(prompt.startswith("NONNEGOTIABLE FRAME CONSTRAINTS:"))
        self.assertLess(prompt.index("exactly three humans"), prompt.index("Create one"))


if __name__ == "__main__":
    unittest.main()

import unittest

from flux2_klein9b_appearance_polish import compose_appearance_polish


class AppearancePolishTests(unittest.TestCase):
    def test_disabled_clause_is_empty(self):
        self.assertEqual(
            compose_appearance_polish(False, expression_authority="the requested expression"),
            "",
        )

    def test_enabled_clause_uses_positive_identity_safe_language(self):
        clause = compose_appearance_polish(
            True,
            expression_authority="the requested expression",
        )
        self.assertIn("recognizable as the same adult", clause)
        self.assertIn("about three to five years younger", clause)
        self.assertIn("slightly stronger natural jaw and chin", clause)
        self.assertIn("modestly higher and more defined cheekbones", clause)
        self.assertIn("the requested expression", clause)
        self.assertIn("attractive, confident, approachable expression", clause)
        self.assertIn("one natural unbroken lip line", clause)
        self.assertIn("every tooth remains behind the lips", clause)
        self.assertIn("single unbroken closed lip line", clause)
        self.assertIn("eyes slightly more attractive", clause)
        self.assertIn("natural eye size, iris color, spacing", clause)
        self.assertIn("reduce fine forehead lines, crow's-feet, and under-eye creasing by about half", clause)
        self.assertIn("noticeable light bronze sun tan", clause)
        self.assertIn("pores finer and less prominent while still visible", clause)
        self.assertIn("stubble neatly trimmed, even, and flattering", clause)
        self.assertIn("identity-faithful", clause)
        for prohibited in ("larger eyes", "smaller nose", "stronger jaw", "face swap"):
            self.assertNotIn(prohibited, clause)

    def test_group_safe_variant_preserves_exact_head_shape(self):
        clause = compose_appearance_polish(
            True,
            expression_authority="the calm expression",
            preserve_bone_structure=True,
        )
        self.assertIn("exact natural head and face shape", clause)
        self.assertIn("true face length-to-width ratio", clause)
        self.assertIn("Do not broaden, square, narrow, lengthen, shorten", clause)
        self.assertNotIn("slightly stronger natural jaw and chin", clause)


if __name__ == "__main__":
    unittest.main()

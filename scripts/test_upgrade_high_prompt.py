import unittest
from experimental_upgrade_high_prompt import make_high_prompt


class HighPromptTests(unittest.TestCase):
    def test_changes_only_identity_presentation_role(self):
        before = 'casual snapshot. Picture 1 preserve source pose. Picture 2 exact expression contours. '
        identity = 'Picture 3 is a protected genuine photograph and supplies current apparent age. '
        after = 'Picture 4 is isolated hair. Keep the same detailed environment.'
        result = make_high_prompt(before + identity + after)
        self.assertTrue(result.startswith(before))
        self.assertTrue(result.endswith(after))
        self.assertIn('m1tch_person', result)
        self.assertIn('no teeth', result)
        self.assertIn('exact iris focus', result)
        self.assertIn('not rounded or swollen', result)
        self.assertNotIn('supplies current apparent age', result)

    def test_refuses_unknown_and_reduced_reference_layout(self):
        for text in ('', 'Picture 1. Picture 3 is hair.',
                     'Picture 3 is a protected genuine photograph. No fourth image.'):
            with self.assertRaises(ValueError):
                make_high_prompt(text)

    def test_shipped_house_role(self):
        result = make_high_prompt('Picture 1. Picture 2. Picture 3 exclusively supplies the identity '
                                  'and current apparent age of m1tch_person. Picture 4 is hair.')
        self.assertTrue(result.startswith('Picture 1. Picture 2. '))
        self.assertTrue(result.endswith('Picture 4 is hair.'))


if __name__ == '__main__':
    unittest.main()

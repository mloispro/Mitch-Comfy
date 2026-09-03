import unittest

from flux2_klein9b_upgrade_reference_policy import (
    QUALITY_IDENTITY_REFERENCE_MEGAPIXELS,
    TURBO_IDENTITY_REFERENCE_MEGAPIXELS,
    identity_reference_megapixels,
)


class UpgradeReferencePolicyTests(unittest.TestCase):
    def test_quality_path_retains_locked_half_megapixel_identity_reference(self):
        self.assertEqual(QUALITY_IDENTITY_REFERENCE_MEGAPIXELS, 0.50)
        self.assertEqual(identity_reference_megapixels(False), 0.50)

    def test_turbo_path_uses_one_megapixel_identity_reference(self):
        self.assertEqual(TURBO_IDENTITY_REFERENCE_MEGAPIXELS, 1.00)
        self.assertEqual(identity_reference_megapixels(True), 1.00)


if __name__ == "__main__":
    unittest.main()

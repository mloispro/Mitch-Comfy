import unittest

from upgrade_expression_acceptance import closed_lip_check, identity_retention_check


class ClosedLipAcceptanceTests(unittest.TestCase):
    def test_third_photo_open_mouth_is_rejected(self):
        self.assertFalse(closed_lip_check(0.005749, 0.066153)["passed"])

    def test_open_source_does_not_waive_requested_closed_lips(self):
        self.assertFalse(closed_lip_check(0.08, 0.066153)["passed"])

    def test_closed_canyon_and_house_pass(self):
        for opening in (0.002698, 0.000767, 0.035):
            self.assertTrue(closed_lip_check(0.005749, opening)["passed"])

    def test_invalid_measurements_fail_closed(self):
        for invalid in (-0.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                closed_lip_check(0.001, invalid)

    def test_source_repair_cannot_use_a_poor_raw_to_waive_identity_loss(self):
        self.assertFalse(identity_retention_check(.9,.5,.74,'source-fidelity')['passed'])

    def test_high_can_improve_identity_over_a_weak_edit_source(self):
        self.assertTrue(identity_retention_check(.35,.75,.74,'high-edit')['passed'])

    def test_genuine_third_repair_passes_against_source(self):
        self.assertTrue(identity_retention_check(.825853,.777842,.825638,'source-fidelity')['passed'])

    def test_invalid_identity_measurements_fail(self):
        with self.assertRaises(ValueError):
            identity_retention_check(.8,.8,float('nan'),'high-edit')


if __name__ == "__main__":
    unittest.main()

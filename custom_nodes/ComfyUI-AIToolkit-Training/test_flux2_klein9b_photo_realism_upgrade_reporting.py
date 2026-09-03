import ast
import unittest
from pathlib import Path


NODE_PATH = Path(__file__).with_name("flux2_klein9b_photo_realism_upgrade.py")


def _report_fields():
    tree = ast.parse(NODE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "report" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        return {
            key.value: value
            for key, value in zip(node.value.keys, node.value.values)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
    raise AssertionError("Upgrade report dictionary was not found")


def _module_constants():
    tree = ast.parse(NODE_PATH.read_text(encoding="utf-8"))
    constants = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


class UpgradePhotoReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields = _report_fields()
        cls.constants = _module_constants()

    def test_full_source_identity_influence_is_reported_as_unproven(self):
        self.assertEqual(ast.literal_eval(self.fields["schema_version"]), 2)
        self.assertIsNone(ast.literal_eval(self.fields["source_used_as_identity"]))
        self.assertFalse(
            ast.literal_eval(self.fields["source_intended_as_identity_reference"])
        )
        self.assertEqual(
            ast.literal_eval(self.fields["source_identity_influence_status"]),
            "unisolated_not_proven_absent",
        )
        note = ast.unparse(self.fields["source_identity_influence_note"])
        self.assertIn("contains the source face", note)
        self.assertIn("cannot", note)
        self.assertIn("claimed absent", note)
        reference_order = ast.unparse(self.fields["reference_order"])
        self.assertIn("intended to guide scene", reference_order)
        self.assertIn("not isolated or proven absent", reference_order)
        identity_mechanism = ast.unparse(self.fields["identity_mechanism"])
        self.assertIn("explicit identity mechanism", identity_mechanism)

    def test_optional_paths_are_not_reported_as_executed_when_disabled(self):
        approval_basis = ast.unparse(self.fields["approval_basis"])
        self.assertIn("phone-off route", approval_basis)
        self.assertIn("not part of that exact shipped-default generation run", approval_basis)
        graph_delta = ast.unparse(self.fields["graph_delta_from_milestone"])
        self.assertIn("if appearance_polish", graph_delta)
        self.assertIn("appearance polish is disabled", graph_delta)
        appearance_scope = ast.unparse(self.fields["appearance_scope"])
        self.assertIn("if appearance_polish", appearance_scope)
        self.assertIn("no face, iris, or hair-local appearance postprocess runs", appearance_scope)

    def test_historical_milestone_sampling_is_unpreserved_for_both_modes(self):
        self.assertFalse(
            ast.literal_eval(self.fields["milestone_sampling_path_preserved"])
        )
        status = ast.unparse(self.fields["milestone_sampling_path_status"])
        self.assertIn("unpreserved_phone_on_prompt_and_smartphone_lora_drift", status)
        self.assertIn("unpreserved_phone_off_prompt_drift", status)
        graph_delta = ast.unparse(self.fields["graph_delta_from_milestone"])
        self.assertIn("phone-on differs from d58732a through prompt drift", graph_delta)
        self.assertIn("phone-off differs from d58732a through prompt drift", graph_delta)
        self.assertIn("Smartphone Snapshot v13 LoRA", graph_delta)
        self.assertNotIn("unchanged generation", graph_delta)
        self.assertTrue(
            ast.literal_eval(self.fields["milestone_generation_prompt_changed"])
        )
        prompt_changed = ast.unparse(
            self.fields["phone_style_generation_prompt_changed"]
        )
        self.assertEqual(prompt_changed, "bool(phone_camera_style)")
        self.assertTrue(
            ast.literal_eval(self.fields["background_generation_prompt_changed"])
        )

    def test_report_only_hardening_preserves_revalidated_sampling_path(self):
        self.assertEqual(self.constants["REVALIDATION_COMMIT"], "b32ecb9")
        self.assertEqual(
            self.constants["REVALIDATION_TAG"],
            "milestone-klein9b-production-revalidated-2026-09-03",
        )
        self.assertTrue(
            ast.literal_eval(self.fields["revalidation_sampling_path_preserved"])
        )
        self.assertFalse(
            ast.literal_eval(
                self.fields[
                    "revalidation_generation_prompt_changed_by_report_hardening"
                ]
            )
        )
        scope = ast.unparse(self.fields["revalidation_comparison_scope"])
        self.assertIn("Compared with b32ecb9", scope)
        self.assertIn("report-only hardening", scope)
        self.assertIn("postprocessing are unchanged", scope)


if __name__ == "__main__":
    unittest.main()

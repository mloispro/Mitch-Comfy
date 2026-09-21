"""Offline checks for evidence integrity and preparation without inherited acceptance."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("evaluation_cases", Path(__file__).with_name("evaluation-cases.py"))
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


class EvaluationCasesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "baseline.png").write_bytes(b"test baseline")
        (self.root / "candidate.png").write_bytes(b"test candidate")
        (self.root / "reference.jpg").write_bytes(b"test reference")
        (self.root / "source.jpg").write_bytes(b"test source")
        self.graph = {"1": {"class_type": "SaveImage", "inputs": {"images": ["2", 0]}}}
        (self.root / "recipe.json").write_text(json.dumps(self.graph))
        self.case = {
            "id": "test-upgrade", "area": "upgrade", "label": "Test <image>",
            "recorded_outcome": "qualified", "scope": "one source",
            "identity_reference_ids": ["other"], "excluded_identity_reference_ids": ["source"],
            "visual_checks": ["Keep pose and closed lips"],
            "artifacts": {role: cases.pin("baseline.png", self.root) for role in
                          ("photo", "diagnostics", "visual_review", "conclusion")},
        }
        self.case["artifacts"]["recipe"] = cases.pin("recipe.json", self.root)
        self.case["artifacts"]["source"] = cases.pin("source.jpg", self.root)
        self.data = {"schema_version": 1, "references": {
            "other": cases.pin("reference.jpg", self.root),
            "source": cases.pin("source.jpg", self.root)}, "cases": [self.case]}

    def load(self, data):
        path = self.root / "catalog.json"
        path.write_text(json.dumps(data))
        return cases.load_catalog(path)

    def prepare(self, name="candidate-review", recipe="recipe.json"):
        return cases.prepare_review(self.data, self.case, "candidate.png", recipe,
                                    "One <controlled> change", self.root / "work/evaluation-reviews" / name,
                                    self.root)

    def test_reference_drift_and_missing_photo_are_detected(self):
        self.assertEqual(cases.check(self.data, [self.case], self.root), 4)
        (self.root / "reference.jpg").write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "Missing or changed"):
            cases.check(self.data, [self.case], self.root)
        (self.root / "reference.jpg").write_bytes(b"test reference")
        (self.root / "baseline.png").unlink()
        with self.assertRaisesRegex(ValueError, "Missing or changed"):
            cases.check(self.data, [self.case], self.root)

    def test_scoped_selection_does_not_validate_unrelated_stale_case(self):
        stale = copy.deepcopy(self.case)
        stale.update(id="other-solo", area="solo")
        stale["artifacts"]["photo"] = {"path": "absent.png", "sha256": "a" * 64}
        self.data["cases"].append(stale)
        selected = cases.select(self.data, area="upgrade", query="closed lips")
        self.assertEqual([c["id"] for c in selected], ["test-upgrade"])
        cases.check(self.data, selected, self.root)
        with self.assertRaisesRegex(ValueError, "Missing or changed"):
            cases.check(self.data, self.data["cases"], self.root)
        with self.assertRaisesRegex(ValueError, "No matching"):
            cases.select(self.data, case_id="invented")

    def test_source_exclusion_cannot_be_lost_or_aliased(self):
        self.load(self.data)
        self.case["identity_reference_ids"].append("source")
        with self.assertRaisesRegex(ValueError, "Excluded source"):
            self.load(self.data)
        self.case["identity_reference_ids"] = ["other"]
        self.data["references"]["other"] = self.data["references"]["source"]
        with self.assertRaisesRegex(ValueError, "Source bytes"):
            self.load(self.data)

    def test_new_review_never_inherits_historical_verdict_or_runs_code(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        output = self.prepare()
        report = cases.read_json(output / "review.json")
        self.assertEqual(report["historical_case"]["recorded_outcome"], "qualified")
        self.assertEqual(report["status"], "pending_review")
        for key in ("decision", "runtime_attribution", "numerical_review"):
            self.assertEqual(report[key]["status"], "unreviewed")
        self.assertIsNone(report["visual_review"][0]["native"])
        self.assertIsNone(report["visual_review"][0]["thumbnail"])
        self.assertEqual(report["candidate_recipe"]["sha256"], cases.digest(self.root / "recipe.json"))
        self.assertEqual(report["historical_case"]["identity_reference_ids"], ["other"])
        self.assertIn("excluded_identity_reference:source", report["historical_evidence"])
        self.assertNotIn("identity_reference:source", report["historical_evidence"])
        page = (output / "review.html").read_text()
        self.assertIn("One &lt;controlled&gt; change", page)
        self.assertNotIn("<script", page)
        self.assertIn("Native size", page)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def test_ui_workflow_is_rejected_before_creating_review(self):
        (self.root / "ui.json").write_text(json.dumps({"nodes": []}))
        with self.assertRaisesRegex(ValueError, "executed API graph"):
            self.prepare(recipe="ui.json")
        self.assertFalse((self.root / "work").exists())

    def test_existing_review_and_paths_outside_output_scope_are_protected(self):
        output = self.prepare()
        before = (output / "review.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual((output / "review.json").read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "Write review bundles"):
            cases.prepare_review(self.data, self.case, "candidate.png", "recipe.json", "change",
                                 self.root / "existing-experiment", self.root)
        with self.assertRaisesRegex(ValueError, "outside this project"):
            cases.resolve("../../outside.jpg", self.root)

    def test_duplicate_case_ids_are_rejected(self):
        self.data["cases"].append(copy.deepcopy(self.case))
        with self.assertRaisesRegex(ValueError, "Duplicate case"):
            self.load(self.data)


if __name__ == "__main__":
    unittest.main()

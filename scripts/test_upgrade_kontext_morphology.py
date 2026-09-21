"""Offline CPU regression checks for the single base-Kontext prompt refinement.

Loads only small saved evidence and the local tokenizer. No model loading, GPU,
HTTP, queue access, or experiment writes; guard fixtures use temporary folders.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).with_name("run-upgrade-kontext-morphology.py")
spec = importlib.util.spec_from_file_location("kontext_morphology_under_test", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

EXPECTED_PROMPT = (
    "Edit only the man's face to look noticeably more handsome while remaining recognizably the same man. "
    "Give him more open, well-defined eyes with relaxed upper eyelids, naturally fuller well-shaped eyebrows, "
    "leaner cheeks and a more defined jaw. Give him a warmer, confident asymmetric closed-lip smile with "
    "both lips gently together and no visible teeth. Make his skin clearer and more even, reducing freckles, "
    "dark spots and deep forehead lines while retaining natural pores and light stubble. Preserve his nose, "
    "eye colour, pupil direction, head angle, forehead height, hairline and face scale. Keep his hair, body, "
    "clothing, background, lighting and framing unchanged. The result should remain a realistic photograph."
)
EXPECTED_PREFIX = "upgrade-high-20260907/kontext-canyon-explicit-high/raw"


def differences(before, after, path=""):
    """Independent recursive JSON comparison, not the runner's diff reporter."""
    if isinstance(before, dict) and isinstance(after, dict):
        changed = []
        for key in sorted(before.keys() | after.keys()):
            here = path + "/" + key
            if key not in before or key not in after:
                changed.append(here)
            else:
                changed.extend(differences(before[key], after[key], here))
        return changed
    return [] if before == after else [path]


class KontextMorphologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads((runner.BASELINE / "experiment.json").read_text(encoding="utf-8"))

    def test_01_completed_baseline_evidence_is_still_pinned(self):
        self.assertEqual(runner.BASELINE.name, "kontext-canyon-adapter-off-control")
        self.assertEqual(runner.BASELINE_ID, "c3aa6628-6003-41fb-ae14-6afb3894c75d")
        for filename, digest in runner.PINS.items():
            with self.subTest(filename=filename):
                self.assertEqual(hashlib.sha256((runner.BASELINE / filename).read_bytes()).hexdigest(), digest)
        saved = json.loads((runner.BASELINE / "prompt-api.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, self.baseline["prompt"])

    def test_02_exact_prompt_and_prefix_are_the_only_changes(self):
        untouched = copy.deepcopy(self.baseline)
        graph, reported = runner.changed_graph(self.baseline)
        self.assertEqual(runner.PROMPT, EXPECTED_PROMPT)
        self.assertEqual(graph["8"]["inputs"]["text"], EXPECTED_PROMPT)
        self.assertEqual(graph["14"]["inputs"]["filename_prefix"], EXPECTED_PREFIX)
        expected_paths = {"/8/inputs/text", "/14/inputs/filename_prefix"}
        self.assertEqual(set(differences(self.baseline["prompt"], graph)), expected_paths)
        self.assertEqual({item["path"] for item in reported}, expected_paths)
        self.assertEqual(len(reported), 2)
        for item in reported:
            _, node, _, field = item["path"].split("/")
            self.assertEqual(item["before"], self.baseline["prompt"][node]["inputs"][field])
            self.assertEqual(item["after"], graph[node]["inputs"][field])
        self.assertEqual(self.baseline, untouched, "Refinement must not mutate the completed baseline.")

    def test_03_source_models_conditioning_and_sampling_stay_fixed(self):
        graph, _ = runner.changed_graph(self.baseline)
        for node_id in graph.keys() - {"8", "14"}:
            self.assertEqual(graph[node_id], self.baseline["prompt"][node_id])
        self.assertEqual(graph["2"]["inputs"]["strength_model"], 0.0)
        self.assertEqual(graph["2"]["inputs"]["model"], ["1", 0])
        self.assertEqual(graph["1"]["inputs"], {
            "unet_name": "flux1-kontext-dev.safetensors", "weight_dtype": "default"})
        self.assertEqual(graph["3"]["inputs"]["clip_name2"], "t5xxl_fp16.safetensors")
        self.assertEqual(graph["8"]["class_type"], "CLIPTextEncode")
        self.assertEqual(graph["8"]["inputs"]["clip"], ["3", 0])
        self.assertNotIn("T5TokenizerOptions", {node["class_type"] for node in graph.values()})
        self.assertNotIn("15", graph)
        self.assertEqual(graph["5"]["inputs"]["image"],
                         "mitch-beautygrpo-canyon-contained-edgepad-e12c0c3d.png")
        self.assertEqual(graph["7"]["inputs"]["pixels"], ["5", 0])
        self.assertEqual(graph["9"]["inputs"], {"conditioning": ["8", 0], "latent": ["7", 0]})
        self.assertEqual(graph["10"]["inputs"]["guidance"], 2.5)
        self.assertEqual(graph["12"]["inputs"], {
            "model": ["2", 0], "positive": ["10", 0], "negative": ["11", 0],
            "latent_image": ["7", 0], "seed": 42, "steps": 28, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0})

    def test_04_wrong_graph_baselines_are_rejected(self):
        mutations = (
            lambda g: g["2"]["inputs"].update(strength_model=1.0),
            lambda g: g["8"]["inputs"].update(text="Different baseline prompt"),
            lambda g: g["8"]["inputs"].update(clip=["15", 0]),
            lambda g: g.update({"15": {"class_type": "AnyUnexpectedNode", "inputs": {}}}),
            lambda g: g.update({"99": {"class_type": "T5TokenizerOptions", "inputs": {}}}),
        )
        for number, mutate in enumerate(mutations):
            with self.subTest(mutation=number):
                baseline = copy.deepcopy(self.baseline)
                mutate(baseline["prompt"])
                with self.assertRaisesRegex(ValueError, "exact adapter-off/direct-CLIP/default-T5"):
                    runner.changed_graph(baseline)

    def test_05_prompt_fits_unchanged_native_t5_and_rejects_rewording(self):
        tokenizer = runner.COMFY / "comfy/text_encoders/t5_tokenizer/tokenizer.json"
        self.assertEqual(hashlib.sha256(tokenizer.read_bytes()).hexdigest(),
                         runner.SOURCE_PINS["comfy/text_encoders/t5_tokenizer/tokenizer.json"])
        self.assertEqual(runner.token_length_guard(EXPECTED_PROMPT), {
            "unpadded_token_count_including_eos": 166,
            "native_minimum_length": 256,
            "padding_override": False,
            "token_ids_sha256": "207aff9afba0761e6e0c03508d46c93b51c00bf0489d6cdb31536d1d4dd7784b"})
        with self.assertRaisesRegex(ValueError, "Exact approved morphology prompt changed"):
            runner.token_length_guard(EXPECTED_PROMPT + " Another instruction.")

    def assert_early_guard(self, fixture, arguments, message):
        with tempfile.TemporaryDirectory(prefix="kontext-morphology-unit-") as temporary:
            root = Path(temporary)
            destination, comfy = root / "experiment", root / "ComfyUI"
            fixture(destination, comfy)
            blocked_helper = Mock(side_effect=AssertionError("No helper, API or GPU access allowed in guard tests."))
            with patch.object(runner, "DESTINATION", destination), patch.object(runner, "COMFY", comfy), \
                    patch.object(runner, "helpers", blocked_helper), patch.object(sys, "argv", [str(SCRIPT), *arguments]):
                with self.assertRaisesRegex(ValueError, message):
                    runner.main()
            blocked_helper.assert_not_called()

    def test_06_existing_preparation_attempts_and_outputs_are_preserved(self):
        for filename in ("submission-intent.json", "submission.json"):
            for arguments in ([], ["--execute"]):
                with self.subTest(filename=filename, arguments=arguments):
                    def attempted(destination, comfy):
                        destination.mkdir()
                        (destination / filename).touch()
                    self.assert_early_guard(attempted, arguments, "Submission already attempted")
        self.assert_early_guard(lambda destination, comfy: destination.mkdir(), [],
                                "Preserve the existing prepared experiment")
        self.assert_early_guard(
            lambda destination, comfy: (comfy / "output/upgrade-high-20260907" / runner.CASE).mkdir(parents=True),
            [], "Experiment output directory exists")

    def test_07_execute_requires_preparation_and_owned_cache_proof(self):
        self.assert_early_guard(lambda destination, comfy: None, ["--execute"],
                                "Prepare and review this exact experiment")
        def prepared(destination, comfy):
            destination.mkdir()
            for name in ("experiment.json", "prompt-api.json", "preparation.json"):
                (destination / name).touch()
        self.assert_early_guard(prepared, ["--execute"], "Execution requires --previous-run")

    def test_08_changed_evidence_is_rejected_before_any_api_or_model_access(self):
        fake_sha = Mock(return_value="0" * 64)
        forbidden_api = Mock(side_effect=AssertionError("Offline test must never contact ComfyUI."))
        forbidden_output = Mock(side_effect=AssertionError("Changed pins must stop before output validation."))
        with self.assertRaisesRegex(ValueError, "Pinned completed base-control evidence changed: experiment.json"):
            runner.verified_manifest({"sha": fake_sha, "api": forbidden_api},
                                     {"successful_output": forbidden_output})
        fake_sha.assert_called_once_with(runner.BASELINE / "experiment.json")
        forbidden_api.assert_not_called()
        forbidden_output.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

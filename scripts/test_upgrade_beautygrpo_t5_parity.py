"""CPU-only T5 experiment tests; no model weights, Comfy imports, APIs or GPU.

Run with the existing ComfyUI Python. Only the small local tokenizer JSON is
read for the fixed-token regression; all experiment evidence and services are
mocked. Submission-guard fixtures live in disposable temporary directories.
"""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).with_name("run-upgrade-beautygrpo-t5-parity.py")
spec = importlib.util.spec_from_file_location("t5_parity_under_test", SCRIPT)
runner = importlib.util.module_from_spec(spec)
with patch.object(sys, "dont_write_bytecode", True):
    spec.loader.exec_module(runner)

FIXED_PROMPT = (
    "Beautify this person's face while maintaining a natural and realistic appearance. "
    "Make his existing slight asymmetric smile more relaxed and quietly confident, "
    "keeping his lips gently together with no visible teeth. Keep his natural eye shape, "
    "softly defined eyelid edges and natural bare skin around the eyes. Preserve his "
    "recognizable identity, exact pupil focus, head tilt, hairline and cheek width. "
    "Keep his body, phone, clothing, background, framing and lighting unchanged."
)


def node(class_type, **inputs):
    return {"class_type": class_type, "inputs": inputs}


def baseline_fixture():
    return {
        "prompt": {
            "1": node("UNETLoader", unet_name="flux1-kontext-dev.safetensors", weight_dtype="default"),
            "2": node("LoraLoaderModelOnly", model=["1", 0], lora_name="beautygrpo\\BeautyGRPO.safetensors", strength_model=1.0),
            "3": node("DualCLIPLoader", clip_name1="clip_l.safetensors", clip_name2="t5xxl_fp16.safetensors", type="flux", device="default"),
            "4": node("VAELoader", vae_name="ae.safetensors"),
            "5": node("LoadImage", image="unchanged-staged-source.png"),
            "7": node("VAEEncode", pixels=["5", 0], vae=["4", 0]),
            "8": node("CLIPTextEncode", clip=["3", 0], text=FIXED_PROMPT),
            "9": node("ReferenceLatent", conditioning=["8", 0], latent=["7", 0]),
            "10": node("FluxGuidance", conditioning=["9", 0], guidance=2.5),
            "11": node("ConditioningZeroOut", conditioning=["8", 0]),
            "12": node("KSampler", model=["2", 0], positive=["10", 0], negative=["11", 0], latent_image=["7", 0],
                       seed=42, steps=28, cfg=1.0, sampler_name="euler", scheduler="simple", denoise=1.0),
            "13": node("VAEDecode", samples=["12", 0], vae=["4", 0]),
            "14": node("SaveImage", images=["13", 0], filename_prefix="unchanged-baseline/raw"),
        },
        "source": {"path": "synthetic-fixture.png", "sha256": "source-fixture", "genuine": False,
                   "upstream_character_lora": "unknown", "preparation": {"prepared_size": [1024, 1024]}},
        "models": [{"target": "same-model", "sha256": "same-model-fixture"}],
        "other_models": [{"path": "same-encoder", "sha256": "same-encoder-fixture"}],
        "coverage": {"native_loader_patches": 342}, "seed": 42, "steps": 28, "guidance": 2.5,
        "character_lora": False, "phone_adapter": False, "turbo": False, "postprocess": False,
        "backend_differences": ["CLIP/T5 FP16 vs author BF16", "CPU seeded noise", "Comfy simple schedule"],
        "fixed_recipe_scope": "old scope", "output_node": "14",
    }


class T5GraphTests(unittest.TestCase):
    def setUp(self):
        self.baseline = baseline_fixture()
        self.control = {
            "read_json": Mock(side_effect=lambda _: copy.deepcopy(self.baseline)),
            "verified_manifest": Mock(return_value={
                "baseline": {"prompt_id": "2c7b50ea-9468-4ab3-bd35-e3d33f229d56"},
                "comparison_path": "baseline-beauty1.png", "comparison_sha256": "output-fixture",
                "helper_pins": {"evaluate-upgrade-beautygrpo.py": "evaluator-fixture"},
                "diagnostic_control_only": True, "zero_adapter_loader": {"must_not_leak": True},
            }),
        }
        self.info = {"T5TokenizerOptions": {"input": {"required": {
            "clip": ["CLIP"], "min_padding": ["INT", {"min": 0, "max": 10000}],
            "min_length": ["INT", {"min": 0, "max": 10000}],
        }}}}
        pins = {runner.COMFY / name: value for name, value in runner.SOURCE_PINS.items()}
        pins[SCRIPT.resolve()] = "script-fixture"
        self.helper = {"sha": Mock(side_effect=lambda path: pins[path]), "api": Mock(return_value=self.info)}
        self.token_patch = patch.object(runner, "token_length_guard", return_value={"unpadded_token_count_including_eos": 101})
        self.tokens = self.token_patch.start()
        self.addCleanup(self.token_patch.stop)

    def build(self):
        return runner.build_manifest(self.control, self.helper, {})

    def test_exact_only_option_node_clip_link_and_prefix_change(self):
        before = copy.deepcopy(self.baseline)
        manifest = self.build()
        graph = copy.deepcopy(manifest["prompt"])
        self.assertEqual(graph.pop("15"), node("T5TokenizerOptions", clip=["3", 0], min_padding=0, min_length=512))
        self.assertEqual(graph["8"]["inputs"]["clip"], ["15", 0])
        graph["8"]["inputs"]["clip"] = ["3", 0]
        self.assertEqual(graph["14"]["inputs"]["filename_prefix"], "upgrade-high-20260907/beautygrpo-canyon-t5-512/raw")
        graph["14"]["inputs"]["filename_prefix"] = before["prompt"]["14"]["inputs"]["filename_prefix"]
        self.assertEqual(graph, before["prompt"])
        self.assertEqual(self.baseline, before)
        self.assertEqual({item["path"] for item in manifest["graph_differences"]},
                         {"/15", "/8/inputs/clip", "/14/inputs/filename_prefix"})
        self.tokens.assert_called_once_with(FIXED_PROMPT)
        self.helper["api"].assert_called_once_with(8188, "object_info")

    def test_active_beauty_source_settings_and_truthful_scope(self):
        manifest = self.build()
        self.assertTrue(manifest["active_beauty_adapter"])
        self.assertEqual(manifest["prompt"]["2"]["inputs"]["strength_model"], 1.0)
        for field in ("source", "models", "other_models", "seed", "steps", "guidance", "turbo", "phone_adapter"):
            self.assertEqual(manifest[field], self.baseline[field])
        self.assertFalse(manifest["author_bit_exact"])
        self.assertEqual(manifest["comparison_label"], "BEAUTYGRPO T5 256")
        self.assertEqual(manifest["comparison_path"], "baseline-beauty1.png")
        self.assertNotIn("diagnostic_control_only", manifest)
        self.assertNotIn("zero_adapter_loader", manifest)
        self.assertEqual(manifest["remaining_author_differences"][:3], self.baseline["backend_differences"])

    def test_rejects_adapter_off_or_changed_clip_or_existing_option_node(self):
        original = copy.deepcopy(self.baseline)
        for mutation in ("adapter", "clip", "node15"):
            with self.subTest(mutation=mutation):
                self.baseline = copy.deepcopy(original)
                if mutation == "adapter": self.baseline["prompt"]["2"]["inputs"]["strength_model"] = 0.0
                elif mutation == "clip": self.baseline["prompt"]["8"]["inputs"]["clip"] = ["other", 0]
                else: self.baseline["prompt"]["15"] = node("Unexpected")
                with self.assertRaisesRegex(ValueError, "fixed active-adapter/direct-CLIP"):
                    self.build()

    def test_rejects_changed_native_source_hash(self):
        self.helper["sha"] = Mock(return_value="changed")
        with self.assertRaisesRegex(ValueError, "tokenizer implementation changed"):
            self.build()
        self.helper["api"].assert_not_called()

    def test_rejects_absent_native_node_or_incompatible_length_schema(self):
        self.helper["api"].return_value = {}
        with self.assertRaisesRegex(ValueError, "not live"):
            self.build()
        self.info["T5TokenizerOptions"]["input"]["required"]["min_length"][1]["max"] = 256
        self.helper["api"].return_value = self.info
        with self.assertRaisesRegex(ValueError, "schema differs"):
            self.build()


class T5TokenAndPinTests(unittest.TestCase):
    def test_exact_fixed_prompt_ids_and_padding(self):
        evidence = runner.token_length_guard(FIXED_PROMPT)
        self.assertEqual(evidence["unpadded_token_count_including_eos"], 101)
        self.assertEqual(evidence["padding_token_count"], 411)
        self.assertEqual(evidence["target_minimum_length"], 512)
        self.assertEqual(evidence["minimum_extra_padding"], 0)
        self.assertTrue(evidence["min_length_is_not_max_length"])
        self.assertEqual(evidence["token_ids_sha256"], "2757538817bf7b16370a1d5b8d514ff47442ede36c191ad6a7d57098d4bdae8d")
        self.assertEqual(evidence["expected_native_padded_ids_sha256"], "6e8471557e8089894f0795f4f21030a31f6710408141b3253ab8e0cc90fe2030")

    def test_changed_prompt_is_rejected(self):
        with self.assertRaises(ValueError):
            runner.token_length_guard("A different prompt.")

    def test_rejects_wrong_count_eos_or_ids_even_with_same_length(self):
        for ids, message in (([3] * 99 + [1], "fixed101-token"), ([3] * 512 + [1], "fixed101-token"),
                             ([3] * 101, "fixed101-token"), ([3] * 100 + [1], "token IDs differ")):
            with self.subTest(length=len(ids), end=ids[-1]):
                tokenizer = Mock()
                tokenizer.encode.return_value = SimpleNamespace(ids=ids)
                module = SimpleNamespace(Tokenizer=SimpleNamespace(from_file=Mock(return_value=tokenizer)))
                with patch.dict(sys.modules, {"tokenizers": module}):
                    with self.assertRaisesRegex(ValueError, message):
                        runner.token_length_guard(FIXED_PROMPT)
                tokenizer.no_padding.assert_called_once()
                tokenizer.no_truncation.assert_called_once()

    def test_all_recorded_source_pins_are_exactly64_hex_characters(self):
        for name, digest in runner.SOURCE_PINS.items():
            with self.subTest(name=name):
                self.assertEqual(len(digest), 64)
                self.assertLessEqual(set(digest), set("0123456789abcdef"))

    def test_malformed_hash_fails_before_loading_helpers(self):
        for malformed in ("a" * 63, "a" * 65, "g" * 64):
            with self.subTest(pin=malformed), patch.dict(runner.SOURCE_PINS, {"bad": malformed}, clear=True), \
                    patch.object(runner, "CONTROL_HELPER") as helper_path, patch.object(runner, "run_path") as load:
                with self.assertRaisesRegex(ValueError, "exactly64 hexadecimal"):
                    runner.helpers()
                helper_path.read_bytes.assert_not_called()
                load.assert_not_called()


class T5SubmissionGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="t5-parity-unit-")
        self.addCleanup(temporary.cleanup)
        self.destination = Path(temporary.name) / "fake-run"
        for name, value in (("DESTINATION", self.destination), ("COMFY", Path(temporary.name) / "ComfyUI")):
            patcher = patch.object(runner, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(runner, "helpers", side_effect=AssertionError("Guard must reject before helper/API/model access"))
        self.helpers = patcher.start()
        self.addCleanup(patcher.stop)

    def invoke(self, *args):
        with patch.object(sys, "argv", [str(SCRIPT), *args]):
            runner.main()

    def test_execute_requires_all_prepared_files(self):
        with self.assertRaisesRegex(ValueError, "Prepare and review"):
            self.invoke("--execute")
        self.destination.mkdir()
        (self.destination / "experiment.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Prepare and review"):
            self.invoke("--execute", "--previous-run", "fake-owned-run")
        self.helpers.assert_not_called()

    def test_existing_intent_or_submission_prevents_any_retry(self):
        self.destination.mkdir()
        for filename in ("submission-intent.json", "submission.json"):
            path = self.destination / filename
            path.write_text("{}", encoding="utf-8")
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, "no blind resubmission"):
                self.invoke("--execute", "--previous-run", "fake-owned-run")
            path.unlink()
        self.helpers.assert_not_called()

    def test_preparation_never_overwrites_existing_destination(self):
        self.destination.mkdir()
        with self.assertRaisesRegex(ValueError, "Preserve the existing"):
            self.invoke()
        self.helpers.assert_not_called()

    def test_execution_requires_explicit_previous_run(self):
        self.destination.mkdir()
        for name in ("experiment.json", "prompt-api.json", "preparation.json"):
            (self.destination / name).write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "requires --previous-run"):
            self.invoke("--execute")
        self.helpers.assert_not_called()


if __name__ == "__main__":
    unittest.main()

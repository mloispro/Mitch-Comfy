"""CPU tests of BeautyGRPO preparation/submission guards; no live services/models."""
import builtins
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw, ImageOps


SCRIPT = Path(__file__).with_name("run-upgrade-beautygrpo.py")
spec = importlib.util.spec_from_file_location("beautygrpo_preflight_under_test", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
REAL_SHA = runner.sha
SOURCE_SHA = "4b32845393fbcbf6ea0ca80068c48af10db52bc81909dba9638370bc7ee0a622"
EXTRA_PINS = {
    "text_encoders/clip_l.safetensors": "660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd",
    "vae/ae.safetensors": "afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38",
}


class BeautyGRPOMainGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="beautygrpo-unit-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "workspace"
        self.comfy = Path(self.temporary.name) / "ComfyUI"
        self.work = self.root / "work/upgrade-high-20260907"
        (self.work / "models").mkdir(parents=True)
        (self.comfy / "input").mkdir(parents=True)
        self.destination = self.work / "beautygrpo-mirror-author"
        self.source = self.root / "datasets/mitch-identity-stills-v3/validation/val_02_body_mirror_sleeveless.jpg"
        self.source.parent.mkdir(parents=True)
        picture = Image.new("RGB", (2992, 2992), (24, 38, 67))
        drawing = ImageDraw.Draw(picture)
        drawing.rectangle((0, 0, 1495, 1495), fill=(220, 35, 20))
        drawing.rectangle((1496, 0, 2991, 1495), fill=(20, 210, 55))
        drawing.rectangle((0, 1496, 1495, 2991), fill=(25, 50, 215))
        exif = Image.Exif()
        exif[274] = 6
        picture.save(self.source, quality=94, exif=exif)
        picture.close()
        self.staged = self.comfy / "input/mitch-beautygrpo-mirror-pil-bilinear-4b328453.png"
        self.models = [{"target": target, "installed": str(self.comfy / "models" / target), "sha256": digest}
            for target, digest in (
                ("diffusion_models/flux1-kontext-dev.safetensors", "base-pin"),
                ("loras/beautygrpo/BeautyGRPO.safetensors", "adapter-pin"),
                ("text_encoders/t5xxl_fp16.safetensors", "t5-pin"))]
        (self.work / "models/verified-download.json").write_text(json.dumps({"models": self.models}), encoding="utf-8")
        self.hashes = {Path(item["installed"]): item["sha256"] for item in self.models}
        self.hashes.update({self.comfy / "models" / relative: digest for relative, digest in EXTRA_PINS.items()})
        self.hashes[self.source] = SOURCE_SHA
        self.hashes[SCRIPT] = "runner-implementation-pin"
        self.config = {"base_shift": .5, "max_shift": 1.15, "base_image_seq_len": 256,
            "max_image_seq_len": 4096, "use_dynamic_shifting": True}
        self.config_path = self.work / "scheduler-config.json"
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        self.info = {kind: {"input": {"required": {}}} for kind in (
            "UNETLoader", "LoraLoaderModelOnly", "DualCLIPLoader", "VAELoader", "LoadImage",
            "VAEEncode", "CLIPTextEncode", "ReferenceLatent", "FluxGuidance",
            "ConditioningZeroOut", "KSampler", "VAEDecode", "SaveImage")}
        for kind, field, names in (
            ("UNETLoader", "unet_name", ["flux1-kontext-dev.safetensors"]),
            ("LoraLoaderModelOnly", "lora_name", ["beautygrpo\\BeautyGRPO.safetensors"]),
            ("DualCLIPLoader", "clip_name1", ["clip_l.safetensors", "t5xxl_fp16.safetensors"]),
            ("DualCLIPLoader", "clip_name2", ["clip_l.safetensors", "t5xxl_fp16.safetensors"]),
            ("VAELoader", "vae_name", ["ae.safetensors"]),
        ):
            self.info[kind]["input"]["required"][field] = [names]
        self.submissions = []
        self.submit_error = None
        self.coverage = {"native_loader_patches": 342, "consumed_tensors": 684, "rank": 32, "alpha": 32}
        self.idle_mock = Mock(return_value={"workers": "mock-only", "hardware": "mock-only"})
        self.compatibility_mock = Mock(return_value=self.coverage)
        hf = ModuleType("huggingface_hub")
        hf.hf_hub_download = Mock(return_value=str(self.config_path))
        self.download_mock = hf.hf_hub_download
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.multiple(runner, ROOT=self.root, COMFY=self.comfy, WORK=self.work,
            sha=self.fake_sha, api=self.fake_api, idle=self.idle_mock, adapter_compatibility=self.compatibility_mock))
        self.stack.enter_context(patch.dict(sys.modules, {"huggingface_hub": hf}))

    def fake_sha(self, path):
        path = Path(path)
        return self.hashes[path] if path in self.hashes else REAL_SHA(path)

    def fake_api(self, port, route, body=None):
        self.assertEqual(port, 8188)
        if route == "object_info":
            return copy.deepcopy(self.info)
        if route == "prompt":
            self.submissions.append(body)
            if self.submit_error:
                raise self.submit_error
            return {"prompt_id": "test-only-job", "node_errors": {}}
        self.fail("Unexpected API operation: " + route)

    def invoke(self, *arguments):
        with patch.object(sys, "argv", [str(SCRIPT), *arguments]), contextlib.redirect_stdout(io.StringIO()):
            runner.main()

    def test_existing_attempt_markers_block_submission_without_gpu_preflight(self):
        for filename in ("submission-intent.json", "submission.json"):
            with self.subTest(filename=filename):
                self.destination.mkdir(exist_ok=True)
                marker = self.destination / filename
                marker.write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Submission already attempted"):
                    self.invoke("--execute")
                self.assertEqual(self.submissions, [])
                self.idle_mock.assert_not_called()
                marker.unlink()

    def test_prepared_manifest_mismatch_blocks_submission_and_is_preserved(self):
        self.invoke()
        path = self.destination / "experiment.json"
        manifest = json.loads(path.read_text())
        manifest["source"]["original_sha256"] = "changed-source-provenance"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        preserved = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Prepared manifest differs"):
            self.invoke("--execute")
        self.assertEqual(path.read_bytes(), preserved)
        self.assertEqual(self.submissions, [])
        self.assertFalse((self.destination / "submission-intent.json").exists())

    def test_prepared_standalone_graph_mismatch_blocks_submission(self):
        self.invoke()
        path = self.destination / "prompt-api.json"
        graph = json.loads(path.read_text())
        graph["12"]["inputs"]["seed"] = 99
        path.write_text(json.dumps(graph), encoding="utf-8")
        preserved = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Prepared standalone graph differs"):
            self.invoke("--execute")
        self.assertEqual(path.read_bytes(), preserved)
        self.assertEqual(self.submissions, [])

    def test_preparation_uses_exif_oriented_pil_bilinear_whole_frame(self):
        original_bytes = self.source.read_bytes()
        self.invoke()
        with Image.open(self.source) as source:
            expected = ImageOps.exif_transpose(source).convert("RGB").resize((1024, 1024), Image.Resampling.BILINEAR)
        expected.info.clear()
        with Image.open(self.staged) as staged:
            self.assertEqual(staged.size, (1024, 1024))
            self.assertEqual(staged.convert("RGB").tobytes(), expected.tobytes())
            self.assertNotIn(274, staged.getexif())
            # Orientation6 rotates original bottom-left blue into top-left.
            red, green, blue = staged.getpixel((20, 20))
            self.assertGreater(blue, red + 100)
            self.assertGreater(blue, green + 100)
        self.assertEqual(self.source.read_bytes(), original_bytes)
        manifest = json.loads((self.destination / "experiment.json").read_text())
        self.assertEqual(manifest["source"]["preparation"]["exif_orientation"], 6)
        self.assertFalse(manifest["source"]["preparation"]["crop"])
        self.assertFalse(manifest["source"]["preparation"]["face_edits"])
        self.assertEqual(manifest["source"]["sha256"], REAL_SHA(self.staged))
        self.assertEqual(self.submissions, [])

    def test_changed_genuine_source_rejected_before_staging(self):
        self.hashes[self.source] = "changed-source"
        with self.assertRaisesRegex(ValueError, "Genuine source changed"):
            self.invoke()
        self.assertFalse(self.staged.exists())
        self.assertEqual(self.submissions, [])

    def test_conflicting_staged_photo_is_not_overwritten(self):
        self.staged.write_bytes(b"preexisting-photo")
        with self.assertRaisesRegex(ValueError, "PIL-prepared source mismatch"):
            self.invoke()
        self.assertEqual(self.staged.read_bytes(), b"preexisting-photo")
        self.assertEqual(self.submissions, [])

    @unittest.skipUnless(os.name == "nt", "Windows rename provides the runner's no-overwrite guarantee")
    def test_concurrently_created_staged_photo_is_not_overwritten(self):
        original_rename = Path.rename
        def concurrent_install(path, target):
            self.assertEqual(Path(target), self.staged)
            self.staged.write_bytes(b"concurrent-photo")
            return original_rename(path, target)
        with patch.object(Path, "rename", autospec=True, side_effect=concurrent_install) as rename_mock:
            with self.assertRaises(FileExistsError):
                self.invoke()
            rename_mock.assert_called_once()
        self.assertEqual(self.staged.read_bytes(), b"concurrent-photo")
        self.assertEqual(self.submissions, [])

    def test_successful_prepared_submission_is_once_only(self):
        self.invoke()
        original_manifest = (self.destination / "experiment.json").read_bytes()
        self.invoke("--execute")
        self.assertEqual(len(self.submissions), 1)
        self.assertEqual((self.destination / "experiment.json").read_bytes(), original_manifest)
        intent = json.loads((self.destination / "submission-intent.json").read_text())
        self.assertEqual(intent["client_id"], self.submissions[0]["client_id"])
        self.assertEqual(self.submissions[0]["prompt"]["3"]["inputs"]["clip_name1"], "clip_l.safetensors")
        with self.assertRaisesRegex(ValueError, "Submission already attempted"):
            self.invoke("--execute")
        self.assertEqual(len(self.submissions), 1)

    def test_uncertain_network_result_leaves_intent_and_blocks_retry(self):
        self.invoke()
        self.submit_error = TimeoutError("response lost after request")
        with self.assertRaises(TimeoutError):
            self.invoke("--execute")
        self.assertEqual(len(self.submissions), 1)
        self.assertTrue((self.destination / "submission-intent.json").exists())
        self.assertFalse((self.destination / "submission.json").exists())
        with self.assertRaisesRegex(ValueError, "Submission already attempted"):
            self.invoke("--execute")
        self.assertEqual(len(self.submissions), 1)

    def test_intent_created_after_preflight_blocks_concurrent_submission(self):
        self.invoke()
        calls = 0
        marker = self.destination / "submission-intent.json"
        def concurrent_intent(_previous):
            nonlocal calls
            calls += 1
            if calls == 2:
                marker.write_text('{"client_id":"other-owner"}', encoding="utf-8")
            return {"workers": "mock-only", "hardware": "mock-only"}
        self.idle_mock.side_effect = concurrent_intent
        with self.assertRaises(FileExistsError):
            self.invoke("--execute")
        self.assertEqual(json.loads(marker.read_text())["client_id"], "other-owner")
        self.assertEqual(self.submissions, [])
        self.assertFalse((self.destination / "submission.json").exists())


class BeautyGRPOAdapterHeaderTests(unittest.TestCase):
    """Shape-only fakes exercise all342 target checks without importing Torch/Comfy."""

    def setUp(self):
        self.base_path = Path("mock-base.safetensors")
        self.lora_path = Path("mock-adapter.safetensors")
        self.config = {"transformer.r": 32, "transformer.lora_alpha": 32,
            "transformer.use_rslora": False, "transformer.use_dora": False}
        self.base = {"block_" + str(index) + ".weight": {"shape": [8, 8]} for index in range(342)}
        self.mapping = {"block_" + str(index) + ".weight": "diffusion_model.block_" + str(index) + ".weight" for index in range(342)}
        self.aliases = {"transformer.block_" + str(index): target for index, target in enumerate(self.mapping.values())}
        self.tensors = {"transformer.block_" + str(index) + suffix: SimpleNamespace(shape=shape)
            for index in range(342) for suffix, shape in ((".lora_A.weight", (32, 8)), (".lora_B.weight", (8, 32)))}
        comfy = ModuleType("comfy")
        comfy.__path__ = []
        cli = ModuleType("comfy.cli_args")
        cli.args = SimpleNamespace(cpu=False)
        utils = ModuleType("comfy.utils")
        utils.flux_to_diffusers = Mock(side_effect=lambda *_args, **_kwargs: self.mapping)
        lora = ModuleType("comfy.lora")
        lora.model_lora_keys_unet = Mock(side_effect=lambda model, _keys: self.aliases)
        adapter_class = type("LoRAAdapter", (), {})
        lora.load_lora = Mock(side_effect=lambda _tensors, keys: {key: adapter_class() for key in keys})
        model_base = ModuleType("comfy.model_base")
        module_class = type("Module", (), {"__init__": lambda _self: None})
        model_base.Flux = type("Flux", (module_class,), {})
        torch = ModuleType("torch")
        torch.nn = SimpleNamespace(Module=module_class)
        torch.cuda = SimpleNamespace(is_available=Mock(return_value=False), is_initialized=Mock(return_value=False))
        safe = ModuleType("safetensors")
        safe.__path__ = []
        safe_torch = ModuleType("safetensors.torch")
        safe_torch.load_file = Mock(side_effect=lambda *_args, **_kwargs: self.tensors)
        comfy.cli_args, comfy.utils, comfy.lora, comfy.model_base = cli, utils, lora, model_base
        safe.torch = safe_torch
        self.load_file_mock = safe_torch.load_file
        self.lora_mock = lora.load_lora
        self.torch = torch
        self.modules = {"comfy": comfy, "comfy.cli_args": cli, "comfy.utils": utils,
            "comfy.lora": lora, "comfy.model_base": model_base,
            "safetensors": safe, "safetensors.torch": safe_torch}

    def run_check(self):
        def fake_header(path):
            return self.base if path == self.base_path else {"__metadata__": {"lora_adapter_metadata": json.dumps(self.config)}}
        original_import = builtins.__import__
        def fake_import(name, *args, **kwargs):
            if name == "torch" or name.startswith("comfy"):
                self.assertEqual(os.environ.get("CUDA_VISIBLE_DEVICES"), "-1")
            if name == "torch":
                return self.torch
            return original_import(name, *args, **kwargs)
        with patch.dict(sys.modules, self.modules), patch.object(sys, "path", list(sys.path)), \
                patch.dict(os.environ), patch.object(builtins, "__import__", side_effect=fake_import), \
                patch.object(runner, "header", side_effect=fake_header):
            return runner.adapter_compatibility(self.base_path, self.lora_path)

    def test_preimported_torch_rejected_before_environment_or_model_access(self):
        with patch.dict(sys.modules, {"torch": self.torch}), \
                patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "unit-test-sentinel"}), \
                patch.object(runner, "header") as header_mock:
            with self.assertRaisesRegex(RuntimeError, "fresh process before importing torch"):
                runner.adapter_compatibility(self.base_path, self.lora_path)
            self.assertEqual(os.environ["CUDA_VISIBLE_DEVICES"], "unit-test-sentinel")
            header_mock.assert_not_called()
        self.load_file_mock.assert_not_called()

    def test_all_rank32_pairs_are_consumed(self):
        report = self.run_check()
        self.assertEqual(report["native_loader_patches"], 342)
        self.assertEqual(report["consumed_tensors"], 684)
        self.assertTrue(report["base_dimensions_match"])
        self.assertIs(report["cuda_initialized"], False)
        self.load_file_mock.assert_called_once_with(str(self.lora_path), device="cpu")

    def test_cuda_available_or_initialized_is_rejected(self):
        for flag in (self.torch.cuda.is_available, self.torch.cuda.is_initialized):
            flag.return_value = True
            with self.assertRaisesRegex(RuntimeError, "must not initialize CUDA"):
                self.run_check()
            flag.return_value = False

    def test_nonstandard_scaling_rejected_before_tensor_load(self):
        for key, value in (("transformer.lora_alpha", 64), ("transformer.use_rslora", True),
                           ("transformer.use_dora", True), ("transformer.rank_pattern", {"x": 16})):
            with self.subTest(key=key), patch.dict(self.config, {key: value}):
                with self.assertRaisesRegex(ValueError, "scaling does not match"):
                    self.run_check()
        self.load_file_mock.assert_not_called()

    def test_dimension_mismatch_and_extra_tensor_are_rejected(self):
        self.tensors["transformer.block_0.lora_A.weight"] = SimpleNamespace(shape=(32, 7))
        with self.assertRaisesRegex(ValueError, "shape mismatch"):
            self.run_check()
        self.tensors["transformer.block_0.lora_A.weight"] = SimpleNamespace(shape=(32, 8))
        self.tensors["unexpected.bias"] = SimpleNamespace(shape=(8,))
        with self.assertRaisesRegex(ValueError, "Incomplete released adapter coverage"):
            self.run_check()

    def test_native_alias_mismatch_and_skipped_patch_are_rejected(self):
        self.aliases["transformer.block_0"] = "wrong-native-target"
        with self.assertRaisesRegex(ValueError, "Native loader alias differs"):
            self.run_check()
        self.aliases["transformer.block_0"] = self.mapping["block_0.weight"]
        self.lora_mock.side_effect = lambda _tensors, _keys: {}
        with self.assertRaisesRegex(ValueError, "skipped adapter targets"):
            self.run_check()

    def test_packed_attention_offset_cannot_escape_weight_shape(self):
        target = ("diffusion_model.block_0.weight", (0, 4, 8))
        self.mapping["block_0.weight"] = target
        self.aliases["transformer.block_0"] = target
        with self.assertRaisesRegex(ValueError, "Bad packed attention offset"):
            self.run_check()


if __name__ == "__main__":
    unittest.main()

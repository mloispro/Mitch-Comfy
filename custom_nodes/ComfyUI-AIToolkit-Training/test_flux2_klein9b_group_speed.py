"""CPU behavioral tests of the actual Group seams and separate Speed node.

The real generate method is compiled with test doubles for model/image I/O.
No Comfy worker, CUDA, model, reference photo, or external service is used.
"""
from __future__ import annotations

import ast
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
ENGINE = HERE / "flux2_klein9b_group_scene_studio.py"
SPEED = HERE / "flux2_klein9b_group_speed.py"
CACHE = HERE / "flux2_klein9b_guarded_cache.py"


class Image:
    def __getitem__(self, key):
        return self


def harness(output, barrier=None, cache_stats=None):
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    engine = ModuleType("group_speed_test.flux2_klein9b_group_scene_studio")
    engine.__file__ = str(ENGINE)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    setattr(engine, target.id, value)
    identity_tree = ast.parse((HERE / "flux2_klein9b_mitch_identity_studio.py").read_text(encoding="utf-8"))
    phone_tree = ast.parse((HERE / "flux2_klein9b_smartphone_style.py").read_text(encoding="utf-8"))
    for node in [*identity_tree.body, *phone_tree.body]:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and not hasattr(engine, target.id):
                    setattr(engine, target.id, value)
    calls = []
    identity_image = Image()
    class Loader:
        def load_unet(self, name, dtype):
            model = {"original": object()}
            calls.append(("model", model))
            return (model,)
        def load_lora_model_only(self, model, name, strength):
            calls.append(("lora", name, strength))
            return (model,)
        def load_clip(self, *args):
            return ("clip",)
        def load_vae(self, *args):
            return ("vae",)
        def load_image(self, name):
            calls.append(("identity_image", name))
            return (identity_image, None)
    class TextEncode:
        def encode(self, clip, text):
            return ([{"text": text, "references": []}],)
    class VAEEncode:
        def encode(self, vae, image):
            return ({"samples": image},)
    class SaveImage:
        def save_images(self, image, prefix, extra_pnginfo):
            path = Path(output) / prefix
            path.parent.mkdir(parents=True, exist_ok=True)
            calls.append(("save", prefix, copy.deepcopy(extra_pnginfo)))
            return {"ui": {"images": [{"filename": "test.png", "subfolder": str(path.parent), "type": "output"}]}}
    def condition_set(condition, values, append):
        cloned = copy.deepcopy(condition)
        cloned[0]["references"] += values["reference_latents"]
        return cloned
    class Guider:
        @staticmethod
        def execute(model, positive, negative, guidance):
            calls.append(("guider", model, positive, negative, guidance))
            if barrier:
                barrier.wait(timeout=5)
            return ({"model": model},)
    class Sampler:
        @staticmethod
        def execute(noise, guider, sampler, sigmas, latent):
            calls.append(("sampler", guider["model"], sampler, sigmas, latent))
            return ("sampled",)
    scope = engine.__dict__
    scope.update(
        json=json, time=time, datetime=datetime, Path=Path,
        comfy_nodes=SimpleNamespace(UNETLoader=Loader, LoraLoaderModelOnly=Loader,
            CLIPLoader=Loader, VAELoader=Loader, LoadImage=Loader,
            CLIPTextEncode=TextEncode, VAEEncode=VAEEncode,
            VAEDecode=lambda: SimpleNamespace(decode=lambda *args: ("photo",)), SaveImage=SaveImage),
        node_helpers=SimpleNamespace(conditioning_set_values=condition_set),
        folder_paths=SimpleNamespace(get_output_directory=lambda: output),
        baseline=SimpleNamespace(_require_model=lambda *args: None, _resize_reference=lambda image, pixels: (image, pixels)),
        _assert_rtx3090=lambda: {"name": "RTX3090"},
        _lora_path=lambda: Path("identity.safetensors"),
        _identity_reference_path=lambda: Path("genuine.jpg"),
        verify_smartphone_style_lora=lambda: "phone.safetensors",
        verify_turbo_lora=lambda: "turbo.safetensors",
        sampling_settings=lambda enabled, steps, guidance: (8, 1.0) if enabled else (steps, guidance),
        compose_group_prompt=lambda prompt, polish=False: prompt,
        apply_smartphone_style_trigger=lambda prompt: prompt,
        build_face_free_layout=lambda *args: (Image(), {"face_interiors_removed": True}),
        smartphone_style_report=lambda: {"name": "phone"},
        turbo_mode_report=lambda enabled, *args: {"enabled": enabled},
        CFGGuider=Guider, SamplerCustomAdvanced=Sampler,
        KSamplerSelect=SimpleNamespace(execute=lambda name: (name,)),
        Flux2Scheduler=SimpleNamespace(execute=lambda *args: (args,)),
        RandomNoise=SimpleNamespace(execute=lambda seed: (seed,)),
        EmptyFlux2LatentImage=SimpleNamespace(execute=lambda *args: (args,)),
    )
    class_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Flux2Klein9BMitchGroupSceneStudioV1")
    exec(compile(ast.Module(body=[class_node], type_ignores=[]), str(ENGINE), "exec"), scope)
    native_class = engine.Flux2Klein9BMitchGroupSceneStudioV1
    class Visual(native_class):
        def generate(self, **kwargs):
            kwargs.pop("scene_preset")
            kwargs["source_scene"] = Image()
            return super().generate(**kwargs)
    fake_cache = ModuleType("group_speed_test.flux2_klein9b_guarded_cache")
    fake_cache.__file__ = str(CACHE)
    def apply_cache(model, **kwargs):
        observed = copy.deepcopy(cache_stats if cache_stats is not None else {
            "unique_steps": 50, "cache_hits": 13, "guard_failures": [], "disabled_reason": None,
            "session_id": str(id(model)),
        })
        wrapped = {"wrapped": model}
        calls.append(("cache", model, wrapped, observed, kwargs))
        return wrapped, observed
    fake_cache.apply = apply_cache
    manifest = json.loads((HERE / "web/assets/scene-presets/manifest.json").read_text(encoding="utf-8"))
    records = manifest["group"]
    presets = {item["label"]: {k: v for k, v in item.items() if k != "label"} for item in records}
    modules = {
        "group_speed_test": ModuleType("group_speed_test"),
        engine.__name__: engine,
        fake_cache.__name__: fake_cache,
        "group_speed_test.flux2_klein9b_group_scene_studio_visual_presets": SimpleNamespace(Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11=Visual),
        "group_speed_test.flux2_klein9b_scene_presets": SimpleNamespace(GROUP_SCENE_PRESETS=presets),
    }
    spec = importlib.util.spec_from_file_location("group_speed_test.flux2_klein9b_group_speed", SPEED)
    speed = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(speed)
    return engine, speed, calls


def generate_original(engine, seed=8675412):
    return engine.Flux2Klein9BMitchGroupSceneStudioV1().generate(
        Image(), "original prompt", 0.5, 0.44, 0.92, False, False, seed)


class GroupSpeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_original_path_keeps_recipe_model_and_report(self):
        engine, speed, calls = harness(self.temp.name)
        result = generate_original(engine)
        report = json.loads(result["result"][-1])
        self.assertNotIn("sampling_adapter", report)
        self.assertEqual(report["purpose"], "flux2_klein9b_mitch_group_scene_studio_v1")
        self.assertTrue(result["result"][-2].startswith(engine.OUTPUT_ROOT + "/"))
        self.assertEqual((report["steps"], report["guidance"], report["width"], report["height"]), (50, 4.0, 832, 1216))
        self.assertFalse(any(call[0] == "cache" for call in calls))
        original_model = next(call[1] for call in calls if call[0] == "model")
        guider = next(call for call in calls if call[0] == "guider")
        self.assertIs(guider[1], original_model)
        self.assertEqual([latent[1] for latent in guider[2][0]["references"]], [250_000, 1_000_000])
        self.assertEqual([latent[1] for latent in guider[3][0]["references"]], [250_000, 1_000_000])

    def test_speed_path_uses_local_adapter_and_distinct_output(self):
        engine, speed, calls = harness(self.temp.name)
        original_guider, original_sampler = engine.CFGGuider, engine.SamplerCustomAdvanced
        response = speed.Flux2Klein9BGroupLoungeFasterQuality().generate(8675412)
        report = json.loads(response["result"][-1])
        self.assertIs(engine.CFGGuider, original_guider)
        self.assertIs(engine.SamplerCustomAdvanced, original_sampler)
        self.assertTrue(response["result"][-2].startswith(speed.SPEED_OUTPUT_ROOT + "/"))
        self.assertEqual(report["sampling_adapter"]["execution_status"], "cache_completed")
        self.assertEqual(report["purpose"], "production_speed_klein9b_group_lounge_faster_quality")
        self.assertFalse(report["fast_turbo"])
        self.assertFalse(report["appearance_polish"])
        cached = next(call for call in calls if call[0] == "cache")
        self.assertEqual(cached[-1], {"enabled": True, "warmup_steps": 10, "skip_interval": 3})
        self.assertIs(next(call[1] for call in calls if call[0] == "guider"), cached[2])
        embedded = next(call[2] for call in calls if call[0] == "save")
        self.assertIn("sampling_adapter", embedded["flux2_klein9b_mitch_group_scene_studio_v1"])

    def test_same_speed_node_reused_has_fresh_per_call_stats(self):
        engine, speed, calls = harness(self.temp.name)
        node = speed.Flux2Klein9BGroupLoungeFasterQuality()
        node.generate(8675412)
        node.generate(999)
        cache_calls = [call for call in calls if call[0] == "cache"]
        self.assertEqual(len(cache_calls), 2)
        self.assertIsNot(cache_calls[0][3], cache_calls[1][3])
        report = next(call[2] for call in reversed(calls) if call[0] == "save")["flux2_klein9b_mitch_group_scene_studio_v1"]
        self.assertFalse(report["sampling_adapter"]["seed_was_in_three_pair_validation"])

    def test_concurrent_original_and_speed_calls_never_patch_shared_globals(self):
        engine, speed, calls = harness(self.temp.name, barrier=threading.Barrier(2))
        guider, sampler = engine.CFGGuider, engine.SamplerCustomAdvanced
        with ThreadPoolExecutor(max_workers=2) as executor:
            normal = executor.submit(generate_original, engine)
            faster = executor.submit(speed.Flux2Klein9BGroupLoungeFasterQuality().generate, 8675412)
            normal_report = json.loads(normal.result(timeout=8)["result"][-1])
            fast_report = json.loads(faster.result(timeout=8)["result"][-1])
        self.assertNotIn("sampling_adapter", normal_report)
        self.assertIn("sampling_adapter", fast_report)
        self.assertIs(engine.CFGGuider, guider)
        self.assertIs(engine.SamplerCustomAdvanced, sampler)
        models = [call[1] for call in calls if call[0] == "guider"]
        self.assertEqual(sum("wrapped" in model for model in models), 1)

    def test_runtime_fallback_is_explicit_not_approved_or_retried(self):
        engine, speed, calls = harness(self.temp.name, cache_stats={
            "unique_steps": 3, "cache_hits": 0, "guard_failures": ["unknown option"],
            "disabled_reason": "unknown option"})
        response = speed.Flux2Klein9BGroupLoungeFasterQuality().generate(8675412)
        report = json.loads(response["result"][-1])
        self.assertEqual(report["sampling_adapter"]["execution_status"], "cache_guard_fallback_unvalidated")
        self.assertIn("not validated", report["approval_basis"])
        self.assertIn("cache_guard_fallback", response["ui"]["text"][0])
        self.assertEqual(sum(call[0] == "sampler" for call in calls), 1)

    def test_recipe_drift_rejected_before_model_loading(self):
        for changed, value in (("WIDTH", 1024), ("STEPS", 8), ("LORA_STRENGTH", 1.1)):
            engine, speed, calls = harness(self.temp.name)
            setattr(engine, changed, value)
            with self.assertRaisesRegex(RuntimeError, "validated recipe"):
                speed.Flux2Klein9BGroupLoungeFasterQuality().generate(8675412)
            self.assertEqual(calls, [])

    def test_only_seed_is_exposed_no_unsupported_settings(self):
        _, speed, _ = harness(self.temp.name)
        schema = speed.Flux2Klein9BGroupLoungeFasterQuality.INPUT_TYPES()
        self.assertEqual(set(schema), {"required"})
        self.assertEqual(set(schema["required"]), {"seed"})
        for seed in (-1, 2**64, True, "123"):
            self.assertIsNot(speed.Flux2Klein9BGroupLoungeFasterQuality.VALIDATE_INPUTS(seed), True)

    def test_local_sources_have_no_work_or_shared_monkeypatch_dependency(self):
        source = SPEED.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self.assertFalse(isinstance(target, ast.Attribute) and target.attr in ("CFGGuider", "SamplerCustomAdvanced", "forward"))
        self.assertNotIn("sys.path", source)
        self.assertNotIn("work/group-cache", source)
        self.assertNotIn("runpy", source)
        self.assertNotIn("work/group-cache", CACHE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

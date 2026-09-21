"""CPU-only adapter, guard and exact accepted-graph packaging checks."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("speed_guard_under_test", HERE / "flux2_klein9b_speed_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
SPEED = ROOT / "workflows/production-speed"
MANIFEST = ROOT / "config/production-speed-solo-upgrade.json"
SCHEMA = ROOT / "work/9b-readiness-resume-20260907/solo-cocktail-ui/schema-snapshot.json"
UPGRADE_SCHEMA = ROOT / "work/9b-readiness-resume-20260907/upgrade-source-faithful-option/schema-snapshot.json"
TYPE_MAP = {"Flux2Klein9BSpeedUNETLoader": "UNETLoader",
            "Flux2Klein9BSpeedCLIPLoader": "CLIPLoader",
            "Flux2Klein9BSpeedVAELoader": "VAELoader",
            "Flux2Klein9BSpeedSampler": "SamplerCustomAdvanced"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def ui_to_api(ui):
    """Reverse only known schema fields, so dropped edges/widgets cannot hide."""
    schemas = read(UPGRADE_SCHEMA)["schemas"] | read(SCHEMA)["schemas"]
    links = {row[0]: row for row in ui["links"]}
    if len(links) != len(ui["links"]):
        raise ValueError("Duplicate UI link")
    output = {}
    for node in ui["nodes"]:
        if node["type"] == "MarkdownNote":
            continue
        kind = TYPE_MAP.get(node["type"], node["type"])
        schema = schemas[kind]
        fields = schema["input"].get("required", {}) | schema["input"].get("optional", {})
        order = schema["input_order"].get("required", []) + schema["input_order"].get("optional", [])
        widgets = [key for key in order if isinstance(fields[key][0], list)
                   or fields[key][0] in {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}]
        values = node["widgets_values"]
        extra = 1 if kind in {"RandomNoise", "LoadImage"} else 0
        if len(values) != len(widgets) + extra:
            raise ValueError(f"Widget count mismatch: {node['id']}")
        inputs = dict(zip(widgets, values[:len(widgets)]))
        for slot, inp in enumerate(node.get("inputs", [])):
            if inp.get("link") is None:
                continue
            link = links[inp["link"]]
            if link[3:5] != [node["id"], slot]:
                raise ValueError("UI destination edge mismatch")
            inputs[inp["name"]] = [str(link[1]), link[2]]
        output[str(node["id"])] = {"class_type": kind, "inputs": inputs}
    return output


class SpeedGuardTests(unittest.TestCase):
    def setUp(self):
        self.good = {"gpu": "NVIDIA GeForce RTX 3090", "port": 8188, "legacy": False,
                     "cpu": False, "available_ram_gib": 40.0, "available_commit_gib": 40.0}

    def test_expected_worker_admitted(self):
        with patch.object(guard, "_runtime_snapshot", return_value=self.good):
            self.assertEqual(guard.guard_runtime(), self.good)

    def test_wrong_gpu_port_cpu_legacy_and_memory_refused(self):
        for key, value in (("gpu", "NVIDIA GeForce RTX 4070"), ("port", 8189),
                           ("port", 8191), ("cpu", True), ("legacy", True),
                           ("available_ram_gib", 11.9), ("available_commit_gib", 11.9)):
            with self.subTest(key=key, value=value), patch.object(
                    guard, "_runtime_snapshot", return_value=self.good | {key: value}):
                with self.assertRaises(RuntimeError):
                    guard.guard_runtime()

    def test_exact_core_loader_calls_after_guard(self):
        cases = ((guard.Flux2Klein9BSpeedUNETLoader, "UNETLoader", "load_unet", (guard.MODEL_NAME, "fp8_e4m3fn")),
                 (guard.Flux2Klein9BSpeedCLIPLoader, "CLIPLoader", "load_clip", (guard.CLIP_NAME, "flux2", "default")),
                 (guard.Flux2Klein9BSpeedVAELoader, "VAELoader", "load_vae", (guard.VAE_NAME,)))
        for cls, native_name, method, args in cases:
            events = []
            result = (object(),)
            native = Mock()
            getattr(native, method).side_effect = lambda *a: events.append(("load", a)) or result
            modules = {"nodes": types.SimpleNamespace(**{native_name: lambda: native})}
            with self.subTest(cls=cls.__name__), patch.dict(sys.modules, modules), patch.object(
                    guard, "guard_runtime", side_effect=lambda: events.append("guard")):
                self.assertIs(getattr(cls(), method)(*args), result)
                self.assertEqual(events, ["guard", ("load", args)])

    def test_every_loading_branch_fails_before_core_import_or_load(self):
        cases = ((guard.Flux2Klein9BSpeedUNETLoader(), "load_unet", (guard.MODEL_NAME, "fp8_e4m3fn")),
                 (guard.Flux2Klein9BSpeedCLIPLoader(), "load_clip", (guard.CLIP_NAME, "flux2", "default")),
                 (guard.Flux2Klein9BSpeedVAELoader(), "load_vae", (guard.VAE_NAME,)))
        with patch.object(guard, "guard_runtime", side_effect=RuntimeError("wrong worker")), \
                patch.dict(sys.modules, {"nodes": None}):
            for instance, method, args in cases:
                with self.subTest(method=method), self.assertRaisesRegex(RuntimeError, "wrong worker"):
                    getattr(instance, method)(*args)

    def test_submission_validation_checks_cached_loaders_without_disabling_model_cache(self):
        for cls, args in ((guard.Flux2Klein9BSpeedUNETLoader, (guard.MODEL_NAME, "fp8_e4m3fn")),
                          (guard.Flux2Klein9BSpeedCLIPLoader, (guard.CLIP_NAME, "flux2", "default")),
                          (guard.Flux2Klein9BSpeedVAELoader, (guard.VAE_NAME,))):
            self.assertFalse(hasattr(cls, "IS_CHANGED"))
            with patch.object(guard, "guard_runtime", return_value=self.good) as checked:
                self.assertIs(cls.VALIDATE_INPUTS(*args), True)
                self.assertIs(cls.VALIDATE_INPUTS(*args), True)
                self.assertEqual(checked.call_count, 2)
            with patch.object(guard, "guard_runtime", side_effect=RuntimeError("wrong worker")):
                self.assertIn("wrong worker", cls.VALIDATE_INPUTS(*args))

    def test_model_precision_encoder_and_vae_changes_rejected(self):
        cases = ((guard.Flux2Klein9BSpeedUNETLoader, ("another.safetensors", "fp8_e4m3fn")),
                 (guard.Flux2Klein9BSpeedUNETLoader, (guard.MODEL_NAME, "default")),
                 (guard.Flux2Klein9BSpeedCLIPLoader, (guard.CLIP_NAME, "flux2", "cpu")),
                 (guard.Flux2Klein9BSpeedCLIPLoader, (guard.CLIP_NAME, "krea2", "default")),
                 (guard.Flux2Klein9BSpeedVAELoader, ("taef2",)))
        with patch.object(guard, "guard_runtime") as runtime:
            for cls, args in cases:
                self.assertIsInstance(cls.VALIDATE_INPUTS(*args), str)
            runtime.assert_not_called()

    def test_sampler_rechecks_each_run_and_preserves_exact_native_args_results(self):
        events = []
        args = tuple(object() for _ in range(5))
        results = (object(), object())
        native = Mock()
        native.execute.side_effect = lambda *a: events.append(("sample", a)) or results
        module = types.SimpleNamespace(SamplerCustomAdvanced=native)
        with patch.dict(sys.modules, {"comfy_extras": types.ModuleType("comfy_extras"),
                                     "comfy_extras.nodes_custom_sampler": module}), patch.object(
                guard, "guard_runtime", side_effect=lambda: events.append("guard")):
            self.assertEqual(guard.Flux2Klein9BSpeedSampler().sample(*args), results)
        self.assertEqual(events, ["guard", ("sample", args)])
        self.assertTrue(math.isnan(guard.Flux2Klein9BSpeedSampler.IS_CHANGED()))

    def test_sampler_guard_prevents_native_execution(self):
        with patch.object(guard, "guard_runtime", side_effect=RuntimeError("headroom")), \
                patch.dict(sys.modules, {"comfy_extras.nodes_custom_sampler": None}):
            with self.assertRaisesRegex(RuntimeError, "headroom"):
                guard.Flux2Klein9BSpeedSampler().sample(*[None] * 5)


class SpeedPackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read(MANIFEST)

    def test_source_ui_payloads_and_new_packages_hash_locked(self):
        for recipe in self.manifest["recipes"].values():
            for kind in ("source_ui", "source_payload", "package"):
                pin = recipe[kind]
                self.assertEqual(Path(pin["path"]).stat().st_size, pin["bytes"])
                self.assertEqual(sha(pin["path"]), pin["sha256"])

    def test_default_genuine_reference_bytes_match_frozen_acceptance(self):
        for recipe in self.manifest["recipes"].values():
            for pin in recipe["references"]:
                self.assertEqual(Path(pin["path"]).name, pin["image"])
                self.assertEqual(Path(pin["path"]).stat().st_size, pin["bytes"])
                self.assertEqual(sha(pin["path"]), pin["sha256"])

    def test_both_ui_graphs_exact_except_declared_guards_and_output_prefix(self):
        for name, recipe in self.manifest["recipes"].items():
            with self.subTest(recipe=name):
                ui = read(SPEED / recipe["file"])
                source = read(recipe["source_payload"]["path"])["prompt"]
                self.assertNotEqual(ui["id"], read(recipe["source_ui"]["path"])["id"])
                actual = ui_to_api(ui)
                self.assertEqual(len(actual), recipe["execution_nodes"])
                self.assertEqual(actual[recipe["save_node"]]["inputs"]["filename_prefix"], recipe["prefix"])
                actual[recipe["save_node"]]["inputs"]["filename_prefix"] = source[recipe["save_node"]]["inputs"]["filename_prefix"]
                self.assertEqual(actual, source)
                self.assertEqual({n["type"] for n in ui["nodes"]} & set(TYPE_MAP), set(TYPE_MAP))
                self.assertFalse({"UNETLoader", "CLIPLoader", "VAELoader", "SamplerCustomAdvanced"}
                                 & {n["type"] for n in ui["nodes"]})

    def test_manifest_reference_roles_match_graph_nodes_and_default_sampling(self):
        for recipe in self.manifest["recipes"].values():
            api = ui_to_api(read(SPEED / recipe["file"]))
            for ref in recipe["references"]:
                self.assertEqual(api[ref["node"]]["inputs"]["image"], ref["image"])
            latent = next(n["inputs"] for n in api.values() if n["class_type"] == "EmptyFlux2LatentImage")
            scheduler = next(n["inputs"] for n in api.values() if n["class_type"] == "Flux2Scheduler")
            noise = next(n["inputs"] for n in api.values() if n["class_type"] == "RandomNoise")
            self.assertEqual(noise["noise_seed"], recipe["defaults"]["seed"])
            self.assertEqual(latent["batch_size"], 1)
            for field in ("width", "height"):
                self.assertEqual(latent[field], recipe["defaults"][field])
                self.assertEqual(scheduler[field], latent[field])
            self.assertEqual(scheduler["steps"], 8)

    def test_prompt_and_source_editability_retained_and_limited_in_notes(self):
        for recipe in self.manifest["recipes"].values():
            ui = read(SPEED / recipe["file"])
            notes = "\n".join(n["widgets_values"][0] for n in ui["nodes"] if n["type"] == "MarkdownNote")
            self.assertIn("UNVALIDATED", notes)
            self.assertIn("8188", notes)
            self.assertTrue(any(n["type"] == "CLIPTextEncode" and n["widgets_values"][0] for n in ui["nodes"]))
            self.assertTrue(any(n["type"] == "LoadImage" for n in ui["nodes"]))


if __name__ == "__main__":
    unittest.main()

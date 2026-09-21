"""CPU-only regression tests; no Comfy imports, checkpoints or GPU access."""
import copy
import json
import sys
import types
import unittest
from unittest.mock import patch

import torch

from flux2_klein9b_guarded_cache import GuardedForwardCache, Unsupported, apply


SCHEDULE = torch.linspace(1.0, 0.0, 51)


def arguments(step, branch=(0,), text=None, refs=None):
    n = len(branch)
    t = SCHEDULE[step - 1:step].repeat(n)
    return {
        "input": torch.full((n, 2, 2, 2), 1.0 + step / 100),
        "timestep": t,
        "cond_or_uncond": list(branch),
        "c": {
            "c_crossattn": torch.tensor(branch).float().reshape(n, 1, 1) if text is None else text,
            "ref_latents": [torch.ones(n, 2, 2, 2), torch.full((n, 2, 2, 2), 2.0)] if refs is None else refs,
            "guidance": torch.full((n,), 3.5),
            "transformer_options": {
                "cond_or_uncond": list(branch), "uuids": [f"branch-{b}" for b in branch],
                "sigmas": t[:1], "sample_sigmas": SCHEDULE.clone(),
            },
        },
    }


class FakeModel:
    def __init__(self):
        self.calls = 0

    def predict(self, x, timestep, **c):
        self.calls += 1
        # Cond velocity2; uncond velocity5. Replaying one into the other is visible.
        velocity = c["c_crossattn"].reshape(-1, 1, 1, 1) * 3 + 2
        return x - timestep.reshape(-1, 1, 1, 1) * velocity


def run_steps(wrapper, model, through=50, partition=((0,), (1,))):
    outputs = []
    for step in range(1, through + 1):
        for branch in partition:
            args = arguments(step, branch)
            result = wrapper(model.predict, args)
            expected = FakeModel().predict(args["input"], args["timestep"], **args["c"])
            torch.testing.assert_close(result, expected, atol=2e-6, rtol=1e-6)
            outputs.append(result)
    return outputs


class GuardedCacheTests(unittest.TestCase):
    def test_separate_cfg_never_mixes_branches(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model)
        self.assertEqual(wrapper.stats["cache_hits"], 26)
        self.assertEqual(model.calls, 74)
        self.assertEqual(wrapper.stats["unique_steps"], 50)
        self.assertEqual(wrapper.stats["hit_steps"], list(range(13, 50, 3)))
        self.assertEqual(wrapper.stats["guard_failures"], [])

    def test_joint_cfg_both_orders(self):
        for group in ((0, 1), (1, 0)):
            wrapper, model = GuardedForwardCache(), FakeModel()
            run_steps(wrapper, model, partition=(group,))
            self.assertEqual(wrapper.stats["cache_hits"], 13)
            self.assertEqual(model.calls, 37)

    def test_declared_interval4_refinement_preserves_partitions(self):
        for partition in (((0,), (1,)), ((0, 1),), ((1, 0),)):
            wrapper, model = GuardedForwardCache(skip_interval=4), FakeModel()
            run_steps(wrapper, model, partition=partition)
            expected_hits = 9 * len(partition)
            self.assertEqual(wrapper.stats["cache_hits"], expected_hits)
            self.assertEqual(model.calls, 50 * len(partition) - expected_hits)
            self.assertEqual(wrapper.stats["hit_steps"], list(range(14, 50, 4)))
            self.assertNotIn(50, wrapper.stats["hit_steps"])
            self.assertEqual(wrapper.stats["guard_failures"], [])

    def test_undeclared_schedules_rejected(self):
        for interval in (1, 2, 5):
            with self.assertRaises(Unsupported):
                GuardedForwardCache(skip_interval=interval)
        with self.assertRaises(Unsupported):
            GuardedForwardCache(warmup_steps=9)

    def test_disabled_is_exact_passthrough(self):
        wrapper, model = GuardedForwardCache(enabled=False), FakeModel()
        run_steps(wrapper, model)
        self.assertEqual(model.calls, 100)
        self.assertEqual(wrapper.stats["cache_hits"], 0)

    def test_genuine_tensor_content_not_pointer_identity(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model, 13)
        self.assertEqual(wrapper.stats["cache_hits"], 2)

    def test_reference_changes_disable_before_hit(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model, 12)
        args = arguments(13)
        args["c"]["ref_latents"][1][0, 0, 0, 0] = 9
        wrapper(model.predict, args)
        self.assertIn("content changed", wrapper.stats["disabled_reason"])
        self.assertEqual(wrapper.stats["cache_hits"], 0)

    def test_text_change_disables(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model, 12)
        args = arguments(13)
        args["c"]["c_crossattn"] += 1
        wrapper(model.predict, args)
        self.assertIn("content changed", wrapper.stats["disabled_reason"])

    def test_inplace_old_reference_mutation_cannot_mutate_snapshot(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        first = arguments(1)
        wrapper(model.predict, first)
        first["c"]["ref_latents"][0].fill_(99)
        wrapper(model.predict, arguments(1, (1,)))
        wrapper(model.predict, arguments(2))
        self.assertIsNone(wrapper.stats["disabled_reason"])

    def test_cfg_partition_change_disables(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model, 12)
        wrapper(model.predict, arguments(13, (0, 1)))
        self.assertIn("partition", wrapper.stats["disabled_reason"])

    def test_repeated_timestep_same_branch_disables(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        args = arguments(1)
        wrapper(model.predict, args)
        wrapper(model.predict, args)
        self.assertIn("repeated", wrapper.stats["disabled_reason"])

    def test_restart_increase_disables_and_clears(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model, 13)
        wrapper(model.predict, arguments(1))
        self.assertIn("nonmonotonic", wrapper.stats["disabled_reason"])
        self.assertEqual(wrapper.entries, {})

    def test_new_session_has_no_stale_cache(self):
        one, model = GuardedForwardCache(), FakeModel()
        run_steps(one, model, 13)
        two = GuardedForwardCache()
        run_steps(two, model, 1)
        self.assertNotEqual(one.stats["session_id"], two.stats["session_id"])
        self.assertEqual(two.stats["cache_hits"], 0)

    def test_missing_cfg_branch_disables(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        wrapper(model.predict, arguments(1))
        wrapper(model.predict, arguments(2))
        self.assertIn("incomplete", wrapper.stats["disabled_reason"])

    def test_schedule_session_change_disables(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model, 12)
        args = arguments(13)
        args["c"]["transformer_options"]["sample_sigmas"][20] -= 0.001
        wrapper(model.predict, args)
        self.assertIn("schedule/session", wrapper.stats["disabled_reason"])

    def test_lora_guard_change_disables(self):
        state = {"same": True}
        wrapper, model = GuardedForwardCache(lambda: state["same"]), FakeModel()
        run_steps(wrapper, model, 12)
        state["same"] = False
        wrapper(model.predict, arguments(13))
        self.assertIn("LoRA", wrapper.stats["disabled_reason"])

    def test_unknown_options_disable(self):
        for key, value in (("unverified_node", 1), ("patches", {"foo": [lambda: None]})):
            wrapper, model = GuardedForwardCache(), FakeModel()
            args = arguments(1)
            args["c"]["transformer_options"][key] = value
            wrapper(model.predict, args)
            self.assertIsNotNone(wrapper.stats["disabled_reason"])

    def test_model_error_propagates_once(self):
        calls = []
        def broken(x, timestep, **c):
            calls.append(1)
            raise RuntimeError("cancelled or broken")
        with self.assertRaisesRegex(RuntimeError, "cancelled"):
            GuardedForwardCache()(broken, arguments(1))
        self.assertEqual(len(calls), 1)

    def test_reject_existing_wrapper_without_replacing(self):
        class Patcher:
            model_options = {"model_function_wrapper": object()}
        original = Patcher.model_options["model_function_wrapper"]
        with self.assertRaises(Unsupported):
            apply(Patcher())
        self.assertIs(Patcher.model_options["model_function_wrapper"], original)

    def test_unknown_branch_never_hits(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        args = arguments(1, (2,))
        wrapper(model.predict, args)
        self.assertIn("CFG branch", wrapper.stats["disabled_reason"])
        self.assertEqual(wrapper.stats["cache_hits"], 0)

    def test_nonfinite_output_disables_and_is_not_retried(self):
        calls = []
        def nan_model(x, timestep, **c):
            calls.append(1)
            return torch.full_like(x, float("nan"))
        wrapper = GuardedForwardCache()
        wrapper(nan_model, arguments(1))
        self.assertIn("nonfinite", wrapper.stats["disabled_reason"])
        self.assertEqual(calls, [1])

    def test_stats_remain_json_serializable(self):
        wrapper, model = GuardedForwardCache(), FakeModel()
        run_steps(wrapper, model)
        json.dumps(wrapper.stats)

    def test_apply_uses_clone_only_and_preserves_static_patches(self):
        class CONST:
            def calculate_denoised(self, sigma, velocity, x):
                return x - velocity * sigma
        comfy = types.ModuleType("comfy")
        sampling = types.ModuleType("comfy.model_sampling")
        sampling.CONST = CONST
        comfy.model_sampling = sampling
        diffusion = type("Flux", (), {"__module__": "comfy.ldm.flux.model"})()
        diffusion.forward = object()
        base = type("Flux2", (), {})()
        base.model_sampling, base.diffusion_model = CONST(), diffusion
        class Patcher:
            def __init__(self):
                self.model_options = {"transformer_options": {}}
                self.model = base
                self.patches = {"identity": [(0.9, "existing weights")], "phone": [(0.25, "existing weights")]}
                self.patches_uuid = "same-patch-id"
                self.hook_patches, self.injections = {}, {}
                self.wrappers, self.additional_models = {}, {}
                self.current_hooks = self.forced_hooks = None
            def clone(self):
                result = copy.copy(self)
                result.model_options = copy.deepcopy(self.model_options)
                return result
            def set_model_unet_function_wrapper(self, wrapper):
                self.model_options["model_function_wrapper"] = wrapper
        original = Patcher()
        original_forward = diffusion.forward
        with patch.dict(sys.modules, {"comfy": comfy, "comfy.model_sampling": sampling}):
            cached, stats = apply(original)
        self.assertIsNot(cached, original)
        self.assertNotIn("model_function_wrapper", original.model_options)
        self.assertIs(diffusion.forward, original_forward)
        self.assertIs(cached.patches, original.patches)
        self.assertIn("model_function_wrapper", cached.model_options)
        self.assertIs(cached.model_options["model_function_wrapper"].stats, stats)
        uncached, baseline_stats = apply(original, enabled=False)
        self.assertNotIn("model_function_wrapper", uncached.model_options)
        self.assertFalse(baseline_stats["enabled"])


if __name__ == "__main__":
    unittest.main()



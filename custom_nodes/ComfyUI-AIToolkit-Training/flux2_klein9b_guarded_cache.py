# Evaluated source: group-cache-20260909, original SHA256
# 8f849c3543746efebb675e5725f4f680d97799fd88207673896476d4b845f9c5.
# Maintained local copy: no runtime dependency on the experiment directory.
"""Experimental CFG-safe Flux velocity replay; NOT Cache-DiT or DBCache.

One apply() call per sampling invocation, after all static LoRAs. No global
state, model-forward mutation, dependency installation, or retry behavior.
Only the existing 50-step, single-image, two-branch Group recipe is supported.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import torch


class Unsupported(ValueError):
    pass


def _meta(t):
    return (tuple(t.shape), str(t.dtype), str(t.device), str(t.layout))


def _snapshot(value):
    if torch.is_tensor(value):
        if value.layout != torch.strided or value.requires_grad:
            raise Unsupported("non-strided or gradient conditioning")
        return value.detach().clone()
    if isinstance(value, dict):
        return {k: _snapshot(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_snapshot(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool, uuid.UUID)):
        return value
    raise Unsupported(f"unsupported conditioning value: {type(value).__name__}")


def _equal(a, b):
    if torch.is_tensor(a) or torch.is_tensor(b):
        return (torch.is_tensor(a) and torch.is_tensor(b)
                and _meta(a) == _meta(b) and torch.equal(a, b))
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    return a == b


def _signature(value):
    """Structural key; exact detached content snapshots also must match."""
    if torch.is_tensor(value):
        return ("tensor", _meta(value))
    if isinstance(value, dict):
        return tuple((k, _signature(value[k])) for k in sorted(value))
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_signature(v) for v in value))
    if value is None or isinstance(value, (str, int, float, bool, uuid.UUID)):
        return value
    raise Unsupported("unsupported cache-key value")


def _nonempty(value):
    if isinstance(value, dict):
        return any(_nonempty(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return bool(value)
    return value is not None


@dataclass
class Entry:
    conditioning: dict
    velocity: torch.Tensor | None = None
    computed_step: int = 0


class GuardedForwardCache:
    """Wraps Comfy apply_model, keeping each CFG grouping strictly separate."""

    def __init__(self, model_guard=lambda: True, enabled=True, *, warmup_steps=10, skip_interval=3):
        if warmup_steps != 10 or skip_interval not in (3, 4):
            raise Unsupported("prototype permits only warmup10 and skip3/4")
        self.enabled = bool(enabled)
        self.model_guard = model_guard
        self.entries = {}
        self.schedule = None
        self.sigma = None
        self.seen = set()
        self.model_call_identity = None
        self.stats = {
            "implementation": "guarded_flux_velocity_replay_v1",
            "session_id": str(uuid.uuid4()), "enabled": self.enabled,
            "warmup_steps": warmup_steps, "skip_interval": skip_interval, "expected_steps": 50,
            "calls": 0, "computed_calls": 0, "cache_hits": 0,
            "unique_steps": 0, "hit_steps": [], "branch_hits": {},
            "disabled_reason": None, "guard_failures": [],
        }

    def _disable(self, reason):
        self.enabled = False
        self.entries.clear()
        self.stats["disabled_reason"] = reason
        self.stats["guard_failures"].append(reason)

    def _inspect(self, model_function, args):
        if not self.model_guard():
            raise Unsupported("model/LoRA patch identity changed")
        if set(args) != {"input", "timestep", "c", "cond_or_uncond"}:
            raise Unsupported("unknown Comfy wrapper argument layout")
        x, timestep, c = args["input"], args["timestep"], args["c"]
        branch = tuple(args["cond_or_uncond"])
        if branch not in ((0,), (1,), (0, 1), (1, 0)):
            raise Unsupported("unknown or repeated CFG branch")
        if not torch.is_tensor(x) or x.ndim != 4 or x.shape[0] != len(branch):
            raise Unsupported("only one image per CFG branch is supported")
        if (x.dtype != torch.float32 or x.requires_grad or x.layout != torch.strided
                or not bool(torch.isfinite(x).all())):
            raise Unsupported("expected unmodified float32 sampler input")
        if (not torch.is_tensor(timestep) or timestep.ndim != 1
                or len(timestep) != len(branch) or not torch.isfinite(timestep).all()
                or not torch.equal(timestep, timestep[:1].expand_as(timestep))):
            raise Unsupported("invalid/mixed timestep batch")
        sigma = float(timestep[0].item())
        if sigma <= 0:
            raise Unsupported("nonpositive sigma")
        allowed_c = {"c_crossattn", "ref_latents", "guidance", "y", "c_concat",
                     "control", "ref_latents_method", "transformer_options"}
        if not isinstance(c, dict) or set(c) - allowed_c:
            raise Unsupported("unknown conditioning input")
        if c.get("control") is not None or c.get("c_concat") is not None:
            raise Unsupported("ControlNet/concat conditioning is unsupported")
        if (not torch.is_tensor(c.get("c_crossattn"))
                or c["c_crossattn"].shape[0] != len(branch)):
            raise Unsupported("missing grounded text conditioning")
        refs = c.get("ref_latents")
        if (not isinstance(refs, list) or len(refs) != 2
                or any(not torch.is_tensor(r) or r.ndim != 4
                       or r.shape[0] != len(branch) for r in refs)):
            raise Unsupported("expected ordered scene and genuine-person reference latents")
        opts = c.get("transformer_options", {})
        allowed_opts = {"cond_or_uncond", "uuids", "sigmas", "sample_sigmas",
                        "patches", "patches_replace", "wrappers", "callbacks"}
        if not isinstance(opts, dict) or set(opts) - allowed_opts:
            raise Unsupported("unknown transformer option")
        if any(_nonempty(opts.get(k)) for k in ("patches", "patches_replace", "wrappers", "callbacks")):
            raise Unsupported("dynamic transformer patches/hooks/wrappers unsupported")
        if tuple(opts.get("cond_or_uncond", ())) != branch:
            raise Unsupported("CFG branch metadata mismatch")
        if not torch.is_tensor(opts.get("sigmas")) or not torch.equal(
                opts["sigmas"], timestep[:1]):
            raise Unsupported("sigma metadata mismatch")
        schedule = opts.get("sample_sigmas")
        if (not torch.is_tensor(schedule) or schedule.ndim != 1 or len(schedule) != 51
                or not torch.isfinite(schedule).all()
                or not bool(torch.all(schedule[:-1] > schedule[1:]))
                or float(schedule[-1].item()) != 0):
            raise Unsupported("expected a strictly descending 50-step schedule ending at zero")
        if self.schedule is None:
            self.schedule = schedule.detach().clone()
        elif not _equal(schedule, self.schedule):
            raise Unsupported("sampling schedule/session changed")
        call_identity = (id(getattr(model_function, "__self__", None)),
                         getattr(model_function, "__func__", model_function))
        if self.model_call_identity is None:
            self.model_call_identity = call_identity
        elif call_identity != self.model_call_identity:
            raise Unsupported("model callable/session changed")
        if sigma != self.sigma:
            if self.sigma is not None and (sigma >= self.sigma or self.seen != {0, 1}):
                raise Unsupported("nonmonotonic sigma or incomplete prior CFG step")
            index = self.stats["unique_steps"]
            if index >= 50 or sigma != float(schedule[index].item()):
                raise Unsupported("repeated/restarted/skipped sampling schedule")
            self.stats["unique_steps"] += 1
            self.sigma = sigma
            self.seen = set()
        if self.seen.intersection(branch):
            raise Unsupported("same CFG branch repeated at one timestep")
        self.seen.update(branch)
        stable_c = {k: v for k, v in c.items() if k != "transformer_options"}
        stable_c["condition_uuids"] = opts.get("uuids")
        key = (branch, _meta(x), _signature(stable_c))
        if key not in self.entries:
            if self.stats["unique_steps"] != 1:
                raise Unsupported("CFG partition/shape/reference signature changed")
            self.entries[key] = Entry(_snapshot(stable_c))
        entry = self.entries[key]
        if not _equal(stable_c, entry.conditioning):
            raise Unsupported("text/reference/conditioning content changed")
        return x, timestep, c, branch, entry

    def __call__(self, model_function, args):
        self.stats["calls"] += 1
        if self.enabled:
            try:
                x, timestep, c, branch, entry = self._inspect(model_function, args)
            except Unsupported as exc:
                self._disable(str(exc))
        if not self.enabled:
            self.stats["computed_calls"] += 1
            return model_function(args["input"], args["timestep"], **args["c"])
        step = self.stats["unique_steps"]
        skip = step > 10 and (step - 10) % self.stats["skip_interval"] == 0 and step < 50
        sigma_view = timestep.reshape((-1, 1, 1, 1))
        if skip and entry.velocity is not None and entry.computed_step == step - 1:
            self.stats["cache_hits"] += 1
            if step not in self.stats["hit_steps"]:
                self.stats["hit_steps"].append(step)
            label = str(branch)
            self.stats["branch_hits"][label] = self.stats["branch_hits"].get(label, 0) + 1
            return x - entry.velocity * sigma_view
        self.stats["computed_calls"] += 1
        # Never catch/retry model exceptions or cancellation.
        output = model_function(x, timestep, **c)
        if (not torch.is_tensor(output) or _meta(output) != _meta(x)
                or not bool(torch.isfinite(output).all())):
            self._disable("unsupported/nonfinite model output")
            return output
        # apply_model returns denoised x0, whereas Flux predicts velocity.
        # Reconstruct velocity under audited CONST.calculate_denoised semantics.
        entry.velocity = ((x - output) / sigma_view).detach().clone()
        entry.computed_step = step
        return output


def apply(model, enabled=True, *, warmup_steps=10, skip_interval=3):
    """Return (cloned ModelPatcher, mutable JSON-serializable stats).

    Call immediately before ONE SamplerCustomAdvanced invocation. Never reuse
    the returned patcher in another sampler/job. Drop it after saving stats.
    Unsupported runtime layouts transparently disable caching and are recorded;
    the experiment runner must reject any run with guard_failures or zero hits.
    """
    if warmup_steps != 10 or skip_interval not in (3, 4):
        raise Unsupported("prototype permits only warmup10 and skip3/4")
    if model.model_options.get("model_function_wrapper") is not None:
        raise Unsupported("refusing to replace an existing model wrapper")
    clone = model.clone()
    if not enabled:
        return clone, GuardedForwardCache(enabled=False, warmup_steps=warmup_steps,
                                          skip_interval=skip_interval).stats
    import comfy.model_sampling
    sampling = clone.model.model_sampling
    diffusion = clone.model.diffusion_model
    if (diffusion.__class__.__name__ != "Flux"
            or diffusion.__class__.__module__ != "comfy.ldm.flux.model"
            or clone.model.__class__.__name__ != "Flux2"
            or getattr(sampling.calculate_denoised, "__func__", None)
               is not comfy.model_sampling.CONST.calculate_denoised):
        raise Unsupported("requires native Flux2 and exact CONST denoised conversion")
    if any(_nonempty(getattr(clone, k, None)) for k in
           ("hook_patches", "current_hooks", "forced_hooks", "injections", "wrappers", "additional_models")):
        raise Unsupported("requires static LoRAs without hooks/injections/wrappers/multigpu")
    patch_id = clone.patches_uuid
    patch_structure = tuple((k, id(v), len(v)) for k, v in sorted(clone.patches.items()))
    def guard():
        return (clone.patches_uuid == patch_id
                and tuple((k, id(v), len(v)) for k, v in sorted(clone.patches.items())) == patch_structure
                and not clone.hook_patches and clone.current_hooks is None
                and clone.forced_hooks is None)
    wrapper = GuardedForwardCache(model_guard=guard, warmup_steps=warmup_steps,
                                  skip_interval=skip_interval)
    clone.set_model_unet_function_wrapper(wrapper)
    return clone, wrapper.stats



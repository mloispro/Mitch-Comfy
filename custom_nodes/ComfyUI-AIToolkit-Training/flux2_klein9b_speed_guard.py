"""Ordinary core-node adapters for the bounded 3090 Production Speed recipes.

No model objects, sampler math, global settings or worker processes are changed.
Each loading branch checks the worker before delegating to its original core
loader. Submission validation also checks cached loaders; the always-changing
sampler rechecks at execution time without invalidating upstream model caches.
"""
from __future__ import annotations

import ctypes
import os

MODEL_NAME = "flux-2-klein-base-9b-bf16.safetensors"
CLIP_NAME = "qwen_3_8b_fp8mixed.safetensors"
VAE_NAME = "flux2-vae.safetensors"
MIN_AVAILABLE_GIB = 12.0
CATEGORY = "Mitch/Production Speed (RTX 3090)"


def _memory_available_gib():
    # ullAvailPageFile is remaining system commit, not disk free or swap free.
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in (
                "total_phys", "avail_phys", "total_page", "avail_page",
                "total_virtual", "avail_virtual", "avail_extended")]
    if os.name != "nt":
        raise RuntimeError("These local Production Speed packages require the validated Windows worker.")
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise RuntimeError("Cannot verify Production Speed host-memory headroom.")
    return status.avail_phys / 2**30, status.avail_page / 2**30


def _runtime_snapshot():
    import torch
    from comfy.cli_args import args
    if not torch.cuda.is_available():
        raise RuntimeError("Production Speed requires the RTX 3090 worker at port 8188.")
    ram, commit = _memory_available_gib()
    return {
        "gpu": torch.cuda.get_device_name(torch.cuda.current_device()),
        "port": int(args.port),
        "legacy": bool(getattr(args, "disable_dynamic_vram", False)),
        "cpu": bool(getattr(args, "cpu", False)),
        "available_ram_gib": ram,
        "available_commit_gib": commit,
    }


def guard_runtime():
    """Fail closed on the wrong worker; never stop/reconfigure/free another job.

    This is a per-call minimum-headroom check, not a promise that arbitrary
    changed prompts/dimensions fit. Fresh-run admission and both-GPU scheduling
    remain the launcher's responsibility; no cross-worker state is mutated.
    """
    state = _runtime_snapshot()
    if "RTX 3090" not in state["gpu"] or state["port"] != 8188 or state["cpu"]:
        raise RuntimeError("Production Speed is RTX 3090 / port 8188 only. Open the 3090 ComfyUI tab.")
    if state["legacy"]:
        raise RuntimeError("Production Speed requires normal dynamic VRAM; --disable-dynamic-vram is not this package's runtime.")
    if min(state["available_ram_gib"], state["available_commit_gib"]) < MIN_AVAILABLE_GIB:
        raise RuntimeError("Production Speed refused: at least 12 GiB available RAM and system commit are required.")
    return state


def _validate(check):
    try:
        check()
        guard_runtime()
    except (RuntimeError, ValueError, OSError) as error:
        return str(error)
    return True


def _require_equal(actual, expected, description):
    if actual != expected:
        raise ValueError(f"Production Speed {description} is fixed to {expected!r}; received {actual!r}.")


class Flux2Klein9BSpeedUNETLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"unet_name": ([MODEL_NAME],), "weight_dtype": (["fp8_e4m3fn"],)}}

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load_unet"
    CATEGORY = CATEGORY

    @staticmethod
    def _check(unet_name, weight_dtype):
        _require_equal(unet_name, MODEL_NAME, "base model")
        _require_equal(weight_dtype, "fp8_e4m3fn", "base loading precision")

    @classmethod
    def VALIDATE_INPUTS(cls, unet_name, weight_dtype):
        return _validate(lambda: cls._check(unet_name, weight_dtype))

    def load_unet(self, unet_name, weight_dtype):
        self._check(unet_name, weight_dtype)
        guard_runtime()
        from nodes import UNETLoader
        return UNETLoader().load_unet(unet_name, weight_dtype)


class Flux2Klein9BSpeedCLIPLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"clip_name": ([CLIP_NAME],), "type": (["flux2"],)},
                "optional": {"device": (["default"],)}}

    RETURN_TYPES = ("CLIP",)
    FUNCTION = "load_clip"
    CATEGORY = CATEGORY

    @staticmethod
    def _check(clip_name, type, device):
        _require_equal(clip_name, CLIP_NAME, "text encoder")
        _require_equal(type, "flux2", "text-encoder type")
        _require_equal(device, "default", "text-encoder device")

    @classmethod
    def VALIDATE_INPUTS(cls, clip_name, type, device="default"):
        return _validate(lambda: cls._check(clip_name, type, device))

    def load_clip(self, clip_name, type="flux2", device="default"):
        self._check(clip_name, type, device)
        guard_runtime()
        from nodes import CLIPLoader
        return CLIPLoader().load_clip(clip_name, type, device)


class Flux2Klein9BSpeedVAELoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"vae_name": ([VAE_NAME],)}}

    RETURN_TYPES = ("VAE",)
    FUNCTION = "load_vae"
    CATEGORY = CATEGORY

    @classmethod
    def VALIDATE_INPUTS(cls, vae_name):
        return _validate(lambda: _require_equal(vae_name, VAE_NAME, "VAE"))

    def load_vae(self, vae_name):
        _require_equal(vae_name, VAE_NAME, "VAE")
        guard_runtime()
        from nodes import VAELoader
        return VAELoader().load_vae(vae_name)


class Flux2Klein9BSpeedSampler:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "noise": ("NOISE",), "guider": ("GUIDER",), "sampler": ("SAMPLER",),
            "sigmas": ("SIGMAS",), "latent_image": ("LATENT",)}}

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("output", "denoised_output")
    FUNCTION = "sample"
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Run safety again even with a fixed seed and cached models/conditioning.
        return float("nan")

    def sample(self, noise, guider, sampler, sigmas, latent_image):
        guard_runtime()
        from comfy_extras.nodes_custom_sampler import SamplerCustomAdvanced
        result = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent_image)
        return (result[0], result[1])


SPEED_NODE_CLASS_MAPPINGS = {
    cls.__name__: cls for cls in (Flux2Klein9BSpeedUNETLoader, Flux2Klein9BSpeedCLIPLoader,
                                Flux2Klein9BSpeedVAELoader, Flux2Klein9BSpeedSampler)
}
SPEED_NODE_DISPLAY_NAME_MAPPINGS = {
    "Flux2Klein9BSpeedUNETLoader": "Speed - Base 9B FP8 (3090 guarded)",
    "Flux2Klein9BSpeedCLIPLoader": "Speed - Qwen FP8mixed (3090 guarded)",
    "Flux2Klein9BSpeedVAELoader": "Speed - Full VAE (3090 guarded)",
    "Flux2Klein9BSpeedSampler": "Speed - Native Sampler (3090 guarded)",
}

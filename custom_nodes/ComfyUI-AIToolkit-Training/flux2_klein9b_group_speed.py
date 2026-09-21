"""Separate Production Speed node for the three-seed-qualified Lounge recipe.

Normal Group behavior/defaults remain unchanged. The native generator's
per-call seam is used; no shared globals, model-forward patches or lab imports.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import flux2_klein9b_group_scene_studio as engine
from . import flux2_klein9b_guarded_cache as guarded_cache
from .flux2_klein9b_group_scene_studio_visual_presets import (
    Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11,
)
from .flux2_klein9b_scene_presets import GROUP_SCENE_PRESETS


LOUNGE_PRESET = "Approved lounge — central Mitch"
VALIDATED_SEEDS = (8675412, 8675413, 8675414)
SPEED_OUTPUT_ROOT = "production-speed/klein9b-group-lounge-faster-quality"
EVIDENCE_ID = "group-cache-20260909-three-matched-pairs"
EVALUATED_CACHE_SOURCE_SHA256 = "8f849c3543746efebb675e5725f4f680d97799fd88207673896476d4b845f9c5"


def _verify_recipe():
    """Reject recipe drift before model loading; no approximate substitutions."""
    expected = {
        "WIDTH": 832, "HEIGHT": 1216, "STEPS": 50, "GUIDANCE": 4.0,
        "LORA_STRENGTH": 0.90, "SMARTPHONE_STYLE_LORA_STRENGTH": 0.25,
        "SCENE_REFERENCE_PIXELS": 250_000, "IDENTITY_REFERENCE_PIXELS": 1_000_000,
        "DEFAULT_TARGET_X": 0.50, "DEFAULT_TARGET_Y": 0.44, "DEFAULT_HEAD_SCALE": 0.92,
        "MODEL_NAME": "flux-2-klein-base-9b-bf16.safetensors",
        "CLIP_NAME": "qwen_3_8b_fp8mixed.safetensors", "VAE_NAME": "flux2-vae.safetensors",
        "LORA_NAME": "m1tch-flux2-klein9b-identity-v3-r32-dop-step1600.safetensors",
        "IDENTITY_REFERENCE": "mitch-klein9b-ref-training04-front-neutral.jpg",
    }
    changed = [name for name, value in expected.items() if getattr(engine, name, None) != value]
    if changed:
        raise RuntimeError("Group Faster Quality requires its validated recipe; changed: " + ", ".join(changed))
    record = GROUP_SCENE_PRESETS.get(LOUNGE_PRESET)
    if not record or record.get("source_sha256", "").lower() != "1b26ac58a4fad8d03f69db7a4085c31b6682c71acbe22d5aee51f9e53fa0332b":
        raise RuntimeError("Validated Lounge source preset is missing or changed")


class _LoungeCachedRunner(Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11):
    """A new runner object per generate call; all cache state stays in locals."""

    def _prepare_sampling_model(self, model, *, steps, guidance):
        if steps != 50 or guidance != 4.0:
            raise RuntimeError("Group Faster Quality requires 50 steps and CFG4")
        wrapped, stats = guarded_cache.apply(model, enabled=True, warmup_steps=10, skip_interval=3)
        return wrapped, {
            "name": "Lounge Faster Quality", "implementation": "guarded_flux_velocity_replay_v1",
            "approximate": True, "evidence_id": EVIDENCE_ID,
            "evaluated_cache_source_sha256": EVALUATED_CACHE_SOURCE_SHA256,
            "deployed_cache_source_sha256": hashlib.sha256(Path(guarded_cache.__file__).read_bytes()).hexdigest(),
            "deployed_engine_source_sha256": hashlib.sha256(Path(engine.__file__).read_bytes()).hexdigest(),
            "validated_seeds": list(VALIDATED_SEEDS), "stats": stats,
        }

    def _generation_output_root(self):
        return SPEED_OUTPUT_ROOT

    def _finalize_sampling_report(self, report, sampling_metadata):
        stats = sampling_metadata["stats"]
        valid = (stats.get("unique_steps") == 50 and stats.get("cache_hits", 0) > 0
                 and not stats.get("guard_failures") and stats.get("disabled_reason") is None)
        sampling_metadata["execution_status"] = "cache_completed" if valid else "cache_guard_fallback_unvalidated"
        sampling_metadata["seed_was_in_three_pair_validation"] = report["seed"] in VALIDATED_SEEDS
        sampling_metadata["scope"] = "Approved Lounge only; 832x1216, 50 Euler, CFG4, TurboOFF, appearanceOFF, RTX3090"
        sampling_metadata["quality_note"] = "Approximately 25% less worker time in three matched pairs; not an identity lock or an improvement in skin/background detail. New seeds require review."
        report["purpose"] = "production_speed_klein9b_group_lounge_faster_quality"
        report["approval_basis"] = (
            "Separate opt-in Lounge speed route supported by three paired runtime/likeness/visual checks; "
            "each new output still requires review. Original production defaults are unchanged."
            if valid else "Cache guard fallback occurred. This output is not validated as the Faster Quality recipe; inspect sampling_adapter. No automatic retry was performed."
        )
        report["sampling_adapter"] = sampling_metadata
        report["manual_review_required"].append("Approximate cache: review identity, bystanders and clothing details; do not assume pixel equivalence")
        return report


class Flux2Klein9BGroupLoungeFasterQuality:
    """Normal Comfy Run, fixed qualified layout, user-adjustable seed only."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"seed": ("INT", {"default": 8675412, "min": 0,
                    "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True})}}

    @classmethod
    def VALIDATE_INPUTS(cls, seed):
        if type(seed) is not int or not 0 <= seed <= 0xFFFFFFFFFFFFFFFF:
            return "Seed must be an unsigned 64-bit integer"
        try:
            _verify_recipe()
        except RuntimeError as error:
            return str(error)
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("photo", "layout_guide", "effective_prompt", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = "image/generation/Production Speed"
    OUTPUT_NODE = True
    DESCRIPTION = "Validated Lounge layout only. About 25% less time in three matched RTX3090 tests; approximate output. Original Group remains unchanged."

    def generate(self, seed):
        valid = self.VALIDATE_INPUTS(seed)
        if valid is not True:
            raise RuntimeError(valid)
        # The native preset resolver loads/verifies its preserved Lounge source.
        # A fresh runner avoids cross-call/cache state even if Comfy reuses this node.
        response = _LoungeCachedRunner().generate(
            source_scene=None, scene_prompt="", target_x=0.50, target_y=0.44,
            head_scale=0.92, appearance_polish=False, fast_turbo=False,
            seed=seed, scene_preset=LOUNGE_PRESET,
        )
        report = json.loads(response["result"][-1])
        status = report["sampling_adapter"]["execution_status"]
        response["ui"]["text"] = (
            f"Production Speed — Lounge Faster Quality: {status}. Review this image; original Group is unchanged.",
        )
        return response

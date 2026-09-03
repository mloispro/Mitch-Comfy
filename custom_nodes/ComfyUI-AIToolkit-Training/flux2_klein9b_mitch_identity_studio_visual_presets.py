from __future__ import annotations

import folder_paths

from .flux2_klein9b_mitch_identity_studio import Flux2Klein9BMitchIdentityStudioV1
from .flux2_klein9b_scene_presets import (
    CUSTOM_IDENTITY_PRESET,
    IDENTITY_SCENE_PRESETS,
    PRESET_MANIFEST_SHA256,
    resolve_identity_profile,
    resolve_identity_scene,
)
from .flux2_klein9b_visual_preset_support import augment_visual_preset_report


class Flux2Klein9BMitchIdentityStudioVisualPresetsV11(
    Flux2Klein9BMitchIdentityStudioV1
):
    """Visual-preset shell around the hash-frozen v1 production generator."""

    @classmethod
    def INPUT_TYPES(cls):
        inherited = super().INPUT_TYPES()
        return {
            "required": dict(inherited["required"]),
            "optional": {
                "scene_preset": (
                    list(IDENTITY_SCENE_PRESETS),
                    {"default": CUSTOM_IDENTITY_PRESET},
                )
            },
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        reference_profile,
        scene_prompt,
        appearance_polish,
        fast_turbo,
        seed,
        scene_preset=CUSTOM_IDENTITY_PRESET,
    ):
        try:
            resolved_prompt, _record = resolve_identity_scene(scene_preset, scene_prompt)
            resolved_profile = resolve_identity_profile(scene_preset, reference_profile)
        except ValueError as exc:
            return str(exc)
        return super().VALIDATE_INPUTS(
            resolved_profile,
            resolved_prompt,
            appearance_polish,
            fast_turbo,
            seed,
        )

    def generate(
        self,
        reference_profile,
        scene_prompt,
        appearance_polish,
        fast_turbo,
        seed,
        scene_preset=CUSTOM_IDENTITY_PRESET,
    ):
        resolved_prompt, record = resolve_identity_scene(scene_preset, scene_prompt)
        resolved_profile = resolve_identity_profile(scene_preset, reference_profile)
        response = super().generate(
            resolved_profile,
            resolved_prompt,
            appearance_polish,
            fast_turbo,
            seed,
        )
        return augment_visual_preset_report(
            response,
            output_directory=folder_paths.get_output_directory(),
            shell_name="flux2_klein9b_mitch_identity_studio_v1_1_visual_presets",
            preset={
                "label": scene_preset,
                "key": record["key"],
                "manifest_sha256": PRESET_MANIFEST_SHA256,
                "reference_profile_input": reference_profile,
                "reference_profile_effective": resolved_profile,
                "scene_prompt_input": scene_prompt.strip(),
                "scene_prompt_effective": resolved_prompt,
            },
        )

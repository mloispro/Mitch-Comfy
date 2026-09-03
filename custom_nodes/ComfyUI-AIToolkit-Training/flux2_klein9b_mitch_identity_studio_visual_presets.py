from __future__ import annotations

import json
from pathlib import Path

import folder_paths

from .flux2_klein9b_mitch_identity_studio import Flux2Klein9BMitchIdentityStudioV1
from .flux2_klein9b_scene_presets import (
    CUSTOM_IDENTITY_PRESET,
    IDENTITY_SCENE_PRESETS,
    resolve_identity_scene,
)


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
        except ValueError as exc:
            return str(exc)
        return super().VALIDATE_INPUTS(
            reference_profile,
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
        response = super().generate(
            reference_profile,
            resolved_prompt,
            appearance_polish,
            fast_turbo,
            seed,
        )
        photo, effective_prompt, output_folder, report_json = response["result"]
        report = json.loads(report_json)
        report.update(
            {
                "purpose": "flux2_klein9b_mitch_identity_studio_v1_1_visual_presets",
                "scene_preset": scene_preset,
                "scene_preset_key": record["key"],
                "recommended_reference_profile": record["profile"],
                "scene_prompt_input": scene_prompt.strip(),
                "scene_prompt": resolved_prompt,
            }
        )
        updated_report_json = json.dumps(report, indent=2)
        report_path = (
            Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        )
        report_path.write_text(updated_report_json, encoding="utf-8")
        response["result"] = (
            photo,
            effective_prompt,
            output_folder,
            updated_report_json,
        )
        return response

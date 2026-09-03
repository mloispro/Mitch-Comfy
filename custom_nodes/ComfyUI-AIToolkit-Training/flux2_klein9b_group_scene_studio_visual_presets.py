from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
import folder_paths

from .flux2_klein9b_group_scene_studio import Flux2Klein9BMitchGroupSceneStudioV1
from .flux2_klein9b_mitch_identity_studio import _verify_sha256
from .flux2_klein9b_scene_presets import (
    CUSTOM_GROUP_PRESET,
    GROUP_SCENE_PRESETS,
    preset_asset_path,
    resolve_group_scene,
)


def _load_group_preset_source(record: dict) -> tuple[torch.Tensor, Path]:
    path = preset_asset_path(record)
    if path is None or not path.is_file():
        raise RuntimeError(f"Missing Group Scene Studio preset source: {path}")
    _verify_sha256(path, record["source_sha256"], f"Group preset {record['key']}")
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array.copy()).unsqueeze(0), path


class Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11(
    Flux2Klein9BMitchGroupSceneStudioV1
):
    """Visual-preset shell around the hash-frozen v1 group generator."""

    @classmethod
    def INPUT_TYPES(cls):
        inherited = super().INPUT_TYPES()
        return {
            "required": dict(inherited["required"]),
            "optional": {
                "scene_preset": (
                    list(GROUP_SCENE_PRESETS),
                    {"default": CUSTOM_GROUP_PRESET},
                )
            },
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        source_scene,
        scene_prompt,
        target_x,
        target_y,
        head_scale,
        appearance_polish,
        fast_turbo,
        seed,
        scene_preset=CUSTOM_GROUP_PRESET,
    ):
        try:
            resolved_prompt, record = resolve_group_scene(scene_preset, scene_prompt)
            if scene_preset != CUSTOM_GROUP_PRESET:
                path = preset_asset_path(record)
                if path is None or not path.is_file():
                    return f"Missing preset source image: {path}"
        except ValueError as exc:
            return str(exc)
        return super().VALIDATE_INPUTS(
            source_scene,
            resolved_prompt,
            target_x,
            target_y,
            head_scale,
            appearance_polish,
            fast_turbo,
            seed,
        )

    def generate(
        self,
        source_scene,
        scene_prompt,
        target_x,
        target_y,
        head_scale,
        appearance_polish,
        fast_turbo,
        seed,
        scene_preset=CUSTOM_GROUP_PRESET,
    ):
        resolved_prompt, record = resolve_group_scene(scene_preset, scene_prompt)
        resolved_source = source_scene
        resolved_x = float(target_x)
        resolved_y = float(target_y)
        resolved_head_scale = float(head_scale)
        source_path = None
        if scene_preset != CUSTOM_GROUP_PRESET:
            resolved_source, source_path = _load_group_preset_source(record)
            resolved_x = float(record["target_x"])
            resolved_y = float(record["target_y"])
            resolved_head_scale = float(record["head_scale"])

        response = super().generate(
            resolved_source,
            resolved_prompt,
            resolved_x,
            resolved_y,
            resolved_head_scale,
            appearance_polish,
            fast_turbo,
            seed,
        )
        photo, layout_guide, effective_prompt, output_folder, report_json = response[
            "result"
        ]
        report = json.loads(report_json)
        report.update(
            {
                "purpose": "flux2_klein9b_mitch_group_scene_studio_v1_1_visual_presets",
                "scene_preset": scene_preset,
                "scene_preset_key": record["key"],
                "scene_preset_source": str(source_path) if source_path else None,
                "scene_preset_source_sha256": record.get("source_sha256"),
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
            layout_guide,
            effective_prompt,
            output_folder,
            updated_report_json,
        )
        return response

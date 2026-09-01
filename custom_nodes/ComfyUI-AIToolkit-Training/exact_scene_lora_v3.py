from __future__ import annotations

import hashlib
import json
from pathlib import Path

import folder_paths
from PIL import Image

from . import one_reference_photo as baseline
from . import reference_photo_studio as studio
from .crowd_proof import MASK_FULL_HEAD, MASK_INTERNAL_FACE, MODE_CONTEXTUAL, _generate


LORA_NAME = r"aitk\m1tch-flux2-klein-4b-identity-v3-portrait-profile.safetensors"
LORA_SHA256 = "c43d7c1fca404a8b316a9d0c8756e140033e4763532628f62facc791f0b8a149"


def _verify_lora() -> str:
    full_path = folder_paths.get_full_path("loras", LORA_NAME)
    if not full_path:
        raise RuntimeError(f"Missing FLUX.2 Klein v3 identity LoRA: {LORA_NAME}")
    path = Path(full_path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest().lower()
    if actual != LORA_SHA256:
        raise RuntimeError(
            f"FLUX.2 Klein v3 LoRA hash mismatch. Expected {LORA_SHA256}, found {actual}."
        )
    return str(path)


class Flux2ExactSceneIdentityV3:
    """Use the new Klein v3 LoRA inside one explicitly selected scene face only."""

    @classmethod
    def INPUT_TYPES(cls):
        references = ["Upload one face photo", *baseline._available_input_images()]
        optional_references = [studio.NO_REFERENCE, *baseline._available_input_images()]
        return {
            "required": {
                "scene_plate_path": (
                    "STRING",
                    {
                        "default": str(
                            Path(folder_paths.get_input_directory())
                            / "mitch-workbench-dating-09-night-city.png"
                        )
                    },
                ),
                "face_reference": (references, {"image_upload": True}),
                "reference_2": (optional_references, {"image_upload": True}),
                "reference_3": (optional_references, {"image_upload": True}),
                "reference_4": (optional_references, {"image_upload": True}),
                "target_face_index_left_to_right": (
                    "INT",
                    {"default": 0, "min": 0, "max": 20, "step": 1},
                ),
                "denoise_strength": (
                    "FLOAT",
                    {"default": 0.65, "min": 0.35, "max": 1.0, "step": 0.05},
                ),
                "lora_strength": (
                    "FLOAT",
                    {"default": 1.20, "min": 0.60, "max": 1.20, "step": 0.05},
                ),
                "seed": (
                    "INT",
                    {"default": 8675310, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
                "scene_context": (
                    "STRING",
                    {"default": "", "multiline": True},
                ),
            },
            "optional": {
                "edit_region": ([MASK_INTERNAL_FACE, MASK_FULL_HEAD],),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        scene_plate_path,
        face_reference,
        reference_2,
        reference_3,
        reference_4,
        target_face_index_left_to_right,
        denoise_strength,
        lora_strength,
        seed,
        scene_context,
        edit_region=MASK_INTERNAL_FACE,
    ):
        plate = Path(scene_plate_path).expanduser()
        if not plate.is_file():
            return f"Scene plate is not available: {plate}"
        with Image.open(plate) as source:
            width, height = source.size
        if width < 512 or height < 512:
            return "The scene plate must be at least 512 pixels on both axes."
        if width % 16 or height % 16:
            return "Scene plate dimensions must be divisible by 16."
        names = studio.selected_reference_names(
            face_reference, reference_2, reference_3, reference_4
        )
        validation = studio._validate_reference_names(names)
        if validation is not True:
            return validation
        if int(target_face_index_left_to_right) < 0:
            return "The left-to-right target face index cannot be negative."
        if not 0.35 <= float(denoise_strength) <= 1.0:
            return "Denoise strength must be between 0.35 and 1.0."
        if not 0.60 <= float(lora_strength) <= 1.20:
            return "LoRA strength must be between 0.60 and 1.20."
        if edit_region not in (MASK_INTERNAL_FACE, MASK_FULL_HEAD):
            return f"Unknown exact-scene edit region: {edit_region}"
        try:
            _verify_lora()
        except RuntimeError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = (
        "photo",
        "transition_mask",
        "diagnostic",
        "report_json",
        "output_folder",
    )
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity/Experiments"
    OUTPUT_NODE = True

    def generate(
        self,
        scene_plate_path,
        face_reference,
        reference_2,
        reference_3,
        reference_4,
        target_face_index_left_to_right,
        denoise_strength,
        lora_strength,
        seed,
        scene_context,
        edit_region=MASK_INTERNAL_FACE,
    ):
        names = studio.selected_reference_names(
            face_reference, reference_2, reference_3, reference_4
        )
        validation = self.VALIDATE_INPUTS(
            scene_plate_path,
            face_reference,
            reference_2,
            reference_3,
            reference_4,
            target_face_index_left_to_right,
            denoise_strength,
            lora_strength,
            seed,
            scene_context,
            edit_region,
        )
        if validation is not True:
            raise RuntimeError(validation)
        _verify_lora()
        photo, mask, diagnostic, report, output_folder, saved = _generate(
            scene_plate_path,
            names,
            MODE_CONTEXTUAL,
            float(lora_strength),
            int(seed),
            24,
            scene_context=scene_context.strip() or None,
            mask_strategy=edit_region,
            denoise_strength=float(denoise_strength),
            preserve_plate_dimensions=True,
            target_face_index_left_to_right=int(target_face_index_left_to_right),
            lora_name=LORA_NAME,
            apply_phone_finish=False,
        )
        report["purpose"] = "exact_supplied_scene_klein_v3_identity_lora"
        report["lora_path"] = _verify_lora()
        report["lora_sha256"] = LORA_SHA256
        report["target_face_index_left_to_right"] = int(
            target_face_index_left_to_right
        )
        report["scene_preservation"] = {
            "outside_transition_mask": "source latent is not sampled",
            "global_phone_finish": False,
            "scene_plate_is_identity_evidence": False,
        }
        report_path = (
            Path(folder_paths.get_output_directory()) / output_folder / "report.json"
        )
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    "FLUX.2 Klein v3 LoRA exact-scene edit; "
                    f"automated {report['acceptance']['status']}; "
                    f"identity {report['identity']['main_identity_similarity']:.4f}. "
                    f"Saved to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (
                photo,
                mask,
                diagnostic,
                json.dumps(report, indent=2),
                output_folder,
            ),
        }

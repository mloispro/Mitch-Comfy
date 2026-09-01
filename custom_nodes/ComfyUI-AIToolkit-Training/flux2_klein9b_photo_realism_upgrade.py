from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime
from pathlib import Path

import comfy.utils
import cv2
import folder_paths
import node_helpers
import nodes as comfy_nodes
import numpy as np
import torch
from comfy_extras.nodes_custom_sampler import (
    CFGGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler

from . import one_reference_photo as baseline
from .flux2_klein9b_mitch_identity_studio import (
    CLIP_NAME,
    GUIDANCE,
    LORA_NAME,
    LORA_SHA256,
    LORA_STRENGTH,
    MODEL_NAME,
    STEPS,
    VAE_NAME,
    _assert_rtx3090,
    _verify_sha256,
)
from .flux2_klein9b_photo_realism_upgrade_presets import (
    DEFAULT_DETAIL_INSTRUCTIONS,
    compose_upgrade_prompt,
    compute_output_dimensions,
    face_interior_rectangle,
)


IDENTITY_REFERENCE = "mitch-klein9b-ref-front-neutral-v2.jpg"
IDENTITY_REFERENCE_SHA256 = "28DF2AE0D717A788370CC825F7BB24CF38DB9C7CDA3F66BAEFAB58BE86D8AF33"
HAIR_REFERENCE = "mitch-natural-hair-only-val05-isolated.png"
HAIR_REFERENCE_SHA256 = "3B7C223BFB6390AED6981EB3C3549CC767BDC967B887D170153EFA6BE7DDB201"
MODEL_SHA256 = "4A54FAD7F5F741B99EEE217198DAAC20B8D8E515E2A1F5B064FD51CF074F95BD"
CLIP_SHA256 = "ABAD16806E0CBABC54E0325D6565847443FE396D5F0BE38BB3CD3FE75A1201D6"
VAE_SHA256 = "D64F3A68E1CC4F9F4E29B6E0DA38A0204FE9A49F2D4053F0EC1FA1CA02F9C4B5"
MODEL_LOAD_DTYPE = "fp8_e4m3fn"
SOURCE_REFERENCE_MEGAPIXELS = 1.00
GUIDE_REFERENCE_MEGAPIXELS = 0.50
IDENTITY_REFERENCE_MEGAPIXELS = 0.50
HAIR_REFERENCE_MEGAPIXELS = 0.10
CANNY_LOW = 0.20
CANNY_HIGH = 0.60
OUTPUT_ROOT = "flux2-klein9b-upgrade-photo-detail-realism-v1"
PROMPTING_STRATEGY = "bfl-flux2-four-role-existing-photo-upgrade-v1"


def _required_input(name: str, expected_sha256: str, label: str) -> Path:
    path = Path(folder_paths.get_input_directory()) / name
    if not path.is_file():
        raise RuntimeError(f"Missing protected {label}: {path}")
    _verify_sha256(path, expected_sha256, label)
    return path


def _required_model(category: str, name: str, expected_sha256: str, label: str) -> Path:
    full_path = folder_paths.get_full_path(category, name)
    if not full_path:
        raise RuntimeError(f"Missing {label}: {name}")
    path = Path(full_path)
    _verify_sha256(path, expected_sha256, label)
    return path


def _decoded_pixel_sha256(image: torch.Tensor) -> str:
    pixels = (
        image[:1, :, :, :3]
        .detach()
        .float()
        .cpu()
        .clamp(0.0, 1.0)
        .mul(255.0)
        .round()
        .byte()
        .contiguous()
        .numpy()
    )
    return hashlib.sha256(pixels.tobytes()).hexdigest().upper()


def _scale_to_total_pixels(image: torch.Tensor, megapixels: float, method: str) -> torch.Tensor:
    height, width = (int(image.shape[1]), int(image.shape[2]))
    scale = math.sqrt(float(megapixels) * 1024.0 * 1024.0 / float(width * height))
    target_width = max(1, round(width * scale))
    target_height = max(1, round(height * scale))
    return comfy.utils.common_upscale(
        image.movedim(-1, 1), target_width, target_height, method, "disabled"
    ).movedim(1, -1)


def _encode_reference(vae, image: torch.Tensor, megapixels: float, method: str):
    resized = _scale_to_total_pixels(image, megapixels, method)
    latent = comfy_nodes.VAEEncode().encode(vae, resized)[0]["samples"]
    return latent, list(map(int, (resized.shape[2], resized.shape[1])))


def _append_reference(conditioning, latent):
    values = {"reference_latents": [latent]}
    return node_helpers.conditioning_set_values(conditioning, values, append=True)


def build_face_free_guide(source_photo: torch.Tensor) -> tuple[torch.Tensor, dict]:
    source = source_photo[:1, :, :, :3].detach().float().cpu()
    height, width = (int(source.shape[1]), int(source.shape[2]))
    rgb = np.clip(source[0].numpy() * 255.0, 0, 255).round().astype(np.uint8)
    faces = baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError("No face was detected in the source photo.")
    if len(faces) != 1:
        raise RuntimeError(
            f"Upgrade Photo Detail & Realism is for one-person photos; detected {len(faces)} faces. "
            "Use Mitch Group Scene Studio for group photographs."
        )
    face = faces[0]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 1.0)
    edges = cv2.Canny(gray, round(CANNY_LOW * 255), round(CANNY_HIGH * 255))
    interior = face_interior_rectangle(face.bbox, width, height)
    cv2.rectangle(edges, interior[:2], interior[2:], 0, thickness=-1)
    guide_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    guide = torch.from_numpy(guide_rgb.astype(np.float32) / 255.0).unsqueeze(0)
    return guide, {
        "source_size": [width, height],
        "detected_face_count": 1,
        "selected_face_bbox": [round(float(value), 4) for value in face.bbox],
        "cleared_face_interior_rectangle": list(interior),
        "canny_low": CANNY_LOW,
        "canny_high": CANNY_HIGH,
        "pre_blur": "Gaussian 5x5 sigma 1.0",
        "role": "geometry only; face interior removed",
    }


class Flux2Klein9BPhotoRealismUpgradeV1:
    """Locked four-role whole-frame upgrade for an existing one-person photograph."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_photo": ("IMAGE",),
                "detail_instructions": (
                    "STRING",
                    {
                        "default": DEFAULT_DETAIL_INSTRUCTIONS,
                        "multiline": True,
                        "placeholder": "Describe the background/material detail that should become more realistic.",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 8675416,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    @classmethod
    def VALIDATE_INPUTS(cls, source_photo, detail_instructions, seed):
        try:
            compose_upgrade_prompt(detail_instructions)
        except ValueError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("photo", "structure_guide", "effective_prompt", "output_folder", "report_json")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity"
    OUTPUT_NODE = True

    def generate(
        self,
        source_photo,
        detail_instructions,
        seed,
        prompt=None,
        extra_pnginfo=None,
    ):
        validation = self.VALIDATE_INPUTS(source_photo, detail_instructions, seed)
        if validation is not True:
            raise RuntimeError(validation)
        if source_photo.ndim != 4 or source_photo.shape[0] != 1 or source_photo.shape[-1] < 3:
            raise RuntimeError("Load exactly one RGB source photograph.")

        gpu = _assert_rtx3090()
        source = source_photo[:1, :, :, :3].detach().float().cpu()
        source_height, source_width = (int(source.shape[1]), int(source.shape[2]))
        output_width, output_height = compute_output_dimensions(source_width, source_height)
        guide, guide_report = build_face_free_guide(source)
        effective_prompt = compose_upgrade_prompt(detail_instructions)

        model_path = _required_model("diffusion_models", MODEL_NAME, MODEL_SHA256, "Klein Base 9B model")
        clip_path = _required_model("text_encoders", CLIP_NAME, CLIP_SHA256, "Qwen 3 8B text encoder")
        vae_path = _required_model("vae", VAE_NAME, VAE_SHA256, "FLUX.2 VAE")
        lora_path = _required_model("loras", LORA_NAME, LORA_SHA256, "protected step-1600 LoRA")
        identity_path = _required_input(
            IDENTITY_REFERENCE, IDENTITY_REFERENCE_SHA256, "genuine identity reference"
        )
        hair_path = _required_input(HAIR_REFERENCE, HAIR_REFERENCE_SHA256, "isolated hair reference")

        started = time.perf_counter()
        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, MODEL_LOAD_DTYPE)[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, LORA_NAME, LORA_STRENGTH
        )[0]
        clip = comfy_nodes.CLIPLoader().load_clip(CLIP_NAME, "flux2", "default")[0]
        vae = comfy_nodes.VAELoader().load_vae(VAE_NAME)[0]

        positive = comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
        negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
        reference_sizes = []

        latent, size = _encode_reference(
            vae, source, SOURCE_REFERENCE_MEGAPIXELS, "bicubic"
        )
        positive = _append_reference(positive, latent)
        negative = _append_reference(negative, latent)
        reference_sizes.append(size)

        latent, size = _encode_reference(
            vae, guide, GUIDE_REFERENCE_MEGAPIXELS, "nearest-exact"
        )
        positive = _append_reference(positive, latent)
        negative = _append_reference(negative, latent)
        reference_sizes.append(size)

        identity_image = comfy_nodes.LoadImage().load_image(IDENTITY_REFERENCE)[0][:1, :, :, :3]
        latent, size = _encode_reference(
            vae, identity_image, IDENTITY_REFERENCE_MEGAPIXELS, "nearest-exact"
        )
        positive = _append_reference(positive, latent)
        negative = _append_reference(negative, latent)
        reference_sizes.append(size)

        hair_image = comfy_nodes.LoadImage().load_image(HAIR_REFERENCE)[0][:1, :, :, :3]
        latent, size = _encode_reference(
            vae, hair_image, HAIR_REFERENCE_MEGAPIXELS, "bicubic"
        )
        positive = _append_reference(positive, latent)
        negative = _append_reference(negative, latent)
        reference_sizes.append(size)

        guider = CFGGuider.execute(model, positive, negative, GUIDANCE)[0]
        sampler = KSamplerSelect.execute("euler")[0]
        sigmas = Flux2Scheduler.execute(STEPS, output_width, output_height)[0]
        noise = RandomNoise.execute(int(seed))[0]
        latent_image = EmptyFlux2LatentImage.execute(output_width, output_height, 1)[0]
        sampled = SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent_image
        )[0]
        photo = comfy_nodes.VAEDecode().decode(vae, sampled)[0]

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{OUTPUT_ROOT}/{run_stamp}"
        report = {
            "schema_version": 1,
            "purpose": "flux2_klein9b_upgrade_photo_detail_and_realism_v1",
            "approval_basis": (
                "Locked from Mitch-approved candidate-klein9b-iphone-structure-v4-seed-8675416.png"
            ),
            "gpu": gpu,
            "worker_requirement": "RTX 3090 / standard ComfyUI port 8188",
            "model": MODEL_NAME,
            "model_path": str(model_path),
            "model_sha256": MODEL_SHA256,
            "model_load_dtype": MODEL_LOAD_DTYPE,
            "text_encoder": CLIP_NAME,
            "text_encoder_path": str(clip_path),
            "text_encoder_sha256": CLIP_SHA256,
            "vae": VAE_NAME,
            "vae_path": str(vae_path),
            "vae_sha256": VAE_SHA256,
            "lora": LORA_NAME,
            "lora_path": str(lora_path),
            "lora_sha256": LORA_SHA256,
            "lora_strength": LORA_STRENGTH,
            "identity_reference": IDENTITY_REFERENCE,
            "identity_reference_path": str(identity_path),
            "identity_reference_sha256": IDENTITY_REFERENCE_SHA256,
            "hair_reference": HAIR_REFERENCE,
            "hair_reference_path": str(hair_path),
            "hair_reference_sha256": HAIR_REFERENCE_SHA256,
            "source_decoded_pixel_sha256": _decoded_pixel_sha256(source),
            "reference_order": [
                "Picture 1: exact source scene, pose, expression, clothing, lighting layout, and composition at 1.00 MP",
                "Picture 2: automatically generated face-interior-free Canny structure guide at 0.50 MP",
                "Picture 3: protected genuine frontal Mitch identity photograph at 0.50 MP",
                "Picture 4: protected genuine isolated hair-material crop at 0.10 MP",
            ],
            "reference_encoded_sizes": reference_sizes,
            "identity_mechanism": (
                "protected Base-9B step-1600 identity LoRA plus genuine-photo native ReferenceLatent"
            ),
            "source_semantic_role": "scene, pose, expression, clothing, lighting layout, and composition",
            "source_used_as_identity": False,
            "guide": guide_report,
            "source_latent_initialization": False,
            "face_swap": False,
            "output_mask": False,
            "restoration": False,
            "selective_sharpening": False,
            "upscaling": False,
            "film_grain_stage": False,
            "second_model_pass": False,
            "prompting_strategy": PROMPTING_STRATEGY,
            "prompt_graph": "prompt-api.json",
            "workflow_snapshot": "workflow-snapshot.json" if extra_pnginfo else None,
            "detail_instructions": str(detail_instructions).strip(),
            "effective_prompt": effective_prompt,
            "source_width": source_width,
            "source_height": source_height,
            "width": output_width,
            "height": output_height,
            "output_resolution_policy": "native when <=1.70 MP; otherwise aspect-preserving 1.70 MP cap; multiples of 16",
            "steps": STEPS,
            "cfg": GUIDANCE,
            "sampler": "euler",
            "scheduler": "Flux2Scheduler",
            "seed": int(seed),
            "seconds": round(time.perf_counter() - started, 3),
            "manual_review_required": [
                "identity and apparent age at full size and thumbnail",
                "unchanged head yaw, pitch, roll, gaze, expression, pose, crop, and scene geometry",
                "hairline, forehead, temple, ear, and back-of-head continuity without shadow bands or halos",
                "natural skin, hair, fabric, and background material detail without oversharpening",
                "coherent whole-frame lighting, depth, sensor texture, and edge softness",
            ],
        }
        png_info = dict(extra_pnginfo) if isinstance(extra_pnginfo, dict) else {}
        png_info["flux2_klein9b_upgrade_photo_detail_realism_v1"] = report
        saved = comfy_nodes.SaveImage().save_images(
            photo,
            f"{output_folder}/photo",
            extra_pnginfo=png_info,
        )
        comfy_nodes.SaveImage().save_images(
            guide,
            f"{output_folder}/structure-guide",
            extra_pnginfo=png_info,
        )
        report_json = json.dumps(report, indent=2)
        run_directory = Path(folder_paths.get_output_directory()) / output_folder
        report_path = run_directory / "report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_json, encoding="utf-8")
        (run_directory / "prompt-api.json").write_text(
            json.dumps(prompt or {}, indent=2), encoding="utf-8"
        )
        if extra_pnginfo:
            (run_directory / "workflow-snapshot.json").write_text(
                json.dumps(extra_pnginfo, indent=2), encoding="utf-8"
            )

        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"Saved Upgrade Photo Detail & Realism result to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, guide, effective_prompt, output_folder, report_json),
        }

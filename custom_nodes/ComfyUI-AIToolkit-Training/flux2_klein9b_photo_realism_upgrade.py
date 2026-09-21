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
from .flux2_klein9b_attractiveness import (
    ATTRACTIVENESS_LEVELS,
    HIGH_PROFILE,
    apply_high_attractiveness,
    normalize_attractiveness,
)
from .flux2_klein9b_deterministic_polish import (
    POLISH_PROFILE,
    apply_deterministic_face_polish,
    build_semantic_hair_mask,
)
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
from .flux2_klein9b_smartphone_style import (
    SMARTPHONE_STYLE_LORA_NAME,
    SMARTPHONE_STYLE_LORA_STRENGTH,
    apply_smartphone_style_trigger,
    smartphone_style_report,
    verify_smartphone_style_lora,
)
from .flux2_klein9b_source_gaze_lock import (
    SOURCE_GAZE_LOCK_PROFILE,
    _detect_refined_landmarks,
    apply_source_gaze_lock,
)
from .flux2_klein9b_upgrade_masking import (
    HUMAN_SEGMENTATION_MODEL,
    HUMAN_SEGMENTATION_SHA256,
    NATURAL_LENS_BLUR_PROFILE,
    apply_natural_lens_background_blur,
    human_foreground_mask,
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
MILESTONE_COMMIT = "d58732a"
MILESTONE_TAG = "milestone-good-identity-workflows-2026-09-01"
REVALIDATION_COMMIT = "b32ecb9"
REVALIDATION_TAG = "milestone-klein9b-production-revalidated-2026-09-03"
APPEARANCE_DEFAULT = "low"
PHONE_STYLE_LABEL_ON = "Deep-focus phone-camera realism (default)"
PHONE_STYLE_LABEL_OFF = "Natural lens background separation"
UPGRADE_PHONE_STYLE_TEST_BASIS = (
    "Native same-seed restored-Upgrade A/B on 2026-09-02: raw identity centroid "
    "0.7816 to 0.7791, polished identity 0.7662 to 0.7397, tolerant structure F1 "
    "0.3076 to 0.2961, and background micro-luma 11.9536 to 12.3539. The adapter "
    "has that known automated-metric tradeoff, but its deep-focus v4 rendering was visually "
    "accepted by Mitch and selected as the default on 2026-09-03. Phone-off natural-lens "
    "background separation remains available as an explicit alternate rendering."
)
APPEARANCE_PROFILE = f"{POLISH_PROFILE}+{SOURCE_GAZE_LOCK_PROFILE}"


def _upgrade_phone_style_report() -> dict:
    result = smartphone_style_report()
    result.update(
        {
            "upgrade_default": True,
            "upgrade_status": "accepted_default",
            "upgrade_acceptance_test": UPGRADE_PHONE_STYLE_TEST_BASIS,
        }
    )
    return result


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
    """Milestone four-role upgrade with face polish and a deterministic camera finish."""

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
                "appearance_polish": (
                    list(ATTRACTIVENESS_LEVELS),
                    {
                        "default": APPEARANCE_DEFAULT,
                        "tooltip": "Attractiveness: off = raw generation; low = previous handsome polish; high = stronger brow/crease retouch after gaze lock. High preserves eye shape but can reduce identity similarity.",
                    },
                ),
                "phone_camera_style": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": PHONE_STYLE_LABEL_ON,
                        "label_off": PHONE_STYLE_LABEL_OFF,
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
    def VALIDATE_INPUTS(
        cls,
        source_photo,
        detail_instructions,
        appearance_polish,
        phone_camera_style,
        seed,
    ):
        try:
            normalize_attractiveness(appearance_polish)
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
        appearance_polish,
        phone_camera_style,
        seed,
        prompt=None,
        extra_pnginfo=None,
    ):
        validation = self.VALIDATE_INPUTS(
            source_photo,
            detail_instructions,
            appearance_polish,
            phone_camera_style,
            seed,
        )
        if validation is not True:
            raise RuntimeError(validation)
        appearance_level = normalize_attractiveness(appearance_polish)
        appearance_polish = appearance_level != "off"
        appearance_profile = APPEARANCE_PROFILE + (
            f"+{HIGH_PROFILE}" if appearance_level == "high" else ""
        )
        if source_photo.ndim != 4 or source_photo.shape[0] != 1 or source_photo.shape[-1] < 3:
            raise RuntimeError("Load exactly one RGB source photograph.")

        gpu = _assert_rtx3090()
        source = source_photo[:1, :, :, :3].detach().float().cpu()
        source_height, source_width = (int(source.shape[1]), int(source.shape[2]))
        output_width, output_height = compute_output_dimensions(source_width, source_height)
        guide, guide_report = build_face_free_guide(source)
        effective_prompt = compose_upgrade_prompt(detail_instructions)
        if phone_camera_style:
            effective_prompt = apply_smartphone_style_trigger(effective_prompt)

        model_path = _required_model("diffusion_models", MODEL_NAME, MODEL_SHA256, "Klein Base 9B model")
        clip_path = _required_model("text_encoders", CLIP_NAME, CLIP_SHA256, "Qwen 3 8B text encoder")
        vae_path = _required_model("vae", VAE_NAME, VAE_SHA256, "FLUX.2 VAE")
        lora_path = _required_model("loras", LORA_NAME, LORA_SHA256, "protected step-1600 LoRA")
        smartphone_lora_path = None
        if phone_camera_style:
            smartphone_lora_path = Path(verify_smartphone_style_lora())
        identity_path = _required_input(
            IDENTITY_REFERENCE, IDENTITY_REFERENCE_SHA256, "genuine identity reference"
        )
        hair_path = _required_input(HAIR_REFERENCE, HAIR_REFERENCE_SHA256, "isolated hair reference")

        started = time.perf_counter()
        model = comfy_nodes.UNETLoader().load_unet(MODEL_NAME, MODEL_LOAD_DTYPE)[0]
        model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
            model, LORA_NAME, LORA_STRENGTH
        )[0]
        if phone_camera_style:
            model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
                model,
                SMARTPHONE_STYLE_LORA_NAME,
                SMARTPHONE_STYLE_LORA_STRENGTH,
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
        raw_photo = comfy_nodes.VAEDecode().decode(vae, sampled)[0][:1, :, :, :3].detach().float().cpu()
        polish_report = None
        polish_mask = torch.zeros_like(raw_photo)
        if appearance_polish:
            generated_rgb = np.clip(
                raw_photo[0].numpy() * 255.0, 0, 255
            ).round().astype(np.uint8)
            generated_faces = baseline._face_analyzer().get(
                cv2.cvtColor(generated_rgb, cv2.COLOR_RGB2BGR)
            )
            if not generated_faces:
                raise RuntimeError(
                    "No face was detected in the generated photograph for deterministic appearance polish."
                )
            generated_face = max(
                generated_faces,
                key=lambda item: float(
                    (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
                ),
            )
            semantic_hair_mask = build_semantic_hair_mask(
                generated_rgb, generated_face.bbox
            )
            photo, polish_mask, polish_report = apply_deterministic_face_polish(
                raw_photo,
                generated_face.bbox,
                generated_face.kps,
                semantic_hair_mask=semantic_hair_mask,
            )
            photo, gaze_mask, gaze_report = apply_source_gaze_lock(source, photo)
            polish_mask = torch.maximum(polish_mask, gaze_mask)
            polish_report["source_gaze_lock"] = gaze_report
            if appearance_level == "high":
                # High runs after gaze correction. It can refine the upper-lid
                # contour, but hard-protects the corrected iris/pupil region.
                polished_rgb = np.clip(photo[0].numpy() * 255.0, 0, 255).round().astype(np.uint8)
                landmarks, _ = _detect_refined_landmarks(polished_rgb)
                source_rgb = np.clip(source[0].detach().float().cpu().numpy() * 255.0,
                                     0, 255).round().astype(np.uint8)
                source_landmarks, _ = _detect_refined_landmarks(source_rgb)
                photo, high_mask, high_report = apply_high_attractiveness(
                    photo, landmarks, semantic_hair_mask, source_landmarks
                )
                polish_mask = torch.maximum(polish_mask, high_mask)
                polish_report["high_attractiveness"] = high_report
            polish_report["profile"] = appearance_profile
            polish_report["level"] = appearance_level
        else:
            photo = raw_photo

        pre_background_blur_photo = photo
        background_blur_mask = torch.zeros_like(photo)
        background_blur_report = None
        human_segmentation_path = None
        if not phone_camera_style:
            human_segmentation_path = (
                Path(folder_paths.models_dir) / "rembg" / HUMAN_SEGMENTATION_MODEL
            )
            if not human_segmentation_path.is_file():
                raise RuntimeError(
                    f"Missing local human segmentation model: {human_segmentation_path}"
                )
            _verify_sha256(
                human_segmentation_path,
                HUMAN_SEGMENTATION_SHA256,
                "U2Net human segmentation model",
            )
            final_rgb = np.clip(photo[0].numpy(), 0.0, 1.0).astype(np.float32)
            human_foreground = human_foreground_mask(
                final_rgb, human_segmentation_path
            )
            blurred_rgb, background_blur_alpha, background_blur_report = (
                apply_natural_lens_background_blur(final_rgb, human_foreground)
            )
            photo = torch.from_numpy(blurred_rgb).unsqueeze(0)
            background_blur_mask = (
                torch.from_numpy(background_blur_alpha)
                .unsqueeze(0)
                .unsqueeze(-1)
                .repeat(1, 1, 1, 3)
            )

        run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        output_folder = f"{OUTPUT_ROOT}/{run_stamp}"
        report = {
            "schema_version": 2,
            "purpose": "flux2_klein9b_upgrade_photo_detail_and_realism_v1",
            "approval_basis": (
                (
                    f"The current phone-on default was freshly revalidated at {REVALIDATION_COMMIT} "
                    f"({REVALIDATION_TAG}). "
                    if phone_camera_style
                    else f"The phone-off route is present at {REVALIDATION_COMMIT} ({REVALIDATION_TAG}) "
                    "but was not part of that exact shipped-default generation run. "
                )
                + f"Relative to historical milestone {MILESTONE_COMMIT}, "
                "both modes include prompt drift; "
                + (
                    "phone-on additionally changes generation with the Smartphone Snapshot v13 LoRA"
                    if phone_camera_style
                    else "phone-off does not add the Smartphone Snapshot LoRA"
                )
            ),
            "milestone_commit": MILESTONE_COMMIT,
            "milestone_tag": MILESTONE_TAG,
            "milestone_sampling_path_preserved": False,
            "milestone_sampling_path_status": (
                "unpreserved_phone_on_prompt_and_smartphone_lora_drift"
                if phone_camera_style
                else "unpreserved_phone_off_prompt_drift"
            ),
            "milestone_generation_prompt_changed": True,
            "milestone_smartphone_lora_changed": bool(phone_camera_style),
            "graph_delta_from_milestone": (
                (
                    "phone-on differs from d58732a through prompt drift and the Smartphone "
                    "Snapshot v13 LoRA; "
                    if phone_camera_style
                    else "phone-off differs from d58732a through prompt drift; it does not use "
                    "the Smartphone Snapshot LoRA; "
                )
                + (
                    "deterministic face, iris, and hair-local appearance polish runs after sampling; "
                    if appearance_polish
                    else "appearance polish is disabled; no face, iris, or hair-local polish runs; "
                )
                + (
                    "phone-on skips the optional background postprocess"
                    if phone_camera_style
                    else "phone-off additionally applies an edge-safe background-only natural-lens finish"
                )
            ),
            "revalidation_commit": REVALIDATION_COMMIT,
            "revalidation_tag": REVALIDATION_TAG,
            "revalidation_sampling_path_preserved": True,
            "revalidation_comparison_scope": (
                "Compared with b32ecb9, generation prompt, model and LoRA selection, reference "
                "order, seed, sampler, and scheduler are unchanged. Low v5 corrects the "
                "ParseNet hair label from neck17 to hair13, retaining all other finish constants "
                "and the source-gaze path; optional High adds landmark-aligned brow "
                "and eye-area refinement afterward without resampling. High may transfer "
                "bounded source upper-lid curvature while fixing eye corners and pupil position."
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
            "additional_loras": (
                [_upgrade_phone_style_report()] if phone_camera_style else []
            ),
            "phone_camera_style": bool(phone_camera_style),
            "phone_camera_style_path": (
                str(smartphone_lora_path) if smartphone_lora_path else None
            ),
            "background_rendering_mode": (
                "deep_focus_smartphone_lora"
                if phone_camera_style
                else NATURAL_LENS_BLUR_PROFILE
            ),
            "natural_lens_background_blur": background_blur_report,
            "human_segmentation_model": (
                HUMAN_SEGMENTATION_MODEL if human_segmentation_path else None
            ),
            "human_segmentation_model_path": (
                str(human_segmentation_path) if human_segmentation_path else None
            ),
            "human_segmentation_model_sha256": (
                HUMAN_SEGMENTATION_SHA256 if human_segmentation_path else None
            ),
            "turbo": False,
            "identity_reference": IDENTITY_REFERENCE,
            "identity_reference_path": str(identity_path),
            "identity_reference_sha256": IDENTITY_REFERENCE_SHA256,
            "hair_reference": HAIR_REFERENCE,
            "hair_reference_path": str(hair_path),
            "hair_reference_sha256": HAIR_REFERENCE_SHA256,
            "source_decoded_pixel_sha256": _decoded_pixel_sha256(source),
            "reference_order": [
                "Picture 1: full source photograph intended to guide scene, pose, expression, clothing, lighting layout, and composition at 1.00 MP; because it contains the source face and is encoded as a ReferenceLatent, identity influence is not isolated or proven absent",
                "Picture 2: automatically generated face-interior-free Canny structure guide at 0.50 MP",
                "Picture 3: protected genuine frontal Mitch identity photograph at 0.50 MP",
                "Picture 4: protected genuine isolated hair-material crop at 0.10 MP",
            ],
            "reference_encoded_sizes": reference_sizes,
            "identity_mechanism": (
                "explicit identity mechanism: protected Base-9B step-1600 identity LoRA plus "
                "the genuine-photo Picture 3 ReferenceLatent"
            ),
            "source_semantic_role": (
                "intended scene, pose, expression, clothing, lighting-layout, and composition "
                "conditioning; not an explicit identity-reference role"
            ),
            "source_used_as_identity": None,
            "source_used_as_identity_scope": (
                "legacy field retained as null because actual identity contribution is unproven; "
                "the source is not intended as the explicit identity reference"
            ),
            "source_intended_as_identity_reference": False,
            "source_identity_influence_status": "unisolated_not_proven_absent",
            "source_identity_influence_note": (
                "The full source photograph contains the source face and is encoded as a "
                "ReferenceLatent, so its identity contribution has not been isolated and cannot "
                "be claimed absent."
            ),
            "guide": guide_report,
            "source_latent_initialization": False,
            "face_swap": False,
            "generation_spatial_mask": False,
            "appearance_postprocess_mask": bool(appearance_polish),
            "background_postprocess_mask": not bool(phone_camera_style),
            "background_generation_prompt_changed": True,
            "background_generation_prompt_changed_scope": (
                "legacy field comparing the current recipe with d58732a: both modes have prompt "
                "drift; phone_style_generation_prompt_changed separately reports the extra "
                "phone-on trigger, while the phone-off camera finish remains postprocess-only"
            ),
            "phone_style_generation_prompt_changed": bool(phone_camera_style),
            "revalidation_generation_prompt_changed_by_report_hardening": False,
            "camera_finish_second_model_pass": False,
            "restoration": False,
            "generation_selective_sharpening": False,
            "appearance_local_detail_contrast": bool(appearance_polish),
            "upscaling": False,
            "film_grain_stage": False,
            "second_model_pass": False,
            "prompting_strategy": PROMPTING_STRATEGY,
            "appearance_polish": bool(appearance_polish),
            "appearance_level": appearance_level,
            "appearance_default_level": APPEARANCE_DEFAULT,
            "appearance_profile": appearance_profile if appearance_polish else None,
            "high_attractiveness_status": (
                "optional_stronger_retouch_user_visual_review_required"
                if appearance_level == "high" else "not_selected"
            ),
            "appearance_generation_prompt_changed": False,
            "appearance_scope": (
                (
                    "deterministic face-local, iris-interior source-gaze, and eroded semantic-hair-interior postprocess; "
                    "the appearance-polish stage runs after sampling and does not alter the selected generation model, prompt, references, seed, or sampler; "
                    + (
                        "High additionally applies a bounded source-guided upper-lid warp and symmetric eye contrast while fixing eye corners and pupil position; "
                        if appearance_level == "high" else
                        "eyelid boundaries remain protected; "
                    )
                    + "head outline and hairline remain protected; "
                    if appearance_polish
                    else "appearance polish is disabled, so no face, iris, or hair-local appearance postprocess runs; "
                )
                + (
                    "phone-camera mode leaves the post-generated background unchanged"
                    if phone_camera_style
                    else "phone-off mode changes only the segmented background with an edge-safe natural-lens blur"
                )
            ),
            "appearance_report": polish_report,
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
                "unchanged head yaw, pitch, roll, gaze, pose, crop, and scene geometry",
                "closed lips with no visible teeth when appearance polish is enabled",
                "hairline, forehead, temple, ear, and back-of-head continuity without shadow bands or halos",
                "natural skin, hair, fabric, and background material detail without smoothing or oversharpening",
                "coherent whole-frame lighting, depth, sensor texture, and edge softness",
            ]
            + (
                ["phone-camera rendering keeps the environment legible without synthetic sharpening"]
                if phone_camera_style
                else ["phone-off background separation reads as optical blur without a cutout edge or subject-color halo"]
            ),
        }
        png_info = dict(extra_pnginfo) if isinstance(extra_pnginfo, dict) else {}
        png_info["flux2_klein9b_upgrade_photo_detail_realism_v1"] = report
        saved = comfy_nodes.SaveImage().save_images(
            photo,
            f"{output_folder}/photo",
            extra_pnginfo=png_info,
        )
        if appearance_polish:
            comfy_nodes.SaveImage().save_images(
                raw_photo,
                f"{output_folder}/before-polish",
                extra_pnginfo=png_info,
            )
            comfy_nodes.SaveImage().save_images(
                polish_mask,
                f"{output_folder}/polish-mask",
                extra_pnginfo=png_info,
            )
        if not phone_camera_style:
            comfy_nodes.SaveImage().save_images(
                pre_background_blur_photo,
                f"{output_folder}/before-background-blur",
                extra_pnginfo=png_info,
            )
            comfy_nodes.SaveImage().save_images(
                background_blur_mask,
                f"{output_folder}/background-blur-mask",
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

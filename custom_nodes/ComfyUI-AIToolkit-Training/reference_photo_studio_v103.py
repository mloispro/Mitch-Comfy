from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import folder_paths
import numpy as np
import torch

from . import reference_photo_studio as studio
from .phone_lens_optics import HAZE_PARAMETERS, apply_phone_lens_haze
from .reference_photo_presets import compose_scene_prompt, selected_reference_names


OUTPUT_ROOT = "flux2-reference-studio-v103"
HAZE_STYLE = "Smartphone — slight lens haze"
HAZE_STRENGTH = 1.75


def _apply_haze_to_tensor(image: torch.Tensor) -> tuple[torch.Tensor, dict]:
    source = image.detach().float().cpu().numpy()
    processed = np.stack(
        [apply_phone_lens_haze(frame[..., :3], HAZE_STRENGTH) for frame in source],
        axis=0,
    )
    result = torch.from_numpy(processed).to(device=image.device, dtype=image.dtype)
    metrics = {
        "strength": HAZE_STRENGTH,
        "parameters": HAZE_PARAMETERS,
        "mean_luminance_before": round(float(source[..., :3].mean()), 5),
        "mean_luminance_after": round(float(processed.mean()), 5),
        "contrast_before": round(float(source[..., :3].std()), 5),
        "contrast_after": round(float(processed.std()), 5),
        "extra_model_passes": 0,
    }
    return result, metrics


def _generate_v103(
    reference_names: list[str],
    scene_prompt: str,
    requested_photo_style: str,
    framing: str,
    moment: str,
):
    studio.baseline._require_model(
        "diffusion_models", studio.baseline.MODEL_4B_BASE_NAME
    )
    studio.baseline._require_model("text_encoders", studio.baseline.CLIP_4B_NAME)
    studio.baseline._require_model("vae", studio.baseline.VAE_NAME)
    started = time.perf_counter()

    profile = studio._generation_profile(
        framing, moment, len(reference_names), requested_photo_style
    )
    prepared = studio._prepare_sources(
        reference_names, profile["reference_strategy"], profile["reference_pixels"]
    )

    generation_photo_style = (
        "Smartphone — natural"
        if requested_photo_style == HAZE_STYLE
        else requested_photo_style
    )
    generation_scene = compose_scene_prompt(
        scene_prompt, generation_photo_style, framing, moment
    )
    effective_prompt = studio.baseline._identity_prompt(
        generation_scene,
        reference_count=2,
        identity_token=studio.baseline.IDENTITY_TOKEN,
    )

    model = studio.comfy_nodes.UNETLoader().load_unet(
        studio.baseline.MODEL_4B_BASE_NAME, "default"
    )[0]
    model = studio.comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
        model,
        studio.baseline.PRODUCTION_LORA_NAME,
        profile["lora_strength"],
    )[0]
    clip = studio.comfy_nodes.CLIPLoader().load_clip(
        studio.baseline.CLIP_4B_NAME, "flux2", "default"
    )[0]
    vae = studio.comfy_nodes.VAELoader().load_vae(studio.baseline.VAE_NAME)[0]

    reference_latents = [
        studio.comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
        for image in prepared["latent_images"]
    ]
    positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
    positive = studio.node_helpers.conditioning_set_values(
        positive,
        {"reference_latents": reference_latents},
        append=True,
    )
    negative = studio.comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
    guider = studio.CFGGuider.execute(
        model, positive, negative, profile["guidance_scale"]
    )[0]
    sampler = studio.KSamplerSelect.execute("euler")[0]
    sigmas = studio.Flux2Scheduler.execute(
        studio.baseline.PRODUCTION_STEPS,
        studio.OUTPUT_WIDTH,
        studio.OUTPUT_HEIGHT,
    )[0]
    latent = studio.EmptyFlux2LatentImage.execute(
        studio.OUTPUT_WIDTH,
        studio.OUTPUT_HEIGHT,
        1,
    )[0]

    attempts = []
    selected_photo = None
    selected_score = -1.0
    selected_seed = studio.baseline.PRODUCTION_SEED
    seed_offsets = (1, 0) if moment == "Candid / looking away" else (0, 1)
    for attempt_index, offset in enumerate(seed_offsets):
        attempt_seed = (studio.baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = studio.RandomNoise.execute(attempt_seed)[0]
        sampled = studio.SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        candidate = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        try:
            candidate_embedding, detection_confidence = studio.baseline._face_embedding(
                candidate, f"generated candidate {attempt_index + 1}"
            )
            similarity = studio.baseline._cosine_similarity(
                prepared["identity_centroid"], candidate_embedding
            )
            error = ""
        except RuntimeError as exc:
            similarity = -1.0
            detection_confidence = 0.0
            error = str(exc)
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "seed": attempt_seed,
                "similarity_to_reference_centroid": round(similarity, 4),
                "face_detection_confidence": round(detection_confidence, 4),
                "error": error,
            }
        )
        if similarity > selected_score:
            selected_photo = candidate
            selected_score = similarity
            selected_seed = attempt_seed
        if similarity >= profile["identity_retry_threshold"]:
            break

    if selected_photo is None or selected_score < 0:
        raise RuntimeError("No face was detected in any generated candidate.")

    optical_processing = {
        "applied": False,
        "method": "none",
        "extra_model_passes": 0,
    }
    if requested_photo_style == HAZE_STYLE:
        selected_photo, haze_metrics = _apply_haze_to_tensor(selected_photo)
        optical_processing = {
            "applied": True,
            "method": "deterministic_highlight_driven_phone_lens_scatter",
            **haze_metrics,
        }

    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output_folder = f"{OUTPUT_ROOT}/{len(reference_names)}-references/{run_stamp}"
    report = {
        "schema_version": 3,
        "purpose": "easy_social_photo_v103_with_optional_deterministic_phone_optics",
        "baseline_tag": "flux2-easy-social-v1.0.3-candidate",
        "model": studio.baseline.MODEL_4B_BASE_NAME,
        "text_encoder": studio.baseline.CLIP_4B_NAME,
        "vae": studio.baseline.VAE_NAME,
        "lora_name": studio.baseline.PRODUCTION_LORA_NAME,
        "generation_profile": profile["name"],
        "lora_strength": profile["lora_strength"],
        "source_references": reference_names,
        "source_reference_count": len(reference_names),
        "primary_generation_reference": prepared["selected_reference"],
        "reference_selection": "automatic local face quality and frontal-angle ranking",
        "model_reference_count": len(reference_latents),
        "derived_primary_face_crop": True,
        "reference_strategy": profile["reference_strategy"],
        "reference_pixels_each": profile["reference_pixels"],
        "detected_identity_sources": prepared["detected_sources"],
        "sources_without_detectable_faces": prepared["missing_face_sources"],
        "requested_scene_prompt": scene_prompt,
        "requested_photo_style": requested_photo_style,
        "generation_photo_style": generation_photo_style,
        "scene_prompt_with_generation_presets": generation_scene,
        "framing": framing,
        "moment": moment,
        "effective_prompt": effective_prompt,
        "width": studio.OUTPUT_WIDTH,
        "height": studio.OUTPUT_HEIGHT,
        "steps": studio.baseline.PRODUCTION_STEPS,
        "guidance_scale": profile["guidance_scale"],
        "sampler": "euler",
        "selected_seed": selected_seed,
        "identity_similarity_to_reference_centroid": round(selected_score, 4),
        "identity_retry_threshold": profile["identity_retry_threshold"],
        "identity_attempts": attempts,
        "optical_processing": optical_processing,
        "seconds": round(time.perf_counter() - started, 3),
        "acceptance": (
            "Identity is ranked before deterministic optics. The haze pass performs no AI rerender "
            "and preserves composition and spatial detail. Final subject review remains authoritative."
        ),
    }
    saved = studio.comfy_nodes.SaveImage().save_images(
        selected_photo,
        f"{output_folder}/photo",
        extra_pnginfo={"flux2_reference_studio_v103": report},
    )
    report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return selected_photo, effective_prompt, output_folder, saved


class Flux2EasySocialPhotoV103(studio.Flux2EasySocialPhoto):
    """v1.0.3: frozen v1.0.2 generation plus optional deterministic phone optics."""

    FUNCTION = "generate_v103"

    def generate_v103(
        self,
        face_reference,
        reference_2,
        reference_3,
        reference_4,
        scene_prompt,
        photo_style,
        framing,
        moment,
    ):
        names = selected_reference_names(
            face_reference, reference_2, reference_3, reference_4
        )
        validation = self.VALIDATE_INPUTS(
            face_reference,
            reference_2,
            reference_3,
            reference_4,
            scene_prompt,
            photo_style,
            framing,
            moment,
        )
        if validation is not True:
            raise RuntimeError(validation)
        photo, effective_prompt, output_folder, saved = _generate_v103(
            reference_names=names,
            scene_prompt=scene_prompt,
            requested_photo_style=photo_style,
            framing=framing,
            moment=moment,
        )
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"Saved v1.0.3 photo from {len(names)} reference(s) to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, effective_prompt, output_folder),
        }

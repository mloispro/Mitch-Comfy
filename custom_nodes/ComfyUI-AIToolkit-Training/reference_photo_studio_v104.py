from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import folder_paths

from . import reference_photo_studio as studio
from .camera_finish import apply_natural_phone_finish
from .complex_scene_route import generate_complex_candidate
from .identity_scope import build_multi_person_identity_prompt
from .reference_photo_presets import compose_scene_prompt, selected_reference_names
from .reference_photo_studio_v103 import HAZE_STYLE, _apply_haze_to_tensor
from .scene_quality import (
    apply_scene_guardrails,
    build_scene_contract,
    requires_complex_route,
)


OUTPUT_ROOT = "flux2-reference-studio-v104"


def _direct_identity_prompt(guarded_scene: str, contract: dict) -> str:
    if "background_people" not in set(contract.get("contexts", [])):
        return studio.baseline._identity_prompt(
            guarded_scene,
            reference_count=2,
            identity_token=studio.baseline.IDENTITY_TOKEN,
        )
    return build_multi_person_identity_prompt(
        guarded_scene,
        studio.baseline.IDENTITY_TOKEN,
    )


def _generate_direct_candidate(
    prepared: dict,
    guarded_scene: str,
    profile: dict,
    moment: str,
    contract: dict,
) -> dict:
    started = time.perf_counter()
    effective_prompt = _direct_identity_prompt(guarded_scene, contract)
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
    selected_confidence = 0.0
    selected_seed = studio.baseline.PRODUCTION_SEED
    seed_offsets = (1, 0) if moment == "Candid / looking away" else (0, 1)
    for attempt_index, offset in enumerate(seed_offsets):
        seed = (studio.baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = studio.RandomNoise.execute(seed)[0]
        sampled = studio.SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        candidate = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        try:
            embedding, confidence = studio.baseline._face_embedding(
                candidate, f"generated candidate {attempt_index + 1}"
            )
            similarity = studio.baseline._cosine_similarity(
                prepared["identity_centroid"], embedding
            )
            error = ""
        except RuntimeError as exc:
            similarity = -1.0
            confidence = 0.0
            error = str(exc)
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "seed": seed,
                "similarity_to_reference_centroid": round(similarity, 4),
                "face_detection_confidence": round(confidence, 4),
                "error": error,
            }
        )
        if similarity > selected_score:
            selected_photo = candidate
            selected_score = similarity
            selected_confidence = confidence
            selected_seed = seed
        if similarity >= profile["identity_retry_threshold"]:
            break
    if selected_photo is None or selected_score < 0:
        raise RuntimeError("No face was detected in any generated candidate.")
    return {
        "photo": selected_photo,
        "effective_prompt": effective_prompt,
        "similarity": selected_score,
        "detection_confidence": selected_confidence,
        "selected_seed": selected_seed,
        "attempts": attempts,
        "layout_stage": None,
        "identity_stage": {
            "model": studio.baseline.MODEL_4B_BASE_NAME,
            "lora": studio.baseline.PRODUCTION_LORA_NAME,
            "steps": studio.baseline.PRODUCTION_STEPS,
            "seconds": round(time.perf_counter() - started, 3),
        },
    }


def _generate_v104(
    reference_names: list[str],
    scene_prompt: str,
    requested_photo_style: str,
    framing: str,
    moment: str,
):
    studio.baseline._require_model("diffusion_models", studio.baseline.MODEL_4B_BASE_NAME)
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
    contract = build_scene_contract(
        scene_prompt, generation_photo_style, framing, moment
    )
    generation_scene = compose_scene_prompt(
        scene_prompt, generation_photo_style, framing, moment
    )
    guarded_scene = apply_scene_guardrails(generation_scene, contract)

    complex_requested = requires_complex_route(contract)
    route_error = ""
    if complex_requested:
        candidate = generate_complex_candidate(
            prepared, generation_scene, contract, profile
        )
        generation_route = "complex_deep_focus_layout_plus_masked_4b_identity"
    else:
        candidate = _generate_direct_candidate(
            prepared, guarded_scene, profile, moment, contract
        )
        generation_route = "direct_4b_identity"

    selected_photo = candidate["photo"]
    optical_processing = {
        "applied": False,
        "method": "none",
        "extra_model_passes": 0,
    }
    if generation_photo_style == "Smartphone — natural":
        selected_photo, optical_processing = apply_natural_phone_finish(selected_photo)
    if requested_photo_style == HAZE_STYLE:
        selected_photo, haze_metrics = _apply_haze_to_tensor(selected_photo)
        optical_processing = {
            "applied": True,
            "method": "restrained_phone_finish_plus_highlight_driven_lens_scatter",
            "phone_finish": optical_processing,
            **haze_metrics,
        }

    identity_passed = candidate["similarity"] >= profile["identity_retry_threshold"]
    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output_folder = f"{OUTPUT_ROOT}/{len(reference_names)}-references/{run_stamp}"
    report = {
        "schema_version": 4,
        "purpose": "easy_social_photo_v104_automatic_scene_complexity_routing",
        "generation_baseline": "flux2-easy-social-v1.0.3",
        "generation_route": generation_route,
        "complex_route_requested": complex_requested,
        "complex_route_error": route_error,
        "model": candidate["identity_stage"]["model"],
        "text_encoder": studio.baseline.CLIP_4B_NAME,
        "vae": studio.baseline.VAE_NAME,
        "lora_name": studio.baseline.PRODUCTION_LORA_NAME,
        "generation_profile": profile["name"],
        "lora_strength": profile["lora_strength"],
        "source_references": reference_names,
        "source_reference_count": len(reference_names),
        "primary_generation_reference": prepared["selected_reference"],
        "reference_selection": "automatic local face quality and frontal-angle ranking",
        "model_reference_count": 3 if candidate["layout_stage"] else len(prepared["latent_images"]),
        "derived_primary_face_crop": True,
        "reference_strategy": profile["reference_strategy"],
        "reference_pixels_each": profile["reference_pixels"],
        "detected_identity_sources": prepared["detected_sources"],
        "sources_without_detectable_faces": prepared["missing_face_sources"],
        "requested_scene_prompt": scene_prompt,
        "requested_photo_style": requested_photo_style,
        "generation_photo_style": generation_photo_style,
        "scene_prompt_with_generation_presets": generation_scene,
        "scene_contract": contract,
        "framing": framing,
        "moment": moment,
        "effective_prompt": candidate["effective_prompt"],
        "width": studio.OUTPUT_WIDTH,
        "height": studio.OUTPUT_HEIGHT,
        "steps": studio.baseline.PRODUCTION_STEPS,
        "guidance_scale": profile["guidance_scale"],
        "sampler": "euler",
        "selected_seed": candidate["selected_seed"],
        "identity_similarity_to_reference_centroid": round(candidate["similarity"], 4),
        "identity_detection_confidence": round(candidate["detection_confidence"], 4),
        "identity_retry_threshold": profile["identity_retry_threshold"],
        "identity_gate_status": "passed" if identity_passed else "review_required",
        "identity_attempts": candidate["attempts"],
        "layout_stage": candidate["layout_stage"],
        "identity_stage": candidate["identity_stage"],
        "optical_processing": optical_processing,
        "seconds": round(time.perf_counter() - started, 3),
        "acceptance": (
            "The same simple controls automatically route ordinary photos through the fast 4B LoRA path. Crowds, groups, "
            "reflections, and combined crowd/traffic prompts first build a coherent deep-focus Z-Image Base scene, promote "
            "the detected main layout subject with a deterministic framing-aware crop, and isolate that subject with local "
            "human segmentation. FLUX.2 Base 4B plus the selected identity LoRA then regenerates only that masked subject; "
            "the unmasked people, vehicles, architecture, furniture, and depth structure remain owned by the scene model. "
            "This is subject-region latent generation, not a face-swap overlay. Every route requires a recognizable, "
            "materially detailed environment under realistic moderate-to-deep focus instead of default portrait blur. "
            "Complex scenes protect a face-relative full-head region before generation and reject final seeds that fail "
            "the narrow crown/head-core integrity check. "
            "Phone haze runs only after identity selection and does not blur scene detail. Tested local VLM critics and an "
            "SDXL refiner are deliberately excluded. Final subject and scene review remains authoritative."
        ),
    }
    saved = studio.comfy_nodes.SaveImage().save_images(
        selected_photo,
        f"{output_folder}/photo",
        extra_pnginfo={"flux2_reference_studio_v104": report},
    )
    report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return selected_photo, candidate["effective_prompt"], output_folder, saved, report


class Flux2EasySocialPhotoV104(studio.Flux2EasySocialPhoto):
    """v1.0.4: simple controls with automatic fast or complex scene routing."""

    FUNCTION = "generate_v104"

    def generate_v104(
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
        photo, effective_prompt, output_folder, saved, report = _generate_v104(
            reference_names=names,
            scene_prompt=scene_prompt,
            requested_photo_style=photo_style,
            framing=framing,
            moment=moment,
        )
        contexts = ", ".join(report["scene_contract"]["contexts"]) or "general"
        route = "complex" if report["complex_route_requested"] else "fast"
        gate = report["identity_gate_status"].replace("_", " ")
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"{route.capitalize()} route; identity {gate}; scene rules: {contexts}. "
                    f"Saved v1.0.4 photo from {len(names)} reference(s) to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, effective_prompt, output_folder),
        }

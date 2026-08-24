from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import folder_paths
import numpy as np

from . import reference_photo_studio as studio
from .camera_finish import apply_natural_phone_finish
from .identity_leakage import evaluate_identity_scope
from .identity_scope import build_multi_person_identity_prompt
from .reference_photo_presets import (
    FRAMINGS,
    MOMENTS,
    PHOTO_STYLES,
    compose_scene_prompt,
    selected_reference_names,
)
from .reference_photo_studio_v103 import HAZE_STYLE, _apply_haze_to_tensor
from .scene_constraints import (
    build_hard_scene_constraints,
    build_scene_topology,
    scene_object_targets,
)
from .scene_objects import count_scene_objects, guarded_multi_person_count_error
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


def _identity_scope_for_photo(
    photo,
    identity_centroid: np.ndarray,
    main_identity_minimum: float,
) -> dict:
    rgb = np.clip(
        photo[0].detach().float().cpu().numpy() * 255.0, 0, 255
    ).astype(np.uint8)
    faces = studio.baseline._face_analyzer().get(
        cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    )
    return evaluate_identity_scope(
        [np.asarray(face.normed_embedding, dtype=np.float32) for face in faces],
        [face.bbox for face in faces],
        [float(face.det_score) for face in faces],
        identity_centroid,
        main_identity_minimum,
    ).as_dict()


def _generate_guarded_multi_person_candidate(
    prepared: dict,
    guarded_scene: str,
    profile: dict,
    moment: str,
    contract: dict,
) -> dict:
    """Generate the complete scene once, then reject identity leaks and count errors."""
    started = time.perf_counter()
    hard_constraints = build_hard_scene_constraints(contract)
    topology = build_scene_topology(contract)
    concise_scene = " ".join(
        item.strip()
        for item in (
            str(contract.get("user_scene", "")),
            PHOTO_STYLES.get(str(contract.get("camera_style", "")), ""),
            FRAMINGS.get(str(contract.get("framing", "")), ""),
            MOMENTS.get(str(contract.get("moment", "")), ""),
            (
                "One coherent in-camera exposure with continuous perspective, lighting, focus falloff, sensor texture, "
                "and occlusion across subject and environment. Keep the real setting structurally readable with natural "
                "distance-dependent detail, not portrait blur, CGI polish, a cutout edge, or a separately sharpened face."
            ),
        )
        if item.strip()
    )
    effective_prompt = build_multi_person_identity_prompt(
        concise_scene,
        studio.baseline.IDENTITY_TOKEN,
        priority_constraints=" ".join(
            item.strip() for item in (hard_constraints, topology) if item.strip()
        ),
    )
    # A strong global identity LoRA can tint secondary faces toward the trained
    # identity. Keep enough strength for Mitch while references and the token do
    # the rest of the identity work.
    lora_strength = min(float(profile["lora_strength"]), 0.50)
    model = studio.comfy_nodes.UNETLoader().load_unet(
        studio.baseline.MODEL_4B_BASE_NAME, "default"
    )[0]
    model = studio.comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
        model,
        studio.baseline.PRODUCTION_LORA_NAME,
        lora_strength,
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

    contexts = set(contract.get("contexts", []))
    requires_multiple_people = bool(
        contexts.intersection({"background_people", "group_photo", "crowd", "reflection"})
    )
    targets = scene_object_targets(contract)
    seed_offsets = (
        (1, 0, 2)
        if moment == "Candid / looking away"
        else (0, 1, 2)
    )
    attempts = []
    selected_photo = None
    selected_scope = None
    selected_counts = None
    selected_seed = None
    preferred_identity_target = float(profile["identity_retry_threshold"])
    for attempt_index, offset in enumerate(seed_offsets):
        seed = (studio.baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = studio.RandomNoise.execute(seed)[0]
        sampled = studio.SamplerCustomAdvanced.execute(
            noise, guider, sampler, sigmas, latent
        )[0]
        candidate = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        scope = _identity_scope_for_photo(
            candidate,
            prepared["identity_centroid"],
            profile["identity_retry_threshold"],
        )
        counts = count_scene_objects(candidate)
        count_error = guarded_multi_person_count_error(
            counts,
            targets,
            requires_multiple_people=requires_multiple_people,
        )
        failures = list(scope["failures"])
        if count_error:
            failures.append("scene_object_count_mismatch")
        accepted = not failures
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "seed": seed,
                "accepted": accepted,
                "failures": failures,
                "identity_scope": scope,
                "scene_object_targets": targets,
                "scene_object_counts": counts,
                "scene_object_count_error": count_error,
                "preferred_identity_target": preferred_identity_target,
                "meets_preferred_identity_target": (
                    scope["main_identity_similarity"] >= preferred_identity_target
                ),
            }
        )
        if accepted:
            if (
                selected_scope is None
                or scope["main_identity_similarity"]
                > selected_scope["main_identity_similarity"]
            ):
                selected_photo = candidate
                selected_scope = scope
                selected_counts = counts
                selected_seed = seed
            if scope["main_identity_similarity"] >= preferred_identity_target:
                break

    if selected_photo is None:
        compact_failures = [
            {
                "seed": item["seed"],
                "failures": item["failures"],
                "identity": item["identity_scope"]["main_identity_similarity"],
                "counts": {
                    "person": item["scene_object_counts"].get("person", 0),
                    "vehicle": item["scene_object_counts"].get("vehicle", 0),
                },
            }
            for item in attempts
        ]
        raise RuntimeError(
            f"FLUX.2 generated {len(attempts)} multi-person candidates, but the identity-leakage "
            "and scene-count gates rejected all of them. No bad image was saved. "
            f"Attempts: {json.dumps(compact_failures)}"
        )

    return {
        "photo": selected_photo,
        "effective_prompt": effective_prompt,
        "similarity": selected_scope["main_identity_similarity"],
        "detection_confidence": selected_scope["main_detection_confidence"],
        "selected_seed": selected_seed,
        "attempts": attempts,
        "layout_stage": None,
        "identity_stage": {
            "mode": "single_pass_full_frame_multi_person",
            "model": studio.baseline.MODEL_4B_BASE_NAME,
            "lora": studio.baseline.PRODUCTION_LORA_NAME,
            "lora_strength": lora_strength,
            "steps": studio.baseline.PRODUCTION_STEPS,
            "identity_scope_gate": selected_scope,
            "preferred_identity_target": preferred_identity_target,
            "scene_object_targets": targets,
            "scene_object_counts": selected_counts,
            "scene_object_count_gate": "passed",
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
        candidate = _generate_guarded_multi_person_candidate(
            prepared, guarded_scene, profile, moment, contract
        )
        generation_route = "single_pass_4b_multi_person_with_leakage_and_count_gates"
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
        "schema_version": 5,
        "purpose": "easy_social_photo_v104_single_pass_multi_person_guardrails",
        "generation_baseline": "flux2-easy-social-v1.0.3",
        "generation_route": generation_route,
        "complex_route_requested": complex_requested,
        "complex_route_error": route_error,
        "model": candidate["identity_stage"]["model"],
        "text_encoder": studio.baseline.CLIP_4B_NAME,
        "vae": studio.baseline.VAE_NAME,
        "lora_name": studio.baseline.PRODUCTION_LORA_NAME,
        "generation_profile": profile["name"],
        "lora_strength": candidate["identity_stage"].get(
            "lora_strength", profile["lora_strength"]
        ),
        "source_references": reference_names,
        "source_reference_count": len(reference_names),
        "primary_generation_reference": prepared["selected_reference"],
        "reference_selection": "automatic local face quality and frontal-angle ranking",
        "model_reference_count": len(prepared["latent_images"]),
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
            "Ordinary solo photos use the fast FLUX.2 Base 4B identity path. Multi-person, crowd, traffic, reflection, and "
            "group requests use the same model in one whole-frame generation, with a deliberately restrained identity LoRA "
            "strength and explicit identity-separation, object-count, camera-ownership, and scene-topology instructions. "
            "Each candidate is rejected unless the requested identity is detected above threshold, no detected secondary "
            "face exceeds the identity-leakage or duplicate-face limits, and local YOLO counts match every explicit person "
            "and vehicle count. Failed candidates trigger up to three deterministic seeds; the first fully valid result "
            "is returned. If every seed fails, the node returns an error and saves no misleading image. This "
            "avoids the pasted-subject appearance inherent to masked two-stage compositing. The gates cannot judge every "
            "background physics or aesthetic issue, so final visual review remains authoritative. Phone optics run only "
            "after candidate acceptance and do not add a model or refiner pass."
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
        route = "guarded multi-person" if report["complex_route_requested"] else "fast solo"
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

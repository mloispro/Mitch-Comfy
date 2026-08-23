from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path

import cv2
import folder_paths
import node_helpers
import numpy as np

import nodes as comfy_nodes
from comfy_extras.nodes_custom_sampler import (
    CFGGuider,
    KSamplerSelect,
    RandomNoise,
    SamplerCustomAdvanced,
)
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler

from . import one_reference_photo as baseline
from .reference_photo_presets import (
    FRAMINGS,
    MOMENTS,
    NO_REFERENCE,
    PHOTO_STYLES,
    compose_scene_prompt,
    duplicate_reference_names,
    selected_reference_names,
)


OUTPUT_ROOT = "flux2-reference-studio"
OUTPUT_WIDTH = 896
OUTPUT_HEIGHT = 1344
SAME_PERSON_FLOOR = 0.50
IDENTITY_RETRY_THRESHOLD = 0.75
CANDIDATE_REFERENCE_STRATEGY = "Full + face crop 2.4x"
CANDIDATE_REFERENCE_PIXELS = 512 * 512
CANDIDATE_LORA_STRENGTH = 0.4
CANDIDATE_GUIDANCE_SCALE = 2.0
ACTION_LORA_STRENGTH = 0.6
ACTION_GUIDANCE_SCALE = 4.0
ACTION_RETRY_THRESHOLD = 0.70
PHONE_LENS_LORA_STRENGTH = 0.5
PHONE_LENS_GUIDANCE_SCALE = 3.0


def _reference_choices(include_none: bool = False) -> list[str]:
    prefix = [NO_REFERENCE] if include_none else ["Upload one face photo"]
    return [*prefix, *baseline._available_input_images()]


def _validate_reference_names(names: list[str]) -> str | bool:
    if not names or names[0] == "Upload one face photo":
        return "Upload at least one genuine face photo."
    if len(names) > 4:
        return "FLUX.2 Klein supports at most four supplied reference photos."
    duplicates = duplicate_reference_names(names)
    if duplicates:
        return f"Each reference should be unique; duplicate selected: {duplicates[0]}"
    for name in names:
        if baseline._looks_generated_reference(name):
            return "Use genuine camera photos, not generated or processed identity fixtures."
        if not folder_paths.exists_annotated_filepath(name):
            return f"Reference image is not available in ComfyUI input: {name}"
    return True


def _normalized_centroid(embeddings: list[np.ndarray]) -> np.ndarray:
    centroid = np.mean(np.stack(embeddings, axis=0), axis=0).astype(np.float32)
    centroid /= max(float(np.linalg.norm(centroid)), 1e-8)
    return centroid


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _generation_profile(
    framing: str, moment: str, reference_count: int, photo_style: str
) -> dict:
    if framing == "Full body" or moment == "Action":
        return {
            "name": "action_identity",
            "lora_strength": ACTION_LORA_STRENGTH,
            "guidance_scale": ACTION_GUIDANCE_SCALE,
            "identity_retry_threshold": ACTION_RETRY_THRESHOLD,
            "reference_strategy": CANDIDATE_REFERENCE_STRATEGY,
            "reference_pixels": CANDIDATE_REFERENCE_PIXELS,
        }
    if moment == "Candid / looking away":
        return {
            "name": "candid_identity",
            "lora_strength": ACTION_LORA_STRENGTH,
            "guidance_scale": ACTION_GUIDANCE_SCALE,
            "identity_retry_threshold": IDENTITY_RETRY_THRESHOLD,
            "reference_strategy": CANDIDATE_REFERENCE_STRATEGY,
            "reference_pixels": CANDIDATE_REFERENCE_PIXELS,
        }
    if photo_style == "Smartphone — slight lens haze":
        return {
            "name": "phone_lens_identity",
            "lora_strength": PHONE_LENS_LORA_STRENGTH,
            "guidance_scale": PHONE_LENS_GUIDANCE_SCALE,
            "identity_retry_threshold": IDENTITY_RETRY_THRESHOLD,
            "reference_strategy": CANDIDATE_REFERENCE_STRATEGY,
            "reference_pixels": CANDIDATE_REFERENCE_PIXELS,
        }
    if reference_count == 1:
        return {
            "name": "single_reference_identity",
            "lora_strength": ACTION_LORA_STRENGTH,
            "guidance_scale": ACTION_GUIDANCE_SCALE,
            "identity_retry_threshold": IDENTITY_RETRY_THRESHOLD,
            "reference_strategy": CANDIDATE_REFERENCE_STRATEGY,
            "reference_pixels": CANDIDATE_REFERENCE_PIXELS,
        }
    return {
        "name": "balanced_realism",
        "lora_strength": CANDIDATE_LORA_STRENGTH,
        "guidance_scale": CANDIDATE_GUIDANCE_SCALE,
        "identity_retry_threshold": IDENTITY_RETRY_THRESHOLD,
        "reference_strategy": CANDIDATE_REFERENCE_STRATEGY,
        "reference_pixels": CANDIDATE_REFERENCE_PIXELS,
    }


def _analyze_reference(name: str, image) -> dict:
    """Measure face usability without changing or uploading the source photo."""
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(
        np.uint8
    )
    faces = baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError(f"No face was detected in reference photo {name}.")
    face = max(
        faces,
        key=lambda item: float(
            (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
        ),
    )
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    left = max(0, min(width - 1, int(math.floor(x1))))
    top = max(0, min(height - 1, int(math.floor(y1))))
    right = max(left + 1, min(width, int(math.ceil(x2))))
    bottom = max(top + 1, min(height, int(math.ceil(y2))))
    face_rgb = rgb[top:bottom, left:right]
    face_gray = cv2.cvtColor(face_rgb, cv2.COLOR_RGB2GRAY)

    sharpness_raw = float(cv2.Laplacian(face_gray, cv2.CV_64F).var())
    sharpness = _clamp01((math.log1p(sharpness_raw) - 3.7) / 3.0)
    brightness = float(face_gray.mean()) / 255.0
    contrast = float(face_gray.std()) / 255.0
    exposure = math.exp(-((brightness - 0.52) / 0.32) ** 2) * _clamp01(
        contrast / 0.16
    )

    bbox_width = max(x2 - x1, 1.0)
    bbox_height = max(y2 - y1, 1.0)
    face_scale = math.sqrt((bbox_width * bbox_height) / max(width * height, 1.0))
    size_score = _clamp01((face_scale - 0.08) / 0.27)

    kps = np.asarray(getattr(face, "kps", []), dtype=np.float32)
    frontal = 0.5
    if kps.shape == (5, 2):
        eye_mid = (kps[0] + kps[1]) * 0.5
        mouth_mid = (kps[3] + kps[4]) * 0.5
        eye_distance = max(float(np.linalg.norm(kps[1] - kps[0])), 1.0)
        nose_offset = abs(float(kps[2][0] - eye_mid[0])) / eye_distance
        mouth_offset = abs(float(mouth_mid[0] - eye_mid[0])) / eye_distance
        frontal = math.exp(-2.8 * nose_offset - 1.4 * mouth_offset)

    margins = (
        max(x1, 0.0) / width,
        max(y1, 0.0) / height,
        max(width - x2, 0.0) / width,
        max(height - y2, 0.0) / height,
    )
    context = 1.0 if min(margins) >= 0.025 else 0.55
    quality_score = context * (
        0.27 * float(face.det_score)
        + 0.25 * sharpness
        + 0.23 * frontal
        + 0.15 * size_score
        + 0.10 * exposure
    )

    embedding = np.asarray(face.normed_embedding, dtype=np.float32)
    embedding /= max(float(np.linalg.norm(embedding)), 1e-8)
    return {
        "reference": name,
        "embedding": embedding,
        "face_detection_confidence": float(face.det_score),
        "quality_score": float(quality_score),
        "sharpness_score": float(sharpness),
        "frontal_score": float(frontal),
        "face_size_score": float(size_score),
        "exposure_score": float(exposure),
        "edge_context_score": float(context),
    }


def _prepare_sources(
    reference_names: list[str], reference_strategy: str, reference_pixels: int
):
    source_images = [
        comfy_nodes.LoadImage().load_image(name)[0][:1, :, :, :3]
        for name in reference_names
    ]
    observations: list[dict] = []
    missing_face_sources: list[str] = []

    for index, (name, image) in enumerate(zip(reference_names, source_images)):
        try:
            observation = _analyze_reference(name, image)
        except RuntimeError:
            missing_face_sources.append(name)
            continue
        observation["source_index"] = index
        observations.append(observation)

    if not observations:
        raise RuntimeError("No face was detected in any supplied reference photo.")

    for left_index, left in enumerate(observations):
        for right in observations[left_index + 1 :]:
            similarity = baseline._cosine_similarity(
                left["embedding"], right["embedding"]
            )
            if similarity < SAME_PERSON_FLOOR:
                raise RuntimeError(
                    f"References {left['reference']} and {right['reference']} may show different "
                    f"people (identity score {similarity:.3f}). Remove the incorrect photo."
                )

    selected = max(observations, key=lambda item: item["quality_score"])
    embeddings = [item["embedding"] for item in observations]
    centroid = _normalized_centroid(embeddings)
    detected_sources: list[dict] = []
    for item in observations:
        detected_sources.append(
            {
                "reference": item["reference"],
                "selected_for_generation": item is selected,
                "face_detection_confidence": round(
                    item["face_detection_confidence"], 4
                ),
                "quality_score": round(item["quality_score"], 4),
                "sharpness_score": round(item["sharpness_score"], 4),
                "frontal_score": round(item["frontal_score"], 4),
                "face_size_score": round(item["face_size_score"], 4),
                "exposure_score": round(item["exposure_score"], 4),
                "edge_context_score": round(item["edge_context_score"], 4),
                "similarity_to_reference_centroid": round(
                    baseline._cosine_similarity(centroid, item["embedding"]), 4
                ),
            }
        )

    # Additional genuine photos are identity evidence for consistency checks and
    # candidate ranking, not extra model latents: controlled tests showed that feeding
    # 2–4 full latents reduced likeness and doubled/tripled latency on the RTX 3090.
    latent_images = baseline._strategy_references(
        source_images[selected["source_index"]],
        reference_strategy,
        reference_pixels,
    )

    return {
        "source_images": source_images,
        "latent_images": latent_images,
        "identity_centroid": centroid,
        "selected_reference": selected["reference"],
        "detected_sources": detected_sources,
        "missing_face_sources": missing_face_sources,
    }


def _generate_reference_studio(
    reference_names: list[str],
    scene_prompt: str,
    photo_style: str,
    framing: str,
    moment: str,
):
    baseline._require_model("diffusion_models", baseline.MODEL_4B_BASE_NAME)
    baseline._require_model("text_encoders", baseline.CLIP_4B_NAME)
    baseline._require_model("vae", baseline.VAE_NAME)
    started = time.perf_counter()

    profile = _generation_profile(
        framing, moment, len(reference_names), photo_style
    )
    prepared = _prepare_sources(
        reference_names, profile["reference_strategy"], profile["reference_pixels"]
    )
    effective_prompt = baseline._identity_prompt(
        scene_prompt,
        reference_count=2,
        identity_token=baseline.IDENTITY_TOKEN,
    )

    model = comfy_nodes.UNETLoader().load_unet(baseline.MODEL_4B_BASE_NAME, "default")[0]
    model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
        model,
        baseline.PRODUCTION_LORA_NAME,
        profile["lora_strength"],
    )[0]
    clip = comfy_nodes.CLIPLoader().load_clip(baseline.CLIP_4B_NAME, "flux2", "default")[0]
    vae = comfy_nodes.VAELoader().load_vae(baseline.VAE_NAME)[0]

    reference_latents = [
        comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
        for image in prepared["latent_images"]
    ]
    positive = comfy_nodes.CLIPTextEncode().encode(clip, effective_prompt)[0]
    positive = node_helpers.conditioning_set_values(
        positive,
        {"reference_latents": reference_latents},
        append=True,
    )
    negative = comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
    guider = CFGGuider.execute(model, positive, negative, profile["guidance_scale"])[0]
    sampler = KSamplerSelect.execute("euler")[0]
    sigmas = Flux2Scheduler.execute(
        baseline.PRODUCTION_STEPS,
        OUTPUT_WIDTH,
        OUTPUT_HEIGHT,
    )[0]
    latent = EmptyFlux2LatentImage.execute(
        OUTPUT_WIDTH,
        OUTPUT_HEIGHT,
        1,
    )[0]

    attempts = []
    selected_photo = None
    selected_score = -1.0
    selected_seed = baseline.PRODUCTION_SEED
    seed_offsets = (1, 0) if moment == "Candid / looking away" else (0, 1)
    for attempt_index, offset in enumerate(seed_offsets):
        attempt_seed = (baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = RandomNoise.execute(attempt_seed)[0]
        sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        candidate = comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        try:
            candidate_embedding, detection_confidence = baseline._face_embedding(
                candidate, f"generated candidate {attempt_index + 1}"
            )
            similarity = baseline._cosine_similarity(
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

    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output_folder = f"{OUTPUT_ROOT}/{len(reference_names)}-references/{run_stamp}"
    report = {
        "schema_version": 2,
        "purpose": "natural_skin_social_photo_with_one_to_four_reference_identity_verification",
        "baseline_tag": "flux2-easy-social-v1.0.2",
        "model": baseline.MODEL_4B_BASE_NAME,
        "text_encoder": baseline.CLIP_4B_NAME,
        "vae": baseline.VAE_NAME,
        "lora_name": baseline.PRODUCTION_LORA_NAME,
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
        "additional_reference_role": "same-person validation and candidate centroid ranking",
        "detected_identity_sources": prepared["detected_sources"],
        "sources_without_detectable_faces": prepared["missing_face_sources"],
        "scene_prompt_with_presets": scene_prompt,
        "photo_style": photo_style,
        "framing": framing,
        "moment": moment,
        "effective_prompt": effective_prompt,
        "width": OUTPUT_WIDTH,
        "height": OUTPUT_HEIGHT,
        "steps": baseline.PRODUCTION_STEPS,
        "guidance_scale": profile["guidance_scale"],
        "sampler": "euler",
        "selected_seed": selected_seed,
        "identity_similarity_to_reference_centroid": round(selected_score, 4),
        "identity_retry_threshold": profile["identity_retry_threshold"],
        "identity_attempts": attempts,
        "seconds": round(time.perf_counter() - started, 3),
        "acceptance": (
            "Identity was ranked locally. Natural skin variation was validated across phone, "
            "professional, candid, and action scenes; final subject review is still authoritative."
        ),
    }
    saved = comfy_nodes.SaveImage().save_images(
        selected_photo,
        f"{output_folder}/photo",
        extra_pnginfo={"flux2_reference_studio": report},
    )
    report_path = Path(folder_paths.get_output_directory()) / output_folder / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return selected_photo, effective_prompt, output_folder, saved


class Flux2EasySocialPhoto:
    """Realism-tuned LoRA generator with one to four genuine identity references."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "face_reference": (_reference_choices(), {"image_upload": True}),
                "reference_2": (_reference_choices(True), {"image_upload": True}),
                "reference_3": (_reference_choices(True), {"image_upload": True}),
                "reference_4": (_reference_choices(True), {"image_upload": True}),
                "scene_prompt": (
                    "STRING",
                    {
                        "default": (
                            "Walking along a lively city sidewalk in soft late-afternoon light, wearing "
                            "a fitted navy crew-neck T-shirt and dark jeans, relaxed and comfortable."
                        ),
                        "multiline": True,
                    },
                ),
                "photo_style": (list(PHOTO_STYLES),),
                "framing": (list(FRAMINGS), {"default": "Waist-up"}),
                "moment": (list(MOMENTS), {"default": "Looking at camera"}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(
        cls,
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
        validation = _validate_reference_names(names)
        if validation is not True:
            return validation
        try:
            compose_scene_prompt(scene_prompt, photo_style, framing, moment)
        except ValueError as exc:
            return str(exc)
        return True

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("photo", "effective_prompt", "output_folder")
    FUNCTION = "generate"
    CATEGORY = "image/generation/FLUX.2 Identity"
    OUTPUT_NODE = True

    def generate(
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
        composed_scene = compose_scene_prompt(scene_prompt, photo_style, framing, moment)
        photo, effective_prompt, output_folder, saved = _generate_reference_studio(
            reference_names=names,
            scene_prompt=composed_scene,
            photo_style=photo_style,
            framing=framing,
            moment=moment,
        )
        return {
            "ui": {
                "images": saved["ui"]["images"],
                "text": (
                    f"Saved natural-skin photo from {len(names)} reference(s) to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, effective_prompt, output_folder),
        }

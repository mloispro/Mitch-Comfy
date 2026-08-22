from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

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
SAME_PERSON_FLOOR = 0.50
IDENTITY_RETRY_THRESHOLD = 0.75
CANDIDATE_REFERENCE_STRATEGY = "Full + face crop 2.4x"
CANDIDATE_REFERENCE_PIXELS = 512 * 512
CANDIDATE_LORA_STRENGTH = 0.4
CANDIDATE_GUIDANCE_SCALE = 2.0


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


def _prepare_sources(reference_names: list[str]):
    source_images = [
        comfy_nodes.LoadImage().load_image(name)[0][:1, :, :, :3]
        for name in reference_names
    ]
    embeddings: list[np.ndarray] = []
    detected_sources: list[dict] = []
    missing_face_sources: list[str] = []

    primary_embedding, primary_confidence = baseline._face_embedding(
        source_images[0], "the primary reference photo"
    )
    embeddings.append(primary_embedding)
    detected_sources.append(
        {
            "reference": reference_names[0],
            "face_detection_confidence": round(primary_confidence, 4),
            "similarity_to_primary": 1.0,
        }
    )

    for name, image in zip(reference_names[1:], source_images[1:]):
        try:
            embedding, confidence = baseline._face_embedding(image, f"reference photo {name}")
        except RuntimeError:
            missing_face_sources.append(name)
            continue
        similarity = baseline._cosine_similarity(primary_embedding, embedding)
        if similarity < SAME_PERSON_FLOOR:
            raise RuntimeError(
                f"Reference {name} may show a different person (identity score {similarity:.3f}). "
                "Remove it or choose another genuine photo of the same subject."
            )
        embeddings.append(embedding)
        detected_sources.append(
            {
                "reference": name,
                "face_detection_confidence": round(confidence, 4),
                "similarity_to_primary": round(similarity, 4),
            }
        )

    # Additional genuine photos are identity evidence for consistency checks and
    # candidate ranking, not extra model latents: controlled tests showed that feeding
    # 2–4 full latents reduced likeness and doubled/tripled latency on the RTX 3090.
    latent_images = baseline._strategy_references(
        source_images[0],
        CANDIDATE_REFERENCE_STRATEGY,
        CANDIDATE_REFERENCE_PIXELS,
    )

    return {
        "source_images": source_images,
        "latent_images": latent_images,
        "identity_centroid": _normalized_centroid(embeddings),
        "detected_sources": detected_sources,
        "missing_face_sources": missing_face_sources,
    }


def _generate_multi_reference(
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

    prepared = _prepare_sources(reference_names)
    effective_prompt = baseline._identity_prompt(
        scene_prompt,
        reference_count=2,
        identity_token=baseline.IDENTITY_TOKEN,
    )

    model = comfy_nodes.UNETLoader().load_unet(baseline.MODEL_4B_BASE_NAME, "default")[0]
    model = comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
        model,
        baseline.PRODUCTION_LORA_NAME,
        CANDIDATE_LORA_STRENGTH,
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
    guider = CFGGuider.execute(model, positive, negative, CANDIDATE_GUIDANCE_SCALE)[0]
    sampler = KSamplerSelect.execute("euler")[0]
    sigmas = Flux2Scheduler.execute(
        baseline.PRODUCTION_STEPS,
        baseline.OUTPUT_WIDTH,
        baseline.OUTPUT_HEIGHT,
    )[0]
    latent = EmptyFlux2LatentImage.execute(
        baseline.OUTPUT_WIDTH,
        baseline.OUTPUT_HEIGHT,
        1,
    )[0]

    attempts = []
    selected_photo = None
    selected_score = -1.0
    selected_seed = baseline.PRODUCTION_SEED
    for offset in range(2):
        attempt_seed = (baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = RandomNoise.execute(attempt_seed)[0]
        sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        candidate = comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        try:
            candidate_embedding, detection_confidence = baseline._face_embedding(
                candidate, f"generated candidate {offset + 1}"
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
                "attempt": offset + 1,
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
        if similarity >= IDENTITY_RETRY_THRESHOLD:
            break

    if selected_photo is None or selected_score < 0:
        raise RuntimeError("No face was detected in any generated candidate.")

    run_stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output_folder = f"{OUTPUT_ROOT}/{len(reference_names)}-references/{run_stamp}"
    report = {
        "schema_version": 1,
        "purpose": "realism_tuned_candidate_with_multi_photo_identity_verification",
        "baseline_tag": "flux2-one-reference-v1.0.0",
        "model": baseline.MODEL_4B_BASE_NAME,
        "text_encoder": baseline.CLIP_4B_NAME,
        "vae": baseline.VAE_NAME,
        "lora_name": baseline.PRODUCTION_LORA_NAME,
        "lora_strength": CANDIDATE_LORA_STRENGTH,
        "source_references": reference_names,
        "source_reference_count": len(reference_names),
        "primary_generation_reference": reference_names[0],
        "model_reference_count": len(reference_latents),
        "derived_primary_face_crop": True,
        "reference_strategy": CANDIDATE_REFERENCE_STRATEGY,
        "reference_pixels_each": CANDIDATE_REFERENCE_PIXELS,
        "additional_reference_role": "same-person validation and candidate centroid ranking",
        "detected_identity_sources": prepared["detected_sources"],
        "sources_without_detectable_faces": prepared["missing_face_sources"],
        "scene_prompt_with_presets": scene_prompt,
        "photo_style": photo_style,
        "framing": framing,
        "moment": moment,
        "effective_prompt": effective_prompt,
        "width": baseline.OUTPUT_WIDTH,
        "height": baseline.OUTPUT_HEIGHT,
        "steps": baseline.PRODUCTION_STEPS,
        "guidance_scale": CANDIDATE_GUIDANCE_SCALE,
        "sampler": "euler",
        "selected_seed": selected_seed,
        "identity_similarity_to_reference_centroid": round(selected_score, 4),
        "identity_retry_threshold": IDENTITY_RETRY_THRESHOLD,
        "identity_attempts": attempts,
        "seconds": round(time.perf_counter() - started, 3),
        "acceptance": "Compare visually against the subject and frozen one-reference v1.",
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

        if len(names) == 1:
            photo, effective_prompt, output_folder, saved = baseline._generate_photo(
                face_reference=names[0],
                scene_prompt=composed_scene,
                seed=baseline.PRODUCTION_SEED,
                strategy_name=CANDIDATE_REFERENCE_STRATEGY,
                output_root=OUTPUT_ROOT,
                reference_pixels=CANDIDATE_REFERENCE_PIXELS,
                steps=baseline.PRODUCTION_STEPS,
                refine_pass=False,
                identity_retry_threshold=IDENTITY_RETRY_THRESHOLD,
                max_attempts=2,
                model_name=baseline.MODEL_4B_BASE_NAME,
                clip_name=baseline.CLIP_4B_NAME,
                lora_name=baseline.PRODUCTION_LORA_NAME,
                lora_strength=CANDIDATE_LORA_STRENGTH,
                use_kv_cache=False,
                identity_token=baseline.IDENTITY_TOKEN,
                guidance_scale=CANDIDATE_GUIDANCE_SCALE,
            )
            return {
                "ui": {
                    "images": saved["ui"]["images"],
                    "text": (f"Saved photo to ComfyUI/output/{output_folder}",),
                },
                "result": (photo, effective_prompt, output_folder),
            }

        photo, effective_prompt, output_folder, saved = _generate_multi_reference(
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
                    f"Saved {len(names)}-reference photo to ComfyUI/output/{output_folder}",
                ),
            },
            "result": (photo, effective_prompt, output_folder),
        }

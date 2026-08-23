from __future__ import annotations

import time

import cv2
import numpy as np
import torch

import comfy.model_management
from comfy_extras.nodes_custom_sampler import BasicGuider
from comfy_extras.nodes_flux import FluxKVCache

from . import reference_photo_studio as studio
from .scene_quality import apply_scene_guardrails


SCENE_MODEL = "flux-2-klein-9b-kv-fp8.safetensors"
SCENE_CLIP = "qwen_3_8b_fp8mixed.safetensors"
SCENE_STEPS = 4
SCENE_REFERENCE_PIXELS = 640 * 640
SCENE_ANCHOR_PIXELS = 384 * 576
FINAL_SEED_OFFSET = 37


def _remove_anchor_identity(image: torch.Tensor) -> tuple[torch.Tensor, dict]:
    rgb = np.clip(image[0].detach().float().cpu().numpy() * 255.0, 0, 255).astype(np.uint8)
    faces = studio.baseline._face_analyzer().get(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not faces:
        raise RuntimeError("No central face was detected in the complex-scene layout pass.")
    face = max(
        faces,
        key=lambda item: float(
            (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
        ),
    )
    height, width = rgb.shape[:2]
    x1, y1, x2, y2 = [float(value) for value in face.bbox]
    face_width = x2 - x1
    face_height = y2 - y1
    left = max(0, int(round(x1 - face_width * 0.45)))
    right = min(width, int(round(x2 + face_width * 0.45)))
    top = max(0, int(round(y1 - face_height * 0.65)))
    bottom = min(height, int(round(y2 + face_height * 0.45)))
    region = rgb[top:bottom, left:right]
    tiny = cv2.resize(region, (6, 8), interpolation=cv2.INTER_AREA)
    obscured = cv2.resize(
        tiny, (region.shape[1], region.shape[0]), interpolation=cv2.INTER_LINEAR
    )
    sigma = max(region.shape[0], region.shape[1]) * 0.10
    obscured = cv2.GaussianBlur(obscured, (0, 0), sigmaX=sigma, sigmaY=sigma)
    mask = np.zeros(region.shape[:2], dtype=np.float32)
    cv2.ellipse(
        mask,
        (region.shape[1] // 2, region.shape[0] // 2),
        (max(1, region.shape[1] // 2 - 2), max(1, region.shape[0] // 2 - 2)),
        0,
        0,
        360,
        1.0,
        -1,
    )
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=max(3.0, sigma * 0.25))[:, :, None]
    masked = rgb.astype(np.float32)
    masked_region = region.astype(np.float32) * (1.0 - mask) + obscured.astype(np.float32) * mask
    masked[top:bottom, left:right] = masked_region
    tensor = torch.from_numpy(masked / 255.0).unsqueeze(0).to(dtype=image.dtype)
    return tensor, {
        "face_bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
        "obscured_bbox": [left, top, right, bottom],
        "method": "strong_pixelation_blur_with_feathered_head_mask",
    }


def _scene_layout_prompt(composed_scene: str, contract: dict) -> str:
    guarded = apply_scene_guardrails(composed_scene, contract)
    return (
        "Create a new realistic photograph using Picture 1 only for the adult man's approximate body proportions and "
        "general appearance. Follow the requested scene exactly, prioritize a coherent background and natural activity, "
        "and do not copy Picture 1's background, pose, clothing, lighting, or expression. "
        f"Photo request: {guarded}"
    )


def _final_identity_prompt(composed_scene: str, contract: dict) -> str:
    guarded = apply_scene_guardrails(composed_scene, contract)
    return (
        "Create one new coherent photorealistic photograph. Picture 1 is a low-resolution scene-layout reference only and "
        "its central person's identity was intentionally obscured. Use its approximate location, camera viewpoint, "
        "composition, activity, body placement, lighting, and background logic, but reconstruct every person and object "
        "as new in-camera content rather than copying pixels. Do not copy the face or identity of its central person. "
        "Pictures 2 and 3 are identity evidence for the central person; Picture 3 is a closer crop of Picture 2, not another "
        "person. The trained identity token is m1tchperson. Render the central person as unmistakably the exact m1tchperson "
        "identity shown in Pictures 2 and 3, preserving current apparent age, facial proportions, eyes, eyebrows, nose, "
        "mouth, ears, jaw, hairline, hair color, and natural unretouched skin. Re-render the entire frame as one in-camera "
        "capture; never paste, swap, smooth, sharpen, or relight the face separately. "
        f"Requested result: {guarded}"
    )


def _generate_scene_anchor(prepared: dict, composed_scene: str, contract: dict) -> tuple[torch.Tensor, dict]:
    studio.baseline._require_model("diffusion_models", SCENE_MODEL)
    studio.baseline._require_model("text_encoders", SCENE_CLIP)
    started = time.perf_counter()
    model = clip = vae = None
    try:
        model = studio.comfy_nodes.UNETLoader().load_unet(SCENE_MODEL, "default")[0]
        model = FluxKVCache.execute(model)[0]
        clip = studio.comfy_nodes.CLIPLoader().load_clip(SCENE_CLIP, "flux2", "default")[0]
        vae = studio.comfy_nodes.VAELoader().load_vae(studio.baseline.VAE_NAME)[0]
        source = studio.comfy_nodes.LoadImage().load_image(prepared["selected_reference"])[0][:1, :, :, :3]
        source = studio.baseline._resize_reference(source, SCENE_REFERENCE_PIXELS)
        reference_latent = studio.comfy_nodes.VAEEncode().encode(vae, source)[0]["samples"]
        prompt = _scene_layout_prompt(composed_scene, contract)
        positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, prompt)[0]
        positive = studio.node_helpers.conditioning_set_values(
            positive, {"reference_latents": [reference_latent]}, append=True
        )
        guider = BasicGuider.execute(model, positive)[0]
        sampler = studio.KSamplerSelect.execute("euler")[0]
        sigmas = studio.Flux2Scheduler.execute(
            SCENE_STEPS, studio.OUTPUT_WIDTH, studio.OUTPUT_HEIGHT
        )[0]
        latent = studio.EmptyFlux2LatentImage.execute(
            studio.OUTPUT_WIDTH, studio.OUTPUT_HEIGHT, 1
        )[0]
        seed = studio.baseline.PRODUCTION_SEED
        noise = studio.RandomNoise.execute(seed)[0]
        sampled = studio.SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        anchor = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0].detach().cpu()
        return anchor, {
            "model": SCENE_MODEL,
            "text_encoder": SCENE_CLIP,
            "steps": SCENE_STEPS,
            "seed": seed,
            "reference": prepared["selected_reference"],
            "reference_pixels": SCENE_REFERENCE_PIXELS,
            "seconds": round(time.perf_counter() - started, 3),
        }
    finally:
        del model, clip, vae
        comfy.model_management.unload_all_models()
        comfy.model_management.soft_empty_cache()


def generate_complex_candidate(
    prepared: dict,
    composed_scene: str,
    contract: dict,
    profile: dict,
) -> dict:
    anchor, layout_report = _generate_scene_anchor(prepared, composed_scene, contract)
    masked_anchor, identity_removal = _remove_anchor_identity(anchor)
    low_resolution_anchor = studio.baseline._resize_reference(
        masked_anchor, SCENE_ANCHOR_PIXELS
    )

    final_started = time.perf_counter()
    model = studio.comfy_nodes.UNETLoader().load_unet(
        studio.baseline.MODEL_4B_BASE_NAME, "default"
    )[0]
    model = studio.comfy_nodes.LoraLoaderModelOnly().load_lora_model_only(
        model, studio.baseline.PRODUCTION_LORA_NAME, profile["lora_strength"]
    )[0]
    clip = studio.comfy_nodes.CLIPLoader().load_clip(
        studio.baseline.CLIP_4B_NAME, "flux2", "default"
    )[0]
    vae = studio.comfy_nodes.VAELoader().load_vae(studio.baseline.VAE_NAME)[0]
    anchor_latent = studio.comfy_nodes.VAEEncode().encode(vae, low_resolution_anchor)[0]["samples"]
    identity_latents = [
        studio.comfy_nodes.VAEEncode().encode(vae, image)[0]["samples"]
        for image in prepared["latent_images"]
    ]
    prompt = _final_identity_prompt(composed_scene, contract)
    positive = studio.comfy_nodes.CLIPTextEncode().encode(clip, prompt)[0]
    positive = studio.node_helpers.conditioning_set_values(
        positive,
        {"reference_latents": [anchor_latent, *identity_latents]},
        append=True,
    )
    negative = studio.comfy_nodes.CLIPTextEncode().encode(clip, "")[0]
    guider = studio.CFGGuider.execute(model, positive, negative, profile["guidance_scale"])[0]
    sampler = studio.KSamplerSelect.execute("euler")[0]
    sigmas = studio.Flux2Scheduler.execute(
        studio.baseline.PRODUCTION_STEPS, studio.OUTPUT_WIDTH, studio.OUTPUT_HEIGHT
    )[0]
    latent = studio.EmptyFlux2LatentImage.execute(studio.OUTPUT_WIDTH, studio.OUTPUT_HEIGHT, 1)[0]

    attempts = []
    selected_photo = None
    selected_score = -1.0
    selected_confidence = 0.0
    selected_seed = studio.baseline.PRODUCTION_SEED + FINAL_SEED_OFFSET
    for offset in (FINAL_SEED_OFFSET, FINAL_SEED_OFFSET + 1):
        seed = (studio.baseline.PRODUCTION_SEED + offset) % (1 << 64)
        noise = studio.RandomNoise.execute(seed)[0]
        sampled = studio.SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        candidate = studio.comfy_nodes.VAEDecode().decode(vae, sampled)[0]
        try:
            embedding, confidence = studio.baseline._face_embedding(
                candidate, f"complex-scene candidate {len(attempts) + 1}"
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
                "attempt": len(attempts) + 1,
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
        raise RuntimeError("No face was detected in the complex-scene identity pass.")
    return {
        "photo": selected_photo,
        "effective_prompt": prompt,
        "similarity": selected_score,
        "detection_confidence": selected_confidence,
        "selected_seed": selected_seed,
        "attempts": attempts,
        "layout_stage": layout_report,
        "identity_stage": {
            "model": studio.baseline.MODEL_4B_BASE_NAME,
            "lora": studio.baseline.PRODUCTION_LORA_NAME,
            "steps": studio.baseline.PRODUCTION_STEPS,
            "anchor_pixels": SCENE_ANCHOR_PIXELS,
            "anchor_shape": list(low_resolution_anchor.shape),
            "anchor_identity_removal": identity_removal,
            "seconds": round(time.perf_counter() - final_started, 3),
        },
    }
